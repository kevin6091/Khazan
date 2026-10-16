"""Actual standalone viewport cards; no Editor viewport screenshot ambiguity."""
from pathlib import Path
import json,os,time,traceback
import unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']);OUT=Path(os.environ['KZ_ALPHA_OUT'])
plan=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
R={'status':'running','actual_standalone_game':True,'saved_assets':0,'materials':[],'images':[]}
WORLD=CAMERA=None;FRAME=0;START=time.monotonic();BUSY=False;KEEP=[]
def spawn(cls,location,rotation=u.Rotator()):
    tr=u.Transform(location=location,rotation=rotation)
    a=u.GameplayStatics.begin_deferred_actor_spawn_from_class(WORLD,cls,tr,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN)
    return u.GameplayStatics.finish_spawning_actor(a,tr)
def finish(error=None):
    u.unregister_slate_post_tick_callback(HANDLE);R['status']='failed' if error else 'passed'
    if error:R['error']=error
    (OUT/'Cards.json').write_text(json.dumps(R,indent=2),encoding='utf-8');u.SystemLibrary.execute_console_command(WORLD,'QUIT')
def tick(delta):
    global WORLD,CAMERA,FRAME,BUSY
    if BUSY:return
    BUSY=True
    try:
        if time.monotonic()-START>240:finish('Standalone cards watchdog');return
        if WORLD is None:
            WORLD=u.load_object(None,'/Game/__ParticleAlphaQA/L_AlphaCards_Inspection.L_AlphaCards_Inspection')
            if not WORLD:return
            pc=u.GameplayStatics.get_player_controller(WORLD,0)
            if not pc:WORLD=None;return
            for pawn in u.GameplayStatics.get_all_actors_of_class(WORLD,u.Pawn):
                pawn.set_actor_hidden_in_game(True);pawn.set_actor_tick_enabled(False)
                cm=pawn.get_component_by_class(u.CharacterMovementComponent)
                if cm:cm.set_movement_mode(u.MovementMode.MOVE_NONE)
            CAMERA=next(a for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.CameraActor) if a.get_actor_label()=='AlphaQA_Camera')
            cam=CAMERA.get_component_by_class(u.CameraComponent);cam.set_editor_property('field_of_view',55)
            pp=cam.get_editor_property('post_process_settings')
            for k,v in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),('bloom_intensity',0.)]:
                pp.set_editor_property(k,v);pp.set_editor_property('override_'+k,True)
            cam.set_editor_property('post_process_settings',pp);cam.set_editor_property('post_process_blend_weight',1.)
            pc.set_view_target_with_blend(CAMERA,0.);KEEP.append(CAMERA)
            for i,path in enumerate([plan['default_particle']]+[r['material'] for r in plan['rows']]):
                mat=u.load_asset(path);assert mat,path
                R['materials'].append({'index':i,'path':path})
            u.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
        FRAME+=1
        if FRAME in (120,150):
            p=u.GameplayStatics.get_player_camera_manager(WORLD,0);R['camera']=[str(p.get_camera_location()),str(p.get_camera_rotation())]
            file=OUT/('Cards_'+str(FRAME)+'.png');u.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(file)+'" -nosuffix');R['images'].append(str(file))
        if FRAME>=180:finish()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
HANDLE=u.register_slate_post_tick_callback(tick)
