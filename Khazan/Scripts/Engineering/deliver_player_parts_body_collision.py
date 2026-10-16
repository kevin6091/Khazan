"""Deliver only the seven tested Player body collision packages, with SHA guards."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007' / 'Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/BodyCollisionTuning'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def write(name, data):
    path = REPORT / name
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

parser = argparse.ArgumentParser()
parser.add_argument('--prepare', action='store_true', help='Record candidates without modifying main')
args = parser.parse_args()
before = json.loads((REPORT / 'BeforeManifest.json').read_text(encoding='utf-8-sig'))
assert len(before) == 7
candidate_path = REPORT / 'CandidateManifest.json'
if args.prepare:
    entries = []
    for entry in before:
        assert digest(MAIN / entry['path']) == entry['beforeSha256'], 'Concurrent main change: ' + entry['path']
        prepared = digest(WORK / entry['path'])
        assert prepared != entry['beforeSha256'], 'Package has not been authored: ' + entry['path']
        entries.append(dict(entry, preparedSha256=prepared))
    # Dependencies first, actor Blueprint last.
    entries.sort(key=lambda x: x['path'].endswith('/BP_Player.uasset'))
    write('CandidateManifest.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'packages': entries})
    print('Prepared seven SHA-guarded candidates; main unchanged.')
else:
    verified = json.loads((REPORT / 'Verification.json').read_text(encoding='utf-8-sig'))
    assert verified['isolated_native_pie_passed'] and verified['stock_saved_reload_passed']
    entries = json.loads(candidate_path.read_text(encoding='utf-8-sig'))['packages']
    for entry in entries:
        assert digest(WORK / entry['path']) == entry['preparedSha256'], 'Candidate changed: ' + entry['path']
        assert digest(MAIN / entry['path']) in (entry['beforeSha256'], entry['preparedSha256']), 'Concurrent main change: ' + entry['path']
    journal = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'complete': False, 'packages': []}
    for entry in entries:
        source, target = WORK / entry['path'], MAIN / entry['path']
        if digest(target) != entry['preparedSha256']:
            pending = target.with_suffix('.uasset.bodycollision_pending')
            if pending.exists():
                assert digest(pending) == entry['preparedSha256'], 'Unexpected pending asset'
            else:
                shutil.copy2(source, pending)
            assert digest(pending) == entry['preparedSha256']
            assert digest(target) == entry['beforeSha256'], 'Main changed during delivery'
            os.replace(pending, target)
        assert digest(target) == entry['preparedSha256']
        journal['packages'].append(dict(entry, delivered=True))
        write('DeliveryManifest.json', journal)
    journal['complete'] = True
    write('DeliveryManifest.json', journal)
    print('Delivered seven tested packages with SHA verification; no Source/Config/map/DLL writes.')
