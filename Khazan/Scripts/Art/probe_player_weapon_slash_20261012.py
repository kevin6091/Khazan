"""Target only the player's actual sockets/components and the requested slash asset."""
from pathlib import Path
import os,json
import unreal as u
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
bp=u.load_asset('/Game/_Art/Player/Character/Bluprints/BP_Player')
assert bp
cdo=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(bp.get_path_name()))
mesh=cdo.get_editor_property('Mesh')
rows=[]
ss=u.get_engine_subsystem(u.SubobjectDataSubsystem)
for h in ss.k2_gather_subobject_data_for_blueprint(bp):
 data=u.SubobjectDataBlueprintFunctionLibrary.get_data(h);obj=u.SubobjectDataBlueprintFunctionLibrary.get_object(data)
 if isinstance(obj,u.SceneComponent):
  row={'name':obj.get_name(),'class':obj.get_class().get_name(),'socket':str(obj.get_attach_socket_name()),'relative_location':str(obj.get_editor_property('RelativeLocation'))}
  if isinstance(obj,u.StaticMeshComponent):row['mesh']=str(obj.get_editor_property('StaticMesh'))
  if isinstance(obj,u.SkeletalMeshComponent):row['mesh']=str(obj.get_editor_property('SkeletalMesh'))
  rows.append(row)
sockets=[str(n) for n in mesh.get_all_socket_names()]
actor=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(cdo.get_class(),u.Vector(),u.Rotator(),transient=True);assert actor
registered=actor.get_editor_property('Mesh');positions={}
for name in ['Weapon_L','Weapon_R','FX_L_Axe_01','FX_L_Axe_02','FX_R_Sword_01','FX_R_Sword_02']:
 t=registered.get_socket_transform(name,u.RelativeTransformSpace.RTS_WORLD);loc=t.translation
 q=t.rotation
 positions[name]={'location':[loc.x,loc.y,loc.z],'rotation':[q.x,q.y,q.z,q.w],'bone':str(registered.get_socket_bone_name(name)),'bone_index':registered.get_bone_index(name)}
u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor)
report={'status':'passed','blueprint':bp.get_path_name(),'mesh':str(mesh.get_editor_property('SkeletalMesh')),'weapon_sockets':[n for n in sockets if any(k in n.lower() for k in ['weapon','sword','axe'])],'components':rows,'reference_sockets':positions}
slash_mesh=u.load_asset('/Game/VFX/01_ARPGEssentials/Meshes/SM_VFX_SlashRing_01');box=slash_mesh.get_bounding_box()
report['slash_mesh']={'path':slash_mesh.get_path_name(),'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}
def unrotate(q,v):
 x,y,z,w=q;vx,vy,vz=v
 # Inverse of the reference grip quaternion, geometry only (centimetres).
 x,y,z=-x,-y,-z;tx,ty,tz=2*(y*vz-z*vy),2*(z*vx-x*vz),2*(x*vy-y*vx)
 return [vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx]
edges={}
for grip,near,tip in [('Weapon_L','FX_L_Axe_02','FX_L_Axe_01'),('Weapon_R','FX_R_Sword_02','FX_R_Sword_01')]:
 g=positions[grip];edges[grip]=[unrotate(g['rotation'],[v-b for v,b in zip(positions[n]['location'],g['location'])]) for n in [near,tip]]
report['reference_edges_cm']=edges
(OUT/'WeaponProbe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
