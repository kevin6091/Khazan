"""Hidden owned editor/commandlet runner with immutable launch/exit evidence."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN if '--main' in sys.argv else MAIN.parent.parent / 'Khazan_BeastDodgeWork_20261012/Khazan'
label, script = sys.argv[1:3]
OUT = MAIN / 'Metadata/BeastDodge_20261012' / label
OUT.mkdir(parents=True, exist_ok=False)
script = Path(script).resolve()
binary = 'UnrealEditor.exe' if '--pie' in sys.argv else 'UnrealEditor-Cmd.exe'
cmd = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/' + binary, str(WORK / 'Khazan.uproject'),
    '-unattended', '-nosplash', '-NoSourceControl', '-NoAutoSave', '-NoLiveCoding', '-EnablePlugins=GameFeatures',
    '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'Editor.log')]
if '--pie' in sys.argv:
    cmd += ['/Game/Maps/DevMap', '-RenderOffscreen', '-Windowed', '-ResX=1280', '-ResY=720', '-ForceRes', '-d3d12', '-ExecCmds=py ' + str(script)]
else:
    cmd += ['-NullRHI', '-run=pythonscript', '-script=' + str(script)]
env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1', KZ_BEAST_OUT=str(OUT))
if len(sys.argv) > 3:
    env['KZ_BEAST_TEST'] = next((v for v in sys.argv[3:] if not v.startswith('--')), 'Khazan.BeastDodge.DefensePIE')
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
started = time.monotonic()
with (OUT / 'stdout.txt').open('wb') as output:
    process = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'command': cmd, 'script': str(script)}, indent=2), encoding='utf-8')
    print('BEAST_EDITOR_START ' + str(process.pid), flush=True)
    code = process.wait()
(OUT / 'Exit.json').write_text(json.dumps({'exit_code': code, 'elapsed_seconds': time.monotonic()-started}, indent=2), encoding='utf-8')
print('BEAST_EDITOR_EXIT ' + str(code), flush=True)
raise SystemExit(code)
