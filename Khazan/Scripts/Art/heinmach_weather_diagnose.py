"""Unsaved native-renderer A/B and Niagara world tick evidence."""
from pathlib import Path
import json
import math
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
OUT = ROOT/'Saved/ImportReports/HeinMachWeather_20261006'
world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
START = time.monotonic()
SIMULATION_REQUESTED = False
HANDLE = None
CAPTURE = None
COUNT = 0
INDEX = 0
REPORT = {'unsaved': True, 'native_calibration_choices': True, 'views': []}
CONFIGS = [('ShadowBeforeDOF',8,'shadow_only'),('ShadowBeforeBloom',8,'shadow_bloom')]

def configure(c):
    name, ev, kind = CONFIGS[INDEX]
    c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_NORMAL if kind == 'normal' else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    if kind != 'normal':
        for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.PostProcessVolume):
            if not isinstance(a, unreal.PostProcessVolume):
                continue
            s = a.get_editor_property('settings')
            if kind != 'source':
                s.set_editor_property('weighted_blendables',unreal.WeightedBlendables(array=[]))
            for f in ['color_saturation','color_saturation_shadows','color_saturation_midtones','color_saturation_highlights',
                      'color_contrast','color_contrast_shadows','color_contrast_midtones','color_contrast_highlights',
                      'color_gain','color_gain_shadows','color_gain_midtones','color_gain_highlights',
                      'color_gamma','color_gamma_shadows','color_gamma_midtones','color_gamma_highlights',
                      'color_offset','color_offset_shadows','color_offset_midtones','color_offset_highlights','scene_color_tint',
                      'film_slope','film_toe','film_shoulder','ambient_occlusion_intensity']:
                if kind != 'source':s.set_editor_property('override_'+f, False)
            for f, v in [('auto_exposure_min_brightness',ev),('auto_exposure_max_brightness',ev),('auto_exposure_bias',0)]:
                s.set_editor_property(f,v)
                s.set_editor_property('override_'+f, True)
            a.set_editor_property('settings',s)
        if kind in ('native_parent','shadow_only','shadow_bloom'):
            m=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/M_HM_RegionalLook')
            REPORT.setdefault('instance_parameters',{})
            for key in ('OP','Blizzard1'):
                mi=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/MI_HM_RegionalLook_'+key)
                REPORT['instance_parameters'][key]={n:unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,n) for n in ('CharacterStencil','HM_SkyRadiance','HM_SourceShadowBrightness','HM_SourceShadowAmbient','HM_NativeShadowFillScale','HazeWeight')}
            if kind in ('shadow_only','shadow_bloom'):
                m.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF if kind=='shadow_only' else unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_BLOOM)
                node=next(n for n in unreal.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionCustom))
                node.set_editor_property('code','return HM_BaseColor.rgb*256.0*View.PreExposure;')
                unreal.MaterialEditingLibrary.recompile_material(m)
            pp=c.get_editor_property('post_process_settings')
            pp.set_editor_property('weighted_blendables',unreal.WeightedBlendables(array=[unreal.WeightedBlendable(weight=1,object=m)]))
            c.set_editor_property('post_process_settings',pp)
        if kind in ('skyflag','cube'):
            sky = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.SkyLight) if a.get_actor_label() == 'HM_PreviewSkyLight')
            component=sky.get_component_by_class(unreal.SkyLightComponent)
            component.set_editor_property('intensity',1.0)
            component.set_editor_property('real_time_capture',True)
            component.set_editor_property('lower_hemisphere_is_black',False)
            component.recapture_sky()
            sm=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/M_HM_SourceSky')
            REPORT['original_sky_surface_flag']=sm.get_editor_property('is_sky')
            if kind=='skyflag':
                sm.set_editor_property('is_sky',True)
                unreal.MaterialEditingLibrary.recompile_material(sm)
                component.recapture_sky()
            else:
                component.set_editor_property('real_time_capture',False)
                component.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
                cube=unreal.load_asset('/Engine/EngineResources/GrayTextureCube')
                assert cube,'Missing diagnostic cube'
                component.set_editor_property('cubemap',cube)
                component.set_editor_property('intensity',64.0)
                component.recapture_sky()

