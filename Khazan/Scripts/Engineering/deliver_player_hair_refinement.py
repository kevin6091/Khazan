"""Deliver the single verified hair PA with before/prepared SHA guards."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/HairRefinement'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def write(name, data):
    temporary = (REPORT / name).with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(REPORT / name)

parser = argparse.ArgumentParser()
parser.add_argument('--prepare', action='store_true')
args = parser.parse_args()
before = json.loads((REPORT / 'BeforeManifest.json').read_text(encoding='utf-8-sig'))
assert len(before) == 1
entry = before[0]
source, target = WORK / entry['path'], MAIN / entry['path']
if args.prepare:
    if (REPORT / 'CandidateManifest.json').exists():
        history = REPORT / 'CandidateHistory'
        history.mkdir(exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        shutil.copy2(REPORT / 'CandidateManifest.json', history / (stamp + '.json'))
    assert digest(target) == entry['beforeSha256'], 'Concurrent main hair change'
    entry['preparedSha256'] = digest(source)
    assert entry['preparedSha256'] != entry['beforeSha256']
    write('CandidateManifest.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), packages=[entry]))
    print('Prepared one hair package; main unchanged.')
else:
    verification = json.loads((REPORT / 'Verification.json').read_text(encoding='utf-8-sig'))
    assert verification['native_pie_passed'] and verification['smaller_motion_confirmed'] and verification['stock_saved_reload_passed']
    entry = json.loads((REPORT / 'CandidateManifest.json').read_text(encoding='utf-8-sig'))['packages'][0]
    assert digest(source) == entry['preparedSha256'], 'Candidate changed after verification'
    assert digest(target) in (entry['beforeSha256'], entry['preparedSha256']), 'Concurrent main hair change'
    if digest(target) != entry['preparedSha256']:
        pending = target.with_suffix('.uasset.hairrefinement_pending')
        if pending.exists():
            assert digest(pending) == entry['preparedSha256'], 'Unexpected pending package'
        else:
            shutil.copy2(source, pending)
        assert digest(pending) == entry['preparedSha256']
        assert digest(target) == entry['beforeSha256'], 'Main changed during delivery'
        os.replace(pending, target)
    assert digest(target) == entry['preparedSha256']
    write('DeliveryManifest.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), complete=True, packages=[dict(entry, delivered=True)]))
    print('Delivered one verified hair package. Runtime source, other assets, map and binary untouched.')
