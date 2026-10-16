"""Transient actual-input/ABP motion A/B in the owned ghosting game process.

Invoke with runpy.run_path(..., init_globals={'WORLD': WORLD, 'OUT': OUT}).
Registers a callback and returns immediately. No C++ or asset authoring.
All frame counts, input pulses and camera offsets are QA fixtures.
"""
from pathlib import Path
import builtins
import datetime
import json
import math
import os
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert ROOT==MAIN/'Saved/ArtStaging/HeinMachGhosting_20261008'
WORLD=globals().get('WORLD')
OUT=Path(globals().get('OUT',MAIN/'Saved/ImportReports/HeinMachGhosting_20261008'))
assert WORLD and unreal.GameplayStatics.get_player_pawn(WORLD,0)
ready=json.loads((OUT/'Mailbox/Ready.json').read_text(encoding='utf-8'))
assert ready['pid']==os.getpid(),'Only the current owned game mailbox may capture'
previous=getattr(builtins,'_heinmach_ghost_capture',None)
assert not previous or previous['done'],'A motion capture is already active'

PC=unreal.GameplayStatics.get_player_controller(WORLD,0)
PAWN=unreal.GameplayStatics.get_player_pawn(WORLD,0)
MESH=PAWN.get_editor_property('mesh')
assert MESH.get_anim_instance(),'Capture requires the actual player ABP'
CAMERA=next(c for c in PAWN.get_components_by_class(unreal.CameraComponent) if c.is_active())
LIBRARY=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
INPUT=LIBRARY.call_method('GetLocalPlayerSubSystemFromPlayerController',
    args=(PC,unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
assert INPUT
ACTIONS={key:unreal.load_asset(path) for key,path in {
    'move':'/Game/Input/Locomotion/IA_Move',
    'sprint':'/Game/Input/Locomotion/IA_Sprint',
    'attack':'/Game/Input/IA_WeakAttack',
    'dodge':'/Game/Input/IA_Dodge'}.items()}
assert all(ACTIONS.values())
ORIGIN=PAWN.get_actor_location();ROTATION=PAWN.get_actor_rotation()
CONTROL_ROTATION=PC.get_control_rotation()
CAMERA_WORLD=CAMERA.get_world_transform()
CAMERA_RELATIVE=CAMERA.get_relative_transform()
CAMERA_PARENT=CAMERA.get_attach_parent();CAMERA_SOCKET=CAMERA.get_attach_socket_name()
CAMERA_CONTROL=CAMERA.get_editor_property('use_pawn_control_rotation')
PARTS=[(c,bool(c.get_editor_property('render_custom_depth')),int(c.get_editor_property('custom_depth_stencil_value')))
       for c in PAWN.get_components_by_class(unreal.SkeletalMeshComponent)]

VARIANTS=globals().get('CAPTURE_VARIANTS',[
    dict(name='Baseline_87_AA2_Count4',screen=87,aa=2,count=4,all_parts_stencil=False),
    dict(name='Native_100_AA2_Count4',screen=100,aa=2,count=4,all_parts_stencil=False),
    dict(name='Native_100_AA2_Count2',screen=100,aa=2,count=2,all_parts_stencil=False),
    dict(name='Native_100_AA3_Count2',screen=100,aa=3,count=2,all_parts_stencil=False),
    dict(name='Native_100_AA3_Count2_AllParts254',screen=100,aa=3,count=2,all_parts_stencil=True)])
CVAR_NAMES=('r.AntiAliasingMethod','sg.ResolutionQuality','r.ScreenPercentage','sg.AntiAliasingQuality',
    'r.TSR.Velocity.WeightClampingSampleCount','r.TSR.History.ScreenPercentage',
    'r.TSR.History.UpdateQuality','r.TSR.RejectionAntiAliasingQuality','r.TSR.History.R11G11B10',
    'r.TSR.ReprojectionField','r.TSR.ShadingRejection.Flickering','r.TSR.Resurrection',
    'r.TemporalAA.Quality','r.FXAA.Quality','t.MaxFPS')
def console(command):unreal.SystemLibrary.execute_console_command(WORLD,command)
def cvars():return {k:unreal.SystemLibrary.get_console_variable_float_value(k) for k in CVAR_NAMES}
ORIGINAL_CVARS=cvars()
RUN_ID=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
RUN=OUT/'Captures'/RUN_ID;RUN.mkdir(parents=True)
STATE=dict(done=False,success=False,index=0,frame=-1,phase='warmup',pid=os.getpid(),session=ready['session'],
    run=str(RUN),handle=None,started=time.monotonic(),direction=1.,images=[],error=None)
REPORT=dict(real_game_viewport=True,highres_screenshot=False,input_route='EnhancedInput action injection -> PlayerController -> CMC/GAS -> actual ABP',
    assets_saved=False,original_cvars=ORIGINAL_CVARS,pid=os.getpid(),session=ready['session'],
    animation_class=MESH.get_anim_instance().get_class().get_path_name(),
    movement_fixture='75 frames; real input along action Y/right, reverses at +/-100 cm from origin',
    camera_fixture='Static player camera, original position +100 cm Z, pitch -8 degrees',
    per_variant_warmup_frames=50,parts_before=[dict(name=c.get_name(),render_custom_depth=d,stencil=s) for c,d,s in PARTS],variants=[])
def write(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8');temporary.replace(path)
def checkpoint():
    write(OUT/'CaptureState.json',{k:v for k,v in STATE.items() if k!='handle'})
    write(RUN/'CaptureMetadata.json',REPORT)
def inject(key,x=0.,y=0.):INPUT.inject_input_vector_for_action(ACTIONS[key],unreal.Vector(x,y,0),[],[])
def release():
    for key in ACTIONS:inject(key)
def reset_pawn():
    release();PAWN.get_editor_property('character_movement').stop_movement_immediately()
    PAWN.set_actor_location(ORIGIN,False,True);PAWN.set_actor_rotation(ROTATION,True)
    PC.set_control_rotation(CONTROL_ROTATION)
def configure():
    variant=VARIANTS[STATE['index']]
    reset_pawn();STATE.update(frame=-1,direction=1.,phase='warmup')
    console('r.AntiAliasingMethod 4');console('sg.AntiAliasingQuality '+str(variant['aa']))
    # Equal history resolution isolates input resolution, moving weight and AA
    # quality; Epic's normal 200% history would otherwise be a second variable.
    console('r.TSR.History.ScreenPercentage 100')
    console('sg.ResolutionQuality '+str(variant['screen']));console('r.ScreenPercentage '+str(variant['screen']))
    console('r.TSR.Velocity.WeightClampingSampleCount '+str(variant['count']))
    console('t.MaxFPS 30')
    for part,depth,stencil in PARTS:
        part.set_custom_depth_stencil_value(254 if variant['all_parts_stencil'] else stencil)
        part.set_render_custom_depth(True if variant['all_parts_stencil'] else depth)
    REPORT['variants'].append(dict(requested=variant,cvars=cvars(),frames=[],images=[],
        movement_observed=False,attack_montage_observed=False))
    checkpoint()
def shot(label):
    row=REPORT['variants'][-1]
    destination=RUN/VARIANTS[STATE['index']]['name'];destination.mkdir(exist_ok=True)
    target=destination/('%03d_%s.png'%(STATE['frame'],label))
    console('Shot filename="'+str(target)+'" -nosuffix')
    row['images'].append(dict(frame=STATE['frame'],phase=STATE['phase'],path=str(target)))
    STATE['images'].append(str(target));checkpoint()
def sample(delta):
    anim=MESH.get_anim_instance();p=PAWN.get_actor_location();v=PAWN.get_velocity()
    montage=anim.get_current_active_montage() if anim else None
    observations={}
    if anim:
        for key in ('GroundSpeed','InputAmount','bHasMovementInput','bIsMoving','bIsStopping','bIsGrounded','LocomotionGait'):
            try:
                value=anim.get_editor_property(key)
                observations[key]=value if isinstance(value,(bool,int,float)) else str(value)
            except Exception as error:observations[key]='unavailable: '+str(error)
    row=dict(frame=STATE['frame'],phase=STATE['phase'],delta_seconds=delta,
        game_seconds=unreal.GameplayStatics.get_time_seconds(WORLD),position=[p.x,p.y,p.z],velocity=[v.x,v.y,v.z],
        anim=observations,montage=montage.get_path_name() if montage else None,cvars=cvars())
    result=REPORT['variants'][-1];result['frames'].append(row)
    if STATE['phase']=='move' and v.length()>1.:result['movement_observed']=True
    if STATE['phase']=='attack' and montage:result['attack_montage_observed']=True
def finish(error=None):
    if STATE['done']:return
    STATE['done']=True;STATE['error']=error
    try:
        release();reset_pawn()
        for part,depth,stencil in PARTS:
            part.set_custom_depth_stencil_value(stencil);part.set_render_custom_depth(depth)
        for key,value in ORIGINAL_CVARS.items():console(key+' '+str(value))
        CAMERA.set_editor_property('use_pawn_control_rotation',CAMERA_CONTROL)
        if CAMERA_PARENT:
            CAMERA.attach_to_component(CAMERA_PARENT,CAMERA_SOCKET,unreal.AttachmentRule.KEEP_WORLD,
                unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
            CAMERA.set_relative_transform(CAMERA_RELATIVE,False,True)
        else:CAMERA.set_world_transform(CAMERA_WORLD,False,True)
    except Exception:
        STATE['cleanup_error']=traceback.format_exc()
    STATE['success']=not error and all(v['movement_observed'] and v['attack_montage_observed'] for v in REPORT['variants'])
    if not error and not STATE['success']:STATE['error']='Actual movement or active attack montage was not observed in every variant'
    REPORT.update(success=STATE['success'],error=STATE['error'],done=True)
    unreal.unregister_slate_post_tick_callback(STATE['handle']);checkpoint()
    print('HEINMACH_GHOST_CAPTURE_DONE',json.dumps({k:v for k,v in STATE.items() if k!='handle'}))
def tick(delta):
    try:
        if time.monotonic()-STATE['started']>600:return finish('Owned capture deadline')
        STATE['frame']+=1;f=STATE['frame']
        if f<50:
            STATE['phase']='warmup';inject('move')
        elif f<125:
            STATE['phase']='move'
            p=PAWN.get_actor_location();yaw=math.radians(CONTROL_ROTATION.yaw)
            offset=-(p.x-ORIGIN.x)*math.sin(yaw)+(p.y-ORIGIN.y)*math.cos(yaw)
            if offset>100:STATE['direction']=-1.
            elif offset<-100:STATE['direction']=1.
            inject('move',0.,STATE['direction'])
        elif f<141:
            STATE['phase']='stop';inject('move')
        elif f<156:
            STATE['phase']='attack_warmup';inject('move')
            if f==141:reset_pawn()
        elif f<186:
            STATE['phase']='attack';inject('move');inject('attack',1. if f==156 else 0.)
        else:
            STATE['phase']='cooldown';release()
        sample(delta)
        if f in (49,65,78,90,120,125,129,135,140,159,164,173,184):shot(STATE['phase'])
        if f%15==0:checkpoint()
        if f>=199:
            STATE['index']+=1
            if STATE['index']>=len(VARIANTS):return finish()
            configure()
    except Exception:finish(traceback.format_exc())

CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
CAMERA.set_editor_property('use_pawn_control_rotation',False)
CAMERA.set_world_location(unreal.Vector(CAMERA_WORLD.translation.x,CAMERA_WORLD.translation.y,CAMERA_WORLD.translation.z+100),False,True)
CAMERA.set_world_rotation(unreal.Rotator(-8.,CONTROL_ROTATION.yaw,0.),False,True)
configure()
STATE['handle']=unreal.register_slate_post_tick_callback(tick)
builtins._heinmach_ghost_capture=STATE
print('HEINMACH_GHOST_CAPTURE_REGISTERED',str(RUN))
