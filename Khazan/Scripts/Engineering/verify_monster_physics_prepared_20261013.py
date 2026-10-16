"""Gate Main delivery on actual fresh saved/RHI/gameplay results and prepared hashes."""
from pathlib import Path
import hashlib,json,shutil,sys
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
qa=OUT/(sys.argv[1] if len(sys.argv)>1 else 'PrivateFinalQA01')
driver=json.loads((qa/'Driver.json').read_text(encoding='utf-8'))
assert driver['status']=='passed' and len(driver['tests'])==3 and all(t['passed'] for t in driver['tests'])
runtime=json.loads((qa/'Runtime.json').read_text(encoding='utf-8'))
assert len(runtime['families'])==6
for f in runtime['families']:
    assert f['finite'] and f['parts']
    assert all(p['simulated']>0 and p['responding']>0 and p['joint_peak_deg']<45. for p in f['parts'])
    assert (qa/f"Physics_{runtime['families'].index(f):02d}.png").exists()
shutil.copy2(WORK/'Saved/MonsterSecondaryPhysicsSaved.json',qa/'MonsterSecondaryPhysicsSaved.json')
manifest=json.loads((OUT/'DeliveryManifest.json').read_text(encoding='utf-8'))
for row in manifest['files']:
    assert sha(OUT/'Prepared'/row['path'])==row['prepared']
    assert sha(WORK/row['path'])==row['prepared'],('Prepared/work mismatch',row['path'])
intake=json.loads((OUT/'LatestSourceIntake.json').read_text(encoding='utf-8'))
for row in intake:
    if row['path'].startswith('Source/Khazan/Tests/'):continue
    assert sha(MAIN/row['path'])==row['main'],('Concurrent runtime change',row['path'])
report=dict(passed=True,private_native_rhi_driver=driver,families=runtime['families'],
    files=len(manifest['files']),source_unchanged_since_intake=True,save_in_validation=0,
    limitations='Current gameplay six families verified; other imported variants statically configured. No claim of original-game physics parity or zero triangle penetration.')
(OUT/'PreparedVerification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PREPARED VERIFICATION PASSED',len(manifest['files']))