def tick(delta):
    global CAPTURE, COUNT, INDEX, world, SIMULATION_REQUESTED
    try:
        if time.monotonic()-START < 12:
            return
        if not SIMULATION_REQUESTED:
            qa=ac.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
            qa.set_actor_label('HM_WeatherQA_Capture')
            unreal.EditorLevelLibrary.editor_play_simulate()
            SIMULATION_REQUESTED=True
            return
        game=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not game:return
        world=game
        if CAPTURE is None:
            actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
            p = next(a for a in actors if a.get_actor_label()=='HM_Tutorial_PlayerStart_DualAxeSword')
            loc, r = p.get_actor_location(), p.get_actor_rotation()
            yaw = math.radians(r.yaw)
            eye = unreal.Vector(loc.x-250*math.cos(yaw),loc.y-250*math.sin(yaw),loc.z+180)
            rot = unreal.Rotator(pitch=-8,yaw=r.yaw,roll=0)
            unreal.EditorLevelLibrary.set_level_viewport_camera_info(eye,rot)
            CAPTURE=next(a for a in actors if a.get_actor_label()=='HM_WeatherQA_Capture')
            CAPTURE.set_actor_location(eye,False,False)
            CAPTURE.set_actor_rotation(rot,False)
            c=CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
            c.set_editor_property('texture_target',unreal.RenderingLibrary.create_render_target2d(world,1280,720,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB))
            c.set_editor_property('always_persist_rendering_state',True)
            c.set_editor_property('capture_every_frame',False)
            c.set_editor_property('fov_angle',65)
            # SceneCaptureRendering.cpp explicitly disables project Lumen for
            # scene captures unless the component itself opts in. QA must use
            # the same indirect lighting as the game before exposure tuning.
            pp=c.get_editor_property('post_process_settings')
            pp.set_editor_property('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN)
            pp.set_editor_property('override_dynamic_global_illumination_method',True)
            pp.set_editor_property('reflection_method',unreal.ReflectionMethod.LUMEN)
            pp.set_editor_property('override_reflection_method',True)
            c.set_editor_property('post_process_settings',pp)
            c.set_editor_property('post_process_blend_weight',1.0)
            REPORT['capture_PP_blend_weight']=c.get_editor_property('post_process_blend_weight')
            REPORT['capture_Lumen_explicit_opt_in']=True
            snow = next(a for a in actors if a.get_actor_label() == 'HM_Environment_SourceSnow')
            comp=snow.get_component_by_class(unreal.NiagaraComponent)
            REPORT['snow_state']={'active':comp.is_active(),'asset':comp.get_asset().get_path_name(), 'component_bounds':str(comp.get_local_bounds()) if hasattr(comp,'get_local_bounds') else 'Unavailable'}
            REPORT['simulation_world']=world.get_path_name()
            REPORT['lights']=[]
            for a in ac.get_all_level_actors():
                if a.get_actor_label() not in ('HM_PreviewSkyLight','HM_PreviewSun'):continue
                lc=a.get_component_by_class(unreal.LightComponentBase)
                row={'label':a.get_actor_label()}
                for f in ('intensity','affects_world','light_color','source_type','cubemap','real_time_capture','lower_hemisphere_is_black','indirect_lighting_intensity','lighting_channels','volumetric_scattering_intensity','mobility'):
                    try:row[f]=str(lc.get_editor_property(f))
                    except:pass
                REPORT['lights'].append(row)
            unreal.SystemLibrary.execute_console_command(world,'t.MaxFPS 30')
            configure(c)
        c=CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        c.capture_scene()
        COUNT+=1
        if COUNT<150:
            return
        filename='Diagnose_'+CONFIGS[INDEX][0]+'.png'
        unreal.RenderingLibrary.export_render_target(world,c.get_editor_property('texture_target'),str(OUT),filename)
        REPORT['views'].append(str(OUT/filename))
        unreal.SystemLibrary.execute_console_command(world,'DumpNiagaraWorldManager')
        INDEX+=1
        COUNT=0
        if INDEX == len(CONFIGS):
            unreal.unregister_slate_post_tick_callback(HANDLE)
            (META/'NativeDiagnosis.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
            unreal.SystemLibrary.quit_editor()
        else:
            configure(c)
    except Exception:
        unreal.unregister_slate_post_tick_callback(HANDLE)
        REPORT['error']=traceback.format_exc()
        (META/'NativeDiagnosis.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
        unreal.SystemLibrary.quit_editor()

HANDLE=unreal.register_slate_post_tick_callback(tick)
