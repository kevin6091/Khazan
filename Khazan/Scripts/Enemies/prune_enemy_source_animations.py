"""Back up, delete, and verify the reviewed Enemy backing-source subset.

Standalone: main('backup'). UE Python: delete_sources() / verify_saved_assets().
This deliberately retains source-only motions and original direct consumers.
"""
import collections
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess

PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / 'Saved/ImportReports'
PLAN = REPORTS / 'HeinMachEnemy_AnimationPruning_Metadata_20260909.json'
BASELINE = REPORTS / 'HeinMachEnemy_AnimationPruning_Backup_20260909.json'
EXECUTION = REPORTS / 'HeinMachEnemy_AnimationPruning_Execution_20260909.json'
AUDIT = REPORTS / 'HeinMachEnemy_AnimationPruning_Audit_20260909.json'
INITIAL = REPORTS / 'HeinMachEnemy_PlaybackOnly_InitialScan_20260909.json'
ROOT = '/Game/_Art/Enemies'
META = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset_file(package, asset_class='AnimSequence'):
    assert package.startswith(ROOT + '/')
    path = PROJECT / (package.replace('/Game/', 'Content/') + ('.umap' if asset_class == 'World' else '.uasset'))
    assert path.resolve().is_relative_to((PROJECT / 'Content/_Art/Enemies').resolve())
    return path


def registry():
    import unreal
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.search_all_assets(True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True, include_searchable_names=False,
        include_soft_management_references=True, include_hard_management_references=True)
    return reg, options


def backup():
    plan = read(PLAN)
    assert plan['status'] == 'planned'
    scan = read(INITIAL)
    candidates = {r['asset'] for r in plan['sources'] if r['decision'] == 'DeleteBackingSource'}
    destination = pathlib.Path.home() / 'Desktop/카잔/EnemyExtracts/AnimationPruning_20260909'
    assert not BASELINE.exists() and not (destination / 'BackupManifest.json').exists(), 'Never overwrite an existing baseline'
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for package, kind in sorted(scan['assets'].items()):
        path = asset_file(package, kind)
        row = {'asset': package, 'class': kind, 'file': path.relative_to(PROJECT).as_posix(),
            'sha256': sha(path), 'bytes': path.stat().st_size, 'delete': package in candidates}
        if row['delete']:
            assert kind == 'AnimSequence' and '/SourceSequences/A_EN_SRC_' in package
            assert not scan['source_refs'][package]
            target = destination / row['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            assert sha(target) == row['sha256']
        rows.append(row)
    own_docs = {'Docs/Art/ART_PROJECT_STATE.md', 'Docs/Art/ART_KNOWLEDGE_INDEX.md',
        'Docs/Art/ART_WORK_CONTINUITY.md', 'Docs/Art/ART_PIPELINE_RULES.md',
        'Docs/Art/ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md'}
    names = subprocess.check_output(['git', 'ls-files', '-m', '-o', '--exclude-standard', '-z', '--', '.'], cwd=PROJECT).decode('utf-8').split('\0')
    names += [p.relative_to(PROJECT).as_posix() for p in (PROJECT / 'Config').glob('*.ini')]
    names += ['Content/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment.umap',
        'Content/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment.umap']
    protected = {}
    for name in sorted(set(names)):
        if name in own_docs or name.startswith(('Content/_Art/Enemies/', 'Scripts/Enemies/')):
            continue
        path = PROJECT / name
        if path.is_file():
            protected[name] = sha(path)
    result = {'status': 'backed_up', 'date': datetime.datetime.now().astimezone().isoformat(),
        'backup': str(destination), 'plan_sha256': sha(PLAN), 'initial_scan_sha256': sha(INITIAL),
        'assets': rows, 'protected_worktree_files': protected,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT).decode().strip()}
    write(BASELINE, result)
    write(destination / 'BackupManifest.json', result)
    shutil.copy2(PLAN, destination / PLAN.name)
    print('BACKUP_VERIFIED', len(candidates), 'candidates;', len(rows) - len(candidates), 'retained;', len(protected), 'protected')


