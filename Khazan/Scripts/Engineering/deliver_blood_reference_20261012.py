"""CAS delivery of two existing runtime files and three blood packages; preserve all other Main work."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, os, shutil, difflib
MAIN=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=MAIN/'Metadata/MonsterBloodReference_20261012';baseline=json.loads((OUT/'Baseline.json').read_text(encoding='utf-8'))
files=['Source/Khazan/Character/KZMonster.h','Source/Khazan/Character/KZMonster.cpp','Content/_Art/Effects/Combat/Blood/FP_Monster_HitBlood.uasset','Content/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround.uasset','Content/_Art/Effects/Combat/Blood/M_Monster_HitBloodSheet.uasset','Content/_Art/Effects/Combat/Blood/FT_Monster_HitBloodGroundMask.uasset','Content/_Art/Effects/Combat/Blood/FT_Monster_HitBloodSheetMask.uasset']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
assert not (OUT/'Delivery.json').exists(),'Initial delivery already applied; use a guarded task-owned revision'
for rel in files:
    assert (WORK/rel).exists(),rel
    assert sha(MAIN/rel)==baseline['selected'].get(rel),(rel,'Concurrent Main change; inspect before merge')
rows=[];patch=[]
for rel in files:
    src=WORK/rel;dst=MAIN/rel
    if rel.startswith('Source/'):
        patch.extend(difflib.unified_diff(dst.read_text(encoding='utf-8-sig').splitlines(True),src.read_text(encoding='utf-8-sig').splitlines(True),fromfile=rel+'.before',tofile=rel))
    temp=dst.with_name(dst.name+'.BloodReference20261012.tmp');assert not temp.exists()
    shutil.copy2(src,temp);os.replace(temp,dst);assert sha(src)==sha(dst)
    rows.append({'path':rel,'before_sha256':baseline['selected'].get(rel),'after_sha256':sha(dst)})
    (OUT/'Delivery.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'status':'applied_pending_fresh_main','rows':rows,'new_runtime_files':0,'user_editor_controlled':False},indent=2),encoding='utf-8')
(OUT/'RuntimeChanges.patch').write_text(''.join(patch),encoding='utf-8')
print('MAIN_DELIVERED',len(rows))
