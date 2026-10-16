"""Preserve current Main changes; merge only task-touched source from its byte baseline."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import subprocess
import sys

MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'
OUT=MAIN/'Metadata/BeastDodge_20261012'/sys.argv[1]
OUT.mkdir(exist_ok=False)
BASE=MAIN/'Metadata/BeastDodge_20261012/Before'
old=json.loads((MAIN/'Metadata/BeastDodge_20261012/Baseline.json').read_text())['baseline']
receipt={'status':'rebased','at':datetime.now().astimezone().isoformat(),'copied_latest':[],'merged':[],'conflicts':[],'expected_main':{}}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
for name,value in old.items():
    if not name.startswith(('Source/','Config/','Content/')):continue
    src=MAIN/name; dest=WORK/name
    current,ours=sha(src),sha(dest)
    receipt['expected_main'][name]=current
    if current==value or ours==current:continue
    if ours==value:
        if current is None:raise RuntimeError('Main removed '+name+'; preserve explicitly before compiling')
        shutil.copy2(src,dest);receipt['copied_latest'].append(name);continue
    if name.startswith('Source/') and src.suffix in ('.cpp','.h','.cs'):
        assert (BASE/name).is_file()
        result=subprocess.run(['git','merge-file','-p',str(dest),str(BASE/name),str(src)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        snapshot=OUT/'MainBefore'/name;snapshot.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,snapshot)
        if result.returncode==0:dest.write_bytes(result.stdout);receipt['merged'].append(name)
        else:
            conflict=OUT/'Conflicts'/name;conflict.parent.mkdir(parents=True,exist_ok=True);conflict.write_bytes(result.stdout)
            receipt['conflicts'].append(name)
    else:receipt['conflicts'].append(name)
for root in ('Source','Config'):
    for src in (MAIN/root).rglob('*'):
        if not src.is_file():continue
        name=src.relative_to(MAIN).as_posix()
        if name in old:continue
        dest=WORK/name;receipt['expected_main'][name]=sha(src)
        if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);receipt['copied_latest'].append(name)
        elif sha(dest)!=sha(src):receipt['conflicts'].append(name)
if receipt['conflicts']:receipt['status']='conflicts'
(OUT/'Rebase.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='expected_main'},indent=2),flush=True)
raise SystemExit(bool(receipt['conflicts']))
