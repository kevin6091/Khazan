"""Reuse original archive files and existing WWiser/parser for the small supplement."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import ROOT,read

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
plan=read(OUT/'ResourcePlan01.json');base=OUT/'BankSource/BBQ/Content/WwiseAudio'
new={r['source']:r for r in read(OUT/'Raw01/AudioFileExtractionReport.json')}
for path in plan['raw_requests']:
    row=plan['reuse'].get(path) or new[path];file=Path(row['target'])
    assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
    dst=base/path.split('/WwiseAudio/',1)[1];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dst)
folder=OUT/'BankRecipes08';folder.mkdir(exist_ok=True)
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe',str(PRIOR/'Tools/wwiser.pyz'),
    '-r','-d','xml','-dn',str(folder/'Banks'),'-nl',str(OUT/'wwnames.txt'),'-g','-go',str(folder/'txtp'),'-gw',str(base/'Media'),
    '-gv','100%','-gl','3721600213','-gra','-grf','-gwd','-gd',str(base/'**/*.bnk')]
if (folder/'Generation.json').exists():code=read(folder/'Generation.json')['exit_code']
else:
    with (folder/'wwiser.log').open('w',encoding='utf-8') as stream:
        code=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT).returncode
    (folder/'Generation.json').write_text(json.dumps({'args':args,'exit_code':code,'recipes':len(list((folder/'txtp').glob('*.txtp')))},indent=2),encoding='utf-8')
assert code==0
facts=read(PRIOR/'BankNodeFacts.json')
xml=ET.fromstring('<banks>'+(folder/'Banks.xml').read_text(encoding='utf-8')+'</banks>')
for bank in xml:
    for obj in bank.iter('object'):
        name=obj.get('name','')
        if not name.startswith('CAk'):continue
        sid=next((f.get('value') for f in obj.findall('field') if f.get('name')=='ulID'),None)
        if not sid:continue
        fields=[dict(f.attrib) for f in obj.iter('field')];fact={'type':name,'bank':dict(bank.attrib),'fields':fields}
        if name=='CAkRanSeqCntr':
            fact['playlist']=[{f.get('name'):f.get('value') for f in item.findall('field')} for item in obj.iter('object') if any(f.get('name')=='weight' for f in item.findall('field'))]
            fact['rtpcs']=[ET.tostring(item,encoding='unicode') for item in obj.iter('object') if item.get('name')=='RTPC']
        if name in ('CAkLayerCntr','CAkAttenuation','CAkFxCustom','CAkAuxBus'):fact['xml']=ET.tostring(obj,encoding='unicode')
        facts[sid]=fact
(OUT/'BankNodeFacts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
events=[r for r in plan['events'] if '/WwiseMotion/' not in r['source_package']]
(OUT/'ResourcePlan.json').write_text(json.dumps({'events':events},indent=2),encoding='utf-8')
import prepare_gameplay_audio_native_cues as native
native.OUT=OUT;native.EXTRACT=OUT;native.FACTS=facts
native.MEDIA_OVERLAY.update({p.name:p for p in (base/'Media').rglob('*.wem')})
native.main()
