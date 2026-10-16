"""Owned hidden UE process; immutable per-run evidence and no user-editor control."""
from pathlib import Path
import json, os, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[2]
label, script = sys.argv[1:3]
OUT = ROOT / 'Metadata/ParticleAlpha_20261013' / label
OUT.mkdir(parents=True, exist_ok=False)
project = Path(os.environ.get('KZ_ALPHA_PROJECT', str(ROOT))).resolve()
render = '--render' in sys.argv
game = '--game' in sys.argv
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
cmd = [str(engine / ('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),
       str(project / 'Khazan.uproject'), '-unattended', '-nosplash', '-nosound',
       '-NoSourceControl', '-NoAutoSave', '-NoLiveCoding', '-EnablePlugins=GameFeatures',
       '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'Editor.log')]
script = str((ROOT / script).resolve())
if render:
    cmd += [os.environ.get('KZ_ALPHA_MAP', '/Engine/Maps/Entry'), '-RenderOffscreen', '-Windowed',
            '-ResX=1280', '-ResY=720', '-ForceRes', '-d3d12', '-ExecCmds=py ' + script]
    if game: cmd += ['-game', '-EnablePlugins=GameFeatures,PythonScriptPlugin']
else:
    cmd += ['-NullRHI', '-run=pythonscript', '-script=' + script]
env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1', KZ_ALPHA_MAIN=str(ROOT), KZ_ALPHA_OUT=str(OUT))
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
start = time.monotonic()
with (OUT / 'stdout.txt').open('wb') as output:
    p = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT, startupinfo=startup,
                         creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': p.pid, 'project': str(project), 'command': cmd}, indent=2), encoding='utf-8')
    print('ALPHA_PROCESS_START', p.pid, flush=True)
    code = p.wait()
(OUT / 'Exit.json').write_text(json.dumps({'exit_code': code, 'elapsed_seconds': time.monotonic()-start}, indent=2), encoding='utf-8')
print('ALPHA_PROCESS_EXIT', code, flush=True)
raise SystemExit(code)
