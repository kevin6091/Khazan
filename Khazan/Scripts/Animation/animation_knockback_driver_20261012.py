from pathlib import Path
import os
MAIN=Path(__file__).resolve().parents[2];OUT=os.environ['KZ_PARRY_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=OUT,KZ_MONSTER_REPAIR_MODE=os.environ.get('KZ_PARRY_MODE','rhi'),KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_TIMING_TEST','Khazan.AnimationTiming.KnockbackPIE'))
source=(MAIN/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace('Khazan_GiantFallWork_20261011/Khazan','Khazan_SlamDistortWork_20261012/Khazan')
exec(compile(source,__file__,'exec'))
