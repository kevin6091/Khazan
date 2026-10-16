"""Run only in a freshly launched, caller-owned Work/Main editor; read and quit."""
from pathlib import Path
import unreal

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
work = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
project = Path(unreal.Paths.project_dir()).resolve()
assert project in (main, work), 'Unexpected project'
COMBAT_REACTION_METADATA_DIR = main / 'Metadata/CombatReaction_20261008'
COMBAT_REACTION_OUTPUT_PATH = COMBAT_REACTION_METADATA_DIR / (
    'WorkSavedReload.json' if project == work else 'MainSavedReload.json')
assert not COMBAT_REACTION_OUTPUT_PATH.exists(), 'Preserve existing readback receipt'
script = COMBAT_REACTION_METADATA_DIR / 'verify_saved_reactions.py'
try:
    exec(compile(script.read_text(encoding='utf-8-sig'), str(script), 'exec'), globals())
finally:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, 'QUIT_EDITOR')
