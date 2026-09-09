"""Bake only Root -> C_P_Kazan onto three new Stop sequences.

The AnimSequence's UE 5.8 AnimationSequencerDataModel is an FK Control Rig
sequence. Only those two bone tracks are changed through its data controller.
Other Control Rig channels (including key times/tangents) are hash checked.
Default mode is read-only verify; use STOP_ROOT_MODE='build' once in Editor.
"""

import hashlib
import json
import math
import re
import runpy
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
BACKUP = PROJECT / 'Saved/ArtBackups/DAS_StopRootTransfer_20260908_141845'
BASELINE = BACKUP / 'baseline.json'
REPORTS = PROJECT / 'Saved/ImportReports'
H = runpy.run_path(str(PROJECT / 'Scripts/Animation/recover_khazan_missing_bone_tracks.py'),
                   run_name='stop_root_helpers')
ASSETS = [
    '/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_LF',
    '/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Run/DAS_Khazan_Run_Stop_RF',
    '/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/Sprint/DAS_Khazan_Sprint_Stop',
]
ROOT = 'Root'
PARENT = 'C_P_Kazan'
IGNORED_CONTROLS = {'root_control', 'c_p_kazan_control'}


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def normalize(value, owner):
    if value is None or isinstance(value, (bool, int, float, str)):
        result = value
    elif isinstance(value, unreal.Object):
        result = value.get_path_name()
    elif hasattr(value, 'export_text'):
        result = value.export_text()
    elif isinstance(value, unreal.Array):
        return [normalize(item, owner) for item in value]
    else:
        result = str(value)
    return result.replace(owner, '<THIS_ASSET>') if isinstance(result, str) else result


def settings(asset):
    # Exclude only animation data whose changes are independently verified.
    excluded = {'animation_track_names', 'controller', 'data_model', 'data_model_interface'}
    properties = re.findall(r'- ``([a-z_]+)``', unreal.AnimSequence.__doc__)
    owner = asset.get_path_name()
    values = {name: normalize(asset.get_editor_property(name), owner)
              for name in properties if name not in excluded}
    fingerprint = H['fingerprint'](asset)
    fingerprint['notifies'] = [x.replace(owner, '<THIS_ASSET>') for x in fingerprint['notifies']]
    values['sequence_details'] = fingerprint
    imp = asset.get_editor_property('asset_import_data')
    values['import_filenames'] = list(imp.extract_filenames()) if imp else []
    return values


def other_channels(asset):
    concrete = unreal.find_object(None, asset.get_editor_property('data_model_interface').get_path_name())
    result = {}
    for track in concrete.get_tracks():
        for section in track.get_sections():
            for channel in section.get_all_channels():
                name = str(channel.channel_name)
                if name.split('.', 1)[0].lower() in IGNORED_CONTROLS:
                    continue
                if name in result:
                    raise RuntimeError('Unexpected duplicate Control Rig channel: ' + name)
                keys = []
                for key in channel.get_keys():
                    time = key.get_time(unreal.MovieSceneTimeUnit.TICK_RESOLUTION)
                    row = {'frame': time.frame_number.value, 'subframe': time.sub_frame, 'value': key.get_value()}
                    for prop in ['interpolation_mode', 'tangent_mode', 'tangent_weight_mode', 'arrive_tangent',
                                 'leave_tangent', 'arrive_tangent_weight', 'leave_tangent_weight']:
                        getter = getattr(key, 'get_' + prop, None)
                        if getter:
                            row[prop] = normalize(getter(), asset.get_path_name())
                    keys.append(row)
                result[name] = {'keys': keys, 'default': channel.get_default() if channel.has_default() else None,
                                'pre': str(channel.get_pre_infinity_extrapolation()),
                                'post': str(channel.get_post_infinity_extrapolation())}
    return result


def max_errors(current, errors):
    return [max(x, y) for x, y in zip(current, errors)]


def check_originals(manifest):
    for relative, expected in manifest['protected_file_hashes'].items():
        if H['sha'](PROJECT / relative) != expected:
            raise RuntimeError('Protected original changed: ' + relative)


def verify_pair(before, compressed=False):
    source = unreal.load_asset(before['source'])
    target = unreal.load_asset(before['target'])
    if settings(source) != before['settings'] or settings(target) != before['settings']:
        raise RuntimeError('A setting, length, marker, notify or attribute changed: ' + before['target'])
    source_channels = other_channels(source)
    target_channels = other_channels(target)
    if digest(source_channels) != before['other_channel_sha256'] or source_channels != target_channels:
        raise RuntimeError('A channel outside Root/C_P_Kazan changed: ' + before['target'])
    expected_names = ({n.lower() for n in before['track_names']} - {'root'}) | {'c_p_kazan'}
    actual_names = {str(n).lower() for n in unreal.AnimationLibrary.get_animation_track_names(target)}
    if expected_names != actual_names:
        raise RuntimeError('Unexpected bone tracks: ' + before['target'])
    skeleton = source.get_editor_property('skeleton')
    reference = skeleton.get_reference_pose()
    root_ref = reference.get_bone_pose(ROOT)
    bones = [str(n) for n in reference.get_bone_names() if str(n).lower() != 'c_p_kazan']
    options = H['evaluation_options'](unreal.AnimDataEvalType.COMPRESSED if compressed else unreal.AnimDataEvalType.RAW)
    if compressed:
        options.optional_skeletal_mesh = unreal.load_asset('/Game/_Art/Kazan/Character/Meshs/SKM_Khazan')
        options.should_retarget = True
    world_error, root_static_error = [0.0]*3, [0.0]*3
    parent_motion = []
    for frame in range(before['keys']):
        a = H['sample'](source, frame, options)
        b = H['sample'](target, frame, options)
        for name in bones:
            world_error = max_errors(world_error, H['errors'](
                a.get_bone_pose(name, unreal.AnimPoseSpaces.WORLD),
                b.get_bone_pose(name, unreal.AnimPoseSpaces.WORLD)))
        root_static_error = max_errors(root_static_error, H['errors'](b.get_bone_pose(ROOT), root_ref))
        if frame in (0, before['keys']-1):
            parent_motion.append(H['components'](b.get_bone_pose(PARENT)))
    tolerance = [2.0, 0.2, 0.01] if compressed else [0.01, 0.005, 0.0001]
    if any(x > y for x, y in zip(world_error, tolerance)):
        raise RuntimeError('Component-space pose changed: ' + str(world_error))
    if root_static_error[0] > 1e-6 or root_static_error[1] > 0.00001 or root_static_error[2] > 1e-6:
        raise RuntimeError('Root is not at reference pose: ' + str(root_static_error))
    displacement = math.dist(parent_motion[0][:3], parent_motion[-1][:3])
    if displacement < 1:
        raise RuntimeError('Top bone did not receive movement')
    return {'component_pose_max_errors': world_error, 'root_reference_max_errors': root_static_error,
            'parent_first_last': parent_motion, 'parent_track_translation_delta': displacement,
            'compared_bones_per_frame': len(bones), 'compared_frames': before['keys'],
            'other_control_rig_channels_unchanged': len(target_channels)}


