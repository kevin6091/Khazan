"""Transient game playback probe: live counts and isolated core-fire frames."""
from pathlib import Path
import json
import time
import traceback
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006/Probe'
OUT.mkdir(parents=True,exist_ok=True)
START=time.monotonic();HANDLE=None;WORLD=CAMERA=COMP=None;FRAME=0
REPORT={'snapshots':[],'saved_assets':False}

def finish(error=None):
    REPORT['error']=error
    (OUT/'Runtime.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    if error:unreal.log_error(error)
    else:print('KZ_HM_FIRES_PLAYBACK_PROBE_PASSED')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')

def tick(delta):
    global WORLD,CAMERA,COMP,FRAME
    try:
        if time.monotonic()-START>200:finish('Probe timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0);pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            pc.set_ignore_look_input(True);pc.set_ignore_move_input(True);pawn.disable_input(pc)
            CAMERA=next(c for c in pawn.get_components_by_class(unreal.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation',False)
            ps=[a.get_component_by_class(unreal.ParticleSystemComponent) for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.Emitter) if 'KZHeinMachTutorialFire' in [str(t) for t in a.tags]]
            COMP=min((c for c in ps if 'fire_small' in c.template.get_name()),key=lambda c:c.get_world_location().distance(unreal.Vector(14700,9675,650)))
            p=COMP.get_world_location();position=p+unreal.Vector(250,-200,110);target=p+unreal.Vector(0,0,20)
            CAMERA.set_world_location(position,False,False);CAMERA.set_world_rotation(unreal.MathLibrary.find_look_at_rotation(position,target),False,False)
            REPORT.update(component=COMP.get_path_name(),location=[p.x,p.y,p.z],parameters=[p.export_text() for p in COMP.get_editor_property('instance_parameters')],initial_system_states=[{'component':c.get_path_name(),'active':c.is_active(),'particles':c.get_num_active_particles()} for c in ps])
            for command in ('t.MaxFPS 30','r.ScreenPercentage 100','r.AntiAliasingMethod 4'):unreal.SystemLibrary.execute_console_command(WORLD,command)
        FRAME+=1
        if FRAME in (1,5,30,60,120,130,150,180):
            REPORT['snapshots'].append({'frame':FRAME,'active':COMP.is_active(),'particle_count':COMP.get_num_active_particles(),'tick_enabled':COMP.is_component_tick_enabled(),'auto_activate':COMP.get_editor_property('auto_activate'),'detail_mode':str(COMP.get_editor_property('detail_mode')),'global_detail_mode':unreal.SystemLibrary.get_console_variable_int_value('r.DetailMode')})
        if FRAME in (60,120,180):
            unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(OUT/('frame_'+str(FRAME)+'.png'))+'" -nosuffix')
        if FRAME==125:
            # Diagnostic only: the saved template, instances, and map are untouched.
            COMP.deactivate();COMP.activate(True)
            for name in ('core_fire','smoke_3','fire_1','fire_2','Fire_ember','for LOD','smoke_1','smoke_2'):
                COMP.set_emitter_enable(name,name=='core_fire')
            REPORT['isolated_core_from_frame']=125
        if FRAME==151:
            COMP.set_template(COMP.template);COMP.activate(True)
            unreal.SystemLibrary.execute_console_command(WORLD,'log LogParticles VeryVerbose')
        if FRAME==190:
            assert COMP.is_active() and COMP.get_num_active_particles()>0,'Core flame failed to remain active'
            finish()
    except Exception:finish(traceback.format_exc())

HANDLE=unreal.register_slate_post_tick_callback(tick)
