import os,runpy,json
from pathlib import Path
assert os.getpid()==2252
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008/ComboRegression')
out.mkdir(exist_ok=True)
tools=ROOT/'Scripts/Engineering'
CASES=['weak_y_buffered','weak_y_committed','charge_02_03','rb_overfury','weak5_y','weak5_y_committed','weak5_y_early']
probe_suite=runpy.run_path(str(tools/'combo_runtime_suite.py'),init_globals={'EXPECTED_ROOT':ROOT,'OUT':out,'TOOLS':tools,'CASES':CASES})
print('COMBO_REGRESSION_STARTED',CASES)
