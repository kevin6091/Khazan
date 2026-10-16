from pathlib import Path
import json
from prepare_gameplay_audio_scope import OUT,EXTRACT,ROOT,read
res=read(OUT/'ResourcePlan.json')
for r in res['events']:
    if r['name'] in ('efx_pc_dualaxesword_com_impact','efx_dualaxesword_strongatk_impact','Play_PLYR_DualAxeSword_Guard_Suc'):
        print('IMPACT MEDIA',r['name'],[m['DebugName'] for m in r['cooked'].get('Media',[])])
index=read(EXTRACT/'Index03/AudioPackageIndex.json')
print('FLESH EVENTS',[r['path'] for r in index if r['path'].endswith('.uasset') and any(k in r['path'].lower() for k in ('flesh','hit_flesh','impact_flesh','bloodhit')) and '/Sound/' in r['path']][:35])
data=read(ROOT/'Metadata/GiantCombatFall_20261011/AuthoringPlan.json')
print('GIANT PLAN KEYS',list(data))
for family in data['families']:
    print('FAMILY KEYS',family['family'],list(family))
    for row in family.get('objects',[]):print('OBJECT',json.dumps(row,ensure_ascii=False)[:2200])
    for key in family:
        if 'object' in key.lower() and key!='objects':print('OBJECT KEY',key,str(family[key])[:2200])
