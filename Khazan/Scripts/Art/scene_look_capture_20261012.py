"""Read saved scene, then capture actual game viewport. No asset saves."""
from pathlib import Path
import hashlib,json,os,time,traceback,unreal

OUT=Path(os.environ['KZ_LOOK_OUT']);LEVEL=os.environ['KZ_LOOK_LEVEL'];MODE=os.environ['KZ_LOOK_MODE']
MAPS={'DevMap':'/Game/Maps/DevMap','HeinMach':'/Game/Maps/L_HeinMach_Environment'}
world=unreal.EditorLoadingAndSavingUtils.load_map(MAPS[LEVEL]);assert world
ac=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=ac.get_all_level_actors()
report={'success':False,'asset_saves':0,'map':world.get_path_name(),'actors':len(actors),'lights':[],'postprocess':[],'poses':{},'views':[]}

def fields(obj,names):
    result={}
    for key in names:
        try:
            value=obj.get_editor_property(key)
            if isinstance(value,(bool,int,float,str)):result[key]=value
            else:result[key]=value.export_text() if hasattr(value,'export_text') else str(value)
        except Exception:pass
    return result

for a in actors:
    p,r,s=a.get_actor_location(),a.get_actor_rotation(),a.get_actor_scale3d()
    report['poses'][a.get_actor_label()]=[a.get_class().get_name(),p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
    for c in a.get_components_by_class(unreal.LightComponentBase):
        report['lights'].append({'actor':a.get_actor_label(),'component':c.get_path_name(),'class':c.get_class().get_name(),
            'properties':fields(c,['intensity','light_color','cast_shadows','mobility','visible','indirect_lighting_intensity',
                'volumetric_scattering_intensity','specular_scale','diffuse_scale','shadow_bias','shadow_slope_bias','contact_shadow_length',
                'light_source_angle','light_source_soft_angle','intensity_units','attenuation_radius','use_inverse_squared_falloff',
                'light_falloff_exponent','source_radius','soft_source_radius','source_length','source_type','cubemap','real_time_capture',
                'lower_hemisphere_is_black','lower_hemisphere_color','distance_field_ambient_occlusion','occlusion_max_distance',
                'occlusion_contrast','occlusion_exponent','min_occlusion','occlusion_combine_mode','affects_world','lighting_channels'])})
    if isinstance(a,unreal.PostProcessVolume):
        settings=a.get_editor_property('settings')
        report['postprocess'].append({'actor':a.get_actor_label(),'properties':fields(a,['priority','unbound','enabled','blend_weight']),
            'settings':settings.export_text()})
    if isinstance(a,unreal.PlayerStart):report.setdefault('player_starts',[]).append({'actor':a.get_actor_label(),'pose':report['poses'][a.get_actor_label()]})

(OUT/'SavedScene.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# QA controls are identical before/after and are not written to the product.
QUALITY={'sg.ResolutionQuality':100,'sg.AntiAliasingQuality':3,'sg.TextureQuality':2,'sg.PostProcessQuality':2,
    'sg.ShadowQuality':2,'sg.GlobalIlluminationQuality':2,'sg.ReflectionQuality':2,'sg.EffectsQuality':2,
    'sg.ViewDistanceQuality':2,'sg.FoliageQuality':2,'sg.ShadingQuality':2,'r.ScreenPercentage':100,
    'r.AntiAliasingMethod':4,'r.MaxAnisotropy':8,'r.Streaming.MipBias':0,'r.Streaming.PoolSize':1600,
    'r.Tonemapper.Sharpen':0.25,'t.MaxFPS':30}
for key,value in QUALITY.items():unreal.SystemLibrary.execute_console_command(world,key+' '+str(value))
report['quality_qa_only']=QUALITY
if LEVEL=='HeinMach' and 'Before' not in OUT.name:
    report['material_shader_statistics']=[]
    for package in ['/Game/_Art/Player/Environment/Rendering/SceneLook/M_HM_PBR_Masked',
        '/Game/_Art/Player/Environment/HeinMach/Reconstructed/OverrideMaterials/Inherited/Materials/MI_WM_COM_SmallTree_Base_003_02']:
        m=unreal.load_asset(package);assert m
        stats=unreal.MaterialEditingLibrary.get_statistics(m)
        report['material_shader_statistics'].append({'material':package,'stats':stats.export_text()})
report['cvars']={key:unreal.SystemLibrary.get_console_variable_float_value(key) for key in ['r.Lumen.DiffuseIndirect.Allow',
    'r.Lumen.HardwareRayTracing','r.Shadow.Virtual.Enable','r.DefaultFeature.AutoExposure','r.DefaultFeature.AmbientOcclusion',
    'r.LumenScene.SurfaceCache.AtlasSize','r.Shadow.Virtual.MaxPhysicalPages','r.VolumetricFog']}
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
START=time.monotonic();HANDLE=None;CAMERA=PAWN=PC=WORLD=None;INDEX=0;FRAME=0;SETTLED=0
VIEWS=[]
if LEVEL=='HeinMach':
    VIEWS=[('Player',None,None),('Entry',[12370.713034,12849.819799,312.732826],[0,-114.986206,0]),
        ('ReferenceStart',[10494.534774,-6517.085901,-5174.297077],[-.266921,177.083725,0]),
        ('OpenSky',[12370.713034,12849.819799,3312.732826],[20,-114.986206,0])]
else:VIEWS=[('Player',None,None),('PlayerFront',None,None),('Monsters',[2000,-2700,260],[-4,26,0])]
if LEVEL=='DevMap' and MODE=='trials':
    VIEWS=[('Current',None,None),('Fill4',None,None),('Fill8',None,None),('Fill8Software',None,None),('Fill8Static',None,None)]

def configure():
    global FRAME,SETTLED
    name,pos,rot=VIEWS[INDEX]
    if MODE=='trials':
        baseline=json.loads((Path(os.environ['KZ_LOOK_MAIN'])/'Metadata/SceneLook_20261012/DevBefore01/Capture.json').read_text())
        pose=next(v['camera'] for v in baseline['views'] if v['name']=='PlayerFront');pos=pose[:3];rot=pose[3:]
        skylight=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.SkyLight)).get_component_by_class(unreal.SkyLightComponent)
        if name!='Current':skylight.set_intensity(4.0 if name=='Fill4' else 8.0)
        if name=='Fill8Software':unreal.SystemLibrary.execute_console_command(WORLD,'r.Lumen.HardwareRayTracing 0')
        if name=='Fill8Static':skylight.set_real_time_capture(False);skylight.recapture_sky()
    if name=='PlayerFront':
        p=PAWN.get_actor_location();pos=[p.x+390,p.y-170,p.z+65];rot=[-6,156,0]
    if pos:
        CAMERA.set_world_location(unreal.Vector(*pos),False,False)
        CAMERA.set_world_rotation(unreal.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]),False,False)
    FRAME=0;SETTLED=time.monotonic()

