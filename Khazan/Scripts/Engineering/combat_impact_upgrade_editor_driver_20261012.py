"""Reuse the tested native driver with the one newly owned project admitted."""
from pathlib import Path
import unreal
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace("Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]", "Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')]")
# Parry owns PIE startup, as does MonsterRepair.
source=source.replace("['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE']", "['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE','Khazan.Parry.PIE']")
exec(compile(source,__file__,'exec'),globals())
