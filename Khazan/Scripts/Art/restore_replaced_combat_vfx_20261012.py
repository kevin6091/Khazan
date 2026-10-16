"""Undo only this task's replaced FX fields, retaining later FPS/timing changes."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);BASE=ROOT/'Metadata/CombatImpactUpgrade_20261012'
change=json.loads((BASE/'BindingsAuthored.json').read_text(encoding='utf-8'))
monster=json.loads((ROOT/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
player=json.loads((ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
original_m={(r['asset'].split('.')[0],r['event_id']):r['effect_fields'] for r in monster['events'] if r.get('effect_fields')}
original_p={(r['montage'].split('.')[0],r['event_id']):r['notify_fields'] for r in player['events']}
fields=['NiagaraTemplate','ParticleTemplate','TrailMesh','SourceSocket','CorrectionBoneName','bUseSourceCorrection','bUseCorrectionCurves','RelativeLocation','RelativeRotation','Scale3D','bAttached','bOnlyStartAttach','bAbsoluteRotation','bOnAttackSuccessed','bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','OnNotifyEndDeattach','RelativeLocationRandomMin','RelativeLocationRandomMax','RelativeRotationRandomMin','RelativeRotationRandomMax']
defaults=u.get_default_object(u.KZAnimNotify_CombatEffect);AL=u.AnimationLibrary;EAL=u.EditorAssetLibrary
selected={}
recorded_particles={}
for kind in ['monster','player']:
 for row in change[kind+'_effects']:
  selected.setdefault(row['asset'].split('.')[0],{})[(row['id'],row.get('ending',False))]=kind
  recorded_particles[(row['asset'].split('.')[0],row['id'])]=row['replaces']
dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())};assert not dirty.intersection(selected)
report={'status':'running','assets':[],'monster_objects':0,'player_objects':0,'restored_fields':fields,'timing_edits':0}
for path,wanted in sorted(selected.items()):
 a=u.load_asset(path);assert a
 filename=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');backup=OUT/'Before'/filename.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(filename,backup)
 before=hashlib.sha256(filename.read_bytes()).hexdigest();events=[e.export_text() for e in AL.get_animation_notify_events(a)];found=set()
 for event in AL.get_animation_notify_events(a):
  parent=event.get_editor_property('Notify');state=event.get_editor_property('NotifyStateClass')
  if isinstance(state,u.KZAnimNotifyState_MonsterVisual):effects=[state.get_editor_property('Effect')]
  elif isinstance(parent,u.KZAnimNotify_CombatEffect):effects=[parent]+list(parent.get_editor_property('BatchedEffects'))
  else:continue
  for effect in effects:
   if not effect:continue
   key=(str(effect.get_editor_property('EventId')),bool(effect.get_editor_property('bEndEvent')))
   if key not in wanted:continue
   kind=wanted[key];source=(original_m if kind=='monster' else original_p)[(path,key[0])]
   for field in fields:
    value=source.get(field,defaults.get_editor_property(field))
    if field=='NiagaraTemplate':value=None
    elif field=='ParticleTemplate':value=u.load_asset(recorded_particles[(path,key[0])]);assert value
    elif field in ('ParticleTemplate','TrailMesh') and isinstance(value,str):value=u.load_asset(value);assert value
    elif field in ('SourceSocket','CorrectionBoneName'):value=u.Name(str(value))
    elif field in ('RelativeLocation','Scale3D','RelativeLocationRandomMin','RelativeLocationRandomMax') and isinstance(value,dict):value=u.Vector(value.get('X',0),value.get('Y',0),value.get('Z',0))
    elif field in ('RelativeRotation','RelativeRotationRandomMin','RelativeRotationRandomMax') and isinstance(value,dict):value=u.Rotator(pitch=value.get('Pitch',0),yaw=value.get('Yaw',0),roll=value.get('Roll',0))
    effect.set_editor_property(field,value)
   assert not effect.get_editor_property('NiagaraTemplate')
   assert effect.get_editor_property('ParticleTemplate') or effect.get_editor_property('TrailMesh')
   report[kind+'_objects']+=1;found.add(key)
 assert found==set(wanted),(path,set(wanted)-found)
 assert events==[e.export_text() for e in AL.get_animation_notify_events(a)],path
 EAL.set_metadata_tag(a,'KZCombatImpactUpgrade','ARCH95 latest: original resource/anchor/geometry restored; monsters have no requested Niagara. Player additional weapon Slash authored separately. Current FPS/timing preserved.')
 assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
 report['assets'].append({'path':path,'file':str(filename.relative_to(ROOT)),'before':before,'after':hashlib.sha256(filename.read_bytes()).hexdigest()})
 (OUT/'Checkpoint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['monster_objects']==120 and report['player_objects']==100
report['status']='passed';(OUT/'Restored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('ORIGINAL_FX_RESTORED',report['monster_objects'],report['player_objects'])
