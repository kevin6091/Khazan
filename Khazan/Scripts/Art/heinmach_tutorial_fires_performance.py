"""Sequential fire/lights on-off-on GPU CSV comparison; no package saves."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'
START=time.monotonic();HANDLE=None;WORLD=None;PARTICLES=[];LIGHTS=[];FRAME=INDEX=0
VARIANTS=['FireOn1','FireOff','FireOn2']
REPORT={'variants':[],'saved_assets':False,'resolution':[1280,720],'aa':'TSR','warmup_frames':200,'sample_frames':200,
        'limits':'Development/offscreen with the user editor concurrently running; other Pawns/AI frozen only in this probe. Sequential incremental cost, not production FPS guarantee.'}

def configure():
    enabled=VARIANTS[INDEX]!='FireOff'
    for comp,asset in PARTICLES:
        comp.set_template(asset if enabled else None)
        if enabled:comp.activate(True)
    for light in LIGHTS:light.set_visibility(enabled)
    REPORT['variants'].append({'name':VARIANTS[INDEX],'light_count':len(LIGHTS),'system_count':len(PARTICLES)})

def finish(error=None):
    REPORT['passed']=not error
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'PerformanceCapture.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HM_FIRES_PERFORMANCE_PASSED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')

def tick(delta):
    global WORLD,FRAME,INDEX,PARTICLES,LIGHTS
    try:
        if time.monotonic()-START>600:finish('Performance timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0);pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            pc.set_ignore_look_input(True);pc.set_ignore_move_input(True);pawn.disable_input(pc)
            camera=next(c for c in pawn.get_components_by_class(unreal.CameraComponent) if c.is_active())
            camera.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            camera.set_editor_property('use_pawn_control_rotation',False)
            p=unreal.Vector(11451.327,14092.962,332.42337);target=unreal.Vector(11804.88,13739.409,257.42337)
            camera.set_world_location(p,False,False);camera.set_world_rotation(unreal.MathLibrary.find_look_at_rotation(p,target),False,False)
            # Keep moving AI and their shadow invalidation out of the comparison.
            # This affects only this unsaved profiling process.
            for actor in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.Pawn):
                controller=actor.get_controller()
                if controller and isinstance(controller,unreal.AIController):controller.stop_movement()
                actor.set_actor_tick_enabled(False)
                for component in actor.get_components_by_class(unreal.ActorComponent):component.set_component_tick_enabled(False)
                movement=actor.get_component_by_class(unreal.CharacterMovementComponent)
                if movement:movement.stop_movement_immediately()
            for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.Actor):
                if 'KZHeinMachTutorialFire' not in [str(t) for t in a.tags]:continue
                c=a.get_component_by_class(unreal.ParticleSystemComponent)
                if c:PARTICLES.append((c,c.template))
                c=a.get_component_by_class(unreal.PointLightComponent)
                if c:LIGHTS.append(c)
            assert len(PARTICLES)==95 and len(LIGHTS)==100
            for command in ('t.MaxFPS 30','r.ScreenPercentage 100','r.AntiAliasingMethod 4','r.GPUCsvStatsEnabled 1','fx.DetailedCSVStats 1'):
                unreal.SystemLibrary.execute_console_command(WORLD,command)
            configure()
        if time.monotonic()-START<12:return
        FRAME+=1
        if FRAME==200:
            filename='HM_TutorialFires_'+VARIANTS[INDEX]+'_20261006.csv'
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STARTFILE='+filename)
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile START')
            REPORT['variants'][-1]['csv']=str(ROOT/'Saved/Profiling/CSV'/filename)
            REPORT['variants'][-1]['live_particles']=sum(c.get_num_active_particles() for c,_ in PARTICLES)
        if FRAME==400:unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STOP')
        if FRAME==410:
            INDEX+=1;FRAME=0
            if INDEX==len(VARIANTS):finish()
            else:configure()
    except Exception:finish(traceback.format_exc())

HANDLE=unreal.register_slate_post_tick_callback(tick)
