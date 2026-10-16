"""Certify collected native/stock evidence for the single Torso delivery."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

report = Path(__file__).resolve().parent
main = report.parents[2]
work = Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan')
def read(name):
    return json.loads((report/name).read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

native, reload = read('NativeComparison.json'), read('SavedReloadComparison.json')
for result in (native['baseline'], native['candidate'], reload['candidate']):
    assert result['selectedResult'] == 'Success' and result['eventsComplete']
    assert not result['warnings']
    assert result['hairMotion']['independentlyRespondingJoints'] == 65
    assert result['hairMotion']['bendPeakDegrees'] < 35
    for part, count in (('Torso', 8), ('Leg', 30)):
        assert result['clothMotion'][part]['independentlyRespondingJoints'] == count
        assert result['clothMotion'][part]['bendPeakDegrees'] < 45
    assert {k:v['observedJoints'] for k,v in result['shoulder'].items()} == {
        'Whole8':8, 'ShortPanel02_02':1, 'LongCloth7':7, 'LongProximal01_02':1}
for compared in (native, reload):
    assert compared['comparison']['exactLoggedHairMetricsEqual']
    assert compared['comparison']['exactLoggedLegMetricsEqual']
    surface = compared['comparison']['surface']['Torso']['candidate']
    assert surface['threeStagesComplete'] and surface['dominantThreeStagesComplete']
    assert surface['sampledInsideZero'] and surface['dominantInsideZero']
    for label in ('baseline','candidate'):
        waist = compared['waist'][label]
        assert waist['available'] and not waist['issues']
        assert waist['nativeScope']['selectedBlockMatchesCsv']
        assert waist['nativeScope']['savedWithNormalIronContact']
        assert waist['nativeScope']['expectedLateDurations']
    assert compared['waist']['baseline']['bones'] == compared['waist']['candidate']['bones']
assert native['candidate']['shoulder'] == reload['candidate']['shoulder']
assert native['candidate']['clothMotion'] == reload['candidate']['clothMotion']
author, saved = read('CandidateProfileAudit.json'), read('SavedReloadProfileAudit.json')
assert author['success'] and author['only_approved_changes_verified'] and author['asset_saved']
assert saved['success'] and saved['only_approved_changes_verified'] and not saved['asset_saved']
assert saved['before_state'] == 'Adjusted' and len(author['joints']) == len(saved['joints']) == 8
for a,b in zip(author['joints'], saved['joints']):
    assert a['bone'] == b['bone'] and a['parent'] == b['parent']
    assert a['full_constraint_matches_expected'] and b['full_constraint_matches_expected']
    for field in ('after_stiffness','after_damping','swing1_degrees','swing2_degrees',
                  'after_profile','saved_default_profile'):
        assert a[field] == b[field]
stock, stock_pose, binding = read('StockObservation.json'), read('StockReadback.json'), read('StockBinding.json')
assert stock['success'] and not stock['cleanupErrors']
assert stock['selectedMainSHA'] == binding['selectedMainSHA']
assert stock_pose['success'] and stock_pose['hair_pa_unchanged']
assert stock_pose['finite_secondary_bones'] == {'Torso':12,'Leg':59,'Hair':72}
assert stock_pose['tested_saved_package_count'] == 1
manifest = read('CandidateManifest.json')
assert len(manifest['packages']) == 1
for entry in manifest['packages']:
    assert sha(work/entry['path']) == entry['preparedSha256']
    assert sha(main/entry['path']) == entry['beforeSha256']
for protected in read('ProtectedBefore.json'):
    if protected['path'].endswith(('Player_Original_Hair_RigidBody_PhysicsAsset.uasset',
                                   'Player_Original_Leg_RigidBody_PhysicsAsset.uasset')):
        assert sha(main/protected['path']) == sha(work/protected['path']) == protected['sha256']
output = dict(utc=datetime.now(timezone.utc).isoformat(), native_pie_passed=True,
    native_saved_reload_passed=True, stock_saved_reload_passed=True,
    hair_motion=native['candidate']['hairMotion'],
    motion={'Torso':{'before':native['baseline']['clothMotion']['Torso'],
                     'after':native['candidate']['clothMotion']['Torso']}},
    shoulder=native['comparison']['shoulder'], only_approved_asset_fields_changed=True,
    waist_64_late_windows_exactly_unchanged=True, native_saved_metrics_exactly_reproduced=True,
    body_surface_scope='Three LOD0/anatomy-proxy snapshots; not continuous skin collision.',
    numeric_source='Assistant temporary tuning; original-game physics values unverified.',
    stock_scope='Current mapped Main base DLL, not future declared Snow module/live patches.',
    evidence={name:sha(report/name) for name in ('NativeComparison.json','SavedReloadComparison.json',
        'CandidateProfileAudit.json','SavedReloadProfileAudit.json','StockObservation.json','StockReadback.json')})
(report/'Verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print('Native, fresh saved-reload and mapped-Main stock evidence passed; Main unchanged.')
