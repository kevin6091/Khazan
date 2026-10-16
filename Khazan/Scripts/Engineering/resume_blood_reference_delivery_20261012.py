"""Resume the two-row delivery journal using a new unlocked particle path."""
from pathlib import Path
from datetime import datetime,timezone
import os,shutil,json,hashlib,difflib
MAIN=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=MAIN/'Metadata/MonsterBloodReference_20261012';receipt=json.loads((OUT/'Delivery.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
assert len(receipt['rows'])==2,receipt['rows']
for row in receipt['rows']:assert sha(MAIN/row['path'])==row['after_sha256'],row
cpp=MAIN/'Source/Khazan/Character/KZMonster.cpp'
data=cpp.read_bytes();old=b'/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBlood"';new=b'/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference"'
assert data.count(old)==1;data=data.replace(old,new);cpp.write_bytes(data)
shutil.copy2(cpp,WORK/'Source/Khazan/Character/KZMonster.cpp')
receipt['rows'][1]['after_sha256']=sha(cpp)
for name in ['FP_Monster_HitBloodReference','M_Monster_HitBloodGround','M_Monster_HitBloodSheet','FT_Monster_HitBloodGroundMask','FT_Monster_HitBloodSheetMask']:
    rel='Content/_Art/Effects/Combat/Blood/'+name+'.uasset';src=WORK/rel;dst=MAIN/rel
    assert src.exists() and not dst.exists(),rel
    temp=dst.with_name(dst.name+'.BloodReference20261012.tmp');assert not temp.exists()
    shutil.copy2(src,temp);os.replace(temp,dst);assert sha(src)==sha(dst)
    receipt['rows'].append({'path':rel,'before_sha256':None,'after_sha256':sha(dst)})
    (OUT/'Delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt.update(status='applied_pending_fresh_main',utc=datetime.now(timezone.utc).isoformat(),locked_original_particle_preserved=True)
(OUT/'Delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
before=OUT/'Before/Source/Khazan/Character/KZMonster.cpp'
patch=difflib.unified_diff(before.read_text(encoding='utf-8-sig').splitlines(True),cpp.read_text(encoding='utf-8-sig').splitlines(True),fromfile='KZMonster.cpp.before',tofile='KZMonster.cpp')
(OUT/'RuntimeChanges.patch').write_text(''.join(patch),encoding='utf-8')
print('MAIN_DELIVERY_RESUMED',len(receipt['rows']))
