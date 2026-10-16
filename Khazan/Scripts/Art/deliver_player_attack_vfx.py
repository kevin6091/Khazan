"""Selected VFX delivery. --prepare writes only Saved; --apply is root-operated.

No editor calls, package saves, compile, native reload or process control.
Requires fresh exact-package MainRelease.json before any Main product mutation.
"""
from pathlib import Path
import argparse, ctypes, datetime as dt, hashlib, json, os, re, shutil, subprocess

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
DELIVERY = OUT / 'MainDelivery'
PLAN = DELIVERY / 'Prepared.json'
SOURCES = {'Source/Khazan/Ability/Combo/KZComboActionAbility.h', 'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
           'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h', 'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp',
           'Source/Khazan/Environment/KZSnowDeformation.h', 'Source/Khazan/Khazan.Build.cs', 'Source/Khazan/Tests/KZCombatEffectPIETest.cpp'}
BRUTAL_SOURCES = {'Source/Khazan/Ability/KZActionAbility.h', 'Source/Khazan/Ability/KZActionAbility.cpp',
                 'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.h',
                 'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp'}
NO_EDITOR_WORLD = '<no-running-Main-editor>'

def require(value, message):
    if not value: raise RuntimeError(message)

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def target(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), 'Relative path required')
    p = (root / relative).resolve()
    require(p != root.resolve() and p.is_relative_to(root.resolve()), 'Destination escapes root: ' + relative)
    return p

