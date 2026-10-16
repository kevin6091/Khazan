import json
from pathlib import Path
from prepare_gameplay_audio_scope import EXTRACT,OUT,ROOT,read
index=read(EXTRACT/'Index03/AudioPackageIndex.json')
def fnv(name):
    h=2166136261
    for c in name.lower().encode():h=((h*16777619)&0xffffffff)^c
    return h
parameters=[r['path'].removesuffix('.uasset') for r in index if '/GameParameters/' in r['path'] and r['path'].endswith('.uasset')]
matched=[p for p in parameters if fnv(p.rsplit('/',1)[-1]) in (2653406601,3672016584)]
print('RTPC MATCH',[(p,fnv(p.rsplit('/',1)[-1])) for p in matched])
spin=[p.removesuffix('.uasset') for p in read(EXTRACT/'SpinIndex01/TargetedPackageIndex.json') if '/Design/Kazan/' in p and ('UltimateSlash_Loop.uasset' in p or 'UltimateSlash_Air.uasset' in p)]
(EXTRACT/'Sources03Requests.json').write_text(json.dumps(spin+matched,indent=2),encoding='utf-8')
print('SOURCE REQUESTS',len(spin+matched))
facts=read(OUT/'BankNodeFacts.json')
for sid in ('876449612','790738164','17876106','385049427','320290709','25845891','356943585'):
    f=facts.get(sid,{})
    print('TARGET',sid,f.get('type'),[(x['name'],x.get('hashname') or x.get('valuefmt') or x['value']) for x in f.get('fields',[]) if x['type']=='tid' or x['name'] in ('ulSwitchGroupID','ulDefaultSwitch','ulStateGroupID','eGroupType')])
