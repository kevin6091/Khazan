"""Root-launched, read-only exact event and bounded missing-resource closure.

Main reads one failed event. Private follows hard/soft dependencies only from
absent Main consumer roots in the immutable author journal. No save or compile.
"""
from pathlib import Path
import ast
import ctypes
import datetime as dt
import hashlib
import json
import os
import re
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
PRIVATE = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
VERIFY_MAIN = os.environ.get('KZ_MONSTER_VFX_VERIFY_MAIN') == '1'
assert WORK == (MAIN if VERIFY_MAIN else PRIVATE), 'Diagnostic project/mode mismatch'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
BASE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
OUT = Path(os.environ['KZ_MONSTER_VFX_TARGETED_DEPENDENCY_REPORT']).resolve()
assert OUT.is_relative_to(BASE.resolve()) and OUT != BASE.resolve()
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT / 'Readback.json').exists(), 'Fresh diagnostic report required'
AUTHOR_FILE = BASE / 'Authoring/PrivateAuthoring.json'
AUTHOR_SHA = 'fe268dad08bd3e34b33671be6307e641a7b95bf1c318e08ad6a4ef0c928e80c0'
EVENT = 'KZMVFX_f3af66febacc3ab35102cf8b'
GUID = 'DACA951243FC6ACE5DF95C9E5174021A'
PROTECTED = {}


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest() if Path(file).is_file() else None


def protect(file):
    file = Path(file)
    key = str(file)
    value = sha(file)
    if key in PROTECTED:
        assert PROTECTED[key] == value, 'Input changed during read-only diagnostic: ' + key
    else:
        PROTECTED[key] = value
    return value


def package_file(root, package):
    assert re.fullmatch(r'/Game/[A-Za-z0-9_/-]+', package) and '..' not in package
    file = root / ('Content/' + package.removeprefix('/Game/') + '.uasset')
    map_file = file.with_suffix('.umap')
    return map_file if not file.exists() and map_file.exists() else file


def module_readback():
    file = WORK / 'Binaries/Win64/UnrealEditor.modules'
    manifest = json.loads(file.read_text(encoding='utf-8-sig'))
    name = manifest['Modules']['Khazan']
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint
    handle = kernel.GetModuleHandleW(name)
    assert handle
    buffer = ctypes.create_unicode_buffer(32768)
    assert kernel.GetModuleFileNameW(handle, buffer, len(buffer))
    actual = Path(buffer.value).resolve()
    assert actual == (WORK / 'Binaries/Win64' / name).resolve()
    return {'path': str(actual), 'name': name, 'sha256': protect(actual),
        'manifest_sha256': protect(file), 'build_id': manifest['BuildId']}


def readonly_getters():
    namespace = {'unreal': unreal, 're': re}
    for file, names in [(MAIN / 'Scripts/Art/player_attack_vfx_author.py', {'guid'}),
            (MAIN / 'Scripts/Art/monster_vfx_author_20261008.py', {'encode', 'data_fields'})]:
        protect(file)
        tree = ast.parse(file.read_text(encoding='utf-8-sig'))
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in functions} == names
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(file), 'exec'), namespace)
    return namespace


def main_event(author):
    expected = next(e for e in author['events'] if e['event_id'] == EVENT)
    assert expected['guid'] == GUID
    source_file = package_file(WORK, expected['asset'])
    protect(source_file)
    particle_package = expected['effect_fields']['ParticleTemplate'].split('.')[0]
    protect(package_file(MAIN, particle_package))
    protect(package_file(PRIVATE, particle_package))
    getters = readonly_getters()
    sequence = unreal.load_asset(expected['asset'])
    assert isinstance(sequence, unreal.AnimSequence)
    events = [e for e in unreal.AnimationLibrary.get_animation_notify_events(sequence)
        if getters['guid'](e.export_text()) == GUID]
    assert len(events) == 1
    state = events[0].get_editor_property('notify_state_class')
    assert state and state.get_class().get_path_name() == '/Script/Khazan.KZAnimNotifyState_MonsterVisual'
    effect = state.get_editor_property('Effect')
    assert effect and str(effect.get_editor_property('EventId')) == EVENT
    actual = getters['data_fields'](effect, expected['effect_fields'])
    wanted = expected['effect_readback']
    difference = {key: {'expected': wanted.get(key), 'actual': actual.get(key)}
        for key in wanted if wanted.get(key) != actual.get(key)}
    return {'event_id': EVENT, 'guid': GUID, 'asset': expected['asset'],
        'asset_sha256': protect(source_file), 'effect_path': effect.get_path_name(),
        'source_package': expected['effect_fields']['SourcePackage'],
        'source_field': expected['effect_fields']['SourceField'],
        'expected_effect_readback': wanted, 'actual_effect_readback': actual,
        'field_difference': difference, 'all_effect_fields_match': not difference,
        'notify_event_export_text': events[0].export_text(),
        'effect_export_text': effect.export_text() if hasattr(effect, 'export_text') else None,
        'particle_main_exists': package_file(MAIN, particle_package).is_file(),
        'particle_private_exists': package_file(PRIVATE, particle_package).is_file()}


