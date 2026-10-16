from pathlib import Path
import os,json,difflib,unreal as u
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']);base=Path(u.Paths.project_dir()).resolve()/'Metadata/WeakAttack01Slash_20261013';a=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo');assert a
before=(base/'FinalAuthor01/After.t3d').read_text(encoding='utf-8-sig')
task=u.AssetExportTask();task.object=a;task.filename=str(out/'SavedMain.t3d');task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;assert u.Exporter.run_asset_export_task(task)
now=(out/'SavedMain.t3d').read_text(encoding='utf-8-sig');diff=list(difflib.unified_diff(before.splitlines(),now.splitlines(),lineterm=''));(out/'SavedDiff.patch').write_text('\n'.join(diff),encoding='utf-8');assert not diff,diff[:20]
ids=['KZFX_bab7be8e310a56b59c0b9461','KZWeaponSlash_KZFX_bab7be8e310a56b59c0b9461'];found=[];others=0
for e in u.AnimationLibrary.get_animation_notify_events(a):
 p=e.get_editor_property('Notify')
 if isinstance(p,u.KZAnimNotify_CombatEffect):
  for x in [p]+list(p.get_editor_property('BatchedEffects')):
   if str(x.get_editor_property('EventId')) in ids:
    found.append({'id':str(x.get_editor_property('EventId')),'end':bool(x.get_editor_property('bEndEvent')),'location':str(x.get_editor_property('RelativeLocation')),'scale':str(x.get_editor_property('Scale3D')),'near':str(x.get_editor_property('WeaponEdgeNearSocket')),'tip':str(x.get_editor_property('WeaponEdgeTipSocket'))})
   else:others+=1
assert len(found)==4
(out/'SavedVerification.json').write_text(json.dumps({'status':'passed','serialized_montage_exactly_matches_final_author':True,'rows':found,'other_effect_objects':others,'asset_saves':0},indent=2),encoding='utf-8');print('WEAK01_MAIN_FRESH_SAVED_EXACT_PASSED')