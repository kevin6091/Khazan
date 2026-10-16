"""Compensate the measured GPU mesh orientation on addon children only."""
from pathlib import Path
import json,os,re,unreal as u
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
r=Path(u.Paths.project_dir()).resolve();assert r.parent.name=='Khazan_PlayerSlashWork_20261013'
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
base=json.loads((MAIN/'Metadata/PlayerSlashAlignment_20261013/Baseline.json').read_text())
prior=json.loads((MAIN/'Metadata/PlayerSlashAlignment_20261013/AuthorOver01/Removed.json').read_text())
fields=list(next(iter(prior['original_snapshot'].values())))
def stable(v):
 if isinstance(v,u.Object):return v.get_path_name()
 return re.sub(r'\s*\(0x[0-9A-Fa-f]+\)','',str(v))
def snapshot(o):return {f:stable(o.get_editor_property(f)) for f in fields}
rows=[];count=0
for rel in base['sha256']:
 if not rel.startswith('Content'):continue
 p='/Game/'+Path(rel.replace('\\','/')).relative_to('Content').with_suffix('').as_posix()
 a=u.load_asset(p);assert a
 events=list(u.AnimationLibrary.get_animation_notify_events(a));clocks=[e.export_text() for e in events]
 original={};objects={};extras=[]
 for e in events:
  n=e.get_editor_property('Notify')
  if not isinstance(n,u.KZAnimNotify_CombatEffect):continue
  for o in [n]+list(n.get_editor_property('BatchedEffects')):
   if str(o.get_editor_property('EventId')).startswith('KZWeaponSlash_'):extras.append(o)
   else:original[o.get_path_name()]=snapshot(o);objects[o.get_path_name()]=o
 for o in extras:
  assert o.get_editor_property('bAlignToWeaponSweep') and o.get_editor_property('NiagaraTemplate').get_name()=='KZ_Slash'
  # Real particles: quarter-turn90 + renderer180; correction90 makes total360.
  o.set_editor_property('RelativeRotation',u.Rotator(yaw=90))
  o.set_editor_property('RelativeLocation',u.Vector(0,0,0))
  # Requested mesh diameter200 x recovered InitialParticle mesh scale2 =400cm.
  o.set_editor_property('WeaponSlashReferenceSpan',400.)
  rot=o.get_editor_property('RelativeRotation');assert rot.yaw==90 and rot.pitch==0 and rot.roll==0
  count+=1
 assert all(snapshot(objects[k])==v for k,v in original.items())
 assert clocks==[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)]
 if extras:
  u.EditorAssetLibrary.set_metadata_tag(a,'KZPlayerAdditionalSlash','Weapon tip/radius/world sweep; measured particle yaw90 plus renderer yaw180 compensated by notify yaw90; internal ScaleLerp neutralised per component; 2026-10-13')
  assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
 rows.append({'asset':p,'extras':len(extras),'original_snapshot':original,'event_clock_guid':clocks})
assert count==66
(out/'Aligned.json').write_text(json.dumps({'status':'passed','rows':rows,'updated_addon_children':count,'relative_yaw_deg':90,'relative_location_cm':[0,0,0],'effective_reference_span_cm':400,'raw_mesh_diameter_cm':200,'initial_particle_radial_scale':2,'GPU_original_rotation_deg':90,'source_shader_mesh_rotation_deg':180,'correction_derivation':'90+180+90=360 degrees'},indent=2),encoding='utf-8')
print('ALIGNED_ONLY_ADDON_TRANSFORMS',count)