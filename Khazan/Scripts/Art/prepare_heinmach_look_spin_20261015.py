"""Snapshot current Main; only map and Spinning montage are writable candidates."""
from pathlib import Path
import hashlib,json,os,shutil
main=Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_HeinLookSpinWork_20261015'/'Khazan'
out=main/'Metadata/HeinMachLookSpin_20261015'
assert not work.exists(),work
out.mkdir(parents=True,exist_ok=True)
targets=['Content/Maps/L_HeinMach_Environment.umap',
 'Content/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack.uasset']
protected=['Content/Maps/DevMap.umap',
 'Content/_Art/Player/Animation/InGame/DAS/OverFury/AM_DAS_Player_OverFury.uasset',
 'Content/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongChargeAttack.uasset',
 'Content/VFX/01_ARPGEssentials/KZ_Slash.uasset']
catalog=json.loads((main/'Metadata/HeinMachColourVFX_20261015/NativeAllDev01/Probe.json').read_text())
for row in catalog['rows']:
    protected.append('Content/'+row['asset'].removeprefix('/Game/')+'.uasset')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
work.mkdir(parents=True)
shutil.copy2(main/'Khazan.uproject',work/'Khazan.uproject')
for name in ('Source','Config'):shutil.copytree(main/name,work/name,ignore=shutil.ignore_patterns('__pycache__'))
for name in ('Content','Plugins'):
    for base,dirs,files in os.walk(main/name):
        dirs[:]=[d for d in dirs if d not in ('Intermediate','Saved','DerivedDataCache')]
        dest=work/Path(base).relative_to(main);dest.mkdir(parents=True,exist_ok=True)
        for file in files:os.link(Path(base)/file,dest/file)
manifest=json.loads((main/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
binary=manifest['Modules']['Khazan'];dest=work/'Binaries/Win64';dest.mkdir(parents=True)
for name in ('UnrealEditor.modules',binary):shutil.copy2(main/'Binaries/Win64'/name,dest/name)
receipt=dict(main=str(main),work=str(work),targets={},protected={},binary=binary,binary_sha256=sha(dest/binary))
for rel in targets:
    source=main/rel;dest=work/rel;backup=out/'Before'/rel
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    dest.unlink();shutil.copy2(source,dest)
    assert not os.path.samefile(source,dest)
    receipt['targets'][rel]=sha(source)
for rel in sorted(set(protected)):receipt['protected'][rel]=sha(main/rel)
# Existing native regression uses this exact reference measurement.
rel='Metadata/CombatImpactUpgrade_20261012/WeaponSlashProbe04/WeaponProbe.json'
(work/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(main/rel,work/rel)
(out/'Preparation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('LOOK_SPIN_PREPARED',len(targets),'protected',len(receipt['protected']),flush=True)
