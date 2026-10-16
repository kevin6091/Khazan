# Exact task delivery. Never closes an editor or edits unrelated assets.
$ErrorActionPreference = 'Stop'
$mainRoot = [System.IO.Path]::GetFullPath('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
$projectFile = Join-Path $mainRoot 'Khazan.uproject'
$taskRoot = Join-Path $mainRoot 'Saved/HealWeapon_20261006'
$reportRoot = Join-Path $mainRoot 'Metadata/HealWeapon_20261006'
$manifest = Get-Content -LiteralPath (Join-Path $taskRoot 'ApplyManifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$statusFile = Join-Path $reportRoot 'ApplyStatus.json'
function Write-Status([string]$stage, $details) {
    @{stage=$stage; utc=(Get-Date).ToUniversalTime().ToString('o'); details=$details} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}
try {
    $editors = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($projectFile,[System.StringComparison]::OrdinalIgnoreCase) -ge 0 })
    if ($editors.Count) { throw 'Main editor still open. Normal exit is required before delivery.' }
    if ($manifest.Count -ne 9) { throw 'Expected exactly seven saved packages and two original path removals.' }
    foreach ($row in $manifest) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $mainRoot $row.path))
        if (-not $target.StartsWith($mainRoot + '\',[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Manifest escaped main project.' }
        if ($row.beforeSha256) {
            if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $row.beforeSha256) { throw "User asset changed: $($row.path)" }
        } elseif (Test-Path -LiteralPath $target) { throw "New target now exists: $($row.path)" }
        if ($row.action -eq 'copy') {
            $prepared = Join-Path (Join-Path $taskRoot 'ReadyContent') $row.path
            if ((Get-FileHash -LiteralPath $prepared -Algorithm SHA256).Hash -ne $row.preparedSha256) { throw "Prepared asset changed: $($row.path)" }
        } elseif ($row.action -ne 'remove') { throw 'Unknown manifest action.' }
    }
    Write-Status 'Applying' @{packages=7; removed_original_paths=2}
    $installed = foreach ($row in $manifest) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $mainRoot $row.path))
        if ($row.action -eq 'copy') {
            New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
            Copy-Item -LiteralPath (Join-Path (Join-Path $taskRoot 'ReadyContent') $row.path) -Destination $target
            $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            if ($hash -ne $row.preparedSha256) { throw "Installed hash differs: $($row.path)" }
            [pscustomobject]@{path=$row.path;action='copy';sha256=$hash}
        } else {
            # Exact original asset, already backed up; UE rename found no package referencers.
            Remove-Item -LiteralPath $target
            [pscustomobject]@{path=$row.path;action='remove';absent=(-not (Test-Path -LiteralPath $target))}
        }
    }
    $installed | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reportRoot 'AssetInstallManifest.json') -Encoding UTF8
    foreach ($path in @('Source/Khazan/Ability/PlayerAbility/KZHealAbility.h','Source/Khazan/Ability/PlayerAbility/KZHealAbility.cpp','Source/Khazan/Tests/KZHealAbilityPIETest.cpp')) {
        (Get-Item -LiteralPath (Join-Path $mainRoot $path)).LastWriteTime = Get-Date
    }
    Write-Status 'Building' @{assets_installed=$true}
    & 'C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat' KhazanEditor Win64 Development $projectFile -WaitMutex -NoHotReloadFromIDE *> (Join-Path $reportRoot 'ColdBuild_Main.log')
    if ($LASTEXITCODE -ne 0) { throw "Main cold build failed, exit $LASTEXITCODE." }
    Write-Status 'Complete' @{assets_installed=$true;build='Succeeded';packages=7;removed_original_paths=2}
} catch {
    Write-Status 'Stopped' @{error=$_.Exception.Message}
    throw
}
