"""Start only the isolated editor's existing snow verification session."""
from pathlib import Path
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
u=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w=u.get_game_world()
print('game_world_before',w)
if not w:unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
