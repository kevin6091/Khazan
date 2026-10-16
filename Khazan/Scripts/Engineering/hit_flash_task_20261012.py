"""Journal this correction's own build/probe processes using the existing runner."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
source = (root / 'Scripts/Engineering/combat_finish_followup_task_20261012.py').read_text(encoding='utf-8')
source = source.replace("OUT = ROOT / 'Metadata/CombatFinishFollowup_20261012'", "OUT = ROOT / 'Metadata/HitFlashCorrection_20261012'")
if sys.argv[1]=='rhi' and sys.argv[2].startswith('Visual'):
    # Process-only 60 Hz capture clock; product Config and Main editor unchanged.
    source = source.replace("'-d3d12']", "'-d3d12','-UseFixedTimeStep','-FPS=60']")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
