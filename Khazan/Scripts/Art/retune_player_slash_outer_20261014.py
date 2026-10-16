"""Second isolated visual pass for the still inward slash windows."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import shutil
import unreal as u

root=Path(u.Paths.project_dir()).resolve()
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert root==main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
out=Path(os.environ['KZ_SLASH_OUT']);out.mkdir(parents=True,exist_ok=True)
first=json.loads((main/'Metadata/PlayerSlashOuter_20261014/AuthorCandidate01/Author.json').read_text(encoding='utf-8'))
# TEMP values, cm and unitless size. Selected from the additive-only RHI pass.
retune={
 'b135cc89':(90,1.25), '6b2e7f2c':(80,1.22), 'dedc9321':(80,1.22),
 'fee2ad76':(85,1.22), 'c971641d':(85,1.22),
 'afd862cd':(100,1.25), '64dc435c':(85,1.22),
 'dd09a312':(100,1.25), '9b5b4c7e':(80,1.22), '8ea9a2c2':(80,1.22),
 '04e5b308':(80,1.22), '77f06cdd':(90,1.22),
 '1e4b39e6':(80,1.22),
}

def export(asset,filename):
 t=u.AssetExportTask();t.object=asset;t.filename=str(filename);t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False
 assert u.Exporter.run_asset_export_task(t)
 return filename.read_text(encoding='utf-8-sig')

seen=set();rows=[]
for item in first['rows']:
 rel=item['file'];file=root/rel
 assert hashlib.sha256(file.read_bytes()).hexdigest()==item['after_sha256'],rel
 backup=out/'Candidate01Assets'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(file,backup)
 asset=u.load_asset(item['asset']);assert asset
 before=export(asset,out/(Path(rel).stem+'_Before.t3d'))
 clock=[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(asset)]
 changed=[]
 for event in u.AnimationLibrary.get_animation_notify_events(asset):
  parent=event.get_editor_property('Notify')
  if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
  for obj in [parent]+list(parent.get_editor_property('BatchedEffects')):
   event_id=str(obj.get_editor_property('EventId'));suffix=event_id[-8:]
   if suffix not in retune or not event_id.startswith('KZWeaponSlash_'):continue
   extension,scale=retune[suffix]
   obj.set_editor_property('WeaponSlashOutwardOffsetCm',float(extension))
   old=obj.get_editor_property('Scale3D')
   obj.set_editor_property('Scale3D',u.Vector(scale,scale,old.z))
   key=(event_id,bool(obj.get_editor_property('bEndEvent')));assert key not in seen;seen.add(key)
   changed.append({'id':event_id,'end':key[1],'outward_cm':extension,'xy_scale':scale})
 assert clock==[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(asset)]
 after=export(asset,out/(Path(rel).stem+'_After.t3d'))
 diff=list(difflib.unified_diff(before.splitlines(),after.splitlines(),lineterm=''))
 content=[line[1:].strip() for line in diff if line.startswith(('+','-')) and not line.startswith(('+++','---'))]
 assert all(line.startswith(('WeaponSlashOutwardOffsetCm=','Scale3D=')) for line in content),(rel,content)
 (out/(Path(rel).stem+'_Changes.patch')).write_text('\n'.join(diff),encoding='utf-8')
 if changed:assert u.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False)
 rows.append({'file':rel,'changes':changed,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
assert len(seen)==len(retune)*2,(len(seen),len(retune))
(out/'Retune.json').write_text(json.dumps({'status':'candidate2_saved','rows':rows,'changed_objects':len(seen),
 'numeric_source':'TEMP visual tuning from CandidateOnlyRHI01; original metadata not claimed'},indent=2),encoding='utf-8')
print('SLASH_OUTER_RETUNED',len(seen))
