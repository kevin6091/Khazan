from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import OUT, EXTRACT, read

p=OUT/'BankRecipes08/Banks.xml'
print('XML bytes',p.stat().st_size,flush=True)
root=ET.fromstring('<banks>'+p.read_text(encoding='utf-8')+'</banks>')
rows={}
for bank in root:
    for e in bank.iter('object'):
        if e.get('name','').startswith('CAk'):
            sid=next((f.get('value') for f in e.findall('field') if f.get('name')=='ulID'),None)
            if sid:rows.setdefault(sid,e)
for sid in ('1067922062','297639475','509168013','823567122'):
    e=rows.get(sid)
    print('OBJECT',sid,ET.tostring(e,encoding='unicode')[:7000] if e is not None else None)
weights=Counter(f.get('value') for e in rows.values() for f in e.iter('field') if f.get('name') in ('weight','Weight','uWeight'))
print('WEIGHTS',weights)
atten=Counter(e.get('name') for e in rows.values() if 'Attenuation' in e.get('name',''))
print('ATTEN',atten)
print('SURFACES',[(Path(r['target']).stem,read(r['target'])[0].get('Properties')) for r in read(EXTRACT/'Physical01/MetadataExtractionReport.json') if r['status']=='ok'])
sources=read(OUT/'ResourcePlan.json')
for r in sources['events']:
    if any(k in r['name'].lower() for k in ('hit','guard_succ','damage','impact')):print('EVENT',r['name'],r['cooked']['EventId'])
