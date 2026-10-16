"""Guarded approved cloth PA snapshot/handoff; never close/save/compile/start PIE.

Preparation only until explicitly executed in the Main editor:
    exec(compile(Path(__file__).read_text(), __file__, 'exec'),
         {'cloth_action': 'snapshot', 'expected_pid': 3528})
After final isolated verification, execute the same file with cloth_action='handoff'.
The handoff holds one GameThread Python call across loader release, existing CAS
delivery and noninteractive reload. Offline '--check' only verifies disk guards.
Optional globals cloth_report_directory, cloth_targets, cloth_motion_parts and
cloth_required_validation_fields narrow the existing defaults. expected_world
must still match the caller's current Main world.
Optional expected_dirty_content permits only the exact unrelated live Montage
packages. Their package/asset identities and direct preview references are kept.
Registry-confirmed referencers are a limited dependency check, not an exhaustive
proof of unsaved references. Engine reload may PostEditChange/compile referencers;
this script never explicitly compiles, saves, or discards any package.
"""
from pathlib import Path
import configparser
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import math
import os
import runpy
import sys

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
REPORT = Path(globals().get('cloth_report_directory',
                          ROOT / 'Metadata/PlayerParts_20261007/ClothRefinement')).resolve()
assert REPORT.is_relative_to(ROOT / 'Metadata') and REPORT != ROOT / 'Metadata', 'Report must remain under Main Metadata'
WORK = ROOT.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
APPROVED_TARGETS = tuple('Content/_Art/Player/Character/Meshs/' + part +
                        '/Player_Original_' + part + '_RigidBody_PhysicsAsset.uasset'
                        for part in ('Torso', 'Leg'))
TARGETS = tuple(globals().get('cloth_targets', APPROVED_TARGETS))
assert TARGETS and len(TARGETS) == len(set(TARGETS)) and set(TARGETS).issubset(APPROVED_TARGETS), 'Only approved Torso/Leg PAs may be handed off'
MOTION_PARTS = tuple(globals().get('cloth_motion_parts', ('Torso', 'Leg')))
assert MOTION_PARTS and len(MOTION_PARTS) == len(set(MOTION_PARTS))
assert set(MOTION_PARTS) == {Path(relative).parent.name for relative in TARGETS}, 'Motion QA must cover the selected parts'
DEFAULT_VALIDATION_FIELDS = ('native_pie_passed', 'native_saved_reload_passed',
                             'stock_saved_reload_passed', 'guard_passed', 'heal_passed')
REQUIRED_VALIDATION_FIELDS = tuple(globals().get('cloth_required_validation_fields', DEFAULT_VALIDATION_FIELDS))
assert len(REQUIRED_VALIDATION_FIELDS) == len(set(REQUIRED_VALIDATION_FIELDS))
assert set(DEFAULT_VALIDATION_FIELDS[:3]).issubset(REQUIRED_VALIDATION_FIELDS)
assert set(REQUIRED_VALIDATION_FIELDS).issubset(DEFAULT_VALIDATION_FIELDS), 'Unknown cloth validation fields'
WORLD = '/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment'
EXPECTED_DIRTY_CONTENT = tuple(globals().get('expected_dirty_content', ()))
assert len(EXPECTED_DIRTY_CONTENT) == len(set(EXPECTED_DIRTY_CONTENT))
assert all(isinstance(name, str) and name.startswith('/Game/') and '.' not in name
           for name in EXPECTED_DIRTY_CONTENT), 'Expected dirty entries must be exact package names'
TARGET_PACKAGES = tuple('/Game/' + relative.removeprefix('Content/').removesuffix('.uasset')
                        for relative in TARGETS)
assert not set(EXPECTED_DIRTY_CONTENT).intersection(TARGET_PACKAGES), 'Dirty targets are never allowed'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(name):
    return json.loads((REPORT / name).read_text(encoding='utf-8-sig'))


