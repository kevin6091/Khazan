"""Resolve original zone/point source transforms from cached level exports."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
from prepare_gameplay_audio_scope import OUT,read,refs,package

actors=read(OUT/'HeinMachAudioSourceActors.json');plan=[];cache={}
for r in actors:
    if r['export']['Type'] in ('xxAkSpatialAudioVolume','AkSpatialAudioVolume','AkAmbientSound','xxAkAmbientSound'):
        filename=r.get('file') or r.get('source_file')
        if not filename:print('KEYS',list(r));break
        if filename not in cache:cache[filename]=read(filename)
        data=cache[filename];obj=r['export'];p=obj.get('Properties',{})
        def objref(ref):
            try:return data[int(ref['ObjectPath'].rsplit('.',1)[-1])]
            except (TypeError,KeyError,IndexError,ValueError):return None
        root=objref(p.get('RootComponent'))
        if root is None and p.get('BrushComponent'):root=objref(p['BrushComponent'])
        inner=objref(p.get('InnerBoxComponent_'))
        brush=objref(p.get('Brush'))
        associated=[e for e in data if objref(e.get('Outer'))==obj]
        if not root:
            root=next((e for e in associated if e.get('Type') in ('AkComponent','BrushComponent','BoxComponent','SceneComponent')),None)
        events={pkg for _,pkg in refs(obj)}
        for comp in associated:
            if comp.get('Type') in ('AkComponent','xxLevelVolumeComponent_SoundEvent'):events.update(pkg for _,pkg in refs(comp))
        if not events:continue
        record={'source_file':filename,'source_sha256':hashlib.sha256(Path(filename).read_bytes()).hexdigest(),
                'source_actor':obj['Name'],'type':obj['Type'],'events':sorted(events),'actor':obj,'root':root,
                'inner_box':inner,'brush':brush,'components':associated,
                'location':(root or {}).get('Properties',{}).get('RelativeLocation',{'X':0.,'Y':0.,'Z':0.})}
        plan.append(record)
(OUT/'HeinMachEnvironmentPlan01.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENV PLAN',len(plan),Counter(r['type'] for r in plan))
for r in plan[:4]:print('ENV',r['source_actor'],r['events'],r['location'],'inner',r['inner_box'],'brush',str(r['brush'])[:400])
