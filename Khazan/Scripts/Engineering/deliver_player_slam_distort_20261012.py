"""CAS-deliver only the verified small Niagara extension and two saved assets."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes,hashlib,json,os,shutil
MAIN=Path(__file__).resolve().parents[2];WORK=MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan';OUT=MAIN/'Metadata/PlayerSlamDistort_20261012'
FILES=['Source/Khazan/'+p for p in ['Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Tests/KZCombatPresentationPIETest.cpp']]
FILES+=['Content/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack.uasset','Content/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort.uasset']
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
assert read('Saved03/SavedAudit.json')['success']
assert read('PrivatePIE05/Driver.json')['status']=='passed'
assert read('PrivatePIE05/Native/Result.json')['passed']
assert read('Alpha01/AlphaRefinement.json')['success']
FILES+=['Content/'+p.split('.')[0].removeprefix('/Game/')+'.uasset' for p in read('Alpha01/AlphaRefinement.json')['saved'] if 'NS_Player_Plunge_ParringDistort' not in p]
baseline=dict(read('Baseline.json')['files']);baseline.update(read('MainMergeBaseline.json')['files']);rows=[]
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateFileW.restype=ctypes.c_void_p
kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
for rel in FILES:
    target=MAIN/rel;source=WORK/rel
    assert target.resolve().is_relative_to(MAIN.resolve()) and source.resolve().is_relative_to(WORK.resolve())
    before=baseline.get(rel);current=sha(target) if target.exists() else None;after=sha(source)
    assert current in [before,after],('Concurrent Main change',rel,current,before)
    if target.exists():
        handle=kernel.CreateFileW(str(target),0x10000,0x7,None,3,0x80,None)
        if handle==ctypes.c_void_p(-1).value:raise OSError(ctypes.get_last_error(),'Selected file locked',str(target))
        kernel.CloseHandle(handle)
    rows.append({'file':rel,'before':before,'after':after})
for row in rows:
    target=MAIN/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha(target)==row['after']:continue
    temp=target.with_name(target.name+'.slam_distort.tmp')
    shutil.copyfile(WORK/row['file'],temp);assert sha(temp)==row['after'];os.replace(temp,target)
(OUT/'Delivery.json').write_text(json.dumps({'status':'MainDeliveredPendingCurrentBuildAndFreshVerification','utc':datetime.now(timezone.utc).isoformat(),'files':rows,'private_dll_delivery':0,'config_delivery':0},indent=2)+'\n',encoding='utf-8')
print('SLAM_DISTORT_MAIN_DELIVERED',len(rows),flush=True)
