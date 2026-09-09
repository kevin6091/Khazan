"""Fresh-process audit for the unified Enemy playback animation structure."""
import collections
import hashlib
import json
import pathlib
import sys

import unreal

PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORTS = PROJECT / 'Saved/ImportReports'
PLAN = json.loads((REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json').read_text(encoding='utf-8-sig'))
BACKUP = json.loads((REPORTS / 'HeinMachEnemy_AnimationStructureBackup_20260909.json').read_text(encoding='utf-8-sig'))
EXECUTION = json.loads((REPORTS / 'HeinMachEnemy_AnimationStructureExecution_20260909.json').read_text(encoding='utf-8-sig'))
REPORT = REPORTS / 'HeinMachEnemy_AnimationStructureAudit_20260909.json'
ROOT = '/Game/_Art/Enemies'
VERSION = '20260909_PlaybackUnifiedV1'
sys.path.insert(0, str(PROJECT / 'Saved/ArtTools/EnemyPython'))
import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_path(value):
    return value.get_path_name().split('.')[0] if value else None


def maximum_pose_error(sequence, manifest):
    data = np.load(manifest['data_file'], mmap_mode='r')
    assert data.shape == (manifest['samples'], len(manifest['bones']), 10)
    maximum = np.zeros(3)
    evaluated = 0
    for mode in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
        options = unreal.AnimPoseEvaluationOptions(evaluation_type=mode, should_retarget=False,
            extract_root_motion=False, incorporate_root_motion_into_pose=True)
        for frame in sorted({0, (manifest['samples'] - 1) // 2, manifest['samples'] - 1}):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(sequence, frame, options)
            assert pose.is_valid(), (sequence.get_path_name(), frame, str(mode))
            for index, bone in enumerate(manifest['bones']):
                actual = pose.get_bone_pose(bone, unreal.AnimPoseSpaces.LOCAL)
                expected = data[frame, index]
                p = [actual.translation.x, actual.translation.y, actual.translation.z]
                q = [actual.rotation.x, actual.rotation.y, actual.rotation.z, actual.rotation.w]
                s = [actual.scale3d.x, actual.scale3d.y, actual.scale3d.z]
                error = [
                    max(abs(a - b) for a, b in zip(p, expected[:3])),
                    min(max(abs(a - b) for a, b in zip(q, expected[3:7])),
                        max(abs(a + b) for a, b in zip(q, expected[3:7]))),
                    max(abs(a - b) for a, b in zip(s, expected[7:])),
                ]
                maximum = np.maximum(maximum, error)
            evaluated += 1
    # Existing importer validation tolerances, not gameplay values.
    assert maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001, (sequence.get_path_name(), maximum.tolist())
    return maximum.tolist(), evaluated


def current_blueprint_components(remap):
    baseline = read(PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/Cleanup_20260909/BlueprintComponents.json')
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    rows = []
    for expected_bp in baseline:
        blueprint = unreal.load_asset(expected_bp['asset'])
        assert blueprint
        actual = {}
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(blueprint):
            component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
            if not isinstance(component, unreal.SkeletalMeshComponent):
                continue
            animation_data = component.get_editor_property('animation_data')
            rotation = component.get_editor_property('relative_rotation')
            scale = component.get_editor_property('relative_scale3d')
            actual[component.get_name()] = {
                'mesh': component.get_skinned_asset().get_path_name() if component.get_skinned_asset() else None,
                'animation': animation_data.anim_to_play.get_path_name() if animation_data.anim_to_play else None,
                'play_rate': animation_data.saved_play_rate,
                'looping': animation_data.saved_looping,
                'collision': str(component.get_collision_enabled()),
                'rotation': {'pitch': rotation.pitch, 'yaw': rotation.yaw, 'roll': rotation.roll},
                'scale': {'x': scale.x, 'y': scale.y, 'z': scale.z},
            }
        expected = expected_bp['components']
        assert set(actual) == set(expected), expected_bp['asset']
        for name, before in expected.items():
            after = actual[name]
            expected_animation = before['animation']
            if expected_animation:
                old_package = expected_animation.split('.')[0]
                new_package = remap.get(old_package, old_package)
                expected_animation = new_package + '.' + new_package.rsplit('/', 1)[1]
            assert after['mesh'] == before['mesh']
            assert after['animation'] == expected_animation, (expected_bp['asset'], name, after['animation'], expected_animation)
            assert after['play_rate'] == before['play_rate'] and after['looping'] == before['looping']
            assert after['collision'] == before['collision']
            for axis, value in before['rotation'].items():
                assert abs(after['rotation'][axis] - value) < 1e-6
            for axis, value in before['scale'].items():
                assert abs(after['scale'][axis] - value) < 1e-6
        rows.append({'asset': expected_bp['asset'], 'family': expected_bp['family'], 'components': actual})
    return rows


def main():
    assert PLAN['status'] == 'planned' and EXECUTION['status'] == 'passed'
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True, include_searchable_names=False,
        include_soft_management_references=True, include_hard_management_references=True)
    assets = {str(a.package_name): a for a in registry.get_assets_by_path(ROOT, recursive=True)}
    previous = read(PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationPruning_20260909/RetainedAssets.json')
    non_animation = {row['asset'] for row in previous['assets'] if row['class'] != 'AnimSequence'}
    expected = non_animation | {row['new_asset'] for row in PLAN['renames']}
    assert set(assets) == expected, {'missing': sorted(expected - set(assets)), 'unexpected': sorted(set(assets) - expected)}
    assert not any(str(a.asset_class_path.asset_name) == 'ObjectRedirector' for a in assets.values())
    animations = {path: data for path, data in assets.items() if str(data.asset_class_path.asset_name) == 'AnimSequence'}
    assert len(animations) == 884
    assert all(path.rsplit('/', 1)[1].startswith('A_EN_PLAY_') for path in animations)
    assert all('/Animations/Playback/' in path for path in animations)
    assert not any(fragment in path for path in animations for fragment in ('/SourceSequences/', '/PlaybackClips/', 'SourceReferences/'))
    for row in PLAN['renames'] + PLAN['legacy_duplicates']:
        assert row['old_asset'] not in assets
        assert not (PROJECT / (row['old_asset'].replace('/Game/', 'Content/') + '.uasset')).exists()
        assert not registry.get_referencers(row['old_asset'], options)
    manifest = read(PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AnimationImportManifest.json')
    manifest_by_old = {row['destination']: row for row in manifest}
    maximum = np.zeros(3)
    duration_error = 0.0
    evaluated_poses = 0
    sequence_rows = []
    for row in PLAN['renames']:
        sequence = unreal.load_asset(row['new_asset'])
        assert isinstance(sequence, unreal.AnimSequence)
        model = sequence.controller.get_model_interface()
        rate = model.get_frame_rate()
        contract = row['contract']
        assert model.get_number_of_keys() == contract['samples'] and model.get_number_of_frames() == contract['frames']
        assert [rate.numerator, rate.denominator] == contract['fps']
        duration_error = max(duration_error, abs(sequence.get_play_length() - contract['seconds']))
        assert abs(sequence.get_editor_property('rate_scale') - contract['rate_scale']) < 1e-6
        assert sequence.get_editor_property('enable_root_motion') == contract['enable_root_motion']
        assert sequence.get_editor_property('force_root_lock') == contract['force_root_lock']
        assert str(sequence.get_editor_property('root_motion_root_lock')) == contract['root_motion_root_lock']
        assert package_path(sequence.get_editor_property('skeleton')) == contract['skeleton']
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'EnemyArtRole') == 'PlaybackSequence'
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'PreviousEnemyArtRole') == row['previous_role']
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'PlaybackDerivation') == row['playback_derivation']
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'CanonicalAnimationStructureVersion') == VERSION
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'CanonicalPlaybackPath') == row['new_asset']
        assert unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'OriginalPackage') == row['original_package']
        pose_error, pose_count = maximum_pose_error(sequence, manifest_by_old[row['old_asset']])
        maximum = np.maximum(maximum, pose_error)
        evaluated_poses += pose_count
        sequence_rows.append({'asset': row['new_asset'], 'family': row['family'],
            'playback_derivation': row['playback_derivation'], 'fps': contract['fps'],
            'samples': contract['samples'], 'seconds': sequence.get_play_length(), 'rate_scale': contract['rate_scale']})
    assert duration_error < 1e-5
    changed_files = {row['file'] for row in BACKUP['changed_assets']}
    unchanged_files = 0
    for relative, value in BACKUP['retained_assets'].items():
        if relative in changed_files:
            continue
        path = PROJECT / relative
        assert path.is_file() and sha(path) == value, ('Unrelated Enemy asset changed', relative)
        unchanged_files += 1
    remap = {row['old_asset']: row['new_asset'] for row in PLAN['renames']}
    blueprints = current_blueprint_components(remap)
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert level.load_level(ROOT + '/HeinMach/Preview/L_HeinMach_EnemyCatalogue')
    catalogue_actors = [actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        if actor.get_actor_label().startswith('EN_Variant_')]
    assert len(catalogue_actors) == 16
    for actor in catalogue_actors:
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            animation = component.get_editor_property('animation_data').anim_to_play
            if animation:
                assert package_path(animation) in animations
    external_changes = []
    for relative, value in BACKUP['protected_worktree_files'].items():
        path = PROJECT / relative
        current = sha(path) if path.is_file() else None
        if current != value:
            external_changes.append({'file': relative, 'before': value, 'after': current})
    missing = []
    for path in assets:
        missing += [{'asset': path, 'dependency': str(dep)} for dep in registry.get_dependencies(path, options)
            if str(dep).startswith(ROOT + '/') and str(dep) not in assets]
    assert not missing, missing
    counts = dict(collections.Counter(str(a.asset_class_path.asset_name) for a in assets.values()))
    result = {
        'status': 'passed',
        'structure_version': VERSION,
        'counts_after': counts,
        'animation_count': len(animations),
        'all_names_use_A_EN_PLAY': True,
        'all_animation_folders_use_Animations_Playback': True,
        'folder_counts': dict(collections.Counter(path.rsplit('/', 1)[0] for path in animations)),
        'derivation_counts': dict(collections.Counter(row['playback_derivation'] for row in PLAN['renames'])),
        'legacy_duplicates_removed': len(PLAN['legacy_duplicates']),
        'redirectors': 0,
        'missing_enemy_dependencies': missing,
        'unchanged_non_affected_enemy_file_hashes': unchanged_files,
        'blueprints': blueprints,
        'catalogue_actor_count': len(catalogue_actors),
        'max_duration_error_seconds': duration_error,
        'maximum_pose_errors_position_cm_quaternion_component_scale': maximum.tolist(),
        'raw_and_compressed_pose_evaluations': evaluated_poses,
        'sequences': sequence_rows,
        'protected_external_changes': external_changes,
        'scope': 'Fresh registry, exact inventory/name/folder/metadata/numeric contracts, source-data RAW+COMPRESSED sample poses, BP templates and catalogue actors. No gameplay AI/Notify execution or original-game video comparison.',
    }
    write(REPORT, result)
    print('ENEMY_ANIMATION_STRUCTURE_AUDIT_PASSED', json.dumps({k: v for k, v in result.items()
        if k not in ('blueprints', 'sequences')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