def write(path, data, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.vfx.tmp')
    require(not temp.exists(), 'Existing receipt staging file: ' + str(temp))
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if expected is not None: require(sha(path) == expected, 'Immediate manifest CAS failed; preserve latest')
    os.replace(temp, path)

def inventory(root, folders, excluded=()):
    excluded = set(excluded)
    return {p.relative_to(root).as_posix(): sha(p) for folder in folders for p in (root / folder).rglob('*')
            if p.is_file() and p.relative_to(root).as_posix() not in excluded}

def protected(root, selected):
    result = inventory(root, ('Config', 'Content/Data', 'Content/Maps', 'Content/_Art/Player/Animation/InGame/DAS', 'Content/_Art/Effects'), selected)
    result['Khazan.uproject'] = sha(root / 'Khazan.uproject')
    return result

def binaries():
    return {p.name: sha(p) for p in (MAIN / 'Binaries/Win64').glob('UnrealEditor-Khazan*') if p.is_file()}

def copy_saved(src, dest, expected):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists(): require(sha(dest) == expected, 'Immutable prepared/backup differs: ' + str(dest))
    else: shutil.copy2(src, dest)
    require(sha(dest) == expected, 'Prepared copy hash mismatch')

def proof_path(value):
    p = Path(value).resolve()
    require(p.is_relative_to(OUT.resolve()) and p.is_file(), 'Evidence must exist inside task report: ' + str(p))
    return p

def process_census():
    """Read-only local WMI query; script paths do not identify the project arg."""
    command = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $rows=@(Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'\" | Select-Object ProcessId,Name,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $rows -Depth 3 -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    rows = json.loads(result.stdout or '[]'); require(isinstance(rows, list), 'Unexpected process census')
    main, unknown = [], []
    for row in rows:
        command_line = row.get('CommandLine') or ''
        arguments = [a or b for a,b in re.findall(r'"([^"]*)"|([^\s"]+)', command_line)]
        projects = [a for a in arguments if a.lower().endswith('.uproject')]
        if not projects or any(not Path(p).is_absolute() for p in projects): unknown.append(row)
        elif any(Path(p).resolve() == (MAIN / 'Khazan.uproject').resolve() for p in projects): main.append(row)
    return dict(utc=utc(), editors=rows, main_project_editors=main, unclassified_editors=unknown,
                method='Read-only Win32_Process; exact absolute uproject command-line argument; unknown project identity blocks closed mode.')

def absent(census):
    require(census.get('main_project_editors') == [] and census.get('unclassified_editors') == [], 'Main or unclassified editor is running; closed mode blocked')

def prepare(args):
    require(not PLAN.exists() and not (DELIVERY / 'Delivered.json').exists(), 'Existing delivery records; preserve them')
    require(args.main_pid is not None and args.main_pid >= 0, 'Explicit Main PID or0 closed mode required')
    initial_census = None
    if args.main_pid == 0:
        require(args.world == NO_EDITOR_WORLD, 'Closed mode must not invent an editor world')
        initial_census = process_census(); absent(initial_census)
    native_path = OUT / 'NativeBuildCandidateProof.json'; native_header = read(native_path)
    author_relative = native_header.get('authoring_receipt', 'Authoring/PrivateAuthoring.json')
    require(author_relative in ('Authoring/PrivateAuthoring.json', 'Authoring/CombinedPrivateAuthoring.json'), 'Unapproved authoring receipt')
    include_brutal = author_relative == 'Authoring/CombinedPrivateAuthoring.json'
    selected_sources = SOURCES | BRUTAL_SOURCES if include_brutal else SOURCES
    montage_count, effect_count = (8, 401) if include_brutal else (6, 347)
    paths = [native_path, OUT / 'SourceIntake/MainIntake.json', OUT / author_relative,
             OUT / 'ResourceAudit/ArtCandidateManifest.json', proof_path(args.saved_audit), OUT / 'RuntimePIE/Driver.json',
             OUT / 'RuntimePIE/Exit.json', OUT / 'RuntimePIE/Launch.json', proof_path(args.floor_proof)]
    native, intake, author, art, audit, driver, exit_info, launch, floor = [read(p) for p in paths]
    require(native['status'] == 'passed_private_candidate_preflight' and native['MainSourceIntakeUnchanged'] and native['only_selected_private_source_changes'], 'Native candidate preflight failed')
    require(native['native_build_exit']['exit_code'] == 0, 'Native build did not finish successfully')
    require(inventory(MAIN, ('Source',)) == intake['files'], 'Main Source changed after intake; rebase first')
    require(inventory(WORK, ('Source',)) == native['private_source'], 'Private Source differs from compiled candidate')
    require(inventory(MAIN, ('Config',)) == native['MainConfig'] and inventory(WORK, ('Config',)) == native['privateConfig'], 'Config changed after native proof')
    module_file = WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll'
    require(sha(module_file) == native['private_native_module'] and sha(WORK / 'Binaries/Win64/UnrealEditor.modules') == native['private_module_manifest'], 'Private module changed after proof')
    require(author['status'] == 'passed' and len(author['montages']) == montage_count and len(author['events']) == effect_count, 'Exact selected montage/event authoring proof required')
    require(native['montages'] == author, 'Native candidate does not bind current montage authoring proof')
    require(all(m['old_gameplay_fields_equal'] and m['unique_branching_trigger_times'] for m in author['montages']), 'Existing gameplay or branching invariants failed')
    art_count = art['candidate_count']
    require(art_count in (12, 15, 16) and len(art['rows']) == art_count and all(r['private_expected_match'] and r['main_preserved'] for r in art['rows']), 'Only the approved twelve, fifteen or sixteen exact art candidates are allowed')
    art_whitelist = {r['asset']: {k: r[k] for k in ('source_package', 'source_sha256', 'before_main_sha256', 'expected_private_sha256')} for r in art['rows']}
    require(len(art_whitelist) == art_count and all(r['source_package'] and re.fullmatch('[0-9a-f]{64}', r['source_sha256']) for r in art_whitelist.values()), 'Unique original source/hash whitelist required')
    require(audit.get('status') == 'passed' and driver.get('status') == 'passed' and exit_info['exit_code'] == 0, 'Fresh saved/native RHI verification not passed')
    plan_name = 'CombinedPreparedPlaybackPlan.json' if include_brutal else 'PreparedPlaybackPlan.json'
    require(audit.get('checked_event_ids') == effect_count and audit.get('checked_start_markers') == effect_count and
            audit.get('checked_end_markers') == effect_count and len(audit.get('montages', [])) == montage_count and
            audit.get('asset_saves') == 0 and audit.get('source_writes') == 0, 'Saved audit must verify the exact current montage/event scope without saves')
    require(audit.get('inputs', {}).get('plan_sha256') == sha(OUT / plan_name) and
            audit.get('inputs', {}).get('authoring_sha256') == sha(paths[2]), 'Saved audit does not bind the current plan and authoring hashes')
    require(paths[4].stat().st_mtime >= paths[2].stat().st_mtime and driver.get('package_saves') == 0 and exit_info['pid'] == launch['pid'] != args.main_pid, 'Saved/runtime receipt is stale or process identity mismatches')
    require(str(WORK / 'Khazan.uproject') in launch['args'] and not any('-nullrhi' in str(a).lower() for a in launch['args']), 'Actual private RHI launch required')
    require(floor.get('status') == 'passed' and not floor.get('error'), 'Lit floor RHI receipt not passed')
    require(floor.get('visual_review_passed') is True, 'Raw script completion is not valid lit floor visual evidence')
    require(floor.get('selected_asset_hashes') == {r['asset']: r['expected_private_sha256'] for r in art['rows']}, 'Reviewed floor proof does not bind all current art candidates')
    require('Test Completed' in driver.get('native_completion', '') and 'Success' in driver['native_completion'] and 'Khazan.CombatEffect.PIE' in driver['native_completion'], 'Exact native CombatEffect result missing')
    log_path = OUT / 'RuntimePIE/PrivatePIE.log'; log = log_path.read_text(encoding='utf-8', errors='replace')
    require(driver.get('material_compile_failures') == [] and 'Failed to compile Material' not in log and
            'Default Material will be used in game' not in log, 'RHI shader/default-material fallback must be resolved before delivery')
    require(str(module_file).replace('\\', '/') in log.replace('\\', '/') and 'InternalLoadLibrary' in log, 'Actual private native load evidence missing')
    require(module_file.stat().st_mtime <= paths[7].stat().st_mtime and paths[0].stat().st_mtime <= paths[7].stat().st_mtime, 'Native evidence newer than runtime launch; rerun PIE')
    require((WORK / 'Binaries/Win64/UnrealEditor-Khazan.pdb').stat().st_mtime <= paths[7].stat().st_mtime, 'Native symbols are newer than verified process')
    paths.extend((log_path, OUT / plan_name, OUT / 'Build/Exit.json', OUT / 'Build/Launch.json', OUT / 'Build/PrivateBuild.log'))
    rows = [dict(file=r['relative'], before=r['before'], after=r['after']) for r in native['source_changes']]
    require({r['file'] for r in rows} == selected_sources and len(rows) == len(selected_sources), 'Exact selected source candidates required')
    for r in rows: require(intake['files'].get(r['file']) == r['before'] and native['private_source'].get(r['file']) == r['after'], 'Source candidate does not bind intake/build')
    rows += [dict(file=m['relative'], before=m['before_sha256'], after=m['after_sha256']) for m in author['montages']]
    for r in art['rows']:
        relative = 'Content/' + r['asset'].removeprefix('/Game/') + '.uasset'
        require(Path(r['main_file']).resolve() == target(MAIN, relative) and Path(r['private_file']).resolve() == target(WORK, relative), 'Art manifest destination mismatch')
        rows.append(dict(file=relative, before=r['before_main_sha256'], after=r['expected_private_sha256']))
    file_count = len(selected_sources) + montage_count + art_count
    package_count = montage_count + art_count
    require(len(rows) == file_count and len({r['file'] for r in rows}) == file_count, 'Exact Source, montage and selected art scope required')
    for r in rows:
        require(re.fullmatch('[0-9a-f]{64}', r['after']) and sha(target(MAIN, r['file'])) == r['before'] and sha(target(WORK, r['file'])) == r['after'], 'Selected baseline/candidate changed: ' + r['file'])
        copy_saved(target(WORK, r['file']), target(DELIVERY / 'Prepared', r['file']), r['after'])
        if r['before'] is not None: copy_saved(target(MAIN, r['file']), target(DELIVERY / 'Before', r['file']), r['before'])
    manifest = MAIN / 'Binaries/Win64/UnrealEditor.modules'; main_modules = read(manifest); work_modules = read(WORK / 'Binaries/Win64/UnrealEditor.modules')
    require(main_modules['BuildId'] == work_modules['BuildId'] == '55116800' and work_modules['Modules']['Khazan'] == 'UnrealEditor-Khazan.dll', 'Installed engine BuildId/private module mismatch')
    require(Path(main_modules['Modules']['Khazan']).name == main_modules['Modules']['Khazan'], 'Unexpected selected module path')
    alias = 'UnrealEditor-KhazanPlayerAttackVFX20261008'; suffix = 0
    while any((MAIN / 'Binaries/Win64' / (alias + e)).exists() for e in ('.dll', '.pdb')):
        suffix += 1; alias = 'UnrealEditor-KhazanPlayerAttackVFX20261008_' + str(suffix)
    native_rows = []
    for extension in ('.dll', '.pdb'):
        relative = 'Binaries/Win64/UnrealEditor-Khazan' + extension; expected = sha(WORK / relative)
        require(expected, 'Missing private native binary: ' + relative)
        copy_saved(WORK / relative, DELIVERY / 'Prepared' / relative, expected)
        native_rows.append(dict(source=relative, destination='Binaries/Win64/' + alias + extension, sha256=expected))
    copy_saved(manifest, DELIVERY / 'Before/Binaries/Win64/UnrealEditor.modules', sha(manifest))
    selected = [r['file'] for r in rows]
    result = dict(utc=utc(), status='PreparedOnly', main=str(MAIN), work=str(WORK), main_pid=args.main_pid, world=args.world, editor_running=args.main_pid != 0, initial_process_census=initial_census,
                  files=rows, packages=sorted('/Game/' + p.removeprefix('Content/').removesuffix('.uasset') for p in selected if p.startswith('Content/')),
                  art_candidate_count=art_count, selected_file_count=file_count, selected_package_count=package_count,
                  source_candidates=sorted(selected_sources), montage_count=montage_count, effect_count=effect_count,
                  authoring_receipt=author_relative,
                  art_manifest_sha256=sha(paths[3]), art_whitelist=art_whitelist,
                  evidence={p.relative_to(OUT).as_posix(): sha(p) for p in paths}, private_source=native['private_source'], main_source_before=intake['files'],
                  protected_main=protected(MAIN, selected), protected_private=protected(WORK, selected), preserved_native=binaries(),
                  native_files=native_rows, module=alias + '.dll', modules_before=main_modules, modules_before_sha256=sha(manifest), BuildId='55116800', helper_sha256=sha(Path(__file__)))
    write(PLAN, result); check(result); return result

def check(plan, delivered=False):
    art_count = plan['art_candidate_count']
    include_brutal = plan['authoring_receipt'] == 'Authoring/CombinedPrivateAuthoring.json'
    selected_sources = SOURCES | BRUTAL_SOURCES if include_brutal else SOURCES
    montage_count, effect_count = (8, 401) if include_brutal else (6, 347)
    require(plan['main'] == str(MAIN) and plan['work'] == str(WORK) and art_count in (12, 15, 16) and
            plan['source_candidates'] == sorted(selected_sources) and plan['montage_count'] == montage_count and plan['effect_count'] == effect_count and
            len(plan['files']) == plan['selected_file_count'] == len(selected_sources) + montage_count + art_count and
            len(plan['packages']) == plan['selected_package_count'] == montage_count + art_count, 'Invalid prepared scope')
    require(sha(Path(__file__)) == plan['helper_sha256'], 'Delivery helper changed after preparation')
    selected = [r['file'] for r in plan['files']]
    art_path = OUT / 'ResourceAudit/ArtCandidateManifest.json'; require(sha(art_path) == plan['art_manifest_sha256'], 'Prepared art manifest changed')
    art = read(art_path)
    require(art['candidate_count'] == art_count and {r['asset']: {k: r[k] for k in ('source_package', 'source_sha256', 'before_main_sha256', 'expected_private_sha256')} for r in art['rows']} == plan['art_whitelist'], 'Exact art source/hash whitelist changed')
    author = read(OUT / plan['authoring_receipt'])
    require(author['status'] == 'passed' and len(author['montages']) == montage_count and len(author['events']) == effect_count, 'Prepared exact authoring scope changed')
    expected = selected_sources | {m['relative'] for m in author['montages']} | {'Content/' + asset.removeprefix('/Game/') + '.uasset' for asset in plan['art_whitelist']}
    require(set(selected) == expected and set(plan['packages']) == {'/Game/' + p.removeprefix('Content/').removesuffix('.uasset') for p in expected if p.startswith('Content/')}, 'Selected file/package set differs from approved source and manifests')
    require(protected(MAIN, selected) == plan['protected_main'] and protected(WORK, selected) == plan['protected_private'], 'Protected Config/Data/Maps/DAS/Effects changed')
    require(inventory(WORK, ('Source',)) == plan['private_source'], 'Compiled private Source changed')
    require(inventory(MAIN, ('Source',)) == plan['private_source' if delivered else 'main_source_before'], 'Main full Source CAS mismatch')
    for path, expected in plan['evidence'].items(): require(sha(target(OUT, path)) == expected, 'Evidence changed: ' + path)
    for r in plan['files']:
        require(sha(target(WORK, r['file'])) == r['after'] and sha(target(DELIVERY / 'Prepared', r['file'])) == r['after'], 'Candidate changed: ' + r['file'])
        require(sha(target(MAIN, r['file'])) == r['after' if delivered else 'before'], 'Main selected CAS mismatch: ' + r['file'])
        if r['before'] is not None: require(sha(target(DELIVERY / 'Before', r['file'])) == r['before'], 'Backup changed')
    for name, expected in plan['preserved_native'].items(): require(sha(MAIN / 'Binaries/Win64' / name) == expected, 'Existing native binary changed: ' + name)
    for r in plan['native_files']:
        require(sha(target(WORK, r['source'])) == r['sha256'] and sha(target(DELIVERY / 'Prepared', r['source'])) == r['sha256'], 'Prepared native binary changed')
        if delivered: require(sha(target(MAIN, r['destination'])) == r['sha256'], 'Delivered alias changed')

def exclusive(path):
    if not path.exists(): return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True); create = kernel.CreateFileW
    create.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p); create.restype = ctypes.c_void_p
    handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
    require(handle not in (None, ctypes.c_void_p(-1).value), 'Still locked; release exact selected loader: ' + str(path))
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,); kernel.CloseHandle(handle)

