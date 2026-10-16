"""Sequential fresh Main tests; keep one RHI test editor at a time."""
from pathlib import Path
import os,sys,json,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/MonsterRootCollisionRepair_20261012'
steps=[('MainRootPoses01','Khazan.MonsterContactRepair.RootPoses.PIE'),('MainContacts01','Khazan.MonsterContactRepair.MonsterHits.PIE'),('MainPlayerCollision01','Khazan.Combat.PlayerAttackCollision.PIE')]
for name,test in steps:
    env=dict(os.environ,KZ_MONSTER_CONTACT_TEST=test)
    code=subprocess.call([sys.executable,str(ROOT/'Scripts/Engineering/run_monster_contact_repair_20261012.py'),name,'Scripts/Engineering/monster_contact_editor_driver_20261012.py','main_rhi'],env=env)
    assert code==0 and json.loads((OUT/name/'Driver.json').read_text())['status']=='passed',name
code=subprocess.call([sys.executable,str(ROOT/'Scripts/Engineering/run_monster_contact_repair_20261012.py'),'MainSavedAudit01','Scripts/Engineering/audit_monster_contact_usage_20261012.py','main_commandlet'])
assert code==0 and json.loads((OUT/'MainSavedAudit01/Usage.json').read_text(encoding='utf-8'))['status']=='passed'
print('MAIN_CONTACT_VALIDATIONS_PASSED',flush=True)
