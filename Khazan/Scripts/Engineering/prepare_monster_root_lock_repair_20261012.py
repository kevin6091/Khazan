"""Freeze current imported root/reference values and exact private backups."""
from pathlib import Path
import json,math,hashlib,shutil
MAIN=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=MAIN/'Metadata/MonsterRootCollisionRepair_20261012'
assert not (OUT/'RootLockPlan.json').exists()
audit=json.loads((OUT/'MainUsageAudit02/RootAudit.json').read_text(encoding='utf-8'))
usage=json.loads((OUT/'MainUsageAudit02/Usage.json').read_text(encoding='utf-8'))
baseline=json.loads((OUT/'Baseline.json').read_text(encoding='utf-8'))['files']
uses={r['asset']:r['uses'] for r in usage['sequences']}
rows=[]
for r in audit['assets']:
    if r['skeleton_root']['bone'].lower()!='root':continue  # Separate prop skeletons.
    first=r['local_motion']['skeleton_root']['start'];reference=r['skeleton_root']['reference_transform']
    cm=math.dist(first['translation'],reference['translation'])
    qa,qb=first['rotation'],reference['rotation']
    dot=abs(sum(a*b for a,b in zip(qa,qb)))/math.sqrt(sum(a*a for a in qa)*sum(b*b for b in qb))
    deg=math.degrees(2*math.acos(min(1,dot)))
    if cm<=.01 and deg<=.001:continue  # Technical pose tolerances, not gameplay tuning.
    package='Content/'+r['package'].removeprefix('/Game/')+'.uasset'
    source=WORK/package;sha=hashlib.sha256(source.read_bytes()).hexdigest()
    assert sha==baseline[package.replace('/', '\\')],package
    backup=OUT/'RootAssetsBefore'/package;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    rows.append({'asset':r['asset'],'package_file':package,'before_sha256':sha,'root_first_frame':first,'root_reference_pose':reference,'offset_cm':cm,'angle_degrees':deg,'before_lock':r['root_motion_settings']['root_motion_root_lock'],'after_lock':'REF_POSE','consumers':uses[r['asset']]})
plan={'status':'prepared','source':'MainUsageAudit02/RootAudit.json: current imported RAW first-root transform and skeleton reference pose; not a new original tuning value','root_lock_adapter':'UE FRootMotionReset::ResetRootBoneForRootMotion RefPose removes absolute source origin; raw channels and extraction deltas are preserved','technical_position_tolerance_cm':.01,'technical_rotation_tolerance_degrees':.001,'assets':rows}
(OUT/'RootLockPlan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(MAIN/'Metadata/MonsterBloodReference_20261012/MainActualHits04/AttackCases.tsv',OUT/'AttackCases.tsv')
print('ROOT_LOCK_PLAN',len(rows),'first offsets',max(r['offset_cm'] for r in rows))
