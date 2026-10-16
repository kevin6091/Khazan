"""Run the existing combat effect PIE test in this task's hidden work editor."""
from pathlib import Path
import os

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work = main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
project = main if os.environ.get('KZ_SLASH_PROJECT') == 'main' else work
out = os.environ['KZ_SLASH_OUT']
os.environ.update(KZ_MONSTER_REPAIR_OUT=out,
                  KZ_MONSTER_REPAIR_MODE='rhi',
                  KZ_MONSTER_REPAIR_TEST='Khazan.CombatEffect.PIE')
source = (main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
old = "assert ROOT in [Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]"
new = "assert ROOT == Path("+repr(str(project))+")"
assert source.count(old) == 1
source = source.replace(old, new, 1)
if os.environ.get('KZ_SLASH_INSPECT') == '1':
    source = source.replace("['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE']",
                            "['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE','Khazan.CombatEffect.PIE']")
exec(compile(source, __file__, 'exec'), globals())
