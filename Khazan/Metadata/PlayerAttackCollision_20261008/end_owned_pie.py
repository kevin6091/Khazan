import os
assert os.getpid()==2252
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
print('OWNED_PIE_END_REQUESTED')
