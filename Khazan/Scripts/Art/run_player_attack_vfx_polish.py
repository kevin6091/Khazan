"""Task-owned hidden VFX polish processes; every invocation has distinct evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008'
mode, name = sys.argv[1:3]
assert mode in ('pie', 'script') and name.replace('_','').isalnum()
directory = OUT / 'Processes' / name
assert not directory.exists(), 'Preserve prior process evidence; use a distinct name'
directory.mkdir(parents=True)
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64')
project = MAIN if '--main' in sys.argv[3:] else WORK
args = [str(engine / ('UnrealEditor.exe' if mode == 'pie' else 'UnrealEditor-Cmd.exe')),
        str(project / 'Khazan.uproject')]
if mode == 'pie': args += ['/Game/Maps/DevMap', '-skipcompile', '-RenderOffscreen']
args += ['-unattended', '-nosound', '-nosplash', '-NoLiveCoding', '-NoSourceControl',
         '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter',
         '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController', '-abslog=' + str(directory / 'Editor.log')]
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
env['KZ_ATTACK_VFX_POLISH_OUTPUT'] = str(directory)
env['KZ_ATTACK_VFX_TRANSFORM_JSONL'] = str(directory / 'TransformObservations.jsonl')
if name.startswith('Direction'):
    env['KZ_ATTACK_VFX_POLISH_FOCUSED_DIRECTION'] = '1'
if name.startswith('BrutalReview'):
    env['KZ_ATTACK_VFX_POLISH_FOCUSED_BRUTAL'] = '1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
    folders = {'Source': 'Source', 'Config': 'Config', 'Effects': 'Content/_Art/Effects',
               'DAS': 'Content/_Art/Player/Animation/InGame/DAS'}
    result = {key: {p.relative_to(project).as_posix(): sha(p)
                   for p in (project / folder).rglob('*') if p.is_file()}
              for key, folder in folders.items()}
    result['uproject'] = {'Khazan.uproject': sha(project / 'Khazan.uproject')}
    binaries = project / 'Binaries/Win64'
    selected = json.loads((binaries / 'UnrealEditor.modules').read_text(encoding='utf-8'))['Modules']['Khazan']
    result['native'] = {'UnrealEditor-Khazan.dll': sha(binaries / selected),
                       'UnrealEditor-Khazan.pdb': sha(binaries / Path(selected).with_suffix('.pdb')),
                       'UnrealEditor.modules': sha(binaries / 'UnrealEditor.modules')}
    return result
before = snapshot()
if mode == 'pie':
    args += ['-ExecCmds=py ' + str(MAIN / 'Scripts/Art/player_attack_vfx_polish_pie.py')]
else:
    script = Path(sys.argv[3]).resolve()
    assert script.is_file()
    args += ['-RenderOffscreen' if '--rhi-script' in sys.argv[4:] else '-nullrhi',
             '-AllowCommandletRendering', '-run=pythonscript', '-script=' + str(script)]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
started = datetime.datetime.now(datetime.timezone.utc)
with (directory / 'stdout.txt').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, env=env,
        startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory / 'Launch.json').write_text(json.dumps(dict(utc=started.isoformat(),pid=process.pid,args=args),indent=2),encoding='utf-8')
    module_checked = False
    while True:
        try:
            code = process.wait(timeout=1)
            break
        except subprocess.TimeoutExpired:
            if not module_checked and (datetime.datetime.now(datetime.timezone.utc)-started).total_seconds() > 10:
                command = "(Get-Process -Id " + str(process.pid) + ").Modules | Where-Object { $_.ModuleName -like 'UnrealEditor-Khazan*' } | Select-Object ModuleName,FileName | ConvertTo-Json -Depth 3"
                probe = subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,
                    startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
                if probe.returncode == 0 and probe.stdout.strip():
                    modules = json.loads(probe.stdout)
                    if isinstance(modules,dict): modules = [modules]
                    for item in modules: item['sha256'] = sha(Path(item['FileName']))
                    (directory / 'ActualNativeModule.json').write_text(json.dumps(dict(pid=process.pid,modules=modules),indent=2),encoding='utf-8')
                    module_checked = True
duration = (datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()
(directory / 'Exit.json').write_text(json.dumps(dict(pid=process.pid,exit_code=code,elapsed_seconds=duration),indent=2),encoding='utf-8')
after = snapshot()
(directory / 'RuntimeIntegrity.json').write_text(json.dumps(dict(status='passed' if before == after else 'failed',
    pid=process.pid,before=before,after=after,package_saves=0,
    scope='Product files before and after the owned process; no external editor controls'),indent=2),encoding='utf-8')
print(json.dumps(dict(name=name,pid=process.pid,exit_code=code,elapsed_seconds=duration)),flush=True)
raise SystemExit(code)
