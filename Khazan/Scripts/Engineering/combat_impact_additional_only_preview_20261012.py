"""Short native preview; temporarily hide Cascade only in the owned test world."""
import os,runpy
from pathlib import Path
os.environ['KZ_SLASH_PREVIEW_ONLY']='1'
runpy.run_path(str(Path(__file__).with_name('combat_impact_player_visual_driver_20261012.py')),run_name='__main__')
