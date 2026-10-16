"""Sequential snow GPU comparison in the isolated real game, without shots."""
from pathlib import Path
import json
import runpy
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
START=time.monotonic()
WORLD=SNOW=HANDLE=None
INDEX=FRAME=0
VARIANTS=['LegacySnow','SparseSnow','NoSnow']
REPORT={'background':True,'assets_saved':False,'viewport':[1280,720],'frame_cap':30,
        'limits':'Development offscreen; Rider editor concurrently running. Sequential effects comparison, not a production frame-rate guarantee.',
        'variants':[]}


def configure():
    name=VARIANTS[INDEX]
    path=('/Game/__HeinMachQA/NS_HM_LegacySnow' if name=='LegacySnow' else
          '/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers')
    SNOW.set_asset(None if name=='NoSnow' else unreal.load_asset(path))
    if name!='NoSnow':SNOW.activate(True)
    REPORT['variants'].append({'name':name,'system':path if name!='NoSnow' else None})


def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'PerformanceCapture.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HEINMACH_REFERENCE_PERFORMANCE_PASSED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,SNOW,INDEX,FRAME
    try:
        if time.monotonic()-START>600:finish('Performance timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0)
            pawn=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            pc.set_ignore_look_input(True);pc.set_ignore_move_input(True)
            pc.disable_input(pc);pawn.disable_input(pc)
            camera=next(c for c in pawn.get_components_by_class(unreal.CameraComponent) if c.is_active())
            camera.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            camera.set_editor_property('use_pawn_control_rotation',False)
            camera.set_world_location(unreal.Vector(12370.713034,12849.819799,312.732826),False,False)
            camera.set_world_rotation(unreal.Rotator(pitch=0,yaw=-114.986206,roll=0),False,False)
            SNOW=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor)
                      if a.get_actor_label()=='HM_Environment_SourceSnow').get_component_by_class(unreal.NiagaraComponent)
            for name,value in CONF['QUALITY_PREVIEW'].items():
                unreal.SystemLibrary.execute_console_command(WORLD,name+' '+str(value))
            for command in ('t.MaxFPS 30','r.GPUCsvStatsEnabled 1','fx.DetailedCSVStats 1'):
                unreal.SystemLibrary.execute_console_command(WORLD,command)
            configure()
        if time.monotonic()-START<10:return
        FRAME+=1
        if FRAME==180 and VARIANTS[INDEX]!='NoSnow':
            cache=unreal.new_object(unreal.NiagaraSimCache)
            assert unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,unreal.NiagaraSimCacheCreateParameters(),SNOW)
            REPORT['variants'][-1]['particles']={name:len(cache.read_position_attribute(emitter_name=name)) for name in
                                               ('Source_Flakes_Fast_Large','Source_Dust')}
        if FRAME==200:
            filename='HM_Reference_'+VARIANTS[INDEX]+'_20261006.csv'
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STARTFILE='+filename)
            unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile START')
            REPORT['variants'][-1]['csv']=str(ROOT/'Saved/Profiling/CSV'/filename)
        if FRAME==400:unreal.SystemLibrary.execute_console_command(WORLD,'CsvProfile STOP')
        if FRAME==410:
            INDEX+=1;FRAME=0
            if INDEX==len(VARIANTS):finish()
            else:configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
