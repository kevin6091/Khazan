"""Recover the eight 2026-09-08 sequences without replacing their edited assets.

Run inside Unreal Editor with RECOVERY_MODE='prepare' first, then 'apply'.
Only the 225 absent tracks are added. Existing root keys, duration, markers,
notifies, curves, metadata, and sequence settings are checked for preservation.
The original on-disk files must match the verified backup before application.
"""

import hashlib
import json
import math
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
BACKUP = PROJECT / 'Saved/ArtBackups/Khazan_SkeletonRecovery_20260908_132146'
REPORTS = PROJECT / 'Saved/ImportReports'
TARGET_BASE = '/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/'
SOURCE_BASE = '/Game/_Art/Kazan/Animation/Weapons/DualAxeSword/Shared/Locomotion/'
PREVIEW_BASE = '/Game/_Recovery/KhazanSkeleton_20260908/'
PAIRS = [
    ('Walk/DAS_Khazan_Walk_Loop', 'Walk/CA_P_Kazan_DualAxeSword_Walk_F'),
    ('Run/DAS_Khazan_Run_Loop', 'Run/CA_P_Kazan_DualAxeSword_Run_F'),
    ('Sprint/DAS_Khazan_Sprint_Loop', 'Sprint/CA_P_Kazan_DualAxeSword_Sprint_F'),
    ('Walk/DAS_Khazan_Walk_Stop_LF', 'Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_LF'),
    ('Walk/DAS_Khazan_Walk_Stop_RF', 'Walk/CA_P_Kazan_DualAxeSword_Walk_Stop_F_RF'),
    ('Run/DAS_Khazan_Run_Stop_LF', 'Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_LF'),
    ('Run/DAS_Khazan_Run_Stop_RF', 'Run/CA_P_Kazan_DualAxeSword_Run_Stop_F_RF'),
    ('Sprint/DAS_Khazan_Sprint_Stop_LF', 'Sprint/CA_P_Kazan_DualAxeSword_Sprint_Stop_F_02'),
]
SETTINGS = ['enable_root_motion', 'force_root_lock', 'root_motion_root_lock',
            'rate_scale', 'interpolation', 'additive_anim_type', 'ref_pose_type']


def model(asset):
    return unreal.AnimationDataModel.cast(asset.get_editor_property('data_model_interface'))


def fingerprint(asset):
    data = model(asset)
    rate = data.get_frame_rate()
    tracks = [str(n) for n in unreal.AnimationLibrary.get_animation_notify_track_names(asset)]
    return {
        'skeleton': asset.get_editor_property('skeleton').get_path_name(),
        'frames': data.get_number_of_frames(), 'keys': data.get_number_of_keys(),
        'frame_rate': [rate.numerator, rate.denominator], 'seconds': asset.get_play_length(),
        'markers_by_track': {
            n: [{'name': str(m.marker_name), 'time': m.time}
                for m in unreal.AnimationLibrary.get_animation_sync_markers_for_track(asset, n)]
            for n in tracks
        },
        'notify_tracks': tracks,
        'notifies': [n.export_text() for n in unreal.AnimationLibrary.get_animation_notify_events(asset)],
        'curve_counts': [data.get_number_of_float_curves(), data.get_number_of_transform_curves()],
        'metadata': {str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(asset).items()},
        'settings': {n: str(asset.get_editor_property(n)) for n in SETTINGS},
    }


def evaluation_options(kind=unreal.AnimDataEvalType.RAW, mesh=None):
    return unreal.AnimPoseEvaluationOptions(
        evaluation_type=kind, should_retarget=False, extract_root_motion=False,
        incorporate_root_motion_into_pose=True, optional_skeletal_mesh=mesh)


def sample(asset, frame, options):
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(asset, frame, options)
    if not pose.is_valid():
        raise RuntimeError('Invalid pose: ' + asset.get_path_name())
    return pose


