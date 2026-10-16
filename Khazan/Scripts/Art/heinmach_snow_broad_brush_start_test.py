"""Start profiling and the existing contact integration QA in the owned snow editor."""
from pathlib import Path
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
u=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not u.get_game_world()
w=u.get_editor_world()
for cmd in ('csvprofile start','CsvCategory HeinMachSnow enable'):
    unreal.SystemLibrary.execute_console_command(w,cmd)
print('BROAD_BRUSH_PROFILE_STARTED')
