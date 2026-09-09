"""Plan one canonical playback name and folder structure for retained Enemy animations.

Run inside Unreal Editor. This is read-only apart from its Saved report.
"""
import collections
import hashlib
import json
import pathlib

import unreal

PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORTS = PROJECT / 'Saved/ImportReports'
REPORT = REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json'
BACKUP = REPORTS / 'HeinMachEnemy_AnimationStructureBackup_20260909.json'
ROOT = '/Game/_Art/Enemies'
META = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909'
LEGACY = {
    '/Game/_Art/Enemies/HeinMach/Empire/Animation/A_EN_Sword_Idle':
        '/Game/_Art/Enemies/HeinMach/Humanoids/Swordsman/Animations/SourceSequences/A_EN_SRC_CA_M_EmpSwd_Stand_F',
    '/Game/_Art/Enemies/HeinMach/Empire/Animation/A_EN_SwordShield_Idle':
        '/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations/SourceSequences/A_EN_SRC_CA_M_EmpireSwordShield_Stand_F',
    '/Game/_Art/Enemies/HeinMach/HalberdElite/Animation/A_EN_HalberdElite_Idle':
        '/Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Animations/SourceSequences/A_EN_SRC_CA_M_Halberd_Stand_F',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def asset_path(value):
    return value.get_path_name().split('.')[0] if value else None


def numeric_contract(sequence):
    model = sequence.controller.get_model_interface()
    frame_rate = model.get_frame_rate()
    return {
        'seconds': sequence.get_play_length(),
        'samples': model.get_number_of_keys(),
        'frames': model.get_number_of_frames(),
        'fps': [frame_rate.numerator, frame_rate.denominator],
        'rate_scale': sequence.get_editor_property('rate_scale'),
        'enable_root_motion': sequence.get_editor_property('enable_root_motion'),
        'force_root_lock': sequence.get_editor_property('force_root_lock'),
        'root_motion_root_lock': str(sequence.get_editor_property('root_motion_root_lock')),
        'skeleton': asset_path(sequence.get_editor_property('skeleton')),
    }


def canonical_target(old, name):
    assert '/Animations/' in old and name.startswith(('A_EN_PLAY_', 'A_EN_SRC_'))
    family = old.rsplit('/Animations/', 1)[0]
    family = family.replace('/SharedSourceReferences', '/Shared')
    family = family.replace('/EliteShield_SourceReferences', '/EliteShield')
    target_name = name.replace('A_EN_SRC_', 'A_EN_PLAY_', 1)
    return family + '/Animations/Playback/' + target_name


def pose_delta(first, second, bone):
    a = first.get_bone_pose(bone, unreal.AnimPoseSpaces.LOCAL)
    b = second.get_bone_pose(bone, unreal.AnimPoseSpaces.LOCAL)
    position = max(abs(getattr(a.translation, key) - getattr(b.translation, key)) for key in ('x', 'y', 'z'))
    scale = max(abs(getattr(a.scale3d, key) - getattr(b.scale3d, key)) for key in ('x', 'y', 'z'))
    qa = [a.rotation.x, a.rotation.y, a.rotation.z, a.rotation.w]
    qb = [b.rotation.x, b.rotation.y, b.rotation.z, b.rotation.w]
    rotation = min(max(abs(x - y) for x, y in zip(qa, qb)), max(abs(x + y) for x, y in zip(qa, qb)))
    return position, rotation, scale


def compare_legacy(legacy_path, canonical_path, manifest):
    legacy = unreal.load_asset(legacy_path)
    canonical = unreal.load_asset(canonical_path)
    assert isinstance(legacy, unreal.AnimSequence) and isinstance(canonical, unreal.AnimSequence)
    assert asset_path(legacy.get_editor_property('skeleton')) == asset_path(canonical.get_editor_property('skeleton'))
    assert numeric_contract(legacy) == numeric_contract(canonical)
    assert unreal.EditorAssetLibrary.get_metadata_tag(legacy, 'OriginalPackage') == manifest['source_package']
    maxima = {}
    for mode, label in ((unreal.AnimDataEvalType.RAW, 'RAW'), (unreal.AnimDataEvalType.COMPRESSED, 'COMPRESSED')):
        options = unreal.AnimPoseEvaluationOptions(evaluation_type=mode, should_retarget=False,
            extract_root_motion=False, incorporate_root_motion_into_pose=True)
        maximum = [0.0, 0.0, 0.0]
        for frame in range(manifest['samples']):
            a = unreal.AnimPoseExtensions.get_anim_pose_at_frame(legacy, frame, options)
            b = unreal.AnimPoseExtensions.get_anim_pose_at_frame(canonical, frame, options)
            assert a.is_valid() and b.is_valid()
            for bone in manifest['bones']:
                delta = pose_delta(a, b, bone)
                maximum = [max(x, y) for x, y in zip(maximum, delta)]
        maxima[label] = maximum
    # Numerical equivalence tolerance for two UE imports of the same original,
    # not a gameplay value. Translation/scale are exact; compression causes the
    # observed quaternion component delta below 2.3e-5.
    assert max(v[0] for v in maxima.values()) < 1e-6
    assert max(v[1] for v in maxima.values()) < 5e-5
    assert max(v[2] for v in maxima.values()) < 1e-6
    return {
        'old_asset': legacy_path,
        'canonical_asset': canonical_path,
        'original_package': manifest['source_package'],
        'contract': numeric_contract(legacy),
        'bones': len(manifest['bones']),
        'all_frames_compared': manifest['samples'],
        'maximum_position_cm_quaternion_component_scale': maxima,
        'comparison_tolerance': [1e-6, 5e-5, 1e-6],
        'referencers': [],
        'action': 'DeleteEquivalentLegacyDuplicate',
    }


def main():
    assert not BACKUP.exists(), 'Plan is frozen by a backup; resume the recorded plan instead'
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True, include_searchable_names=False,
        include_soft_management_references=True, include_hard_management_references=True)
    data = [a for a in registry.get_assets_by_path(ROOT, recursive=True)
        if str(a.asset_class_path.asset_name) == 'AnimSequence']
    assert len(data) == 887
    manifest_rows = read(META / 'AnimationImportManifest.json')
    by_destination = {row['destination']: row for row in manifest_rows}
    rows = []
    legacy = []
    for asset_data in data:
        old = str(asset_data.package_name)
        sequence = unreal.load_asset(old)
        assert isinstance(sequence, unreal.AnimSequence)
        referencers = sorted(str(x) for x in registry.get_referencers(old, options))
        if old in LEGACY:
            assert not referencers
            legacy.append(compare_legacy(old, LEGACY[old], by_destination[LEGACY[old]]))
            continue
        assert old in by_destination, old
        manifest = by_destination[old]
        name = sequence.get_name()
        target = canonical_target(old, name)
        role = unreal.EditorAssetLibrary.get_metadata_tag(sequence, 'EnemyArtRole')
        expected_role = manifest['kind']
        assert role == expected_role, (old, role, expected_role)
        derivation = 'CompositeBake' if role == 'PlaybackClip' else 'DirectOriginalTimeline'
        assert role in ('PlaybackClip', 'SourceSequence')
        rows.append({
            'old_asset': old,
            'new_asset': target,
            'old_name': name,
            'new_name': target.rsplit('/', 1)[1],
            'family': manifest['family'],
            'previous_role': role,
            'playback_derivation': derivation,
            'original_package': manifest['source_package'],
            'contract': numeric_contract(sequence),
            'referencers': referencers,
        })
    assert len(rows) == 884 and len(legacy) == 3
    targets = [row['new_asset'] for row in rows]
    assert len(targets) == len(set(targets)), [p for p, count in collections.Counter(targets).items() if count > 1]
    assert all(row['new_name'].startswith('A_EN_PLAY_') for row in rows)
    assert all('/Animations/Playback/' in row['new_asset'] for row in rows)
    assert not any(unreal.EditorAssetLibrary.does_asset_exist(path) for path in targets)
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    result = {
        'status': 'planned',
        'structure_version': '20260909_PlaybackUnifiedV1',
        'root': ROOT,
        'before_count': 887,
        'rename_count': len(rows),
        'delete_equivalent_legacy_count': len(legacy),
        'after_count': len(rows),
        'target_folder_counts': dict(collections.Counter(row['new_asset'].rsplit('/', 1)[0] for row in rows)),
        'derivation_counts': dict(collections.Counter(row['playback_derivation'] for row in rows)),
        'name_contract': 'A_EN_PLAY_<original asset basename>; AC identifies Composite bake, CA identifies a direct original timeline. Existing full-package disambiguation suffixes remain.',
        'folder_contract': '<region>/Humanoids/<family>/Animations/Playback',
        'metadata_contract': 'EnemyArtRole=PlaybackSequence; PlaybackDerivation retains CompositeBake versus DirectOriginalTimeline; OriginalPackage and immutable import TimingContract remain.',
        'renames': rows,
        'legacy_duplicates': legacy,
    }
    write(REPORT, result)
    print('ENEMY_ANIMATION_STRUCTURE_PLAN', json.dumps({k: v for k, v in result.items()
        if k not in ('renames', 'legacy_duplicates')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
