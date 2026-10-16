"""Reuse the existing native MonsterVisual test for current human attack abilities only."""
import os,runpy
from pathlib import Path
os.environ['KZ_MONSTER_VFX_HUMAN_ONLY']='1'
runpy.run_path(str(Path(__file__).with_name('combat_impact_upgrade_editor_driver_20261012.py')),run_name='__main__')
