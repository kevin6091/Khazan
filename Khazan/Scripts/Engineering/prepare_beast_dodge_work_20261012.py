"""Create an isolated source/config project with owned gameplay asset roots."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_BeastDodgeWork_20261012/Khazan'
OUT = MAIN / 'Metadata/BeastDodge_20261012'
assert not (OUT / 'Baseline.json').exists(), 'Use the saved work receipt instead of staging twice'
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def junction(path, target):
    assert not path.exists() and path.resolve().is_relative_to(WORK.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    # Fixed native PowerShell arguments; no shell-built deletion or moving.
    env = dict(os.environ, KZ_STAGE_JUNCTION_PATH=str(path), KZ_STAGE_JUNCTION_TARGET=str(target))
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        'New-Item -ItemType Junction -Path $env:KZ_STAGE_JUNCTION_PATH -Target $env:KZ_STAGE_JUNCTION_TARGET | Out-Null'],
        capture_output=True, text=True, env=env)
    assert result.returncode == 0 and path.is_dir(), result.stderr


baseline = {}
for folder in ('Source', 'Config'):
    shutil.copytree(MAIN / folder, WORK / folder, dirs_exist_ok=True)
    shutil.copytree(MAIN / folder, OUT / 'Before' / folder, dirs_exist_ok=True)
    for file in (MAIN / folder).rglob('*'):
        if file.is_file():
            baseline[file.relative_to(MAIN).as_posix()] = sha(file)
shutil.copy2(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
baseline['Khazan.uproject'] = sha(MAIN / 'Khazan.uproject')
junction(WORK / 'Plugins', MAIN / 'Plugins')
(WORK / 'Content').mkdir()
owned = ('Monsters', 'Data', 'Bluprints')
copied_bytes = 0
for folder in (MAIN / 'Content').iterdir():
    if not folder.is_dir():
        continue
    target = WORK / 'Content' / folder.name
    if folder.name in owned:
        shutil.copytree(folder, target)
        for file in folder.rglob('*'):
            if file.is_file():
                baseline[file.relative_to(MAIN).as_posix()] = sha(file)
                copied_bytes += file.stat().st_size
    else:
        junction(target, folder)
manifest = json.loads((MAIN / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
binary = MAIN / 'Binaries/Win64' / manifest['Modules']['Khazan']
(WORK / 'Binaries/Win64').mkdir(parents=True)
alias = 'UnrealEditor-KhazanBeastDodgeBaseline20261012.dll'
shutil.copy2(binary, WORK / 'Binaries/Win64' / alias)
manifest['Modules']['Khazan'] = alias
(WORK / 'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(WORK / 'Metadata/BeastDodge_20261012').mkdir(parents=True)
receipt = {'status': 'staged', 'utc': datetime.now(timezone.utc).isoformat(), 'main': str(MAIN), 'work': str(WORK), 'owned_content_roots': list(owned), 'borrowed_content_read_only': True, 'copied_asset_bytes': copied_bytes, 'baseline': baseline, 'baseline_module': str(binary), 'baseline_module_sha256': sha(binary)}
(OUT / 'Baseline.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
(OUT / 'ResumeState.json').write_text(json.dumps({'status': 'in_progress', 'work': str(WORK), 'remaining': ['Source StateTree mapping, player recovery, dodge immunity and feedback', 'Author owned data and compile', 'Native precise branch/timing/cleanup tests and rendered feedback review', 'Main CAS publication and fresh validation', 'Final domain records']}, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in receipt.items() if k != 'baseline'}), flush=True)
