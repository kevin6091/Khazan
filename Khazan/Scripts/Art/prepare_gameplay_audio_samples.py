from pathlib import Path
from collections import Counter
import json

root=Path(__file__).resolve().parents[2]
task=root/'Saved/Extracted/GameplayAudio_20261011'
index=json.loads((task/'Index03/AudioPackageIndex.json').read_text(encoding='utf-8'))
files={r['path'] for r in index}
print('chunk1 sound paths:',[r['path'] for r in index if 'chunk1-' in r['archive']])
print('Raw bnk root examples:',[r['path'] for r in index if r['path'].endswith('.bnk')][:4])
sample=task/'Sample01/BBQ/Content/_Kazan_/Sound/Player/Player_Common/Player_VO/Play_PLYR_VO_Dmg.json'
data=json.loads(sample.read_text(encoding='utf-8'))[0]
languages=[item['Key']['LanguageName'] for item in data['EventCookedData']['EventLanguageMap']]
print('Available VO languages:',languages)
requests=[]
for item in data['EventCookedData']['EventLanguageMap']:
    if item['Key']['LanguageName'] not in ['Korean(KR)','English(US)','SFX']:
        continue
    for field,raw_field in [('SoundBanks','SoundBankPathName'),('Media','MediaPathName')]:
        for obj in item['Value'][field]:
            relative=obj[raw_field]
            matches=[f for f in files if f.endswith('/'+relative)]
            assert len(matches)==1,(relative,matches)
            requests.append(matches[0])
    print('Selected language',item['Key']['LanguageName'],len(item['Value']['SoundBanks']),len(item['Value']['Media']))
init=[r['path'] for r in index if r['path'].lower().endswith('/init.bnk')]
assert len(init)==1,init
requests+=init
(task/'RawSampleRequests.json').write_text(json.dumps(sorted(set(requests)),indent=2),encoding='utf-8')
print('Raw sample files:',len(set(requests)))
