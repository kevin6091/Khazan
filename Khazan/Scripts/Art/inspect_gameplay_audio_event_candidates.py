from collections import Counter
import json
import re
from prepare_gameplay_audio_scope import EXTRACT, OUT, ROOT, read, SourceCache

index=read(EXTRACT/'Index03/AudioPackageIndex.json')
paths=[r['path'] for r in index if r['path'].endswith('.uasset')]
for term in ('footstep','ftsp','impact','heal','guard','dodge','roll','cloth','rustle','fire','torch'):
    hits=[p for p in paths if '/Sound/Player/' in p and term in p.lower()]
    print('PLAYER EVENTS',term, [p.rsplit('/',1)[-1][:-7] for p in hits][:35])
print('PLAYER DIRECTORIES',Counter('/'.join(p.split('/')[6:-1]) for p in paths if '/Sound/Player/' in p).most_common(12))
for term in ('object','interaction','bonfire','torch','fire_loop','footstep'):
    hits=[p for p in paths if term in p.lower() and '/Sound/' in p and '/Monster/' not in p and '/Player/' not in p]
    print('OTHER EVENTS',term,[p.rsplit('/',1)[-1][:-7] for p in hits][:30])
current=read(OUT/'CurrentAssets02/CurrentAssets.json')['assets']
print('PLAYER MISSING SOURCE MAP',[(c['asset'],c.get('import_source')) for c in current if
       '/Player/' in c['asset'] and c['type']=='AnimSequence' and not c['metadata'].get('OriginalPackage')][:45])
cache=SourceCache()
p='BBQ/Content/_Kazan_/Design/Kazan/Reaction/DualAxeSword/AC_Kazan_DualAxeSword_Off_DamageNormal_D_F'
data=cache.get(p)
for i,o in enumerate(data[0] if data else []):
    prop=o.get('Properties',{})
    if o.get('Type')=='AnimComposite':
        print('REACTION TRACK',prop.get('AnimationTrack'),prop.get('DilationCurve'),prop.get('SourceDilationCurve'))
        print('REACTION AUDIO TIMES',[(n.get('NotifyName'),n.get('LinkValue'),n.get('Duration'),n.get('Notify')) for n in prop.get('Notifies',[]) if 'Ak' in n.get('NotifyName','')])
    elif 'AkEvent' in o.get('Type',''):
        print('REACTION EVENT',i,prop)
