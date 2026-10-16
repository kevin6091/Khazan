"""Archive only the two unused packages created in this task, using saved dependency and byte proof."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/MonsterBloodReference_20261012'
proof=json.loads((OUT/'MainSaved04/SavedAudit.json').read_text(encoding='utf-8'));assert proof['status']=='passed'
ref=proof['retired_trial_referencers'];prefix='/Game/_Art/Effects/Combat/Blood/'
assert ref[prefix+'M_Monster_HitBloodSheet']==[] and ref[prefix+'FT_Monster_HitBloodSheetMask']==[prefix+'M_Monster_HitBloodSheet']
receipt=json.loads((OUT/'Delivery.json').read_text(encoding='utf-8'));lookup={r['path']:r for r in receipt['rows']};backup=OUT/'RetiredTrials';backup.mkdir(exist_ok=False)
retired=[]
for name in ['M_Monster_HitBloodSheet','FT_Monster_HitBloodSheetMask']:
    rel='Content/_Art/Effects/Combat/Blood/'+name+'.uasset';path=ROOT/rel;sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert lookup[rel]['before_sha256'] is None and sha==lookup[rel]['after_sha256']
    assert path.resolve().is_relative_to(ROOT.resolve())
    shutil.copy2(path,backup/path.name);path.unlink();retired.append(lookup[rel])
receipt['rows']=[r for r in receipt['rows'] if r not in retired];receipt['retired_trials']=retired
(OUT/'Delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');(backup/'Archived.json').write_text(json.dumps(retired,indent=2),encoding='utf-8')
# Failed replacement's exact task-owned copy is no longer needed; the user's original is preserved.
temp=ROOT/'Content/_Art/Effects/Combat/Blood/FP_Monster_HitBlood.uasset.BloodReference20261012.tmp'
if temp.exists():
    assert temp.resolve().is_relative_to(ROOT.resolve());shutil.copy2(temp,backup/temp.name);temp.unlink()
print('TRIAL_PACKAGES_ARCHIVED',len(retired))
