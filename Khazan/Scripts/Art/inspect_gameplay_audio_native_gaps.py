from pathlib import Path
from collections import Counter
import re
from prepare_gameplay_audio_scope import OUT, EXTRACT, read
from prepare_gameplay_audio_native_cues import parse_recipe,path_tree,walk,FACTS
p=next(p for p in (OUT/'BankRecipes08/txtp').glob('*Footsteps*') if '[kz_apc_switch=kz] [physical_material=pm_snow]' in p.name)
text=p.read_text(encoding='utf-8-sig')
print('PATH LAYERS',[(n['id'],len(n['children']),len(n['signature']),sum(n['signature'].values())) for n in path_tree(text) if n['kind']=='CAkLayerCntr'])
print('BODY GROUPS',[(n['kind'],len(n.get('children',[])),n.get('source_node'),n.get('rtpc_layer')) for n in walk(parse_recipe(p)['graph']) if n['kind']!='wave'])
for sid in ('2492340343','4132611353','3667955469','4163716935'):
    f=FACTS.get(sid)
    print('GAP BANK EVENT',sid,f)
    if f:
        actionids=[r['value'] for r in f['fields'] if r['type']=='tid']
        print('ACTIONS',[(i,FACTS.get(i)) for i in actionids])
plan=read(OUT/'ResourcePlan.json')
print('LOCO GAMEPARAM',[(r['source_package'],r['export'].get('GameParameterCookedData')) for r in plan['gamesyncs'] if str(r['export'].get('GameParameterCookedData',{}).get('ShortId',0) & 0xffffffff) in ('2653406601','3672016584')])
print('SPIN',[(p) for p in read(EXTRACT/'SpinIndex01/TargetedPackageIndex.json') if '/Design/Kazan/' in p and ('UltimateSlash_Loop.uasset' in p or 'UltimateSlash_Air.uasset' in p)])
