"""Unsaved effect-only PIE/render checks in a hidden process; no gameplay hookups."""
from pathlib import Path
import json
import math
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
OUT = ROOT / 'Saved/ImportReports/CombatEffects_20261006/Preview'
OUT.mkdir(parents=True, exist_ok=True)
ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
BY_NAME = {r['name']: r for r in ROWS if r['source_type'] == 'ParticleSystem'}
NAMES = ['PP_AtkEx_Guard', 'PP_AtkEx_JustGuard', 'PP_AtkEx_Parry', 'FP_BloodBleed_001',
         'FP_Kazan_DualaxeSword_FatalbloodEX_slash_01',
         'FP_P_World_Pc_Deepsnow_Footstep_normal', 'FP_P_World_Pc_Deepsnow_footstep_dash_normal',
         'FP_P_World_Mon_L_Deepsnow_footstep_dash_normal', 'FP_P_World_Pc_Deepsnow_Smash_normal']
START = time.monotonic()
HANDLE = None
REQUESTED = False
WORLD = None
CAPTURE = None
CAMERA = None
COMPONENT = None
INDEX = -1
FRAMES = 0
KEEP = []
REPORT = {'status': 'running', 'actual_RHI': True, 'background_PIE': True,
          'asset_saves': False, 'user_editor_untouched': True, 'effects': [],
          'boundary': 'Native standalone effect rendering in an unsaved blank PIE world. No weapon sockets, combat events, surface routing or original game appearance equivalence tested.',
          'QA_choices': 'Camera fit, 1280x720 image size, fixed exposure, 30 FPS cap and frames 1/2/4/8/16 are inspection settings, not original gameplay values.'}

def checkpoint():
    (META / 'RepresentativeEffectRendering.json').write_text(json.dumps(REPORT, indent=2) + '\n', encoding='utf-8')

def finish(error=None):
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    checkpoint()
    unreal.unregister_slate_post_tick_callback(HANDLE)
    print('KZ_COMBAT_EFFECTS_RENDER_' + REPORT['status'].upper(), flush=True)
    unreal.SystemLibrary.quit_editor()

def setup():
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    assert world
    world.get_world_settings().set_editor_property('default_game_mode', unreal.load_class(None, '/Script/Engine.GameModeBase'))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
    capture.set_actor_label('KZFX_RenderCapture')
    camera = actors.spawn_actor_from_class(unreal.CameraActor, unreal.Vector())
    camera.set_actor_label('KZFX_RenderCamera')
    camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', 60.0)
    c = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    KEEP.extend([capture, camera, target])
    c.set_editor_property('texture_target', target)
    c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property('capture_every_frame', False)
    c.set_editor_property('always_persist_rendering_state', True)
    c.set_editor_property('fov_angle', 60.0)
    pp = c.get_editor_property('post_process_settings')
    for f, v in [('auto_exposure_min_brightness', 1.0), ('auto_exposure_max_brightness', 1.0)]:
        pp.set_editor_property(f, v)
        pp.set_editor_property('override_' + f, True)
    c.set_editor_property('post_process_settings', pp)
    c.set_editor_property('post_process_blend_weight', 1.0)
    unreal.SystemLibrary.execute_console_command(world, 't.MaxFPS 30')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()

def next_effect():
    global INDEX, COMPONENT, FRAMES
    if COMPONENT:
        COMPONENT.destroy_component(COMPONENT)
    INDEX += 1
    FRAMES = 0
    if INDEX == len(NAMES):
        finish()
        return
    name = NAMES[INDEX]
    row = BY_NAME[name]
    asset = unreal.load_asset(row['destination'])
    assert asset
    KEEP.append(asset)
    original = next(x for x in json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig')) if x['Type'] == 'ParticleSystem' and not x.get('Outer'))
    bounds = original.get('Properties', {}).get('FixedRelativeBoundingBox')
    center = unreal.Vector(0, 0, 50)
    extent = 150.0
    if bounds and bounds.get('IsValid') and 'Min' in bounds and 'Max' in bounds:
        center = unreal.Vector(*[(bounds['Min'][a] + bounds['Max'][a]) * .5 for a in 'XYZ'])
        extent = max((bounds['Max'][a] - bounds['Min'][a]) * .5 for a in 'XYZ')
    # Source culling boxes can span an entire battle area. The QA camera uses
    # a bounded close inspection distance, not the original gameplay camera.
    distance = max(300.0, min(800.0, extent * 2.5))
    if name in ('PP_AtkEx_Guard', 'PP_AtkEx_JustGuard', 'PP_AtkEx_Parry'):
        distance = 150.0
    eye = center + unreal.Vector(distance, -distance, distance * .65)
    direction = center - eye
    rotation = unreal.Rotator(pitch=math.degrees(math.atan2(direction.z, math.hypot(direction.x, direction.y))), yaw=math.degrees(math.atan2(direction.y, direction.x)), roll=0)
    for actor in (CAPTURE, CAMERA):
        actor.set_actor_location(eye, False, False)
        actor.set_actor_rotation(rotation, False)
    COMPONENT = unreal.GameplayStatics.spawn_emitter_at_location(WORLD, asset, unreal.Vector(), auto_destroy=False)
    assert COMPONENT, name
    REPORT['effects'].append({'name': name, 'asset': row['destination'], 'source': row['source_package'],
                              'captures': [], 'active_particle_counts': [], 'camera': [eye.x, eye.y, eye.z]})
    checkpoint()
    print('KZFX_RENDER ' + name, flush=True)

def tick(delta):
    global REQUESTED, WORLD, CAPTURE, CAMERA, FRAMES
    try:
        if time.monotonic() - START > 420:
            finish('Background render QA timing limit reached.')
            return
        if time.monotonic() - START < 10:
            return
        if not REQUESTED:
            setup()
            REQUESTED = True
            return
        if WORLD is None:
            WORLD = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not WORLD:
                return
            actors = unreal.GameplayStatics.get_all_actors_of_class(WORLD, unreal.Actor)
            CAPTURE = next(a for a in actors if a.get_actor_label() == 'KZFX_RenderCapture')
            CAMERA = next(a for a in actors if a.get_actor_label() == 'KZFX_RenderCamera')
            controller = unreal.GameplayStatics.get_player_controller(WORLD, 0)
            if controller:
                controller.set_view_target_with_blend(CAMERA, 0.0)
            REPORT['world'] = WORLD.get_path_name()
            next_effect()
            return
        FRAMES += 1
        c = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        c.capture_scene()
        if FRAMES in (1, 2, 4, 8, 16):
            name = NAMES[INDEX]
            count = COMPONENT.get_num_active_particles()
            filename = name + '_' + str(FRAMES) + '.png'
            unreal.RenderingLibrary.export_render_target(WORLD, c.get_editor_property('texture_target'), str(OUT), filename)
            REPORT['effects'][-1]['active_particle_counts'].append(count)
            REPORT['effects'][-1]['captures'].append({'frame': FRAMES, 'image': str(OUT / filename), 'active_particles': count})
            checkpoint()
        if FRAMES >= 20:
            next_effect()
    except Exception:
        finish(traceback.format_exc())

HANDLE = unreal.register_slate_post_tick_callback(tick)
