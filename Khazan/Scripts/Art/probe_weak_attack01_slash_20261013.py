from pathlib import Path
import json,os,unreal as u
root=Path(u.Paths.project_dir()).resolve();out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
a=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo');assert a
rows=[]
fields=['EventId','bEndEvent','WindowStartTime','WindowEndTime','ParticleTemplate','NiagaraTemplate','TrailMesh','TrailMaterial','SourceSocket','RelativeLocation','RelativeRotation','Scale3D','bUseSourceCorrection','SourceCorrectionTransform','CorrectionBoneName','bAttached','bAbsoluteRotation','SourcePackage','SourceField']
for e in u.AnimationLibrary.get_animation_notify_events(a):
 n=e.get_editor_property('Notify')
 if isinstance(n,u.KZAnimNotify_CombatEffect):
  for x in [n]+list(n.get_editor_property('BatchedEffects')):
   if not x.get_editor_property('EventId').is_none() and x.get_editor_property('WindowStartTime')<1:
    rows.append({f:str(x.get_editor_property(f)) for f in fields})
for name,asset in [('Montage',a),('PlaneSlash',u.load_asset('/Game/_Art/Effects/DualAxeSword/Core/FP_DAS_PlaneSlash_Enhanced'))]:
 task=u.AssetExportTask();task.object=asset;task.filename=str(out/(name+'.t3d'));task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;assert u.Exporter.run_asset_export_task(task)
(out/'Probe.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('WEAK01_SOURCE_PROBE_PASSED',len(rows))