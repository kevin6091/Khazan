"""Install only the frozen selected sources/assets after an exact Main preflight."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import subprocess

MAIN=Path(__file__).resolve().parents[2]
OUT=MAIN/'Metadata/BeastDodge_20261012/Completion'
plan=json.loads((OUT/'DeliveryPlan.json').read_text())
WORK=Path(plan['work'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
query="Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'\" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
raw=subprocess.check_output(['powershell','-NoProfile','-Command',query],text=True,encoding='utf-8',errors='replace').strip()
processes=json.loads(raw) if raw else []
if isinstance(processes,dict):processes=[processes]
for p in processes:
    assert str(MAIN/'Khazan.uproject').lower() not in (p.get('CommandLine') or '').lower(), 'Main editor is open; no files installed'
prepared=[]
for row in plan['files']:
    src=WORK/row['path'];dest=MAIN/row['path']
    assert src.resolve().is_relative_to(WORK) and dest.resolve().is_relative_to(MAIN)
    assert sha(dest)==row['expected_main'],'Main changed: '+row['path']
    data=src.read_bytes();assert hashlib.sha256(data).hexdigest()==row['prepared_sha256']
    prepared.append((row,dest,data))
receipt={'status':'installing','at':datetime.now().astimezone().isoformat(),'files':[],'binary_copied':False,'maps_written':0,'source_vfx_packages_written':0}
for row,dest,data in prepared:
    assert sha(dest)==row['expected_main'],'Concurrent Main mutation: '+row['path']
    if dest.exists():
        before=OUT/'InstallBefore'/row['path'];before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(dest.read_bytes())
    dest.parent.mkdir(parents=True,exist_ok=True)
    temporary=dest.with_name(dest.name+'.beast20261012.tmp');assert not temporary.exists()
    temporary.write_bytes(data);os.replace(temporary,dest)
    assert sha(dest)==row['prepared_sha256']
    receipt['files'].append(row)
    (OUT/'InstallReceipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['status']='installed'
(OUT/'InstallReceipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'status':'installed','files':len(prepared),'binary_copied':False}),flush=True)