def components(transform):
    p, q, s = transform.translation, transform.rotation, transform.scale3d
    return [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def errors(actual, expected):
    a, b = components(actual), components(expected)
    position = math.dist(a[:3], b[:3])
    scale = math.dist(a[7:], b[7:])
    norm = math.sqrt(sum(x * x for x in a[3:7]) * sum(x * x for x in b[3:7]))
    dot = abs(sum(a[i] * b[i] for i in range(3, 7))) / norm
    angle = math.degrees(2 * math.acos(min(1.0, dot)))
    return position, angle, scale


def run(mode):
    if mode not in ('prepare', 'apply'):
        raise ValueError('RECOVERY_MODE must be prepare or apply')
    manifest = json.loads((BACKUP / 'manifest.json').read_text(encoding='utf-8'))
    backups = {r['path']: r for r in manifest['files']}
    if mode == 'apply':
        preview = json.loads((REPORTS / 'Khazan_SkeletonRecovery_prepare_20260908.json').read_text(encoding='utf-8'))
        if preview.get('status') != 'passed' or len(preview['assets']) != len(PAIRS):
            raise RuntimeError('All eight preview recoveries must pass first')

    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for target_rel, _ in PAIRS:
        if TARGET_BASE + target_rel in dirty:
            raise RuntimeError('Unsaved user edits: ' + target_rel)
        rel = 'Content/' + (TARGET_BASE + target_rel)[6:] + '.uasset'
        expected_hash = backups[rel]['sha256']
        if sha(PROJECT / rel) != expected_hash or sha(BACKUP / rel) != expected_hash:
            raise RuntimeError('Asset changed since backup: ' + rel)

    report = {'mode': mode, 'backup': str(BACKUP), 'status': 'in_progress', 'assets': []}
    report_path = REPORTS / ('Khazan_SkeletonRecovery_' + mode + '_20260908.json')
    options = evaluation_options()
    try:
        for target_rel, source_rel in PAIRS:
            original = unreal.load_asset(TARGET_BASE + target_rel)
            source = unreal.load_asset(SOURCE_BASE + source_rel)
            before = fingerprint(original)
            source_info = fingerprint(source)
            source_names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(source)]
            target_names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(original)]
            if target_names != ['root'] or len(source_names) != 226:
                raise RuntimeError('Unexpected track layout: ' + target_rel)
            if before['skeleton'] != source_info['skeleton'] or before['frame_rate'] != source_info['frame_rate']:
                raise RuntimeError('Skeleton/frame rate mismatch: ' + target_rel)
            if before['keys'] > source_info['keys'] or before['curve_counts'] != [0, 0]:
                raise RuntimeError('Unsupported source range or custom curves: ' + target_rel)
            count = before['keys']
            missing = [n for n in source_names if n.lower() != 'root']
            keys = {n: [[], [], []] for n in missing}
            root_before = []
            for frame in range(count):
                pose = sample(source, frame, options)
                for name in missing:
                    transform = pose.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
                    keys[name][0].append(transform.translation)
                    keys[name][1].append(transform.rotation)
                    keys[name][2].append(transform.scale3d)
                root_before.append(components(sample(original, frame, options).get_bone_pose('root')))

            if mode == 'prepare':
                destination = PREVIEW_BASE + target_rel
                if unreal.EditorAssetLibrary.does_asset_exist(destination):
                    raise RuntimeError('Preview already exists; inspect it before rerunning: ' + destination)
                target = unreal.EditorAssetLibrary.duplicate_loaded_asset(original, destination)
                if not target:
                    raise RuntimeError('Could not create recovery preview')
            else:
                target = original

            controller = unreal.AnimationDataController.cast(target.controller)
            controller.open_bracket('Restore missing Khazan bone tracks', True)
            try:
                for name, (positions, rotations, scales) in keys.items():
                    if not controller.add_bone_curve(name, True):
                        raise RuntimeError('Could not add bone: ' + name)
                    if not controller.set_bone_track_keys(name, positions, rotations, scales, True):
                        raise RuntimeError('Could not write bone keys: ' + name)
            finally:
                controller.close_bracket(True)

            if fingerprint(target) != before:
                raise RuntimeError('Edited sequence settings/markers changed: ' + target_rel)
            if len(unreal.AnimationLibrary.get_animation_track_names(target)) != 226:
                raise RuntimeError('Incomplete recovery: ' + target_rel)
            maxima = [0.0, 0.0, 0.0]
            for frame in range(count):
                pose = sample(target, frame, options)
                if components(pose.get_bone_pose('root')) != root_before[frame]:
                    raise RuntimeError('Existing root changed at frame ' + str(frame))
                for name in missing:
                    expected = unreal.Transform()
                    expected.translation = keys[name][0][frame]
                    expected.rotation = keys[name][1][frame]
                    expected.scale3d = keys[name][2][frame]
                    delta = errors(pose.get_bone_pose(name), expected)
                    maxima = [max(x, y) for x, y in zip(maxima, delta)]
            if maxima[0] > 0.001 or maxima[1] > 0.02 or maxima[2] > 0.0001:
                raise RuntimeError('Pose mismatch: ' + str(maxima))
            if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
                raise RuntimeError('Save failed: ' + target_rel)
            row = {'target': target.get_path_name(), 'source': source.get_path_name(),
                   'restored_tracks': len(missing), 'retained': before,
                   'validated_keys_per_track': count, 'max_errors': maxima,
                   'root_pose_sha256': hashlib.sha256(json.dumps(root_before).encode()).hexdigest(),
                   'root_keys_preserved': True, 'settings_and_markers_preserved': True}
            report['assets'].append(row)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('RECOVERED ' + target_rel + ' ' + str(maxima))
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'assets': len(report['assets']), 'report': str(report_path)}))


if __name__ == '__main__':
    run(globals().get('RECOVERY_MODE', 'prepare'))
