"""Render each currently referenced VFX in the real PIE viewport on both maps.

The neutral unlit panel and isolated high-altitude stage are QA only. They
separate colour/exposure from the different backgrounds, without SceneCapture.
Actual combat placement is verified by the existing gameplay PIE tests.
"""
from pathlib import Path
import hashlib,json,math,os,time,traceback
import unreal as u

main=Path(os.environ['KZ_HM_COLOUR_MAIN']);out=Path(os.environ['KZ_HM_COLOUR_OUT'])
level=os.environ.get('KZ_HM_COLOUR_LEVEL','HeinMach')
mode=os.environ['KZ_HM_COLOUR_MODE']
assert mode.startswith('work_') or mode.startswith('main_')
catalog=os.environ.get('KZ_HM_COLOUR_CATALOG','CandidateAudit03')
usage=json.loads((main/('Metadata/HeinMachColourVFX_20261015/'+catalog+'/Usage.json')).read_text(encoding='utf-8'))
systems=usage['systems']
if os.environ.get('KZ_HM_COLOUR_PROBE_ASSETS'):
    selected=set(os.environ['KZ_HM_COLOUR_PROBE_ASSETS'].split(','))
    systems=[row for row in systems if row['asset'] in selected]
    assert systems,selected
if os.environ.get('KZ_HM_COLOUR_PROBE_LIMIT'):systems=systems[:int(os.environ['KZ_HM_COLOUR_PROBE_LIMIT'])]
if os.environ.get('KZ_HM_COLOUR_PROBE_REPEAT'):systems=systems*int(os.environ['KZ_HM_COLOUR_PROBE_REPEAT'])
map_path='/Game/Maps/DevMap' if level=='DevMap' else '/Game/Maps/L_HeinMach_Environment'
world=u.EditorLoadingAndSavingUtils.load_map(map_path);assert world
u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
for name,value in {'r.ScreenPercentage':100,'sg.AntiAliasingQuality':3,'sg.PostProcessQuality':2,'sg.EffectsQuality':2,
                   'sg.TextureQuality':2,'r.Streaming.MipBias':0,'t.MaxFPS':60}.items():
    u.SystemLibrary.execute_console_command(world,name+' '+str(value))
lib=u.MaterialEditingLibrary
panel_material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_HeinColourProbeBackdrop','/Game/Tools/TaskQA_20261015',u.Material,u.MaterialFactoryNew())
assert panel_material
panel_material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
# Refraction reads opaque scene colour before translucency. An opaque panel
# is essential to compare its input rather than the two different skies.
panel_material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
panel_material.set_editor_property('two_sided',True);panel_material.set_editor_property('bUseTranslucencyVertexFog',False)
colour=lib.create_material_expression(panel_material,u.MaterialExpressionConstant3Vector)
colour.set_editor_property('constant',u.LinearColor(.018,.018,.018,1))
inverse=lib.create_material_expression(panel_material,u.MaterialExpressionEyeAdaptationInverse)
one=lib.create_material_expression(panel_material,u.MaterialExpressionConstant);one.set_editor_property('r',1)
names=list(lib.get_material_expression_input_names(inverse))
assert lib.connect_material_expressions(colour,'',inverse,next(x for x in names if 'Light' in x))
assert lib.connect_material_expressions(one,'',inverse,next(x for x in names if 'Alpha' in x))
assert lib.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert lib.connect_material_property(one,'',u.MaterialProperty.MP_OPACITY)
assert not list(lib.recompile_material(panel_material))
actor_subsystem=u.get_editor_subsystem(u.EditorActorSubsystem)
start_actor=next(actor for actor in actor_subsystem.get_all_level_actors() if isinstance(actor,u.PlayerStart))
stage=start_actor.get_actor_location()+u.Vector(0,0,20000)
# Supported editor actor API; these unsaved actors are then duplicated into PIE.
editor_panel=actor_subsystem.spawn_actor_from_class(u.StaticMeshActor,stage+u.Vector(500,0,0),u.Rotator(pitch=90))
editor_panel.set_actor_label('QA_ColourPanel')
mesh=editor_panel.get_component_by_class(u.StaticMeshComponent)
mesh.set_editor_property('mobility',u.ComponentMobility.MOVABLE)
mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));mesh.set_material(0,panel_material)
editor_panel.set_actor_scale3d(u.Vector(60,60,60));mesh.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
editor_camera=actor_subsystem.spawn_actor_from_class(u.CameraActor,stage+u.Vector(-750,0,80),u.Rotator(pitch=-6))
editor_camera.set_actor_label('QA_ColourCamera')
editor_camera.get_component_by_class(u.CameraComponent).set_field_of_view(55)
report={'status':'running','map':map_path,'asset_saves':0,'method':'actual game Shot; neutral panel; fixed timestep60; all runtime-reference systems',
        'rows':[],'quality_scope':'QA isolation only, not an ordinary combat camera or Shipping performance measurement'}
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
start=time.monotonic();game=player=camera=active=panel=None
index=0;frame=0;phase='world';handle=None
pending_image=None;pending_since=0
spawn_clock=0