def native_references(value):
    if isinstance(value, str):
        return set(re.findall(r'/Game/[A-Za-z0-9_/-]+', value))
    if isinstance(value, dict):
        return set().union(*(native_references(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(native_references(v) for v in value))
    return set()


def package_row(package, roots):
    private_file = package_file(PRIVATE, package)
    main_file = package_file(MAIN, package)
    return {'package': package, 'relative': str(private_file.relative_to(PRIVATE)).replace('\\', '/'),
        'private_sha256': protect(private_file), 'main_sha256': protect(main_file),
        'is_root': package in roots}


def private_closure(author):
    roots = set().union(*(native_references(e['effect_fields']) for e in author['events']))
    roots |= native_references(author['death_presentations'])
    assert len(roots) == 316, 'Immutable consumer root contract changed'
    missing = sorted(p for p in roots if not package_file(MAIN, p).is_file())
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    assert callable(getattr(registry, 'get_dependencies', None))
    assert callable(getattr(registry, 'scan_files_synchronous', None))
    options = {}
    for kind in ('hard', 'soft'):
        opts = unreal.AssetRegistryDependencyOptions()
        for key, value in {'include_hard_package_references': kind == 'hard',
                'include_soft_package_references': kind == 'soft', 'include_searchable_names': False,
                'include_hard_management_references': False, 'include_soft_management_references': False}.items():
            opts.set_editor_property(key, value)
        options[kind] = opts
    queue = list(missing)
    visited, external, rows, edges = set(), set(), [], []
    while queue:
        package = queue.pop(0)
        if package in visited:
            continue
        visited.add(package)
        row = package_row(package, missing)
        assert row['private_sha256'] is not None, 'Missing private dependency: ' + package
        registry.scan_files_synchronous([str(package_file(PRIVATE, package))], False)
        edge = {'package': package}
        for kind, opts in options.items():
            deps = sorted(str(p) for p in registry.get_dependencies(package, opts))
            edge[kind] = deps
            for dependency in deps:
                if dependency.startswith('/Game/'):
                    if dependency not in visited:
                        queue.append(dependency)
                else:
                    external.add(dependency)
        rows.append(row)
        edges.append(edge)
    return {'source_author': {'path': str(AUTHOR_FILE), 'sha256': AUTHOR_SHA},
        'referenced_root_count': len(roots), 'referenced_roots': sorted(roots),
        'root_derivation': 'Immutable author events[].effect_fields and death_presentations only; no Plan original/source-reference aliases.',
        'missing_referenced_roots': [package_row(p, missing) for p in missing],
        'start_packages': missing, 'packages': sorted(rows, key=lambda r: r['package']),
        'edges': sorted(edges, key=lambda r: r['package']),
        'external_engine_script_packages': sorted(external),
        'dependency_options': {kind: opts.export_text() for kind, opts in options.items()},
        'api_source': 'UE5.8 AssetRegistry/IAssetRegistry.h FAssetRegistryDependencyOptions/GetDependencies/ScanFilesSynchronous',
        'boundary': 'Only absent native consumer roots and their actual package hard/soft closure are scanned; no whole-project scan or package writes.'}


report = {'schema': 'Khazan.MonsterVFX.TargetedDependencyReadback.v1', 'status': 'running',
    'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'pid': os.getpid(), 'project': str(WORK),
    'mode': 'main_exact_event' if VERIFY_MAIN else 'private_missing_reference_closure',
    'package_saves': 0, 'asset_mutations': 0, 'source_writes': 0, 'compile_api_calls': 0,
    'statistics_api_calls': 0, 'warmup_api_calls': 0, 'simulation_calls': 0,
    'overall_visual_pass': False, 'boundary': 'Diagnostic evidence only; original MainSaved failure and original968 delivery remain untouched.'}
try:
    assert protect(AUTHOR_FILE) == AUTHOR_SHA
    report['source_author'] = {'path': str(AUTHOR_FILE), 'sha256': AUTHOR_SHA}
    report['script_sha256'] = protect(Path(__file__))
    report['loaded_native_module'] = module_readback()
    author = json.loads(AUTHOR_FILE.read_text(encoding='utf-8-sig'))
    if VERIFY_MAIN:
        report['exact_event'] = main_event(author)
    else:
        report['closure'] = private_closure(author)
    report['status'] = 'passed'
except Exception:
    report.update(status='failed', error=traceback.format_exc())
    unreal.log_error(report['error'])
report['protected_sha_before'] = PROTECTED
report['protected_sha_after'] = {file: sha(file) for file in PROTECTED}
report['all_source_assets_sha_unchanged'] = report['protected_sha_after'] == PROTECTED
if not report['all_source_assets_sha_unchanged']:
    report.update(status='failed', error='Read-only input asset bytes changed')
(OUT / 'Readback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('KZ_MONSTER_VFX_TARGETED_DEPENDENCY_' + report['status'].upper(), flush=True)
