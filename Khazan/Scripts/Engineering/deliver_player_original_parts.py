"""Deliver only the verified Original parts packages, with preflight hash protection."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007' / 'Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007'
BASE = 'Content/_Art/Player/Character/'
journal_path = REPORT / 'DeliveryManifest.json'
journal = json.loads(journal_path.read_text(encoding='utf-8')) if journal_path.exists() else {}
recorded = {row['path']: row for row in journal.get('packages', [])}
verification = json.loads((REPORT / 'Verification.json').read_text(encoding='utf-8-sig'))
for key in ('native_physics', 'original_geometry', 'guard', 'heal', 'stock_reload', 'visual_review'):
    if verification.get(key) != 'Success':
        raise RuntimeError('Missing successful verification: ' + key)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

before = {row['path']: row['beforeSha256'] for row in json.loads((REPORT / 'BeforeManifest.json').read_text(encoding='utf-8-sig'))}
paths = []
for part in ('Torso', 'Leg', 'Hair'):
    paths += [BASE + 'Meshs/' + part + '/Player_Original_' + part + '_RigidBody_PhysicsAsset.uasset']
for part in ('Torso', 'Shoes', 'Leg', 'Hair', 'Arm'):
    paths += [BASE + 'Bluprints/Parts/ABP_Player_Original_' + part + '.uasset',
              BASE + 'Meshs/' + part + '/Player_Original_' + part + '_PhysicsAsset.uasset']
# Put dependencies on disk first, then the player Blueprint that refers to them.
paths += [BASE + 'Bluprints/BP_Player.uasset']

rows = []
for relative in paths:
    source, target = WORK / relative, MAIN / relative
    if not source.is_file():
        raise RuntimeError('Missing prepared package: ' + relative)
    prior = before.get(relative)
    prepared = sha(source)
    previous = recorded.get(relative, {})
    already_delivered = target.exists() and previous.get('deliveredSha256') == prepared and sha(target) == prepared
    if prior:
        if not already_delivered and sha(target) != prior:
            raise RuntimeError('Concurrent main change; reconcile before delivery: ' + relative)
    elif target.exists() and not already_delivered:
        raise RuntimeError('New target already exists; reconcile: ' + relative)
    row = {'path': relative, 'beforeSha256': prior, 'preparedSha256': prepared}
    if already_delivered:
        row['deliveredSha256'] = prepared
    rows.append(row)

# Main ABP and body PhysicsAsset are explicitly retained, not delivered.
for relative in (BASE + 'Bluprints/ABP_Player.uasset', BASE + 'Meshs/Player_PhysicsAsset.uasset'):
    if sha(WORK / relative) != before[relative]:
        raise RuntimeError('Unplanned change in protected work package: ' + relative)

for row in rows:
    if row.get('deliveredSha256'):
        continue
    relative = row['path']
    source, target = WORK / relative, MAIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # Check again immediately before each write, then atomically replace one file.
    if row['beforeSha256'] and sha(target) != row['beforeSha256']:
        raise RuntimeError('Concurrent main change during delivery: ' + relative)
    pending = target.with_suffix('.uasset.playerparts_pending')
    if pending.exists() and sha(pending) != row['preparedSha256']:
        raise RuntimeError('Unexpected staging file; inspect before retry: ' + str(pending))
    if not pending.exists():
        shutil.copy2(source, pending)
    try:
        os.replace(pending, target)
    except PermissionError as error:
        row['blocked'] = str(error)
    else:
        row['deliveredSha256'] = sha(target)
        if row['deliveredSha256'] != row['preparedSha256']:
            raise RuntimeError('Delivered digest mismatch: ' + relative)
    journal_path.write_text(json.dumps({
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'main': str(MAIN), 'work': str(WORK), 'packages': rows,
        'source_or_config_or_map_delivered': False,
        'current_main_editor_controlled': False, 'complete': all(r.get('deliveredSha256') for r in rows),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
complete = sum(bool(row.get('deliveredSha256')) for row in rows)
print('Delivered and verified', complete, 'of', len(rows), 'Original-player packages.')
if complete != len(rows):
    print('Remaining existing packages are locked; retry after the owning main editor exits. No process is stopped by this script.')
    raise SystemExit(2)
