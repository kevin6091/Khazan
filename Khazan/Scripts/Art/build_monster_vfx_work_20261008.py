"""Compile the isolated Monster VFX candidate; no Main editor or product writes."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

MAIN = Path(__file__).resolve().parents[2]
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/Build'
OUT.mkdir(parents=True, exist_ok=True)
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
ARGS = [str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),
        str(ENGINE / 'Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'),
        'KhazanEditor', 'Win64', 'Development', '-Project=' + str(WORK / 'Khazan.uproject'),
        '-WaitMutex', '-NoHotReloadFromIDE', '-NoXGE', '-NoUBA', '-MaxParallelActions=2']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def inputs(root):
    rows = {p.relative_to(root).as_posix(): sha(p)
            for folder in ('Source', 'Config') for p in (root / folder).rglob('*') if p.is_file()}
    rows['Khazan.uproject'] = sha(root / 'Khazan.uproject')
    return rows

attempt = 1
while (OUT / ('Attempt' + str(attempt))).exists():
    attempt += 1
OUT = OUT / ('Attempt' + str(attempt))
OUT.mkdir()
before = inputs(WORK)
main_before = inputs(MAIN)
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
env = dict(os.environ)
env['UE_SKIP_UBT_SDK_SETUP'] = '1'
start = time.monotonic()
with (OUT / 'PrivateBuild.log').open('w', encoding='utf-8') as stream:
    process = subprocess.Popen(ARGS, stdout=stream, stderr=subprocess.STDOUT, env=env,
        startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'args': ARGS,
        'private_inputs': before, 'main_inputs': main_before}, indent=2), encoding='utf-8')
    code = process.wait()
report = {'exit_code': code, 'pid': process.pid, 'elapsed_seconds': time.monotonic()-start,
    'private_inputs_unchanged': inputs(WORK) == before,
    'main_inputs_unchanged': inputs(MAIN) == main_before,
    'private_inputs': before, 'main_inputs': main_before,
    'native': {name: sha(WORK / 'Binaries/Win64' / name) for name in
        ('UnrealEditor-Khazan.dll', 'UnrealEditor-Khazan.pdb', 'UnrealEditor.modules')}}
(OUT / 'Exit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(OUT.parent / 'Latest.json').write_text(json.dumps({'attempt': str(OUT), 'exit_code': code}, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ('exit_code', 'elapsed_seconds', 'private_inputs_unchanged', 'main_inputs_unchanged')}), flush=True)
raise SystemExit(code)
