"""Run isolated Art authoring/verification without connecting to the user's Rider."""
from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')


def main():
    stage = sys.argv[1]
    render = '--render' in sys.argv
    game = '--game' in sys.argv
    script = ROOT / 'Scripts/Art' / ('heinmach_weather_' + stage + '.py')
    assert script.is_file(), script
    log = ROOT / 'Saved/Logs' / ('HeinMachWeather_' + stage + '_20261006.log')
    args = [str(ENGINE / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),
            str(ROOT / 'Khazan.uproject'), '-unattended', '-nosound', '-nosplash',
            '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol',
            '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter', '-abslog=' + str(log)]
    if render:
        args += ['/Game/Maps/L_HeinMach_Environment', '-RenderOffscreen',
                 '-windowed', '-ResX=1280', '-ResY=720', '-ExecCmds=py ' + str(script)]
        if game:args += ['-game','-EnablePlugins=GameFeatures,PythonScriptPlugin']
    else:
        args += ['-nullrhi', '-run=pythonscript', '-script=' + str(script)]
    if '--material-only' in sys.argv:args += ['-HMWeatherMaterialOnly']
    if '--refine' in sys.argv:args += ['-HMWeatherRefine']
    if '--saved' in sys.argv:args += ['-HMRefinementSavedOnly']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    start = time.monotonic()
    with log.with_suffix('.stdout.txt').open('w', encoding='utf-8') as out:
        result = subprocess.run(args, stdout=out, stderr=subprocess.STDOUT,
                                startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    markers={'look':['KZ_HEINMACH_LOOK_APPLIED','KZ_HEINMACH_EXPOSURE_CONTRACT_FIXED','KZ_HEINMACH_REALISM_REFINED'],
             'snow':['KZ_HEINMACH_SNOW_APPLIED','KZ_HEINMACH_SNOW_MATERIAL_UPDATED'],
             'qa_materials':['KZ_HEINMACH_QA_MATERIALS_READY'],
             'render_probe':['KZ_HEINMACH_RENDER_GRAPHS_VERIFIED'],
             'audit':['KZ_HEINMACH_FRESH_AUDIT_PASSED'],
             'cleanup':['KZ_HEINMACH_UNUSED_TRIALS_CLEANED'],
             'refine_capture':['KZ_HEINMACH_REALISM_CAPTURED'],
             'niagara_probe':['KZ_NIAGARA_INPUTS_PROBED']}
    verified=result.returncode==0
    if verified and stage in markers:
        verified=any(marker in log.read_text(encoding='utf-8',errors='replace') for marker in markers[stage])
    exit_code=result.returncode if result.returncode else (0 if verified else 1)
    report = {'stage': stage, 'exit_code': exit_code,'unreal_process_exit_code':result.returncode,'stage_marker_verified':verified,
              'elapsed_seconds': round(time.monotonic() - start, 2), 'log': str(log),
              'isolated_background_process': True, 'RiderLink_disabled': True}
    target = ROOT / 'Saved/ImportReports' / ('HeinMachWeather_Process_' + stage + '_20261006.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
