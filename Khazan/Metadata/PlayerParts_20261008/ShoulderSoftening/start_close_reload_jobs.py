"""Private saved-reload PIE, with transient close camera framing only."""
from pathlib import Path
import json, os, time
import unreal

work = Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan').resolve()
assert Path(unreal.Paths.project_dir()).resolve() == work
ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert ed.get_game_world() is None
state = {'start': time.monotonic(), 'handle': None}

def frame(delta):
    world = ed.get_game_world()
    if world and unreal.GameplayStatics.get_time_seconds(world) > 1.5:
        cls = unreal.load_class(None, '/Script/Khazan.KZPlayer')
        players = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
        if players:
            arm = players[0].get_component_by_class(unreal.SpringArmComponent)
            assert arm is not None
            # Assistant-selected visual inspection framing, not gameplay tuning.
            arm.set_editor_property('target_arm_length', 220.0,
                notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            offset = arm.get_editor_property('socket_offset')
            arm.set_editor_property('socket_offset', unreal.Vector(offset.x, offset.y, offset.z + 50.0),
                notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            (work/'Saved/ShoulderCloseFraming.json').write_text(json.dumps({
                'pid': os.getpid(), 'cameraOnly': True, 'armCm': 220.0,
                'addedSocketZCm': 50.0, 'savedToAssets': False,
                'gameplayControlInputPhysicsUnchanged': True}), encoding='utf-8')
            unreal.unregister_slate_post_tick_callback(state['handle'])
            state['handle'] = None
            return
    if time.monotonic() - state['start'] > 70:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = None
        unreal.log_error('Shoulder close-framing watchdog expired')

state['handle'] = unreal.register_slate_post_tick_callback(frame)
source = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerParts_20261008/WaistJitter/start_reload_jobs.py')
exec(compile(source.read_text(encoding='utf-8-sig'), str(source), 'exec'))
