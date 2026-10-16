"""Actual game viewport fire playback/route captures; no asset or config saves."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'/('MainPreview' if ROOT==MAIN else 'Preview')
OUT.mkdir(parents=True,exist_ok=True)
START=time.monotonic();HANDLE=None;WORLD=CAMERA=PC=PAWN=None;FRAME=INDEX=0
VIEWS=[('StartTorch',[11804.88,13739.409,172.42337],500.,-45.),
       ('TutorialBrazier',[14700.,9675.,610.],550.,145.),
       ('StoneBrazier',[12483.195,15558.151,252.17082],350.,75.),
       ('CaveFire',[30633.258,3011.5623,-1929.4939],350.,190.),
       ('CaveWood',[33625.293,6117.3027,-1924.9999],600.,-90.),
       ('EscapeFire',[5168.754,-5719.592,-4895.2124],350.,40.)]
REPORT={'views':[],'actual_game_viewport':True,'saved_assets':False,'render_settings':{'resolution':[1280,720],'fps_cap':30,'aa':'TSR'},'frame_seconds':[]}


def configure():
    name,p,d,yaw=VIEWS[INDEX]
    import math
    target=unreal.Vector(p[0],p[1],p[2]+85)
    particles=[a.get_component_by_class(unreal.ParticleSystemComponent) for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.Emitter) if 'KZHeinMachTutorialFire' in [str(t) for t in a.tags]]
    nearby=min((c for c in particles if c.template.get_name()!='FP_FireDust_001'),key=lambda c:c.get_world_location().distance(target))
    if name in ('StoneBrazier','CaveFire','EscapeFire'):
        target=nearby.get_world_location()+unreal.Vector(0,0,15);p=[target.x,target.y,target.z-85];d=150
    a=math.radians(yaw);position=[p[0]-math.cos(a)*d,p[1]-math.sin(a)*d,p[2]+160]
    rotation=unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*position),target)
    CAMERA.set_world_location(unreal.Vector(*position),False,False);CAMERA.set_world_rotation(rotation,False,False)
    REPORT['views'].append({'name':name,'camera':position,'target':[target.x,target.y,target.z],'frames':[],'component':nearby.get_path_name()})


def finish(error=None):
    REPORT['passed']=not error
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'Playback.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HM_FIRES_CAPTURE_PASSED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,CAMERA,PC,PAWN,FRAME,INDEX
    try:
        if time.monotonic()-START>600:finish('Capture timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment');assert WORLD
            PC=unreal.GameplayStatics.get_player_controller(WORLD,0);PAWN=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            PC.set_ignore_look_input(True);PC.set_ignore_move_input(True);PC.disable_input(PC);PAWN.disable_input(PC)
            CAMERA=next(c for c in PAWN.get_components_by_class(unreal.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation',False)
            for command in ('t.MaxFPS 30','r.ScreenPercentage 100','r.AntiAliasingMethod 4'):
                unreal.SystemLibrary.execute_console_command(WORLD,command)
            configure()
        if time.monotonic()-START<12:return
        FRAME+=1
        if FRAME>45:REPORT['frame_seconds'].append(delta)
        if FRAME in (60,90):
            name=VIEWS[INDEX][0];path=OUT/(name+'_'+str(FRAME)+'.png')
            unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(path)+'" -nosuffix')
            REPORT['views'][-1]['frames'].append(str(path))
            comp=unreal.load_object(None,REPORT['views'][-1]['component'])
            REPORT['views'][-1].setdefault('live_particle_samples',[]).append({'frame':FRAME,'active':comp.is_active(),'particles':comp.get_num_active_particles()})
            assert comp.is_active() and comp.get_num_active_particles()>0,'Inactive core flame at '+name
        if FRAME==96:
            INDEX+=1;FRAME=0
            if INDEX==len(VIEWS):finish();return
            configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
