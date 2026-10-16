"""Deliver exactly the prepared files, guarded by hash CAS and actual private proofs."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,os
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan');ROOT=MAIN/'Metadata/MonsterPresentationRepair_20261011';PREP=ROOT/'DeliveryPreparation'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
plan=read(PREP/'Plan.json');assert plan['status']=='prepared' and not plan['conflicts']
assert read(ROOT/'QuickVisual04/Driver.json')['status']=='passed'
assert read(ROOT/'DissolveGrain02/DissolveGrain.json')['status']=='passed'
assert read(ROOT/'QuickVisual05/Driver.json')['status']=='passed'
assert read(ROOT/'SavedAudit03/SavedAudit.json')['status']=='passed'
assert read(ROOT/'NativeParticleAuthor04/Driver.json')['status']=='passed'
a=read(ROOT/'AudioCensusMainBefore01/AudioCensus.json');b=read(ROOT/'AudioCensusWork02/AudioCensus.json');assert a['status']==b['status']=='passed' and a['animations']==b['animations']
assert len(plan['source'])==10 and len(plan['assets'])==59
OUT=ROOT/'MainDelivery';OUT.mkdir(exist_ok=True)
for r in plan['source']+plan['assets']:
    current=sha(MAIN/r['path']);assert current in [r['before'],r['after']],('Concurrent Main change',r['path'])
    if current==r['after'] and r['after']!=r['before'] and r['before'] is not None:
        assert sha(OUT/'Before'/r['path'])==r['before'],('Already applied without task backup',r['path'])
    source=(PREP/'Staged' if r in plan['source'] else WORK)/r['path'];assert sha(source)==r['after'],('Staged change',r['path'])
rows=[]
for r in plan['source']+plan['assets']:
    target=MAIN/r['path'];source=(PREP/'Staged' if r in plan['source'] else WORK)/r['path'];backup=OUT/'Before'/r['path']
    if sha(target)!=r['after']:
        assert sha(target)==r['before'],('Concurrent update at write',r['path'])
        if target.exists():
            if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            assert sha(backup)==r['before'],('Task backup changed',r['path'])
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.kzmpr-20261011.tmp');shutil.copy2(source,temp);assert sha(temp)==r['after']
        assert sha(target)==r['before'],('Concurrent update before replace',r['path'])
        os.replace(temp,target);assert sha(target)==r['after']
    rows.append(r)
    (OUT/'Progress.json').write_text(json.dumps({'status':'Applying','applied':len(rows),'last':r['path']},ensure_ascii=False,indent=2),encoding='utf-8')
receipt={'status':'MainFilesAppliedBuildAndFreshQAStillRequired','utc':datetime.now(timezone.utc).isoformat(),'source_files':len(plan['source']),'asset_packages':len(plan['assets']),'concurrent_audio_notifies_preserved':a['notify_count'],'rows':rows,'private_author_delivered':False,'new_runtime_files':0}
(OUT/'Receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='rows'},ensure_ascii=False))
