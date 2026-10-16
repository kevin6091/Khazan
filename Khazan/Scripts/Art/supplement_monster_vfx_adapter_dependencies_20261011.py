"""Root-operated exact four-adapter supplement; no editor/source/native edits.

Default --closure prepares Saved-only evidence/staging. --apply copies only the
four previously absent packages after a closed-editor CAS. Original 968-row
receipts and all resource manifests stay immutable. verification_view returns
an in-memory Prepared copy with exactly four protected-content additions.
"""
from pathlib import Path
import argparse
import copy
import json
import os
import re
import runpy
import shutil

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
BASE = OUT / 'MainDelivery/AdapterSupplement'
H = runpy.run_path(str(MAIN / 'Scripts/Art/deliver_monster_vfx_main_20261008.py'))
WORK, RESOURCES = H['WORK'], H['RESOURCES']
load, sha, require, target = H['load'], H['sha'], H['require'], H['target']
PREPARED_SHA = '1e08c8773db1798671efe26f7b662d748e11ca1f8633c8432e5aea728a7425b0'
DELIVERED_SHA = '12f3af9d3a3e3fb50ec8caf42f652e50786d1f452c9ffb4bbea6cb5e5c86603a'
DELIVER_HELPER_SHA = '4ee6074d7652e6fada0573ed163cec77172b29754a70b9ebe09c659cdc93e391'
REVISION_SHA = '6309ef7d0b9f91a4c9182e9e179a15fda75116eb23f01d8638db3b33621be60e'
PRIVATE_NATIVE_SHA = 'b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a'
PRIVATE_MODULES_SHA = '6320d764411f50743e5c25a19a2df5cf43366b6e8d8450e7b3c989f3d6379fe4'
DIAGNOSTIC_SCRIPT_SHA = '4209175915b17aa04fda9479eac6665af614e2dd83b28b3c38dd118f090ff86f'
PRIVATE_DIAGNOSTIC_SHA = '2d4fc32b03af5ec042bc8dfabe427e21bf9f55f5efdf53e52d4ffa132f5aa6b8'
MAIN_DIAGNOSTIC_SHA = 'e0fa8f0031d26f0fd5377b4d3bc4098a9f8b0e30f415d4cb821e7e6d64a5de5b'
FAILED_MAIN_SAVED_SHA = '1d8535b060d303be453f7a7ac6697817547dbe1a6e89e93392dc552a305dfa50'
FIRST_MAIN_RUNTIME_SHA = '2f785b4577e797e12a458f8093410ce7f32b6a1315afa1e4a0dc7ab40adb2b62'
FILES = {'Content/_Art/Effects/Combat/Blood/' + name + '.uasset': digest for name, digest in {
    'FP_BloodSplit_01': '13e673e8b65926d5bf1681a5fdef6fb796bcc19dc99088e7b6c93453322f9d0b',
    'FP_BloodSplit_02': '180742251a320e738e7ecb2e16555fa397f2e7974d2febda6b8e34223ffa712c',
    'FP_Dmg_Blood_Base': 'ba72c52dfe4f49c0b9f85062c9081f647e71b789aadb1e2d10b70c1ce96cedfa',
    'FP_Dmg_Blood_Base_BK': '15001d436ee226ff1405727ca14e297ce9f5a029106ab072c62479b7a4ed6486',
}.items()}
PACKAGES = {'/Game/' + p[8:-7]: p for p in FILES}
PROVENANCE = {
    'Author': OUT / 'Authoring/PrivateAuthoring.json',
    'Plan': OUT / 'PreparedPlaybackPlan.json',
    'Union': RESOURCES / 'UnionAssetManifest.json',
    'Adapters': RESOURCES / 'NativeAdapterMap.json',
    'ImportAdapters': RESOURCES / 'Import_adapters.json',
    'Art457': RESOURCES / 'ArtCandidateManifest.json',
    'MaterialRevision': OUT / 'Authoring/VisualMaterialRepairRevision.json',
    'MainExactDiagnostic': BASE / 'Diagnostics/Main1/Readback.json',
}


