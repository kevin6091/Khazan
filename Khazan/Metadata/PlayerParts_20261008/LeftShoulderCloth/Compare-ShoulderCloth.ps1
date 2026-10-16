# Offline-only comparison. Never opens an editor or writes assets.
# Usage: .\Compare-ShoulderCloth.ps1
# Optional profile inputs: -BaselineProfile <audit.json> -CandidateProfile <audit.json>
[CmdletBinding()]
param(
    [string]$BaselineLog = '',
    [string]$CandidateLog = '',
    [string]$BaselineProfile = '',
    [string]$CandidateProfile = '',
    [string[]]$BaselineScreenshots = @(),
    [string[]]$CandidateScreenshots = @(),
    [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
$ShoulderReportDirectory = [IO.Path]::GetDirectoryName($MyInvocation.MyCommand.Path)
if (!$BaselineLog) { $BaselineLog = Join-Path $ShoulderReportDirectory 'BaselineNative.log' }
if (!$CandidateLog) { $CandidateLog = Join-Path $ShoulderReportDirectory 'CandidateNative.log' }
if (!$BaselineProfile) { $BaselineProfile = Join-Path $ShoulderReportDirectory 'BaselineProfileAudit.json' }
if (!$CandidateProfile) { $CandidateProfile = Join-Path $ShoulderReportDirectory 'CandidateProfileAudit.json' }
if (!$Output) { $Output = Join-Path $ShoulderReportDirectory 'NativeComparison.json' }
$Invariant = [Globalization.CultureInfo]::InvariantCulture

function Read-Tokens([string]$Line) {
    $fields = [ordered]@{}
    foreach ($match in [regex]::Matches($Line, '(?<key>[A-Za-z][A-Za-z0-9_]*)=(?<value>[^\s]+)')) {
        $value = $match.Groups['value'].Value
        $number = 0.0
        if ([double]::TryParse($value, [Globalization.NumberStyles]::Float, $Invariant, [ref]$number)) { $value = $number }
        $fields[$match.Groups['key'].Value] = $value
    }
    return $fields
}
function File-Evidence([string]$Path) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $file = Get-Item -LiteralPath $Path
    return [ordered]@{ path = $file.FullName; bytes = $file.Length; sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
}
function Read-Run([string]$Path) {
    $run = [ordered]@{ available = $false; file = $null; selectedResult = 'Missing'; lastCompletedResult = $null; eventsComplete = $false; warnings = @(); shoulder = [ordered]@{}; clothMotion = [ordered]@{}; hairMotion = $null; surface = [ordered]@{}; surfaceWeights = [ordered]@{}; skippedSurface = @() }
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { $run.warnings += 'Log not copied yet.'; return $run }
    $run.available = $true; $run.file = File-Evidence $Path
    $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8)
    $start = -1; $completed = -1; $result = $null
    for ($i = 0; $i -lt $lines.Count; ++$i) {
        if ($lines[$i] -match 'LogAutomationController:.*Test Started\..*Path=\{Khazan\.PlayerParts\.PIE\}') { $start = $i }
        if ($lines[$i] -match 'LogAutomationController:.*Test Completed\. Result=\{(?<result>[^}]+)\}.*Path=\{Khazan\.PlayerParts\.PIE\}') {
            $completed = $i; $result = $Matches['result']
            $run.lastCompletedResult = [ordered]@{ result = $result; line = $i + 1; raw = $lines[$i] }
        }
    }
    $begin = -1; $end = -1
    if ($start -gt $completed) {
        $run.selectedResult = 'Incomplete'; $begin = $start
        $run.warnings += 'A later PIE started without a completed result; prior completed result is not treated as current success.'
    } elseif ($completed -ge 0) {
        $run.selectedResult = $result
        # UE prints Test Completed BEFORE its buffered BeginEvents/metrics/EndEvents.
        for ($i = $completed + 1; $i -lt $lines.Count; ++$i) {
            if ($begin -lt 0 -and $lines[$i] -match 'LogAutomationController: BeginEvents: Khazan\.PlayerParts\.PIE\s*$') { $begin = $i }
            if ($begin -ge 0 -and $lines[$i] -match 'LogAutomationController: EndEvents: Khazan\.PlayerParts\.PIE\s*$') { $end = $i; break }
        }
        if ($begin -lt 0) { $begin = $completed; $run.warnings += 'Completed result lacks its buffered PIE event block.' }
    } else {
        $run.selectedResult = 'NoCompletedPIE'; $begin = [Math]::Max(0, $start)
        $run.warnings += 'No completed native PlayerParts PIE result found.'
    }
    $run.eventsComplete = $end -ge 0
    if ($end -lt 0) { $end = $lines.Count - 1 }
    $run.selectedLineRange = @(($begin + 1), ($end + 1))
    for ($i = $begin; $i -le $end; ++$i) {
        if ($i -lt 0) { continue }
        $line = $lines[$i]
        if ($line -match 'LogAutomationController: ShoulderFlutterMetrics ') { $f = Read-Tokens $line; $run.shoulder[[string]$f.group] = $f }
        elseif ($line -match 'LogAutomationController: ClothMotion part=') { $f = Read-Tokens $line; $run.clothMotion[[string]$f.part] = $f }
        elseif ($line -match 'LogAutomationController: HairMotion ') { $run.hairMotion = Read-Tokens $line }
        elseif ($line -match 'LogAutomationController: ClothSurfaceProbe part=') {
            $f = Read-Tokens $line; $run.surface[('{0}:{1}' -f $f.part, [int]$f.stage)] = $f
            if ($f.sampledVertices -le 0 -or $f.externalActors -le 0 -or $f.finite -ne 1) { $run.warnings += ('Invalid/empty surface sample at {0}:{1}; zero inside does not prove clearance.' -f $f.part, $f.stage) }
        } elseif ($line -match 'LogAutomationController: ClothSurfaceWeights part=') { $f = Read-Tokens $line; $run.surfaceWeights[('{0}:{1}' -f $f.part, [int]$f.stage)] = $f }
        elseif ($line -match 'LogAutomationController: ClothSurfaceProbe skipped:') { $run.skippedSurface += $line }
    }
    foreach ($group in @('Whole8', 'ShortPanel02_02', 'LongCloth7')) {
        if (!$run.shoulder.Contains($group) -or $run.shoulder[$group].samples -le 0) { $run.warnings += "Missing/empty shoulder group $group." }
    }
    return $run
}
function Numeric-Diff($Before, $After) {
    $rows = @()
    if ($null -eq $Before -or $null -eq $After) { return $rows }
    foreach ($key in $Before.Keys) {
        if (!$After.Contains($key) -or $Before[$key] -isnot [double] -or $After[$key] -isnot [double]) { continue }
        $base = [double]$Before[$key]; $next = [double]$After[$key]
        $percent = $null
        if ($base -ne 0) { $percent = 100.0 * ($next - $base) / [Math]::Abs($base) }
        $rows += [ordered]@{ field = $key; baseline = $base; candidate = $next; delta = $next - $base; changePercent = $percent }
    }
    return $rows
}
function Surface-Summary($Run) {
    $stages = @(); $complete = $true; $allOutside = $true
    foreach ($stage in @(3, 4, 5)) {
        $key = "Torso:$stage"; $probe = $Run.surface[$key]; $weights = $Run.surfaceWeights[$key]
        $valid = $null -ne $probe -and $probe.sampledVertices -gt 0 -and $probe.externalActors -eq 18 -and $probe.finite -eq 1
        $complete = $complete -and $valid
        $allOutside = $allOutside -and $valid -and $probe.insideVertices -eq 0
        $stages += [ordered]@{ stage = $stage; valid = $valid; probe = $probe; dominant = $weights }
    }
    return [ordered]@{ threeStagesComplete = $complete; allSampledTorsoVerticesOutside = $(if ($complete) { $allOutside } else { $null }); stages = $stages; caveat = 'Sampled linear LOD0 vertices against 18 anatomy collision proxies; not body triangle skin, all poses or continuous collision.' }
}
function Flatten-Json($Value, [string]$Prefix, [hashtable]$Flat) {
    if ($Value -is [pscustomobject]) {
        foreach ($property in $Value.PSObject.Properties) { Flatten-Json $property.Value $(if ($Prefix) { "$Prefix.$($property.Name)" } else { $property.Name }) $Flat }
    } elseif ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) { Flatten-Json $Value[$key] $(if ($Prefix) { "$Prefix.$key" } else { [string]$key }) $Flat }
    } elseif ($Value -is [array]) {
        for ($i = 0; $i -lt $Value.Count; ++$i) { Flatten-Json $Value[$i] "$Prefix[$i]" $Flat }
    } else { $Flat[$Prefix] = $Value }
}
function Semantic-Diff($Before, $After) {
    $left = @{}; $right = @{}; Flatten-Json $Before '' $left; Flatten-Json $After '' $right
    $rows = @()
    foreach ($key in (@($left.Keys) + @($right.Keys) | Sort-Object -Unique)) {
        if ($left.ContainsKey($key) -and $right.ContainsKey($key) -and $left[$key] -eq $right[$key]) { continue }
        $rows += [ordered]@{ path = $key; baseline = $left[$key]; candidate = $right[$key] }
    }
    return $rows
}
function Profile-Comparison([string]$BeforePath, [string]$AfterPath) {
    $report = [ordered]@{ available = $false; baselineFile = File-Evidence $BeforePath; candidateFile = File-Evidence $AfterPath; joints = @(); onlySlerpStiffnessChangedAcrossEightProfiles = $null }
    if ($null -eq $report.baselineFile -or $null -eq $report.candidateFile) { return $report }
    $base = Get-Content -LiteralPath $BeforePath -Encoding UTF8 -Raw | ConvertFrom-Json
    $candidate = Get-Content -LiteralPath $AfterPath -Encoding UTF8 -Raw | ConvertFrom-Json
    $report.available = $true; $report.baselineSuccess = $base.success; $report.candidateSuccess = $candidate.success
    $report.candidateApplyRequested = $candidate.apply_requested; $report.springScale = $candidate.spring_scale
    $onlyExpected = $base.success -eq $true -and $candidate.success -eq $true -and @($base.joints).Count -eq 8 -and @($candidate.joints).Count -eq 8
    foreach ($joint in $base.joints) {
        $matches = @($candidate.joints | Where-Object { $_.bone -ceq $joint.bone })
        if ($matches.Count -ne 1) { $onlyExpected = $false; $report.joints += [ordered]@{ bone = $joint.bone; error = 'Missing or duplicate candidate bone.' }; continue }
        $next = $matches[0]
        $diff = @(Semantic-Diff $joint.after_profile $next.after_profile)
        $savedDiff = @(Semantic-Diff $next.after_profile $next.saved_default_profile)
        $expectedOnly = $diff.Count -eq 1 -and $diff[0].path -match '^angularDrive\.slerpDrive\.stiffness$' -and $next.after_stiffness -eq $next.expected_adjusted_stiffness -and $joint.parent -ceq $next.parent -and $savedDiff.Count -eq 0 -and $next.full_constraint_matches_expected -eq $true
        $onlyExpected = $onlyExpected -and $expectedOnly
        $report.joints += [ordered]@{ bone = $joint.bone; parentUnchanged = $joint.parent -ceq $next.parent; expectedOnly = $expectedOnly; profileDiff = $diff; candidateSavedDefaultDiff = $savedDiff; nativeFullConstraintAssertionPassed = $next.full_constraint_matches_expected; baselineStiffness = $joint.after_stiffness; candidateStiffness = $next.after_stiffness; baselineDamping = $joint.damping; candidateDamping = $next.damping }
    }
    $report.onlySlerpStiffnessChangedAcrossEightProfiles = $onlyExpected
    $report.scope = 'Eight exported constraint profiles plus native full-constraint assertion; not a semantic audit of every PA body or other asset.'
    return $report
}
function Screenshot-Evidence([string[]]$Paths, [string]$Prefix) {
    if ($Paths.Count -eq 0) { $Paths = @(Get-ChildItem -LiteralPath $ShoulderReportDirectory -Filter "$Prefix*.png" -File | ForEach-Object { $_.FullName }) }
    $result = @()
    foreach ($path in $Paths) { $evidence = File-Evidence $path; if ($null -ne $evidence) { $result += $evidence } }
    return $result
}
$baseline = Read-Run $BaselineLog; $candidate = Read-Run $CandidateLog
$shoulderDiff = [ordered]@{}
foreach ($group in @('Whole8', 'ShortPanel02_02', 'LongCloth7')) { $shoulderDiff[$group] = @(Numeric-Diff $baseline.shoulder[$group] $candidate.shoulder[$group]) }
$torsoDiff = @(Numeric-Diff $baseline.clothMotion['Torso'] $candidate.clothMotion['Torso'])
$legDiff = @(Numeric-Diff $baseline.clothMotion['Leg'] $candidate.clothMotion['Leg'])
$hairDiff = @(Numeric-Diff $baseline.hairMotion $candidate.hairMotion)
$report = [ordered]@{
    generatedUtc = [DateTime]::UtcNow.ToString('o')
    scope = 'Offline last native PlayerParts PIE event block; no editor, input, camera or physics changes.'
    baseline = $baseline
    candidate = $candidate
    comparison = [ordered]@{
        shoulder = $shoulderDiff
        torso = $torsoDiff; leg = $legDiff; hair = $hairDiff
        hairLoggedNumericValuesExactlyEqual = $(if ($hairDiff.Count -gt 0) { @($hairDiff | Where-Object { $_.delta -ne 0 }).Count -eq 0 } else { $null })
        legLoggedNumericValuesExactlyEqual = $(if ($legDiff.Count -gt 0) { @($legDiff | Where-Object { $_.delta -ne 0 }).Count -eq 0 } else { $null })
        caveat = 'Relative percentages use logged rounded values; zero baseline yields null percent. Delta quaternion observations cover moving stages3/4, not static sag. No automatic tiny-flutter threshold or final approval. Exact metrics do not prove full asset invariance.'
    }
    torsoSurface = [ordered]@{ baseline = Surface-Summary $baseline; candidate = Surface-Summary $candidate }
    profileComparison = Profile-Comparison $BaselineProfile $CandidateProfile
    screenshots = [ordered]@{ baseline = @(Screenshot-Evidence $BaselineScreenshots 'Baseline'); candidate = @(Screenshot-Evidence $CandidateScreenshots 'Candidate'); visualReviewPerformedByScript = $false }
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($Output), ($report | ConvertTo-Json -Depth 40), [Text.UTF8Encoding]::new($false))
[pscustomobject]@{ report = [IO.Path]::GetFullPath($Output); baselineResult = $baseline.selectedResult; candidateResult = $candidate.selectedResult; baselineWarnings = $baseline.warnings.Count; candidateWarnings = $candidate.warnings.Count; profilesAvailable = $report.profileComparison.available } | ConvertTo-Json -Compress
