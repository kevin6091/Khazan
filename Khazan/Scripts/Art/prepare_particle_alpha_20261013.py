"""Thin isolated project; material folders are owned copies, other data read only."""
from pathlib import Path
import hashlib, json, shutil, subprocess
MAIN = Path(__file__).resolve().parents[2]
ROOT = MAIN / 'Metadata/ParticleAlpha_20261013'
WORK = MAIN.parent.parent / 'Khazan_ParticleAlphaWork_20261013/Khazan'
assert not WORK.exists(), 'Do not overwrite an existing work project'
audit = json.loads((ROOT / 'Audit02/Audit.json').read_text(encoding='utf-8'))
targets = [r['path'] for r in audit['materials'] if r['class'] == 'Material']
targets.append('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NET_HM_WeatherBudget')
relatives = ['Content/' + p.removeprefix('/Game/') + '.uasset' for p in targets]
branch = set()
for r in relatives:
    p = Path(r).parent
    while p.as_posix() != '.': branch.add(p.as_posix()); p = p.parent
WORK.mkdir(parents=True)
report = {'work': str(WORK), 'main': str(MAIN), 'targets': [], 'copied_bytes': 0, 'junctions': [], 'source_or_config_changes': False}

def junction(source, target):
    # Exact verified directories; no deletion or moving and no shell expansion.
    assert source.is_dir() and source.resolve().is_relative_to(MAIN.resolve())
    assert target.parent.resolve().is_relative_to(WORK.resolve())
    result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(target), str(source)], capture_output=True)
    assert result.returncode == 0, result.stderr
    report['junctions'].append(str(target.relative_to(WORK)))

def mirror(source, target):
    relative = source.relative_to(MAIN).as_posix()
    if source.is_dir() and relative not in branch:
        junction(source, target); return
    if source.is_dir():
        target.mkdir()
        for child in source.iterdir(): mirror(child, target / child.name)
    else:
        shutil.copy2(source, target); report['copied_bytes'] += source.stat().st_size

shutil.copy2(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
shutil.copytree(MAIN / 'Config', WORK / 'Config')
shutil.copytree(MAIN / 'Binaries', WORK / 'Binaries')
for name in ('Plugins', 'Source', 'Scripts'): junction(MAIN / name, WORK / name)
mirror(MAIN / 'Content', WORK / 'Content')
for r in relatives:
    source, dest = MAIN / r, WORK / r
    assert dest.resolve().is_relative_to(WORK.resolve()), r
    h = hashlib.sha256(source.read_bytes()).hexdigest()
    assert h == hashlib.sha256(dest.read_bytes()).hexdigest()
    backup = ROOT / 'Before' / r; backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, backup)
    report['targets'].append({'path': r, 'before_sha256': h})
report['main_map_sha256'] = hashlib.sha256((MAIN / 'Content/Maps/L_HeinMach_Environment.umap').read_bytes()).hexdigest()
report['main_snow_system_sha256'] = audit['snow']['sha256']
(ROOT / 'Preparation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'work': str(WORK), 'owned_targets': len(relatives), 'copied_bytes': report['copied_bytes'], 'junctions': len(report['junctions'])}))
