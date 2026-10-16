import json
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import OUT, EXTRACT, read
facts=read(OUT/'BankNodeFacts.json')
for sid in ('297639475',):
    e=ET.fromstring(facts[sid]['xml'])
    print(ET.tostring(e,encoding='unicode')[-12000:])
    print('ALL DIRECT CHILD FIELDS',[(l.get('name'),[dict(f.attrib) for f in l.findall('field')]) for l in e.iter('object')])
print('SPIN SOURCE', [p for p in read(EXTRACT/'SpinIndex01/TargetedPackageIndex.json') if '/Design/' in p])
print('COND',[{'asset':e['asset'],'prop':e['source']['properties']} for e in read(OUT/'PlaybackPlan.json')['events'] if e['source']['type']=='xxAnimNotifyState_CondAkEvent'])
