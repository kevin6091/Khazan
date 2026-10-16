"""Copy the visually verified five montages from the isolated work copy to Main."""
from pathlib import Path
import hashlib
import json
import os
import shutil

main = Path(__file__).resolve().parents[2]
work = main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
out = main/'Metadata/PlayerSlashOuter_20261014/MainApply'
out.mkdir(parents=True,exist_ok=True)
prep = json.loads((main/'Metadata/PlayerSlashOuter_20261014/WorkPreparation.json').read_text(encoding='utf-8'))
retune = json.loads((main/'Metadata/PlayerSlashOuter_20261014/RetuneCandidate02/Retune.json').read_text(encoding='utf-8'))
expected_after = {row['file']:row['sha256'] for row in retune['rows']}
assert set(prep['targets']) == set(expected_after)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

rows = []
for rel,before in prep['targets'].items():
    target = main/rel
    source = work/rel
    assert sha(target) == before, f'Main changed during isolated validation: {rel}'
    assert sha(source) == expected_after[rel], f'Work candidate changed: {rel}'
    rows.append({'file':rel,'before_sha256':before,'after_sha256':expected_after[rel]})

# Save every original before changing any Main asset, then use a replace on the
# same volume. On a Windows editor lock, restore already replaced assets.
for row in rows:
    backup = out/'Before'/row['file']
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(main/row['file'],backup)
    assert sha(backup) == row['before_sha256']

done = []
try:
    for row in rows:
        target = main/row['file']
        stage = target.with_suffix(target.suffix+'.kzs-stage')
        shutil.copy2(work/row['file'],stage)
        assert sha(stage) == row['after_sha256']
        os.replace(stage,target)
        assert sha(target) == row['after_sha256']
        done.append(row)
except BaseException:
    for row in reversed(done):
        target = main/row['file']
        stage = target.with_suffix(target.suffix+'.kzs-restore')
        shutil.copy2(out/'Before'/row['file'],stage)
        os.replace(stage,target)
        assert sha(target) == row['before_sha256']
    raise
finally:
    for row in rows:
        for suffix in ('.kzs-stage','.kzs-restore'):
            stage = (main/row['file']).with_suffix('.uasset'+suffix)
            if stage.exists():stage.unlink()

receipt = {'status':'applied','source':'isolated visually validated work copy',
           'targets':{row['file']:row for row in rows}}
(out/'Receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('SLASH_OUTER_MAIN_APPLIED',len(rows))
