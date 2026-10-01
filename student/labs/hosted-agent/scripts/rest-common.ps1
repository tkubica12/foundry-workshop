$ErrorActionPreference = 'Stop'
$LabRoot = [IO.DirectoryInfo]$PSScriptRoot
$RepositoryRoot = $LabRoot.Parent.Parent.Parent.Parent.FullName
$PrivateRoot = Join-Path $RepositoryRoot '.workshop\hosted-agent'

function Get-PrivatePath([string]$Path) {
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    $root = [IO.Path]::GetFullPath($PrivateRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($root, [StringComparison]::Ordinal) -or [IO.Path]::GetExtension($full) -ne '.json') {
        throw 'Keep JSON configuration and receipts under .workshop/hosted-agent in this checkout'
    }
    $item = $full
    while ($item -and $item -ne $RepositoryRoot) {
        if ((Test-Path -LiteralPath $item) -and (Get-Item -LiteralPath $item -Force).LinkType) {
            throw 'Private paths must not traverse symbolic links'
        }
        $item = Split-Path $item -Parent
    }
    return $full
}

function Save-Receipt([string]$Path, $Value) {
    [IO.Directory]::CreateDirectory((Split-Path $Path -Parent)) | Out-Null
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 80) + "`n", [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temporary, $Path, $true)
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

function Read-Receipt([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
}

function Read-Seat([string]$Path) {
    $config = Read-Receipt (Get-PrivatePath $Path)
    $fields = @('agent_name','environment','image','model','owner','project_endpoint','project_resource_id')
    if (-not $config -or (@($config.Keys | Sort-Object) -join ',') -ne ($fields -join ',')) {
        throw 'Configuration fields must match config.example.json exactly'
    }
    foreach ($field in $fields | Where-Object { $_ -ne 'environment' }) {
        if ($config[$field] -isnot [string] -or [string]::IsNullOrWhiteSpace($config[$field])) { throw "Missing string: $field" }
    }
    if ($config.owner -cnotmatch '^lab07-[a-z0-9-]{3,32}$' -or
        $config.agent_name -cnotmatch ('^' + [regex]::Escape($config.owner) + '-s[0-9]{2,3}$')) {
        throw 'Use an assigned lowercase lab07-<run>-sNN name and matching owner'
    }
    $arm = [regex]::Match($config.project_resource_id,
        '^/subscriptions/([0-9a-f-]{36})/resourceGroups/([^/]+)/providers/Microsoft.CognitiveServices/accounts/([^/]+)/projects/([^/]+)$',
        [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $arm.Success -or $config.project_endpoint -cne
        "https://$($arm.Groups[3].Value).services.ai.azure.com/api/projects/$($arm.Groups[4].Value)") {
        throw 'Project ARM ID and credential-free HTTPS endpoint must match'
    }
    if ($config.image -cnotmatch '^[a-z0-9.-]+/[a-z0-9_./-]+@sha256:[a-f0-9]{64}$') { throw 'An immutable image digest is required' }
    $environment = $config.environment
    $allowed = @('TOOLBOX_ENDPOINT','PARTNERS_MCP_URL','COMPLAINTS_MCP_URL','MCP_API_KEY',
        'LAB07_RECORD_CONTENT','OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT')
    if ($environment -isnot [System.Collections.IDictionary]) { throw 'environment must be an object' }
    foreach ($key in $environment.Keys) {
        if ($key -notin $allowed -or $environment[$key] -isnot [string] -or [string]::IsNullOrWhiteSpace($environment[$key])) {
            throw 'Only approved nonempty environment values are allowed'
        }
    }
    if ($environment.Contains('TOOLBOX_ENDPOINT')) {
        if (@($environment.Keys | Where-Object { $_ -in @('MCP_API_KEY','PARTNERS_MCP_URL','COMPLAINTS_MCP_URL') }).Count) {
            throw 'Choose toolbox or direct MCP, not both'
        }
        if ($environment.TOOLBOX_ENDPOINT -cnotmatch
            ('^' + [regex]::Escape($config.project_endpoint) + '/toolboxes/[a-zA-Z0-9_-]+/versions/[0-9]+/mcp\?api-version=v1$')) {
            throw 'Use a version-pinned toolbox in the same project'
        }
    } else {
        if (@('MCP_API_KEY','PARTNERS_MCP_URL','COMPLAINTS_MCP_URL' | Where-Object { -not $environment.Contains($_) }).Count) {
            throw 'Provide a toolbox or both MCP URLs and a connection placeholder'
        }
        if ($environment.MCP_API_KEY -cnotmatch '^\$\{\{connections\.[a-zA-Z0-9_-]+\.credentials\.[a-zA-Z0-9_-]+\}\}$') {
            throw 'MCP_API_KEY must be a Foundry connection placeholder, never a literal secret'
        }
        foreach ($key in @('PARTNERS_MCP_URL','COMPLAINTS_MCP_URL')) {
            $url = [uri]$environment[$key]
            if ($url.Scheme -ne 'https' -or -not $url.Host -or $url.UserInfo -or $url.AbsolutePath -ne '/mcp' -or $url.Query -or $url.Fragment) {
                throw 'Direct MCP endpoints must be credential-free HTTPS /mcp URLs'
            }
        }
    }
    return $config
}

function Get-SeatFingerprint($Config) {
    $canonical = [ordered]@{}
    foreach ($key in $Config.Keys | Sort-Object) {
        if ($key -eq 'environment') {
            $canonical[$key] = [ordered]@{}
            foreach ($envKey in $Config.environment.Keys | Sort-Object) { $canonical[$key][$envKey] = $Config.environment[$envKey] }
        } else { $canonical[$key] = $Config[$key] }
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($canonical | ConvertTo-Json -Depth 10 -Compress))
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}

function Invoke-AzCommand([string[]]$Arguments, [int]$Seconds = 90) {
    $az = Get-Command az -CommandType Application -ErrorAction Stop | Select-Object -First 1
    if ($az.Source.EndsWith('.cmd')) { throw 'Run the REST lab in Linux PowerShell 7 in Azure Cloud Shell, not Windows az.cmd' }
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $az.Source
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'Cannot start Azure CLI' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($Seconds * 1000)) {
            $process.Kill($true)
            $process.WaitForExit()
            throw 'Azure CLI timed out; retain receipts and inspect the outcome before replay'
        }
        return @{code=$process.ExitCode;output=$stdout.GetAwaiter().GetResult();error=$stderr.GetAwaiter().GetResult()}
    } finally { $process.Dispose() }
}

