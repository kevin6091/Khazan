from prepare_gameplay_audio_scope import OUT,ROOT,read
import json
plan=read(OUT/'AudioAuthoringPlan01.json');samples=[]
for family in ('Player','HalberdElite','HeavySwordsman','SwordShield','Swordsman','ApesStoneHandElite','Yetuga'):
    candidates=[e for e in plan['events'] if e['family']==family and e['cue'] and not e['only_local_or_locked'] and
                ('/Attack/' in e['asset'] or family=='Player' and any(k in e['asset'] for k in ('WeakAttack','ChargeAttack','OverFury')))]
    candidates.sort(key=lambda e:(e['start']>0.2,e['clip']['seconds']>4.,e['asset'],e['start']))
    e=candidates[0]
    samples.append({'family':family,'asset':e['asset'],'seconds':e['clip']['seconds'],
                    'expected':[{'start':x['start'],'cue':x['cue'],'state':x['state']} for x in plan['events'] if x['asset']==e['asset'] and x['cue']]})
loops={c['asset'] for c in read(OUT/'NativeCuePlan01.json')['cues'] if c['loop']}
loop=next(e for e in plan['events'] if e['family']=='Player' and e['stop_at_end'] and e['duration']>0.3)
samples.append({'family':'Player','asset':loop['asset'],'seconds':loop['clip']['seconds'],'cancel':True,
    'expected':[{'start':loop['start'],'cue':loop['cue'],'state':True}]})
result={'samples':samples,'submix':'/Game/Audio/Original/Settings/SM_Original','output':str(OUT/'RuntimeAudioCapture'),
        'qa_policy':'Transient montage fixture on actual DevMap actors; no gameplay/asset save. Check real notify dispatch, finite tail and loop cancellation.'}
(OUT/'RuntimeSamples01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNTIME SAMPLES',[(s['family'],s['asset'].rsplit('/',1)[-1],s['seconds'],s.get('cancel')) for s in samples])
