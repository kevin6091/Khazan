"""Run the real CombatEffect native test; its native fixture owns the side camera."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('combat_impact_upgrade_editor_driver_20261012.py')),run_name='__main__')
