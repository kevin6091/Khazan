"""Finalize the delivered canonical snow contact change after fresh native Main QA.

Run explicitly with ordinary Python after MainVerificationExit.json reports success.
This script reads verification evidence and writes task receipts only; it does not
launch/stop editors, save packages, or modify gameplay, assets, or user settings.
"""
from pathlib import Path
import csv
import datetime
import hashlib
import json
import math
import re
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008'
OLD = OUT.parent/'Contact55_20261007'
MAP = 'Content/Maps/L_HeinMach_Environment.umap'
MANIFEST = 'Binaries/Win64/UnrealEditor.modules'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return digest.hexdigest()

def utc(value):
    stamp = datetime.datetime.fromisoformat(value)
    assert stamp.tzinfo is not None, 'Evidence must use timezone-aware UTC'
    return stamp

def write(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)

def main():
    delivery = read(OUT/'Delivery.json')
    launch, native, exited = (read(OUT/name) for name in
        ('MainVerificationLaunch.json', 'MainVerification.json', 'MainVerificationExit.json'))
    receipt_sha = sha(OUT/'Delivery.json')
    assert delivery['success'] and delivery['canonical_map_pending'] is False
    assert delivery['map_asset'] == '/Game/Maps/L_HeinMach_Environment'
    assert native['success'] and native['saved_scene_passed'] and native['native_pie_passed']
    assert exited['success'] and exited['exit_code'] == 0
    assert native['pid'] == launch['pid'] == exited['pid'] != launch.get('protected_editor_pid')
    assert utc(delivery['utc']) < utc(launch['utc']) < utc(native['utc']) <= utc(exited['utc'])
    assert launch['delivery_sha256'] == native['delivery_sha256'] == receipt_sha
    assert native['map_asset'] == delivery['map_asset']
    module = Path(delivery['module']).resolve()
    assert module.parent == (ROOT/'Binaries/Win64').resolve()
    assert Path(native['module_path']).resolve() == Path(launch['module']).resolve() == module
    assert sha(module) == native['module_sha256'] == delivery['module_sha256']
    assert read(ROOT/MANIFEST)['Modules']['Khazan'] == module.name
    required = {MAP, MANIFEST, 'Binaries/Win64/'+module.name,
        'Source/Khazan/Environment/KZSnowDeformation.h',
        'Source/Khazan/Environment/KZSnowDeformation.cpp',
        'Source/Khazan/Tests/KZSnowDeformationPIETest.cpp'}
    assert required <= delivery['hashes'].keys()
    for group in ('hashes', 'protected'):
        for relative, expected in delivery[group].items():
            path = (ROOT/relative).resolve()
            assert path.is_relative_to(ROOT.resolve()) and sha(path) == expected, relative
    assert sha(ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll') == delivery['normal_module_preserved_sha256']
    assert sha(OUT/'SurfaceProfiles.json') == delivery['surface_profiles_sha256']
    for key, expected in delivery['settings'].items():
        actual = native['snow_contact_settings'][key]
        pairs = zip(actual, expected) if isinstance(expected, list) else [(actual, expected)]
        if isinstance(expected, list): assert len(actual) == len(expected), key
        assert all(abs(float(a)-float(b)) < 1e-6 for a, b in pairs), key
    archived = read(OUT/'PreviousPendingApplyStatus.json')
    assert archived.get('canonical_map_pending') is True, 'Prior pending receipt must be preserved'
    log = (OUT/'MainVerify.log').read_text(encoding='utf-8', errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in log
    assert 'Test Completed. Result={Fail}' not in log
    foot = re.findall(r'SnowFootGPU dentCm=([\d.]+)', log)
    weapon = re.findall(r'SnowGPU before=[\d.]+ after=[\d.]+ dentCm=([\d.]+)', log)
    assert foot and weapon, 'Native rendered depth evidence is required'
    perf = None
    cutoff = utc(launch['utc']).timestamp()
    for capture in sorted((ROOT/'Saved/Profiling/CSV').glob('*.csv'),
                          key=lambda p: p.stat().st_mtime, reverse=True):
        if capture.stat().st_mtime < cutoff: continue
        with capture.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            column = next((k for k in (reader.fieldnames or []) if k.endswith('/SnowTick')), None)
            if not column: continue
            values = []
            for row in reader:
                try: value = float(row[column])
                except (ValueError, TypeError, KeyError): continue
                if math.isfinite(value) and value > 0: values.append(value)
        if not values: continue
        values.sort()
        perf = dict(csv=str(capture), csv_sha256=sha(capture), column=column,
            active_samples=len(values), mean_ms=statistics.mean(values),
            p95_ms=values[int((len(values)-1)*.95)], max_ms=values[-1],
            scope='SnowTick CPU in background Development Editor; walking and frozen real-attack fixtures, not worst-case fast attack sweeps; GPU/shipping performance unmeasured')
        break
    assert perf, 'Fresh post-launch Main active SnowTick CSV is required'
    evidence = {name: sha(OUT/name) for name in ('Delivery.json', 'MainVerificationLaunch.json',
        'MainVerification.json', 'MainVerificationExit.json', 'MainVerify.log', 'PreviousPendingApplyStatus.json')}
    final = dict(success=True, canonical_map_pending=False, native_main_pie_verified=True,
        status='VerifiedCanonicalAttackContact', native_verified_map_asset=native['map_asset'],
        canonical_sha256=delivery['hashes'][MAP], delivery=delivery, main=native,
        main_launch=launch, main_exit=exited, evidence_sha256=evidence,
        foot_depth_cm=float(foot[-1]), weapon_depth_cm=float(weapon[-1]), performance=perf,
        limits=['Frozen real Attack fixtures do not measure worst-case fast montage sweep cost',
            'GPU/shipping performance unmeasured; no original-game pixel parity claim',
            'Old Contact55 preview QA is separate from this fresh canonical Main native QA'],
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(OUT/'FinalVerification.json', final)
    write(OLD/'PendingApplyStatus.json', dict(state='SupersededByAttackContact20261008',
        canonical_map_pending=False, delivery=str(OUT/'Delivery.json'),
        delivery_sha256=receipt_sha, final_verification=str(OUT/'FinalVerification.json'),
        final_verification_sha256=sha(OUT/'FinalVerification.json'),
        previous_status_archive=str(OUT/'PreviousPendingApplyStatus.json'), old_wait_pid=2256,
        worker_action='Superseded; this finalizer performs no process operations',
        old_contact55_native_canonical_qa_claimed=False, utc=final['utc']))
    print('SNOW_ATTACK_CONTACT_FINAL_VERIFIED', json.dumps(dict(
        pid=native['pid'], foot_cm=final['foot_depth_cm'], weapon_cm=final['weapon_depth_cm'], performance=perf)))

if __name__ == '__main__':
    main()
