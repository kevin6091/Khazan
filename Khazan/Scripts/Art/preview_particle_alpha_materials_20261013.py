"""Regular PIE viewport inspection of isolated material cards, no scene capture/save."""
from pathlib import Path
import json, os, time, traceback
import unreal as u
OUT = Path(os.environ['KZ_ALPHA_OUT']); START = time.monotonic()
R = {'status': 'running', 'actual_RHI': True, 'saved_assets': 0, 'scope': 'Material spatial alpha on cards; a diagnostic fixture, not gameplay/particle-lifetime parity', 'materials': [], 'images': []}
WORLD = CAMERA = None; REQUESTED = False; FRAME = 0; KEEP = []; BUSY = False
PATHS = ['/Game/_Art/Effects/Shared/Materials/Other/DefaultParticle',
         '/Game/_Art/Effects/Shared/Materials/BBQ_Material/Base/Base_DefaltParticle',
         '/Game/_Art/Effects/Shared/Materials/BBQ_Material/Base/Base_Particle',
         '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/DefaultParticle']
RISK=os.environ.get('KZ_ALPHA_CARDS')=='risk'
if RISK:
    plan=json.loads((Path(os.environ['KZ_ALPHA_MAIN'])/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
    PATHS=[plan['default_particle']]+[r['material'] for r in plan['rows']]

def finish(error=None):
    u.unregister_slate_post_tick_callback(HANDLE)
    R['status'] = 'failed' if error else 'passed'
    if error: R['error'] = error
    (OUT / 'Preview.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
    u.SystemLibrary.quit_editor()

def setup():
    global REQUESTED
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    world.get_world_settings().set_editor_property('default_game_mode', u.load_class(None, '/Script/Engine.GameModeBase'))
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    camera = actors.spawn_actor_from_class(u.CameraActor, u.Vector(0,0,950 if RISK else 650), u.Rotator(pitch=-90,yaw=0,roll=0))
    camera.set_actor_label('AlphaQA_Camera')
    cam = camera.get_component_by_class(u.CameraComponent)
    cam.set_editor_property('field_of_view', 55)
    pp = cam.get_editor_property('post_process_settings')
    for name, value in [('auto_exposure_min_brightness',1.0),('auto_exposure_max_brightness',1.0),('bloom_intensity',0.0)]:
        pp.set_editor_property(name,value); pp.set_editor_property('override_'+name,True)
    cam.set_editor_property('post_process_settings',pp); cam.set_editor_property('post_process_blend_weight',1)
    # Visible neutral background prevents black translucent cards from disappearing.
    bg = u.AssetToolsHelpers.get_asset_tools().create_asset('M_AlphaQA_Background_'+OUT.name, '/Game/__ParticleAlphaQA', u.Material, u.MaterialFactoryNew())
    u.MaterialEditingLibrary.delete_all_material_expressions(bg)
    bg.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    color = u.MaterialEditingLibrary.create_material_expression(bg,u.MaterialExpressionConstant3Vector,0,0)
    color.set_editor_property('constant',u.LinearColor(.12,.12,.12,1))
    assert u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not list(u.MaterialEditingLibrary.recompile_material(bg)); KEEP.append(bg)
    plane = u.load_asset('/Engine/BasicShapes/Plane')
    backdrop = actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5))
    component = backdrop.get_component_by_class(u.StaticMeshComponent); component.set_static_mesh(plane); component.set_material(0,bg)
    backdrop.set_actor_scale3d(u.Vector(12,12,1)); KEEP.extend([backdrop,camera])
    for index,path in enumerate(PATHS):
        asset=u.load_asset(path); assert asset,path
        position=u.Vector((index//5-1.5)*150,(index%5-2)*150,0) if RISK else u.Vector((index//2)*180-90,(index%2)*180-90,0)
        actor=actors.spawn_actor_from_class(u.StaticMeshActor,position)
        component=actor.get_component_by_class(u.StaticMeshComponent);component.set_static_mesh(plane);component.set_material(0,asset)
        actor.set_actor_scale3d(u.Vector(1.2 if RISK else 1.3,1.2 if RISK else 1.3,1)); KEEP.append(actor)
        R['materials'].append({'index':index,'path':path,'location':str(actor.get_actor_location())})
    u.SystemLibrary.execute_console_command(world,'t.MaxFPS 30')
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();REQUESTED=True

def tick(delta):
    global WORLD,CAMERA,FRAME,BUSY
    if BUSY:return
    BUSY=True
    try:
        if time.monotonic()-START>180:finish('Material card watchdog');return
        if time.monotonic()-START<8:return
        if not REQUESTED:setup();return
        if WORLD is None:
            WORLD=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if not WORLD:return
            for actor in u.GameplayStatics.get_all_actors_of_class(WORLD,u.Pawn):actor.set_actor_hidden_in_game(True)
            CAMERA=next(a for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.CameraActor) if a.get_actor_label()=='AlphaQA_Camera')
            u.GameplayStatics.get_player_controller(WORLD,0).set_view_target_with_blend(CAMERA,0)
        FRAME+=1
        if FRAME==55:
            pcm=u.GameplayStatics.get_player_camera_manager(WORLD,0)
            R['actual_camera']={'location':str(pcm.get_camera_location()),'rotation':str(pcm.get_camera_rotation()),'view_target':str(u.GameplayStatics.get_player_controller(WORLD,0).get_view_target())}
            R['actual_meshes']=[{'name':a.get_name(),'location':str(a.get_actor_location()),'mesh':str(a.get_component_by_class(u.StaticMeshComponent).get_editor_property('static_mesh'))} for a in u.GameplayStatics.get_all_actors_of_class(WORLD,u.StaticMeshActor)]
        if FRAME in (60,90):
            target=OUT/('AlphaCards_'+str(FRAME)+'.png');u.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(target)+'" -nosuffix');R['images'].append(str(target))
        if FRAME>=110:finish()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
HANDLE=u.register_slate_post_tick_callback(tick)
