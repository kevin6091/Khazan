from pathlib import Path
from collections import Counter
import re
import zipfile
from prepare_gameplay_audio_scope import OUT, EXTRACT, read

with zipfile.ZipFile(OUT/'Tools/wwiser.pyz') as archive:
    for name in archive.namelist():
        if name.endswith('.py'):
            content=archive.read(name).decode('utf-8')
            if 'incorrect master volume' in content:
                lines=content.splitlines()
                i=next(i for i,v in enumerate(lines) if 'incorrect master volume' in v)
                print('VOLUME PARSER',name,'\n'.join(lines[max(0,i-30):i+4]))
            if 'selected localized bank' in content:
                lines=content.splitlines()
                i=next(i for i,v in enumerate(lines) if 'selected localized bank' in v)
                print('LANGUAGE SELECT',name,'\n'.join(lines[max(0,i-22):i+4]))
files=list((OUT/'BankRecipes01/txtp').glob('*.txtp'))
print('RECIPES',len(files),'switches',Counter(s for p in files for s in re.findall(r'\[([^\]]+)\]',p.stem)).most_common(12))
for term in ('VO_Dmg','pm_snow','Forest01','dualaxesword_weakatk01','footstep_walk'):
    matches=[p for p in files if term.lower() in p.name.lower()]
    print('SAMPLE',term,[p.name for p in matches[:3]])
    if matches:
        text=matches[0].read_text(encoding='utf-8-sig')
        print('BODY','\n'.join(text.splitlines()[:12]))
        print('EVENT IDS',re.findall(r'CAkEvent\[\d+\] (\d+)',text))
plan=read(OUT/'ResourcePlan.json')
for e in plan['events']:
    if e['name']=='Play_PLYR_VO_Dmg':
        print('DAMAGE VO',e['cooked']['EventId'],e['cooked']['SoundBanks'],e['language'])
print('SELECTED SWITCHES',[(g['export']['Name'],g['export'].get('GroupValueCookedData')) for g in plan['gamesyncs'] if 'kz' in g['export']['Name'].lower()])
