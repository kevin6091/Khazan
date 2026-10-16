"""Stock verification build intake. Preserve only this task's three source edits."""
from pathlib import Path
import hashlib, json, shutil
MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
OUT = MAIN / 'Metadata/EnemyAnimationOrganization_20261007'
OWN = {'Source/Khazan/Character/KZMonster.h', 'Source/Khazan/AI/KZMonsterStateTreeNodes.cpp',
       'Source/Khazan/Tests/KZMonsterAIPIETest.cpp'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
baseline = {row['path']: row['sha256'] for row in json.loads((OUT / 'BeforeManifest.json').read_text())['files']}
for relative in OWN:
    assert sha(MAIN / relative) == baseline[relative], 'Concurrent edit: ' + relative
rows = []
for folder in ['Source', 'Config']:
    for source in (MAIN / folder).rglob('*'):
        if not source.is_file(): continue
        relative = source.relative_to(MAIN).as_posix()
        rows.append(dict(path=relative, sha256=sha(source)))
        if relative not in OWN:
            destination = WORK / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
shutil.copy2(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
(WORK / 'Khazan.uproject').touch()  # Invalidate the author's cached source list after removal.
temporary = WORK / 'Source/Khazan/Tests/EnemyAnimationAttackAuthorEditor.cpp'
assert temporary.resolve().is_relative_to((WORK / 'Source').resolve())
if temporary.exists(): temporary.unlink()
extra = [p.relative_to(WORK).as_posix() for p in (WORK / 'Source').rglob('*')
         if p.is_file() and not (MAIN / p.relative_to(WORK)).exists()]
assert not extra, extra
(OUT / 'StockSourceIntake.json').write_text(json.dumps(dict(files=rows, owned=sorted(OWN), temporary_runtime_files=extra), indent=2), encoding='utf-8')
print(json.dumps(dict(intake=len(rows), runtime_files_added=0, edited_source_files=len(OWN))))
