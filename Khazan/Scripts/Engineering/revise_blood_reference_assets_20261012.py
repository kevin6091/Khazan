"""Guarded replacement only of task-owned packages, plus new fluid variants."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil
ROOT=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan');OUT=ROOT/'Metadata/MonsterBloodReference_20261012'
receipt=json.loads((OUT/'Delivery.json').read_text(encoding='utf-8'));by_path={r['path']:r for r in receipt['rows']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
rev=OUT/'FluidRevision01';rev.mkdir(exist_ok=False);rows=[]
for name in ['FP_Monster_HitBloodReference','M_Monster_HitBloodFluid','FT_Monster_HitBloodFluid']:
    rel='Content/_Art/Effects/Combat/Blood/'+name+'.uasset';src=WORK/rel;dst=ROOT/rel
    before=sha(dst);assert before==(by_path.get(rel) or {}).get('after_sha256'),rel
    if dst.exists():shutil.copy2(dst,rev/dst.name)
    temp=dst.with_name(dst.name+'.BloodFluidRevision.tmp');assert not temp.exists();shutil.copy2(src,temp);os.replace(temp,dst)
    row={'path':rel,'before_sha256':before,'after_sha256':sha(dst)};rows.append(row)
    if rel in by_path:by_path[rel]['after_sha256']=row['after_sha256']
    else:receipt['rows'].append({'path':rel,'before_sha256':None,'after_sha256':row['after_sha256']})
for row in receipt['rows']:
    if row['path'].startswith('Source/'):
        row['after_sha256']=sha(ROOT/row['path'])
receipt['revision']='FluidRevision01';receipt['utc']=datetime.now(timezone.utc).isoformat()
(OUT/'Delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');(rev/'Revision.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('FLUID_REVISION_DELIVERED',len(rows))
