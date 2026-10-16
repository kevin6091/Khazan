"""Task-owned hidden process; never attaches to or controls another editor."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/CombatUI_20261011' / sys.argv[1]
OUT.mkdir(parents=True, exist_ok=False)
entry = str((ROOT / sys.argv[2]).resolve())
mode = sys.argv[3] if len(sys.argv) > 3 else 'commandlet'
project = Path(os.environ.get('KZ_COMBAT_UI_PROJECT', str(ROOT / 'Khazan.uproject'))).resolve()
assert project.is_file() and project.suffix == '.uproject'
cmd = ['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' if mode == 'commandlet' else
       'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe', str(project),
       '-unattended', '-nosplash', '-nosound', '-NoSourceControl', '-NoLiveCoding', '-NoAutoSave',
       '-EnablePlugins=GameFeatures', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(OUT / 'Editor.log')]
if mode == 'commandlet': cmd += ['-NullRHI', '-run=pythonscript', '-script=' + entry]
else:
    cmd += ['/Engine/Maps/Entry' if mode in ['asset_editor', 'asset_rhi'] else '/Game/Maps/DevMap', '-RenderOffscreen', '-Windowed', '-ResX=1600', '-ResY=900', '-ForceRes', '-ExecCmds=py ' + entry]
    if mode == 'asset_editor': cmd += ['-NullRHI']
env = dict(os.environ, KZ_COMBAT_UI_OUTPUT=str(OUT), KZ_COMBAT_UI_EDITOR_MODE=mode, PYTHONUTF8='1', UE_SKIP_UBT_SDK_SETUP='1')
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
start = time.monotonic(); process = subprocess.Popen(cmd, env=env, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
(OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'command': cmd, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2), encoding='utf-8')
print('OWNED_UI_EDITOR', process.pid, flush=True)
try: result = process.wait(timeout=900)
except subprocess.TimeoutExpired:
    process.terminate(); result = process.wait(timeout=30)
    print('OWNED_UI_WATCHDOG_TERMINATED', flush=True)
(OUT / 'Exit.json').write_text(json.dumps({'pid': process.pid, 'exit': result, 'seconds': time.monotonic() - start}, indent=2), encoding='utf-8')
print('OWNED_UI_EXIT', result, flush=True)
sys.exit(result)
