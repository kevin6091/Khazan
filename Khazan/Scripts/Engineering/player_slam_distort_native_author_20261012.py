"""Access protected Niagara user-parameter authoring through the existing DEV fixture."""
from pathlib import Path
import os
MAIN=Path(__file__).resolve().parents[2]
os.environ.update(KZ_MONSTER_REPAIR_OUT=os.environ['KZ_PARRY_OUT'],KZ_MONSTER_REPAIR_MODE='asset_editor',
    KZ_MONSTER_REPAIR_TEST='Khazan.CombatPresentation.AuthorSlamDistort')
source=(MAIN/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace('Khazan_GiantFallWork_20261011/Khazan','Khazan_SlamDistortWork_20261012/Khazan')
exec(compile(source,'owned_slam_distort_native_author','exec'))
