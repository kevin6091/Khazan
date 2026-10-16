"""Compare flat native Nanite and fallback depth against the same PIE collision point."""
from pathlib import Path
import json
import time
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert W
P=unreal.Vector(12000,13500,117.65061950683594)
parts=[];old=[];mids={}
for a in unreal.GameplayStatics.get_all_actors_of_class(W,unreal.Actor):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if not c.component_has_tag('HeinMachSnowSurface'):continue
        parts.append(c)
        for i in range(c.get_num_materials()):
            mat=c.get_material(i);old.append((c,i,mat))
            key=mat.get_path_name()
            if key not in mids:
                mid=unreal.MaterialLibrary.create_dynamic_material_instance(W,mat)
                for param in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mat):
                    if str(param).startswith('SnowHeightCm_'):mid.set_scalar_parameter_value(param,0)
                mid.set_scalar_parameter_value('SnowRimHeightCm_Temporary',0)
                mids[key]=mid
            c.set_material(i,mids[key])
C=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
    unreal.SceneCapture2D,P+unreal.Vector(0,0,800),unreal.Rotator(pitch=-90,yaw=0,roll=0),True)
SC=C.get_component_by_class(unreal.SceneCaptureComponent2D)
RT=unreal.RenderingLibrary.create_render_target2d(W,128,128,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
SC.texture_target=RT
SC.capture_source=unreal.SceneCaptureSource.SCS_SCENE_DEPTH
SC.fov_angle=15
SC.set_editor_property('LODDistanceFactor',0.01)
print('capture_rotation',C.get_actor_rotation())
SC.capture_every_frame=False;SC.capture_on_movement=False
SC.primitive_render_mode=unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
for c in parts:SC.show_only_component(c)
state=dict(step=0,next=time.monotonic()+1,readings={})
def depth_tick(delta):
    if time.monotonic()<state['next']:return
    s=state['step'];state['step']+=1;state['next']=time.monotonic()+1
    if s==0:SC.capture_scene()
    elif s==1:
        state['readings']['nanite_zero_height']=str(unreal.RenderingLibrary.read_render_target_raw_pixel(W,RT,64,64,False))
        unreal.SystemLibrary.execute_console_command(W,'r.Nanite 0')
    elif s==2:SC.capture_scene()
    elif s==3:
        state['readings']['fallback_zero_height']=str(unreal.RenderingLibrary.read_render_target_raw_pixel(W,RT,64,64,False))
        state['readings']['capture_location']=str(C.get_actor_location())
        state['readings']['capture_rotation']=str(C.get_actor_rotation())
        for c,i,m in old:c.set_material(i,m)
        unreal.SystemLibrary.execute_console_command(W,'r.Nanite 1')
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(C)
        path=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/DepthOriginProbe.json')
        path.write_text(json.dumps(state['readings'],indent=2),encoding='utf-8')
        unreal.unregister_slate_post_tick_callback(DEPTH_HANDLE)
DEPTH_HANDLE=unreal.register_slate_post_tick_callback(depth_tick)
print('DEPTH_PROBE_SCHEDULED')