def write(name, data):
    destination = REPORT / name
    if destination.exists():
        history = REPORT / 'MainSelectiveHistory'
        history.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (history / (timestamp + '_' + name)).write_bytes(destination.read_bytes())
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(destination)


def candidate():
    data = read('CandidateManifest.json')
    assert len(data['packages']) == len(TARGETS)
    assert {entry['path'] for entry in data['packages']} == set(TARGETS)
    before_entries = read('BeforeManifest.json')
    assert len(before_entries) == len(TARGETS) and {entry['path'] for entry in before_entries} == set(TARGETS)
    before = {entry['path']: entry['beforeSha256'] for entry in before_entries}
    for entry in data['packages']:
        assert entry['beforeSha256'] == before[entry['path']]
        assert digest(WORK / entry['path']) == entry['preparedSha256']
    return data


def loaded_main_modules():
    """Inspect only this process's project DLLs; no external process control."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                        wintypes.LPWSTR, wintypes.DWORD]
    handles = (wintypes.HMODULE * 4096)()
    needed = wintypes.DWORD()
    process = kernel.GetCurrentProcess()
    assert psapi.EnumProcessModulesEx(process, handles, ctypes.sizeof(handles), ctypes.byref(needed), 3)
    assert needed.value <= ctypes.sizeof(handles)
    paths = set()
    for handle in handles[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        buffer = ctypes.create_unicode_buffer(32768)
        assert psapi.GetModuleFileNameExW(process, handle, buffer, len(buffer))
        path = Path(buffer.value).resolve()
        if path.is_relative_to(ROOT / 'Binaries/Win64') and path.name.lower().startswith('unrealeditor-khazan') and path.suffix.lower() == '.dll':
            paths.add(path.relative_to(ROOT).as_posix())
    assert paths, 'No Main project DLL loaded in this process'
    return sorted(paths)


def protected_paths(world, loaded):
    paths = {path.relative_to(ROOT).as_posix()
             for folder in ('Source', 'Config', 'Content/_Art/Player/Character')
             for path in (ROOT / folder).rglob('*') if path.is_file()}
    paths.difference_update(TARGETS)
    for target in TARGETS:
        paths.discard(target + '.clothrefinement_pending')
    paths.add('Khazan.uproject')
    package = world.split('.', 1)[0]
    assert package.startswith('/Game/')
    paths.add('Content/' + package.removeprefix('/Game/') + '.umap')
    for name in EXPECTED_DIRTY_CONTENT:
        paths.add('Content/' + name.removeprefix('/Game/') + '.uasset')
    paths.add('Binaries/Win64/UnrealEditor.modules')
    modules = json.loads((ROOT / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
    active = (ROOT / 'Binaries/Win64' / modules['Modules']['Khazan']).resolve()
    assert active.is_relative_to(ROOT / 'Binaries/Win64') and active.is_file()
    paths.add(active.relative_to(ROOT).as_posix())
    paths.update(loaded)
    return sorted(paths)


def check_protected(snapshot):
    expected = {entry['path']: entry['sha256'] for entry in snapshot['protected']}
    assert set(protected_paths(snapshot['world'], snapshot['loaded_project_modules'])) == set(expected), 'Protected inventory changed'
    changed = [path for path, sha in expected.items()
               if not (ROOT / path).is_file() or digest(ROOT / path) != sha]
    assert not changed, ('Concurrent protected changes; take a fresh snapshot', changed)


def check_disk(snapshot, delivered=False):
    manifest = candidate()
    assert digest(REPORT / 'CandidateManifest.json') == snapshot['candidate_manifest_sha256'], 'Candidate changed after snapshot'
    for entry in manifest['packages']:
        wanted = entry['preparedSha256'] if delivered else entry['beforeSha256']
        assert digest(ROOT / entry['path']) == wanted, ('Main target changed', entry['path'])
    check_protected(snapshot)
    return manifest


def check_verified():
    verification = read('Verification.json')
    for field in REQUIRED_VALIDATION_FIELDS:
        assert verification.get(field) is True, ('Isolated validation incomplete', field)
    assert verification['hair_motion']['independentlyRespondingJoints'] == 65
    assert verification['hair_motion']['bendPeakDegrees'] < 35
    for part in MOTION_PARTS:
        assert verification['motion'][part]['after']['bendPeakDegrees'] < 45
    manifest = candidate()
    assert datetime.datetime.fromisoformat(verification['utc']) >= datetime.datetime.fromisoformat(manifest['utc']), 'Verification predates candidate'
    return digest(REPORT / 'Verification.json')


if '--check' in sys.argv:
    snapshot = read('MainSelectiveSnapshot.json')
    check_disk(snapshot)
    check_verified()
    print('Disk CAS/protected/candidate/isolated verification guards passed; no Main action.')
else:
    import unreal
    action = globals().get('cloth_action', 'snapshot')
    expected_pid = globals().get('expected_pid', 3528)
    expected_world = globals().get('expected_world', WORLD)
    assert action in ('snapshot', 'handoff')
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    assert os.getpid() == expected_pid, ('Wrong editor PID', os.getpid(), expected_pid)
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    dirty_identities = {}
    dirty_records = []

    def reference_name(value):
        if value is None:
            return None
        return value.get_path_name() if hasattr(value, 'get_path_name') else str(value)

    def check_dirty_content():
        current = {package.get_name(): package for package in
                   unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        assert set(current) == set(EXPECTED_DIRTY_CONTENT), ('Dirty content changed; preserve it', sorted(current))
        for name, package in sorted(current.items()):
            assert name not in TARGET_PACKAGES
            object_path = name + '.' + name.rsplit('/', 1)[1]
            asset = unreal.find_object(None, object_path, follow_redirectors=False)
            assert isinstance(asset, unreal.AnimMontage), ('Only unrelated dirty Montages are supported', name)
            assert asset.get_outermost() == package
            skeleton = asset.get_editor_property('skeleton')
            preview = asset.get_editor_property('preview_skeletal_mesh')
            references = (reference_name(skeleton), reference_name(preview))
            for obj in (skeleton, preview):
                if isinstance(obj, unreal.Object):
                    assert obj.get_outermost().get_name() not in TARGET_PACKAGES, ('Dirty preview references target', name)
                if isinstance(obj, unreal.SkeletalMesh):
                    physics = obj.get_editor_property('physics_asset')
                    assert not physics or physics.get_outermost().get_name() not in TARGET_PACKAGES, ('Dirty preview mesh uses target PA', name)
            if name not in dirty_identities:
                dirty_identities[name] = (package, asset, skeleton, preview)
                dirty_records.append(dict(package=name, asset=object_path, class_name=asset.get_class().get_name(),
                                          skeleton=references[0], preview_skeletal_mesh=references[1]))
            else:
                previous = dirty_identities[name]
                assert package == previous[0] and asset == previous[1], ('Dirty package/asset identity changed', name)
                assert skeleton == previous[2] and preview == previous[3], ('Dirty montage preview references changed', name)
        return current

    def clean_world():
        assert editor.get_game_world() is None, 'PIE is active'
        check_dirty_content()
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Dirty map; preserve it'
        world = editor.get_editor_world()
        assert world and world.get_path_name() == expected_world, ('Editor world changed', world)
        return world

    world = clean_world()
    manifest = candidate()
    packages = []
    for relative in TARGETS:
        asset_path = '/Game/' + relative.removeprefix('Content/').removesuffix('.uasset')
        asset = unreal.load_asset(asset_path)
        assert isinstance(asset, unreal.PhysicsAsset)
        package = asset.get_outermost()
        assert package.get_name() == asset_path
        assert package != world.get_outermost(), 'Never reload the current map'
        packages.append(package)
    clean_world()
    dirty_reference_checks = []
    if EXPECTED_DIRTY_CONTENT:
        assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        assert callable(assets.find_package_referencers_for_asset), 'Cannot confirm dirty-package independence'
        for asset_path in TARGET_PACKAGES:
            object_path = asset_path + '.' + asset_path.rsplit('/', 1)[1]
            registered = {str(name) for name in assets.find_package_referencers_for_asset(object_path, load_assets_to_confirm=False)}
            assert not set(EXPECTED_DIRTY_CONTENT).intersection(registered), ('Dirty package is a registered PA referencer', asset_path)
            confirmed = {str(name) for name in assets.find_package_referencers_for_asset(object_path, load_assets_to_confirm=True)}
            assert not set(EXPECTED_DIRTY_CONTENT).intersection(registered | confirmed), ('Dirty package references selected PA', asset_path)
            dirty_reference_checks.append(dict(target=asset_path, registered=sorted(registered), confirmed_loaded=sorted(confirmed)))
        clean_world()
    assert callable(unreal.EditorLoadingAndSavingUtils.fully_load_packages)
    assert callable(unreal.EditorLoadingAndSavingUtils.reload_packages)
    assert hasattr(unreal.ReloadPackagesInteractionMode, 'ASSUME_NEGATIVE')

    if action == 'snapshot':
        loaded = loaded_main_modules()
        protected = [dict(path=path, sha256=digest(ROOT / path))
                     for path in protected_paths(expected_world, loaded)]
        snapshot = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        pid=os.getpid(), project=str(ROOT), world=expected_world,
                        candidate_manifest_sha256=digest(REPORT / 'CandidateManifest.json'),
                        loaded_project_modules=loaded, protected=protected,
                        reload_api_doc=unreal.EditorLoadingAndSavingUtils.reload_packages.__doc__,
                        fully_load_api_doc=unreal.EditorLoadingAndSavingUtils.fully_load_packages.__doc__,
                        dirty_content=len(EXPECTED_DIRTY_CONTENT), dirty_content_names=sorted(EXPECTED_DIRTY_CONTENT),
                        preserved_dirty_assets=dirty_records, dirty_reference_checks=dirty_reference_checks,
                        dirty_reference_check_limit='Registry candidates plus loaded confirmation; unsaved unregistered references are not exhaustively enumerated.',
                        dirty_map=0, game_world=False)
        check_disk(snapshot)
        clean_world()
        write('MainSelectiveSnapshot.json', snapshot)
        print('Main selective cloth PA read-only snapshot prepared:', os.getpid(), len(protected))
    else:
        result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pid=os.getpid(),
                      project=str(ROOT), world=expected_world, success=False,
                      save_or_compile_or_pie=False, main_close=False, packages_reload_requested=list(TARGETS))
        selected = actors.get_selected_level_actors()
        selected_paths = {actor.get_path_name() for actor in selected}
        actor_identities = {actor.get_path_name(): actor for actor in actors.get_all_level_actors()}
        actor_paths = set(actor_identities)
        try:
            snapshot = read('MainSelectiveSnapshot.json')
            assert snapshot['pid'] == os.getpid() and snapshot['world'] == expected_world
            assert snapshot.get('dirty_content_names', []) == sorted(EXPECTED_DIRTY_CONTENT), 'Snapshot dirty scope changed'
            assert snapshot.get('preserved_dirty_assets', []) == dirty_records, 'Snapshot dirty preview references changed'
            assert snapshot['loaded_project_modules'] == loaded_main_modules()
            check_disk(snapshot)
            verified_sha = check_verified()
            clean_world()
            # Engine fully_load_packages flushes only these packages and ResetLoaders
            # for them, releasing their disk handles without reloading/closing the map.
            unreal.EditorLoadingAndSavingUtils.fully_load_packages(packages)
            result['loaders_released'] = True
            assert clean_world() == world
            check_disk(snapshot)
            assert digest(REPORT / 'Verification.json') == verified_sha
            original_argv = sys.argv
            try:
                delivery = ROOT / 'Scripts/Engineering/deliver_player_cloth_refinement.py'
                sys.argv = [str(delivery)]
                runpy.run_path(str(delivery), run_name='__main__',
                               init_globals={'cloth_report_directory': REPORT,
                                             'cloth_targets': TARGETS,
                                             'cloth_required_validation_fields': REQUIRED_VALIDATION_FIELDS})
            finally:
                sys.argv = original_argv
            result['disk_delivered'] = True
            check_disk(snapshot, delivered=True)
            assert clean_world() == world
            result['reload_requested'] = True
            outcome = unreal.EditorLoadingAndSavingUtils.reload_packages(
                packages, interaction_mode=unreal.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
            result['reload_return'] = str(outcome)
            assert isinstance(outcome, tuple) and len(outcome) == 2 and outcome[0] and not str(outcome[1]), ('Selective reload failed', outcome)
            assert clean_world() == world
            current_actors = actors.get_all_level_actors()
            assert {actor.get_path_name() for actor in current_actors} == actor_paths, 'Editor actors changed'
            assert all(actor == actor_identities[actor.get_path_name()] for actor in current_actors), 'Editor actor identities changed'
            actors.set_selected_level_actors([actor for actor in current_actors if actor.get_path_name() in selected_paths])
            settings = configparser.ConfigParser()
            settings.read(REPORT / 'TemporaryTuning.ini', encoding='utf-8-sig')
            result['solver_readback'] = []
            for relative in TARGETS:
                part = Path(relative).parent.name
                asset = unreal.load_asset('/Game/' + relative.removeprefix('Content/').removesuffix('.uasset'))
                solver = asset.get_editor_property('solver_settings')
                step = solver.get_editor_property('fixed_time_step')
                position = solver.get_editor_property('position_iterations')
                linear = solver.get_editor_property('use_linear_joint_solver')
                assert math.isclose(step, settings.getfloat('ClothRefinement', 'FixedTimeStepSeconds'), rel_tol=1e-6)
                assert position == settings.getint('ClothRefinement', 'PositionIterations')
                assert linear == settings.getboolean('ClothRefinement', 'UseLinearJointSolver' + part)
                result['solver_readback'].append(dict(part=part, fixed_time_step=step, position_iterations=position, linear=linear))
            check_disk(snapshot, delivered=True)
            assert clean_world() == world
            assert snapshot['loaded_project_modules'] == loaded_main_modules()
            result.update(success=True, dirty_content=len(EXPECTED_DIRTY_CONTENT),
                          dirty_content_names=sorted(EXPECTED_DIRTY_CONTENT), preserved_dirty_assets=dirty_records,
                          dirty_reference_checks=dirty_reference_checks, unrelated_dirty_identities_preserved=True,
                          dirty_reference_check_limit='Registry candidates plus loaded confirmation; unsaved unregistered references are not exhaustively enumerated.',
                          explicit_compile_or_save=False, engine_implicit_referencer_updates_possible=True,
                          dirty_map=0, game_world=False,
                          protected_unchanged=len(snapshot['protected']), selected_actors_preserved=True)
        except Exception as error:
            result['error'] = repr(error)
            raise
        finally:
            result['target_disk_sha256'] = {relative: digest(ROOT / relative) for relative in TARGETS}
            if result.get('reload_requested') and not result.get('selected_actors_preserved'):
                try:
                    if editor.get_editor_world() == world:
                        actors.set_selected_level_actors([actor for actor in actors.get_all_level_actors()
                                                         if actor.get_path_name() in selected_paths])
                        result['selected_actors_preserved'] = True
                except Exception as restore_error:
                    result['selection_restore_error'] = repr(restore_error)
            write('MainSelectiveHandoff.json', result)
            print('Main selective cloth PA handoff:', result.get('success'), os.getpid())
