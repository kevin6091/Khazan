"""Finish the saved snow plan in the isolated work project; preserve the clean map."""
from pathlib import Path
from array import array
import os,json,hashlib,traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan') or (os.environ.get('KZ_PRESENTATION_READ_ONLY')=='1' and ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'))
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
BASE=MAIN/'Metadata/CombatPresentationFix_20261011'
OUT=Path(os.environ['KZ_CLEAN_OUTPUT'])
READ_ONLY=os.environ.get('KZ_PRESENTATION_READ_ONLY')=='1'
MAP='/Game/Maps/L_HeinMach_Environment'
report={'success':False,'read_only':READ_ONLY,'saved':[],'provenance':'User-requested maximum snow 40cm/foot 35cm, prior weapon 50cm capped at substrate; capsule padding 15cm is the documented interpretation. Sun5000/Sky1.1 are assistant temporary visual tuning, not original metadata.'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pose(a):
 p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
 return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]

try:
 assert unreal.EditorLoadingAndSavingUtils.load_map(MAP)
 actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
 assert len(actors)==9861 and not any(isinstance(a,unreal.PostProcessVolume) for a in actors)
 poses={a.get_path_name():pose(a) for a in actors}
 owner=next(a for a in actors if isinstance(a,unreal.KZSnowDeformation))
 manifest=json.loads((BASE/'SnowBake/SurfaceProfiles.json').read_text(encoding='utf-8-sig'))
 profiles=[];materials=[]
 for entry in manifest['profiles']:
  material=unreal.load_asset(entry['material']);assert material
  scalar={str(n.get_editor_property('parameter_name')):n for n in unreal.MaterialEditingLibrary.get_material_expressions(material) if isinstance(n,unreal.MaterialExpressionScalarParameter)}
  for key,value in [('SnowHeightCm_DeepSnow',40.),('HM_DepthReferenceCm_User',40.)]:
   assert key in scalar
   if READ_ONLY:assert scalar[key].get_editor_property('default_value')==value
   else:material.modify();scalar[key].set_editor_property('default_value',value)
  for layer,value in entry['height_by_layer_cm'].items():
   if value:assert scalar['SnowHeightCm_'+layer].get_editor_property('default_value')==value
  if not READ_ONLY:
   errors=unreal.MaterialEditingLibrary.recompile_material(material);assert not errors,errors
   unreal.EditorAssetLibrary.set_metadata_tag(material,'SnowDepthProvenance','User40cm maximum/35cm foot/substrate-capped weapon; fieldR normalized to40cm; 2026-10-11')
   assert unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
   report['saved'].append(material.get_path_name())
  data=Path(entry['samples_file']);assert sha(data)==entry['samples_sha256']
  samples=array('f');samples.frombytes(data.read_bytes())
  profile=unreal.KZSnowSurfaceSamples()
  for key,value in [('material',material),('uv_origin_cm',unreal.Vector2D(*entry['uv_origin_cm'])),('uv_scale_cm',unreal.Vector2D(*entry['uv_scale_cm'])),('resolution',unreal.IntPoint(*entry['resolution'])),('samples',list(samples)),('depth_reference_cm',entry['depth_reference_cm']),('rim_height_cm',entry['rim_height_cm'])]:profile.set_editor_property(key,value)
  profiles.append(profile)
  materials.append({'asset':entry['material'],'samples_count':len(samples),'bytes':len(samples)*4,'depth_reference_cm':entry['depth_reference_cm'],'height_by_layer_cm':entry['height_by_layer_cm']})
 settings={'foot_compression':35./40.,'weapon_compression':1.,'player_capsule_padding_cm':15.}
 if not READ_ONLY:
  owner.modify();owner.set_editor_property('surface_contact_samples',profiles)
  for key,value in settings.items():owner.set_editor_property(key,value)
 for key,value in settings.items():assert abs(owner.get_editor_property(key)-value)<1e-6
 actual=owner.get_editor_property('surface_contact_samples');assert len(actual)==2
 for a,b in zip(actual,profiles):
  for key in ['samples','depth_reference_cm','rim_height_cm','material']:assert a.get_editor_property(key)==b.get_editor_property(key)
 lights=[]
 for a in actors:
  if a.get_actor_label()=='HM_PreviewSun':
   c=a.get_component_by_class(unreal.DirectionalLightComponent);desired=5000.
  elif isinstance(a,unreal.SkyLight):
   c=a.get_component_by_class(unreal.SkyLightComponent);desired=1.1
  else:continue
  before=c.get_editor_property('intensity')
  if READ_ONLY:assert abs(before-desired)<1e-4
  else:c.modify();c.set_editor_property('intensity',desired)
  lights.append({'actor':a.get_actor_label(),'before':before,'after':c.get_editor_property('intensity'),'source':'assistant temporary visual tuning'})
 assert len(lights)==2,lights
 assert poses=={a.get_path_name():pose(a) for a in actors}
 if not READ_ONLY:
  assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
  report['saved'].append(MAP)
 report.update(success=True,actor_count=len(actors),postprocess_volumes=0,actor_transforms_preserved=True,settings=settings,materials=materials,lights=lights)
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'Snow40.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
