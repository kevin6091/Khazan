param(
    [ValidateSet('Inspect','Bind','Restore')][string]$Action = 'Inspect',
    [int]$MainProcessId = 13700
)
# Offline opt-in only. Never stop a process or write Main binaries/assets.
$ErrorActionPreference = 'Stop'
$MainRoot = [IO.Path]::GetFullPath('C:\Users\user\Desktop\GitProject\Khazan\Khazan')
$WorkRoot = [IO.Path]::GetFullPath('C:\Users\user\Desktop\GitProject\Khazan_PlayerPartsWork_20261007\Khazan')
$ReportRoot = [IO.Path]::GetFullPath($PSScriptRoot)
if ($ReportRoot -ne (Join-Path $MainRoot 'Metadata\PlayerParts_20261008\WaistJitter')) { throw 'Unexpected report directory' }
$BindingPath = Join-Path $ReportRoot 'StockBinding.json'
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Check([bool]$Condition, [string]$Message) { if (!$Condition) { throw $Message } }
function WorkPath([string]$Relative) {
    $Path = [IO.Path]::GetFullPath((Join-Path $WorkRoot $Relative))
    Check ($Path.StartsWith($WorkRoot + '\', [StringComparison]::OrdinalIgnoreCase)) 'Target escapes Work'
    Check ($Relative -match '^Binaries/Win64/UnrealEditor(?:-Khazan(?:-\d+)?\.(dll|pdb)|\.modules)$') 'Unapproved Work binary target'
    $Path
}
function AssertWorkAbsent {
    $Rows = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(UnrealEditor(?:-Cmd)?|UnrealBuildTool|dotnet|LiveCodingConsole)\.exe$' })
    foreach ($Row in $Rows) {
        if ($Row.Name -match '^UnrealEditor') { Check (![string]::IsNullOrWhiteSpace($Row.CommandLine)) 'Cannot determine an editor project; abort' }
        if ($Row.CommandLine) {
            $Command = $Row.CommandLine.Replace('/', '\')
            Check ($Command.IndexOf($WorkRoot, [StringComparison]::OrdinalIgnoreCase) -lt 0) ('Work editor/build still active: ' + $Row.ProcessId)
        }
    }
}
function WriteBinding($Data) {
    $Temporary = $BindingPath + '.tmp'
    [IO.File]::WriteAllText($Temporary, ($Data | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $Temporary -Destination $BindingPath -Force
}
function ReplaceWork([string]$Source, [string]$Relative, [string]$ExpectedSha) {
    $Target = WorkPath $Relative
    AssertWorkAbsent
    $Pending = $Target + '.waist_stock_pending'
    Check (!(Test-Path -LiteralPath $Pending)) 'A previous binary staging file remains; inspect before continuing'
    Copy-Item -LiteralPath $Source -Destination $Pending
    Check ((Sha $Pending) -eq $ExpectedSha) 'Staged binary hash mismatch'
    Move-Item -LiteralPath $Pending -Destination $Target -Force
    Check ((Sha $Target) -eq $ExpectedSha) 'Written Work binary hash mismatch'
}

if ($Action -eq 'Restore') {
    AssertWorkAbsent
    $Binding = Get-Content -LiteralPath $BindingPath -Raw | ConvertFrom-Json
    Check ($Binding.status -eq 'Bound' -and $Binding.workRoot -eq $WorkRoot) 'No matching bound stock state'
    foreach ($Entry in $Binding.boundFiles) {
        $Target = WorkPath $Entry.relativePath
        $Original = @($Binding.workFilesBefore | Where-Object { $_.relativePath -eq $Entry.relativePath })
        Check ($Original.Count -eq 1) 'Missing original file recovery record'
        if (Test-Path -LiteralPath $Target) {
            $Current = Sha $Target
            Check ($Current -eq $Entry.sha256 -or ($Binding.bindingPhase -ne 'Complete' -and $Original[0].existed -and $Current -eq $Original[0].sha256)) ('Bound binary drift: ' + $Entry.relativePath)
        } else { Check ($Binding.bindingPhase -ne 'Complete' -and !$Original[0].existed) 'A required binary is missing' }
    }
    foreach ($Entry in $Binding.workFilesBefore) {
        if ($Entry.relativePath -notin @($Binding.boundFiles.relativePath)) {
            $Untouched = WorkPath $Entry.relativePath
            if ($Entry.existed) { Check ((Sha $Untouched) -eq $Entry.sha256) 'Unreplaced private binary drift; preserve it' }
            else { Check (!(Test-Path -LiteralPath $Untouched)) 'Unexpected unbound private file appeared' }
        }
        if ($Entry.existed) {
            $Backup = [IO.Path]::GetFullPath((Join-Path $ReportRoot $Entry.backupRelativePath))
            Check ($Backup.StartsWith($ReportRoot + '\', [StringComparison]::OrdinalIgnoreCase)) 'Backup escapes report'
            Check ((Sha $Backup) -eq $Entry.sha256) 'Private backup hash mismatch'
        }
    }
    foreach ($Entry in $Binding.workFilesBefore) {
        if ($Entry.existed) { ReplaceWork (Join-Path $ReportRoot $Entry.backupRelativePath) $Entry.relativePath $Entry.sha256 }
        else {
            $Target = WorkPath $Entry.relativePath
            AssertWorkAbsent
            if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target } # Only the verified newly bound exact binary; never recursive.
        }
    }
    foreach ($Entry in $Binding.workFilesBefore) {
        $Target = WorkPath $Entry.relativePath
        if ($Entry.existed) { Check ((Sha $Target) -eq $Entry.sha256) 'Private restore readback failed' }
        else { Check (!(Test-Path -LiteralPath $Target)) 'New stock-only binary remains' }
    }
    $Binding.status = 'Restored'
    $Binding | Add-Member -NotePropertyName restoredUtc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    WriteBinding $Binding
    Write-Output 'Work private DLL/PDB/modules restored and hashes verified; Main unchanged.'
    exit
}

$MainCommand = (Get-CimInstance Win32_Process -Filter "ProcessId=$MainProcessId").CommandLine
Check ($MainCommand -and $MainCommand.Replace('/', '\').IndexOf((Join-Path $MainRoot 'Khazan.uproject'), [StringComparison]::OrdinalIgnoreCase) -ge 0) 'Expected Main process/project mismatch'
$MainModulesPath = Join-Path $MainRoot 'Binaries\Win64\UnrealEditor.modules'
$MainModules = Get-Content -LiteralPath $MainModulesPath -Raw | ConvertFrom-Json
$Name = [string]$MainModules.Modules.Khazan
Check ($Name -match '^UnrealEditor-Khazan(?:-\d+)?\.dll$') 'Unexpected selected Main DLL name'
$MainDll = [IO.Path]::GetFullPath((Join-Path (Join-Path $MainRoot 'Binaries\Win64') $Name))
$MainPdb = [IO.Path]::ChangeExtension($MainDll, '.pdb')
$Mapped = @((Get-Process -Id $MainProcessId).Modules | ForEach-Object { $_.FileName } | Where-Object {
    $_.StartsWith((Join-Path $MainRoot 'Binaries\Win64\'), [StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($_).StartsWith('UnrealEditor-Khazan', [StringComparison]::OrdinalIgnoreCase)
})
Check ($Mapped -contains $MainDll) 'Main module declaration is not mapped in expected process'
Check (Test-Path -LiteralPath $MainPdb) 'Selected Main PDB missing'
$MainSha = Sha $MainDll; $MainPdbSha = Sha $MainPdb; $MainModulesSha = Sha $MainModulesPath
$Plan = [ordered]@{ utc=[DateTime]::UtcNow.ToString('o'); mainProcessId=$MainProcessId; mainRoot=$MainRoot; workRoot=$WorkRoot;
    selectedMainPath=$MainDll; selectedMainSHA=$MainSha; selectedMainPdbSHA=$MainPdbSha; mainModulesSHA=$MainModulesSha;
    buildId=$MainModules.BuildId; observedMainProjectModules=$Mapped;
    limitation='Selected mapped Main base DLL only. Main live coding patches are recorded, not copied; no claim of live-patched Main behavior equivalence.' }
if ($Action -eq 'Inspect') { $Plan | ConvertTo-Json -Depth 6; exit }

AssertWorkAbsent
if (Test-Path -LiteralPath $BindingPath) {
    $Old = Get-Content -LiteralPath $BindingPath -Raw | ConvertFrom-Json
    Check ($Old.status -eq 'Restored') 'An existing stock binding must be restored first'
    $History = Join-Path $ReportRoot 'StockBindingHistory'; New-Item -ItemType Directory -Path $History -Force | Out-Null
    Copy-Item -LiteralPath $BindingPath -Destination (Join-Path $History ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '.json'))
}
$WorkModulesPath = WorkPath 'Binaries/Win64/UnrealEditor.modules'
$WorkModules = Get-Content -LiteralPath $WorkModulesPath -Raw | ConvertFrom-Json
$PrivateName = [string]$WorkModules.Modules.Khazan
Check ($PrivateName -match '^UnrealEditor-Khazan(?:-\d+)?\.dll$') 'Unexpected private Work module name'
$RelativeDll = 'Binaries/Win64/' + $Name
$RelativePdb = 'Binaries/Win64/' + [IO.Path]::ChangeExtension($Name, '.pdb')
$Paths = @('Binaries/Win64/UnrealEditor.modules', ('Binaries/Win64/' + $PrivateName), ('Binaries/Win64/' + [IO.Path]::ChangeExtension($PrivateName, '.pdb')), $RelativeDll, $RelativePdb) | Select-Object -Unique
$Stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$BackupRelative = 'StockPrivateBackup/' + $Stamp
$BackupFolder = Join-Path $ReportRoot $BackupRelative
New-Item -ItemType Directory -Path $BackupFolder | Out-Null
$Before = @()
foreach ($Relative in $Paths) {
    $Path = WorkPath $Relative; $Exists = Test-Path -LiteralPath $Path
    $Entry = [ordered]@{ relativePath=$Relative; existed=$Exists; sha256=$null; backupRelativePath=$null }
    if ($Exists) {
        $Entry.sha256 = Sha $Path; $Entry.backupRelativePath = $BackupRelative + '/' + [IO.Path]::GetFileName($Path)
        Copy-Item -LiteralPath $Path -Destination (Join-Path $ReportRoot $Entry.backupRelativePath)
        Check ((Sha (Join-Path $ReportRoot $Entry.backupRelativePath)) -eq $Entry.sha256) 'Private backup readback failed'
    }
    $Before += $Entry
}
Check ((Sha $MainDll) -eq $MainSha -and (Sha $MainPdb) -eq $MainPdbSha -and (Sha $MainModulesPath) -eq $MainModulesSha) 'Selected Main files changed during preparation'
foreach ($Entry in $Before) { if ($Entry.existed) { Check ((Sha (WorkPath $Entry.relativePath)) -eq $Entry.sha256) 'Private Work binary changed during backup' } }
$WorkModules.BuildId = $MainModules.BuildId; $WorkModules.Modules.Khazan = $Name
$PreparedModules = Join-Path $BackupFolder 'Bound_UnrealEditor.modules'
[IO.File]::WriteAllText($PreparedModules, ($WorkModules | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
$ModulesSha = Sha $PreparedModules
$Bound = @(@{relativePath=$RelativeDll; sha256=$MainSha}, @{relativePath=$RelativePdb; sha256=$MainPdbSha}, @{relativePath='Binaries/Win64/UnrealEditor.modules'; sha256=$ModulesSha})
# Persist verified recovery evidence before the first Work mutation.
$Plan.status = 'Bound'; $Plan.selectedWorkPath = WorkPath $RelativeDll; $Plan.workFilesBefore=$Before; $Plan.boundFiles=$Bound
$Plan.bindingPhase = 'Prepared; inspect boundFiles before launching observer'
WriteBinding $Plan
ReplaceWork $MainDll $RelativeDll $MainSha
ReplaceWork $MainPdb $RelativePdb $MainPdbSha
ReplaceWork $PreparedModules 'Binaries/Win64/UnrealEditor.modules' $ModulesSha
Check ((Sha $MainDll) -eq $MainSha -and (Sha $MainPdb) -eq $MainPdbSha -and (Sha $MainModulesPath) -eq $MainModulesSha) 'Main selected files changed; Work binding is not certified'
$Plan.bindingPhase = 'Complete'; WriteBinding $Plan
Write-Output 'Stock Main base DLL/PDB/BuildId bound in Work only; backup and SHA guards recorded.'
