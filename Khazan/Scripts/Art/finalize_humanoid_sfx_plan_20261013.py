from pathlib import Path
import json
import re
from prepare_gameplay_audio_scope import ROOT,read
from prepare_gameplay_audio_native_cues import path_tree

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
plan=read(OUT/'PlaybackPlan01.json');base=read(PRIOR/'AudioAuthoringPlan01.json')
native=read(PRIOR/'NativeCuePlan01.json')['cues']+read(OUT/'NativeCuePlan01.json')['cues']
cues={c['event_package']:c for c in native};facts=read(OUT/'BankNodeFacts.json')
controls=dict(base['stop_targets']);node_to_cues={}
for c in native:
    for f in c['recipes']:
        for n in path_tree(Path(f).read_text(encoding='utf-8-sig')):node_to_cues.setdefault(n['id'],set()).add(c['asset'])
for r in read(OUT/'ResourcePlan.json')['events']:
    if r['source_package'] in cues:continue
    f=facts.get(str(r['cooked']['EventId']),{});actions=[facts.get(x['value'],{}) for x in f.get('fields',[]) if x['name']=='ulActionID']
    stops=[a for a in actions if a.get('type')=='CAkActionStop'];targets=set();fades=[]
    for a in stops:
        fs=a['fields']
        for x in fs:
            if x['name']=='idExt':targets.update(node_to_cues.get(x['value'],[]))
        for i,x in enumerate(fs[:-1]):
            if x['name']=='pID' and 'TransitionTime' in x.get('valuefmt',''):fades.append(float(fs[i+1]['value'])/1000.)
    controls[r['source_package']]={'sounds':sorted(targets),'fade_seconds':max(fades,default=0),'actions':stops}
events=[];excluded=[]
for e in plan['events']:
    c=cues.get(e['event_package']);stop=controls.get(e['event_package'],{});end=cues.get(e['end_event_package']);endstop=controls.get(e['end_event_package'],{})
    if '/WwiseMotion/' in e['event_package']:
        excluded.append(dict(e,reason='Original hardware motion feedback; not an audible SFX'));continue
    if not c and not stop.get('sounds'):
        excluded.append(dict(e,reason='Control without resolved audible target'));continue
    loop=bool(c and c['loop']);is_state=e.get('is_state',e.get('state',False)) or loop
    duration=max(0.,e['end']-e['start'])
    if loop and not duration:
        inv=next(r for r in read(OUT/'Inventory02/Inventory.json')['animations'] if r['asset']==e['asset']);duration=inv['seconds']-e['start']
    # TEMP 80ms anti-click minimum only for source stop/cancel. Finite one-shots
    # continue through montage transitions with their original natural tail.
    stop_fade=max(.08,float(stop.get('fade_seconds',0))) if stop.get('sounds') else 0.
    end_fade=max(.08,float(endstop.get('fade_seconds',0))) if loop or endstop.get('sounds') else 0.
    events.append(dict(e,cue=c['asset'] if c else '',end_cue=end['asset'] if end else '',state=is_state and duration>0,
        duration=duration,stop_sounds=stop.get('sounds',[]),stop_fade_seconds=stop_fade,
        stop_at_end=bool(loop or endstop.get('sounds')),fade_seconds=end_fade))
plan.update(events=events,excluded_control_events=excluded,stop_targets=controls,
            counts=dict(plan['counts'],authored=len(events)),numeric_policy='Original raw fields and existing inverse_map; explicit TEMP voice .85/foot .90/weapon1, stop minimum.08s, reaction-start0.')
(OUT/'AudioAuthoringPlan01.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('AUTHOR_EVENTS',len(events),'TRACKS',len(set(e['asset'] for e in events)),'EXCLUDED',len(excluded),[(e['event_package'].rsplit('/',1)[-1],e['reason']) for e in excluded])
