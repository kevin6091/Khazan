"""Preflight every selected package and source before merging the verified repair."""
from pathlib import Path
import hashlib,json,ctypes,shutil,os
P=Path(__file__).resolve().parents[2];W=P.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan';O=P/'Metadata/AnimationTimingKnockback_20261012'
def read(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read('AuthorFinal/NativeAuthor.json')['success']
assert read('PrivateSaved03/SavedAudit.json')['success']
assert read('KnockbackAfter02/KnockbackRuntime.json')['passed']
assert read('PrivateBuild11/Exit.json')['exit']==0
baseline=dict(read('Baseline.json')['files']);baseline.update(read('AssetMergeBaseline.json')['files']);plan=read('Plan.json');kb=read('KnockbackBaseline.json');runtime=read('RuntimeMergeBaseline.json')
targets={r:h for r,h in baseline.items() if r.startswith('Content/')}
targets.update(kb['files']);targets[kb['new_asset']]=None
targets.update({r:runtime['files'][r] for r in runtime['delivery']})
for name in ['KZAnimationTimingEditor.cpp','KZKnockbackPIETest.cpp']:targets['Source/Khazan/Tests/'+name]=None
build='Source/Khazan/Khazan.Build.cs';old=(P/build).read_text(encoding='utf-8');new=old
if '"MovieScene"' not in old:
 assert old.count('"Json", "UnrealEd"')==1
 new=old.replace('"Json", "UnrealEd"','"Json", "UnrealEd", "MovieScene"')
 (O/'MainBuildCandidate.cs').write_text(new,encoding='utf-8');targets[build]=sha(P/build)
kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.restype=ctypes.c_void_p
kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
rows=[];conflicts=[];locks=[]
for r,before in targets.items():
 src=O/'MainBuildCandidate.cs' if r==build else W/r;dst=P/r
 assert dst.resolve().is_relative_to(P.resolve()) and src.is_file()
 after=sha(src);current=sha(dst) if dst.exists() else None
 if current not in [before,after]:conflicts.append({'file':r,'baseline':before,'current':current,'candidate':after})
 if dst.exists():
  h=kernel.CreateFileW(str(dst),0x10000,0x7,None,3,0x80,None)
  if h==ctypes.c_void_p(-1).value:locks.append({'file':r,'win32_error':ctypes.get_last_error()})
  else:kernel.CloseHandle(h)
 rows.append({'file':r,'before':before,'after':after,'source':str(src)})
preflight={'conflicts':conflicts,'locks':locks,'files':rows,'product_writes':0}
(O/'DeliveryPreflight.json').write_text(json.dumps(preflight,indent=2)+'\n',encoding='utf-8')
if conflicts or locks:raise RuntimeError('Preserved Main; conflicts='+str(len(conflicts))+' locks='+str(len(locks)))
for row in rows:
 dst=P/row['file'];src=Path(row['source']);dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and sha(dst)==row['after']:continue
 if dst.exists():
  backup=O/'MainBeforeDelivery'/row['file'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
 temp=dst.with_name(dst.name+'.timing_knockback.tmp');shutil.copyfile(src,temp);assert sha(temp)==row['after'];os.replace(temp,dst)
(O/'Delivery.json').write_text(json.dumps({'status':'MainDeliveredPendingBuildAndFreshVerification','files':rows,'dll_delivery':0,'config_delivery':0},indent=2)+'\n',encoding='utf-8')
print('MAIN_TIMING_KNOCKBACK_DELIVERED',len(rows),flush=True)
