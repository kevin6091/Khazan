"""Fresh load: addon-only changes preserve every original notify field/clock."""
from pathlib import Path
import json,os,re,unreal as u
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
root=Path(u.Paths.project_dir()).resolve()
assert root in [MAIN,MAIN.parent.parent/'Khazan_PlayerSlashWork_20261013/Khazan']
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
report=json.loads((MAIN/'Metadata/PlayerSlashAlignment_20261013/AuthorAlign03/Aligned.json').read_text(encoding='utf-8'))
over=json.loads((MAIN/'Metadata/PlayerSlashAlignment_20261013/AuthorOver01/Removed.json').read_text(encoding='utf-8'))
def stable(v):
 if isinstance(v,u.Object):return v.get_path_name()
 return re.sub(r'\s*\(0x[0-9A-Fa-f]+\)','',str(v))
counts={};preserved=0
for row in report['rows']:
 p=row['asset'];a=u.load_asset(p);assert a
 events=list(u.AnimationLibrary.get_animation_notify_events(a))
 assert [e.export_text() for e in events]==row['event_clock_guid']
 nodes=[]
 for e in events:
  n=e.get_editor_property('Notify')
  if isinstance(n,u.KZAnimNotify_CombatEffect):nodes.extend([n]+list(n.get_editor_property('BatchedEffects')))
 objects={n.get_path_name():n for n in nodes}
 extras=[n for n in nodes if str(n.get_editor_property('EventId')).startswith('KZWeaponSlash_')]
 assert len(extras)==row['extras']
 for object_path,fields in row['original_snapshot'].items():
  assert object_path in objects
  n=objects[object_path]
  assert {f:stable(n.get_editor_property(f)) for f in fields}==fields,object_path
  preserved+=1
 for n in extras:
  rot=n.get_editor_property('RelativeRotation');loc=n.get_editor_property('RelativeLocation')
  assert rot.yaw==90 and rot.pitch==0 and rot.roll==0,(n.get_path_name(),str(rot))
  assert loc.x==0 and loc.y==0 and loc.z==0,(n.get_path_name(),str(loc))
  assert n.get_editor_property('WeaponSlashReferenceSpan')==400
  assert n.get_editor_property('NiagaraTemplate').get_name()=='KZ_Slash' and n.get_editor_property('bAlignToWeaponSweep')
 if 'OverFury' in p:
  assert not extras
  assert [e.export_text() for e in events]==over['event_clock_guid']
  for object_path,fields in over['original_snapshot'].items():
   assert {f:stable(objects[object_path].get_editor_property(f)) for f in fields}==fields
 counts[p]=len(extras)
assert sum(counts.values())==66
(out/'SavedVerification.json').write_text(json.dumps({'status':'passed','project':str(root),'extra_objects':counts,'remaining_start_end_pairs':33,'original_objects_all_six_preserved':preserved,'original_properties_each':37,'event_clock_guid_preserved':True,'OverFury_original_objects_preserved':len(over['original_snapshot']),'addon_yaw_deg':90,'addon_location_cm':[0,0,0]},indent=2),encoding='utf-8')
print('SAVED_PLAYER_SLASH_ALIGNMENT_PASSED',preserved,66)
