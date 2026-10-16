"""Add separate weapon-driven Niagara children; keep every original FX untouched."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);BASE=ROOT/'Metadata/CombatImpactUpgrade_20261012'
old=json.loads((BASE/'BindingsAuthored.json').read_text(encoding='utf-8'))
geometry=json.loads((BASE/'WeaponSlashProbe03/WeaponProbe.json').read_text(encoding='utf-8'))['slash_mesh']
minimum=u.Vector(*geometry['min']);maximum=u.Vector(*geometry['max']);centre=(minimum+maximum)*.5
span=maximum.y-minimum.y;assert span>0
# Source renderer Meshes[0].Rotation.Yaw=180; compensate its mesh coordinate frame.
rotation=u.Rotator(yaw=180);centre_offset=u.Vector(centre.x,centre.y,-centre.z)
slash=u.load_asset('/Game/VFX/01_ARPGEssentials/KZ_Slash');assert slash
AL=u.AnimationLibrary;EAL=u.EditorAssetLibrary
selected={}
for r in old['player_effects']:selected.setdefault(r['asset'].split('.')[0],set()).add((r['id'],r['ending']))
dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())};assert not dirty.intersection(selected)
report={'status':'running','assets':[],'added':[],'geometry':geometry,'reference_span_cm':span,'renderer_rotation_degrees':180,'geometry_policy':'Mesh bounds + actual FX_L_Axe_01/02 or FX_R_Sword_01/02; sweep from successive finalized poses in actor space. No fixed front offset. Original effects and animation clocks untouched.'}
for path,wanted in sorted(selected.items()):
 a=u.load_asset(path);filename=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset')
 backup=OUT/'Before'/filename.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(filename,backup)
 before=hashlib.sha256(filename.read_bytes()).hexdigest();events=[e.export_text() for e in AL.get_animation_notify_events(a)];found=set();original=[]
 for e in AL.get_animation_notify_events(a):
  parent=e.get_editor_property('Notify')
  if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
  children=list(parent.get_editor_property('BatchedEffects'));new_children=[]
  for effect in [parent]+children:
   key=(str(effect.get_editor_property('EventId')),bool(effect.get_editor_property('bEndEvent')))
   if key not in wanted:continue
   assert effect.get_editor_property('ParticleTemplate') and not effect.get_editor_property('NiagaraTemplate')
   original.append((effect,{f:str(effect.get_editor_property(f)) for f in ['ParticleTemplate','SourceSocket','RelativeLocation','RelativeRotation','Scale3D','WindowStartTime','WindowEndTime','bOnAttackSuccessed']}))
   addon=u.new_object(u.KZAnimNotify_CombatEffect,outer=parent,name='WeaponSlash_'+key[0]+('_End' if key[1] else '_Begin'));assert addon
   for field in ['WindowStartTime','WindowEndTime','CustomTimeDilation','bEndEvent','bOnAttackSuccessed']:addon.set_editor_property(field,effect.get_editor_property(field))
   addon.set_editor_property('EventId','KZWeaponSlash_'+key[0]);addon.set_editor_property('NiagaraTemplate',slash)
   addon.set_editor_property('bAlignToWeaponSweep',True);addon.set_editor_property('WeaponSlashReferenceSpan',span)
   addon.set_editor_property('RelativeRotation',rotation);addon.set_editor_property('RelativeLocation',centre_offset)
   addon.set_editor_property('bAbsoluteRotation',True)
   for field in ['bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','bDestroyOnAnimEnd','OnNotifyEndDeattach']:addon.set_editor_property(field,True)
   anchor=str(effect.get_editor_property('CorrectionBoneName'));particle=effect.get_editor_property('ParticleTemplate').get_name()
   side='L' if anchor=='Weapon_L' or 'SpinningBeast_Axe' in particle else 'R' if anchor=='Weapon_R' else 'auto'
   if side!='auto':
    addon.set_editor_property('WeaponEdgeNearSocket','FX_L_Axe_02' if side=='L' else 'FX_R_Sword_02')
    addon.set_editor_property('WeaponEdgeTipSocket','FX_L_Axe_01' if side=='L' else 'FX_R_Sword_01')
   addon.set_editor_property('SourcePackage','UserSelected:'+slash.get_path_name())
   addon.set_editor_property('SourceField','Additional weapon sweep for '+key[0]+'; '+side+'; actual source FX blade sockets and Niagara mesh bounds')
   new_children.append(addon);found.add(key)
   report['added'].append({'asset':path,'original_id':key[0],'id':str(addon.get_editor_property('EventId')),'ending':key[1],'weapon':side,'original_particle':particle})
  if new_children:parent.set_editor_property('BatchedEffects',children+new_children)
 assert found==wanted,(path,wanted-found)
 for effect,fields in original:assert fields=={f:str(effect.get_editor_property(f)) for f in fields}
 assert events==[e.export_text() for e in AL.get_animation_notify_events(a)]
 EAL.set_metadata_tag(a,'KZPlayerAdditionalSlash','ARCH95 latest: original effects retained + separate KZ_Slash aligned to actual cutting-edge sockets/sweep. Frame/mesh-derived geometry; no actor-front tuning.')
 assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
 report['assets'].append({'path':path,'file':str(filename.relative_to(ROOT)),'before':before,'after':hashlib.sha256(filename.read_bytes()).hexdigest()})
 (OUT/'Checkpoint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(report['added'])==100
report['status']='passed';(OUT/'Added.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('PLAYER_ADDITIONAL_WEAPON_SLASH',len(report['added']))
