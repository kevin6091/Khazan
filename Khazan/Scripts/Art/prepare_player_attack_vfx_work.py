"""Private authoring tree. Shared Content junctions are read-only inputs."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
assert not WORK.exists(), WORK
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True)
for folder in ('Source', 'Config', 'Plugins', 'Binaries'):
    shutil.copytree(ROOT / folder, WORK / folder)
shutil.copy2(ROOT / 'Khazan.uproject', WORK / 'Khazan.uproject')
PRIVATE = ('_Art/Player/Animation/InGame/DAS',)

def junction(src, dst):
    # Both paths are resolved, exist within the explicit project roots, and
    # this invokes PowerShell end-to-end without shell-built command strings.
    quoted_src = str(src.resolve()).replace("'", "''")
    quoted_dst = str(dst.absolute()).replace("'", "''")
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "New-Item -ItemType Junction -Path '" + quoted_dst + "' -Target '" + quoted_src + "' | Out-Null"], check=True)

def content(src, dst, relative=''):
    dst.mkdir()
    for entry in src.iterdir():
        rel = (relative + '/' + entry.name).strip('/')
        target = dst / entry.name
        if not entry.is_dir():
            shutil.copy2(entry, target)
        elif rel in PRIVATE:
            shutil.copytree(entry, target)
        elif any(p.startswith(rel + '/') for p in PRIVATE):
            content(entry, target, rel)
        else:
            junction(entry, target)
content(ROOT / 'Content', WORK / 'Content')
manifest = {}
for base in ('Source', 'Config', 'Binaries'):
    for file in (ROOT / base).rglob('*'):
        if file.is_file():
            manifest[str(file.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(file.read_bytes()).hexdigest()
for file in (ROOT / 'Content/_Art/Player/Animation/InGame/DAS').rglob('*.uasset'):
    manifest[str(file.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(file.read_bytes()).hexdigest()
(OUT / 'WorkBaseline.json').write_text(json.dumps({'root': str(ROOT), 'work': str(WORK), 'private_content': PRIVATE,
    'sha256': manifest, 'shared_content': 'Read-only input junctions. Never save/delete any shared package.'}, indent=2), encoding='utf-8')
print(json.dumps({'work': str(WORK), 'baseline_files': len(manifest)}), flush=True)