function Invoke-SeatRest([string]$Method, [string]$Url, $Body = $null,
    [hashtable]$Headers = @{}, [switch]$AllowNotFound, [int]$Seconds = 90) {
    $arguments = @('rest','--method',$Method,'--url',$Url,'--resource','https://ai.azure.com','--output','json')
    $bodyFile = $null
    try {
        if ($null -ne $Body) {
            $bodyFile = Join-Path ([IO.Path]::GetTempPath()) ("lab07-$([guid]::NewGuid().ToString('N')).json")
            [IO.File]::WriteAllText($bodyFile, ($Body | ConvertTo-Json -Depth 80 -Compress), [Text.UTF8Encoding]::new($false))
            if (-not $IsWindows) { & chmod 600 $bodyFile; if ($LASTEXITCODE -ne 0) { throw 'Cannot restrict request file permissions' } }
            $arguments += @('--body', "@$bodyFile")
        }
        if ($Headers.Count) {
            $arguments += '--headers'
            foreach ($key in $Headers.Keys) { $arguments += "$key=$($Headers[$key])" }
        }
        $result = Invoke-AzCommand -Arguments $arguments -Seconds $Seconds
        if ($result.code -ne 0) {
            if ($AllowNotFound -and $result.error -match '(?i)(\(NotFound\)|"code"\s*:\s*"(NotFound|not_found|AgentNotFound|ResourceNotFound)")') { return $null }
            throw "Azure CLI REST $Method failed: $($result.error.Trim()). Retain receipts; do not blindly replay."
        }
        if ($result.error) { Write-Warning $result.error.Trim() }
        if ([string]::IsNullOrWhiteSpace($result.output)) { return $null }
        return $result.output | ConvertFrom-Json -AsHashtable
    } finally {
        if ($bodyFile -and (Test-Path -LiteralPath $bodyFile)) { Remove-Item -LiteralPath $bodyFile }
    }
}

function Get-VersionUrl($Config, $Receipt) {
    if ($Receipt.version -isnot [string] -or $Receipt.version -cnotmatch '^[0-9]+$') { throw 'No known valid version; recover rather than recreate' }
    return "$($Config.project_endpoint)/agents/$($Config.agent_name)/versions/$($Receipt.version)?api-version=v1"
}

function Assert-Receipt($Config, $Receipt) {
    if (-not $Receipt -or $Receipt.config -cne (Get-SeatFingerprint $Config) -or
        $Receipt.agent -cne $Config.agent_name -or $Receipt.owner -cne $Config.owner) {
        throw 'A matching deployment receipt is required'
    }
}

function Assert-OwnedVersion($Config, $Receipt, $Version) {
    Assert-Receipt $Config $Receipt
    if (-not $Version -or "$($Version.version)" -cne $Receipt.version -or
        $Version.metadata.lab07_owner -cne $Config.owner -or
        $Version.metadata.lab07_config -cne (Get-SeatFingerprint $Config) -or
        $Version.definition.container_configuration.image -cne $Config.image) {
        throw 'Live ownership, version or image differs; refusing operation'
    }
}