def binding(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def immutable_json(path, data):
    require(not path.exists(), 'Never overwrite supplement evidence: ' + str(path))
    H['write'](path, data)


def original_gate(prepared):
    require(sha(OUT / 'MainDelivery/Prepared.json') == PREPARED_SHA
            and sha(OUT / 'MainDelivery/Delivered.json') == DELIVERED_SHA,
            'Original 968 delivery receipts changed')
    require(prepared == load(OUT / 'MainDelivery/Prepared.json') and len(prepared['files']) == 968
            and prepared['helper_sha256'] == DELIVER_HELPER_SHA
            and sha(MAIN / 'Scripts/Art/deliver_monster_vfx_main_20261008.py') == DELIVER_HELPER_SHA,
            'Original Prepared/helper identity changed')
    require(sha(PROVENANCE['MaterialRevision']) == REVISION_SHA, 'Current visual revision changed')
    require(not (set(FILES) & {r['file'] for r in prepared['files']})
            and not (set(FILES) & set(prepared['protected_main'])), 'Supplement was not originally absent')


def authored_roots(author):
    roots = set()
    def walk(value):
        if isinstance(value, dict):
            for v in value.values(): walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
        elif isinstance(value, str):
            roots.update(re.findall(r'/Game/[A-Za-z0-9_/-]+', value))
    for event in author['events']: walk(event.get('effect_fields', {}))
    walk(author['death_presentations'])
    return roots


def validate_closure(path, delivered=False):
    path = Path(path).resolve()
    require(path == (BASE / 'Diagnostics/Private1/Readback.json').resolve()
            and sha(path) == PRIVATE_DIAGNOSTIC_SHA, 'Exact private registry proof changed')
    report = load(path)
    require(report.get('schema') == 'Khazan.MonsterVFX.TargetedDependencyReadback.v1'
            and report.get('status') == 'passed'
            and report.get('mode') == 'private_missing_reference_closure'
            and Path(report['project']).resolve() == WORK.resolve()
            and report.get('package_saves') == report.get('asset_mutations') == report.get('source_writes') == 0
            and report.get('compile_api_calls') == report.get('statistics_api_calls')
                == report.get('warmup_api_calls') == report.get('simulation_calls') == 0
            and report.get('all_source_assets_sha_unchanged') is True
            and report.get('protected_sha_before') == report.get('protected_sha_after'),
            'Actual immutable private registry readback did not pass')
    loaded = report['loaded_native_module']
    require(loaded['name'] == 'UnrealEditor-Khazan.dll' and loaded['build_id'] == H['BUILD_ID']
            and loaded['sha256'] == sha(WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll') == PRIVATE_NATIVE_SHA
            and loaded['manifest_sha256'] == sha(WORK / 'Binaries/Win64/UnrealEditor.modules') == PRIVATE_MODULES_SHA
            and Path(loaded['path']).resolve() == (WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll').resolve()
            and report['script_sha256'] == DIAGNOSTIC_SCRIPT_SHA
            and sha(MAIN / 'Scripts/Art/monster_vfx_saved_targeted_dependency_readback_20261011.py') == DIAGNOSTIC_SCRIPT_SHA,
            'Registry readback loaded a different private native module')
    closure = report['closure']
    author = load(PROVENANCE['Author'])
    roots = authored_roots(author)
    require(len(roots) == 316 and closure['referenced_root_count'] == 316
            and len(closure['referenced_roots']) == 316 and set(closure['referenced_roots']) == roots
            and closure['source_author'] == binding(PROVENANCE['Author']), 'Actual authored root identity differs')
    missing = closure['missing_referenced_roots']
    require(len(missing) == 4 and {r['package'] for r in missing} == set(PACKAGES)
            and len(closure['start_packages']) == 4 and set(closure['start_packages']) == set(PACKAGES),
            'Registry closure does not prove exactly the four absent roots')
    rows = closure['packages']
    require(len(rows) == 22 and len(rows) == len({r['package'] for r in rows}), 'Registry closure must contain exactly 22 unique packages')
    packages = {r['package']: r for r in rows}
    edges = closure['edges']
    require(len(edges) == len({r['package'] for r in edges}) and {r['package'] for r in edges} == set(packages),
            'Registry edges must cover every non-engine package exactly once')
    edge_map = {r['package']: r for r in edges}
    reachable, pending, external = set(), list(PACKAGES), set()
    while pending:
        package = pending.pop()
        if package in reachable: continue
        require(package in packages, 'Unrecorded reachable native package: ' + package)
        reachable.add(package)
        edge = edge_map[package]
        for kind in ('hard', 'soft'):
            require(len(edge[kind]) == len(set(edge[kind])), 'Duplicate registry dependency')
            for child in edge[kind]:
                if child.startswith(('/Engine/', '/Script/')): external.add(child)
                else:
                    require(child.startswith('/Game/'), 'Unknown external dependency namespace: ' + child)
                    pending.append(child)
    require(reachable == set(packages) and set(closure['external_engine_script_packages']) == external,
            'Registry closure includes extra or omitted packages')
    for package, row in packages.items():
        relative = 'Content/' + package[6:] + '.uasset'
        require(row['relative'] == relative and row['is_root'] == (package in PACKAGES), 'Registry path/root mismatch')
        expected = row['private_sha256']
        require(H['HASH'].fullmatch(expected or '') and sha(target(WORK, relative)) == expected,
                'Registry private bytes changed: ' + relative)
        if package in PACKAGES:
            require(expected == FILES[relative] and row['main_sha256'] is None,
                    'Four adapter baseline/candidate identity differs')
        else:
            require(row['main_sha256'] == expected, 'Dependency was absent or had unintended Main bytes: ' + relative)
        require(sha(target(MAIN, relative)) == (expected if delivered or package not in PACKAGES else None),
                'Current Main dependency CAS failed: ' + relative)
    for row in missing:
        require(row['relative'] == PACKAGES[row['package']] and row['main_sha256'] is None
                and row['private_sha256'] == FILES[row['relative']], 'Missing-root proof differs')
    for package in roots - set(PACKAGES):
        require(target(MAIN, 'Content/' + package[6:] + '.uasset').is_file(), 'Additional missing authored root: ' + package)
    return report


def provenance_gate(bindings):
    require(set(bindings) == set(PROVENANCE), 'Provenance scope differs')
    for name, path in PROVENANCE.items():
        require(bindings[name] == binding(path), 'Frozen supplement provenance changed: ' + name)
    diagnostic = load(PROVENANCE['MainExactDiagnostic'])
    exact = diagnostic['exact_event']
    delivered = load(OUT / 'MainDelivery/Delivered.json')
    loaded = diagnostic['loaded_native_module']
    require(sha(PROVENANCE['MainExactDiagnostic']) == MAIN_DIAGNOSTIC_SHA
            and diagnostic['status'] == 'passed' and diagnostic['mode'] == 'main_exact_event'
            and Path(diagnostic['project']).resolve() == MAIN.resolve()
            and diagnostic['script_sha256'] == DIAGNOSTIC_SCRIPT_SHA
            and diagnostic['package_saves'] == diagnostic['asset_mutations'] == diagnostic['source_writes']
                == diagnostic['compile_api_calls'] == diagnostic['statistics_api_calls']
                == diagnostic['warmup_api_calls'] == diagnostic['simulation_calls'] == 0
            and diagnostic['all_source_assets_sha_unchanged'] is True
            and diagnostic['protected_sha_before'] == diagnostic['protected_sha_after']
            and loaded['name'] == delivered['module'] and loaded['sha256'] == PRIVATE_NATIVE_SHA
            and loaded['manifest_sha256'] == delivered['module_manifest_sha256']
            and loaded['build_id'] == H['BUILD_ID']
            and exact['event_id'] == 'KZMVFX_f3af66febacc3ab35102cf8b'
            and exact['guid'] == 'DACA951243FC6ACE5DF95C9E5174021A'
            and exact['field_difference'] == {'ParticleTemplate': {
                'expected': '/Game/_Art/Effects/Combat/Blood/FP_BloodSplit_01.FP_BloodSplit_01', 'actual': None}}
            and exact['particle_main_exists'] is False and exact['particle_private_exists'] is True,
            'Exact Main null-template diagnostic changed')
    union = {r['destination']: r for r in load(PROVENANCE['Union'])}
    adapters = {r['native_destination']: r for r in load(PROVENANCE['Adapters'])['adapters']}
    imported = {r['destination']: r for r in load(PROVENANCE['ImportAdapters'])['native_assets']}
    art = {r['destination'] for r in load(PROVENANCE['Art457'])['assets']}
    for package, relative in PACKAGES.items():
        u, a, i = union[package], adapters[package], imported[package]
        require(package not in art and u.get('reused_native') is True and u.get('existing_native_sha256') is None
                and a['adapter_kind'] == 'source_renderer_Cascade' and a['native_type'] == i['native_type'] == 'ParticleSystem'
                and u['source_package'] == a['source_package'] == i['source_package']
                and u['source_sha256'] == a['source_sha256'] == i['source_sha256']
                and i['sha256'] == FILES[relative], 'Adapter/import/Union provenance differs')
        source = Path(a['source_json'])
        if not source.is_absolute(): source = MAIN / source
        require(sha(source) == a['source_sha256'] and sha(Path(a['derived_graph'])) == a['derived_graph_sha256'],
                'Source/derived adapter graph changed')


def archive_failures():
    history = BASE / 'FailureHistory'
    entries = []
    saved = OUT / 'Authoring/MainSavedReadback.json'
    require(sha(saved) == FAILED_MAIN_SAVED_SHA and load(saved)['status'] == 'failed',
            'Archive the exact failed initial Main saved readback before recheck')
    paths = [(saved, history / 'MainSavedReadback_Attempt1.json')]
    attempt = OUT / 'MainMonsterRuntimePIE/Attempt1'
    require((attempt / 'Exit.json').is_file(), 'First Main native runtime must finish before supplement')
    require(sha(attempt / 'Driver.json') == FIRST_MAIN_RUNTIME_SHA
            and load(attempt / 'Driver.json')['status'] == 'passed'
            and load(attempt / 'Exit.json')['exit_code'] == 0, 'First pre-supplement runtime proof identity differs')
    for name in ('Driver.json', 'Launch.json', 'Exit.json', 'PrivatePIE.log'):
        paths.append((attempt / name, history / 'MainMonsterRuntimePIE_Attempt1' / name))
    for source, dest in paths:
        require(source.is_file(), 'Missing initial Main proof: ' + str(source))
        H['copy_immutable'](source, dest, sha(source))
        entries.append({'original': binding(source), 'archive': binding(dest)})
    archive = {'schema': 'Khazan.MonsterVFX.InitialMainFailureArchive.v1', 'utc': H['utc'](),
               'initial_main_saved_status': 'failed', 'original_runtime_status': 'passed_pre_supplement',
               'original_runtime_attempt': str(attempt), 'entries': entries}
    immutable_json(history / 'Archive.json', archive)
    return binding(history / 'Archive.json')


def validate_archive(record):
    path = Path(record['path'])
    require(path == (BASE / 'FailureHistory/Archive.json').resolve() and sha(path) == record['sha256'], 'Failure archive changed')
    archive = load(path)
    require(archive['initial_main_saved_status'] == 'failed' and len(archive['entries']) == 5, 'Incomplete initial proof archive')
    for row in archive['entries']:
        p = Path(row['archive']['path'])
        require(p.resolve().is_relative_to((BASE / 'FailureHistory').resolve())
                and sha(p) == row['archive']['sha256'] == row['original']['sha256'], 'Immutable initial proof archive changed')
    expected_originals = {str((OUT / 'Authoring/MainSavedReadback.json').resolve())} | {
        str((OUT / 'MainMonsterRuntimePIE/Attempt1' / n).resolve())
        for n in ('Driver.json', 'Launch.json', 'Exit.json', 'PrivatePIE.log')}
    require({str(Path(r['original']['path']).resolve()) for r in archive['entries']} == expected_originals,
            'Initial proof archive path scope differs')
    require(sha(BASE / 'FailureHistory/MainSavedReadback_Attempt1.json') == FAILED_MAIN_SAVED_SHA
            and sha(BASE / 'FailureHistory/MainMonsterRuntimePIE_Attempt1/Driver.json') == FIRST_MAIN_RUNTIME_SHA,
            'Initial saved failure/runtime receipt identity differs')


def supplement_gate(record, delivered=False):
    require(record['schema'] == 'Khazan.MonsterVFX.AdapterDependencySupplement.v1'
            and record['original_prepared_sha256'] == PREPARED_SHA
            and record['original_delivered_sha256'] == DELIVERED_SHA
            and record['deliver_helper_sha256'] == DELIVER_HELPER_SHA
            and record['supplement_helper_sha256'] == sha(__file__)
            and record['original_selected_count'] == 968 and record['supplemental_adapter_count'] == 4
            and record['total_selected_count'] == 972, 'Supplement receipt identity differs')
    rows = record['files']
    require(len(rows) == 4 and {r['relative'] for r in rows} == set(FILES), 'Supplement file scope differs')
    for row in rows:
        relative = row['relative']
        require(row['before_main_sha256'] is None and row['after_sha256'] == FILES[relative]
                and sha(target(BASE / 'Prepared', relative)) == row['after_sha256'], 'Supplement staging changed')
    proof = record['registry_readback']
    require(sha(proof['path']) == proof['sha256'], 'Registry proof changed')
    validate_closure(proof['path'], delivered=delivered)
    provenance_gate(record['provenance'])
    validate_archive(record['failure_archive'])


def verification_view(prepared):
    """Keep original 968 rows/evidence; authorize only four protected additions."""
    original_gate(prepared)
    path = BASE / 'SupplementalDelivered.json'
    record = load(path)
    require(record['status'] == 'FourAdapterDependenciesDeliveredFreshMainRequired'
            and record['main_mutations'] == record['asset_copies'] == 4
            and record['source_mutations'] == record['native_mutations'] == record['asset_saves'] == 0
            and record['prepared_supplement_sha256'] == sha(BASE / 'Prepared.json'), 'Supplement was not successfully delivered')
    prepared_supplement = load(BASE / 'Prepared.json')
    require(record['files'] == prepared_supplement['files']
            and record['registry_readback'] == prepared_supplement['registry_readback']
            and record['provenance'] == prepared_supplement['provenance']
            and record['failure_archive'] == prepared_supplement['failure_archive'], 'Supplement receipt/preparation differs')
    supplement_gate(record, delivered=True)
    view = copy.deepcopy(prepared)
    view['protected_main'].update(FILES)
    return view, path, record


def prepare(closure):
    H['census_gate'](H['census'](), 0)
    original = load(OUT / 'MainDelivery/Prepared.json')
    original_gate(original)
    require(not (BASE / 'Prepared.json').exists() and not (BASE / 'SupplementalDelivered.json').exists(), 'Supplement already prepared/delivered')
    validate_closure(closure)
    provenance = {name: binding(path) for name, path in PROVENANCE.items()}
    provenance_gate(provenance)
    H['check'](original, delivered=True)
    failure_archive = archive_failures()
    for relative, digest in FILES.items():
        H['copy_immutable'](target(WORK, relative), target(BASE / 'Prepared', relative), digest)
    result = {'schema': 'Khazan.MonsterVFX.AdapterDependencySupplement.v1', 'status': 'PreparedOnly', 'utc': H['utc'](),
              'original_prepared_sha256': PREPARED_SHA, 'original_delivered_sha256': DELIVERED_SHA,
              'deliver_helper_sha256': DELIVER_HELPER_SHA, 'supplement_helper_sha256': sha(__file__),
              'original_selected_count': 968, 'supplemental_adapter_count': 4, 'total_selected_count': 972,
              'files': [{'relative': p, 'before_main_sha256': None, 'after_sha256': s} for p, s in sorted(FILES.items())],
              'registry_readback': binding(closure), 'provenance': provenance, 'failure_archive': failure_archive,
              'closed_editor_census': H['census'](), 'main_mutations': 0}
    H['census_gate'](result['closed_editor_census'], 0)
    supplement_gate(result)
    immutable_json(BASE / 'Prepared.json', result)
    return result


def apply():
    require(not (BASE / 'SupplementalDelivered.json').exists(), 'Supplement already delivered')
    plan = load(BASE / 'Prepared.json')
    original = load(OUT / 'MainDelivery/Prepared.json')
    original_gate(original); supplement_gate(plan)
    H['census_gate'](H['census'](), 0)
    H['check'](original, delivered=True)
    copied = []
    try:
        for row in plan['files']:
            H['census_gate'](H['census'](), 0)
            dest = target(MAIN, row['relative'])
            require(not dest.exists(), 'Never overwrite a Main supplement package')
            dest.parent.mkdir(parents=True, exist_ok=True)
            temporary = dest.with_name(dest.name + '.adapter-supplement.tmp')
            require(not temporary.exists(), 'Existing product supplement staging file')
            with temporary.open('xb') as output, target(BASE / 'Prepared', row['relative']).open('rb') as source:
                shutil.copyfileobj(source, output)
            require(sha(temporary) == row['after_sha256'] and not dest.exists(), 'Immediate absent-file copy CAS failed')
            # Windows rename fails if dest exists: atomic publication never replaces a concurrent file.
            require(os.name == 'nt', 'This exclusive publication contract is Windows-only')
            os.rename(temporary, dest)
            copied.append(row)
            require(sha(dest) == row['after_sha256'], 'Supplement copy SHA mismatch')
        supplement_gate(plan, delivered=True)
        view = copy.deepcopy(original); view['protected_main'].update(FILES)
        H['check'](view, delivered=True)
        final_census = H['census'](); H['census_gate'](final_census, 0)
        result = dict(plan, status='FourAdapterDependenciesDeliveredFreshMainRequired', utc=H['utc'](),
                      prepared_supplement_sha256=sha(BASE / 'Prepared.json'), main_mutations=4, asset_copies=4,
                      source_mutations=0, native_mutations=0, asset_saves=0,
                      final_process_census=final_census, fresh_Main_verification_required=True)
        immutable_json(BASE / 'SupplementalDelivered.json', result)
        return result
    except Exception as error:
        rollback = []
        for row in reversed(copied):
            dest = target(MAIN, row['relative'])
            if sha(dest) == row['after_sha256']:
                H['exclusive'](dest); dest.unlink(); rollback.append({'relative': row['relative'], 'status': 'RemovedOwnNewPackage'})
            else: rollback.append({'relative': row['relative'], 'status': 'PreservedConcurrentEdit'})
        immutable_json(BASE / 'FailedApply.json', {'status': 'failed', 'utc': H['utc'](), 'error': str(error), 'rollback': rollback})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--closure', type=Path)
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.closure: result = prepare(args.closure.resolve())
    elif args.apply: result = apply()
    else:
        view, _, result = verification_view(load(OUT / 'MainDelivery/Prepared.json'))
        H['check'](view, delivered=True)
    print(json.dumps({'status': result['status'], 'original_selected_count': 968, 'supplemental_adapter_count': 4, 'total_selected_count': 972}))
