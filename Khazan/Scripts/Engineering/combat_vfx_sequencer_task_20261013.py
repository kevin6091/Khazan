"""Reuse owned editor/build processes for the combat VFX authoring workflow."""
from pathlib import Path
main = Path(__file__).resolve().parents[2]
source = (main / 'Scripts/Engineering/monster_physics_task_20261013.py').read_text(encoding='utf-8')
source = source.replace("OUT = MAIN/'Metadata/MonsterSecondaryPhysics_20261013'", "OUT = MAIN/'Metadata/CombatVFXSequencer_20261013'")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
