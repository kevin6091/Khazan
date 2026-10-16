"""Explicit root-owned application of the probed two-package revision."""
from pathlib import Path
import runpy

script = Path(__file__).with_name('monster_vfx_apes_current_material_binding_revision_20261008.py')
runpy.run_path(str(script), init_globals={'KZ_MONSTER_VFX_APES_BINDING_MODE': 'apply'}, run_name='__main__')
