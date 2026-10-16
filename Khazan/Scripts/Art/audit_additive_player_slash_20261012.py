"""Read only the latest amended packages; no saves or broad asset scan."""
from pathlib import Path
import json,os,hashlib
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);BASE=ROOT/'Metadata/CombatImpactUpgrade_20261012'
restore=json.loads((BASE/'RestoreOriginalFX01/Restored.json').read_text(encoding='utf-8'));add=json.loads((BASE/'PlayerAdditive01/Added.json').read_text(encoding='utf-8'))
latest={r['path']:r for r in restore['assets']};latest.update({r['path']:r for r in add['assets']})
if (BASE/'ExactOriginalRefs01/ExactRefs.json').exists():latest.update({r['path']:r for r in json.loads((BASE/'ExactOriginalRefs01/ExactRefs.json').read_text(encoding='utf-8'))['assets']})
old=json.loads((BASE/'BindingsAuthored.json').read_text(encoding='utf-8'));original={}
for kind in ['monster','player']:
 for row in old[kind+'_effects']:original[(row['asset'].split('.')[0],row['id'],row.get('ending',False))]=row['replaces'].split('.')[0]
AL=u.AnimationLibrary;counts={'monster_original':0,'player_original':0,'player_additional':0};found=set()
for path,row in latest.items():
 assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['after'],path
 asset=u.load_asset(path);assert asset
 for event in AL.get_animation_notify_events(asset):
  parent=event.get_editor_property('Notify');state=event.get_editor_property('NotifyStateClass')
  if isinstance(state,u.KZAnimNotifyState_MonsterVisual):effects=[state.get_editor_property('Effect')];kind='monster'
  elif isinstance(parent,u.KZAnimNotify_CombatEffect):effects=[parent]+list(parent.get_editor_property('BatchedEffects'));kind='player'
  else:continue
  for e in effects:
   if not e:continue
   key=(path,str(e.get_editor_property('EventId')),bool(e.get_editor_property('bEndEvent')))
   if key in original:
    assert not e.get_editor_property('NiagaraTemplate'),key
    assert e.get_editor_property('ParticleTemplate').get_path_name().split('.')[0]==original[key],key
    counts[kind+'_original']+=1;found.add(key)
   if kind=='monster':assert not e.get_editor_property('NiagaraTemplate'),key
   if key[1].startswith('KZWeaponSlash_'):
    assert kind=='player' and e.get_editor_property('NiagaraTemplate').get_path_name()=='/Game/VFX/01_ARPGEssentials/KZ_Slash.KZ_Slash'
    assert e.get_editor_property('bAlignToWeaponSweep') and e.get_editor_property('WeaponSlashReferenceSpan')==200
    assert not e.get_editor_property('ParticleTemplate') and not e.get_editor_property('bUseSourceCorrection')
    assert e.get_editor_property('bDestroyOnNotifyEnd') and e.get_editor_property('bDestroyOnAnimEnd')
    counts['player_additional']+=1
assert found==set(original),(set(original)-found)
assert counts=={'monster_original':120,'player_original':100,'player_additional':100},counts
assert not list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
(OUT/'SavedAudit.json').write_text(json.dumps({'status':'passed','counts':counts,'packages':len(latest),'writes':0,'saves':0,'monster_requested_niagara':0,'preserved_original_fx':True},indent=2),encoding='utf-8')
print('ADDITIVE_SLASH_SAVED_AUDIT_PASSED',counts)
