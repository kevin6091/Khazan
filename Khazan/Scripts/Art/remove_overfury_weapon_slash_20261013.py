"""Remove only the superseded OverFury addon, preserving every original notify."""
from pathlib import Path
import json,os,hashlib,re,unreal as u
r=Path(u.Paths.project_dir()).resolve();assert r.parent.name=='Khazan_PlayerSlashWork_20261013'
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
p='/Game/_Art/Player/Animation/InGame/DAS/OverFury/AM_DAS_Player_OverFury'
a=u.load_asset(p);assert a
before_events=[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)]
fields=['EventId','bEndEvent','ParticleTemplate','NiagaraTemplate','SourceSocket','RelativeLocation','RelativeRotation','Scale3D','WindowStartTime','WindowEndTime','CustomTimeDilation','bOnAttackSuccessed','bDestroyOnNotifyEnd','bDestroyOnAnimEnd']
fields += ['RelativeLocationRandomMin','RelativeLocationRandomMax','RelativeRotationRandomMin','RelativeRotationRandomMax','bUseWorldParticleUnits','bAttached','bOnlyStartAttach','OnNotifyEndDeattach','bAbsoluteRotation','TranslucencySortPriority','bSpawnOnFloor','bWinterOnly','bDestroyOnNotifyEndDeactived','bUseSourceCorrection','CorrectionBoneName','SourceCorrectionTransform','bUseCorrectionCurves','SurfaceOverride','bOverrideSurface','DecalMaterial','DecalSize','DecalLifeSpan','DecalOpacityCurveIndex']
def stable(v):
 if isinstance(v,u.Object):return v.get_path_name()
 return re.sub(r'\s*\(0x[0-9A-Fa-f]+\)','',str(v))
def snapshot(o):return {f:stable(o.get_editor_property(f)) for f in fields}
original=[];removed=[]
for e in u.AnimationLibrary.get_animation_notify_events(a):
 n=e.get_editor_property('Notify')
 if not isinstance(n,u.KZAnimNotify_CombatEffect):continue
 children=list(n.get_editor_property('BatchedEffects'))
 for o in [n]+children:
  if not str(o.get_editor_property('EventId')).startswith('KZWeaponSlash_'):original.append((o,snapshot(o)))
 kept=[]
 for o in children:
  if str(o.get_editor_property('EventId')).startswith('KZWeaponSlash_'):
   assert o.get_editor_property('bAlignToWeaponSweep') and o.get_editor_property('NiagaraTemplate').get_name()=='KZ_Slash'
   removed.append({'id':str(o.get_editor_property('EventId')),'ending':bool(o.get_editor_property('bEndEvent'))})
  else:kept.append(o)
 if len(kept)!=len(children):n.set_editor_property('BatchedEffects',kept)
assert len(removed)==34
assert before_events==[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)]
for o,d in original:assert d==snapshot(o)
u.EditorAssetLibrary.set_metadata_tag(a,'KZPlayerAdditionalSlash','OverFury: source effects only; KZWeaponSlash addon removed by user request 2026-10-13')
assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
(out/'Removed.json').write_text(json.dumps({'status':'passed','asset':p,'removed':removed,'original_objects_preserved':len(original),'notify_event_clock_guid_preserved':True,'event_clock_guid':before_events,'original_snapshot':{o.get_path_name():d for o,d in original}},indent=2),encoding='utf-8')
print('OVERFURY_ONLY_ADDON_REMOVED',len(removed))
