from collections import Counter
import json
import re
from prepare_gameplay_audio_scope import EXTRACT, OUT, ROOT, read

rows=read(OUT/'DecodedManifest01.json')
for r in rows:
    if r['status']=='decode_failed' or r.get('clipped_samples',0):
        print('DECODE ISSUE',r['recipe_name'],r['status'],r.get('clipped_samples'),r['decoder_log'][:600])
for rel in ('Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPreparedPlaybackPlan.json',
            'Metadata/GiantCombatFall_20261011/AuthoringPlan.json',
            'Saved/ImportReports/Khazan_DAS_Locomotion_RuntimeBuild.json'):
    p=ROOT/rel
    if p.exists():
        v=read(p)
        print('BINDING PLAN',rel, list(v)[:20] if isinstance(v,dict) else len(v))
        if isinstance(v,dict):
            for k,value in v.items():
                if k in ('events','fall_plan','player_fall','montages','sources','assets','rows'):
                    print('BINDING FIELDS',k,json.dumps(value[:1] if isinstance(value,list) else value,ensure_ascii=False)[:2400])
supp=read(EXTRACT/'Supplement01/MetadataExtractionReport.json')
print('SUPPLEMENT',Counter(r['status'] for r in supp))
print('SUPPLEMENT FAIL',[(r['source'],r.get('error')) for r in supp if r['status']!='ok'][:12])
plan=read(OUT/'ResourcePlan.json')
for name in ('Play_PLYR_Footsteps','Play_PLYR_VO_Dmg'):
    e=next(r for r in plan['events'] if r['name']==name)
    print('EVENT',name,'top fields',list(e['cooked']), 'media',len(e['cooked'].get('Media',[])),
          'leaf example',json.dumps(e['cooked'].get('SwitchContainerLeaves',[])[:1])[:2600])
