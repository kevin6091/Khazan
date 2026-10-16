"""Launch only task-owned hidden processes, without controlling another editor."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
script = Path(sys.argv[1]).resolve()
project = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / 'Khazan.uproject'
assert script.is_file() and project.is_file()
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008/Processes'
OUT.mkdir(parents=True, exist_ok=True)
log = OUT / (script.stem + '.log')
args = [str(ENGINE / 'UnrealEditor-Cmd.exe'), str(project), '-unattended', '-nosound', '-nosplash',
        '-NoLiveCoding', '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter', '-nullrhi',
        '-abslog=' + str(log), '-run=pythonscript', '-script=' + str(script)]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
started = time.monotonic()
with log.with_suffix('.stdout.txt').open('w', encoding='utf-8') as out:
    process = subprocess.Popen(args, stdout=out, stderr=subprocess.STDOUT, startupinfo=startup,
                               creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / (script.stem + '_launch.json')).write_text(json.dumps({'pid': process.pid, 'args': args}, indent=2), encoding='utf-8')
    rc = process.wait()
result = {'exit_code': rc, 'pid': process.pid, 'elapsed_seconds': time.monotonic() - started, 'log': str(log)}
(OUT / (script.stem + '_exit.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
raise SystemExit(rc)
