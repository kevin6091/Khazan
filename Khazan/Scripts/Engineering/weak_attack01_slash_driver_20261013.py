"""Owned resumed validation binds the loaded DLL despite concurrent manifest writes."""
from pathlib import Path
import os

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out = os.environ['KZ_MONSTER_PHYSICS_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=out, KZ_MONSTER_REPAIR_MODE='rhi',
                  KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_SLASH_TEST', 'Khazan.CombatEffect.PIE'))
source = (main / 'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
old = "buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"
new = """report['manifest_snapshot_module']=str(module)
candidates=[p for p in (ROOT/'Binaries/Win64').glob('UnrealEditor-Khazan*.dll') if kernel.GetModuleHandleW(p.name)]
assert len(candidates)==1, candidates
module=candidates[0]
report['manifest_module']=str(module)
report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
report['module_binding']='Actual loaded process module; manifest snapshot may change during other builds'
buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"""
assert source.count(old) == 1
source = source.replace(old, new, 1)
source=source.replace("Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]","Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_WeakSlashWork_20261013/Khazan')]")
if os.environ.get('KZ_SLASH_INSPECT')=='1':source=source.replace("['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE']","['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE','Khazan.CombatEffect.PIE']")

probe = r"""
if os.environ.get('KZ_WEAK_SOURCE_ONLY')=='1':
 montage=unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo')
 for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
  parent=event.get_editor_property('Notify')
  if isinstance(parent,unreal.KZAnimNotify_CombatEffect):
   for data in [parent]+list(parent.get_editor_property('BatchedEffects')):
    if str(data.get_editor_property('EventId')).startswith('KZWeaponSlash_') and data.get_editor_property('WindowStartTime')<2:data.set_editor_property('NiagaraTemplate',None)
_diag_frame=-1
_diag_fault=False
def pose_diagnostic():
 global _diag_frame,_diag_fault
 if _diag_fault:return
 try:
  for world in unreal.EditorLevelLibrary.get_pie_worlds(False):
   player=unreal.GameplayStatics.get_player_character(world,0)
   if not player:return
   t=unreal.GameplayStatics.get_time_seconds(world)
   frame=round(t*60)
   if frame==_diag_frame:return
   _diag_frame=frame
   body=player.get_editor_property('Mesh')
   def v(x):return [x.x,x.y,x.z]
   row={'time':t,'actor':v(player.get_actor_location()),'forward':v(player.get_actor_forward_vector()),'right':v(player.get_actor_right_vector()),'sockets':{n:v(body.get_socket_location(n)) for n in ['Weapon_L','Weapon_R','FX_L_Axe_01','FX_L_Axe_02','FX_R_Sword_01','FX_R_Sword_02']},'effects':[]}
   for fx in player.get_components_by_class(unreal.SceneComponent):
    tags=[str(tag) for tag in fx.get_editor_property('ComponentTags')]
    if 'KZCombatEffect' in tags:
     tr=fx.get_world_transform()
     row['effects'].append({'class':fx.get_class().get_name(),'tags':tags,'position':v(tr.translation),'scale':v(tr.scale3d),'quat':[tr.rotation.x,tr.rotation.y,tr.rotation.z,tr.rotation.w],'socket':str(fx.get_attach_socket_name())})
   with (OUT/'LivePose.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
   if os.environ.get('KZ_WEAK_BACK_CAMERA')=='1':
    base=player.get_actor_location()
    forward=player.get_actor_forward_vector();right=player.get_actor_right_vector()
    location=base-forward*480+right*80+unreal.Vector(0,0,340)
    for camera in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.CameraActor):
     camera.set_actor_location(location,False,False);camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location,base+unreal.Vector(0,0,80)),False)
 except Exception as e:
  _diag_fault=True;(OUT/'PoseDiagnosticError.txt').write_text(str(e))
"""
source=source.replace('START=time.monotonic();',probe+'\nSTART=time.monotonic();',1)
source=source.replace("        log=(OUT/'Editor.log').read_text", "        pose_diagnostic()\n        log=(OUT/'Editor.log').read_text",1)

exec(compile(source, __file__, 'exec'), globals())
