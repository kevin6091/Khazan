"""Actual PS simulation/viewport on eight representative affected effect families."""
from pathlib import Path
import json,os,time,traceback
import unreal as u
OUT=Path(os.environ['KZ_ALPHA_OUT']);START=time.monotonic();WORLD=CAMERA=PSC=None;FRAME=0;INDEX=-1;BUSY=False;WARM=0
PATHS=['/Game/_Art/Effects/Combat/Shared/P_kazan_charge_start',
 '/Game/_Art/Effects/Combat/GuardParry/PP_AtkEx_Parry',
 '/Game/_Art/Effects/Monsters/ApesYetuga/FP_Boss_Yetuga_PartGroggy_blood_01',
 '/Game/_Art/Effects/Monsters/Human/FP_DeathEffect',
 '/Game/_Art/Effects/Monsters/Human/P_bladepierce_large',
 '/Game/_Art/Effects/Monsters/Human/PP_W_Dust_Front',
 '/Game/_Art/Effects/Combat/Shared/FP_breath_Small',
 '/Game/_Art/Effects/DualAxeSword/Core/FP_Kazan_Dualaxesword_flow_charge_01']
R={'status':'running','actual_standalone_game':True,'asset_saves':0,'effects':[],'scope':'Representative actual particle simulation and alpha appearance; no gameplay hit/ability behavior test.'}
def finish(error=None):
    u.unregister_slate_post_tick_callback(HANDLE);R['status']='failed' if error else 'passed'
    if error:R['error']=error
    (OUT/'Effects.json').write_text(json.dumps(R,indent=2),encoding='utf-8');u.SystemLibrary.execute_console_command(WORLD,'QUIT')
def next_effect():
    global PSC,INDEX,FRAME
    if PSC:PSC.destroy_component(PSC)
    INDEX+=1;FRAME=0
    if INDEX>=len(PATHS):finish();return
    a=u.load_asset(PATHS[INDEX]);assert a,PATHS[INDEX]
    PSC=u.GameplayStatics.spawn_emitter_at_location(WORLD,a,u.Vector(0,0,100),auto_destroy=False);assert PSC
    R['effects'].append({'path':PATHS[INDEX],'frames':[]})
def tick(delta):
    global WORLD,CAMERA,FRAME,WARM,BUSY
    if BUSY:return
    BUSY=True
    try:
        if time.monotonic()-START>360:finish('Effects watchdog');return
        if WORLD is None:
            WORLD=u.load_object(None,'/Game/__ParticleAlphaQA/L_AlphaCards_Inspection.L_AlphaCards_Inspection')
            if not WORLD:return
            pc=u.GameplayStatics.get_player_controller(WORLD,0)
            if not pc:WORLD=None;return
            for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.Pawn):a.set_actor_hidden_in_game(True)
            for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.StaticMeshActor):
                if a.get_actor_label().startswith('AlphaQA_Card_'):a.set_actor_hidden_in_game(True)
            CAMERA=next(a for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.CameraActor) if a.get_actor_label()=='AlphaQA_Camera')
            CAMERA.set_actor_location(u.Vector(400,-600,400),False,False);CAMERA.set_actor_rotation(u.Rotator(pitch=-22.6,yaw=123.69),False)
            pc.set_view_target_with_blend(CAMERA,0);u.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
        if INDEX<0:
            WARM+=1
            if WARM<100:return
            next_effect();return
        FRAME+=1
        if FRAME in (6,18,36):
            file=OUT/('Effect_'+str(INDEX)+'_'+str(FRAME)+'.png');u.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(file)+'" -nosuffix')
            R['effects'][-1]['frames'].append({'frame':FRAME,'particles':PSC.get_num_active_particles(),'image':str(file)})
        if FRAME>=55:next_effect()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
HANDLE=u.register_slate_post_tick_callback(tick)
