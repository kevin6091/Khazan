from pathlib import Path
import os,runpy
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT']);os.environ['KZ_PARRY_OUT']=str(OUT)
runpy.run_path(str(Path(__file__).resolve().parents[1]/'Engineering/combat_impact_upgrade_editor_driver_20261012.py'),run_name='__main__')