def check_baseline():
    baseline = read(BASELINE)
    assert sha(PLAN) == baseline['plan_sha256']
    assert sha(INITIAL) == baseline['initial_scan_sha256']
    for row in baseline['assets']:
        path = PROJECT / row['file']
        if row['delete']:
            assert sha(pathlib.Path(baseline['backup']) / row['file']) == row['sha256']
            if not path.exists():
                continue  # Resuming only this exact, backed-up deletion plan.
        assert sha(path) == row['sha256'], ('Concurrent asset change', row['asset'])
    return baseline


def delete_sources():
    import unreal
    baseline = check_baseline()
    reg, options = registry()
    candidates = [r for r in baseline['assets'] if r['delete']]
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not any(p.get_name().startswith(ROOT) for p in dirty), 'Unsaved Enemy edits must be preserved'
    remaining = []
    for row in candidates:
        assert row['class'] == 'AnimSequence' and '/SourceSequences/A_EN_SRC_' in row['asset']
        assert not reg.get_referencers(row['asset'], options), ('Still referenced', row['asset'])
        if (PROJECT / row['file']).exists():
            asset = unreal.load_asset(row['asset'])
            assert isinstance(asset, unreal.AnimSequence)
            remaining.append(asset)
    # Every candidate has zero package referencers, including other candidates.
    # Only UE's asset deletion API mutates Content; no recursive file deletion.
    if remaining:
        assert unreal.EditorAssetLibrary.delete_loaded_assets(remaining), 'UE deletion failed'
    absent = [r for r in candidates if not (PROJECT / r['file']).exists()]
    assert len(absent) == len(candidates), ('Files remain', [r['asset'] for r in candidates if (PROJECT / r['file']).exists()])
    check_baseline()
    result = {'status': 'passed', 'deleted_count': len(absent), 'deleted_bytes': sum(r['bytes'] for r in absent),
        'retained_hashes_unchanged': sum(not r['delete'] for r in baseline['assets']),
        'blueprint_changes': 0, 'playback_animation_changes': 0, 'backup': baseline['backup']}
    write(EXECUTION, result)
    print('ENEMY_ANIMATION_PRUNING_PASSED', result)