def apply(args):
    require(not (DELIVERY / 'Delivered.json').exists(), 'Successful delivery already recorded')
    plan = read(PLAN); check(plan)
    release_path = proof_path(args.release); release = read(release_path)
    require(release.get('success') is True and release.get('pid') == plan['main_pid'] and Path(release.get('project', '')).resolve() == MAIN and release.get('world') == plan['world'], 'Wrong Main release identity')
    require(release.get('pie') is False and release.get('dirty_content') == [] and release.get('dirty_maps') == [] and set(release.get('released_packages', [])) == set(plan['packages']), 'Exact selected clean idle package release required')
    require(len(release['released_packages']) == plan['selected_package_count'] and release.get('prepared_sha256') == sha(PLAN), 'Release does not bind prepared plan')
    stamp = dt.datetime.fromisoformat(release['utc'].replace('Z', '+00:00')); prepared = dt.datetime.fromisoformat(plan['utc']); age = (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds()
    require(stamp.tzinfo is not None and stamp >= prepared and 0 <= age <= 300, 'Release proof is stale')
    final_census = None
    if not plan['editor_running']:
        require(release.get('editor_running') is False and plan['main_pid'] == 0 and plan['world'] == NO_EDITOR_WORLD, 'Closed release mode mismatch')
        recorded_census = release.get('process_census') or {}; absent(recorded_census)
        census_stamp = dt.datetime.fromisoformat(recorded_census['utc'].replace('Z', '+00:00')); census_age = (dt.datetime.now(dt.timezone.utc) - census_stamp).total_seconds()
        require(census_stamp.tzinfo is not None and census_stamp >= prepared and 0 <= census_age <= 300, 'Closed process census is stale')
        final_census = process_census(); absent(final_census)
    manifest = MAIN / 'Binaries/Win64/UnrealEditor.modules'; require(sha(manifest) == plan['modules_before_sha256'], 'Main module selection changed; preserve latest')
    for r in plan['files']: exclusive(target(MAIN, r['file']))
    replaced = []; module_after = None
    try:
        for r in plan['native_files']:
            dest = target(MAIN, r['destination']); require(not dest.exists(), 'Unique alias now exists; never overwrite')
            shutil.copy2(target(DELIVERY / 'Prepared', r['source']), dest); require(sha(dest) == r['sha256'], 'Native alias copy failed')
        if not plan['editor_running']: absent(process_census())
        for r in plan['files']:
            dest = target(MAIN, r['file']); exclusive(dest); require(sha(dest) == r['before'], 'Concurrent Main selected edit')
            dest.parent.mkdir(parents=True, exist_ok=True); temp = dest.with_name(dest.name + '.vfx-delivery.tmp')
            require(not temp.exists(), 'Existing product staging file'); shutil.copy2(target(DELIVERY / 'Prepared', r['file']), temp)
            require(sha(temp) == r['after'] and sha(dest) == r['before'], 'Immediate CAS failed'); exclusive(dest)
            os.replace(temp, dest); replaced.append(r); require(sha(dest) == r['after'], 'Selected copy failed')
        check(plan, delivered=True); require(sha(manifest) == plan['modules_before_sha256'], 'Main module changed during product copy')
        if not plan['editor_running']: final_census = process_census(); absent(final_census)
        data = read(manifest); data['Modules']['Khazan'] = plan['module']; write(manifest, data, expected=plan['modules_before_sha256']); module_after = sha(manifest)
        check(plan, delivered=True)
        require(sha(manifest) == module_after and read(manifest)['Modules']['Khazan'] == plan['module'], 'Module selection changed after alias publication')
        result = dict(utc=utc(), status='SourceContentAndNativeAliasDelivered', files=plan['files'], module=plan['module'], native_files=plan['native_files'],
                      module_manifest_sha256=module_after, BuildId=plan['BuildId'], prepared_sha256=sha(PLAN), release_sha256=sha(release_path),
                      full_source_matches=True, protected_unchanged=True, stock_native_preserved=True, existing_editor_reloaded=False,
                      existing_editor_closed=False, assets_saved_in_existing_editor=False, fresh_Main_validation_required=True,
                      editor_running_at_prepare=plan['editor_running'], closed_mode_process_census=final_census)
        write(DELIVERY / 'Delivered.json', result); return result
    except Exception as error:
        rollback = []
        if module_after and sha(manifest) == module_after:
            temp = manifest.with_name('UnrealEditor.modules.vfx-rollback.tmp'); require(not temp.exists(), 'Existing module rollback staging')
            shutil.copy2(DELIVERY / 'Before/Binaries/Win64/UnrealEditor.modules', temp)
            require(sha(manifest) == module_after and sha(temp) == plan['modules_before_sha256'], 'Module rollback CAS failed')
            os.replace(temp, manifest)
        for r in reversed(replaced):
            dest = target(MAIN, r['file'])
            if sha(dest) != r['after']: rollback.append(dict(file=r['file'], status='PreservedConcurrentEdit')); continue
            try:
                exclusive(dest)
                if r['before'] is None: dest.unlink()
                else:
                    backup = target(DELIVERY / 'Before', r['file']); require(sha(backup) == r['before'], 'Rollback backup changed')
                    temp = dest.with_name(dest.name + '.vfx-rollback.tmp'); require(not temp.exists(), 'Existing rollback staging'); shutil.copy2(backup, temp); os.replace(temp, dest)
                rollback.append(dict(file=r['file'], status='RestoredBaseline'))
            except Exception as failure: rollback.append(dict(file=r['file'], status='RollbackFailed', error=str(failure)))
        write(DELIVERY / ('Failure_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'), dict(utc=utc(), error=str(error), rollback=rollback, unique_alias_preserved_for_audit=True)); raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); action = parser.add_mutually_exclusive_group(required=True); action.add_argument('--prepare', action='store_true'); action.add_argument('--apply', action='store_true')
    audit_name = 'CombinedSavedAssetAudit.json' if (OUT / 'Authoring/CombinedPrivateAuthoring.json').is_file() else 'SavedAssetAudit.json'
    parser.add_argument('--floor-proof'); parser.add_argument('--saved-audit', default=str(OUT / audit_name)); parser.add_argument('--main-pid', type=int); parser.add_argument('--world', default='/Game/Maps/DevMap.DevMap')
    parser.add_argument('--release', default=str(DELIVERY / 'MainRelease.json')); args = parser.parse_args()
    if args.prepare: require(args.main_pid is not None and args.floor_proof, '--prepare needs --main-pid and --floor-proof')
    result = prepare(args) if args.prepare else apply(args)
    print(json.dumps({k: result[k] for k in ('status', 'module') if k in result}))
