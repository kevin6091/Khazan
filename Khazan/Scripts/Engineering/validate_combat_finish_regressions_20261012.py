"""Serial owned editor regressions; each starts a fresh PIE and current Main DLL."""
from pathlib import Path
import subprocess,sys,json
ROOT=Path(__file__).resolve().parents[2]
runner=ROOT/'Scripts/Engineering/combat_finish_followup_task_20261012.py'
cases=[('EffectsFinal01','Khazan.CombatEffect.PIE'),('CollisionFinal01','Khazan.Combat.PlayerAttackCollision.PIE'),('ParryFinal01','Khazan.Parry.PIE')]
results=[]
for name,test in cases:
    code=subprocess.call([sys.executable,str(runner),'rhi',name,'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py',test],cwd=ROOT)
    folder=ROOT/'Metadata/CombatFinishFollowup_20261012'/name
    report=json.loads((folder/'Driver.json').read_text(encoding='utf-8'))
    results.append({'name':name,'test':test,'exit':code,'status':report['status'],'module_sha256':report['module_sha256']})
    (ROOT/'Metadata/CombatFinishFollowup_20261012/Regressions.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert code==0 and report['status']=='passed',name
print('CURRENT_MAIN_REGRESSIONS_PASSED',len(results))