def verify_saved_assets():
    """Run in a separate commandlet after deletion; writes reports only."""
    import unreal
    assert read(EXECUTION)['status'] == 'passed'
    baseline = check_baseline()
    reg, options = registry()
    assets = {str(a.package_name): a for a in reg.get_assets_by_path(ROOT, recursive=True)}
    retained = {r['asset'] for r in baseline['assets'] if not r['delete']}
    removed = {r['asset'] for r in baseline['assets'] if r['delete']}
    assert set(assets) == retained
    missing = []
    for asset in assets:
        missing += [{'asset': asset, 'dependency': str(p)} for p in reg.get_dependencies(asset, options)
            if str(p).startswith(ROOT + '/') and str(p) not in assets]
    assert not missing, missing
    assert not any(reg.get_referencers(p, options) for p in removed)
    manifest = read(META / 'Expansion_20260909/AnimationImportManifest.json')
    animations = []
    max_duration_error = 0.
    evaluated_poses = 0
    for row in manifest:
        if row['destination'] not in retained:
            continue
        seq = unreal.load_asset(row['destination'])
        assert isinstance(seq, unreal.AnimSequence)
        assert seq.get_editor_property('skeleton')
        duration_error = abs(seq.get_play_length() - row['duration'])
        # Numerical checks against the preserved import contract, not tuning.
        assert duration_error < 1e-5
        max_duration_error = max(max_duration_error, duration_error)
        assert abs(seq.get_editor_property('rate_scale') - row['rate_scale']) < 1e-6
        model = seq.controller.get_model_interface()
        rate = model.get_frame_rate()
        assert [rate.numerator, rate.denominator] == row['fps']
        assert model.get_number_of_keys() == row['samples']
        if row['kind'] == 'PlaybackClip':
            assert not any(str(p) in removed for p in reg.get_dependencies(row['destination'], options))
            for frame in sorted({0, (row['samples'] - 1) // 2, row['samples'] - 1}):
                opts = unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.COMPRESSED,
                    should_retarget=False, extract_root_motion=False, incorporate_root_motion_into_pose=True)
                pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq, frame, opts)
                assert pose.is_valid(), (row['destination'], frame)
                evaluated_poses += 1
        animations.append({'asset': row['destination'], 'kind': row['kind'], 'fps': row['fps'],
            'seconds': seq.get_play_length(), 'rate_scale': seq.get_editor_property('rate_scale')})
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert level.load_level(ROOT + '/HeinMach/Preview/L_HeinMach_EnemyCatalogue')
    actors = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        if a.get_actor_label().startswith('EN_Variant_')}
    catalogue = read(META / 'Expansion_20260909/AssemblyCatalog.json')
    assert len(actors) == len(catalogue) == 16
    blueprints = []
    for row in catalogue:
        actor = actors['EN_Variant_' + row['asset'].rsplit('/', 1)[1]]
        components = {c.get_name(): c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)}
        body = components['EnemyBody']
        assert body.get_editor_property('animation_data').anim_to_play.get_path_name().split('.')[0] == row['idle_asset']
        rotation = body.get_editor_property('relative_rotation')
        assert abs(rotation.pitch) < 1e-5 and abs(rotation.roll) < 1e-5 and abs(rotation.yaw + 90) < 1e-5
        for name, component in components.items():
            assert component.get_skinned_asset() and component.get_skinned_asset().get_editor_property('skeleton')
            assert all(component.get_material(i) for i in range(component.get_num_materials()))
            animation = component.get_editor_property('animation_data').anim_to_play
            if animation:
                assert animation.get_path_name().split('.')[0] in retained
            if name != 'EnemyBody':
                assert component.get_attach_parent() == body
            if name.startswith(('EnemyWeapon', 'EnemyShield', 'EnemyQuiver')):
                assert body.does_socket_exist(component.get_attach_socket_name())
        blueprints.append({'asset': row['asset'], 'components': len(components), 'idle_asset': row['idle_asset'], 'valid': True})
    external_changes = [name for name, value in baseline['protected_worktree_files'].items()
        if not (PROJECT / name).is_file() or sha(PROJECT / name) != value]
    result = {'status': 'passed', 'counts_after': dict(collections.Counter(str(a.asset_class_path.asset_name) for a in assets.values())),
        'removed_count': len(removed), 'retained_hashes_unchanged': len(retained),
        'playback_count': sum(r['kind'] == 'PlaybackClip' for r in animations),
        'source_count': sum(r['kind'] == 'SourceSequence' for r in animations),
        'legacy_idle_count': 3, 'missing_dependencies': missing, 'max_duration_error_seconds': max_duration_error,
        'playback_compressed_pose_samples': evaluated_poses,
        'blueprints': blueprints, 'animations': animations, 'protected_external_changes': external_changes,
        'scope': 'Fresh process, complete retained-file hashes, exact stored frame rate, duration/rate, compressed pose evaluation and catalogue components. No combat AI/Notify execution or original-game video comparison.'}
    write(AUDIT, result)
    print('ANIMATION_PRUNING_FRESH_AUDIT_PASSED', {k: v for k, v in result.items() if k not in ('blueprints', 'animations')})


def main(mode):
    if mode == 'backup':
        backup()
    elif mode == 'delete':
        delete_sources()
    elif mode == 'verify':
        verify_saved_assets()
    else:
        raise ValueError(mode)


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
