"""Run both focused camera suites in one owned RHI editor with their PIE owners."""
from pathlib import Path


driver = Path(__file__).with_name("monster_physics_validation_driver_20261013.py")
source = driver.read_text(encoding="utf-8")
old = "if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
new = "if test == 'Khazan.GiantCamera.PIE':unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
assert source.count(old) == 1
source = source.replace(old, new)
exec(compile(source, str(driver), "exec"), {"__file__": str(driver), "__name__": "__main__"})
