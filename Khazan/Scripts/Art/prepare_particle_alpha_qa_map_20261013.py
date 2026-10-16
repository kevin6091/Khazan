from pathlib import Path
import json,os,unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']);PROJECT=Path(u.Paths.project_dir()).resolve()
assert PROJECT==MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
plan=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/Engine.GameModeBase'))
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(0,0,950),u.Rotator(pitch=-90))
camera.set_actor_label('AlphaQA_Camera');cam=camera.get_component_by_class(u.CameraComponent);cam.set_editor_property('field_of_view',55)
pp=cam.get_editor_property('post_process_settings')
for k,v in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),('bloom_intensity',0.)]:pp.set_editor_property(k,v);pp.set_editor_property('override_'+k,True)
cam.set_editor_property('post_process_settings',pp);cam.set_editor_property('post_process_blend_weight',1.)
plane=u.load_asset('/Engine/BasicShapes/Plane');bg=u.load_asset('/Game/__ParticleAlphaQA/M_AlphaDiagnosticSavedBg');assert bg
back=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5));c=back.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(plane);c.set_material(0,bg);back.set_actor_scale3d(u.Vector(12,12,1))
for i,path in enumerate([plan['default_particle']]+[r['material'] for r in plan['rows']]):
    a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector((i//5-1.5)*150,(i%5-2)*150,0));a.set_actor_label('AlphaQA_Card_'+str(i))
    c=a.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(plane);c.set_material(0,u.load_asset(path));a.set_actor_scale3d(u.Vector(1.2,1.2,1))
assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/__ParticleAlphaQA/L_AlphaCards_Inspection')
print('QA_MAP_SAVED_IN_WORK_ONLY')
