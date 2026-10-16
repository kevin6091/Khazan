"""Deliver only Parry's six native edits, one DEV test and thirteen packages."""
from pathlib import Path
from datetime import datetime, timezone
import ctypes, hashlib, json, os, shutil, sys
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan'
META=MAIN/'Metadata/Parry_20261012'
SOURCE=[
 'Source/Khazan/Ability/PlayerAbility/KZGuardAbility.h',
 'Source/Khazan/Ability/PlayerAbility/KZGuardAbility.cpp',
 'Source/Khazan/Ability/KZAbilitySystemComponent.h',
 'Source/Khazan/Ability/KZAbilitySystemComponent.cpp',
 'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
 'Source/Khazan/Ability/MonsterAbility/KZMonsterSkillObject.cpp',
 'Source/Khazan/Tests/KZParryPIETest.cpp']
BASE=json.loads((META/'Baseline.json').read_text(encoding='utf-8'))['files']
AUTHOR=json.loads((META/'Author01/Authoring.json').read_text(encoding='utf-8'))
ASSETS=['Content/'+p.removeprefix('/Game/')+'.uasset' for p in AUTHOR['saved']]
assert len(ASSETS)==13
def sha(p):
    if not p.is_file(): return None
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def lockcheck(p):
    # Opening for write/delete with full sharing does not change a byte. A
    # foreign read handle denying either access must prevent replacement.
    if not p.exists():return None
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
    k.CreateFileW.restype=ctypes.c_void_p
    k.CloseHandle.argtypes=[ctypes.c_void_p]
    h=k.CreateFileW(str(p),0x40000000|0x10000,7,None,3,0x80,None)
    if h==ctypes.c_void_p(-1).value:return ctypes.get_last_error()
    k.CloseHandle(h);return None
def rows():
    result=[]
    for rel in SOURCE+ASSETS:
        old=sha(MAIN/rel);new=sha(WORK/rel);assert new,rel
        result.append({'path':rel,'baseline':BASE.get(rel),'main':old,'candidate':new,
                       'conflict':old not in (BASE.get(rel),new),
                       'lock_error':lockcheck(MAIN/rel) if old!=new else None})
    return result
def main(mode):
    report={'utc':datetime.now(timezone.utc).isoformat(),'mode':mode,'main':str(MAIN),'work':str(WORK),'rows':rows()}
    report['conflicts']=[r['path'] for r in report['rows'] if r['conflict']]
    report['locks']=[{'path':r['path'],'winerror':r['lock_error']} for r in report['rows'] if r['lock_error']]
    name='DeliveryPreflight.json' if mode=='preflight' else 'Delivery.json'
    if mode=='deliver':
        assert not report['conflicts'],report['conflicts']
        # No partial Main package delivery while a required existing asset is locked.
        if report['locks']:report['status']='prepared_main_locked'
        else:
            backup=META/'DeliveryBefore';backup.mkdir(exist_ok=False)
            for r in report['rows']:
                p=MAIN/r['path'];assert sha(p)==r['main'],'Concurrent Main edit: '+str(p)
                if r['main']==r['candidate']:continue
                if p.exists():
                    b=backup/r['path'];b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,b)
                p.parent.mkdir(parents=True,exist_ok=True)
                staged=p.with_name(p.name+'.parry20261012.tmp')
                assert not staged.exists()
                # Delivery is a new write. Retaining a pre-existing source's
                # old mtime can make UHT skip a changed reflected header.
                shutil.copyfile(WORK/r['path'],staged)
                assert sha(p)==r['main'],'Concurrent Main edit: '+str(p)
                os.replace(staged,p);assert sha(p)==r['candidate']
            report['status']='delivered'
    else:report['status']='ready' if not report['conflicts'] and not report['locks'] else 'prepared_main_locked' if report['locks'] and not report['conflicts'] else 'conflicts'
    (META/name).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
