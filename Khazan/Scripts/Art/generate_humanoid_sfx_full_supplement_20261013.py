from pathlib import Path
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import ROOT,read
import prepare_gameplay_audio_native_cues as native
OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
stage=sys.argv[1] if len(sys.argv)>1 else '03'
recipe=sys.argv[2] if len(sys.argv)>2 else '10'
resource=read(OUT/('ResourcePlan'+stage+'.json'));base=OUT/'BankSource/BBQ/Content/WwiseAudio'
rows=list(resource['reuse'].values())+read(OUT/('Raw'+stage)/'AudioFileExtractionReport.json')
for r in rows:
    dst=base/r['source'].split('/WwiseAudio/',1)[1];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r['target'],dst)
folder=OUT/('BankRecipes'+recipe);folder.mkdir(exist_ok=False)
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe',str(PRIOR/'Tools/wwiser.pyz'),
    '-r','-d','xml','-dn',str(folder/'Banks'),'-nl',str(OUT/'wwnames.txt'),'-g','-go',str(folder/'txtp'),'-gw',str(base/'Media'),
    '-gv','100%','-gl','3721600213','-gra','-grf','-gwd','-gd',str(base/'**/*.bnk')]
with (folder/'wwiser.log').open('w',encoding='utf-8') as f:code=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT).returncode
assert code==0
facts=read(OUT/'BankNodeFacts.json');xml=ET.fromstring('<banks>'+(folder/'Banks.xml').read_text(encoding='utf-8')+'</banks>')
for bank in xml:
    for obj in bank.iter('object'):
        name=obj.get('name','');sid=next((f.get('value') for f in obj.findall('field') if f.get('name')=='ulID'),None)
        if not sid or not name.startswith('CAk'):continue
        fact={'type':name,'bank':dict(bank.attrib),'fields':[dict(f.attrib) for f in obj.iter('field')]}
        if name=='CAkRanSeqCntr':
            fact['playlist']=[{f.get('name'):f.get('value') for f in item.findall('field')} for item in obj.iter('object') if any(f.get('name')=='weight' for f in item.findall('field'))]
        if name in ('CAkLayerCntr','CAkAttenuation','CAkFxCustom','CAkAuxBus'):fact['xml']=ET.tostring(obj,encoding='unicode')
        facts[sid]=fact
for p in (folder/'txtp').glob('*.txtp'):shutil.copy2(p,OUT/'BankRecipes08/txtp'/p.name)
(OUT/'BankNodeFacts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
(OUT/'ResourcePlan.json').write_text(json.dumps({'events':resource['events']},indent=2),encoding='utf-8')
native.OUT=OUT;native.EXTRACT=OUT;native.FACTS=facts;native.MEDIA_OVERLAY.update({p.name:p for p in (base/'Media').rglob('*.wem')});native.main()
