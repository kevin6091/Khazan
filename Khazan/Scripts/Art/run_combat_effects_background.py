"""Run a task-owned Art stage in a hidden process; never control the user's editor."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
stage = sys.argv[1]
script = ROOT / 'Scripts/Art' / ('combat_effects_' + stage + '.py')
assert script.is_file(), script
outdir = ROOT / 'Saved/ImportReports/CombatEffects_20261006'
outdir.mkdir(parents=True, exist_ok=True)
phase = sys.argv[sys.argv.index('--phase') + 1] if '--phase' in sys.argv else None
label = stage + ('_' + phase if phase else '')
log = outdir / (label + '.log')
render = '--render' in sys.argv
args = [str(ENGINE / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),
        str(ROOT / 'Khazan.uproject'), '-unattended', '-nosound', '-nosplash',
        '-NoSourceControl', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter', '-abslog=' + str(log)]
args += ['-ini:Editor:[TextureImporter]:LoadHdrAsLongLatCubemap=' + ('1' if phase == 'cube' else '0')]
if '--phase' in sys.argv:
    args += ['-KZFXPhase=' + sys.argv[sys.argv.index('--phase') + 1]]
if render:
    args += ['-RenderOffscreen', '-windowed', '-ResX=1280', '-ResY=720',
             '-ExecCmds=py ' + str(script)]
else:
    args += ['-nullrhi', '-run=pythonscript', '-script=' + str(script)]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
start = time.monotonic()
env = dict(os.environ)
# Art imports need no platform SDK discovery; avoid another session's Build.bat lock.
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
with log.with_suffix('.stdout.txt').open('w', encoding='utf-8') as output:
    completed = subprocess.run(args, stdout=output, stderr=subprocess.STDOUT,
                               startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
report = {'stage': stage, 'exit_code': completed.returncode,
          'elapsed_seconds': round(time.monotonic() - start, 2), 'log': str(log),
          'hidden_process': True, 'user_editor_untouched': True}
(outdir / (label + '_process.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)
raise SystemExit(completed.returncode)
