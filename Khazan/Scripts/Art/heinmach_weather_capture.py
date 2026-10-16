"""Unsaved SceneCapture QA in a hidden real-RHI editor; never drives Rider."""
from pathlib import Path
import json
import math
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
OUT = ROOT / 'Saved/ImportReports/HeinMachWeather_20261006'
OUT.mkdir(parents=True, exist_ok=True)
STAGE = 'Final'
START = time.monotonic()
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
HANDLE = None
CAPTURE = None
CAMERAS = []
INDEX = -1
FRAME_COUNT = 0
REPORT = {'stage':STAGE, 'real_RHI':True, 'background_process':True, 'captures':[],
          'camera_contract':'QA views derived from preserved PlayerStart; offset/FOV are authoring choices, not original gameplay camera.'}
SNOW = None
SIMULATION_REQUESTED=False
GAME_CAMERA=None


def setup():
    global CAPTURE, CAMERAS, SNOW
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world and world.get_path_name().startswith('/Game/Maps/L_HeinMach_Environment')
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    start = next(a for a in ac.get_all_level_actors() if a.get_actor_label()=='HM_Tutorial_PlayerStart_DualAxeSword')
    p, r = start.get_actor_location(), start.get_actor_rotation()
    yaw = math.radians(r.yaw)
    eye = unreal.Vector(p.x-250*math.cos(yaw),p.y-250*math.sin(yaw),p.z+180)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(eye,unreal.Rotator(pitch=-8,yaw=r.yaw,roll=0))
    CAMERAS = [('StartRoute',eye,unreal.Rotator(pitch=-8,yaw=r.yaw,roll=0)),
               ('StartSky',eye,unreal.Rotator(pitch=25,yaw=r.yaw,roll=0)),
               ('OpenSky',eye+unreal.Vector(0,0,3000),unreal.Rotator(pitch=15,yaw=r.yaw,roll=0)),
               ('WindView',eye+unreal.Vector(0,0,3000),unreal.Rotator(pitch=-15,yaw=-60,roll=0))]
    cave=next(a for a in ac.get_all_level_actors() if a.get_actor_label()=='HM_Environment_PP_HeinMach_Light_213')
    cave_eye=cave.get_actor_bounds(False)[0]
    CAMERAS.append(('CaveBoundsProbe',cave_eye,unreal.Rotator(pitch=-8,yaw=r.yaw,roll=0)))
    # Camera pose is transient. Do not save this world.
    CAPTURE = ac.spawn_actor_from_class(unreal.SceneCapture2D,eye)
    CAPTURE.set_actor_label('HM_WeatherQA_Capture')
    qa_camera=ac.spawn_actor_from_class(unreal.CameraActor,eye)
    qa_camera.set_actor_label('HM_WeatherQA_Camera')
    qa_camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view',65.0)
    c = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
    target = unreal.RenderingLibrary.create_render_target2d(world,1280,720,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    c.set_editor_property('texture_target',target)
    c.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property('capture_every_frame',False)
    c.set_editor_property('always_persist_rendering_state',True)
    c.set_editor_property('fov_angle',65.0)
    c.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name='SeparateTranslucency',enabled=True),unreal.EngineShowFlagsSetting(show_flag_name='PostProcessMaterial',enabled=True)])
    pp=c.get_editor_property('post_process_settings')
    pp.set_editor_property('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN)
    pp.set_editor_property('override_dynamic_global_illumination_method',True)
    pp.set_editor_property('reflection_method',unreal.ReflectionMethod.LUMEN)
    pp.set_editor_property('override_reflection_method',True)
    c.set_editor_property('post_process_settings',pp)
    c.set_editor_property('post_process_blend_weight',1.0)
    # Whole-scene warmup and continuous capture permit texture/eye adaptation.
    unreal.SystemLibrary.execute_console_command(world,'r.ShaderPipelineCache.Enabled 0')
    unreal.SystemLibrary.execute_console_command(world,'t.MaxFPS 30')
    return c


def finish(error=None):
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (META / (STAGE + 'Visual.json')).write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.SystemLibrary.quit_editor()


def on_tick(delta_seconds):
    global INDEX, FRAME_COUNT, CAPTURE, SIMULATION_REQUESTED, GAME_CAMERA, SNOW
    try:
        if time.monotonic()-START > 240:
            finish('QA process timing limit; not a gameplay limit.')
            return
        if time.monotonic()-START < 12:
            return
        if not SIMULATION_REQUESTED:
            setup()
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            SIMULATION_REQUESTED=True
            CAPTURE=None
            return
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:return
        if CAPTURE is None:
            actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
            by={a.get_actor_label():a for a in actors}
            CAPTURE=by['HM_WeatherQA_Capture']
            GAME_CAMERA=by['HM_WeatherQA_Camera']
            SNOW=by['HM_Environment_SourceSnow'].get_component_by_class(unreal.NiagaraComponent)
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            if pc:pc.set_view_target_with_blend(GAME_CAMERA,0.0)
            REPORT['simulation_world']=world.get_path_name()
            REPORT['serialized_snow_auto_activation_observed']=SNOW.is_active()
            REPORT['Lumen_capture_opt_in']=True
            REPORT['snow_component']={}
            for f in ('visible','hidden_in_game','rendering_enabled','auto_activate','cast_shadow'):
                try:REPORT['snow_component'][f]=str(SNOW.get_editor_property(f))
                except:pass
        c = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        # This background PIE world ticks normally. No force-solo/manual tick
        # override is used: verify the actual serialized runtime behavior.
        c.capture_scene()
        if INDEX == -1:
            INDEX = 0
            name,p,r = CAMERAS[INDEX]
            CAPTURE.set_actor_location(p,False,False)
            CAPTURE.set_actor_rotation(r,False)
            GAME_CAMERA.set_actor_location(p,False,False)
            GAME_CAMERA.set_actor_rotation(r,False)
            return
        FRAME_COUNT += 1
        if FRAME_COUNT < 180:
            return
        name,p,r = CAMERAS[INDEX]
        c.capture_scene()
        filename = STAGE+'_'+name+'.png'
        unreal.RenderingLibrary.export_render_target(world,c.get_editor_property('texture_target'),str(OUT),filename)
        REPORT['captures'].append({'name':name,'image':str(OUT/filename),'location':[p.x,p.y,p.z],
                                   'rotation':[r.pitch,r.yaw,r.roll], 'warmup_frames':FRAME_COUNT})
        try:
            cache=unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(world)
            result=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,unreal.NiagaraSimCacheCreateParameters(),SNOW)
            particles=cache.read_position_attribute(emitter_name='Source_Flakes_Fast_Large')
            REPORT['captures'][-1]['snow_particles_observed']=len(particles)
            REPORT['captures'][-1]['snow_position_sample']=[[v.x,v.y,v.z] for v in particles[:8]]
            sizes=cache.read_vector2_attribute(attribute_name='SpriteSize',emitter_name='Source_Flakes_Fast_Large')
            REPORT['captures'][-1]['snow_size_sample']=[[v.x,v.y] for v in sizes[:8]]
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            pcm=unreal.GameplayStatics.get_player_camera_manager(world,0)
            if pcm:
                cp=pcm.get_camera_location()
                REPORT['captures'][-1]['player_camera_location']=[cp.x,cp.y,cp.z]
                REPORT['captures'][-1]['player_view_target']=str(pc.get_view_target())
        except Exception as error:
            REPORT['captures'][-1]['sim_cache_diagnostic']=str(error)
        INDEX += 1
        if INDEX == len(CAMERAS):
            finish()
            return
        FRAME_COUNT = 0
        name,p,r = CAMERAS[INDEX]
        CAPTURE.set_actor_location(p,False,False)
        CAPTURE.set_actor_rotation(r,False)
        GAME_CAMERA.set_actor_location(p,False,False)
        GAME_CAMERA.set_actor_rotation(r,False)
    except Exception:
        finish(traceback.format_exc())


HANDLE = unreal.register_slate_post_tick_callback(on_tick)
