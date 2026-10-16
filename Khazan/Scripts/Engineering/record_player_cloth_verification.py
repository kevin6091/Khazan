"""Record real cloth motion/contact measurements and stock saved readback."""
from pathlib import Path
import datetime, hashlib, json, re
MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/ClothRefinement'
def read(name): return (REPORT / name).read_text(encoding='utf-8-sig')
def metrics(text, prefix):
    line = next(l for l in reversed(text.splitlines()) if prefix in l)
    return {k: float(v) for k, v in re.findall(r'(\w+)=(-?[0-9.]+)', line)}
before, after = read('PIE_Before_Fixed30.log'), read('PIE_FinalSaved_Success.log')
assert 'Result={Success} Name={PIE} Path={Khazan.PlayerParts.PIE}' in after
normal_delta = read('PIE_FinalSaved_NormalDelta_Success.log')
assert 'Result={Success} Name={PIE} Path={Khazan.PlayerParts.PIE}' in normal_delta
data = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='IsolatedComplete',
            native_pie_passed=True, native_saved_reload_passed=True, stock_saved_reload_passed=True,
            main_integration_complete=False, new_runtime_files=0, motion={}, contacts={})
data['comparison_conditions'] = dict(editor_fixed_frame_seconds=1/30, same_native_move_turn_stop_sequence=True,
    before_packages='BeforeManifest.json', after_packages='CandidateManifest.json',
    simulated_joint_membership_changed='Torso6->8, Leg26->30; attachment protection changes membership. RMS is each saved direct simulated joint set, not a paired bone-by-bone estimate.')
data['saved_fresh_process_normal_delta'] = {part: metrics(normal_delta,'ClothMotion part='+part) for part in ('Torso','Leg')}
for values in data['saved_fresh_process_normal_delta'].values(): assert values['bendPeakDegrees'] < 45
data['saved_fresh_process_normal_delta']['Hair'] = metrics(normal_delta,'HairMotion rootSamples=')
assert data['saved_fresh_process_normal_delta']['Hair']['bendPeakDegrees'] < 35
for part in ('Torso', 'Leg'):
    assert ('ClothMotionScope part=' + part + ' angular=SavedDirectSimulatedJointFrames') in before
    assert ('ClothMotionScope part=' + part + ' angular=SavedDirectSimulatedJointFrames') in after
    old, new = metrics(before, 'ClothMotion part=' + part), metrics(after, 'ClothMotion part=' + part)
    assert new['independentlyRespondingJoints'] > 0
    assert new['bendRmsDegrees'] < old['bendRmsDegrees']
    assert new['bendPeakDegrees'] < 45
    data['motion'][part] = dict(before=old, after=new)
for part in ('Torso', 'Leg', 'Hair'):
    contacts = metrics(after, 'ActualBodyContacts part=' + part)
    if part != 'Torso': assert contacts['manifoldPoints'] > 0 and contacts['accumulatedImpulse'] > 0
    data['contacts'][part] = dict(actual_contacts=contacts, before_depth=metrics(before, 'BodyContactDepth part=' + part), after_depth=metrics(after, 'BodyContactDepth part=' + part))
data['hair_motion'] = metrics(after, 'HairMotion rootSamples=')
data['hair_before_motion'] = metrics(before, 'HairMotion rootSamples=')
assert data['hair_motion'] == data['hair_before_motion'], 'Hair motion changed under matched sequence'
assert data['hair_motion']['independentlyRespondingJoints'] == 65
assert data['hair_motion']['bendPeakDegrees'] < 35
for name in ('Guard', 'Heal'):
    assert f'Result={{Success}} Name={{PIE}} Path={{Khazan.{name}.PIE}}' in read(name + '_Stock_Success.log')
data.update(guard_passed=True, heal_passed=True)
stock = json.loads(read('Stock_RuntimeReadback.json'))
assert stock['success'] and stock['hair_pa_unchanged'] and stock['finite_secondary_bones'] == {'Torso': 12, 'Leg': 59, 'Hair': 72}
entries = json.loads(read('CandidateManifest.json'))['packages']
assert len(entries) == 2
for e in entries: assert hashlib.sha256((WORK / e['path']).read_bytes()).hexdigest().upper() == e['preparedSha256']
data['surface_body_proxy'] = {}
for part in ('Torso', 'Leg'):
    stages = {}
    for stage in (3,4,5):
        def surface(t, prefix):
            lines = [l for l in t.splitlines() if prefix in l and ('stage='+str(stage)+' ') in l]
            return {k: float(v) for k,v in re.findall(r'(\w+)=(-?[0-9.]+)',lines[-1])}
        stages[str(stage)] = dict(before=surface(before,'ClothSurfaceProbe part='+part),
            after=surface(after,'ClothSurfaceProbe part='+part),
            before_dominant=surface(before,'ClothSurfaceWeights part='+part),
            after_dominant=surface(after,'ClothSurfaceWeights part='+part))
    data['surface_body_proxy'][part] = stages
data['limits'] = ['Original-game physics values unverified', 'Surface observations cover three current-pose linear-skinned LOD0 snapshots against body PhysicsAsset proxy, not exact rendered body skin or all actions. Selected vertex membership changes with simulated attachment protection.', 'Leg still has body-proxy overlap; zero mesh penetration is not proven.', 'Hair-relative restore frequency/damping and most limits remain the feel basis. Leg depth0 swing32deg is an explicit body-clearance exception to the 10percent angular limit relation; different chain lengths and contact response prevent an identical displacement ratio.']
(REPORT / 'Verification.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Verified native cloth refinement and stock Original-part readback; Main delivery pending.')
