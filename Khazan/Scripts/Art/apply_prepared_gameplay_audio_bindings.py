"""Hash-guarded delivery after the owned authoring process releases its handles."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=OUT/sys.argv[1]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=read(RUN/'Bindings.json');assert plan['success']
receipt={'time':datetime.datetime.now().astimezone().isoformat(),'rows':[],'pending':[],'conflicts':[]}
for r in plan['combos']:
    if not any(r.get(k) for k in ('player_impacts','monster_guards','object_guards','projectiles')):continue
    path=r['asset'];assert path.startswith('/Game/')
    target=(ROOT/'Content'/(path[6:]+'.uasset')).resolve()
    assert target.is_relative_to((ROOT/'Content').resolve())
    prepared=Path(r['prepared']).resolve();assert prepared.is_relative_to((RUN/'Prepared').resolve())
    assert sha(prepared)==r['prepared_sha256']
    current=sha(target);item={'asset':path,'before_sha256':r['before_sha256'],'prepared_sha256':r['prepared_sha256']}
    if current==r['prepared_sha256']:item['status']='already_applied'
    elif current!=r['before_sha256']:
        item['status']='concurrent_saved_change';receipt['conflicts'].append(path)
    else:
        replace=RUN/'ReplaceAfterExit'/target.relative_to(ROOT)
        replace.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prepared,replace)
        try:
            os.replace(replace,target);assert sha(target)==r['prepared_sha256'];item['status']='applied'
        except PermissionError:
            item['status']='file_locked';receipt['pending'].append(path)
    item['current_sha256']=sha(target);receipt['rows'].append(item)
receipt['success']=not receipt['pending'] and not receipt['conflicts']
name=sys.argv[2] if len(sys.argv)>2 else 'Delivery01.json'
file=RUN/name;assert not file.exists()
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'success':receipt['success'],'rows':len(receipt['rows']),'pending':receipt['pending'],'conflicts':receipt['conflicts']}),flush=True)
