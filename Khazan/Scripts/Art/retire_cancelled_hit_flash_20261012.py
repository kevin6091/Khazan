"""Remove only the two unbound assets created by the cancelled flash task."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);EAL=u.EditorAssetLibrary;rows=[]
paths=['/Game/_Art/Effects/Combat/AttackContact/PP_Monster_HitFlameFlash','/Game/_Art/Effects/Combat/AttackContact/M_Monster_HitFlameFlash']
for path in paths:
 if not EAL.does_asset_exist(path):continue
 references=EAL.find_package_referencers_for_asset(path,True);assert not references,(path,references)
 filename=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');backup=OUT/(filename.name+'.retired-backup')
 shutil.copy2(filename,backup);digest=hashlib.sha256(filename.read_bytes()).hexdigest()
 assert EAL.delete_asset(path)
 if filename.exists():
  assert filename.resolve().parent==ROOT/'Content/_Art/Effects/Combat/AttackContact'
  assert hashlib.sha256(filename.read_bytes()).hexdigest()==digest
  filename.rename(OUT/(filename.stem+'.quarantined-uasset'))
 assert not filename.exists()
 rows.append({'path':path,'before':digest,'backup':str(backup),'references':references})
(OUT/'Retired.json').write_text(json.dumps({'status':'passed','removed':rows},indent=2),encoding='utf-8');print('CANCELLED_FLASH_REMOVED',len(rows))
