"""Closed-project, selected attack-VFX polish delivery; root operates mutations.

--prepare writes only this task's Main/Saved staging and backups. --apply requires
an explicit frozen root manifest and approval receipt. Neither mode controls an
editor. Delivery is provisional until --finalize proves fresh Main RHI/readback.
The previous VFX task's helper and evidence are never rewritten.
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
import subprocess

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008'
DELIVERY = OUT / 'MainDelivery'
PLAN = DELIVERY / 'Prepared.json'
ALIAS = 'UnrealEditor-KhazanPlayerAttackVFXPolish20261008'
TEST = 'Source/Khazan/Tests/KZCombatEffectPIETest.cpp'
EFFECTS = 'Content/_Art/Effects'
DAS = 'Content/_Art/Player/Animation/InGame/DAS'
PROTECTED = ('Config', 'Content/Data', 'Content/Maps', 'Content/Monsters',
             'Content/_Art/Enemies', EFFECTS, DAS)
HASH = re.compile(r'^[0-9a-f]{64}$')
REQUIRED_EVIDENCE = {'build_exit', 'build_launch', 'build_log', 'runtime_launch',
    'runtime_exit', 'runtime_driver', 'runtime_log', 'runtime_integrity', 'root_visual_review',
    'saved_montage_audit', 'saved_montage_launch', 'saved_montage_exit',
    'saved_art_audit', 'saved_art_launch', 'saved_art_exit'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def target(root, relative):
    require(isinstance(relative, str) and '\\' not in relative and
            not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'Canonical relative forward-slash path required: ' + str(relative))
    path = (root / relative).resolve()
    require(path != root.resolve() and path.is_relative_to(root.resolve()),
            'Path escapes root: ' + relative)
    return path


def inventory(root, folders, excluded=()):
    excluded = set(excluded)
    return {p.relative_to(root).as_posix(): sha(p) for folder in folders
            for p in (root / folder).rglob('*') if p.is_file() and
            p.relative_to(root).as_posix() not in excluded}


def product(root, selected):
    result = inventory(root, PROTECTED, selected)
    result['Khazan.uproject'] = sha(root / 'Khazan.uproject')
    return result


def write_new(path, data):
    require(path.resolve().is_relative_to(OUT.resolve()), 'Receipts must stay in new task Saved')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def copy_saved(source, destination, expected):
    require(destination.resolve().is_relative_to(DELIVERY.resolve()), 'Staging must stay in Main Saved')
    require(HASH.fullmatch(expected or '') and sha(source) == expected, 'Staging source CAS failed')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, destination.open('xb') as dest:
        shutil.copyfileobj(src, dest)
    require(sha(destination) == expected, 'Staged bytes mismatch')


def proof(ref, original=False):
    require(isinstance(ref, dict) and HASH.fullmatch(ref.get('sha256') or ''), 'Hash-bound evidence ref required')
    path = target(MAIN if original else OUT, ref['path'])
    allowed = (MAIN / 'Saved').resolve() if original else OUT.resolve()
    require(path.is_relative_to(allowed) and path.is_file() and sha(path) == ref['sha256'],
            'Missing/changed evidence: ' + str(path))
    return path


def classify_editors(rows):
    main, unknown = [], []
    for row in rows:
        args = [a or b for a, b in re.findall(r'"([^"]*)"|([^\s"]+)', row.get('CommandLine') or '')]
        projects = [a for a in args if a.lower().endswith('.uproject')]
        if len(projects) != 1 or not Path(projects[0]).is_absolute():
            unknown.append(row)
        elif Path(projects[0]).resolve() == (MAIN / 'Khazan.uproject').resolve():
            main.append(row)
    return dict(utc=utc(), editors=rows, main_project_editors=main,
                unclassified_editors=unknown, method='Read-only Win32_Process; exact absolute .uproject argument')


def process_census():
    command = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $rows=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*.exe'} | Select-Object ProcessId,Name,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $rows -Depth 3 -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
        capture_output=True, text=True, encoding='utf-8', errors='replace', check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout or '[]')
    require(isinstance(rows, list), 'Unexpected process census result')
    return classify_editors(rows)


def closed():
    census = process_census()
    require(not census['main_project_editors'] and not census['unclassified_editors'],
            'Main or unclassified UE editor appeared; stop delivery, never close it')
    return census


def exclusive(path):
    if not path.exists():
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                       ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p)
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
    require(handle not in (None, ctypes.c_void_p(-1).value), 'Selected file locked: ' + str(path))
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle(handle)


def asset_file(asset):
    require(isinstance(asset, str) and asset.startswith('/Game/_Art/Effects/') and '.' not in asset,
            'Only exact /Game/_Art/Effects package names may be selected')
    return 'Content/' + asset.removeprefix('/Game/') + '.uasset'


def selected_rows(frozen, baseline):
    require(frozen.get('status') == 'FrozenForPolishDelivery' and frozen.get('producer_role') == 'root',
            'Explicit root-frozen candidate manifest required')
    sources = frozen.get('selected_sources', [])
    allowed = {TEST}
    extra = frozen.get('scope_change')
    if extra:
        require(extra.get('root_authorized') is True and extra.get('reason') and
                isinstance(extra.get('allowed_sources'), list), 'Runtime scope expansion needs explicit root evidence')
        allowed.update(extra['allowed_sources'])
    require(sources and len({r['file'] for r in sources}) == len(sources), 'Unique selected Source rows required')
    rows = []
    for row in sources:
        file = row['file']
        require(file in allowed and file in baseline['Source'] and file.startswith('Source/') and
                Path(file).suffix in ('.cpp', '.h', '.cs'), 'Unapproved/new Source candidate: ' + file)
        require(row['before_main_sha256'] == baseline['Source'][file], 'Source row differs from latest Main baseline')
        rows.append(dict(file=file, before=row['before_main_sha256'], after=row['expected_private_sha256']))
    art = frozen.get('art', [])
    require(art and len({r['asset'] for r in art}) == len(art), 'Explicit unique Art selection required')
    for row in art:
        file = asset_file(row['asset'])
        require(row['before_main_sha256'] == baseline[EFFECTS].get(file), 'Art before hash differs from baseline')
        require(row.get('source_package') and HASH.fullmatch(row.get('source_sha256', '')) and
                row.get('change_kind'), 'Source provenance and actual change kind required')
        source = proof(row['source_evidence'], original=True)
        require(sha(source) == row['source_sha256'], 'Art source evidence hash differs from source provenance')
        rows.append(dict(file=file, before=row['before_main_sha256'], after=row['expected_private_sha256']))
    require(len({r['file'] for r in rows}) == len(rows), 'Selected paths collide')
    require(all(HASH.fullmatch(r['after'] or '') and r['before'] != r['after'] for r in rows),
            'Selected candidates must be real, hash-bound changes')
    return rows


def montage_audit(audit, baseline):
    require(audit.get('status') == 'passed' and audit.get('asset_saves') == 0 and
            audit.get('source_writes') == 0 and audit.get('package_bytes_unchanged') is True,
            'Saved montage audit must be read-only, successful and byte-preserving')
    require(audit.get('checked_event_ids') == 401 and audit.get('checked_start_markers') == 401 and
            audit.get('checked_end_markers') == 401 and len(audit.get('montages', [])) == 8,
            'Fresh saved audit must cover all8 unchanged montages/401 windows')
    flags = ('unique_actual_trigger_times', 'all_actual_triggers_equal_authored_boundary_policy',
             'original_gameplay_guid_core_input_names_equal', 'original_exact_trigger_snapshot_equal',
             'section_slot_segment_export_rows_equal', 'all_authored_field_types_values_equal')
    packages = set()
    for row in audit['montages']:
        package = row['path'].split('.')[0]
        file = 'Content/' + package.removeprefix('/Game/') + '.uasset'
        require(file.startswith(DAS + '/') and row['saved_sha256'] == baseline[DAS].get(file) and
                all(row.get(flag) is True for flag in flags), 'Saved montage hash/contract changed: ' + package)
        packages.add(package)
    require(len(packages) == 8, 'Saved montage audit contains duplicate packages')


def art_audit(audit, frozen):
    require(audit.get('status') == 'passed' and audit.get('asset_saves') == 0 and
            audit.get('source_writes') == 0, 'Fresh read-only Art audit required')
    rows = audit.get('rows', [])
    expected = {r['asset']: r['expected_private_sha256'] for r in frozen['art']}
    require(len(rows) == len(expected) and {r['asset']: r['saved_sha256'] for r in rows} == expected and
            all(r.get('compile_errors') == [] for r in rows), 'Exact selected Art saved/compile audit failed')


def launch_check(launch, exit_info, project, earliest, rhi):
    require(launch.get('pid') == exit_info.get('pid') and isinstance(launch.get('pid'), int) and
            launch['pid'] > 0 and exit_info.get('exit_code') == 0, 'Fresh process did not exit successfully')
    args = launch.get('args', [])
    require(isinstance(args, list) and str(project / 'Khazan.uproject') in args,
            'Wrong verification project')
    require(not rhi or not any('-nullrhi' in str(a).lower() for a in args), 'Actual RHI missing')
    stamp = dt.datetime.fromisoformat(launch['utc'].replace('Z', '+00:00'))
    require(stamp.tzinfo is not None and earliest <= stamp.timestamp() <= dt.datetime.now(dt.timezone.utc).timestamp(),
            'Verification launch predates candidate or is future-dated')


def runtime_check(driver, log, actual_module):
    require(driver.get('status') == 'passed' and driver.get('package_saves') == 0 and
            driver.get('material_compile_failures') == [], 'Actual RHI test or material compilation failed')
    completion = driver.get('native_completion', '')
    require('Test Completed' in completion and 'Success' in completion and
            'Khazan.CombatEffect.PIE' in completion, 'Current complete native VFX test result missing')
    require('Failed to compile Material' not in log and 'Default Material will be used in game' not in log,
            'Material compile/default fallback present in real RHI log')
    require('InternalLoadLibrary' in log and str(actual_module).replace('\\', '/') in log.replace('\\', '/'),
            'Actual loaded candidate DLL path evidence missing')
    pattern = r'CombatEffect Brutal Case=([0-3])[^\r\n]*ConfiguredDamage=([^\s]+) AuthoredDamage=([^\s]+) DamageMode=([^\s]+)'
    cases = {int(case): (float(damage), float(authored), mode)
             for case, damage, authored, mode in re.findall(pattern, log)}
    require(set(cases) == {0, 1, 2, 3}, 'Current Brutal negative/product-positive coverage missing')
    require(all(cases[i] == (0., 50., 'transient_zero_negative') for i in (0, 1)) and
            all(cases[i] == (50., 50., 'authored_product') for i in (2, 3)) and
            'CombatEffect Brutal cancel/current-instance/wrong-avatar/late-marker cleanup passed' in log,
            'Old HP0/6.25 evidence cannot replace current authored HP50 verification')


def runtime_integrity(report, pid, expected):
    require(report.get('status') == 'passed' and report.get('pid') == pid and
            report.get('package_saves') == 0 and report.get('before') == expected == report.get('after'),
            'Actual RHI Source/Config/Effects/DAS/project/native snapshots changed or are unbound')


def validate(frozen, ready, evidence):
    baseline = ready['baseline']
    require(ready.get('status') == 'PrivateReady' and Path(ready['main']).resolve() == MAIN and
            Path(ready['work']).resolve() == WORK and ready.get('source_count') == len(baseline['Source']),
            'Wrong latest private intake identity')
    rows = selected_rows(frozen, baseline)
    selected = [r['file'] for r in rows]
    source_after = dict(baseline['Source'])
    source_after.update({r['file']: r['after'] for r in rows if r['file'].startswith('Source/')})
    require(inventory(MAIN, ('Source',)) == baseline['Source'] and
            inventory(WORK, ('Source',)) == source_after, 'Full Main/private Source CAS mismatch; intake/rebase first')
    for folder in ('Config', DAS, EFFECTS):
        require(inventory(MAIN, (folder,)) == baseline[folder], 'Main baseline changed: ' + folder)
        expected = dict(baseline[folder])
        expected.update({r['file']: r['after'] for r in rows if r['file'].startswith(folder + '/')})
        require(inventory(WORK, (folder,)) == expected, 'Unselected private changes: ' + folder)
    require(sha(MAIN / 'Khazan.uproject') == sha(WORK / 'Khazan.uproject') == baseline['uproject']['Khazan.uproject'],
            'Project descriptor changed')
    require(inventory(MAIN, ('Binaries/Win64',)) == baseline['native'], 'Stock/previous native/module baseline changed')
    for row in rows:
        require(sha(target(MAIN, row['file'])) == row['before'] and
                sha(target(WORK, row['file'])) == row['after'], 'Selected CAS failed: ' + row['file'])
    require(set(evidence) >= REQUIRED_EVIDENCE, 'Frozen candidate lacks required evidence refs')
    paths = {name: proof(ref) for name, ref in evidence.items()}
    build, build_launch = read(paths['build_exit']), read(paths['build_launch'])
    inputs = {**source_after, **baseline['Config'], **baseline['uproject']}
    require(build.get('exit_code') == 0 and build.get('inputs_unchanged_during_build') is True and
            build.get('private_build_inputs') == inputs == build_launch.get('private_build_inputs') and
            build.get('pid') == build_launch.get('pid') and
            '-Project=' + str(WORK / 'Khazan.uproject') in build_launch.get('args', []) and
            build.get('build_log_sha256') == sha(paths['build_log']), 'New successful exact-input private build required')
    native = build.get('native_binary_hashes', {})
    require(set(native) == {'UnrealEditor-Khazan.dll', 'UnrealEditor-Khazan.pdb', 'UnrealEditor.modules'} and
            all(HASH.fullmatch(value or '') and sha(WORK / 'Binaries/Win64' / name) == value
                for name, value in native.items()), 'Current native binaries differ from successful new build')
    earliest = max(paths['build_exit'].stat().st_mtime,
                   *(target(WORK, r['file']).stat().st_mtime for r in rows))
    for prefix, rhi in (('runtime', True), ('saved_montage', False), ('saved_art', False)):
        launch_check(read(paths[prefix + '_launch']), read(paths[prefix + '_exit']), WORK, earliest, rhi)
        require(paths[prefix + '_launch'].stat().st_mtime >= earliest, 'Fresh proof predates final asset/build: ' + prefix)
        require(paths[prefix + '_exit'].stat().st_mtime >= paths[prefix + '_launch'].stat().st_mtime,
                'Exit receipt predates launch: ' + prefix)
    for prefix, result in (('runtime', 'driver'), ('saved_montage', 'audit'), ('saved_art', 'audit')):
        require(paths[prefix + '_' + result].stat().st_mtime >= paths[prefix + '_launch'].stat().st_mtime,
                'Verification result predates launch: ' + prefix)
    require(read(paths['saved_montage_audit']).get('pid') == read(paths['saved_montage_launch'])['pid'] and
            read(paths['saved_art_audit']).get('pid') == read(paths['saved_art_launch'])['pid'], 'Saved audit PID mismatch')
    montage_audit(read(paths['saved_montage_audit']), baseline)
    art_audit(read(paths['saved_art_audit']), frozen)
    runtime_check(read(paths['runtime_driver']), paths['runtime_log'].read_text(encoding='utf-8', errors='replace'),
                  WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll')
    expected_effects = dict(baseline[EFFECTS])
    expected_effects.update({r['file']: r['after'] for r in rows if r['file'].startswith(EFFECTS + '/')})
    runtime_integrity(read(paths['runtime_integrity']), read(paths['runtime_launch'])['pid'],
        dict(Source=source_after, Config=baseline['Config'], Effects=expected_effects,
             DAS=baseline[DAS], uproject=baseline['uproject'], native=native))
    visual = read(paths['root_visual_review'])
    require(visual.get('producer_role') == 'root' and visual.get('visual_review_passed') is True and
            visual.get('selected_asset_hashes') == {r['asset']: r['expected_private_sha256'] for r in frozen['art']} and
            visual.get('runtime_log_sha256') == sha(paths['runtime_log']), 'Root visual review must bind final real-RHI Art candidate')
    return rows, source_after, native


def prepare(args):
    require(not PLAN.exists() and not (DELIVERY / 'Delivered.json').exists(), 'Preserve existing delivery evidence')
    census = closed()
    frozen_path = proof(dict(path=args.frozen_manifest, sha256=args.frozen_sha256))
    frozen = read(frozen_path)
    ready_path = OUT / 'PrivateReady.json'
    require(frozen.get('private_ready_sha256') == sha(ready_path), 'Frozen manifest must bind current PrivateReady')
    ready = read(ready_path)
    rows, source_after, native = validate(frozen, ready, frozen['evidence'])
    selected = [r['file'] for r in rows]
    main_modules = read(MAIN / 'Binaries/Win64/UnrealEditor.modules')
    work_modules = read(WORK / 'Binaries/Win64/UnrealEditor.modules')
    require(main_modules['BuildId'] == work_modules['BuildId'] and
            work_modules['Modules']['Khazan'] == 'UnrealEditor-Khazan.dll', 'Installed engine/private module manifest mismatch')
    alias = frozen.get('module_alias', ALIAS)
    require(re.fullmatch(re.escape(ALIAS) + r'(?:_[1-9][0-9]*)?', alias), 'Only unique task-specific native aliases allowed')
    require(not any((MAIN / 'Binaries/Win64' / (alias + suffix)).exists() for suffix in ('.dll', '.pdb')),
            'Alias collision; never overwrite any existing native alias')
    protected_main = product(MAIN, selected)
    protected_private = product(WORK, selected)
    for row in rows:
        copy_saved(target(WORK, row['file']), target(DELIVERY / 'Prepared', row['file']), row['after'])
        if row['before'] is not None:
            copy_saved(target(MAIN, row['file']), target(DELIVERY / 'Before', row['file']), row['before'])
    binaries = []
    for suffix in ('.dll', '.pdb'):
        source = 'Binaries/Win64/UnrealEditor-Khazan' + suffix
        copy_saved(WORK / source, DELIVERY / 'Prepared' / source, native[Path(source).name])
        binaries.append(dict(source=source, destination='Binaries/Win64/' + alias + suffix,
                             sha256=native[Path(source).name]))
    manifest = 'Binaries/Win64/UnrealEditor.modules'
    copy_saved(MAIN / manifest, DELIVERY / 'Before' / manifest, sha(MAIN / manifest))
    plan = dict(utc=utc(), status='PreparedOnly', main=str(MAIN), work=str(WORK), closed_mode=True,
        files=rows, packages=sorted(r['asset'] for r in frozen['art']),
        frozen_manifest=dict(path=frozen_path.relative_to(OUT).as_posix(), sha256=sha(frozen_path)),
        private_ready_sha256=sha(ready_path), helper_sha256=sha(Path(__file__)),
        evidence=frozen['evidence'], main_source_before=ready['baseline']['Source'], private_source=source_after,
        protected_main=protected_main, protected_private=protected_private, native_before=ready['baseline']['native'],
        private_native=native, native_files=binaries, module=alias + '.dll',
        modules_before=main_modules, modules_before_sha256=sha(MAIN / manifest),
        initial_process_census=census, final_prepare_census=closed(),
        production_runtime_changed=any(r['file'].startswith('Source/') and r['file'] != TEST for r in rows),
        native_role='New dev QA plus unchanged production runtime unless explicit frozen runtime scope expands.')
    write_new(PLAN, plan)
    check(plan)
    return plan


def check(plan, delivered=False):
    require(plan.get('main') == str(MAIN) and plan.get('work') == str(WORK) and plan.get('closed_mode') is True,
            'Wrong prepared identity')
    require(plan['helper_sha256'] == sha(Path(__file__)) and
            plan['private_ready_sha256'] == sha(OUT / 'PrivateReady.json'), 'Helper/intake changed after prepare')
    frozen = read(proof(plan['frozen_manifest']))
    rows = selected_rows(frozen, read(OUT / 'PrivateReady.json')['baseline'])
    require(rows == plan['files'] and frozen['evidence'] == plan['evidence'], 'Frozen scope changed')
    selected = [r['file'] for r in rows]
    require(product(MAIN, selected) == plan['protected_main'] and
            product(WORK, selected) == plan['protected_private'], 'Protected Data/Config/Maps/Monsters/DAS/Effects changed')
    require(inventory(WORK, ('Source',)) == plan['private_source'] and
            inventory(MAIN, ('Source',)) == plan['private_source' if delivered else 'main_source_before'], 'Full Source CAS changed')
    for ref in plan['evidence'].values():
        proof(ref)
    for row in rows:
        require(sha(target(WORK, row['file'])) == sha(target(DELIVERY / 'Prepared', row['file'])) == row['after'] and
                sha(target(MAIN, row['file'])) == row['after' if delivered else 'before'], 'Selected bytes changed: ' + row['file'])
        if row['before'] is not None:
            require(sha(target(DELIVERY / 'Before', row['file'])) == row['before'], 'Immutable backup changed')
    for name, digest in plan['private_native'].items():
        require(sha(WORK / 'Binaries/Win64' / name) == digest, 'Verified private native changed')
    for row in plan['native_files']:
        require(sha(target(DELIVERY / 'Prepared', row['source'])) == row['sha256'], 'Prepared native changed')
    expected_native = dict(plan['native_before'])
    if delivered:
        expected_native.update({r['destination']: r['sha256'] for r in plan['native_files']})
    actual_native = inventory(MAIN, ('Binaries/Win64',))
    manifest = 'Binaries/Win64/UnrealEditor.modules'
    require({k: v for k, v in actual_native.items() if k != manifest} ==
            {k: v for k, v in expected_native.items() if k != manifest}, 'Stock/previous alias/native inventory changed')


def replace_cas(staged, destination, before, after):
    closed()
    require(sha(destination) == before and sha(staged) == after, 'Immediate selected CAS failed')
    exclusive(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(sha(destination) == before, 'Concurrent destination edit')
    os.replace(staged, destination)
    require(sha(destination) == after, 'Atomic replacement failed')


def apply(args):
    require(args.root_authorized and not (DELIVERY / 'Delivered.json').exists(), 'Only root may apply once after review')
    plan = read(PLAN)
    check(plan)
    approval_path = proof(dict(path=args.approval, sha256=args.approval_sha256))
    approval = read(approval_path)
    require(approval.get('producer_role') == 'root' and approval.get('approved') is True and
            approval.get('prepared_sha256') == sha(PLAN), 'Root review must approve exact prepared bytes')
    stamp = dt.datetime.fromisoformat(approval['utc'].replace('Z', '+00:00'))
    age = (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds()
    require(stamp.tzinfo is not None and stamp >= dt.datetime.fromisoformat(plan['utc']) and 0 <= age <= 300,
            'Root approval stale; refresh after observing current processes')
    census = closed()
    manifest = MAIN / 'Binaries/Win64/UnrealEditor.modules'
    require(sha(manifest) == plan['modules_before_sha256'], 'Main module CAS changed')
    replaced, aliases, module_after = [], [], None
    try:
        for row in plan['native_files']:
            closed()
            destination = target(MAIN, row['destination'])
            with target(DELIVERY / 'Prepared', row['source']).open('rb') as src, destination.open('xb') as dest:
                shutil.copyfileobj(src, dest)
            require(sha(destination) == row['sha256'], 'New alias copy mismatch')
            aliases.append(row['destination'])
        precopy = closed()
        for index, row in enumerate(plan['files']):
            staged = DELIVERY / 'Atomic' / ('product_' + str(index))
            copy_saved(target(DELIVERY / 'Prepared', row['file']), staged, row['after'])
            replace_cas(staged, target(MAIN, row['file']), row['before'], row['after'])
            replaced.append(row)
        check(plan, delivered=True)
        pre_module = closed()
        require(sha(manifest) == plan['modules_before_sha256'], 'Module changed during selected copies')
        modules = dict(plan['modules_before'])
        modules['Modules'] = dict(modules['Modules'])
        modules['Modules']['Khazan'] = plan['module']
        staged = DELIVERY / 'Atomic' / 'UnrealEditor.modules'
        write_new(staged, modules)
        module_after = sha(staged)
        replace_cas(staged, manifest, plan['modules_before_sha256'], module_after)
        check(plan, delivered=True)
        require(sha(manifest) == module_after and read(manifest)['Modules']['Khazan'] == plan['module'], 'Published module changed')
        result = dict(utc=utc(), status='SelectedPolishDeliveredFreshMainValidationPending',
            files=plan['files'], native_files=plan['native_files'], module=plan['module'],
            module_manifest_sha256=module_after, prepared_sha256=sha(PLAN), approval_sha256=sha(approval_path),
            production_runtime_changed=plan['production_runtime_changed'], native_role=plan['native_role'],
            stock_and_previous_aliases_preserved=True, protected_unchanged=True, full_source_matches=True,
            existing_editor_closed=False, existing_editor_reloaded=False, existing_editor_saved=False,
            fresh_Main_actual_RHI_and_saved_audits_required=True,
            censuses=dict(apply_start=census, before_product=precopy, before_module=pre_module))
        write_new(DELIVERY / 'Delivered.json', result)
        return result
    except Exception as error:
        rollback = []
        # Never write rollback bytes while a newly opened user/unknown editor exists.
        try:
            closed()
            if module_after and sha(manifest) == module_after:
                staged = DELIVERY / 'Atomic' / 'module_rollback'
                copy_saved(DELIVERY / 'Before/Binaries/Win64/UnrealEditor.modules', staged, plan['modules_before_sha256'])
                replace_cas(staged, manifest, module_after, plan['modules_before_sha256'])
            for index, row in enumerate(reversed(replaced)):
                closed()
                destination = target(MAIN, row['file'])
                if sha(destination) != row['after']:
                    rollback.append(dict(file=row['file'], status='PreservedConcurrentEdit'))
                    continue
                if row['before'] is None:
                    exclusive(destination)
                    require(sha(destination) == row['after'], 'New asset changed during rollback')
                    destination.unlink()
                else:
                    staged = DELIVERY / 'Atomic' / ('rollback_' + str(index))
                    copy_saved(target(DELIVERY / 'Before', row['file']), staged, row['before'])
                    replace_cas(staged, destination, row['after'], row['before'])
                rollback.append(dict(file=row['file'], status='RestoredBaseline'))
        except Exception as failure:
            rollback.append(dict(status='RollbackStoppedPreserveEditorOrConcurrentWork', error=str(failure)))
        write_new(DELIVERY / ('Failure_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json'),
                  dict(utc=utc(), error=str(error), rollback=rollback, copied_aliases=aliases,
                       aliases_preserved_for_audit=True, fresh_validation_not_claimed=True))
        raise


def finalize(args):
    delivered = read(DELIVERY / 'Delivered.json')
    plan = read(PLAN)
    check(plan, delivered=True)
    require(sha(MAIN / 'Binaries/Win64/UnrealEditor.modules') == delivered['module_manifest_sha256'], 'Delivered module changed')
    final_path = proof(dict(path=args.verification, sha256=args.verification_sha256))
    final = read(final_path)
    require(final.get('producer_role') == 'root' and final.get('status') == 'FreshMainPolishVerified' and
            final.get('delivered_sha256') == sha(DELIVERY / 'Delivered.json'), 'Root final verification must bind exact delivery')
    paths = {key: proof(value) for key, value in final['evidence'].items()}
    needed = {'runtime_launch', 'runtime_exit', 'runtime_driver', 'runtime_log', 'runtime_integrity', 'saved_montage_audit',
              'saved_montage_launch', 'saved_montage_exit', 'saved_art_audit', 'saved_art_launch', 'saved_art_exit'}
    require(set(paths) >= needed, 'Fresh Main verification evidence incomplete')
    after_delivery = dt.datetime.fromisoformat(delivered['utc']).timestamp()
    for prefix, rhi in (('runtime', True), ('saved_montage', False), ('saved_art', False)):
        launch_check(read(paths[prefix + '_launch']), read(paths[prefix + '_exit']), MAIN, after_delivery, rhi)
        require(paths[prefix + '_launch'].stat().st_mtime >= after_delivery, 'Main proof predates delivery')
        require(paths[prefix + '_exit'].stat().st_mtime >= paths[prefix + '_launch'].stat().st_mtime,
                'Main exit receipt predates launch')
    for prefix in ('saved_montage', 'saved_art'):
        require(read(paths[prefix + '_audit']).get('pid') == read(paths[prefix + '_launch'])['pid'] and
                paths[prefix + '_audit'].stat().st_mtime >= paths[prefix + '_launch'].stat().st_mtime,
                'Fresh Main saved audit PID/time mismatch')
    require(paths['runtime_driver'].stat().st_mtime >= paths['runtime_launch'].stat().st_mtime,
            'Main RHI result predates launch')
    runtime_check(read(paths['runtime_driver']), paths['runtime_log'].read_text(encoding='utf-8', errors='replace'),
                  MAIN / 'Binaries/Win64' / delivered['module'])
    frozen = read(proof(plan['frozen_manifest']))
    baseline = read(OUT / 'PrivateReady.json')['baseline']
    expected_effects = dict(baseline[EFFECTS])
    expected_effects.update({r['file']: r['after'] for r in plan['files'] if r['file'].startswith(EFFECTS + '/')})
    # Names are technical snapshot roles, not the stock files to overwrite.
    expected_native = dict(plan['private_native'])
    expected_native['UnrealEditor.modules'] = delivered['module_manifest_sha256']
    runtime_integrity(read(paths['runtime_integrity']), read(paths['runtime_launch'])['pid'],
        dict(Source=plan['private_source'], Config=baseline['Config'], Effects=expected_effects,
             DAS=baseline[DAS], uproject=baseline['uproject'], native=expected_native))
    montage_audit(read(paths['saved_montage_audit']), baseline)
    art_audit(read(paths['saved_art_audit']), frozen)
    check(plan, delivered=True)
    result = dict(utc=utc(), status='MainPolishDeliveredAndFreshVerified', delivered_sha256=sha(DELIVERY / 'Delivered.json'),
                  final_verification_sha256=sha(final_path), module=delivered['module'],
                  production_runtime_changed=plan['production_runtime_changed'], protected_unchanged=True,
                  pixel_parity_claimed=False, existing_editor_modified=False)
    write_new(DELIVERY / 'Completion.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    action.add_argument('--finalize', action='store_true')
    parser.add_argument('--frozen-manifest', default='FrozenCandidateManifest.json')
    parser.add_argument('--frozen-sha256')
    parser.add_argument('--root-authorized', action='store_true')
    parser.add_argument('--approval', default='MainDelivery/RootApproval.json')
    parser.add_argument('--approval-sha256')
    parser.add_argument('--verification', default='FreshMainVerification.json')
    parser.add_argument('--verification-sha256')
    args = parser.parse_args()
    result = prepare(args) if args.prepare else apply(args) if args.apply else finalize(args)
    print(json.dumps({key: result[key] for key in ('status', 'module') if key in result}))
