from pathlib import Path
import json
import xml.etree.ElementTree as ET
import zipfile
import struct
from prepare_gameplay_audio_scope import OUT, EXTRACT, read, SourceCache

plan=read(OUT/'ResourcePlan.json')
event=next(e for e in plan['events'] if e['name']=='Play_PLYR_VO_Dmg')
print('DAMAGE VO',event['cooked']['EventId'],event['cooked']['SoundBanks'],event['language'])
bank=EXTRACT/'Raw03/BBQ/Content/WwiseAudio'/event['cooked']['SoundBanks'][0]['SoundBankPathName']
print('DAMAGE BANK',bank,bank.exists())
print('DAMAGE BANK HEADER',struct.unpack('<III',bank.read_bytes()[8:20]))
for folder in ('BankRecipes06','BankRecipes07'):
    text=(OUT/folder/'Banks.xml').read_text(encoding='utf-8')
    start=text.find('filename="Play_PLYR_VO_Dmg.bnk"')
    print('BANK LANGUAGE XML',folder,text[start:start+1800])
cache=SourceCache()
for name in ('CA_P_Kazan_DualAxeSword_Run_F','CA_P_Kazan_DualAxeSword_Sprint_F','CA_P_Kazan_DualAxeSword_Walk_F'):
    p='BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/'+name
    d=cache.get(p)[0][0]
    print('LOOP SOURCE',name,{k:v for k,v in d['Properties'].items() if any(x in k.lower() for x in ('length','frame','rate','dilation'))})
curfile=OUT/'CurrentAssets03/CurrentAssets.json'
if curfile.exists():
    cur=read(curfile)
    print('CURRENT03',cur.get('success'),cur.get('error'))
    for c in cur['assets']:
        if c['asset'].split('.')[0].endswith(('DAS_Player_Run_Loop','DAS_Player_Walk_Loop','DAS_Player_Sprint_Loop')):
            print('LOOP CURRENT',c['asset'],{k:v for k,v in c.items() if k not in ('notifies','metadata')})
with zipfile.ZipFile(OUT/'Tools/wwiser.pyz') as z:
    for name in z.namelist():
        if name.endswith('wlang.py'):
            print('LANG SOURCE',z.read(name).decode()[-6500:])
