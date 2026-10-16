from pathlib import Path
import os,json,unreal as u
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']);a=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo');changed=[]
for e in u.AnimationLibrary.get_animation_notify_events(a):
 p=e.get_editor_property('Notify')
 if isinstance(p,u.KZAnimNotify_CombatEffect):
  for x in [p]+list(p.get_editor_property('BatchedEffects')):
   if str(x.get_editor_property('EventId'))!='KZWeaponSlash_KZFX_bab7be8e310a56b59c0b9461':continue
   x.set_editor_property('WeaponEdgeNearSocket','FX_R_Sword_02');x.set_editor_property('WeaponEdgeTipSocket','FX_R_Sword_01');x.set_editor_property('Scale3D',u.Vector(1.15,1.15,1));changed.append(x.get_path_name())
assert len(changed)==2;assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
(out/'Author.json').write_text(json.dumps({'status':'private_hand_selection_candidate','changed':changed,'side':'Weapon_R','geometry':'FX_R_Sword_02/01','scale':[1.15,1.15,1],'forward_cm':35,'mirror_hypothesis':'rejected; opposite hand was followed'},indent=2));print('WEAK01_RIGHT_SWEEP_CANDIDATE_SAVED')