def run(mode):
    if mode not in ('build', 'verify'):
        raise ValueError('STOP_ROOT_MODE must be build or verify')
    manifest = json.loads((BACKUP / 'manifest.json').read_text(encoding='utf-8'))
    report = {'status': 'in_progress', 'mode': mode, 'backup': str(BACKUP), 'assets': []}
    report_path = REPORTS / ('Khazan_DAS_StopRootTransfer_' + mode + '_20260908.json')
    try:
        check_originals(manifest)
        if mode == 'build':
            if BASELINE.exists():
                raise RuntimeError('A baseline exists; inspect previous build before rerunning')
            dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
            for path in ASSETS:
                if path in dirty or unreal.EditorAssetLibrary.does_asset_exist(path + '_New'):
                    raise RuntimeError('Unsaved original or an existing _New asset: ' + path)
            baseline = {'assets': []}
            for path in ASSETS:
                source = unreal.load_asset(path)
                info = settings(source)
                names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(source)]
                if 'root' not in {n.lower() for n in names} or 'c_p_kazan' in {n.lower() for n in names}:
                    raise RuntimeError('Unexpected Root/C_P_Kazan tracks: ' + path)
                if info['sequence_details']['curve_counts'] != [0, 0]:
                    raise RuntimeError('Layered custom curves require separate review')
                native = other_channels(source)
                row = {'source': path, 'target': path + '_New', 'settings': info, 'track_names': names,
                       'keys': H['model'](source).get_number_of_keys(), 'other_channel_sha256': digest(native)}
                baseline['assets'].append(row)
            BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')

            for before in baseline['assets']:
                source = unreal.load_asset(before['source'])
                skeleton = source.get_editor_property('skeleton')
                mesh = skeleton.get_skeleton_preview_mesh()
                if [str(n).lower() for n in mesh.get_bone_children(PARENT)] != ['root']:
                    raise RuntimeError('Unexpected sibling of Root requires extra bone edits')
                root_ref = skeleton.get_reference_pose().get_bone_pose(ROOT)
                options = H['evaluation_options']()
                positions, rotations, scales = [], [], []
                for frame in range(before['keys']):
                    pose = H['sample'](source, frame, options)
                    # UE multiplication: local * parent. Solve
                    # Root_ref * Parent_new = Root_old(t) * Parent_old(t).
                    transferred = root_ref.inverse().multiply(pose.get_bone_pose(ROOT)).multiply(pose.get_bone_pose(PARENT))
                    positions.append(transferred.translation)
                    rotations.append(transferred.rotation)
                    scales.append(transferred.scale3d)
                target = unreal.EditorAssetLibrary.duplicate_loaded_asset(source, before['target'])
                if not target:
                    raise RuntimeError('Could not duplicate: ' + before['source'])
                controller = unreal.AnimationDataController.cast(target.controller)
                controller.open_bracket('Bake Root movement onto C_P_Kazan', True)
                try:
                    if not controller.add_bone_curve(PARENT, True):
                        raise RuntimeError('Could not add top-bone Control Rig curve')
                    if not controller.set_bone_track_keys(PARENT, positions, rotations, scales, True):
                        raise RuntimeError('Could not bake top-bone keys')
                    if not controller.remove_bone_track(ROOT, True):
                        raise RuntimeError('Could not clear Root animation track')
                finally:
                    controller.close_bracket(True)
                result = {'target': before['target'], 'raw': verify_pair(before)}
                if not unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
                    raise RuntimeError('Save failed: ' + before['target'])
                result['compressed'] = verify_pair(before, True)
                report['assets'].append(result)
                report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print('STOP_ROOT_BAKED ' + before['target'])
        else:
            baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
            report['commandlet'] = '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
            for before in baseline['assets']:
                report['assets'].append({'target': before['target'], 'raw': verify_pair(before),
                                         'compressed': verify_pair(before, True)})
        check_originals(manifest)
        report['protected_original_files_unchanged'] = len(manifest['protected_file_hashes'])
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('DAS_STOP_ROOT_TRANSFER ' + json.dumps({'status': report['status'], 'assets': len(report['assets']), 'report': str(report_path)}))


if __name__ == '__main__':
    run(globals().get('STOP_ROOT_MODE', 'verify'))
