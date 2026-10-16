"""Current native fixture owns a separate floating PIE view and all gameplay."""
from pathlib import Path
import os,unreal
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out=os.environ['KZ_MONSTER_PHYSICS_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=out,KZ_MONSTER_REPAIR_MODE='rhi',KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_SLASH_TEST','Khazan.CombatEffect.PIE'))
s=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
s=s.replace("Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]","Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerSlashWork_20261013/Khazan')]")
if os.environ.get('KZ_SLASH_INSPECT')=='1':s=s.replace("['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE']","['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE','Khazan.CombatEffect.PIE']")
if os.environ.get('KZ_SLASH_DEBUG_HOLD')=='1':s=s.replace('if elapsed<8:return','if elapsed<45:return')
exec(compile(s,__file__,'exec'),globals())
