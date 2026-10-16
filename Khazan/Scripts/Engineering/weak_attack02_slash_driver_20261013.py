"""Observe only; the native fixture owns playback and no asset is saved."""
from pathlib import Path
import os

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source = (main / 'Scripts/Engineering/weak_attack01_slash_driver_20261013.py').read_text(encoding='utf-8')
source = source.replace("row={'time':t,", "row={'montage_time':(body.get_anim_instance().montage_get_position(body.get_anim_instance().get_current_active_montage()) if body.get_anim_instance().get_current_active_montage() else 0),'actor_quat':[player.get_actor_transform().rotation.x,player.get_actor_transform().rotation.y,player.get_actor_transform().rotation.z,player.get_actor_transform().rotation.w],'time':t,", 1)
probe = r'''
montage = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo')
all_events = unreal.AnimationLibrary.get_animation_notify_events(montage)
snapshot = []
fields = ['EventId', 'bEndEvent', 'WindowStartTime', 'WindowEndTime', 'ParticleTemplate', 'NiagaraTemplate', 'TrailMesh', 'TrailMaterial', 'SourceSocket', 'RelativeLocation', 'RelativeRotation', 'Scale3D', 'bAlignToWeaponSweep', 'WeaponEdgeNearSocket', 'WeaponEdgeTipSocket', 'WeaponSlashReferenceSpan', 'bUseSourceCorrection', 'SourceCorrectionTransform', 'CorrectionBoneName', 'bAttached', 'bAbsoluteRotation', 'SourcePackage', 'SourceField']
for event in all_events:
 parent = event.get_editor_property('Notify')
 if not isinstance(parent, unreal.KZAnimNotify_CombatEffect): continue
 for data in [parent] + list(parent.get_editor_property('BatchedEffects')):
  start = data.get_editor_property('WindowStartTime')
  if not 2 <= start < 3.9: continue
  snapshot.append({'path': data.get_path_name(), **{f: str(data.get_editor_property(f)) for f in fields}})
  if os.environ.get('KZ_WEAK02_SOURCE_ONLY') == '1' and str(data.get_editor_property('EventId')).startswith('KZWeaponSlash_'):
   data.set_editor_property('NiagaraTemplate', None)
(OUT / 'Weak02Data.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
task = unreal.AssetExportTask()
task.object = montage; task.filename = str(OUT / 'Montage.t3d'); task.exporter = unreal.ObjectExporterT3D(); task.automated = True; task.prompt = False
assert unreal.Exporter.run_asset_export_task(task)
'''
entry = "exec(compile(source, __file__, 'exec'), globals())"
assert source.count(entry) == 1
source = source.replace(entry, "source = source.replace('START=time.monotonic();', " + repr(probe) + " + '\\nSTART=time.monotonic();', 1)\n" + entry, 1)
assert "Weak02Data.json" in source
exec(compile(source, __file__, 'exec'), globals())
