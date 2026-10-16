"""Revise only existing task-owned blood packages against the last delivery SHA."""
from pathlib import Path
import json,hashlib,shutil,os,sys
ROOT=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan');OUT=ROOT/'Metadata/MonsterBloodReference_20261012'
receipt=json.loads((OUT/'Delivery.json').read_text(encoding='utf-8'));lookup={r['path']:r for r in receipt['rows']};directory=OUT/sys.argv[1]
assert not (directory/'Revision.json').exists(),'Completed revision must not run again';directory.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
names=['FP_Monster_HitBloodReference','M_Monster_HitBloodGround','FT_Monster_HitBloodGroundMask','M_Monster_HitBloodFluid','FT_Monster_HitBloodFluid'];rows=[]
for name in names:
    rel='Content/_Art/Effects/Combat/Blood/'+name+'.uasset';dst=ROOT/rel;src=WORK/rel
    assert sha(dst)==lookup[rel]['after_sha256'],rel
    if sha(src)==sha(dst):
        leftover=dst.with_name(dst.name+'.BloodOwnedRevision.tmp')
        if leftover.exists():
            assert leftover.resolve().is_relative_to(ROOT.resolve()) and sha(leftover)==sha(src);leftover.unlink()
        continue
    shutil.copy2(dst,directory/dst.name);before=sha(dst);tmp=dst.with_name(dst.name+'.BloodOwnedRevision.tmp');assert not tmp.exists()
    shutil.copy2(src,tmp);os.replace(tmp,dst);lookup[rel]['after_sha256']=sha(dst);rows.append({'path':rel,'before_sha256':before,'after_sha256':sha(dst)})
receipt['revision']=sys.argv[1]
(OUT/'Delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');(directory/'Revision.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('OWNED_PACKAGES_REVISED',len(rows))
