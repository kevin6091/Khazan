"""Reuse the existing owned-process journal for the current, superseding request."""
from pathlib import Path
import sys, os

root = Path(__file__).resolve().parents[2]
source = (root/'Scripts/Engineering/combat_finish_followup_task_20261012.py').read_text(encoding='utf-8')
source = source.replace("OUT = ROOT / 'Metadata/CombatFinishFollowup_20261012'", "OUT = ROOT / 'Metadata/CombatImpactUpgrade_20261012'")
if os.environ.get('KZ_IMPACT_PROJECT'):
    project = Path(os.environ['KZ_IMPACT_PROJECT']).resolve()
    assert project == Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
    source = source.replace("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path("+repr(str(project))+")")
    source = source.replace("OUT = ROOT / 'Metadata/CombatImpactUpgrade_20261012'", "OUT = Path("+repr(str(root/'Metadata/CombatImpactUpgrade_20261012'))+")")
if sys.argv[1] == 'rhi':
    source = source.replace("'-d3d12']", "'-d3d12','-UseFixedTimeStep','-FPS=60']")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
