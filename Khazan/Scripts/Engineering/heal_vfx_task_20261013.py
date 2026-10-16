"""Use the existing hidden, below-normal owned process runner."""
from pathlib import Path
import os
MAIN = Path(__file__).resolve().parents[2]
source = (MAIN/'Scripts/Engineering/monster_physics_task_20261013.py').read_text(encoding='utf-8')
source = source.replace('Khazan_PlayerPartsWork_20261007', 'Khazan_HealVFXWork_20261013')
source = source.replace('Metadata/MonsterSecondaryPhysics_20261013', 'Metadata/HealVFX_20261013')
source = source.replace('KZ_MONSTER_PHYSICS_OUT', 'KZ_HEAL_VFX_OUT')
source = source.replace("'-EnablePlugins=GameFeatures'", "'-EnablePlugins=GameFeatures,CascadeToNiagaraConverter'")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
