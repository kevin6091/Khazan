from pathlib import Path
import json,hashlib,os,shutil,datetime
m=Path(__file__).resolve().parents[2];o=m/'Metadata/GiantHitOverlay_20261013';w=m.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan'
qa=json.loads((o/'CPU02/Driver.json').read_text(encoding='utf-8'));assert qa['status']=='passed',qa
plan=json.loads((o/'DeliveryPlan.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in plan['assets']:
 p=m/row['relative'];q=w/row['relative'];assert sha(q)==row['work_sha256']
 assert (sha(p) if p.exists() else None)==row['before_sha256'],('Concurrent Main asset edit',row['relative'])
 assert p.resolve().is_relative_to((m/'Content').resolve()) and q.resolve().is_relative_to((w/'Content').resolve())
for row in plan['assets']:
 dst=m/row['relative'];dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_name(dst.name+'.GiantHitDelivery')
 if tmp.exists():assert sha(tmp)==row['work_sha256']
 else:shutil.copy2(w/row['relative'],tmp)
 os.replace(tmp,dst);assert sha(dst)==row['work_sha256']
# Main-compiled objects were linked outside the watched Binaries to avoid editor reloads.
module=Path(qa['actual_loaded_module']);expected=qa['module_sha256'];assert sha(module)==expected
alias=m/'Binaries/Win64'/module.name;assert not alias.exists();shutil.copy2(module,alias)
p=m/'Binaries/Win64/UnrealEditor.modules';b=p.read_bytes();manifest=json.loads(b.decode('utf-8-sig'));manifest['Modules']['Khazan']=alias.name
assert p.read_bytes()==b,'Concurrent manifest change';tmp=p.with_name(p.name+'.GiantHitDelivery');tmp.write_text(json.dumps(manifest,indent=2),encoding='utf-8');os.replace(tmp,p)
receipt=dict(status='applied_to_main_files',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),assets=plan['assets'],main_module=str(alias),module_sha256=expected,note='Running foreign Main editors were not reloaded or controlled. Restart is required for their cached DLL/assets.')
(o/'MainDelivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('Main assets',len(plan['assets']),'fresh Main-object DLL',alias.name)