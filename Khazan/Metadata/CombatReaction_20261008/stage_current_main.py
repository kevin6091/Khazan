import datetime,hashlib,json,pathlib,shutil
MAIN=pathlib.Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_MonsterWork_20261006'/'Khazan'
OUT=MAIN/'Metadata/CombatReaction_20261008'
assert WORK.is_dir() and not (OUT/'StageBaseline.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
paths=['Khazan.uproject']
paths += [p.relative_to(MAIN).as_posix() for folder in ('Source','Config') for p in (MAIN/folder).rglob('*') if p.is_file()]
for folder in ('Content/Monsters','Content/Input','Content/Data','Content/Bluprints/AbilitySystem'):
    paths += [p.relative_to(MAIN).as_posix() for p in (MAIN/folder).rglob('*.uasset')]
paths += [p.relative_to(MAIN).as_posix() for p in (MAIN/'Content/Bluprints/Characters').rglob('*.uasset')]
paths += [p.relative_to(MAIN).as_posix() for p in (MAIN/'Content/Bluprints/Monsters').rglob('*.uasset')]
# Copy only packages delivered by the completed VFX task, retaining its current dependency closure.
vfx=json.loads((MAIN/'Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json').read_text(encoding='utf-8'))
delivery=MAIN/'Saved/ImportReports/PlayerAttackVFX_20261008/MainDelivery/Delivered.json'
if delivery.is_file():
    value=json.loads(delivery.read_text(encoding='utf-8'))
    # Actual known assets are covered by the current DAS directories below; no inferred receipt schema.
paths += [p.relative_to(MAIN).as_posix() for p in (MAIN/'Content/_Art/Player/Animation/InGame/DAS').rglob('*.uasset')]
baseline={relative:sha(MAIN/relative) for relative in sorted(set(paths))}
rows=[]
for relative,expected in baseline.items():
    source,dest=MAIN/relative,WORK/relative
    before=sha(dest)
    if before!=expected:
        if dest.is_file():
            backup=OUT/'WorkBefore'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    assert sha(source)==expected and sha(dest)==expected
    rows.append(dict(relative=relative,main=expected,work_before=before,copied=before!=expected))
(OUT/'StageBaseline.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),main=str(MAIN),work=str(WORK),rows=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(checked=len(rows),copied=sum(r['copied'] for r in rows))))
