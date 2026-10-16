"""Offline waist metrics from preserved native logs and CSV; never edits assets."""
import csv, hashlib, json, math, re, sys
from pathlib import Path

root = Path(__file__).resolve().parent
labels = sys.argv[1:] or ['Baseline', 'NoIronContact']
report = {'scope': 'Published parent-relative poses and actual immediate-physics actors; cached active contact gap is not skin penetration.', 'initialPhaseCaution': 'Baseline/NoIronContact PhysicsOff label used initialization-only p.RigidBodyNode; it did not pause already initialized nodes. Exclude that phase from conclusions. IdleLate and AfterReleaseLate have actual valid simulated actors.', 'runs': {}}
for label in labels:
    log = root / f'{label}Native.log'
    path = root / f'PlayerWaistJitter_{label}.csv'
    text = log.read_text(encoding='utf-8-sig', errors='replace')
    results = re.findall(r'Test Completed\. Result=\{([^}]+)\} Name=\{PIE\} Path=\{Khazan\.PlayerParts\.PIE\}', text)
    data = {'nativeResult': results[-1] if results else 'Incomplete', 'csvSha256': hashlib.sha256(path.read_bytes()).hexdigest().upper(), 'bones': {}, 'assertionErrors': [s for s in text.splitlines() if 'LogAutomationController: Error:' in s]}
    grouped = {}
    for row in csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines()):
        if row['hasPrevious'] != '1' or float(row['deltaSeconds']) <= 0: continue
        grouped.setdefault(row['phase'] + '|' + row['bone'], []).append(row)
    for key, rows in grouped.items():
        def rms(field): return math.sqrt(sum(float(r[field]) ** 2 for r in rows) / len(rows))
        data['bones'][key] = dict(samples=len(rows), meshJointStepRmsDegrees=rms('meshJointStepDegrees'), meshJointSpeedRmsDegreesPerSecond=rms('meshJointSpeedDegreesPerSecond'), actorJointStepRmsDegrees=rms('actorJointStepDegrees'), actorAngularSpeedRmsDegreesPerSecond=rms('actorAngularSpeedDegreesPerSecond'), parentWorldStepRmsDegrees=rms('parentWorldStepDegrees'), positionStepRmsCm=rms('parentRelativePositionStepCm'), activeContactPointSamples=sum(float(r['activeContactPoints']) for r in rows), activeContactImpulseSum=sum(float(r['accumulatedImpulse']) for r in rows), peakCachedGapCm=min(float(r['cachedMinSeparationCm']) for r in rows), collisionFlags=sorted(set(r['actorHasCollision'] for r in rows)), enabledFlags=sorted(set(r['actorEnabled'] for r in rows)))
    report['runs'][label] = data
out = root / ('Comparison_' + '_'.join(labels) + '.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
for label, data in report['runs'].items():
    print(label, data['nativeResult'])
    eligible = [(key, row) for key, row in data['bones'].items() if not key.startswith('PhysicsOff|')]
    for key, row in sorted(eligible, key=lambda kv: kv[1]['meshJointStepRmsDegrees'], reverse=True)[:12]:
        print(key, json.dumps(row))
