"""Build the owned project once with an immutable input receipt."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN if '--main' in sys.argv else MAIN.parent.parent / 'Khazan_BeastDodgeWork_20261012/Khazan'
label, suffix = sys.argv[1:3]
OUT = MAIN / 'Metadata/BeastDodge_20261012' / label
OUT.mkdir(parents=True, exist_ok=False)


def inputs():
    return {p.relative_to(WORK).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (WORK / 'Source').rglob('*') if p.is_file() and p.suffix in ('.cpp', '.h', '.cs')}


before = inputs()
cmd = ['C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat', 'KhazanEditor', 'Win64', 'Development', str(WORK / 'Khazan.uproject'), '-WaitMutex', '-NoHotReload', '-NoHotReloadFromIDE', '-MaxParallelActions=1', '-NoXGE', '-NoUBA']
if suffix != 'stock': cmd += ['-ModuleWithSuffix=Khazan,' + suffix]
cmd += [value for value in sys.argv[3:] if value != '--main']
(OUT / 'Input.json').write_text(json.dumps({'command': cmd, 'source_sha256': before}, indent=2), encoding='utf-8')
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
started = time.monotonic()
env = dict(os.environ, UE_SKIP_UBT_SDK_SETUP='1')
with (OUT / 'Build.log').open('wb') as stream:
    process = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW, env=env)
    (OUT / 'Launch.json').write_text(json.dumps({'pid': process.pid, 'command': cmd}, indent=2), encoding='utf-8')
    print('BEAST_DODGE_BUILD_START ' + str(process.pid), flush=True)
    code = process.wait()
binary = WORK / 'Binaries/Win64' / ('UnrealEditor-Khazan.dll' if suffix == 'stock' else 'UnrealEditor-Khazan-' + suffix + '.dll')
receipt = {'exit_code': code, 'elapsed_seconds': time.monotonic() - started, 'input_unchanged': before == inputs(), 'module': str(binary), 'module_sha256': hashlib.sha256(binary.read_bytes()).hexdigest() if binary.exists() else None}
(OUT / 'Exit.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt), flush=True)
raise SystemExit(code)
