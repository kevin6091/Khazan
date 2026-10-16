"""Launch an owned hidden editor process for the one-field asset change/audit."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
label, mode = sys.argv[1:3]
OUT = ROOT / 'Metadata/PlayerReceivedHitVFXRemoval_20261013' / label
OUT.mkdir(parents=True, exist_ok=False)
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
render = mode == 'rhi'
cmd = [str(engine / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')), str(ROOT / 'Khazan.uproject'),
       '-unattended', '-nosplash', '-nosound', '-NoSourceControl', '-NoLiveCoding',
       '-NoAutoSave', '-EnablePlugins=GameFeatures',
       '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
       '-abslog=' + str(OUT / 'Editor.log')]
if render:
    cmd += ['/Engine/Maps/Entry', '-RenderOffscreen', '-Windowed', '-ForceRes',
            '-ResX=1600', '-ResY=900', '-d3d12', '-UseFixedTimeStep', '-FPS=60',
            '-ExecCmds=py ' + str(ROOT / 'Scripts/Engineering/player_received_hit_vfx_validation_driver_20261013.py')]
else:
    cmd += ['-NullRHI', '-run=pythonscript',
            '-script=' + str(ROOT / 'Scripts/Engineering/remove_player_received_hit_vfx_20261013.py')]
env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1', KZ_RECEIVED_HIT_OUT=str(OUT), KZ_RECEIVED_HIT_MODE=mode)
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
start = time.monotonic()
with (OUT / 'stdout.txt').open('wb') as log:
    process = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT,
                               startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'command': cmd}, indent=2), encoding='utf-8')
    print('RECEIVED_HIT_PROCESS_START', process.pid, flush=True)
    code = process.wait()
(OUT / 'Exit.json').write_text(json.dumps({'exit_code': code, 'elapsed_seconds': time.monotonic()-start}, indent=2), encoding='utf-8')
print('RECEIVED_HIT_PROCESS_EXIT', code, flush=True)
raise SystemExit(code)
