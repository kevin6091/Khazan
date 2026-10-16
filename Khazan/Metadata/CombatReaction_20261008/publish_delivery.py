from pathlib import Path
import json, hashlib, shutil, os, datetime
out=Path(__file__).resolve().parent
manifest=json.loads((out/'PreparedDelivery.json').read_text(encoding='utf8'))
main=Path(manifest['main']); work=Path(manifest['work'])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def atomic(source,dest,expected):
    assert sha(dest)==expected, 'CAS changed: '+str(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.CombatReaction.tmp'); assert not temp.exists()
    shutil.copy2(source,temp)
    after=sha(source); assert sha(temp)==after and sha(dest)==expected
    os.replace(temp,dest); assert sha(dest)==after
    return after
receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),complete=False,rows=[],user_editor_controlled=False)
target=out/'DeliveryReceipt.json'; assert not target.exists(), 'Preserve existing receipt'
def save(): target.write_text(json.dumps(receipt,indent=2),encoding='utf8')
try:
    assert sha(work/'Binaries/Win64/UnrealEditor-Khazan.dll')==manifest['dll_sha256'], 'Prepared DLL changed'
    assert sha(work/'Binaries/Win64/UnrealEditor-Khazan.pdb')==manifest['pdb_sha256'], 'Prepared PDB changed'
    for r in manifest['rows']:
        assert sha(main/r['relative'])==r['before'], r['relative']
        assert sha(work/r['relative'])==r['after'], r['relative']
    module=main/'Binaries/Win64/UnrealEditor.modules'
    assert sha(module)==manifest['main_modules_before']
    assert sha(main/'Binaries/Win64/UnrealEditor-Khazan.dll')==manifest['main_canonical_dll_before']
    for r in manifest['rows']:
        dest=main/r['relative']
        if dest.is_file():
            backup=out/'BeforeDelivery'/r['relative']; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dest,backup)
        after=atomic(work/r['relative'],dest,r['before'])
        receipt['rows'].append(dict(relative=r['relative'],before=r['before'],after=after)); save()
    dll=main/'Binaries/Win64'/manifest['alias']; assert not dll.exists()
    atomic(work/'Binaries/Win64/UnrealEditor-Khazan.dll',dll,None)
    atomic(work/'Binaries/Win64/UnrealEditor-Khazan.pdb',dll.with_suffix('.pdb'),None)
    assert sha(dll)==manifest['dll_sha256'] and sha(dll.with_suffix('.pdb'))==manifest['pdb_sha256']
    backup=out/'BeforeDelivery/Binaries/Win64/UnrealEditor.modules'; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(module,backup)
    value=json.loads(module.read_text(encoding='utf-8-sig')); value['Modules']['Khazan']=manifest['alias']
    candidate=out/'CandidateUnrealEditor.modules'; candidate.write_text(json.dumps(value,indent=2),encoding='utf8')
    atomic(candidate,module,manifest['main_modules_before'])
    receipt.update(complete=True,alias=manifest['alias'],dll_sha256=sha(dll),modules_sha256=sha(module),
        canonical_dll_preserved=sha(main/'Binaries/Win64/UnrealEditor-Khazan.dll')==manifest['main_canonical_dll_before'])
    save(); print(json.dumps(dict(complete=True,files=len(receipt['rows']),alias=manifest['alias'])))
except Exception as error:
    receipt['error']=str(error); save(); raise
