"""Task-owned hidden Unreal processes; never uses the user's Rider editor."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(os.environ.get('KZ_AUDIO_PROJECT_ROOT',str(ROOT)))
OUT = Path(os.environ.get('KZ_AUDIO_REPORT_ROOT',str(ROOT / 'Saved/ImportReports/GameplayAudio_20261011')))
OUT.mkdir(parents=True,exist_ok=True)
name, script = sys.argv[1:3]
directory = OUT / name
directory.mkdir(exist_ok=False)
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
pie = '--pie' in sys.argv
args = [str(engine / ('UnrealEditor.exe' if pie else 'UnrealEditor-Cmd.exe')),
        str(PROJECT / 'Khazan.uproject'), '-unattended', '-nosplash',
        '-NoLiveCoding', '-NoSourceControl', '-NoAutoSave',
        '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter',
        '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-abslog=' + str(directory / 'Editor.log')]
if '--audio' not in sys.argv:
    args += ['-nosound']
else:
    args += ['-AudioMixer']
if pie:
    args += ['/Game/Maps/DevMap', '-nullrhi' if '--nullrhi' in sys.argv else '-RenderOffscreen',
             '-ExecCmds=py ' + str(Path(script).resolve())]
else:
    args += ['-RenderOffscreen' if '--rhi' in sys.argv else '-nullrhi',
             '-AllowCommandletRendering', '-run=pythonscript',
             '-script=' + str(Path(script).resolve())]
env = dict(os.environ, KZ_AUDIO_OUTPUT=str(directory), KZ_AUDIO_MAIN=str(PROJECT))
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
start = datetime.datetime.now(datetime.timezone.utc)
with (directory / 'stdout.txt').open('w', encoding='utf-8') as stream:
    proc = subprocess.Popen(args, env=env, stdout=stream, stderr=subprocess.STDOUT,
                            startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'Launch.json').write_text(json.dumps({'pid': proc.pid, 'args': args,
        'utc': start.isoformat()}, indent=2), encoding='utf-8')
    code = proc.wait()
(directory / 'Exit.json').write_text(json.dumps({'pid': proc.pid, 'exit_code': code,
    'seconds': (datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()}, indent=2), encoding='utf-8')
print(json.dumps({'name': name, 'exit_code': code, 'pid': proc.pid}), flush=True)
raise SystemExit(code)
