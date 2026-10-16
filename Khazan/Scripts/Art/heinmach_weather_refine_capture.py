"""Same-camera native look comparisons in an isolated real game; never saves assets."""
from pathlib import Path
import json
import runpy
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
META=CONF['REFINE_META']
OUT=ROOT/'Saved/ImportReports/HeinMachLookRefinement_20261006'
OUT.mkdir(parents=True,exist_ok=True)
META.mkdir(parents=True,exist_ok=True)
START=time.monotonic()
HANDLE=None
WORLD=None
FRAME=0
INDEX=0
CAMERA=None
SAVED_ONLY='-HMRefinementSavedOnly' in unreal.SystemLibrary.get_command_line()
STAGES=['SavedPlayer','SavedEntry','OpenSky','Cave'] if SAVED_ONLY else ['LegacyHigh','Neutral','Lifted','OpenSky','Cave']
if SAVED_ONLY:
    OUT=OUT/'Saved'
    OUT.mkdir(parents=True,exist_ok=True)
REPORT={'background':True,'standalone_game':True,'assets_saved':False,'tests':[],
        'material_MIDs_used':not SAVED_ONLY,'saved_look_verification':SAVED_ONLY}


def configure():
    global CAMERA
    stage=STAGES[INDEX]
    quality=CONF['QUALITY_PREVIEW'].copy()
    if stage=='LegacyMedium':
        quality.update({name:1 for name in quality if name.startswith('sg.')})
        quality.update({'sg.ResolutionQuality':71,'r.ScreenPercentage':71,'r.Streaming.MipBias':1,
                        'r.Streaming.PoolSize':600,'r.Tonemapper.Sharpen':0})
    for name,value in quality.items():
        unreal.SystemLibrary.execute_console_command(WORLD,name+' '+str(value))
    if not SAVED_ONLY and stage in ('Neutral','Lifted','OpenSky','Cave'):
        mids={}
        for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume):
            s=CONF['realism_settings'](a.get_editor_property('settings'))
            blendables=[]
            for wb in s.get_editor_property('weighted_blendables').array:
                if wb.object is None:continue
                parent=wb.object
                # UE5.8 MaterialInstance.cpp rejects MID parents; every trial
                # must inherit the saved regional MIC, not the previous MID.
                while isinstance(parent,unreal.MaterialInstanceDynamic):
                    parent=parent.get_editor_property('parent')
                path=parent.get_path_name()
                if path not in mids:
                    mid=unreal.MaterialLibrary.create_dynamic_material_instance(WORLD,parent)
                    for name in ('WorldOutlineOpacity','WorldToonWeight','CharacterOutlineOpacity',
                                 'CharacterToonWeight','ShadeSmoothness','HM_NativeShadowFillScale'):
                        value=3.0 if stage=='Lifted' and name=='HM_NativeShadowFillScale' else CONF['NATIVE'][name]
                        mid.set_scalar_parameter_value(name,value)
                    mids[path]=mid
                blendables.append(unreal.WeightedBlendable(weight=wb.weight,object=mids[path]))
            s.set_editor_property('weighted_blendables',unreal.WeightedBlendables(array=blendables))
            a.set_editor_property('settings',s)
        sun=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.DirectionalLight)
                 if a.get_actor_label()=='HM_PreviewSun')
        sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('specular_scale',CONF['NATIVE']['SunSpecularScale'])
    if stage=='SavedEntry':
        CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
        CAMERA.set_editor_property('use_pawn_control_rotation',False)
        CAMERA.set_world_location(unreal.Vector(12370.713034,12849.819799,312.732826),False,False)
        CAMERA.set_world_rotation(unreal.Rotator(pitch=0,yaw=-114.986206,roll=0),False,False)
    if stage in ('OpenSky','Cave'):
        if stage=='OpenSky':
            p=CAMERA.get_world_location()
            CAMERA.set_world_location(unreal.Vector(p.x,p.y,p.z+3000),False,False)
            CAMERA.set_world_rotation(unreal.Rotator(pitch=20,yaw=-115,roll=0),False,False)
        else:
            cave=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume)
                      if a.get_actor_label()=='HM_Environment_PP_HeinMach_Light_213')
            p,_=cave.get_actor_bounds(False)
            CAMERA.set_world_location(p,False,False)
            CAMERA.set_world_rotation(unreal.Rotator(pitch=0,yaw=45,roll=0),False,False)
    REPORT['tests'].append({'stage':stage,'native_shadow_fill':3 if stage=='Lifted' else (CONF['NATIVE']['HM_NativeShadowFillScale'] if stage!='LegacyHigh' else 8),
                            'cvars':{name:unreal.SystemLibrary.get_console_variable_float_value(name) for name in quality}})


def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (META/('SavedGameVerification.json' if SAVED_ONLY else 'VisualComparison.json')).write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HEINMACH_REALISM_CAPTURED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,FRAME,INDEX,CAMERA
    try:
        if time.monotonic()-START>360:finish('Native style comparison timed out');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            assert WORLD
            # Hidden game windows can still receive hardware mouse deltas.
            # Freeze this QA camera before any stage so only rendering changes.
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0)
            pc.set_ignore_look_input(True)
            pc.set_ignore_move_input(True)
            pc.disable_input(pc)
            pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            pawn.disable_input(pc)
            cameras=pawn.get_components_by_class(unreal.CameraComponent)
            CAMERA=next(c for c in cameras if c.is_active())
            if not SAVED_ONLY:
                CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,
                                             unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
                CAMERA.set_editor_property('use_pawn_control_rotation',False)
                CAMERA.set_world_location(unreal.Vector(12370.713034,12849.819799,312.732826),False,False)
                CAMERA.set_world_rotation(unreal.Rotator(pitch=0,yaw=-114.986206,roll=0),False,False)
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            if SAVED_ONLY:
                unreal.SystemLibrary.execute_console_command(WORLD,'r.GPUCsvStatsEnabled 1')
                unreal.SystemLibrary.execute_console_command(WORLD,'fx.DetailedCSVStats 1')
            configure()
        if time.monotonic()-START<10:return
        FRAME+=1
        if SAVED_ONLY and STAGES[INDEX]=='SavedEntry' and FRAME==30:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STARTFILE=HM_RefinedHigh_20261006.csv')
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile START')
        if SAVED_ONLY and STAGES[INDEX]=='SavedEntry' and FRAME==130:
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STOP')
        if FRAME==150:
            target=OUT/(STAGES[INDEX]+'.png')
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0)
            p,r=pcm.get_camera_location(),pcm.get_camera_rotation()
            REPORT['tests'][-1].update(image=str(target),camera=[p.x,p.y,p.z,r.pitch,r.yaw,r.roll])
            unreal.SystemLibrary.execute_console_command(WORLD,'HighResShot 1280x720 filename="'+str(target)+'"')
            if SAVED_ONLY and STAGES[INDEX]=='SavedPlayer':
                snow=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor)
                          if a.get_actor_label()=='HM_Environment_SourceSnow').get_component_by_class(unreal.NiagaraComponent)
                cache=unreal.new_object(unreal.NiagaraSimCache)
                assert unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,unreal.NiagaraSimCacheCreateParameters(),snow)
                REPORT['snow']={'system':snow.get_asset().get_path_name(),
                                'flakes':len(cache.read_position_attribute(emitter_name='Source_Flakes_Fast_Large')),
                                'dust':len(cache.read_position_attribute(emitter_name='Source_Dust'))}
        if FRAME>=160:
            INDEX+=1;FRAME=0
            if INDEX==len(STAGES):finish()
            else:configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
