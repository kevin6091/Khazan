"""Reuse the native 18+5 fixture; observe all changed slash families and finishers."""
from pathlib import Path
import os
root=Path(os.environ['KZ_CLEAN_MAIN'])
path=root/'Saved/ImportReports/HeinMachCleanPresentation_20261011/capture_final_vfx.py'
code=path.read_text(encoding='utf-8')
anchor="for old,new in scope['changes'].items():"
extra="""scope['changes']['slot = int(position * 2)']='slot = int(position * 6)'
scope['changes'][\"CAPTURE_COUNTS.get(key, 0) >= 24 or len(REPORT['captures']) >= 300\"]=\"CAPTURE_COUNTS.get(key, 0) >= 80 or len(REPORT['captures']) >= 900\"
scope['changes'][\"key = montage.get_name() + '_' + section\"]=\"key = montage.get_name() + '_' + section\\n        if not any(n in montage.get_name() for n in ('WeakAttackCombo','StrongAttackCombo','Player_DodgeAttack','StrongChargeAttack','OverFury','BrutalFront','BrutalBack')):\\n            return\"
"""
assert code.count(anchor)==1
exec(compile(code.replace(anchor,extra+anchor),str(path),'exec'),dict(__name__='__main__',__file__=str(path)))
