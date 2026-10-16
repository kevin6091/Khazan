"""Use the established native automation driver only in this owned process."""
from pathlib import Path
import os,json,shutil
root=Path(__file__).resolve().parents[2]
out=Path(os.environ['KZ_MONSTER_CONTACT_OUT'])
usage=json.loads((root/'Metadata/MonsterRootCollisionRepair_20261012/MainUsageAudit02/Usage.json').read_text(encoding='utf-8'))
if 'RootPoses' in os.environ['KZ_MONSTER_CONTACT_TEST']:
    rows=usage['sequences']
    if os.environ.get('KZ_MONSTER_CONTACT_ROOT_BASELINE')=='1':
        rows=[r for r in rows if r['asset'].endswith('Attack_ChargeTackle_End.Attack_ChargeTackle_End') or r['asset'].endswith('Locomotion_Run_Loop_Stone.Locomotion_Run_Loop_Stone')]
    (out/'RootCases.tsv').write_text(''.join(r['asset']+'\t'+r['uses'][0][0]+'\n' for r in rows),encoding='utf-8')
if os.environ['KZ_MONSTER_CONTACT_TEST']=='Khazan.MonsterRepair.PIE':
    source=root/'Metadata/MonsterRootCollisionRepair_20261012/AttackCases.tsv'
    assert source.exists();shutil.copy2(source,out/'AttackCases.tsv')
os.environ['KZ_MONSTER_REPAIR_OUT']=os.environ['KZ_MONSTER_CONTACT_OUT']
os.environ['KZ_MONSTER_REPAIR_MODE']='rhi'
os.environ['KZ_MONSTER_REPAIR_TEST']=os.environ['KZ_MONSTER_CONTACT_TEST']
source=(root/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
exec(compile(source,'owned_monster_contact_driver','exec'))
