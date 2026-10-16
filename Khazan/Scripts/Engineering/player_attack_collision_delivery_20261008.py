"""Guarded six-file delivery. Does not close/reload editors or alter binaries.

Run --prepare after verification/current Source intake; release only the two
owned package loaders through Rider, record MainLoaderRelease.json, then --apply.
Native DLL alias/manifest delivery and fresh-process validation are separate.
"""
from pathlib import Path
import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
import re
import shutil

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan').resolve()
OUT = MAIN / 'Metadata/PlayerAttackCollision_20261008'
PRODUCT = ('Source/Khazan/Ability/Combo/KZComboActionAbility.h',
           'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
           'Source/Khazan/Ability/Combo/KZComboDefinitionData.h')
TEST = 'Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp'
ASSETS = ('Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset',
          'Content/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.uasset')
OWNED = PRODUCT + (TEST,) + ASSETS
BASELINE = {PRODUCT[0]: 'cf6b21368d5b2e68a8f67d314ab56bea6616b13f8c2151531b8c5ed6e4072182',
            PRODUCT[1]: '8c1e8e45784c00ccac120d18b1ff1a0f77a517db36f0ba1ba4a497f54d8b9bf1',
            PRODUCT[2]: '99634739e3dc74a0881ef39a0d966029207a8d61de348aeb0f77d5f04a755630',
            TEST: None, ASSETS[0]: '0e557090cecfe166dcf73716614dc33bdffbd430f30dfeb42e5d65d1118a505b',
            ASSETS[1]: None}
PACKAGES = tuple('/Game/' + p[len('Content/'):-len('.uasset')] for p in ASSETS)
REQUIRED = {'player_attack_collision_pie': 'Khazan.Combat.PlayerAttackCollision.PIE',
            'guard_pie': 'Khazan.Guard.PIE', 'heal_pie': 'Khazan.Heal.PIE',
            'combo_regression_pie': None}
