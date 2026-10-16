"""Probe new native schema and UE serialization before any candidate asset save."""
from pathlib import Path
import runpy

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
runpy.run_path(str(MAIN / 'Scripts/Art/monster_vfx_author_20261008.py'),
    run_name='__main__', init_globals={'KZ_MONSTER_VFX_AUTHOR_MODE': 'probe'})
