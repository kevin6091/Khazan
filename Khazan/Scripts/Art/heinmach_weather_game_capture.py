"""Read actual game viewport frames offscreen, with no editor/map writes."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachWeather_20261006'
START=time.monotonic()
HANDLE=None
FRAMES=0
REPORT={'background':True,'standalone_game':True,'saved_assets_modified':False}
WORLD=None
SNOW=None
SOURCE_ASSET=None
QA_CAMERA=None

def shot(name):
    target=OUT/(name+'.png')
    unreal.SystemLibrary.execute_console_command(WORLD,'HighResShot 1280x720 filename="'+str(target)+'"')
    REPORT.setdefault('images',[]).append(str(target))

def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (META/'GameViewportVerification.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')

def tick(delta):
    global WORLD,FRAMES,SNOW,SOURCE_ASSET,QA_CAMERA
    try:
        if time.monotonic()-START<10:return
        if time.monotonic()-START>300:finish('Offscreen game verification timeout.');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            assert WORLD
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            unreal.SystemLibrary.execute_console_command(WORLD,'r.GPUCsvStatsEnabled 1')
            unreal.SystemLibrary.execute_console_command(WORLD,'fx.DetailedCSVStats 1')
            REPORT['world']=WORLD.get_path_name()
        FRAMES+=1
        if FRAMES==180:
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0)
            if pcm:
                p=pcm.get_camera_location();r=pcm.get_camera_rotation()
                REPORT['camera_location']=[p.x,p.y,p.z];REPORT['camera_rotation']=[r.pitch,r.yaw,r.roll]
            REPORT['game_actors']=len(unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.Actor))
            actors=unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor)
            SNOW=next(a for a in actors if a.get_actor_label()=='HM_Environment_SourceSnow').get_component_by_class(unreal.NiagaraComponent)
            SOURCE_ASSET=SNOW.get_asset()
            cache=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(WORLD)
            unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,unreal.NiagaraSimCacheCreateParameters(),SNOW)
            REPORT['particle_count']=len(cache.read_position_attribute(emitter_name='Source_Flakes_Fast_Large'))
            REPORT['dust_particle_count']=len(cache.read_position_attribute(emitter_name='Source_Dust'))
            REPORT['dust_positions']=[[v.x,v.y,v.z] for v in cache.read_position_attribute(emitter_name='Source_Dust')[:5]]
            shot('GameViewport_Source')
        if FRAMES==240:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STARTFILE=HM_Snow_On_20261006.csv')
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile START')
        if FRAMES==420:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STOP')
            SNOW.set_asset(None)
        if FRAMES==540:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STARTFILE=HM_Snow_Off_20261006.csv')
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile START')
        if FRAMES==720:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STOP')
            shot('GameViewport_SnowOff')
        if FRAMES==780:
            SNOW.set_asset(SOURCE_ASSET);SNOW.activate(True)
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0)
            rotation=pc.get_control_rotation()
            pc.set_control_rotation(unreal.Rotator(pitch=35,yaw=rotation.yaw,roll=0))
            REPORT['sky_camera_is_unsaved']=True
        if FRAMES==960:shot('GameViewport_Sky')
        if FRAMES==1020:
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0)
            pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            QA_CAMERA=pawn.get_component_by_class(unreal.CameraComponent)
            assert QA_CAMERA
            p=pcm.get_camera_location();r=pcm.get_camera_rotation()
            QA_CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            QA_CAMERA.set_editor_property('use_pawn_control_rotation',False)
            QA_CAMERA.set_world_location(p+unreal.Vector(0,0,3000),False,False)
            QA_CAMERA.set_world_rotation(unreal.Rotator(pitch=15,yaw=r.yaw,roll=0),False,False)
            REPORT['extra_view_contract']='Transient existing player camera detached; QA height offset 3000cm, not a source gameplay camera.'
        if FRAMES==1200:
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0)
            p=pcm.get_camera_location();REPORT['open_sky_camera']=[p.x,p.y,p.z]
            shot('GameViewport_OpenSky')
        if FRAMES==1260:
            cave=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume) if a.get_actor_label()=='HM_Environment_PP_HeinMach_Light_213')
            p=cave.get_actor_bounds(False)[0]
            QA_CAMERA.set_world_location(p,False,False)
            QA_CAMERA.set_world_rotation(unreal.Rotator(pitch=-8,yaw=-115,roll=0),False,False)
            REPORT['cave_probe_camera']=[p.x,p.y,p.z]
            REPORT['cave_probe_contract']='Original cave brush bounds center; visibility/volume probe, not a source gameplay camera.'
        if FRAMES==1440:shot('GameViewport_CaveProbe')
        if FRAMES>=1500:finish()
    except Exception:finish(traceback.format_exc())

HANDLE=unreal.register_slate_post_tick_callback(tick)
