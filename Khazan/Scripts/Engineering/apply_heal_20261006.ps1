param([switch]$WaitForEditorExit, [switch]$ValidateOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$expectedRoot = [System.IO.Path]::GetFullPath('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
if ($projectRoot -ne $expectedRoot) { throw 'Heal installer requires the original Khazan project.' }
$taskRoot = Join-Path $projectRoot 'Saved/HealImplementation_20261006'
$reportRoot = Join-Path $projectRoot 'Metadata/HealImplementation_20261006'
$manifest = Get-Content -LiteralPath (Join-Path $taskRoot 'ApplyManifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$projectFile = Join-Path $projectRoot 'Khazan.uproject'
$stateFile = Join-Path $reportRoot 'ApplyStatus.json'

function Write-ApplyState($phase, $details) {
    @{phase=$phase; utc=(Get-Date).ToUniversalTime().ToString('o'); pid=$PID; details=$details} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $stateFile -Encoding UTF8
}
function Get-MainEditors {
    Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine.Replace('/', '\').IndexOf($projectFile, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    }
}
function Confirm-PreparedFiles {
    foreach ($row in $manifest.source_inputs) {
        if ((Get-FileHash -LiteralPath (Join-Path $projectRoot $row.file) -Algorithm SHA256).Hash -ne $row.sha256) {
            throw "Source changed after verified build: $($row.file)"
        }
    }
    foreach ($row in $manifest.assets) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $row.file))
        $contentRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'Content/'))
        if (-not $target.StartsWith($contentRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Asset target escaped Content.' }
        $prepared = Join-Path $taskRoot (Join-Path 'ReadyContent' $row.file)
        if ((Get-FileHash -LiteralPath $prepared -Algorithm SHA256).Hash -ne $row.prepared_sha256) { throw "Prepared asset changed: $($row.file)" }
        if (Test-Path -LiteralPath $target) {
            $currentHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            if ($currentHash -ne $row.before_sha256 -and $currentHash -ne $row.prepared_sha256) { throw "Main asset changed: $($row.file)" }
        } elseif ($row.before_sha256) { throw "Existing asset missing: $($row.file)" }
    }
}

try {
    Confirm-PreparedFiles
    $mainEditors = @(Get-MainEditors)
    if ($ValidateOnly) {
        Write-ApplyState 'Prepared' @{asset_count=$manifest.assets.Count; main_editor_pids=@($mainEditors.ProcessId); validation=$true}
        exit 0
    }
    if ($mainEditors.Count -gt 0 -and -not $WaitForEditorExit) { throw 'Close the main editor before applying Heal, or use -WaitForEditorExit.' }
    if ($mainEditors.Count -gt 0) { Write-ApplyState 'WaitingForEditorExit' @{main_editor_pids=@($mainEditors.ProcessId); asset_count=$manifest.assets.Count} }
    while (@(Get-MainEditors).Count -gt 0) { Start-Sleep -Seconds 2 }
    # A user may save changes while this helper waits. Recheck everything before any write.
    Confirm-PreparedFiles
    Write-ApplyState 'ApplyingAssets' @{asset_count=$manifest.assets.Count}
    $installed = @()
    foreach ($row in $manifest.assets) {
        $destination = Join-Path $projectRoot $row.file
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        if (-not (Test-Path -LiteralPath $destination) -or (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $row.prepared_sha256) {
            Copy-Item -LiteralPath (Join-Path $taskRoot (Join-Path 'ReadyContent' $row.file)) -Destination $destination
        }
        $installedHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($installedHash -ne $row.prepared_sha256) { throw "Installed hash mismatch: $($row.file)" }
        $installed += @{file=$row.file; before_sha256=$row.before_sha256; installed_sha256=$installedHash}
    }
    @{utc=(Get-Date).ToUniversalTime().ToString('o'); assets=$installed; count=$installed.Count; main_editor_reloaded=$false} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reportRoot 'AssetInstallManifest.json') -Encoding UTF8
    Write-ApplyState 'BuildingMainProject' @{installed_assets=$installed.Count}
    foreach ($row in $manifest.source_inputs) { (Get-Item -LiteralPath (Join-Path $projectRoot $row.file)).LastWriteTime = Get-Date }
    & 'C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat' KhazanEditor Win64 Development "-Project=$projectFile" -WaitMutex -NoHotReloadFromIDE -DisableLiveCoding 2>&1 |
        Tee-Object -FilePath (Join-Path $reportRoot 'ColdBuild_MainAfterApply.log')
    if ($LASTEXITCODE -ne 0) { throw "Main build failed with exit code $LASTEXITCODE; see ColdBuild_MainAfterApply.log." }
    Write-ApplyState 'Complete' @{installed_assets=$installed.Count; build='Succeeded'; editor_reopened=$false}
} catch {
    Write-ApplyState 'Stopped' @{error=$_.Exception.Message; recovery='Review the changed file or build log, then rerun this script. Existing backups are under Before.'}
    throw
}
