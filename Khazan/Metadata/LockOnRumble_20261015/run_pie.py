"""Run only this task's hidden editor and existing native regression suites."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else 'PIE01')
OUT.mkdir(exist_ok=False)
TESTS = sys.argv[2] if len(sys.argv) > 2 else 'Khazan.CombatUI.PIE,Khazan.GiantFall.PIE'
env = os.environ.copy()
env.update(KZ_MONSTER_PHYSICS_OUT=str(OUT), KZ_MONSTER_PHYSICS_TESTS=TESTS,
           KZ_COMBAT_UI_OUTPUT=str(OUT), KZ_GIANT_FALL_OUTPUT=str(OUT))
exe = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
driver = ROOT / 'Scripts/Engineering/combat_feel_validation_driver_20261015.py'
args = [str(exe), str(ROOT / 'Khazan.uproject'), '/Engine/Maps/Entry',
        '-unattended', '-nosplash', '-nosound', '-NoSourceControl', '-NoLiveCoding', '-NoAutoSave',
        '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
        '-RenderOffscreen', '-Windowed', '-ResX=1600', '-ResY=900', '-ForceRes', '-d3d12',
        '-abslog=' + str(OUT / 'Editor.log'), '-ExecCmds=py ' + str(driver)]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
begin = time.monotonic()
with (OUT / 'Process.log').open('wb') as stream:
    proc = subprocess.Popen(args, env=env, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                            startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / 'Launch.json').write_text(json.dumps(dict(pid=proc.pid, args=args,
        tests=TESTS, utc=datetime.datetime.now(datetime.timezone.utc).isoformat()), indent=2), encoding='utf-8')
    print('Task editor PID', proc.pid, flush=True)
    code = proc.wait()
(OUT / 'Exit.json').write_text(json.dumps(dict(exit_code=code,
    seconds=time.monotonic() - begin), indent=2), encoding='utf-8')
print('Task editor exit', code, flush=True)
raise SystemExit(code)
