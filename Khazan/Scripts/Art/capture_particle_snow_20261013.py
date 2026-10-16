"""Actual standalone game viewport; transient camera/cache, regular Shot, no saves."""
from pathlib import Path
import json, os, time, traceback
import unreal as u
OUT = Path(os.environ['KZ_ALPHA_OUT'])
WORLD = PC = PAWN = CAMERA = SNOW = None
START = time.monotonic(); FRAME = 0; INDEX = 0; HANDLE = None
R = {'status': 'running', 'actual_game_viewport': True, 'assets_saved': False, 'views': [], 'samples': []}

def finish(error=None):
    u.unregister_slate_post_tick_callback(HANDLE)
    R['status'] = 'failed' if error else 'passed'
    if error: R['error'] = error
    (OUT / 'Capture.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
    u.SystemLibrary.execute_console_command(WORLD, 'QUIT')

def sample():
    cache = u.new_object(u.NiagaraSimCache)  # Engine/Transient; never a map outer.
    assert u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache, u.NiagaraSimCacheCreateParameters(), SNOW)
    return {name: len(cache.read_position_attribute(emitter_name=name)) for name in ('Source_Flakes_Fast_Large', 'Source_Dust')}

def tick(delta):
    global WORLD, PC, PAWN, CAMERA, SNOW, FRAME, INDEX
    try:
        if time.monotonic()-START > 360: finish('Game capture watchdog'); return
        if WORLD is None:
            WORLD = u.load_object(None, '/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            if not WORLD: return
            PC = u.GameplayStatics.get_player_controller(WORLD, 0)
            PAWN = u.GameplayStatics.get_player_pawn(WORLD, 0)
            if not PC or not PAWN: return
            PC.set_ignore_look_input(True); PC.set_ignore_move_input(True)
            CAMERA = next(c for c in PAWN.get_components_by_class(u.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(u.DetachmentRule.KEEP_WORLD, u.DetachmentRule.KEEP_WORLD, u.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation', False)
            actor = next(a for a in u.GameplayStatics.get_all_actors_of_class(WORLD, u.NiagaraActor) if a.get_actor_label() == 'HM_Environment_SourceSnow')
            SNOW = actor.get_component_by_class(u.NiagaraComponent)
            R['system'] = SNOW.get_asset().get_path_name()
            # Editor-only scalability reflection is unavailable in -game.
            # Record the exact loaded project's saved budget and measure particles.
            import hashlib
            budget_file = Path(u.Paths.project_dir()) / 'Content/_Art/Player/Environment/Rendering/HeinMachWeather/NET_HM_WeatherBudget.uasset'
            R['budget_sha256'] = hashlib.sha256(budget_file.read_bytes()).hexdigest()
            u.SystemLibrary.execute_console_command(WORLD, 't.MaxFPS 30')
            R['initial_camera'] = {'location': str(CAMERA.get_world_location()), 'rotation': str(CAMERA.get_world_rotation())}
        FRAME += 1
        if FRAME in (180, 240, 300):
            R['samples'].append({'frame': FRAME, 'counts': sample()})
        if FRAME == 300:
            pcm = u.GameplayStatics.get_player_camera_manager(WORLD, 0)
            p, r = pcm.get_camera_location(), pcm.get_camera_rotation()
            target = OUT / 'Entry.png'
            R['views'].append({'name': 'Entry', 'camera': [p.x,p.y,p.z,r.pitch,r.yaw,r.roll], 'image': str(target)})
            u.SystemLibrary.execute_console_command(WORLD, 'Shot filename="'+str(target)+'" -nosuffix')
        if FRAME == 315:
            CAMERA.set_world_rotation(u.Rotator(30, 0, 0), False, True)
        if FRAME == 375:
            target = OUT / 'OpenSky.png'
            pcm = u.GameplayStatics.get_player_camera_manager(WORLD, 0); p, r = pcm.get_camera_location(), pcm.get_camera_rotation()
            R['views'].append({'name': 'OpenSky', 'camera': [p.x,p.y,p.z,r.pitch,r.yaw,r.roll], 'image': str(target)})
            u.SystemLibrary.execute_console_command(WORLD, 'Shot filename="'+str(target)+'" -nosuffix')
        if FRAME == 395: finish()
    except Exception: finish(traceback.format_exc())

HANDLE = u.register_slate_post_tick_callback(tick)
