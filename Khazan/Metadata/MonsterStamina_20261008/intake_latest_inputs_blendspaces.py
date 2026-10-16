import datetime, hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
OUT = MAIN / 'Metadata/MonsterStamina_20261008'
target = OUT / 'LatestInputBlendSpaceIntake.json'
if target.exists(): raise RuntimeError('Do not overwrite the prior intake receipt')
paths = ['Content/Data/DA_InputData.uasset', 'Content/Input/IA_RB.uasset', 'Content/Input/IMC_Default.uasset']
paths += ['Content/Monsters/' + f + '/Animations/BS_Combat_' + f + '.uasset'
          for f in ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
rows = []
for relative in paths:
    source, destination = MAIN / relative, WORK / relative
    if not source.is_file(): raise RuntimeError('Missing latest Main asset: ' + relative)
    before, requested = sha(destination), sha(source)
    if before != requested:
        if destination.is_file():
            backup = OUT / 'WorkBeforeLateAssets' / relative
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
    if sha(destination) != requested or sha(source) != requested: raise RuntimeError('Intake changed during copy')
    rows.append(dict(relative=relative, main_before=requested, work_before=before, work_after=requested, copied=before!=requested))
target.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    main_write=False, scope='Latest input3 and latest combat BS4; BS tuning is a subsequent single-field author operation.', rows=rows), indent=2), encoding='utf-8')
print(json.dumps(dict(receipt=str(target), copied=sum(r['copied'] for r in rows))))
