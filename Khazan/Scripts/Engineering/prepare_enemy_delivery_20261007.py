"""Produce a scoped, hash guarded delivery manifest; no Main mutation."""
from pathlib import Path
import hashlib, json
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
OUT=MAIN/'Metadata/EnemyAnimationOrganization_20261007'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={r['path']:r['sha256'] for r in json.loads((OUT/'BeforeManifest.json').read_text())['files']}
seq=json.loads((OUT/'RenamePlan.json').read_text(encoding='utf-8'))['rows']
montage=json.loads((OUT/'MontageRenameApplied.json').read_text())
def file(asset):return 'Content/'+asset.removeprefix('/Game/')+'.uasset'
deleted={file(r['old']) for r in seq+montage}
changed={file(r['new']) for r in seq+montage}
for relative,original in before.items():
    if not relative.startswith('Content/'):continue
    if relative in deleted:
        assert not (WORK/relative).exists(),relative
    elif not (WORK/relative).exists():raise RuntimeError('Unplanned missing package '+relative)
    elif sha(WORK/relative)!=original:changed.add(relative)
for p in json.loads((OUT/'AttackExpansionPlan.json').read_text(encoding='utf-8')):
    base='/Game/Monsters/'+p['family']
    changed.update(file(a) for a in [base+'/Animations/Attack/Montages/Attack_'+p['id'],base+'/Data/DA_Combo_'+p['id'],base+'/Abilities/GA_'+p['id']])
    changed.update(file(s['game_destination']) for s in p['steps'])
changed.update(['Source/Khazan/Character/KZMonster.h','Source/Khazan/AI/KZMonsterStateTreeNodes.cpp','Source/Khazan/Tests/KZMonsterAIPIETest.cpp'])
rows=[]
for relative in sorted(changed):
    assert (WORK/relative).is_file(),relative
    assert relative not in deleted,relative
    expected=before.get(relative)
    if expected:assert sha(MAIN/relative)==expected,'Concurrent edit '+relative
    else:assert not (MAIN/relative).exists(),'Existing destination '+relative
    rows.append(dict(path=relative,before_sha256=expected,prepared_sha256=sha(WORK/relative)))
for relative in sorted(deleted):assert sha(MAIN/relative)==before[relative],relative
report=dict(status='PreparedPendingFinalPIE',files=rows,deleted=[dict(path=p,before_sha256=before[p]) for p in sorted(deleted)],runtime_files_added=0)
(OUT/'PreparedDeliveryManifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(prepared_files=len(rows),old_packages=len(deleted),existing=sum(r['before_sha256'] is not None for r in rows))))
