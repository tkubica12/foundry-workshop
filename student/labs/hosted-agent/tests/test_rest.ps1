$ErrorActionPreference = 'Stop'
$scripts = Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts'
. (Join-Path $scripts 'rest-common.ps1')
$nativeAzCommand = (Get-Command Invoke-AzCommand).ScriptBlock
$nativeExecutable = (Get-Command pwsh -CommandType Application | Select-Object -First 1).Source
$errors = $null
$tokens = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $scripts 'lab07.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$function = $ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-Lab'}, $true)
Invoke-Expression $function.Extent.Text
$directory = Join-Path $PrivateRoot ("rest-tests-$([guid]::NewGuid().ToString('N'))")
New-Item -ItemType Directory -Path $directory | Out-Null
$Config = Join-Path $directory 'seat.config.json'
$State = Join-Path $directory 'seat.state.json'
$Conversation = Join-Path $directory 'read.json'
$ApprovalId = $null
$Confirm = $true
$Timeout = 30
$seat = @{
    owner='lab07-rest-tests';agent_name='lab07-rest-tests-s01'
    project_endpoint='https://demo-foundry.services.ai.azure.com/api/projects/demo-project'
    project_resource_id='/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/demo-group/providers/Microsoft.CognitiveServices/accounts/demo-foundry/projects/demo-project'
    model='demo-model';image=('ghcr.io/example/workshop@sha256:' + ('1' * 64))
    environment=@{TOOLBOX_ENDPOINT='https://demo-foundry.services.ai.azure.com/api/projects/demo-project/toolboxes/demo-tools/versions/1/mcp?api-version=v1'}
}
Save-Receipt $Config $seat
$script:queue = [Collections.Generic.Queue[hashtable]]::new()
$script:calls = [Collections.Generic.List[object]]::new()
$script:checks = 0
function Invoke-AzCommand {
    param([string[]]$Arguments, [int]$Seconds)
    $script:calls.Add(@{arguments=$Arguments;seconds=$Seconds})
    if ($script:queue.Count -eq 0) { throw 'Unexpected Azure CLI call; offline test refuses live execution' }
    return $script:queue.Dequeue()
}
function Enqueue($Value) {
    $script:queue.Enqueue(@{code=0;output=($Value | ConvertTo-Json -Depth 80 -Compress);error=''})
}
function Account { Enqueue @{id='00000000-0000-0000-0000-000000000001'} }
function Missing { $script:queue.Enqueue(@{code=1;output='';error='ERROR: Not Found({"error":{"code":"AgentNotFound"}})'}) }
function Assert([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
    $script:checks++
}
function Must-Fail([scriptblock]$Action, [string]$Pattern) {
    try { & $Action; throw 'Expected failure did not occur' }
    catch { Assert ($_.Exception.Message -match $Pattern) "Expected error $Pattern, got $($_.Exception.Message)" }
}
function Version([string]$Status='active') {
    return @{version='1';status=$Status;metadata=@{lab07_owner=$seat.owner;lab07_config=(Get-SeatFingerprint $seat)};
        definition=@{container_configuration=@{image=$seat.image}}}
}
function Receipt([string]$Status='active') {
    return @{config=(Get-SeatFingerprint $seat);agent=$seat.agent_name;owner=$seat.owner;version='1';status=$Status}
}
function Clear-State {
    foreach ($file in Get-ChildItem -LiteralPath $directory -File) { if ($file.FullName -ne $Config) { Remove-Item -LiteralPath $file.FullName } }
    $script:queue.Clear()
    $script:calls.Clear()
    $script:Conversation = $null
    $script:ApprovalId = $null
}
try {
    $read = Read-Seat $Config
    Assert ($read.agent_name -eq $seat.agent_name) 'Valid private assignment'
    Must-Fail { Get-PrivatePath (Join-Path $RepositoryRoot 'public.json') } 'Keep JSON'
    $altered = $seat.Clone()
    $altered.image = 'ghcr.io/example/workshop:latest'
    Save-Receipt $Config $altered
    Must-Fail { Read-Seat $Config } 'immutable'
    $altered = $seat.Clone()
    $altered.environment = @{PARTNERS_MCP_URL='https://partners.example/mcp';COMPLAINTS_MCP_URL='https://cases.example/mcp';MCP_API_KEY='literal-secret-not-allowed'}
    Save-Receipt $Config $altered
    Must-Fail { Read-Seat $Config } 'placeholder'
    Save-Receipt $Config $seat
    Assert ((Get-SeatFingerprint (Read-Seat $Config)) -eq (Get-SeatFingerprint $seat)) 'Stable configuration fingerprint'
    $other = Version
    $other.metadata.lab07_owner='lab07-different'
    Must-Fail { Assert-OwnedVersion $seat (Receipt) $other } 'ownership'

    Clear-State
    $Operation='preflight'
    Account
    $script:queue.Enqueue(@{code=0;output='future-expiry';error=''})
    Enqueue @{value=@()}
    Invoke-Lab
    Assert (-not (Test-Path $State)) 'Preflight creates no deployment receipt'
    Assert ($script:calls.Count -eq 3) 'Preflight checks account, token audience and project'

    Clear-State
    $Operation='deploy'
    Account; Missing; Enqueue (Version); Enqueue (Version)
    Invoke-Lab
    Assert ((Read-Receipt $State).status -eq 'active') 'Deploy persists active known version'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 1) 'Exactly one create POST'
    $script:calls.Clear()
    Account; Enqueue (Version)
    Invoke-Lab
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 0) 'Repeated deploy polls known version without POST'

    Clear-State
    $Operation='deploy'
    Account; Missing
    $script:queue.Enqueue(@{code=1;output='';error='ERROR: transport outcome uncertain'})
    Must-Fail { Invoke-Lab } 'uncertain'
    Assert ((Read-Receipt $State).status -eq 'create-requested') 'Uncertain create retains intent'
    Assert (-not (Read-Receipt $State).version) 'Uncertain create invents no version'
    Account
    Must-Fail { Invoke-Lab } 'known valid version'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 1) 'Uncertain create is not replayed'
    $Operation='recover-create'
    Account; Enqueue @{data=@((Version));has_more=$false}; Enqueue (Version)
    Invoke-Lab
    Assert ((Read-Receipt $State).version -eq '1') 'Recover matching version without create'

    Clear-State
    Save-Receipt $State (Receipt)
    $Operation='cleanup'
    Account
    $wrong=Version; $wrong.definition.container_configuration.image='different'
    Enqueue $wrong
    Must-Fail { Invoke-Lab } 'ownership'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'DELETE' }).Count -eq 0) 'Wrong digest forbids deletion'
    Account; Enqueue (Version); $script:queue.Enqueue(@{code=0;output='';error=''}); Missing
    Invoke-Lab
    Assert ((Read-Receipt $State).status -eq 'cleaned') 'Cleanup verifies absence before marking cleaned'
    $deletes = @($script:calls | Where-Object { $_.arguments -contains 'DELETE' })
    Assert ($deletes.Count -eq 1 -and ($deletes[0].arguments -join ' ') -match '/versions/1\?api-version=v1&force=true') 'Only the immutable version is deleted'
    Account; Missing; Missing
    Invoke-Lab
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'DELETE' }).Count -eq 1) 'Repeated cleanup independently verifies absence without DELETE'

    Clear-State
    Save-Receipt $State (Receipt)
    $Conversation=Join-Path $directory 'read.json'
    $Operation='start'
    Account; Enqueue (Version); Enqueue @{data=@((Version));has_more=$false}
    Enqueue @{id='response-1';status='completed';output=@(@{type='mcp_approval_request';id='approval-1';arguments='synthetic-read'})}
    Invoke-Lab
    Assert ((Read-Receipt $Conversation).turns.Count -eq 1) 'Trace and response persisted'
    $Operation='approve'
    $ApprovalId='stale-id'
    Account; Enqueue (Version); Enqueue @{data=@((Version));has_more=$false}
    Must-Fail { Invoke-Lab } 'exact pending'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 1) 'Stale approval sends no POST'
    $ApprovalId='approval-1'
    Account; Enqueue (Version); Enqueue @{data=@((Version));has_more=$false}
    $script:queue.Enqueue(@{code=1;output='';error='ERROR: uncertain response'})
    Must-Fail { Invoke-Lab } 'uncertain'
    Assert (Test-Path ([IO.Path]::ChangeExtension($Conversation,'.pending.json'))) 'Uncertain turn retains pending marker'
    Account; Enqueue (Version); Enqueue @{data=@((Version));has_more=$false}
    Must-Fail { Invoke-Lab } 'Previous POST uncertain'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 2) 'Approval transport failure is not replayed'

    Clear-State
    Save-Receipt $State (Receipt)
    $Conversation=Join-Path $directory 'reject.json'
    Save-Receipt $Conversation @{config=(Get-SeatFingerprint $seat);version='1';turns=@();response=@{id='prior';output=@(@{type='mcp_approval_request';id='approval-reject'})}}
    $Operation='reject'
    $ApprovalId='approval-reject'
    Account; Enqueue (Version); Enqueue @{data=@((Version));has_more=$false}
    Enqueue @{id='rejected';status='failed';output=@();error=@{code='interrupt_rejected';message='explicit denial'}}
    Must-Fail { Invoke-Lab } 'interrupt_rejected'
    Assert ((Read-Receipt $Conversation).response.status -eq 'failed') 'Rejection persists failed response, not success'
    Assert (-not (Test-Path ([IO.Path]::ChangeExtension($Conversation,'.pending.json')))) 'Known rejection is not an uncertain POST'

    Clear-State
    Save-Receipt $State (Receipt)
    $Operation='start'; $Conversation=Join-Path $directory 'multi.json'
    Account; Enqueue (Version); Enqueue @{data=@((Version),(Version));has_more=$true}
    Must-Fail { Invoke-Lab } 'another version'
    Assert (@($script:calls | Where-Object { $_.arguments -contains 'POST' }).Count -eq 0) 'Ambiguous routing sends no Responses request'

    Clear-State
    $Operation='preflight'
    $seatLock = Join-Path $directory 'seat.lock'
    [IO.File]::WriteAllText($seatLock,'held')
    Must-Fail { Invoke-Lab } 'holds the lock'
    Assert (Test-Path $seatLock) 'Existing lock is never removed by a losing process'
    $savedState = $State
    $State = Join-Path $directory 'alternate.state.json'
    Must-Fail { Invoke-Lab } 'holds the lock'
    Assert ($script:calls.Count -eq 0) 'Alternate receipt filename cannot bypass the seat lock'
    $State = $savedState
    Remove-Item -LiteralPath $seatLock
    $script:queue.Enqueue(@{code=1;output='';error='ERROR: (Forbidden) denied'})
    Must-Fail { Invoke-SeatRest GET 'https://demo.example' -AllowNotFound } 'Forbidden'
    Assert ($script:queue.Count -eq 0) 'NotFound exception never swallows permission failures'
    $script:queue.Enqueue(@{code=1;output='';error='ERROR: Not Found({"error":{"code":"not_found","message":"Absent [Request ID: synthetic-id]"}})'})
    Assert ($null -eq (Invoke-SeatRest GET 'https://demo.example' -AllowNotFound)) 'Foundry wire not_found is recognized without matching generic error text'

    Clear-State
    $Operation='backup'
    $backupOutput = @(Invoke-Lab)
    $archive = ($backupOutput | Where-Object { $_ -like 'Backup: *' }).Substring(8)
    try {
        Assert ($script:calls.Count -eq 0) 'Backup works without Azure login or network calls'
        $zip = [IO.Compression.ZipFile]::OpenRead($archive)
        try {
            Assert (@($zip.Entries.FullName).Count -eq 1 -and $zip.Entries[0].FullName -eq 'seat.config.json') 'Backup contains private JSON, not the process lock'
        } finally { $zip.Dispose() }
    } finally { if ($archive -and (Test-Path $archive)) { Remove-Item -LiteralPath $archive } }

    function Get-Command {
        param($Name, $CommandType, $ErrorAction)
        if ($Name -ne 'az') { throw 'Unexpected executable discovery' }
        return @(@{Source=$nativeExecutable}, @{Source='unused-secondary-az.cmd'})
    }
    try {
        $result = & $nativeAzCommand -Arguments @('-NoProfile','-NonInteractive','-Command',"Write-Output 'native-client-ok'")
        Assert ($result.code -eq 0 -and $result.output.Trim() -eq 'native-client-ok') 'Native subprocess uses the first executable, not all command matches'
        Must-Fail { & $nativeAzCommand -Arguments @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 5') -Seconds 1 } 'timed out'
    } finally { Remove-Item Function:\Get-Command }

    Write-Output "PASS: $script:checks REST client regression checks; no cloud calls"
} finally {
    foreach ($file in Get-ChildItem -LiteralPath $directory -File) { Remove-Item -LiteralPath $file.FullName }
    Remove-Item -LiteralPath $directory
}
