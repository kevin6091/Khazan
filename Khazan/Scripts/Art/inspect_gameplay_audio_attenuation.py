from collections import Counter
import json
import re
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import OUT,read
facts=read(OUT/'BankNodeFacts.json')
atts={k:v for k,v in facts.items() if v['type']=='CAkAttenuation'}
print('ATTENUATION',len(atts))
for sid,f in list(atts.items())[:3]:
    print('ATT',sid,f['xml'][:7000])
for sid in ('2785835910','1791118518'):
    print('BUS',sid,[(f['name'],f.get('valuefmt',f['value'])) for f in facts.get(sid,{}).get('fields',[])])
for name in ('Play_PLYR_Footsteps','Play_PLYR_DualAxeSword_Guard_Suc','Play_PLYR_VO_Dodge','efx_pc_dualaxesword_com_impact'):
    cues=read(OUT/'NativeCuePlan01.json')['cues'];c=next((r for r in cues if r['event_name']==name),None)
    print('CUE',name, bool(c),c.get('loop') if c else None)
print('COMPLEX',[(r['recipe'].split('txtp')[1],r['reason']) for r in read(OUT/'NativeCuePlan01.json')['fallback']])
