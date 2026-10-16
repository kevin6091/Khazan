"""Invalidate private UBT objects after earlier copy2 intake; bytes stay intact."""
from pathlib import Path
import datetime
import hashlib
import json
import os

MAIN = Path(__file__).resolve().parents[2]
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008/Build'
assert (WORK / 'Source').resolve() == WORK / 'Source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
main_before = {p.relative_to(MAIN).as_posix(): sha(p) for p in (MAIN / 'Source').rglob('*') if p.is_file()}
rows = []
for file in (WORK / 'Source').rglob('*'):
    if not file.is_file():
        continue
    digest = sha(file)
    before = file.stat().st_mtime_ns
    os.utime(file, None)
    assert sha(file) == digest
    rows.append(dict(file=file.relative_to(WORK).as_posix(), sha256=digest,
                     mtime_before_ns=before, mtime_after_ns=file.stat().st_mtime_ns))
assert main_before == {p.relative_to(MAIN).as_posix(): sha(p) for p in (MAIN / 'Source').rglob('*') if p.is_file()}
report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='passed_private_timestamp_only',
              source_content_changes=0, Main_source_unchanged=True, files=rows,
              reason='Earlier copy2 intake retained old Main timestamps; KZGameplayTags.cpp changed bytes were older than cached private .obj and four new tag definitions were not linked.')
(OUT / 'PrivateSourceTimestampRefresh.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(report['status'], len(rows), 'private sources; Main and all source bytes unchanged')
