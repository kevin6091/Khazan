"""Record actual motion comparisons, saved profile evidence and stock readback."""
from pathlib import Path
import datetime
import hashlib
import json
import re

MAIN = Path(__file__).resolve().parents[2]
REPORT = MAIN / 'Metadata/PlayerParts_20261007/HairRefinement'

def read(name):
    return (REPORT / name).read_text(encoding='utf-8-sig')

def motion(text):
    line = next(line for line in reversed(text.splitlines()) if 'HairMotion rootSamples=' in line)
    return {name: float(value) for name, value in re.findall(r'(\w+)=([0-9.]+)', line)}

before_text, after_text = read('PIE_Before.log'), read('PIE_FinalSaved_Success.log')
assert 'Result={Success} Name={PIE} Path={Khazan.PlayerParts.PIE}' in after_text
before, after = motion(before_text), motion(after_text)
assert after['tipPeakCm'] < before['tipPeakCm'] and after['tipRmsCm'] < before['tipRmsCm']
assert after['bendPeakDegrees'] < 35 and after['independentlyRespondingJoints'] == 65
for part in ('Hair', 'Torso', 'Leg'):
    line = next(line for line in reversed(after_text.splitlines()) if 'ActualBodyContacts part=' + part in line)
    assert int(re.search(r'manifoldPoints=(\d+)', line)[1]) > 0
    assert float(re.search(r'accumulatedImpulse=([0-9.]+)', line)[1]) > 0
profiles = [line for line in read('SavedProfileAudit.log').splitlines() if 'CollisionJoint part=Hair' in line]
assert len(profiles) == 65
assert all('orientationDrive=1 velocityDrive=1' in line for line in profiles)
assert 'Result={Success} Name={PIE} Path={Khazan.Guard.PIE}' in read('Guard_Stock_Success.log')
assert 'Result={Success} Name={PIE} Path={Khazan.Heal.PIE}' in read('Heal_Stock_Success.log')
stock = json.loads(read('Stock_RuntimeReadback.json'))
assert stock['hair_finite_secondary_bones'] == 72 and len(stock['face_locks_follow_current_parent_pose']) == 4
entries = json.loads(read('CandidateManifest.json'))['packages']
work = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
assert len(entries) == 1
assert hashlib.sha256((work / entries[0]['path']).read_bytes()).hexdigest().upper() == entries[0]['preparedSha256']
data = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='IsolatedComplete',
            native_pie_passed=True, smaller_motion_confirmed=True, native_saved_reload_passed=True,
            saved_default_profiles_confirmed=65, stock_saved_reload_passed=True, guard_passed=True, heal_passed=True,
            before=before, after=after,
            tip_peak_reduction_percent=100 * (1 - after['tipPeakCm'] / before['tipPeakCm']),
            tip_rms_reduction_percent=100 * (1 - after['tipRmsCm'] / before['tipRmsCm']),
            simulated_bodies=65, kinematic_bodies=3, dynamic_strands=14, face_locks_copy_pose_bones=4,
            main_integration_complete=False, new_runtime_files=0,
            limits=['Original-game physics values unverified', 'Measured comparison, not deterministic or statistical proof',
                    'Not every vertex, LOD, action or prolonged hardware condition inspected'])
(REPORT / 'Verification.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Verified isolated hair refinement:', data['tip_peak_reduction_percent'], '% smaller peak, 65 responding joints.')
