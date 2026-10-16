from pathlib import Path
import os,json,hashlib,difflib,unreal as u
root=Path(u.Paths.project_dir()).resolve();assert root.parent.name=='Khazan_WeakSlashWork_20261013'
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']);asset='/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo';a=u.load_asset(asset);assert a
src='KZFX_bab7be8e310a56b59c0b9461';addon='KZWeaponSlash_'+src
clock=[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)]
def export(name):
 t=u.AssetExportTask();t.object=a;t.filename=str(out/name);t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False;assert u.Exporter.run_asset_export_task(t);return (out/name).read_text(encoding='utf-8-sig')
before=export('Before.t3d');changed=[];found=set()
for e in u.AnimationLibrary.get_animation_notify_events(a):
 p=e.get_editor_property('Notify')
 if not isinstance(p,u.KZAnimNotify_CombatEffect):continue
 for x in [p]+list(p.get_editor_property('BatchedEffects')):
  name=str(x.get_editor_property('EventId'))
  if name not in [src,addon]:continue
  found.add((name,bool(x.get_editor_property('bEndEvent'))))
  row={'path':x.get_path_name(),'id':name,'end':bool(x.get_editor_property('bEndEvent')),'before':{f:str(x.get_editor_property(f)) for f in ['RelativeLocation','Scale3D','RelativeRotation','WeaponEdgeNearSocket','WeaponEdgeTipSocket']}}
  if name==src:
   # TEMP visual tuning from the user's request; original raw fields remain in Before.t3d.
   loc=x.get_editor_property('RelativeLocation');x.set_editor_property('RelativeLocation',u.Vector(loc.x+35,loc.y,loc.z))
   scale=x.get_editor_property('Scale3D');x.set_editor_property('Scale3D',u.Vector(scale.x*1.15,scale.y*1.15,scale.z))
  else:
   # Original world-space correction bone is not the active hand. Weak01's
   # actual downward cutting trajectory uses Weapon_R; Weapon_L retracts upward.
   x.set_editor_property('RelativeLocation',u.Vector(35,0,0));x.set_editor_property('Scale3D',u.Vector(1.15,1.15,1));x.set_editor_property('WeaponEdgeNearSocket','FX_R_Sword_02');x.set_editor_property('WeaponEdgeTipSocket','FX_R_Sword_01')
  row['after']={f:str(x.get_editor_property(f)) for f in ['RelativeLocation','Scale3D','RelativeRotation','WeaponEdgeNearSocket','WeaponEdgeTipSocket']};changed.append(row)
assert len(found)==4,found
assert clock==[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)]
after=export('After.t3d');delta=list(difflib.unified_diff(before.splitlines(),after.splitlines(),lineterm=''));(out/'Changes.patch').write_text('\n'.join(delta),encoding='utf-8')
# No object/asset template, clocks, audio or transform outside these four occurrences may change.
removed=[l[1:].strip() for l in delta if l.startswith('-') and not l.startswith('---')];added=[l[1:].strip() for l in delta if l.startswith('+') and not l.startswith('+++')]
assert all(l.startswith(('RelativeLocation=','Scale3D=','WeaponEdgeNearSocket=','WeaponEdgeTipSocket=')) for l in removed+added),(removed,added)
assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
file=root/'Content/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo.uasset'
(out/'Author.json').write_text(json.dumps({'status':'private_candidate_saved','asset':asset,'changes':changed,'clock_guid_unchanged':True,'changed_serialized_fields':removed+added,'only_changed_fields':['RelativeLocation','Scale3D','WeaponEdgeNearSocket','WeaponEdgeTipSocket'],'forward_cm':35,'size_multiplier':1.15,'values_source':'TEMP user-requested visual tuning, not original game metadata','sha256':hashlib.sha256(file.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('WEAK01_CANDIDATE_AUTHORED',len(changed))