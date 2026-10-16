"""Read-only RHI driver and actual-character screenshots for native VFX QA."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
VERIFY_MAIN = os.environ.get('KZ_MONSTER_VFX_VERIFY_MAIN') == '1'
assert WORK == (MAIN if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan'))
OUT = Path(os.environ['KZ_MONSTER_VFX_REPORT']).resolve()
assert OUT.is_relative_to((MAIN / 'Saved/ImportReports/MonsterVFX_20261008').resolve())
TEST = os.environ.get('KZ_MONSTER_VFX_TEST', 'Khazan.MonsterVisual.PIE')
LOG = OUT / 'PrivatePIE.log'
REPORT = {'status': 'running', 'project': str(WORK), 'test': TEST, 'captures': [], 'package_saves': 0,
    'verification': 'fresh_saved_Main' if VERIFY_MAIN else 'private_candidate',
    'boundary': 'Actual RHI/native fixture; inspection camera/cadence are QA settings, not original gameplay values or pixel parity.'}
manifest_path = WORK / 'Binaries/Win64/UnrealEditor.modules'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
module_name = manifest['Modules']['Khazan']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
module_handle = kernel.GetModuleHandleW(module_name)
assert module_handle, 'Selected Khazan module is not actually loaded: ' + module_name
module_path_buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(module_handle, module_path_buffer, len(module_path_buffer))
module_path = Path(module_path_buffer.value).resolve()
assert module_path == (WORK / 'Binaries/Win64' / module_name).resolve()
REPORT['loaded_native_module'] = {'path': str(module_path), 'name': module_name,
    'build_id': manifest['BuildId'], 'sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(),
    'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'verification': 'Win32 GetModuleHandleW/GetModuleFileNameW of the actual loaded module'}
REPORT['driver_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
REPORT['monster_camera_bounds'] = 'Actual body mesh bounds, excluding transient particle component bounds (QA framing only)'
START = time.monotonic()
STARTED = REQUESTED = BUSY = FINISHED = False
CAPTURE = TARGET = None
LAST = {}
COUNTS = {}

def finish(error=None):
    global FINISHED
    if FINISHED:
        return
    FINISHED = True
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (OUT / 'Driver.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global STARTED, REQUESTED, BUSY, CAPTURE, TARGET
    if BUSY or FINISHED:
        return
    BUSY = True
    try:
        elapsed = time.monotonic()-START
        if elapsed > 720:
            finish('Native VFX PIE driver timed out'); return
        if elapsed < 8:
            return
        if not STARTED:
            unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            unreal.SystemLibrary.execute_console_command(None, 'Automation RunTests ' + TEST)
            STARTED = True
            return
        log = LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else ''
        if TEST in log and 'Test Started' in log and not REQUESTED:
            REQUESTED = True
            actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
            actor.set_actor_label('MonsterVFXInspectionCapture')
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        lines = [line for line in log.splitlines() if 'Test Completed' in line and TEST in line]
        if lines:
            REPORT['native_completion'] = lines[-1]
            REPORT['material_compile_failures'] = [line for line in log.splitlines()
                if 'Failed to compile Material' in line or 'Default Material will be used in game' in line]
            error = None if 'Success' in lines[-1] else lines[-1]
            if REPORT['material_compile_failures']:
                error = 'RHI material fallback: ' + '\n'.join(REPORT['material_compile_failures'])
            finish(error); return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        if TEST == 'Khazan.CombatEffect.PIE':
            focus = unreal.GameplayStatics.get_player_character(world, 0)
        else:
            candidates = unreal.GameplayStatics.get_all_actors_with_tag(world, 'KZMonsterVFXCapture')
            focus = candidates[0] if candidates else None
        if not focus:
            return
        mesh = focus.get_editor_property('mesh')
        anim = mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        label = focus.get_actor_label()
        section = str(anim.montage_get_current_section(montage)) if montage else ''
        position = anim.montage_get_position(montage) if montage else unreal.GameplayStatics.get_time_seconds(world)
        key = label + '_' + (montage.get_name() + '_' + section if montage else 'Sequence')
        frozen = bool(mesh.get_editor_property('pause_anims'))
        if frozen:
            key += '_Frozen'
        # This samples screenshots; native notifies remain at exact authored times.
        slot = int(position*5)
        if LAST.get(key) == slot or COUNTS.get(key, 0) >= 24 or len(REPORT['captures']) >= 2400:
            return
        LAST[key] = slot
        COUNTS[key] = COUNTS.get(key, 0)+1
        if CAPTURE is None:
            CAPTURE = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)
                if a.get_actor_label() == 'MonsterVFXInspectionCapture')
            TARGET = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
            component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
            component.set_editor_property('texture_target', TARGET)
            component.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            component.set_editor_property('capture_every_frame', False)
            component.set_editor_property('always_persist_rendering_state', True)
        if TEST == 'Khazan.CombatEffect.PIE':
            camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
            location, rotation, fov = camera.get_camera_location(), camera.get_camera_rotation(), camera.get_fov_angle()
        else:
            # Particle adapters may have large source bounds. Including them in
            # actor bounds moves the inspection camera away from the real body.
            origin, extent, sphere_radius = unreal.SystemLibrary.get_component_bounds(mesh)
            radius = max(extent.x, extent.y, extent.z, 1.)
            location = origin + focus.get_actor_forward_vector()*radius*3.8 + focus.get_actor_right_vector()*radius*1.5 + unreal.Vector(0, 0, radius*.55)
            rotation = unreal.MathLibrary.find_look_at_rotation(location, origin)
            fov = 50.
        CAPTURE.set_actor_location(location, False, False)
        CAPTURE.set_actor_rotation(rotation, False)
        component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        component.set_editor_property('fov_angle', fov)
        component.capture_scene()
        filename = str(len(REPORT['captures'])).zfill(4) + '_' + ''.join(c if c.isalnum() or c in '_-' else '_' for c in key) + '.png'
        unreal.RenderingLibrary.export_render_target(world, TARGET, str(OUT), filename)
        particles = [{'component': c.get_path_name(), 'active': c.is_active(),
            'template': c.get_editor_property('template').get_path_name() if c.get_editor_property('template') else None,
            'tags': [str(t) for t in c.get_editor_property('component_tags')]}
            for c in focus.get_components_by_class(unreal.ParticleSystemComponent)]
        REPORT['captures'].append({'actor': focus.get_path_name(), 'label': label,
            'montage': montage.get_path_name() if montage else None, 'section': section,
            'position_seconds': position, 'frozen_final_pose': frozen,
            'particles': particles, 'image': str(OUT / filename)})
    except Exception:
        finish(traceback.format_exc())
    finally:
        BUSY = False

HANDLE = unreal.register_slate_post_tick_callback(tick)
