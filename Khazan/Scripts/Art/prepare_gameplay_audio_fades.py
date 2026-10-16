"""Original CAkActionPlay linear fade duration, without invented mix values."""
from pathlib import Path
import json
from prepare_gameplay_audio_scope import OUT,read
from prepare_gameplay_audio_native_cues import path_tree

facts=read(OUT/'BankNodeFacts.json')
resources={r['source_package']:r for r in read(OUT/'ResourcePlan.json')['events']}
rows=[]
for cue in read(OUT/'NativeCuePlan01.json')['cues']:
    resource=resources[cue['event_package']]
    event=facts.get(str(resource['cooked']['EventId']),{})
    actions=[facts.get(f['value'],{}) for f in event.get('fields',[]) if f['name']=='ulActionID']
    plays=[a for a in actions if a.get('type')=='CAkActionPlay']
    trees=[n for file in cue['recipes'] for n in path_tree(Path(file).read_text(encoding='utf-8-sig'))]
    def find(nodes,ident):
        for node in nodes:
            if node['id']==ident:return node
            result=find(node['children'],ident)
            if result:return result
    def media(node):
        return {Path(m).stem for m in node['media']} | set().union(*(media(c) for c in node['children']))
    for action in plays:
        fields=action.get('fields',[]);ms=0.;curve=None
        for i,f in enumerate(fields[:-1]):
            if f['name']=='pID' and 'TransitionTime' in f.get('valuefmt',''):ms=float(fields[i+1]['value'])
        curve=next((f for f in fields if f['name']=='eFadeCurve'),None)
        if ms<=0:continue
        target=next(f['value'] for f in fields if f['name']=='idExt')
        node=find(trees,target);assert node,(cue['event_name'],target)
        ids=sorted(media(node));assert ids,(cue['event_name'],target)
        curve_id=int(curve['value']);assert curve_id in (2,4,6),curve
        rows.append({'cue':cue['asset'],'seconds':ms/1000.,'source_package':cue['event_package'],
                     'target':target,'target_media':ids,'curve_id':curve_id,
                     'field':'CAkEvent.ulActionID -> CAkActionPlay.idExt and AkPropBundle pID16 TransitionTime; eFadeCurve',
                     'source':{'action':action,'transition_ms':ms,'curve':curve},
                     'formula':'milliseconds / 1000; source Linear is exact. Native Log1/Exp1 shape is a temporary sqrt(t)/t^2 adapter; source duration is retained.'})
(OUT/'SourcePlayFadePlan01.json').write_text(json.dumps({'fades':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('SOURCE LINEAR PLAY FADES',[(r['cue'].rsplit('/',1)[-1],r['seconds']) for r in rows])
