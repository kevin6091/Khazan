"""Own the previously staged workspace and keep the new task's process evidence separate."""
from pathlib import Path
import os
MAIN=Path(__file__).resolve().parents[2]
os.environ['KZ_TIMING_MAIN']=str(MAIN)
os.environ.setdefault('KZ_TIMING_PLAN',str(MAIN/'Metadata/AnimationTimingKnockback_20261012/Plan.json'))
source=(MAIN/'Scripts/Engineering/player_slam_distort_task_20261012.py').read_text(encoding='utf-8')
# The underlying runner substitutes its output root from the parry runner's literal.
source=source.replace("OUT = MAIN / 'Metadata/PlayerSlamDistort_20261012'","OUT = MAIN / 'Metadata/AnimationTimingKnockback_20261012'")
source=source.replace('2026101296','2026101297')
exec(compile(source,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})
