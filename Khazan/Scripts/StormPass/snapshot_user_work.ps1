param([ValidateSet('Capture','Verify')][string]$Mode = 'Verify')
$ErrorActionPreference = 'Stop'
$projectDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$repositoryDir = (git -C $projectDir rev-parse --show-toplevel).Trim()
$reportFile = Join-Path $projectDir 'Saved/ImportReports/StormPass_UserWork_Baseline_20260907.json'
if ($Mode -eq 'Capture') {
    if (Test-Path -LiteralPath $reportFile) { throw 'Baseline already exists; refusing overwrite.' }
    $paths = @((git -C $repositoryDir -c core.quotepath=false diff --name-only),
               (git -C $repositoryDir -c core.quotepath=false ls-files --others --exclude-standard)) |
        ForEach-Object { $_ } | Sort-Object -Unique
    $records = foreach ($relative in $paths) {
        if ($relative -match '^Khazan/(Scripts/StormPass/|Docs/Art/|Content/_Art/Kazan/Environment/StormPass/)') { continue }
        $absolute = [IO.Path]::GetFullPath((Join-Path $repositoryDir $relative))
        if (-not $absolute.StartsWith($repositoryDir.Replace('/', '\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Path outside repository: $relative"
        }
        $present = Test-Path -LiteralPath $absolute -PathType Leaf
        [pscustomobject]@{path=$relative; exists=$present; sha256=$(if ($present) {(Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash} else {$null})}
    }
    $payload = [pscustomobject]@{captured_at=(Get-Date -Format o); head=(git -C $repositoryDir rev-parse HEAD).Trim(); records=@($records)}
    [IO.File]::WriteAllText($reportFile, ($payload | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    "Captured $(@($records).Count) pre-existing user files/deletions."
} else {
    $payload = Get-Content -LiteralPath $reportFile -Encoding UTF8 -Raw | ConvertFrom-Json
    $failures = foreach ($record in $payload.records) {
        $absolute = Join-Path $repositoryDir $record.path
        $present = Test-Path -LiteralPath $absolute -PathType Leaf
        if ($present -ne $record.exists) { $record.path }
        elseif ($present -and (Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash -ne $record.sha256) { $record.path }
    }
    if (@($failures).Count) { throw "User work changed: $($failures -join ', ')" }
    "Verified $($payload.records.Count) pre-existing user files/deletions unchanged."
}
