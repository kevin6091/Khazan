"""CAS delivery of approved verified cloth PhysicsAssets; no other Main writes."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil
MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
REPORT = Path(globals().get('cloth_report_directory',
                          MAIN / 'Metadata/PlayerParts_20261007/ClothRefinement')).resolve()
assert REPORT.is_relative_to(MAIN / 'Metadata') and REPORT != MAIN / 'Metadata'
APPROVED_TARGETS = tuple('Content/_Art/Player/Character/Meshs/' + part +
                        '/Player_Original_' + part + '_RigidBody_PhysicsAsset.uasset'
                        for part in ('Torso', 'Leg'))
TARGETS = tuple(globals().get('cloth_targets', APPROVED_TARGETS))
assert TARGETS and len(TARGETS) == len(set(TARGETS)) and set(TARGETS).issubset(APPROVED_TARGETS)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def write(name, data):
    tmp = (REPORT / name).with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(REPORT / name)
parser = argparse.ArgumentParser()
parser.add_argument('--prepare', action='store_true')
args = parser.parse_args()
before = json.loads((REPORT / 'BeforeManifest.json').read_text(encoding='utf-8-sig'))
assert len(before) == len(TARGETS) and {entry['path'] for entry in before} == set(TARGETS)
if args.prepare:
    if (REPORT / 'CandidateManifest.json').exists():
        history = REPORT / 'CandidateHistory'; history.mkdir(exist_ok=True)
        shutil.copy2(REPORT / 'CandidateManifest.json', history / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'))
    for entry in before:
        assert digest(MAIN / entry['path']) == entry['beforeSha256'], 'Concurrent Main cloth change'
        entry['preparedSha256'] = digest(WORK / entry['path'])
        assert entry['preparedSha256'] != entry['beforeSha256']
    write('CandidateManifest.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), packages=before))
    print('Prepared cloth packages; Main unchanged:', len(before))
else:
    verification = json.loads((REPORT / 'Verification.json').read_text(encoding='utf-8-sig'))
    assert verification['native_pie_passed'] and verification['stock_saved_reload_passed']
    if 'cloth_required_validation_fields' in globals():
        fields = tuple(cloth_required_validation_fields)
        allowed = ('native_pie_passed', 'native_saved_reload_passed',
                   'stock_saved_reload_passed', 'guard_passed', 'heal_passed')
        assert set(allowed[:3]).issubset(fields) and set(fields).issubset(allowed)
        assert all(verification.get(field) is True for field in fields)
    packages = json.loads((REPORT / 'CandidateManifest.json').read_text(encoding='utf-8-sig'))['packages']
    assert len(packages) == len(TARGETS) and {entry['path'] for entry in packages} == set(TARGETS)
    before_sha = {entry['path']: entry['beforeSha256'] for entry in before}
    for entry in packages:
        assert entry['beforeSha256'] == before_sha[entry['path']]
        assert digest(WORK / entry['path']) == entry['preparedSha256']
        assert digest(MAIN / entry['path']) in (entry['beforeSha256'], entry['preparedSha256'])
    for entry in packages:
        target = MAIN / entry['path']
        if digest(target) != entry['preparedSha256']:
            pending = target.with_suffix('.uasset.clothrefinement_pending')
            if pending.exists(): assert digest(pending) == entry['preparedSha256']
            else: shutil.copy2(WORK / entry['path'], pending)
            assert digest(pending) == entry['preparedSha256']
            assert digest(target) == entry['beforeSha256']
            os.replace(pending, target)
        assert digest(target) == entry['preparedSha256']
    write('DeliveryManifest.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), complete=True, packages=[dict(e, delivered=True) for e in packages]))
    print('Delivered verified cloth PAs:', len(packages))
