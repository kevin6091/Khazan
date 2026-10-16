"""CAS only this repair onto current Main; deliver no private binary or config."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
MAIN=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan');OUT=MAIN/'Metadata/MonsterRootCollisionRepair_20261012'
assert not (OUT/'Delivered.json').exists()
for name in ['RootPreservationAfter02','SixFamilyContacts03','AllAttackEffects01']:
    assert json.loads((OUT/name/'Driver.json').read_text())['status']=='passed',name
before={r['asset']:r for r in json.loads((OUT/'RootPreservationBefore01/RootPoses.json').read_text())}
after={r['asset']:r for r in json.loads((OUT/'RootPreservationAfter02/RootPoses.json').read_text())}
assert len(before)==len(after)==392 and before.keys()==after.keys()
for asset,r in after.items():
    assert r['data_model_sha1']==before[asset]['data_model_sha1'] and r['notifies_sha1']==before[asset]['notifies_sha1'],asset
    assert r['root_offset_cm']<.01 and r['root_angle_degrees']<.00572958,asset
(OUT/'NativePreservationProof.json').write_text(json.dumps({'status':'passed','body_sequences':392,'samples':1176,'complete_data_models_unchanged':392,'complete_notifies_unchanged':392,'prop_sequences_audited_separately':3,'before':'RootPreservationBefore01/RootPoses.json','after':'RootPreservationAfter02/RootPoses.json','technical_compressed_tolerance':'.01cm / 1e-4rad'},indent=2),encoding='utf-8')
applied=json.loads((OUT/'RootLockPrivateApply03/Applied.json').read_text(encoding='utf-8'));assert applied['status']=='applied_private_pending_fresh_native_validation' and len(applied['changed'])==88
source=['Ability/Combo/KZComboActionAbility.cpp','Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Character/KZMonster.h','Character/KZMonster.cpp','Tests/KZPlayerAttackCollisionPIETest.cpp','Tests/KZMonsterPresentationRepairPIETest.cpp','Tests/KZMonsterContactRepairPIETest.cpp']
selected=['Source/Khazan/'+p for p in source]+[r['package_file'] for r in applied['changed']]
baseline=json.loads((OUT/'Baseline.json').read_text(encoding='utf-8'))['files']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for relative in selected:
    target=MAIN/relative;key=str(Path(relative))
    if key in baseline:assert sha(target)==baseline[key],relative
    else:assert not target.exists(),relative
    assert (WORK/relative).is_file(),relative
for r in applied['changed']:assert sha(WORK/r['package_file'])==r['after_sha256']
preserved={p:sha(MAIN/p) for p in baseline if p not in {str(Path(r)) for r in selected}}
records=[]
for relative in selected:
    target=MAIN/relative;key=str(Path(relative));before_sha=sha(target) if target.exists() else None
    if target.exists():
        assert before_sha==baseline[key]
        backup=OUT/'MainBefore'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(WORK/relative,target)
    records.append({'path':relative,'before_sha256':before_sha,'after_sha256':sha(target)})
assert all(sha(MAIN/p)==s for p,s in preserved.items())
report={'status':'delivered_pending_main_build_and_runtime','utc':datetime.now(timezone.utc).isoformat(),'main':str(MAIN),'runtime_files':4,'dev_files':3,'new_runtime_files':0,'animation_packages':88,'files':records,'unselected_baseline_files_preserved':len(preserved),'private_binaries_delivered':0,'backup':'MainBefore'}
(OUT/'Delivered.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('MAIN_CONTACT_DELIVERED',len(records),'preserved',len(preserved))
