from pathlib import Path
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
print('OWN_SNOW_END_PIE_REQUESTED')
