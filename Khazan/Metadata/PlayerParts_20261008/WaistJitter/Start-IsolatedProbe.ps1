param([string]$Label = 'Baseline', [switch]$NoIronContact, [switch]$NullRHI, [switch]$NormalDelta)
$ErrorActionPreference = 'Stop'
if ($Label -notmatch '^[A-Za-z0-9]+$') { throw 'Invalid probe label' }
$work = 'C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan'
if (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -like '*Khazan_PlayerPartsWork_20261007*' }) { throw 'Own work editor is already running' }
$argsList = @(('"' + $work + '/Khazan.uproject"'), '/Game/Maps/DevMap', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=720', '-PlayerWaistJitterProbe', "-PlayerWaistProbeLabel=$Label", '-PlayerClothView', '-PlayerClothFrontView', '-EnablePlugins=GameFeatures', '-skipcompile', '-NoLiveCoding', '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-Unattended', '-NoSplash', '-NoSound', '-log=PlayerPartsWorkEditor.log')
if ($NullRHI) { $argsList += '-NullRHI' } else { $argsList += '-RenderOffscreen' }
if (!$NormalDelta) { $argsList += @('-UseFixedTimeStep', '-FPS=30') }
if ($NoIronContact) { $argsList += '-PlayerWaistDisableIronContact' }
$cap = if ($NormalDelta) { 60 } else { 30 }
$argsList += ('-ExecCmds="py ' + $work + '/Saved/player_parts_isolated_editor.py,t.MaxFPS ' + $cap + ',r.ScreenPercentage 100,r.MotionBlurQuality 0"')
$proc = Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
$proc.PriorityClass = 'BelowNormal'
@{ pid=$proc.Id; label=$Label; noIronContact=$NoIronContact.IsPresent; normalDelta=$NormalDelta.IsPresent; arguments=$argsList } | ConvertTo-Json -Depth 3
