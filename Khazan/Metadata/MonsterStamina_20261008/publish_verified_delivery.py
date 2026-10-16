import datetime, hashlib, json, os, pathlib, shutil
OUT = pathlib.Path(__file__).resolve().parent
manifest = json.loads((OUT / 'PreparedDeliveryManifest.json').read_text(encoding='utf-8'))
MAIN, WORK = pathlib.Path(manifest['main']), pathlib.Path(manifest['work'])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def atomic(source, destination, expected):
    if sha(destination) != expected: raise RuntimeError('Destination CAS mismatch: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.MonsterStamina.tmp')
    if temp.exists(): raise RuntimeError('Unexpected existing staged file: ' + str(temp))
    shutil.copy2(source, temp)
    expected_after = sha(source)
    if sha(temp) != expected_after or sha(destination) != expected:
        raise RuntimeError('Staging/CAS changed: ' + str(destination))
    os.replace(temp, destination)
    if sha(destination) != expected_after: raise RuntimeError('Published hash differs')
    return expected_after
receipt = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), complete=False, rows=[],
    loaded_user_editor_reloaded=False, canonical_dll_preserved=False)
target = OUT / 'DeliveryReceipt.json'
if target.exists(): raise RuntimeError('Preserve existing delivery receipt; resume from exact rows')
def save(): target.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
try:
    # Validate the entire selected payload before changing any destination.
    for row in manifest['rows']:
        assert sha(MAIN / row['relative']) == row['before'], 'Main changed: ' + row['relative']
        assert sha(WORK / row['relative']) == row['after'], 'Candidate changed: ' + row['relative']
    module = MAIN / 'Binaries/Win64/UnrealEditor.modules'
    assert sha(module) == manifest['main_modules_before']
    assert sha(MAIN / 'Binaries/Win64/UnrealEditor-Khazan.dll') == manifest['main_canonical_dll_before']
    for row in manifest['rows']:
        destination = MAIN / row['relative']
        if destination.is_file():
            backup = OUT / 'BeforeDelivery' / row['relative']
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(destination, backup)
        after = atomic(WORK / row['relative'], destination, row['before'])
        receipt['rows'].append(dict(relative=row['relative'], before=row['before'], after=after)); save()
    # Keep every existing DLL untouched. Switch only the module manifest to a unique verified module.
    alias = manifest['alias']
    dll = MAIN / 'Binaries/Win64' / alias
    assert not dll.exists()
    atomic(WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll', dll, None)
    pdb = dll.with_suffix('.pdb'); assert not pdb.exists()
    atomic(WORK / 'Binaries/Win64/UnrealEditor-Khazan.pdb', pdb, None)
    saved_module = OUT / 'BeforeDelivery/Binaries/Win64/UnrealEditor.modules'
    saved_module.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(module, saved_module)
    value = json.loads(module.read_text(encoding='utf-8-sig'))
    value['Modules']['Khazan'] = alias
    candidate = OUT / 'CandidateUnrealEditor.modules'
    candidate.write_text(json.dumps(value, indent=2), encoding='utf-8')
    atomic(candidate, module, manifest['main_modules_before'])
    receipt.update(complete=True, alias=alias, dll_sha256=sha(dll), modules_sha256=sha(module),
        canonical_dll_preserved=sha(MAIN / 'Binaries/Win64/UnrealEditor-Khazan.dll') == manifest['main_canonical_dll_before'])
    save()
    print(json.dumps(dict(complete=True, files=len(receipt['rows']), alias=alias)))
except Exception as error:
    receipt['error'] = str(error); save(); raise
