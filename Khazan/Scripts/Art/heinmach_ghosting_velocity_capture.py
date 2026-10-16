"""Actual moving-body velocity diagnostics in the owned game, without asset edits."""
import json
import traceback
import unreal
import builtins

pc=unreal.GameplayStatics.get_player_controller(WORLD,0)
pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
lib=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',args=(pc,unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
move=unreal.load_asset('/Game/Input/Locomotion/IA_Move')
base=pawn.get_actor_location()
state=dict(frame=0,done=False,error=None)
parts=[(m,m.get_editor_property('render_custom_depth'),m.get_editor_property('custom_depth_stencil_value')) for m in pawn.get_components_by_class(unreal.SkeletalMeshComponent)]
def cmd(s):unreal.SystemLibrary.execute_console_command(WORLD,s)
for m,_,_ in parts:m.set_render_custom_depth(True);m.set_custom_depth_stencil_value(254)
cmd('r.ScreenPercentage 100');cmd('sg.AntiAliasingQuality 2');cmd('r.TSR.Velocity.WeightClampingSampleCount 2')
def finish(error=None):
    if state['done']:return
    unreal.unregister_slate_post_tick_callback(state['handle'])
    inp.inject_input_vector_for_action(move,unreal.Vector(),[],[])
    cmd('ShowFlag.VisualizeMotionBlur 0');cmd('ShowFlag.VisualizeReprojection 0');cmd('ShowFlag.PostProcessMaterial 1')
    for m,d,s in parts:m.set_render_custom_depth(d);m.set_custom_depth_stencil_value(s)
    state.update(done=True,error=error)
    (OUT/'VelocityCapture.json').write_text(json.dumps({k:v for k,v in state.items() if k!='handle'},indent=2),encoding='utf-8')
def tick(delta):
    try:
        f=state['frame'];state['frame']+=1
        inp.inject_input_vector_for_action(move,unreal.Vector(0,1 if f<65 else -1,0),[],[])
        if f==30:cmd('ShowFlag.VisualizeMotionBlur 1')
        if f==40:cmd('Shot filename="'+str(OUT/'moving_velocity.png')+'" -nosuffix')
        if f==50:cmd('ShowFlag.VisualizeMotionBlur 0');cmd('ShowFlag.VisualizeReprojection 1')
        if f==60:cmd('Shot filename="'+str(OUT/'moving_reprojection.png')+'" -nosuffix')
        if f==70:cmd('ShowFlag.VisualizeReprojection 0');cmd('ShowFlag.PostProcessMaterial 0')
        if f==80:cmd('Shot filename="'+str(OUT/'moving_no_regional_pp.png')+'" -nosuffix')
        if f==90:cmd('ShowFlag.PostProcessMaterial 1')
        if f==100:cmd('Shot filename="'+str(OUT/'moving_with_regional_pp.png')+'" -nosuffix')
        if f>=110:finish()
    except Exception:finish(traceback.format_exc())
state['handle']=unreal.register_slate_post_tick_callback(tick)
builtins._heinmach_velocity_capture=state
print('Velocity capture registered')
