"""Fresh saved data plus existing actual Guard/HP/received-hit native regression."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
os.environ['KZ_RECEIVED_HIT_MODE'] = 'verify'
saved_audit = ROOT / 'Scripts/Engineering/remove_player_received_hit_vfx_20261013.py'
exec(compile(saved_audit.read_text(encoding='utf-8'), str(saved_audit), 'exec'),
     {'__file__': str(saved_audit), '__name__': '__main__'})
driver = ROOT / 'Scripts/Engineering/monster_physics_validation_driver_20261013.py'
source = driver.read_text(encoding='utf-8')
source = source.replace("os.environ['KZ_MONSTER_PHYSICS_OUT']", "os.environ['KZ_RECEIVED_HIT_OUT']")
source = source.replace("os.environ['KZ_MONSTER_PHYSICS_TESTS'].split(',')", "['Khazan.Parry.PIE']")
# KZParryQA::FWait owns its RequestPlaySession; a second request tears down its pawn.
source = source.replace("if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()", "# Native Parry test starts its own PIE session.")
exec(compile(source, str(driver), 'exec'), {'__file__': str(driver), '__name__': '__main__'})
