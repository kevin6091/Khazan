"""Prepare an exact Main CAS plan, preserving every unrelated current change."""
from pathlib import Path
import hashlib
import json
import shutil

MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'
OUT=MAIN/'Metadata/BeastDodge_20261012/Completion'
baseline=json.loads((MAIN/'Metadata/BeastDodge_20261012/Baseline.json').read_text())['baseline']
rebased=json.loads((MAIN/'Metadata/BeastDodge_20261012/Rebase03/Rebase.json').read_text())['expected_main']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
selected=[]
for root in ('Source','Config','Content/Monsters','Content/Data','Content/Bluprints'):
    for src in (WORK/root).rglob('*'):
        if not src.is_file():continue
        if root=='Source' and src.suffix not in ('.cpp','.h','.cs'):continue
        name=src.relative_to(WORK).as_posix()
        if root.startswith('Content/') and src.suffix not in ('.uasset','.umap'):continue
        expected=rebased.get(name,baseline.get(name))
        current=sha(MAIN/name);new=sha(src)
        if current==new:continue
        if current!=expected:raise RuntimeError('Main changed after rebase: '+name)
        if name.startswith('Source/') and '/Tests/' in name and name not in baseline:
            assert src.name in ('KZBeastDodgePIETest.cpp','KZBeastPatternPIETest.cpp','KZBeastRecoveryPIETest.cpp')
        if name.startswith('Config/'):raise RuntimeError('No config mutation is part of this task: '+name)
        selected.append({'path':name,'expected_main':current,'prepared_sha256':new,'bytes':src.stat().st_size})
        if current:
            backup=OUT/'MainBefore'/name;backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():shutil.copy2(MAIN/name,backup)
assert not (WORK/'Source/Khazan/Tests/KZBeastDodgeAuthor.cpp').exists()
assert 'StateTreeEditorModule' not in (WORK/'Source/Khazan/Khazan.Build.cs').read_text()
plan={'status':'prepared','main':str(MAIN),'work':str(WORK),'files':selected,'runtime_new_files':0,'new_development_test_files':3,'maps_written':0,'source_vfx_packages_written':0}
(OUT/'DeliveryPlan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'status':'prepared','files':len(selected),'source':sum(r['path'].startswith('Source/') for r in selected),'assets':sum(r['path'].startswith('Content/') for r in selected),'bytes':sum(r['bytes'] for r in selected)},indent=2),flush=True)
