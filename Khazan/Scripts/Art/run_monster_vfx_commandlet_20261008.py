"""Run an explicitly selected task script in an isolated, hidden commandlet."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

MAIN = Path(__file__).resolve().parents[2]
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
script = Path(sys.argv[1]).resolve()
assert script.is_file() and script.is_relative_to((MAIN / 'Scripts').resolve())
verify_main = '--main' in sys.argv[2:]
real_rhi = '--rhi' in sys.argv[2:]
project = MAIN if verify_main else WORK
assert (project / 'Khazan.uproject').is_file()
parent = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/Processes' / (('Main_' if verify_main else 'Private_') + script.stem)
parent.mkdir(parents=True, exist_ok=True)
attempt = 1
while (parent / ('Attempt' + str(attempt))).exists():
    attempt += 1
out = parent / ('Attempt' + str(attempt))
out.mkdir()
args = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
    str(project / 'Khazan.uproject'), '-unattended', '-nosound', '-nosplash', '-NoLiveCoding',
    '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
    '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter',
    *(['-AllowCommandletRendering', '-RenderOffscreen'] if real_rhi else ['-nullrhi']),
    '-abslog=' + str(out / 'Commandlet.log'), '-run=pythonscript', '-script=' + str(script)]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
env['KZ_MONSTER_VFX_VERIFY_MAIN'] = '1' if verify_main else '0'
start = time.monotonic()
with (out / 'Commandlet.stdout.txt').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, env=env,
        startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    (out / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': args,
        'rhi_mode': 'real' if real_rhi else 'null'}, indent=2), encoding='utf-8')
    code = process.wait()
result = {'exit_code': code, 'pid': process.pid, 'elapsed_seconds': time.monotonic()-start}
(out / 'Exit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(parent / 'Latest.json').write_text(json.dumps({'attempt': str(out), 'exit_code': code}, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
raise SystemExit(code)
