param(
    [Parameter(Mandatory)][ValidateSet('preflight','deploy','status','recover-create','cleanup','start','approve','reject','backup')][string]$Operation,
    [Parameter(Mandatory)][string]$Config,
    [Parameter(Mandatory)][string]$State,
    [string]$Conversation,
    [string]$ApprovalId,
    [switch]$Confirm,
    [ValidateRange(30,900)][int]$Timeout = 600
)
. (Join-Path $PSScriptRoot 'rest-common.ps1')

function Invoke-Lab {
    $configPath = Get-PrivatePath $Config
    $statePath = Get-PrivatePath $State
    if ($configPath -eq $statePath -or (Split-Path $configPath -Parent) -ne (Split-Path $statePath -Parent)) {
        throw 'Use separate configuration and state files in the same private seat directory'
    }
    $seat = Read-Seat $configPath
    $directory = Split-Path $statePath -Parent
    if ($directory -eq [IO.Path]::GetFullPath($PrivateRoot)) { throw 'Use a separate seat subdirectory, not the shared private root' }
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    if (-not $IsWindows) { & chmod 700 $directory; if ($LASTEXITCODE -ne 0) { throw 'Cannot restrict seat directory permissions' } }
    $conversationPath = $null
    if ($Operation -in @('start','approve','reject')) {
        if (-not $Conversation) { throw 'Specify a private conversation JSON file' }
        $conversationPath = Get-PrivatePath $Conversation
        if ((Split-Path $conversationPath -Parent) -ne $directory -or $conversationPath -in @($configPath,$statePath) -or
            $conversationPath.EndsWith('.pending.json')) { throw 'Use a distinct conversation file in the same seat directory' }
    } elseif ($Conversation -or $ApprovalId) { throw 'Conversation/ApprovalId apply only to Responses operations' }
    $lockPath = Join-Path $directory 'seat.lock'
    $lock = $null
    try {
        try { $lock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None) }
        catch [IO.IOException] { throw 'Another seat operation holds the lock; wait and inspect before removing a stale lock' }
        if ($Operation -ne 'backup') {
            $accountResult = Invoke-AzCommand -Arguments @('account','show','--output','json')
            if ($accountResult.code -ne 0) { throw "Azure CLI account check failed: $($accountResult.error)" }
            $account = $accountResult.output | ConvertFrom-Json -AsHashtable
            $subscription = $seat.project_resource_id.Split('/')[2]
            if ($account.id -ne $subscription) { throw 'Active subscription differs from the seat assignment; use az account set' }
        }
        Write-Output "Scope: $($seat.agent_name) $($seat.image)"
        Write-Output 'No model, toolbox, MCP backend, registry or role changes.'
        $receipt = Read-Receipt $statePath
        if ($receipt) { Assert-Receipt $seat $receipt }
        switch ($Operation) {
            'preflight' {
                $tokenCheck = Invoke-AzCommand -Arguments @('account','get-access-token','--resource','https://ai.azure.com','--query','expiresOn','--output','tsv')
                if ($tokenCheck.code -ne 0 -or -not $tokenCheck.output.Trim()) {
                    throw 'Foundry token unavailable. Keep Cloud Shell open; use the documented assigned-tenant az login --scope recovery, then rerun preflight.'
                }
                $null = Invoke-SeatRest GET "$($seat.project_endpoint)/connections?api-version=v1"
                Write-Output 'PASS: configuration and project access; runtime, capacity and monitoring still require qualification'
            }
            'deploy' {
                if (-not $Confirm) { throw 'Pass -Confirm to create only the assigned agent/version' }
                if ($receipt) {
                    Assert-Receipt $seat $receipt
                    if ($receipt.status -in @('cleaned','cleanup-requested')) { throw 'Seat already cleaned or cleaning; do not redeploy under the same name' }
                    Wait-SeatActive $seat $receipt $statePath $Timeout
                    return
                }
                $existing = Invoke-SeatRest GET "$($seat.project_endpoint)/agents/$($seat.agent_name)?api-version=v1" -AllowNotFound
                if ($existing) { throw 'Agent name exists; choose a newly assigned isolated name' }
                $receipt = @{config=(Get-SeatFingerprint $seat);agent=$seat.agent_name;owner=$seat.owner;status='create-requested'}
                Save-Receipt $statePath $receipt
                $environment = @{MODEL_DEPLOYMENT_NAME=$seat.model}
                foreach ($key in $seat.environment.Keys) { $environment[$key] = $seat.environment[$key] }
                $version = Invoke-SeatRest POST "$($seat.project_endpoint)/agents/$($seat.agent_name)/versions?api-version=v1" @{
                    definition=@{kind='hosted';cpu='1';memory='2Gi';protocol_versions=@(@{protocol='responses';version='2.0.0'});
                        container_configuration=@{image=$seat.image};environment_variables=$environment}
                    metadata=@{lab07_owner=$seat.owner;lab07_config=(Get-SeatFingerprint $seat)}
                    description='Optional Lab 07: read-only LangGraph instrument specialist'
                }
                $receipt.version = "$($version.version)"
                Assert-OwnedVersion $seat $receipt $version
                $receipt.status = $version.status
                Save-Receipt $statePath $receipt
                Wait-SeatActive $seat $receipt $statePath $Timeout
            }
            'status' {
                Assert-Receipt $seat $receipt
                if ($receipt.status -in @('cleaned','cleanup-requested')) { throw 'Use cleanup to verify a cleaned/uncertain-delete receipt' }
                Wait-SeatActive $seat $receipt $statePath $Timeout
            }
            'recover-create' {
                Assert-Receipt $seat $receipt
                if ($receipt.version -or $receipt.status -ne 'create-requested') { throw 'Recover only an uncertain create with no recorded version' }
                $versions = Invoke-SeatRest GET "$($seat.project_endpoint)/agents/$($seat.agent_name)/versions?api-version=v1"
                if (@($versions.data).Count -ne 1 -or $versions.has_more) { throw 'Recovery requires exactly one version; ask the facilitator, do not recreate' }
                $candidate = $versions.data[0]
                $receipt.version = "$($candidate.version)"
                $live = Invoke-SeatRest GET (Get-VersionUrl $seat $receipt)
                Assert-OwnedVersion $seat $receipt $live
                $receipt.status = $live.status
                Save-Receipt $statePath $receipt
                Write-Output 'PASS: recovered one matching owned version without a POST; run status'
            }
            'cleanup' {
                if (-not $Confirm) { throw 'Pass -Confirm to delete only the recorded owned version and sessions' }
                Assert-Receipt $seat $receipt
                $url = Get-VersionUrl $seat $receipt
                $live = Invoke-SeatRest GET $url -AllowNotFound
                if ($live) {
                    if ($receipt.status -eq 'cleaned') { throw 'Cleaned version reappeared; ask the facilitator, do not delete it' }
                    Assert-OwnedVersion $seat $receipt $live
                    $receipt.status = 'cleanup-requested'
                    Save-Receipt $statePath $receipt
                    $null = Invoke-SeatRest DELETE "$url&force=true"
                }
                if (Invoke-SeatRest GET $url -AllowNotFound) { throw 'Recorded version remains; retain receipt and inspect deletion' }
                $receipt.status = 'cleaned'
                Save-Receipt $statePath $receipt
                Write-Output 'PASS: owned version absent; no parent DELETE issued. Other versions and shared resources were not targeted.'
                Write-Output 'Deleting the last version can make the parent disappear. Monitoring/checkpoint retention is separate.'
            }
            'backup' {
                $archive = Join-Path $HOME ("$($seat.agent_name)-receipts-$([guid]::NewGuid().ToString('N')).zip")
                $files = @(Get-ChildItem -LiteralPath $directory -File -Filter '*.json')
                foreach ($file in $files) { $null = Get-PrivatePath $file.FullName }
                Compress-Archive -LiteralPath $files.FullName -DestinationPath $archive
                if (-not $IsWindows) { & chmod 600 $archive; if ($LASTEXITCODE -ne 0) { throw 'Cannot restrict archive permissions' } }
                Write-Output "Backup: $archive"
                Write-Output 'Download with Cloud Shell Manage files > Download before closing/restarting. Keep this personal recovery archive private.'
            }
            default {
                Assert-Receipt $seat $receipt
                Invoke-SeatTurn $seat $receipt $conversationPath $Operation $ApprovalId
            }
        }
    } finally {
        if ($lock) { $lock.Dispose(); Remove-Item -LiteralPath $lockPath }
    }
}

try { Invoke-Lab }
catch {
    Write-Error "FAIL: $($_.Exception.Message). Keep private state and back it up before leaving ephemeral Cloud Shell." -ErrorAction Continue
    exit 1
}
