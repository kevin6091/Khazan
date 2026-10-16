import hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
OUT = MAIN / 'Metadata/MonsterStamina_20261008'
assert json.loads((OUT / 'IntegratedRegression.json').read_text(encoding='utf-8'))['success']
assert json.loads((OUT / 'NativePIE.json').read_text(encoding='utf-8'))['success']
rows = []
for name in ['MonsterStaminaAuthorEditor.cpp', 'MonsterStaminaBodiesAuthorEditor.cpp', 'MonsterStaminaPIEEditor.cpp']:
    source = WORK / 'Source/Khazan/Tests' / name
    destination = MAIN / 'Scripts/Engineering' / name
    assert source.resolve().is_relative_to((WORK / 'Source/Khazan/Tests').resolve())
    if source.is_file():
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            backup = OUT / 'EditorHelpersBeforeStockCleanup' / name
            assert not backup.exists()
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
        shutil.copy2(source, destination)
        rows.append(dict(relative=str(source.relative_to(WORK)), preserved=str(destination), sha256=digest))
        source.unlink()
stock = MAIN / 'Source/Khazan/Khazan.Build.cs'
baseline = json.loads((OUT / 'MainSourceBaselineAfterCollision.json').read_text(encoding='utf-8'))
assert hashlib.sha256(stock.read_bytes()).hexdigest() == baseline['Source/Khazan/Khazan.Build.cs']
shutil.copy2(stock, WORK / 'Source/Khazan/Khazan.Build.cs')
(OUT / 'EditorHelperCleanup.json').write_text(json.dumps(dict(rows=rows, stock_build_cs_sha256=baseline['Source/Khazan/Khazan.Build.cs']), indent=2), encoding='utf-8')
print('Preserved editor fixtures; restored stock Build.cs')
