"""Existing owned-process runner, scoped to Main or the fresh GiantVFX workspace."""
from pathlib import Path
import os, sys

main = Path(__file__).resolve().parents[2]
source = (main/'Scripts/Engineering/combat_finish_followup_task_20261012.py').read_text(encoding='utf-8')
source = source.replace("OUT = ROOT / 'Metadata/CombatFinishFollowup_20261012'", "OUT = ROOT / 'Metadata/GiantVFX_20261013'")
source = source.replace("'-EnablePlugins=GameFeatures'", "'-EnablePlugins=GameFeatures,CascadeToNiagaraConverter'")
if os.environ.get('KZ_GIANT_VFX_PROJECT'):
    project = Path(os.environ['KZ_GIANT_VFX_PROJECT']).resolve()
    assert project == main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
    source = source.replace("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path("+repr(str(project))+")")
    source = source.replace("OUT = ROOT / 'Metadata/GiantVFX_20261013'", "OUT = Path("+repr(str(main/'Metadata/GiantVFX_20261013'))+")")
    source = source.replace("entry = ROOT/sys.argv[3]", "entry = Path("+repr(str(main))+")/sys.argv[3]")
if sys.argv[1] == 'rhi':
    source = source.replace("'-d3d12']", "'-d3d12', '-UseFixedTimeStep', '-FPS=60']")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
