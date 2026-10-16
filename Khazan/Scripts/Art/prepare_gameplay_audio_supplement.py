"""Target native/default sound data needed by footsteps and confirmed impacts."""
import json
from prepare_gameplay_audio_scope import EXTRACT, OUT, ROOT, read

index=read(EXTRACT/'Index03/AudioPackageIndex.json')
paths=[r['path'][:-7] for r in index if r['path'].endswith('.uasset')]
names={'Play_PLYR_Footsteps','Play_PLYR_FootStep_Sprint_Stop','Play_PLYR_VO_Dmg',
       'Play_PLYR_VO_Dodge','efx_pc_dualaxesword_com_impact','efx_dualaxesword_strongatk_impact',
       'Play_PLYR_DualAxeSword_Guard_Suc','Play_PLYR_DualAxeSword_JustGuard_Suc',
       'Play_PLYR_Movement_Armor_Rustle','Play_PLYR_DualAxeSword_Weapon_Rustle',
       'Play_Chaos_LOBJ_Fire_Loop','kazan_footstep_info','Monster_Human_Footstep_info',
       'Monster_Apes_Footstep_info','Human_M_Yetuga_Footstep_info'}
requests={p for p in paths if p.rsplit('/',1)[-1] in names}
# Reactions were imported from raw sequences. Recover the authored composite
# sound occurrence, then map its raw time back through its actual segment.
current=read(OUT/'CurrentAssets02/CurrentAssets.json')['assets']
source_prefix='BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/'
for c in current:
    if c['type']!='AnimSequence' or '/Player/' not in c['asset']:
        continue
    original=c['metadata'].get('OriginalPackage')
    if original:
        requests.add(original)
    else:
        name=c['asset'].split('.')[0].rsplit('/',1)[-1]
        if c.get('import_source'):
            name=c['import_source'].replace('\\','/').rsplit('/',1)[-1].rsplit('.',1)[0]
        if name.startswith('CA_P_Kazan_'):
            requests.add(source_prefix+name)
    if '/Reaction/' in c['asset']:
        name=c['asset'].split('.')[0].rsplit('/',1)[-1].replace('CA_P_','AC_',1)
        requests.add('BBQ/Content/_Kazan_/Design/Kazan/Reaction/DualAxeSword/'+name)
    if '/BrutalAttack/' in c['asset']:
        name=c['asset'].split('.')[0].rsplit('/',1)[-1]
        requests.add('BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Grapple/'+name)
(EXTRACT/'SupplementRequests.json').write_text(json.dumps(sorted(requests),indent=2),encoding='utf-8')
print('Supplement',len(requests),'native event/data',len(names))
