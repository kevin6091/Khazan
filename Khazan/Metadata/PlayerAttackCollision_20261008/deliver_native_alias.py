"""Preserve the running Main DLL; publish matched Source module under a distinct filename."""
import json,hashlib,shutil,datetime,os
from pathlib import Path
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan').resolve()
OUT=MAIN/'Metadata/PlayerAttackCollision_20261008'
ALIAS='UnrealEditor-KhazanPlayerAttackCollision20261008'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def sources(root):return {p.relative_to(root).as_posix():sha(p) for p in (root/'Source').rglob('*') if p.is_file()}
receipt=json.loads((OUT/'SourceContentDelivered.json').read_text(encoding='utf-8'))
assert receipt['status']=='SourceContentDelivered'
assert sources(MAIN)==sources(WORK),'Full current Source differs; never copy a stale native module'
for row in receipt['files']:assert sha(MAIN/row['file'])==row['after']==sha(WORK/row['file'])
manifest=MAIN/'Binaries/Win64/UnrealEditor.modules'
old=manifest.read_bytes();old_hash=sha(manifest)
data=json.loads(old.decode('utf-8-sig'))
work_modules=json.loads((WORK/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
assert data['BuildId']==work_modules['BuildId']=='55116800'
assert data['Modules']['Khazan']=='UnrealEditor-Khazan.dll'
preserved={p.name:sha(p) for p in (MAIN/'Binaries/Win64').glob('UnrealEditor-Khazan.*') if p.is_file()}
assert preserved.get('UnrealEditor-Khazan.dll')
before=OUT/'BeforeNative';before.mkdir(exist_ok=True)
backup=before/'UnrealEditor.modules'
assert not backup.exists()
backup.write_bytes(old)
files=[]
for ext in ('.dll','.pdb'):
    src=WORK/('Binaries/Win64/UnrealEditor-Khazan'+ext)
    dest=MAIN/('Binaries/Win64/'+ALIAS+ext)
    assert src.is_file() and not dest.exists()
    shutil.copy2(src,dest)
    assert sha(src)==sha(dest)
    files.append({'file':dest.relative_to(MAIN).as_posix(),'source':str(src),'sha256':sha(dest)})
assert sha(manifest)==old_hash and sources(MAIN)==sources(WORK)
assert all(sha(MAIN/'Binaries/Win64'/name)==value for name,value in preserved.items())
data['Modules']['Khazan']=ALIAS+'.dll'
temp=manifest.with_name('UnrealEditor.modules.attack-20261008.tmp')
assert not temp.exists()
temp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
assert sha(manifest)==old_hash
os.replace(temp,manifest)
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'NativeAliasDelivered',
        'files':files,'BuildId':data['BuildId'],'manifest_before_sha256':old_hash,
        'manifest_after_sha256':sha(manifest),'stock_modules_preserved':preserved,
        'full_source_matches':True,'source_snapshot':sources(MAIN),
        'running_Main_native_reloaded':False,'running_Main_restart_required':True,
        'reason':'Fresh process uses matched private build; running Main stock DLL remains intact'}
(OUT/'NativeAliasDelivered.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('NATIVE_ALIAS_DELIVERED',ALIAS,'stock files unchanged; existing Main unchanged')
