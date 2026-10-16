"""Read saved libraries before any UE rename; old/source identities remain immutable."""
from pathlib import Path
import csv
import hashlib
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/EnemyAnimationOrganization_20261007'
OUT.mkdir(parents=True, exist_ok=True)
FAMILIES = ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']
TARGETS = {f: f'/Game/_Art/Enemies/HeinMach/Humanoids/{f}/Animations' for f in FAMILIES}
TARGETS.update(Yetuga='/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations',
               ApesStoneHandElite='/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations')
LIBRARIES = [
    ROOT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationStructure_20260909/AnimationLibrary.csv',
    ROOT / 'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/AnimationLibrary.csv',
    ROOT / 'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/AnimationLibrary.csv',
]
records = {}
for library in LIBRARIES:
    for row in csv.DictReader(library.open(encoding='utf-8-sig')):
        asset = row.get('PlaybackAsset', row.get('Destination'))
        family = next((f for f, prefix in TARGETS.items() if asset.startswith(prefix + '/')), None)
        if not family:
            continue
        file = ROOT / ('Content/' + asset.removeprefix('/Game/') + '.uasset')
        if not file.is_file():
            raise RuntimeError(f'Saved current library path missing: {asset}')
        records[asset] = dict(family=family, scope='ArtLibrary', old=asset,
                              original_package=row.get('OriginalPackage', row.get('SourcePackage')),
                              derivation=row.get('Derivation', row.get('PlaybackDerivation')),
                              library=str(library.relative_to(ROOT)).replace('\\', '/'),
                              file=str(file.relative_to(ROOT)).replace('\\', '/'),
                              sha256=hashlib.sha256(file.read_bytes()).hexdigest())
for family in FAMILIES:
    folder = ROOT / f'Content/Monsters/{family}/Animations/InGame'
    for file in sorted(folder.glob('A_EN_PLAY_*.uasset')):
        old = '/Game/' + str(file.relative_to(ROOT / 'Content').with_suffix('')).replace('\\', '/')
        source = next((r for r in records.values() if r['family'] == family and Path(r['old']).name == file.stem), None)
        assert source, file
        records[old] = dict(source, scope='Gameplay', old=old,
                            file=str(file.relative_to(ROOT)).replace('\\', '/'),
                            sha256=hashlib.sha256(file.read_bytes()).hexdigest())
archive = ROOT / 'Content/_Art/Enemies/HeinMach/Humanoids/Archer'
archer = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in archive.rglob('*.uasset')}
skills = {}
empire = ROOT / 'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire'
for family, directory in zip(FAMILIES, ['EmpireSword', 'Empire_SwordShield', 'Empire_SwordHArmor', 'EmpireHalberd_E']):
    skills[family] = [str(p.relative_to(ROOT)).replace('\\', '/') for p in sorted((empire / directory).rglob('SB_*.json'))]
result = dict(status='InventoryOnly', targets=TARGETS, rows=list(records.values()), archer_protected=archer,
              skill_sources=skills, source_libraries=[str(p.relative_to(ROOT)).replace('\\', '/') for p in LIBRARIES])
(OUT / 'Inventory.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
(OUT / 'Names.txt').write_text('\n'.join(f"{r['family']}\t{r['scope']}\t{Path(r['old']).name}" for r in records.values()), encoding='utf-8')
print(json.dumps({'assets':len(records), 'families':dict(Counter((r['family'],r['scope']) for r in records.values()).most_common()) if False else dict(Counter(r['family'] + '/' + r['scope'] for r in records.values())),
                  'skill_sources':{f:[Path(p).stem for p in ps] for f,ps in skills.items()}}, indent=2))