def finish(error=None):
    global phase
    if phase=='done':return
    phase='done'
    report['status']='failed' if error else 'passed';report['seconds']=time.monotonic()-start
    if error:report['error']=error;u.log_error(error)
    (out/'Probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle)
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play();u.SystemLibrary.quit_editor()

def shot(name):
    global pending_image,pending_since
    # Slate can tick several times between viewport draws. Hold the simulation
    # until the real game screenshot has completed, rather than overwriting an
    # outstanding request with the next effect.
    u.GameplayStatics.set_game_paused(game,True)
    pending_image=out/name;pending_since=time.monotonic()
    pc=u.GameplayStatics.get_player_controller(game,0)
    pc.set_view_target_with_blend(camera,0)
    report['method']='native PIE game viewport ReadPixels; neutral panel; fixed timestep60; current referenced systems'
    u.SystemLibrary.execute_console_command(game,'KZ.QA.ColourShot "'+str(pending_image)+'"',pc)

def image_ready():
    if pending_image.exists() and pending_image.stat().st_size>0:return True
    if time.monotonic()-pending_since>30:raise RuntimeError('Viewport screenshot did not complete: '+str(pending_image))
    return False
def remove():
    global active
    if active:
        if u.SystemLibrary.is_valid(active):active.destroy_component(active)
        active=None

def spawn():
    global active,frame,spawn_clock
    item=systems[index];asset=u.load_asset(item['asset']);assert asset,item['asset']
    if isinstance(asset,u.ParticleSystem):
        active=u.GameplayStatics.spawn_emitter_attached(asset,player.get_editor_property('mesh'),u.Name('Root'),stage,u.Rotator(),u.Vector(1,1,1),
            u.AttachLocationType.KEEP_WORLD_POSITION,True,u.PSCPoolMethod.NONE,True)
    else:
        active=u.NiagaraFunctionLibrary.spawn_system_at_location(game,asset,stage,u.Rotator(),u.Vector(1,1,1),True,True,u.NCPoolMethod.NONE,False)
    assert active,item['asset']
    frame=0;spawn_clock=u.GameplayStatics.get_time_seconds(game)

def tick(delta):
    global game,player,camera,panel,active,index,frame,phase,stage
    try:
        if time.monotonic()-start>3600:finish('Colour probe watchdog');return
        if game is None:
            game=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if not game:return
            player=u.GameplayStatics.get_player_pawn(game,0);pc=u.GameplayStatics.get_player_controller(game,0)
            if not player or not pc:game=None;return
            player.set_actor_location(stage,False,False)
            player.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_NONE)
            pc.set_ignore_move_input(True);pc.set_ignore_look_input(True)
            for actor in u.GameplayStatics.get_all_actors_of_class(game,u.Actor):
                if actor==player or actor.get_actor_label().startswith('QA_Colour'):continue
                if isinstance(actor,(u.StaticMeshActor,u.InstancedFoliageActor,u.KZMonster)) and 'sky' not in actor.get_actor_label().lower():
                    actor.set_actor_hidden_in_game(True)
                for effect in actor.get_components_by_class(u.FXSystemComponent):effect.set_visibility(False)
            for mesh in player.get_components_by_class(u.SkeletalMeshComponent):
                mesh.set_visibility(False,False)
                mesh.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            camera=next(actor for actor in u.GameplayStatics.get_all_actors_of_class(game,u.CameraActor) if actor.get_actor_label()=='QA_ColourCamera')
            pc.set_view_target_with_blend(camera,0)
            phase='settle';frame=0;return
        frame+=1
        if phase=='settle':
            if frame>=90:shot('Background.png');phase='background_wait';frame=0
        elif phase=='background_wait':
            if image_ready():u.GameplayStatics.set_game_paused(game,False);phase='start';frame=0
        elif phase=='start':
            if frame>=4:spawn();phase='effect'
        elif phase=='effect':
            if u.GameplayStatics.get_time_seconds(game)-spawn_clock>=.2:
                path='VFX_'+str(index).zfill(3)+'.png';shot(path);phase='effect_wait'
                valid=u.SystemLibrary.is_valid(active)
                location=active.get_world_location() if valid else stage
                row={'index':index,'asset':systems[index]['asset'],'class':systems[index]['class'],
                     'image':path,'active':active.is_active() if valid else False,
                     'completed_before_sample':not valid,'finite_position':all(math.isfinite(v) for v in (location.x,location.y,location.z)),
                     'sample_age_game_seconds':u.GameplayStatics.get_time_seconds(game)-spawn_clock}
                row['view_target']=u.GameplayStatics.get_player_controller(game,0).get_view_target().get_name()
                if valid and isinstance(active,u.ParticleSystemComponent):
                    try:row['active_particles']=active.get_num_active_particles()
                    except Exception:pass
                report['rows'].append(row)
        elif phase=='effect_wait':
            if image_ready():
                remove();index+=1
                if index==len(systems):finish();return
                if index%20==0:
                    (out/'Progress.json').write_text(json.dumps({'rendered':index,'total':len(systems)}),encoding='utf-8')
                    u.log('HEIN_VFX_COLOUR_PROGRESS '+str(index))
                u.GameplayStatics.set_game_paused(game,False);spawn();phase='effect'
    except Exception:finish(traceback.format_exc())

handle=u.register_slate_post_tick_callback(tick)
