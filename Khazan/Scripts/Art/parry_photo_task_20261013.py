"""Owned hidden Unreal process for scoped parry assets and native feedback QA."""
from pathlib import Path
import json, os, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[2]
label, mode, script = sys.argv[1:4]
OUT = ROOT / 'Metadata/ParryPhoto_20261013' / label
OUT.mkdir(parents=True, exist_ok=False)
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
render = mode == 'render'
cmd = [str(engine / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),
       str(ROOT / 'Khazan.uproject'), '-unattended', '-nosplash', '-nosound',
       '-NoSourceControl', '-NoAutoSave', '-NoLiveCoding', '-EnablePlugins=GameFeatures',
       '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT/'Editor.log')]
if render:
    cmd += ['/Engine/Maps/Entry', '-RenderOffscreen', '-Windowed', '-ForceRes',
            '-ResX=1600', '-ResY=900', '-d3d12', '-ExecCmds=py ' + str(ROOT/script)]
else:
    cmd += ['-NullRHI', '-run=pythonscript', '-script=' + str(ROOT/script)]
env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1', KZ_PARRY_PHOTO_OUT=str(OUT))
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
start = time.monotonic()
with (OUT/'stdout.txt').open('wb') as log:
    p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT,
                         startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT/'Launch.json').write_text(json.dumps({'pid':p.pid,'command':cmd},indent=2),encoding='utf-8')
    print('PARRY_PHOTO_PROCESS_START',p.pid,flush=True)
    code=p.wait()
(OUT/'Exit.json').write_text(json.dumps({'exit_code':code,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
print('PARRY_PHOTO_PROCESS_EXIT',code,flush=True)
raise SystemExit(code)
