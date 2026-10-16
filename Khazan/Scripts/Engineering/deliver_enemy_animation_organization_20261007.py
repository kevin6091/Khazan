"""Deliver only the verified Monster work files while Main Editor is closed.

All source/destination/deletion hashes and path boundaries are checked before
the first write. The immutable Before backup and prepared Work project are kept.
"""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
OUT = MAIN / 'Metadata/EnemyAnimationOrganization_20261007'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target(root, relative):
    path = (root / relative).resolve()
    assert path.is_relative_to(root) and path != root, relative
    assert relative.startswith(('Content/', 'Source/Khazan/')), relative
    return path


manifest = json.loads((OUT / 'PreparedDeliveryManifest.json').read_text(encoding='utf-8'))
assert manifest['runtime_files_added'] == 0
intake = json.loads((OUT / 'StockSourceIntake.json').read_text(encoding='utf-8'))
own = set(intake['owned'])
assert own == {row['path'] for row in manifest['files'] if row['path'].startswith('Source/')}
for row in intake['files']:
    assert sha(MAIN / row['path']) == row['sha256'], 'Concurrent source/config change: ' + row['path']
for row in manifest['files']:
    source = target(WORK, row['path'])
    destination = target(MAIN, row['path'])
    assert sha(source) == row['prepared_sha256'], 'Prepared file changed: ' + row['path']
    if row['before_sha256']:
        assert sha(destination) == row['before_sha256'], 'Main edit: ' + row['path']
    else:
        assert not destination.exists(), 'Main destination already exists: ' + row['path']
for row in manifest['deleted']:
    destination = target(MAIN, row['path'])
    assert destination.is_relative_to(MAIN / 'Content'), row['path']
    assert sha(destination) == row['before_sha256'], 'Main old package edit: ' + row['path']
    assert not target(WORK, row['path']).exists(), row['path']
inventory = json.loads((OUT / 'Inventory.json').read_text(encoding='utf-8'))
for relative, expected in inventory['archer_protected'].items():
    assert sha(target(MAIN, relative)) == expected, 'Archer changed: ' + relative

if '--check-only' in sys.argv:
    print(json.dumps(dict(status='PreconditionsPassed', prepared_files=len(manifest['files']),
                          old_packages=len(manifest['deleted']), protected_archer=len(inventory['archer_protected']))))
    sys.exit(0)

# Stage exact files beside their destination, then replace only those named files.
staged = []
try:
    for row in manifest['files']:
        destination = target(MAIN, row['path'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.monster-delivery-20261007.tmp')
        assert not temporary.exists(), temporary
        shutil.copy2(target(WORK, row['path']), temporary)
        assert sha(temporary) == row['prepared_sha256'], row['path']
        staged.append((temporary, destination))
    for temporary, destination in staged:
        temporary.replace(destination)
    for row in manifest['deleted']:
        target(MAIN, row['path']).unlink()  # Exact files only; no recursive deletion.
finally:
    for temporary, _ in staged:
        if temporary.exists():
            assert temporary.resolve().is_relative_to(MAIN)
            temporary.unlink()

for row in manifest['files']:
    assert sha(target(MAIN, row['path'])) == row['prepared_sha256'], row['path']
for row in manifest['deleted']:
    assert not target(MAIN, row['path']).exists(), row['path']
for row in intake['files']:
    if row['path'] not in own:
        assert sha(MAIN / row['path']) == row['sha256'], row['path']
for relative, expected in inventory['archer_protected'].items():
    assert sha(target(MAIN, relative)) == expected, relative

manifest.update(status='DeliveredHashVerified', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                protected_archer=len(inventory['archer_protected']),
                unrelated_source_config_verified=len(intake['files']) - len(own))
(OUT / 'DeliveredManifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({key: manifest[key] for key in ['status', 'utc', 'protected_archer', 'unrelated_source_config_verified']},
                 ensure_ascii=False))
