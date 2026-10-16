from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from prepare_gameplay_audio_scope import ROOT,read
import prepare_gameplay_audio_native_cues as native

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
resource=read(OUT/'ResourcePlan.json');r=read(OUT/'Events02/MetadataExtractionReport.json')[0];o=read(r['target'])[0]
events=[]
for lang in o['EventCookedData']['EventLanguageMap']:
    if lang['Key']['LanguageName'] not in ('SFX','Korean(KR)'):continue
    events.append({'source_package':r['source'],'name':o['Name'],'language':lang['Key'],'cooked':lang['Value'],
        'metadata_file':r['target'],'metadata_sha256':hashlib.sha256(Path(r['target']).read_bytes()).hexdigest(),
        'duration_properties':{k:v for k,v in o.items() if any(t in k.lower() for t in ('duration','infinite','attenuation'))}})
base=OUT/'BankSource/BBQ/Content/WwiseAudio'
for row in read(OUT/'Raw02/AudioFileExtractionReport.json'):
    target=base/row['source'].split('/WwiseAudio/',1)[1];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(row['target'],target)
folder=OUT/'BankRecipes09';folder.mkdir(exist_ok=False)
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe',str(PRIOR/'Tools/wwiser.pyz'),
    '-r','-d','xml','-dn',str(folder/'Banks'),'-nl',str(OUT/'wwnames.txt'),'-g','-go',str(folder/'txtp'),'-gw',str(base/'Media'),
    '-gv','100%','-gl','3721600213','-gra','-grf','-gwd','-gd',str(base/'Event/Play_PLYR_DualAxeSword_Swish_L.bnk')]
with (folder/'wwiser.log').open('w',encoding='utf-8') as f:code=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT).returncode
assert code==0
# The existing parser reads the first recipe directory. Copy just the new left
# recipes into its task-local folder, never into the original frozen reports.
for p in (folder/'txtp').glob('*.txtp'):shutil.copy2(p,OUT/'BankRecipes08/txtp'/p.name)
resource['events']+=events;(OUT/'ResourcePlan.json').write_text(json.dumps(resource,indent=2),encoding='utf-8')
native.OUT=OUT;native.EXTRACT=OUT;native.FACTS=read(OUT/'BankNodeFacts.json')
native.MEDIA_OVERLAY.update({p.name:p for p in (base/'Media').rglob('*.wem')})
native.main()
