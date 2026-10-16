from prepare_gameplay_audio_scope import OUT,read
from prepare_gameplay_audio_native_cues import walk
p=read(OUT/'NativeCuePlan01.json');facts=read(OUT/'BankNodeFacts.json')
for cue in p['cues']:
    for n in walk(cue['graph']):
        if n['kind']=='sequence' and len(n.get('children',[]))>1:
            sid=n.get('source_node');f=facts.get(sid,{})
            print('SEQUENCE',cue['event_name'],len(n['children']),sid,[(x['name'],x.get('valuefmt') or x['value']) for x in f.get('fields',[]) if x['name'] in ('eMode','bIsContinuous','sLoopCount','wAvoidRepeatCount')],cue['source']['duration_properties'])
print('RUN OCC',[{'type':e['source']['type'],'asset':e['asset'],'props':e['source']['properties']} for e in read(OUT/'PlaybackPlan.json')['events'] if e['event_package'].endswith('/vo_kz_effort_run')])
