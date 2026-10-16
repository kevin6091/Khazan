"""Reusable targeted bank facts for native cue authorship; no asset writes."""
from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import OUT, EXTRACT, read

root=ET.fromstring('<banks>'+ ''.join((OUT/folder/'Banks.xml').read_text(encoding='utf-8') for folder in ('BankRecipes08','BankRecipes11','BankRecipes12') if (OUT/folder/'Banks.xml').exists())+'</banks>')
facts={}; all_nodes={}
for bank in root:
    for obj in bank.iter('object'):
        name=obj.get('name','')
        if not name.startswith('CAk'):continue
        sid=next((f.get('value') for f in obj.findall('field') if f.get('name')=='ulID'),None)
        if not sid or sid in facts:continue
        fields=[dict(f.attrib) for f in obj.iter('field')]
        facts[sid]={'type':name,'bank':dict(bank.attrib),'fields':fields}
        all_nodes[sid]=obj
        if name=='CAkRanSeqCntr':
            facts[sid]['playlist']=[{f.get('name'):f.get('value') for f in item.findall('field')}
                for item in obj.iter('object') if any(f.get('name')=='weight' for f in item.findall('field'))]
            facts[sid]['rtpcs']=[ET.tostring(item,encoding='unicode') for item in obj.iter('object') if item.get('name')=='RTPC']
        if name=='CAkLayerCntr':facts[sid]['xml']=ET.tostring(obj,encoding='unicode')
        if name in ('CAkAttenuation','CAkFxCustom','CAkAuxBus'):
            facts[sid]['xml']=ET.tostring(obj,encoding='unicode')
(OUT/'BankNodeFacts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
for sid in ('1067922062','297639475'):
    e=all_nodes[sid]
    print('OBJECT',sid,'playlist',facts[sid].get('playlist'))
    for l in e.iter('list'):
        if l.get('name') in ('pRTPCMgr','pAssociatedChildData','pCrossfadingRTPC'):
            print('RTPC',ET.tostring(l,encoding='unicode')[:8500])
print('Facts',len(facts),Counter(r['type'] for r in facts.values()))
print('NONUNIFORM',[(sid,f['playlist']) for sid,f in facts.items() if f.get('playlist') and
      len({x.get('weight') for x in f['playlist']})>1])
