"""Byte-exact CAS delivery of only the 106 validated packages."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
OUT=ROOT/'Metadata/CombatImpactUpgrade_20261012'
plan=json.loads((OUT/'BindingsAuthored.json').read_text(encoding='utf-8'))
assert json.loads((OUT/'WorkSaved01/SavedAudit.json').read_text(encoding='utf-8'))['status']=='passed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in plan['assets']:
 assert sha(WORK/row['file'])==row['after']
 assert sha(ROOT/row['file']) in (row['before'],row['after']),row['path']
rows=[]
for row in plan['assets']:
 target=ROOT/row['file'];before=sha(target)
 if before!=row['after']:
  backup=OUT/'MainBefore'/row['file'];backup.parent.mkdir(parents=True,exist_ok=True)
  assert not backup.exists();shutil.copy2(target,backup)
  shutil.copyfile(WORK/row['file'],target)
 assert sha(target)==row['after'];rows.append(dict(row,delivered_before=before))
(OUT/'Delivered.json').write_text(json.dumps({'status':'passed','packages':len(rows),'rows':rows,'source_or_dll_copied':0},indent=2),encoding='utf-8')
print('MAIN_ASSETS_DELIVERED',len(rows))
