"""Launch an isolated, hidden Unreal verification process with exit evidence."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
label, project_arg, script_arg = sys.argv[1:4]
project, script = Path(project_arg).resolve(), Path(script_arg).resolve()
assert project.is_file() and script.is_file()
out = META / label
out.mkdir(parents=True, exist_ok=True)
args = [str(ENGINE / 'UnrealEditor-Cmd.exe'), str(project), '-unattended', '-nosplash', '-nosound', '-NoSourceControl', '-NoLiveCoding', '-NoAutoSave', '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(out / 'Editor.log'), '-run=pythonscript', '-script=' + str(script)]
if project == ROOT / 'Khazan.uproject':
    args.append('-EnablePlugins=GameFeatures')
args.append('-AllowCommandletRendering' if '--rhi' in sys.argv else '-NullRHI')
args.extend(arg for arg in sys.argv[4:] if arg.startswith('-VFX'))
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
start = time.monotonic()
with (out / 'stdout.txt').open('w', encoding='utf-8') as output:
    process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (out / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': args, 'project': str(project), 'script': str(script), 'hidden_process': True}, indent=2) + '\n', encoding='utf-8')
    print('FAB_VFX_AUDIT_START ' + json.dumps({'pid': process.pid, 'label': label}), flush=True)
    code = process.wait()
receipt = {'exit_code': code, 'elapsed_seconds': round(time.monotonic() - start, 2), 'pid': process.pid, 'log': str(out / 'Editor.log')}
(out / 'Exit.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
if script.name == 'audit_fab_vfx_dependencies_20261012.py' and (META / 'StageDependencies.json').exists():
    (out / 'DependencyAudit.json').write_bytes((META / 'StageDependencies.json').read_bytes())
if script.name == 'audit_fab_vfx_load_20261012.py':
    artifact = META / ('MainLoad.json' if project == ROOT / 'Khazan.uproject' else 'StageLoad.json')
    if artifact.exists():
        (out / 'AssetLoadAudit.json').write_bytes(artifact.read_bytes())
if script.name == 'audit_fab_vfx_shaders_20261012.py' and (META / 'MainShaders.json').exists():
    (out / 'ShaderAudit.json').write_bytes((META / 'MainShaders.json').read_bytes())
if script.name in ('audit_fab_vfx_organized_20261012.py', 'audit_fab_vfx_wp_demo_20261012.py'):
    project_label = 'Main' if project == ROOT / 'Khazan.uproject' else 'Stage'
    completion = META / 'Completion'
    for suffix, destination in (('OrganizedAudit.json', 'OrganizedAudit.json'), ('WPDemoAudit.json', 'WPDemoAudit.json')):
        artifact = completion / (project_label + suffix)
        if artifact.exists():
            (out / destination).write_bytes(artifact.read_bytes())
print('FAB_VFX_AUDIT_EXIT ' + json.dumps(receipt), flush=True)
raise SystemExit(code)