function Wait-SeatActive($Config, $Receipt, [string]$State, [int]$Timeout) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Timeout)
    do {
        $version = Invoke-SeatRest GET (Get-VersionUrl $Config $Receipt)
        Assert-OwnedVersion $Config $Receipt $version
        $Receipt.status = $version.status
        Save-Receipt $State $Receipt
        Write-Output "Version $($Receipt.version) status $($version.status)"
        if ($version.status -eq 'active') { return }
        if ($version.status -in @('failed','deleting','deleted')) { throw "Hosted version is $($version.status); inspect provisioning diagnostics" }
        Start-Sleep -Seconds 10
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Activation timed out; use status with the recorded version, not another create'
}

function Invoke-SeatTurn($Config, $Receipt, [string]$Conversation, [string]$Operation, [string]$ApprovalId) {
    if ($Receipt.status -ne 'active') { throw 'Matching active receipt required' }
    $live = Invoke-SeatRest GET (Get-VersionUrl $Config $Receipt)
    Assert-OwnedVersion $Config $Receipt $live
    if ($live.status -ne 'active') { throw 'Recorded version is not active' }
    $versions = Invoke-SeatRest GET "$($Config.project_endpoint)/agents/$($Config.agent_name)/versions?api-version=v1"
    if (@($versions.data).Count -ne 1 -or "$($versions.data[0].version)" -cne $Receipt.version -or $versions.has_more) {
        throw 'Named endpoint can route another version; do not invoke it'
    }
    $pendingPath = [IO.Path]::ChangeExtension($Conversation, '.pending.json')
    if (Test-Path -LiteralPath $pendingPath) { throw 'Previous POST uncertain; inspect pending receipt, never replay blindly' }
    if ($Operation -eq 'start') {
        if (Test-Path -LiteralPath $Conversation) { throw 'Conversation exists; reset with a new filename' }
        if ($ApprovalId) { throw 'Approval ID is valid only with approve/reject' }
        $request = @{
            input='Use the complaint read tool to retrieve complaint-003, then the partner read tool to retrieve partner-055. Call the tools; the runtime asks for approval. Do not execute writes. After both reads, summarize the returned complaint and partner and explain the next human decision using only their facts.'
            stream=$false;store=$true
        }
        $turns = @()
    } else {
        $prior = Read-Receipt $Conversation
        if (-not $prior -or $prior.config -cne (Get-SeatFingerprint $Config) -or $prior.version -cne $Receipt.version) { throw 'Conversation belongs to another deployment' }
        $pending = @($prior.response.output | Where-Object { $_.type -eq 'mcp_approval_request' -and $_.id -ceq $ApprovalId })
        if (-not $ApprovalId -or $pending.Count -ne 1) { throw 'Use one exact pending Approval ID from the latest response' }
        $request = @{
            previous_response_id=$prior.response.id
            input=@(@{type='mcp_approval_response';approval_request_id=$ApprovalId;approve=($Operation -eq 'approve')})
            stream=$false;store=$true
        }
        $turns = @($prior.turns)
    }
    $trace = [guid]::NewGuid().ToString('N')
    Save-Receipt $pendingPath @{config=(Get-SeatFingerprint $Config);operation=$Operation;trace_id=$trace;previous_response_id=$request.previous_response_id}
    $response = Invoke-SeatRest POST "$($Config.project_endpoint)/agents/$($Config.agent_name)/endpoint/protocols/openai/responses?api-version=v1" $request @{
        traceparent="00-$trace-$([guid]::NewGuid().ToString('N').Substring(0,16))-01"
    } -Seconds 240
    if (-not $response.id -or $response.output -isnot [array] -or -not $response.status) { throw 'Malformed response; pending receipt retained' }
    $turns += @{operation=$Operation;trace_id=$trace;response_id=$response.id;previous_response_id=$request.previous_response_id}
    Save-Receipt $Conversation @{config=(Get-SeatFingerprint $Config);version=$Receipt.version;response=$response;turns=$turns}
    Remove-Item -LiteralPath $pendingPath
    Write-Output "Trace ID: $trace"
    Write-Output "Response ID: $($response.id)"
    Write-Output "Status: $($response.status)"
    foreach ($item in $response.output) {
        if ($item.type -eq 'mcp_approval_request') {
            Write-Output "Approval ID: $($item.id)"
            Write-Output ('Review: ' + ($item | ConvertTo-Json -Depth 20 -Compress))
        } elseif ($item.type -eq 'message') {
            foreach ($content in $item.content) { if ($content.type -eq 'output_text') { Write-Output $content.text } }
        }
    }
    if ($response.status -eq 'failed') { throw ('Response error: ' + ($response.error | ConvertTo-Json -Compress)) }
}
