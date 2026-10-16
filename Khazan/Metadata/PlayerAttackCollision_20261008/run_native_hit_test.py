import os,time
from pathlib import Path
assert os.getpid()==2252
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
log=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008/OwnedPIEEditor.log')
offset=log.stat().st_size
deadline=time.monotonic()+30
state={'started':False}
def start_after_framework_tick(delta):
    if state['started']:return
    with log.open('r',encoding='utf-8',errors='replace') as f:
        f.seek(offset);new=f.read()
    if 'Test Started.' in new and 'Path={Khazan.Combat.PlayerAttackCollision.PIE}' in new:
        state['started']=True
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        print('PIE_STARTED_AFTER_AUTOMATION_BEGIN')
    elif time.monotonic()>deadline:
        state['started']=True;unreal.unregister_slate_post_tick_callback(handle)
        print('ERROR AUTOMATION_START_NOT_OBSERVED')
handle=unreal.register_slate_post_tick_callback(start_after_framework_tick)
console('Automation RunTests Khazan.Combat.PlayerAttackCollision.PIE')
print('NATIVE_HIT_SUITE_REQUESTED_AFTER_FRAMEWORK')
