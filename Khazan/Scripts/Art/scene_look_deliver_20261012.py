"""Hash-guarded selected Content delivery only. No source, config or editor control."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes,hashlib,json,os,shutil,sys
MAIN=Path(__file__).resolve().parents[2];WORK=MAIN.parent.parent/'Khazan_SceneLookWork_20261012/Khazan';OUT=MAIN/'Metadata/SceneLook_20261012'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def files():
    packages=json.loads((OUT/'MaskAuthor03/MaskAuthoring.json').read_text())['saved']
    return ['Content/'+p.removeprefix('/Game/')+'.uasset' for p in packages]+['Content/Maps/DevMap.umap','Content/Maps/L_HeinMach_Environment.umap']
def prepare():
    assert json.loads((OUT/'PreparedSaved02/SavedAudit.json').read_text())['success']
    for run in ['DevAfter02','HeinAfter04']:
        assert json.loads((OUT/run/'Capture.json').read_text())['success']
        assert json.loads((OUT/run/'Exit.json').read_text())['exit']==0
    expected=json.loads((OUT/'Baseline.json').read_text())['files']
    expected.update(json.loads((OUT/'MaskBaseline.json').read_text())['files'])
    rows=[]
    for rel in files():
        src=WORK/rel;target=MAIN/rel
        assert src.resolve().is_relative_to(WORK.resolve()),('Writable ownership',rel)
        assert target.resolve().is_relative_to((MAIN/'Content').resolve())
        before=expected.get(rel)
        current=sha(target) if target.exists() else None
        assert current==before,('Main changed since baseline',rel,current,before)
        rows.append({'file':rel,'before':before,'prepared':sha(src),'bytes':src.stat().st_size})
    write('PreparedDelivery.json',{'status':'VerifiedPrepared','utc':datetime.now(timezone.utc).isoformat(),'files':rows,
        'runtime_source_changes':0,'config_changes':0,'native_delivery':0,'backup':'Before','main_editor_control':0})
    print('VERIFIED_PREPARED',len(rows),flush=True)
def install():
    plan=json.loads((OUT/'PreparedDelivery.json').read_text())
    # Validate every selected file and replacement access before any write.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.restype=ctypes.c_void_p
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    for row in plan['files']:
        target=MAIN/row['file'];current=sha(target) if target.exists() else None
        assert current in [row['before'],row['prepared']],('Concurrent Main change',row['file'])
        assert sha(WORK/row['file'])==row['prepared']
        if target.exists():
            handle=kernel.CreateFileW(str(target),0x10000,0x7,None,3,0x80,None)
            if handle==ctypes.c_void_p(-1).value:
                write('DeliveryBlocked.json',{'file':row['file'],'win32_error':ctypes.get_last_error(),'prepared_verified':True,'content_writes':0})
                raise OSError(ctypes.get_last_error(),'Selected package is locked',str(target))
            kernel.CloseHandle(handle)
    journal={'status':'Installing','files':[],'utc':datetime.now(timezone.utc).isoformat()};write('Delivery.json',journal)
    for row in plan['files']:
        target=MAIN/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and sha(target)==row['prepared']:continue
        temporary=target.with_name(target.name+'.scene_look_20261012.tmp')
        assert temporary.resolve().is_relative_to((MAIN/'Content').resolve())
        shutil.copyfile(WORK/row['file'],temporary)
        assert sha(temporary)==row['prepared'];os.replace(temporary,target)
        assert sha(target)==row['prepared']
        journal['files'].append(row['file']);write('Delivery.json',journal)
    journal['status']='MainDeliveredPendingFreshVerification';write('Delivery.json',journal)
    print('MAIN_SELECTED_DELIVERED',len(journal['files']),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