PLAN = OUT / 'PreparedDeliveryManifest.json'
RECEIPT = OUT / 'SourceContentDelivered.json'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def target(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Relative path required')
    path = (root / relative).resolve()
    require(path != root and path.is_relative_to(root), 'Path escapes project: ' + relative)
    return path


def shared_read_target(root, relative):
    # Work's Monster content is an intentional Main junction. This exception is
    # read-only and never used for the six mutation destinations or candidates.
    require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Relative path required')
    lexical = Path(os.path.abspath(root / relative))
    require(lexical != root and lexical.is_relative_to(root), 'Read path escapes project')
    path = lexical.resolve()
    require(path.is_relative_to(root) or (root == WORK and path.is_relative_to(MAIN)), 'Unexpected shared read target')
    return path


def sha(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def decode(path):
    value = path.read_bytes()
    return value.decode('utf-16' if value.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig', errors='replace')


def runtime_source(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted((root / 'Source').rglob('*'))
            if p.is_file() and 'Tests' not in p.relative_to(root).parts}


def protected_inventory():
    files = set()
    for directory in ('Source', 'Config'):
        files.update(p for p in (MAIN / directory).rglob('*') if p.is_file())
    for p in (MAIN / 'Content/_Art/Player').rglob('*.uasset'):
        if p.name.startswith(('BP_', 'ABP_')) or 'Physics' in p.name or 'RigidBody' in p.name or 'Item' in p.relative_to(MAIN).parts:
            files.add(p)
    for relative in ('Khazan.uproject', 'Content/Maps/DevMap.umap',
                     'Content/Data/Character/DA_CharacterDefinition_Player.uasset'):
        if target(MAIN, relative).is_file():
            files.add(target(MAIN, relative))
    for family in ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite', 'ApesStoneHandElite', 'Yetuga'):
        for relative in (f'Content/Monsters/{family}/Data/DA_Character_{family}.uasset',
                         f'Content/Monsters/{family}/Effects/GE_Init_{family}.uasset'):
            if target(MAIN, relative).is_file():
                files.add(target(MAIN, relative))
    return {p.relative_to(MAIN).as_posix(): sha(p) for p in sorted(files)
            if p.relative_to(MAIN).as_posix() not in OWNED}


def verify_combo_suite(log, evidence):
    suite = read(log)
    positive = {'weak_y_buffered', 'weak_y_committed', 'charge_02_03', 'rb_overfury',
                'weak5_y', 'weak5_y_committed'}
    negative = 'weak5_y_early'
    results = suite.get('results', [])
    require(suite.get('done') is True and not suite.get('error') and len(results) == 7 and
            {x.get('case') for x in results} == positive | {negative}, 'Combo regression suite is incomplete')
    require(all('error' in x and x['error'] is None for x in results if x['case'] in positive),
            'One of the six positive combo cases failed')
    # The legacy probe stops on a target montage even for its deliberate early
    # input trial. Keep its raw timeout; independently prove the expected reject.
    expectation_path = OUT / 'VerifiedComboExpectations.json'
    expected = read(expectation_path)
    timeout = 'Target montage/section not observed before QA deadline'
    require(expected.get('reviewed') is True and expected.get('expected_reject') is True and
            expected.get('negative_case') == negative and expected.get('raw_error') == timeout and
            set(expected.get('positive_cases', [])) == positive, 'Reviewed negative combo expectation required')
    evidence[expectation_path.relative_to(OUT).as_posix()] = sha(expectation_path)
    required_evidence = {'ComboRegression/SuiteState.json', 'ComboRegression/Runtime_weak5_y_early.json',
                         'AssetAudit/Current_AM_DAS_WeakAttackCombo.t3d', 'run_combo_regression.py'}
    require(set(expected.get('evidence_sha256', {})) == required_evidence and
            log == target(OUT, 'ComboRegression/SuiteState.json'), 'Unexpected combo evidence scope')
    for relative, digest in expected['evidence_sha256'].items():
        require(sha(target(OUT, relative)) == digest, 'Reviewed combo evidence changed: ' + relative)
        evidence[relative] = digest
    scripts = {'Scripts/Engineering/combo_runtime_probe.py', 'Scripts/Engineering/combo_runtime_suite.py'}
    require(set(expected.get('work_script_sha256', {})) == scripts, 'Exact reviewed probe/suite scripts required')
    for relative, digest in expected['work_script_sha256'].items():
        require(sha(target(WORK, relative)) == digest, 'Reviewed QA script changed: ' + relative)
        evidence['work:' + relative] = digest
    runtime = read(target(OUT, 'ComboRegression/Runtime_weak5_y_early.json'))
    result = next(x for x in results if x['case'] == negative)
    rows = runtime.get('rows', [])
    events = runtime.get('events', [])
    require(runtime.get('done') is True and runtime.get('case') == negative and
            runtime.get('actual_input_route') is True and runtime.get('error') == timeout and
            result.get('error') == timeout and result.get('events') == events, 'Early-input raw runtime evidence invalid')
    sections = ['Attack01', 'Attack02', 'Attack03', 'Attack04', 'Attack05']
    observed_sections = list(dict.fromkeys(r['section'] for r in rows if r.get('section')))
    observed_montages = list(dict.fromkeys(r['montage'] for r in rows if r.get('montage')))
    require(observed_sections == sections and result.get('sections') == sections and
            observed_montages == ['AM_DAS_WeakAttackCombo'] and result.get('montages') == observed_montages,
            'Early trial did not complete weak1..5 or unexpectedly reached another montage')
    route = [(e.get('key'), e.get('edge')) for e in events]
    require(route == [('x', 'press'), ('x', 'release')] * 5 + [('y', 'press'), ('y', 'release')],
            'Early trial input events are missing or unexpected')
    export = decode(target(OUT, 'AssetAudit/Current_AM_DAS_WeakAttackCombo.t3d'))
    require(re.search(r'Begin Object Name="AnimNotify_PlayMontageNotify_12"[^\n]*\n\s*NotifyName="InputOpen"', export),
            'Weak05 notify12 is no longer InputOpen')
    marker = re.search(r'BranchingPointMarkers\(12\)=\(NotifyIndex=12,TriggerTime=([\d.]+)\)', export)
    require(marker is not None, 'Weak05 InputOpen marker missing')
    input_open = float(marker.group(1))
    y_events = events[-2:]
    require(y_events == expected.get('negative_input_events'), 'Reviewed early Y events changed')
    y_rows = [r for r in rows if y_events[0]['frame'] <= r['frame'] <= y_events[1]['frame']]
    require(len(y_rows) == y_events[1]['frame'] - y_events[0]['frame'] + 1 and
            all(r['section'] == 'Attack05' and r['montage'] == 'AM_DAS_WeakAttackCombo' and
                r['position'] < input_open for r in y_rows) and input_open == expected.get('input_open_montage_seconds'),
            'Early Y pulse was not wholly before the actual Weak05 InputOpen')


def verify_proof(proof_path):
    proof = read(proof_path)
    require(set(proof.get('required_tests', {})) == set(REQUIRED) and
            all(proof['required_tests'][k] is True for k in REQUIRED), 'Four required test flags must be true')
    require(set(proof.get('source', {})) == set(PRODUCT + (TEST,)), 'Proof Source scope must be exact four files')
    require(set(proof.get('assets', {})) == set(ASSETS), 'Proof asset scope must be exact two packages')
    hashes = {**proof['source'], **proof['assets']}
    for relative, expected in hashes.items():
        require(isinstance(expected, str) and re.fullmatch('[0-9a-fA-F]{64}', expected), 'Invalid candidate hash')
        require(sha(target(WORK, relative)) == expected.lower(), 'Verified Work file changed: ' + relative)
    evidence = {proof_path.relative_to(OUT).as_posix(): sha(proof_path)}
    build = target(OUT, proof['build_log'])
    require(re.search(r'(?m)^Result:\s*Succeeded\s*$', decode(build)), 'Verified cold build did not succeed')
    evidence[build.relative_to(OUT).as_posix()] = sha(build)
    require(set(proof.get('test_logs', {})) == set(REQUIRED), 'Proof needs four test evidence paths')
    for key, path in proof['test_logs'].items():
        log = target(OUT, path)
        if REQUIRED[key]:
            results = re.findall(r'Test Completed\. Result=\{([^}]+)\}[^\n]*Path=\{' + re.escape(REQUIRED[key]) + r'\}', decode(log))
            require(results and results[-1] == 'Success', 'Latest native result is not Success: ' + key)
        else:
            verify_combo_suite(log, evidence)
        evidence[log.relative_to(OUT).as_posix()] = sha(log)
    return {p: h.lower() for p, h in hashes.items()}, evidence


def initializer_audit():
    rows = []
    for family in ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite', 'ApesStoneHandElite', 'Yetuga'):
        for relative in (f'Content/Monsters/{family}/Data/DA_Character_{family}.uasset',
                         f'Content/Monsters/{family}/Effects/GE_Init_{family}.uasset'):
            main_hash, work_hash = sha(target(MAIN, relative)), sha(shared_read_target(WORK, relative))
            if family in ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite'):
                require(main_hash and main_hash == work_hash, 'Required prepared MonsterStats differ: ' + relative)
            rows.append(dict(file=relative, main=main_hash, work=work_hash, equal=main_hash == work_hash,
                             delivery_action='Preserve Main; never copied by this helper'))
    return rows


def prepare_delivery(proof_path=None):
    require(not PLAN.exists() and not RECEIPT.exists(), 'Prepared plan/receipt already exists; do not overwrite snapshots')
    proof_path = Path(proof_path).resolve() if proof_path else OUT / 'VerifiedDeliveryProof.json'
    require(proof_path.is_relative_to(OUT), 'Proof must be inside this report')
    after, evidence = verify_proof(proof_path)
    source_before = {row['file'].replace('\\', '/'): row['main'].lower() for row in read(OUT / 'SourceBefore.json')}
    asset_before = {row['file'].replace('\\', '/'): row['before'].lower() for row in read(OUT / 'PlayerDefinitionsBefore.json')}
    before = {p: source_before[p] for p in PRODUCT}
    before.update({TEST: None, ASSETS[0]: asset_before[ASSETS[0]], ASSETS[1]: None})
    require(before == BASELINE, 'Unexpected original Source/Player DA baseline')
    for relative, expected in before.items():
        require(sha(target(MAIN, relative)) == expected, 'Main target changed from original baseline: ' + relative)
    main_runtime, work_runtime = runtime_source(MAIN), runtime_source(WORK)
    require({p: h for p, h in main_runtime.items() if p not in PRODUCT} ==
            {p: h for p, h in work_runtime.items() if p not in PRODUCT}, 'Main/Work non-owned runtime Source differs; refresh private intake/build first')
    stats = initializer_audit()
    protected = protected_inventory()
    for relative in OWNED:
        ready = target(OUT / 'Ready', relative)
        ready.parent.mkdir(parents=True, exist_ok=True)
        require(not ready.exists(), 'Existing Ready file requires review: ' + relative)
        shutil.copy2(target(WORK, relative), ready)
        require(sha(ready) == after[relative], 'Ready hash mismatch')
        if before[relative] is not None:
            backup = target(OUT / 'Before', relative)
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                require(sha(backup) == before[relative], 'Immutable backup differs: ' + relative)
            else:
                shutil.copy2(target(MAIN, relative), backup)
            require(sha(backup) == before[relative], 'Backup hash mismatch')
    live = read(OUT / 'MainBeforeLive.json')
    require(live.get('pie') is False and live.get('dirty_content') == [] and live.get('dirty_maps') == [], 'Initial Main state was not idle/clean')
    plan = dict(utc=utc(), status='PreparedOnly', main=str(MAIN), work=str(WORK), main_pid=live['pid'],
                world=live['world'], files=[dict(file=p, before=before[p], after=after[p]) for p in OWNED],
                protected=protected, work_runtime=work_runtime, initializer_audit=stats,
                proof=proof_path.relative_to(OUT).as_posix(), evidence=evidence,
                packages=list(PACKAGES), product_runtime_files_added=0, development_file_added=TEST,
                native_binary_delivery='Separate parent-owned alias phase; current Main native remains unchanged')
    write(PLAN, plan)
    check_delivery(plan)
    return plan


def check_delivery(plan=None, delivered=False):
    plan = plan or read(PLAN)
    require(plan.get('main') == str(MAIN) and plan.get('work') == str(WORK) and
            plan.get('packages') == list(PACKAGES) and len(plan.get('files', [])) == len(OWNED) and
            {r.get('file') for r in plan['files']} == set(OWNED), 'Invalid six-file delivery manifest scope')
    require({r['file']: r.get('before') for r in plan['files']} == BASELINE and
            all(isinstance(r.get('after'), str) and re.fullmatch('[0-9a-f]{64}', r['after']) for r in plan['files']),
            'Delivery baseline/candidate hashes are invalid')
    require(protected_inventory() == plan['protected'], 'Protected Source/Config/Player/Stats inventory changed')
    require(runtime_source(WORK) == plan['work_runtime'], 'Prepared Work runtime Source changed')
    for path, expected in plan['evidence'].items():
        evidence_path = target(WORK, path[len('work:'):]) if path.startswith('work:') else target(OUT, path)
        require(sha(evidence_path) == expected, 'Verification evidence changed: ' + path)
    for row in plan['files']:
        p = row['file']
        require(sha(target(WORK, p)) == row['after'] and sha(target(OUT / 'Ready', p)) == row['after'], 'Prepared candidate changed: ' + p)
        require(sha(target(MAIN, p)) == row['after' if delivered else 'before'], 'Main CAS/hash mismatch: ' + p)
        if row['before'] is not None:
            require(sha(target(OUT / 'Before', p)) == row['before'], 'Immutable backup changed: ' + p)
    if delivered:
        require(runtime_source(MAIN) == plan['work_runtime'], 'Delivered Main/Work full runtime Source differs')
    return dict(status='DeliveredHashesPassed' if delivered else 'PreconditionsPassed', owned_files=6,
                protected_files=len(plan['protected']), full_runtime_source_matches=delivered)


def _exclusive_available(path):
    if os.name != 'nt' or not path.exists():
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                       ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p)
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
    require(handle not in (None, ctypes.c_void_p(-1).value), 'File is still locked; release exact package loader: ' + str(path))
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle(handle)


def _release_proof(plan, path):
    release = read(path)
    require(release.get('success') is True and release.get('pid') == plan['main_pid'] and
            Path(release.get('project', '')).resolve() == MAIN and release.get('world') == plan['world'] and
            release.get('pie') is False and release.get('dirty_content') == [] and release.get('dirty_maps') == [] and
            len(release.get('released_packages', [])) == len(PACKAGES) and
            set(release.get('released_packages', [])) == set(PACKAGES), 'Invalid exact-package Main loader-release proof')
    stamp = dt.datetime.fromisoformat(release['utc'].replace('Z', '+00:00'))
    prepared = dt.datetime.fromisoformat(plan['utc'])
    require(stamp.tzinfo is not None and prepared.tzinfo is not None, 'Timezone-aware proof UTC required')
    age = (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds()
    require(stamp >= prepared and 0 <= age <= 300, 'Loader-release proof predates plan or is stale')
    return release


def apply_delivery(release_proof=None):
    require(not RECEIPT.exists(), 'Successful delivery already recorded; do not repeat')
    plan = read(PLAN)
    check_delivery(plan)
    release_path = Path(release_proof).resolve() if release_proof else OUT / 'MainLoaderRelease.json'
    require(release_path.is_relative_to(OUT), 'Loader proof must be inside this report')
    release = _release_proof(plan, release_path)
    for row in plan['files']:
        _exclusive_available(target(MAIN, row['file']))
    module_path = MAIN / 'Binaries/Win64/UnrealEditor.modules'
    modules_before = sha(module_path)
    staged, replaced, rollback = [], [], []
    try:
        for row in plan['files']:
            dest = target(MAIN, row['file'])
            dest.parent.mkdir(parents=True, exist_ok=True)
            staged_file = target(OUT / 'Staged', row['file'])
            staged_file.parent.mkdir(parents=True, exist_ok=True)
            temp = staged_file.with_name(staged_file.name + '.attack-delivery-20261008.tmp')
            require(not temp.exists(), 'Staging file exists; do not overwrite: ' + str(temp))
            shutil.copy2(target(OUT / 'Ready', row['file']), temp)
            staged.append((row, temp))
            require(sha(temp) == row['after'], 'Staged hash mismatch')
        check_delivery(plan)
        for row, temp in staged:
            dest = target(MAIN, row['file'])
            require(sha(dest) == row['before'], 'Main changed immediately before replace: ' + row['file'])
            _exclusive_available(dest)
            os.replace(temp, dest)
            replaced.append(row)
            require(sha(dest) == row['after'], 'Delivered hash mismatch')
        verification = check_delivery(plan, delivered=True)
        require(sha(module_path) == modules_before, 'Module manifest changed during six-file delivery')
        receipt = dict(utc=utc(), status='SourceContentDelivered', files=plan['files'], backup='Before',
                       loader_release=release, verification=verification, modules_unchanged=True,
                       main_pie_started=False, editor_closed=False, binary_copy=False, native_reload=False,
                       current_Main_native='Still existing old process; separate alias/fresh-process validation pending')
        write(RECEIPT, receipt)
        return receipt
    except Exception as error:
        # Roll back only bytes still equal to our own candidate; never overwrite
        # an intervening user edit. Every before byte is immutable and verified.
        for row in reversed(replaced):
            dest = target(MAIN, row['file'])
            if sha(dest) != row['after']:
                rollback.append(dict(file=row['file'], status='SkippedConcurrentEdit')); continue
            try:
                if row['before'] is None:
                    dest.unlink()
                else:
                    backup = target(OUT / 'Before', row['file'])
                    require(sha(backup) == row['before'], 'Rollback backup changed')
                    temp = dest.with_name(dest.name + '.attack-rollback-20261008.tmp')
                    require(not temp.exists(), 'Rollback staging already exists')
                    shutil.copy2(backup, temp); os.replace(temp, dest)
                rollback.append(dict(file=row['file'], status='RestoredBaseline', sha256=sha(dest)))
            except Exception as rollback_error:
                rollback.append(dict(file=row['file'], status='RollbackFailed', error=str(rollback_error)))
        write(OUT / ('DeliveryFailure_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'),
              dict(utc=utc(), error=str(error), replaced=[r['file'] for r in replaced], rollback=rollback))
        raise
    finally:
        for row, temp in staged:
            if temp.exists() and sha(temp) == row['after']:
                temp.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--check', action='store_true')
    action.add_argument('--apply', action='store_true')
    action.add_argument('--audit', action='store_true')
    parser.add_argument('--proof')
    parser.add_argument('--release-proof')
    args = parser.parse_args()
    result = (prepare_delivery(args.proof) if args.prepare else apply_delivery(args.release_proof) if args.apply
              else check_delivery(delivered=args.audit))
    print(json.dumps(dict(status=result.get('status'), files=len(result.get('files', [])),
                          protected_files=result.get('protected_files', len(result.get('protected', {})))), ensure_ascii=False))
