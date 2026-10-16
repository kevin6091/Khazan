"""Read the real gameplay skeletal presentation and postprocess state."""
import json
import unreal

pawn = unreal.GameplayStatics.get_player_pawn(WORLD, 0)
pc = unreal.GameplayStatics.get_player_controller(WORLD, 0)

def value(obj, name):
    try:
        result = obj.get_editor_property(name)
        return result.get_path_name() if hasattr(result, 'get_path_name') else str(result)
    except Exception as exc:
        return 'unexposed: ' + str(exc)

meshes = []
for mesh in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
    row = dict(name=mesh.get_name(), path=mesh.get_path_name(), materials=[m.get_path_name() if m else None for m in mesh.get_materials()])
    for key in ['skeletal_mesh_asset', 'visible', 'hidden_in_game', 'render_custom_depth', 'custom_depth_stencil_value', 'per_bone_motion_blur', 'animation_mode', 'leader_pose_component', 'visibility_based_anim_tick_option', 'enable_update_rate_optimizations', 'force_motion_blur']:
        row[key] = value(mesh, key)
    inst = mesh.get_anim_instance()
    row['anim_instance'] = inst.get_class().get_path_name() if inst else None
    meshes.append(row)
cvars = ['r.AntiAliasingMethod','r.ScreenPercentage','sg.AntiAliasingQuality','r.TSR.Velocity.WeightClampingSampleCount','r.TSR.History.ScreenPercentage','r.TSR.ShadingRejection.Flickering','r.MotionBlurQuality','r.MotionBlur.Amount','r.VelocityOutputPass','r.CustomDepth']
report = dict(pawn=pawn.get_path_name(), location=str(pawn.get_actor_location()), rotation=str(pawn.get_actor_rotation()), meshes=meshes, cvars={key:unreal.SystemLibrary.get_console_variable_float_value(key) for key in cvars})
for camera in pawn.get_components_by_class(unreal.CameraComponent):
    report['camera'] = dict(path=camera.get_path_name(), location=str(camera.get_world_location()), rotation=str(camera.get_world_rotation()), post_process_blend_weight=value(camera,'post_process_blend_weight'))
(OUT/'RuntimeProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.execute_console_command(WORLD, 'Shot filename="' + str(OUT/'initial.png') + '" -nosuffix')
print(json.dumps(report,indent=2))