def finish(error=None):
    if error:report['error']=error;unreal.log_error(error)
    report['dirty_content']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    (OUT/'Capture.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global WORLD,CAMERA,PAWN,PC,INDEX,FRAME
    try:
        if time.monotonic()-START>500:finish('Capture timeout');return
        if WORLD is None:
            WORLD=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if WORLD is None:return
            PC=unreal.GameplayStatics.get_player_controller(WORLD,0);PAWN=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            if not PC or not PAWN:WORLD=None;return
            PC.set_ignore_look_input(True);PC.set_ignore_move_input(True);PC.disable_input(PC);PAWN.disable_input(PC)
            CAMERA=next(c for c in PAWN.get_components_by_class(unreal.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation',False)
            report['player_materials']=[{'component':c.get_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]}
                for c in PAWN.get_components_by_class(unreal.SkeletalMeshComponent)]
            configure();return
        FRAME+=1
        if FRAME==150 and time.monotonic()-SETTLED<12:FRAME-=1;return
        if FRAME==150:
            name,pos,rot=VIEWS[INDEX];target=OUT/(name+'.png')
            pcm=unreal.GameplayStatics.get_player_camera_manager(WORLD,0);p,r=pcm.get_camera_location(),pcm.get_camera_rotation()
            report['views'].append({'name':name,'camera':[p.x,p.y,p.z,r.pitch,r.yaw,r.roll],'image':str(target)})
            unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(target)+'" -nosuffix')
        if FRAME>=156:
            INDEX+=1
            if INDEX>=len(VIEWS):report['success']=True;finish()
            else:configure()
    except Exception:finish(traceback.format_exc())

HANDLE=unreal.register_slate_post_tick_callback(tick)
