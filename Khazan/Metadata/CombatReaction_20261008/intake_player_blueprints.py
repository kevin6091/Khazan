from pathlib import Path
import hashlib, shutil, json, datetime
main=Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
out=main/'Metadata/CombatReaction_20261008'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
rows=[]
for p in sorted((main/'Content/_Art/Player/Character/Bluprints').rglob('*.uasset')):
    rel=p.relative_to(main).as_posix(); target=work/rel
    before=sha(target); expected=sha(p)
    if before != expected:
        backup=out/'PlayerBlueprintWorkBefore'/rel
        backup.parent.mkdir(parents=True,exist_ok=True)
        if target.is_file(): shutil.copy2(target,backup)
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
    assert sha(p)==expected and sha(target)==expected
    rows.append(dict(relative=rel,main_sha256=expected,work_before=before,copied=before!=expected))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,scope='Current Main Player character Blueprint dependencies only; no Main writes')
(out/'PlayerBlueprintIntake.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('Player Blueprint intake:',len(rows),'checked,',sum(r['copied'] for r in rows),'copied')
