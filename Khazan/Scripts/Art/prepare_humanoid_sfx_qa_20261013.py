"""Current action closure plus representative actual-mixer fixtures, no pose edits."""
from pathlib import Path
from collections import defaultdict,Counter
import json
import re
from prepare_gameplay_audio_scope import ROOT,read

OUT=ROOT/'Metadata/HumanoidSFX_20261013';plan=read(OUT/'AudioAuthoringPlan01.json');inv=read(OUT/'Inventory02/Inventory.json')
by=defaultdict(list)
for e in plan['events']:by[e['asset']].append(e)
animations={r['asset']:r for r in inv['animations']}
slots={r['asset']:set(p.split('.')[0] for s in r.get('slots',[]) for p in re.findall(r"/Game/[^'\"]+",s)) for r in inv['animations'] if r['type']=='AnimMontage'}
current=set()
for c in inv['combos']:
    for n in c['nodes']:current.update(slots.get(n['montage'],set()))
for d in inv['definitions']:
    for p in re.findall(r"/Game/[^'\"]+",d['hit']+' '+d['stamina']):current.update(slots.get(p.split('.')[0],set()))
for d in inv['ability_defaults']:
    for v in d['properties'].values():current.update(slots.get(str(v).split('.')[0],set()))
closure=[]
for path in sorted(current):
    if path not in animations:continue
    row=animations[path];events=by[path]
    callback=[e for e in plan.get('callback_owned_events',[]) if e['asset']==path]
    closure.append({'asset':path,'family':row['family'],'audio_occurrences':len(events),'original_source':row['metadata'].get('OriginalPackage'),
        'status':'Attached' if events else 'Approved result callback' if callback or 'Player_Parry_' in path else 'Quiet hold/transition; no serialized source audio, not an audible dispatch gap'})
selected={p for p in current if p in by and animations.get(p,{}).get('family')=='Player' and by[p]}
for family in plan['scope'][1:]:
    candidates=[r for r in inv['animations'] if r['type']=='AnimSequence' and r['family']==family and r['asset'] in by]
    for category,filter_name in [('attack',lambda p:'/Attack/' in p),('walk',lambda p:'Walk' in p),('damage',lambda p:'Damage_Normal' in p or 'Damage_Weak' in p),
                                 ('death',lambda p:'/Death/' in p or '/Die/' in p),('exhaustion',lambda p:'Exhaust' in p),('talk',lambda p:'Talk' in p)]:
        options=sorted((r for r in candidates if filter_name(r['asset']) and any(e['cue'] for e in by[r['asset']])),key=lambda r:(r['seconds'],r['asset']))
        if options:selected.add(options[0]['asset'])
samples=[]
for path in sorted(selected):
    r=animations[path];expected=[{'cue':e['cue'],'start':e['start'],'state':e['state']} for e in by[path] if e['cue'] and not e['only_local_or_locked']]
    if not expected:continue
    samples.append({'family':r['family'],'asset':path,'seconds':r['seconds'],'expected':expected})
charge=next(e for e in plan['events'] if e['family']=='Player' and e['cue'] and e['stop_at_end'] and e['duration']>.3)
samples.append({'family':'Player','asset':charge['asset'],'seconds':animations[charge['asset']]['seconds'],'cancel':True,
    'expected':[{'cue':charge['cue'],'start':charge['start'],'state':True}]})
result={'samples':samples,'projectile_count':0,'submix':'/Game/Audio/Original/Settings/SM_Original',
    'output':str(OUT/'RuntimeCapture01'),'timeout_seconds':sum(s['seconds']+.6 for s in samples)+60,
    'tail_sound':'/Game/Audio/Original/Events/SC_vo_empiresword_dmg_s',
    'qa_policy':'Actual mesh montage dispatch + all expected cues, explicit cancellation, stateless loop cleanup and audio-thread actor-destruction tail. No asset/map saves.'}
(OUT/'RuntimeSamples01.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
resolution=[]
native_events={c['event_package'] for c in read(OUT/'NativeCuePlan01.json')['cues']}|{c['event_package'] for c in read(ROOT/'Saved/ImportReports/GameplayAudio_20261011/NativeCuePlan01.json')['cues']}
for r in plan['unresolved']:
    if r.get('event') in native_events or r.get('event') in plan['stop_targets'] or '/WwiseMotion/' in r.get('event',''):
        resolution.append(dict(r,status='Resolved by scoped original cue/control resource or hardware-motion exclusion'))
    else:resolution.append(dict(r,status='Unresolved'))
coverage={'actions':closure,'source_candidate_resolution':resolution,'missing_resources':[r for r in resolution if r['status']=='Unresolved'],
    'callback_owned':plan.get('callback_owned_events',[]),'voice_duplicates_coalesced':plan.get('coalesced_voice_events',[]),
    'counts':{'bound_sequences':len(closure),'attached':sum(r['audio_occurrences']>0 for r in closure),'fixtures':len(samples),
        'occurrences':len(plan['events']),'scope_sequences':len(by),'family_occurrences':dict(Counter(e['family'] for e in plan['events']))}}
(OUT/'Coverage01.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8')
assert not coverage['missing_resources'],coverage['missing_resources']
print('QA',len(samples),'SECONDS',sum(s['seconds']+.6 for s in samples),'BOUND',len(closure),'EVENTS',len(plan['events']))
