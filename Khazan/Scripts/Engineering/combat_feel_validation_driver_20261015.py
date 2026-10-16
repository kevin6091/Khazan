"""Use existing owned PIE driver; Parry alone owns its own play-session request."""
from pathlib import Path
import unreal

driver = Path(unreal.Paths.project_dir()).resolve() / "Scripts/Engineering/monster_physics_validation_driver_20261013.py"
source = driver.read_text(encoding="utf-8")
old = "if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
new = "if test != 'Khazan.Parry.PIE' and (test.endswith('.PIE') or test.endswith('KnockbackPIE')):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
assert source.count(old) == 1
exec(compile(source.replace(old, new), str(driver), "exec"), {"__file__": str(driver), "__name__": "__main__"})
