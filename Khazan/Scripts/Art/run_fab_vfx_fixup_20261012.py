"""Run Epic's redirector fixup only in the task-owned staging project."""
from pathlib import Path
import json
import os
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
number = len(list(META.glob('Fixup[0-9][0-9]'))) + 1
OUT = META / ('Fixup%02d' % number)
OUT.mkdir(parents=True, exist_ok=True)
assert STAGE.resolve().is_relative_to((ROOT / 'Saved/ArtStaging').resolve())
args = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe', str(STAGE / 'FabVFXComplete.uproject'), '-run=ResavePackages', '-fixupredirects', '-projectonly', '-unattended', '-NoSourceControl', '-NoAutoSave', '-NoLiveCoding', '-nosplash', '-nosound', '-NullRHI', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'Editor.log')]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
start = time.monotonic()
with (OUT / 'stdout.txt').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': args}, indent=2), encoding='utf-8')
    print('VFX_FIXUP_START ' + str(process.pid), flush=True)
    code = process.wait()
(OUT / 'Exit.json').write_text(json.dumps({'exit_code': code, 'elapsed_seconds': time.monotonic()-start}, indent=2), encoding='utf-8')
print('VFX_FIXUP_EXIT ' + str(code), flush=True)
raise SystemExit(code)
