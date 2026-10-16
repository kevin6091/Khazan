"""Resolve later source-plan variants using the actual pre-replacement manifest."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);BASE=ROOT/'Metadata/CombatImpactUpgrade_20261012'
old=json.loads((BASE/'BindingsAuthored.json').read_text(encoding='utf-8'));selected={}
for kind in ['monster','player']:
 for row in old[kind+'_effects']:selected.setdefault(row['asset'].split('.')[0],{})[(row['id'],row.get('ending',False))]=row['replaces']
report={'status':'running','assets':[],'fixed':[]}
for path,wanted in selected.items():
 a=u.load_asset(path);filename=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');changed=False;before=hashlib.sha256(filename.read_bytes()).hexdigest()
 for event in u.AnimationLibrary.get_animation_notify_events(a):
  parent=event.get_editor_property('Notify');state=event.get_editor_property('NotifyStateClass')
  effects=[state.get_editor_property('Effect')] if isinstance(state,u.KZAnimNotifyState_MonsterVisual) else [parent]+list(parent.get_editor_property('BatchedEffects')) if isinstance(parent,u.KZAnimNotify_CombatEffect) else []
  for e in effects:
   if not e:continue
   key=(str(e.get_editor_property('EventId')),bool(e.get_editor_property('bEndEvent')))
   if key not in wanted:continue
   target=u.load_asset(wanted[key]);assert target
   if e.get_editor_property('ParticleTemplate')!=target:
    if not changed:
     backup=OUT/'Before'/filename.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(filename,backup)
    e.set_editor_property('ParticleTemplate',target);changed=True;report['fixed'].append({'asset':path,'id':key[0],'ending':key[1],'resource':target.get_path_name()})
 if changed:assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
 report['assets'].append({'path':path,'file':str(filename.relative_to(ROOT)),'before':before,'after':hashlib.sha256(filename.read_bytes()).hexdigest(),'changed':changed})
report['status']='passed';(OUT/'ExactRefs.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('EXACT_PRE_REPLACEMENT_REFERENCES',len(report['fixed']))
