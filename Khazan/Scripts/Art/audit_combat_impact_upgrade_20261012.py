"""Fresh saved-package verification without saving or editing."""
from pathlib import Path
import hashlib,json,os,re
import unreal as u
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);PLAN=json.loads((MAIN/'Metadata/CombatImpactUpgrade_20261012/BindingsAuthored.json').read_text(encoding='utf-8'))
AL=u.AnimationLibrary;EAL=u.EditorAssetLibrary
integrated=[]
timing_delivery=MAIN/'Metadata/AnimationTimingKnockback_20261012/Delivery.json'
timing={r['file'].replace('\\','/'):r for r in json.loads(timing_delivery.read_text(encoding='utf-8'))['files']} if timing_delivery.exists() else {}
def export(a,name):
 t=u.AssetExportTask();t.object=a;t.filename=str(OUT/name);t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False
 assert u.Exporter.run_asset_export_task(t);return (OUT/name).read_text(encoding='utf-8-sig')
for row in PLAN['assets']:
 p=ROOT/row['file'];expected=row['after'];concurrent=timing.get(row['file'].replace('\\','/'))
 if ROOT==MAIN and concurrent:
  assert concurrent['before']==row['after'],row['path']
  expected=concurrent['after']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,row['path']
 integrated.append({'path':row['path'],'file':row['file'],'sha256':expected,'animation_timing_merge':bool(ROOT==MAIN and concurrent)})
 a=u.load_asset(row['path']);assert a,row['path']
 for event in AL.get_animation_notify_events(a) if isinstance(a,u.AnimSequenceBase) else []:
  parent=event.get_editor_property('Notify');state=event.get_editor_property('NotifyStateClass')
  if isinstance(state,u.KZAnimNotifyState_MonsterVisual):effects=[state.get_editor_property('Effect')]
  elif isinstance(parent,u.KZAnimNotify_CombatEffect):effects=[parent]+list(parent.get_editor_property('BatchedEffects'))
  else:continue
  for effect in effects:
   if not effect:continue
   system=effect.get_editor_property('NiagaraTemplate')
   if not system:continue
   assert system.get_path_name().split('.')[0] in ['/Game/VFX/01_ARPGEssentials/KZ_Slash','/Game/VFX/01_ARPGEssentials/KZ_SwordsMan_Sting']
   assert not effect.get_editor_property('ParticleTemplate') and not effect.get_editor_property('bUseSourceCorrection')
   assert effect.get_editor_property('SourceSocket')==u.Name('None')
   assert effect.get_editor_property('Scale3D')==u.Vector(1,1,1)
d=u.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
for n in d.get_editor_property('Nodes'):
 if str(n.get_editor_property('NodeId'))=='SpinningAttack01':
  for w in n.get_editor_property('AttackWindows'):
   for k in w.get_editor_property('Keys'):
    c=k.get_editor_property('Center');assert c.x>0 and abs(c.y)<1e-6
guard=u.get_default_object(EAL.load_blueprint_class('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'))
assert guard.get_editor_property('ParryImpactEffect').get_name()=='PP_Combat_HitBurst'
player=u.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player');assert player.get_editor_property('HitReactions').get_editor_property('ImpactEffect').get_name()=='PP_Combat_HitBurst'
for path in ['/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst','/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference']:
 a=u.load_asset(path);text=export(a,a.get_name()+'.t3d');lines=[l for l in text.splitlines() if l.startswith('   Emitters(')]
 assert len(lines)==(3 if a.get_name()=='PP_Combat_HitBurst' else 6)
 assert all('KZHitFlash' not in l for l in lines)
 assert sum('KZHitFire' in l for l in lines)==3
 if (MAIN/'Metadata/CombatImpactUpgrade_20261012/HitBurstFinalDelivered.json').exists():
  final=json.loads((MAIN/'Metadata/CombatImpactUpgrade_20261012/HitBurstFinalDelivered.json').read_text(encoding='utf-8'))
  row=next(r for r in final['rows'] if r['path']==path)
  assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['after']
  for name in ['KZHitFireBlue','KZHitFirePurple','KZHitFireRed']:
   emitter=re.search(r'^   Begin Object Name="'+name+r'" .*?^   End Object',text,re.M|re.S).group(0)
   assert 'TypeDataModule=' not in emitter or 'TypeDataModule=None' in emitter
  assert text.count('Material="/Script/Engine.Material\'/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/DefaultParticle.DefaultParticle\'"')>=3
  if path.endswith('FP_Monster_HitBloodReference'):
   old=(MAIN/'Metadata/CombatImpactUpgrade_20261012/BloodBefore.t3d').read_text(encoding='utf-8-sig')
   blocks=lambda s:{m.group(1):m.group(0) for m in re.finditer(r'^   Begin Object Name="([^"]+)" .*?^   End Object',s,re.M|re.S)}
   normalize=lambda s:re.sub(r'^ +Begin Object Name="ParticleModuleEventGenerator_1" .*?^ +End Object\n?', '',s,flags=re.M|re.S)
   before,after=blocks(old),blocks(text)
   original_names=[n for n in before if not n.startswith('KZHitFlash')]
   # T3D root blocks include nested distributions. The 53-object pre-upgrade
   # report counted descendants; here 32 original root blocks cover that data.
   assert len(original_names)==32
   assert all(normalize(after.get(n,''))==normalize(before[n]) for n in original_names)
assert not EAL.find_package_referencers_for_asset('/Game/_Art/Effects/Combat/AttackContact/PP_Monster_HitFlameFlash',False)
for name in ['PP_Monster_HitFlameFlash','M_Monster_HitFlameFlash']:
 assert not (ROOT/'Content/_Art/Effects/Combat/AttackContact'/(name+'.uasset')).exists()
material=u.load_asset('/Game/VFX/01_ARPGEssentials/Materials/MM_VFX_MaskedParticles');assert material.get_editor_property('BlendMode')==u.BlendMode.BLEND_TRANSLUCENT
assert not list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
(OUT/'SavedAudit.json').write_text(json.dumps({'status':'passed','packages':len(PLAN['assets']),'monster_bindings':len(PLAN['monster_effects']),'player_bindings':len(PLAN['player_effects']),'data_edits':0,'saves':0,'flash_template_references':0,'project':str(ROOT)},indent=2),encoding='utf-8')
print('COMBAT_IMPACT_SAVED_AUDIT_PASSED',len(PLAN['assets']))
(OUT/'IntegratedPackages.json').write_text(json.dumps({'status':'passed','packages':integrated,'concurrent_timing_preserved':sum(r['animation_timing_merge'] for r in integrated)},indent=2),encoding='utf-8')
