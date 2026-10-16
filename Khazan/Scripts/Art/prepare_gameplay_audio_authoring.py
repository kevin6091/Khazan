"""Attach current clip timelines to native cues and source stop targets."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
from prepare_gameplay_audio_scope import ROOT,OUT,EXTRACT,read
from prepare_gameplay_audio_native_cues import path_tree

playback=read(OUT/'PlaybackPlan.json');native=read(OUT/'NativeCuePlan01.json');facts=read(OUT/'BankNodeFacts.json');resources=read(OUT/'ResourcePlan.json')
cue_by_package={c['event_package']:c for c in native['cues']}
node_to_cues={}
for c in native['cues']:
    for filename in c['recipes']:
        for n in path_tree(Path(filename).read_text(encoding='utf-8-sig')):
            node_to_cues.setdefault(n['id'],set()).add(c['asset'])
nonplay={};stop_targets={}
for event in resources['events']:
    if event['source_package'] in cue_by_package:continue
    eventid=str(event['cooked']['EventId']);f=facts.get(eventid,{})
    actions=[facts.get(x['value'],{}) for x in f.get('fields',[]) if x['name']=='ulActionID']
    stops=[x for x in actions if x.get('type')=='CAkActionStop']
    soundtargets=set();fade=[]
    for a in stops:
        for x in a.get('fields',[]):
            if x['name']=='idExt':soundtargets.update(node_to_cues.get(x['value'],set()))
        fields=a.get('fields',[])
        for i,x in enumerate(fields[:-1]):
            if x['name']=='pID' and 'TransitionTime' in x.get('valuefmt',''):
                fade.append(float(fields[i+1]['value'])/1000.)
    stop_targets[event['source_package']]={'sounds':sorted(soundtargets),'fade_seconds':max(fade,default=0.),'actions':stops}
    nonplay[event['source_package']]={'event_id':eventid,'types':[a.get('type') for a in actions],'is_stop':bool(stops)}
events=[];skipped=[]
for e in playback['events']:
    c=cue_by_package.get(e['event_package']);stop=stop_targets.get(e['event_package'],{})
    if not c and not stop.get('sounds'):
        skipped.append(dict(e,reason='Source event is state/mix control or unmapped stop',control=nonplay.get(e['event_package'])));continue
    clipend=e['clip']['seconds'];duration=max(0.,e['end']-e['start']);endcue=cue_by_package.get(e['end_event_package'])
    endstop=stop_targets.get(e['end_event_package'],{})
    isloop=c and c['loop'];state=e['is_state'] and duration>0 or isloop
    if isloop and duration==0:duration=clipend-e['start']
    events.append(dict(e,cue=c['asset'] if c else '',end_cue=endcue['asset'] if endcue else '',
        duration=duration,state=bool(state),stop_sounds=stop.get('sounds',[]),stop_fade_seconds=stop.get('fade_seconds',0.),
        stop_at_end=bool(isloop or endstop.get('sounds')),fade_seconds=endstop.get('fade_seconds',0.) or (0.08 if isloop else 0.),
        fade_source='Source stop TransitionTime ms /1000' if endstop.get('fade_seconds') else ('Temporary 80ms cancellation anti-click, native-loop adapter' if isloop else 'Natural finite tail'),
        only_local_or_locked=bool(e['source']['properties'].get('bCheckTargetCondition'))))
paths=sorted(set(e['asset'] for e in events))
before={}
for path in paths:
    p=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset')
    assert p.exists(),p
    before[path]={'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
plan={'events':events,'skipped_control_events':skipped,'nonplay_events':nonplay,'stop_targets':stop_targets,
      'before_assets':before,'counts':{'notify_events':len(events),'affected_sequences':len(paths),'point':sum(not e['state'] for e in events),'state':sum(e['state'] for e in events)},
      'timing_policy':'Source LinkValue/EndLink -> source trim/playrate/dilation -> current baked clip, legacy3 frame-clock conversion; no pose/rate/root changes.'}
(OUT/'AudioAuthoringPlan01.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('AUTHOR',plan['counts'],'CONTROL SKIP',len(skipped),Counter(e['event_package'].rsplit('/',1)[-1] for e in skipped))
print('TIMED STOP',sum(bool(e['stop_sounds']) for e in events),'LOOP WINDOWS',sum(e['stop_at_end'] for e in events))
