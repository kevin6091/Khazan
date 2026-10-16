"""Fresh current project with only this task's writable assets isolated."""
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Metadata/HumanoidSFX_20261013'
WORK=ROOT.parent.parent/'Khazan_HumanoidSFXWork_20261013'/'Khazan'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plan=read(OUT/'AudioAuthoringPlan01.json');inventory=read(OUT/'Inventory02/Inventory.json')
targets={e['asset'] for e in plan['events']+plan.get('callback_owned_events',[])}
targets.update(c['asset'] for c in inventory['combos'] if any(n['windows'] for n in c['nodes']))
targets.update(r['class'].split('.')[0] for r in inventory['ability_defaults'] if '/Player/Dodge/' in r['class'])
assert not (OUT/'Stage01.json').exists(),'An isolated stage is already recorded; resume it.'
WORK.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'Khazan.uproject',WORK/'Khazan.uproject')
for directory in ('Config','Binaries','Plugins'):
    if directory=='Plugins' and (WORK/directory).exists():continue
    shutil.copytree(ROOT/directory,WORK/directory,dirs_exist_ok=True,copy_function=shutil.copy2 if directory in ('Config','Binaries') else os.link)
# Scripts remain the current Main scripts. Only their project destination is
# switched by the runner; evidence and metadata remain under Main.
assert (WORK/'Metadata').resolve()==(ROOT/'Metadata').resolve(),'Create the task Metadata directory junction before staging.'
rows=[];links=0
for source in (ROOT/'Content').rglob('*'):
    if not source.is_file():continue
    relative=source.relative_to(ROOT);target=WORK/relative;target.parent.mkdir(parents=True,exist_ok=True)
    asset='/Game/'+source.relative_to(ROOT/'Content').with_suffix('').as_posix()
    if source.suffix=='.uasset' and asset in targets:
        shutil.copy2(source,target)
        rows.append({'asset':asset,'relative':relative.as_posix(),'baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    else:os.link(source,target);links+=1
assert len(rows)==len(targets),(len(rows),len(targets))
(OUT/'Stage01.json').write_text(json.dumps({'project':str(WORK),'isolated':rows,'hardlinks':links,
    'policy':'Fresh current Main baseline. Only scoped audio assets are independently writable; no old prepared payload reused.'},indent=2),encoding='utf-8')
print('ISOLATED',len(rows),'HARDLINKS',links,'PROJECT',WORK)
