"""Launch only task-owned hidden Unreal editors for slash review."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys
import time

main = Path(__file__).resolve().parents[2]
work = main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
project = main if os.environ.get('KZ_SLASH_PROJECT') == 'main' else work
out_root = main/'Metadata/PlayerSlashOuter_20261014'
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')

def run(name):
    out = out_root/name
    out.mkdir(parents=True, exist_ok=False)
    command = [str(engine), str(project/'Khazan.uproject'), '-unattended', '-nosplash',
               '-nosound', '-NoSourceControl', '-NoLiveCoding', '-NoAutoSave',
               '-EnablePlugins=GameFeatures',
               '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
               '-abslog='+str(out/'Editor.log'), '/Engine/Maps/Entry',
               '-RenderOffscreen', '-Windowed', '-ResX=1600', '-ResY=900',
               '-UseFixedTimeStep', '-FPS=60', '-d3d12',
               '-ExecCmds=py '+str(main/'Scripts/Engineering/player_slash_outer_driver_20261014.py')]
    env = dict(os.environ, KZ_SLASH_OUT=str(out), KZ_SLASH_PAIR_AUDIT='1' if project == work else '0',
               KZ_SLASH_INSPECT='1', KZ_SLASH_COMPOSED_ONLY='1',
               PYTHONUTF8='1', UE_SKIP_UBT_SDK_SETUP='1')
    start = time.monotonic()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    with (out/'stdout.txt').open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(command, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, startupinfo=startup,
                                   creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        (out/'Launch.json').write_text(json.dumps({
            'pid': process.pid, 'command': command,
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }, indent=2), encoding='utf-8')
        print('SLASH_OUTER_OWNED_EDITOR', process.pid, flush=True)
        code = process.wait()
    (out/'Exit.json').write_text(json.dumps({
        'pid': process.pid, 'exit': code, 'seconds': time.monotonic()-start,
    }, indent=2), encoding='utf-8')
    print('SLASH_OUTER_OWNED_EXIT', code, flush=True)
    return code

if __name__ == '__main__':
    sys.exit(run(sys.argv[1]))
