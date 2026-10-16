"""Real game viewport screenshots, with temporal history; assets are never saved."""
from pathlib import Path
import json
import runpy
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
BASE=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
MODE='baseline'
for name in ('final','motion','trial'):
    if '-HMReference'+name.title() in unreal.SystemLibrary.get_command_line():MODE=name
OUT=BASE/MODE
OUT.mkdir(parents=True,exist_ok=True)
START=time.monotonic()
WORLD=CAMERA=PAWN=PC=HANDLE=None
FRAME=INDEX=0
STAGES=['Player','Entry','ReferenceStart','Boss','OpenSky']
PARTICLE_READBACK='-HMReferenceParticleReadback' in unreal.SystemLibrary.get_command_line()
if PARTICLE_READBACK:
    STAGES=['Player']
    OUT=BASE/'particle_readback';OUT.mkdir(parents=True,exist_ok=True)
REPORT={'mode':MODE,'real_game_viewport':True,'highres_screenshot':False,'assets_saved':False,'views':[]}


def camera(p,r):
    CAMERA.set_world_location(unreal.Vector(*p),False,False)
    CAMERA.set_world_rotation(unreal.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),False,False)


def configure():
    stage=STAGES[INDEX]
    if stage=='Entry':camera([12370.713034,12849.819799,312.732826],[0,-114.986206,0])
    if stage=='ReferenceStart':camera([10494.534774,-6517.085901,-5174.297077],[-.266921,177.083725,0])
    if stage=='Boss':
        a=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume)
               if a.get_actor_label()=='HM_Environment_PP_HeinMach_Light_211')
        p,e=a.get_actor_bounds(False)
        trace=unreal.SystemLibrary.line_trace_single(WORLD,
            unreal.Vector(p.x,p.y,p.z+e.z),unreal.Vector(p.x,p.y,p.z-e.z),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True)
        assert trace is not None,'Boss camera has no ground collision'
        hit=trace.to_dict()
        assert hit['blocking_hit'],'Boss ground trace did not hit'
        ground=hit['impact_point']
        # QA viewing height only; does not change gameplay or saved transforms.
        camera([ground.x,ground.y,ground.z+180],[-5,45,0])
    if stage=='OpenSky':camera([12370.713034,12849.819799,3312.732826],[20,-114.986206,0])
    REPORT['views'].append({'name':stage})


def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'Capture.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HEINMACH_REFERENCE_CAPTURE_PASSED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,FRAME,INDEX,CAMERA,PAWN,PC
    try:
        if time.monotonic()-START>600:finish('Capture timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            assert WORLD
            PC=unreal.GameplayStatics.get_player_controller(WORLD,0)
            PAWN=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            PC.set_ignore_look_input(True);PC.set_ignore_move_input(True)
            PC.disable_input(PC);PAWN.disable_input(PC)
            CAMERA=next(c for c in PAWN.get_components_by_class(unreal.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation',False)
            for name,value in CONF['QUALITY_PREVIEW'].items():
                unreal.SystemLibrary.execute_console_command(WORLD,name+' '+str(value))
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            REPORT['character']=[{'name':c.get_name(),'mesh':str(c.get_editor_property('skeletal_mesh_asset')),
                                  'per_bone_motion_blur':c.get_editor_property('per_bone_motion_blur'),
                                  'render_custom_depth':c.get_editor_property('render_custom_depth'),
                                  'stencil':c.get_editor_property('custom_depth_stencil_value')}
                                 for c in PAWN.get_components_by_class(unreal.SkeletalMeshComponent)]
            configure()
        if time.monotonic()-START<10:return
        FRAME+=1
        if FRAME==100:
            target=OUT/(STAGES[INDEX]+'.png')
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0)
            p,r=pcm.get_camera_location(),pcm.get_camera_rotation()
            REPORT['views'][-1].update(camera=[p.x,p.y,p.z,r.pitch,r.yaw,r.roll],image=str(target))
            unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(target)+'" -nosuffix')
            if STAGES[INDEX]=='Player':
                snow=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor)
                          if a.get_actor_label()=='HM_Environment_SourceSnow').get_component_by_class(unreal.NiagaraComponent)
                cache=unreal.new_object(unreal.NiagaraSimCache)
                assert unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,unreal.NiagaraSimCacheCreateParameters(),snow)
                REPORT['snow']={'system':snow.get_asset().get_path_name(),
                                'flakes':len(cache.read_position_attribute(emitter_name='Source_Flakes_Fast_Large')),
                                'dust':len(cache.read_position_attribute(emitter_name='Source_Dust'))}
                if PARTICLE_READBACK:
                    REPORT['snow']['geometry']={}
                    for emitter in ('Source_Flakes_Fast_Large','Source_Dust'):
                        sizes=cache.read_vector2_attribute(attribute_name='SpriteSize',emitter_name=emitter)
                        assert sizes,'SpriteSize not captured: '+emitter
                        REPORT['snow']['geometry'][emitter]={'count':len(sizes),
                            'size_x_cm':[min(v.x for v in sizes),max(v.x for v in sizes)],
                            'size_y_cm':[min(v.y for v in sizes),max(v.y for v in sizes)],
                            'boundary':'Niagara SpriteSize before material SizeBySpeed WPO; original source range is separate.'}
        if FRAME>=106:
            INDEX+=1;FRAME=0
            if INDEX==len(STAGES):finish()
            else:configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
