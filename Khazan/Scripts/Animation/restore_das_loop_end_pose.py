"""Restore the user's frame-0-to-last-frame edit on three baked DAS loops.

Execute in Editor with LOOP_CLOSURE_MODE='apply'. The default mode, 'verify',
only reads assets and checks the saved pre-edit snapshot. No source reimport,
length/marker adjustment, or modification of the external Control Rig scenes.
"""

import hashlib
import json
import math
import runpy
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
BACKUP = PROJECT / 'Saved/ArtBackups/DAS_LoopClosure_20260908_134814'
BASELINE = BACKUP / 'loop_pose_before.json'
REPORTS = PROJECT / 'Saved/ImportReports'
HELPERS = runpy.run_path(str(PROJECT / 'Scripts/Animation/recover_khazan_missing_bone_tracks.py'),
                         run_name='loop_closure_helpers')
ASSETS = ['/Game/_Art/Kazan/Animation/InGame/DAS/Locomotion/' + gait + '/DAS_Khazan_' + gait + '_Loop'
          for gait in ['Walk', 'Run', 'Sprint']]
EXPECTED_LAST = [33, 119, 119]


def file_path(package):
    return PROJECT / ('Content/' + package[6:] + '.uasset')


def capture(asset):
    names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(asset)]
    info = HELPERS['fingerprint'](asset)
    options = HELPERS['evaluation_options']()
    frames = []
    for frame in range(info['keys']):
        pose = HELPERS['sample'](asset, frame, options)
        frames.append([HELPERS['components'](pose.get_bone_pose(n)) for n in names])
    return {'path': asset.get_path_name().split('.')[0], 'names': names, 'info': info, 'frames': frames}


def delta(a, b):
    norm = math.sqrt(sum(x*x for x in a[3:7]) * sum(x*x for x in b[3:7]))
    dot = abs(sum(x*y for x, y in zip(a[3:7], b[3:7]))) / norm
    return [math.dist(a[:3], b[:3]), math.degrees(2*math.acos(min(1.0, dot))), math.dist(a[7:], b[7:])]


def maximum(current, value):
    return [max(x, y) for x, y in zip(current, value)]


def verify_one(before):
    asset = unreal.load_asset(before['path'])
    after = capture(asset)
    if before['info'] != after['info'] or before['names'] != after['names']:
        raise RuntimeError('Sequence settings, length, markers, or track names changed: ' + before['path'])
    middle_error, seam_error, previous_seam = [0.0]*3, [0.0]*3, [0.0]*3
    for index in range(len(before['names'])):
        previous_seam = maximum(previous_seam, delta(before['frames'][0][index], before['frames'][-1][index]))
        seam_error = maximum(seam_error, delta(after['frames'][0][index], after['frames'][-1][index]))
    for old_frame, new_frame in zip(before['frames'][:-1], after['frames'][:-1]):
        for old, new in zip(old_frame, new_frame):
            middle_error = maximum(middle_error, delta(old, new))
    if middle_error[0] > 0.001 or middle_error[1] > 0.02 or middle_error[2] > 0.0001:
        raise RuntimeError('Intermediate frame changed: ' + str(middle_error))
    if seam_error[0] > 1e-7 or seam_error[1] > 1e-5 or seam_error[2] > 1e-7:
        raise RuntimeError('First and last RAW poses differ: ' + str(seam_error))
    return {'asset': before['path'], 'last_frame': before['info']['frames'],
            'seconds': before['info']['seconds'], 'tracks': len(before['names']),
            'markers_preserved': before['info']['markers_by_track'],
            'raw_endpoint_error_before': previous_seam, 'raw_endpoint_error_after': seam_error,
            'intermediate_frame_max_error': middle_error}


def verify_compressed(before):
    asset = unreal.load_asset(before['path'])
    mesh = unreal.load_asset('/Game/_Art/Kazan/Character/Meshs/SKM_Khazan')
    opts = HELPERS['evaluation_options'](unreal.AnimDataEvalType.COMPRESSED, mesh)
    opts.should_retarget = True
    first = HELPERS['sample'](asset, 0, opts)
    last = HELPERS['sample'](asset, before['info']['frames'], opts)
    error = [0.0]*3
    for name in before['names']:
        error = maximum(error, HELPERS['errors'](first.get_bone_pose(name), last.get_bone_pose(name)))
    if error[0] > 0.01 or error[1] > 0.02 or error[2] > 0.0001:
        raise RuntimeError('Compressed endpoints differ: ' + str(error))
    return error


def run(mode):
    if mode not in ('apply', 'verify'):
        raise ValueError('Unsupported LOOP_CLOSURE_MODE')
    result = {'status': 'in_progress', 'mode': mode, 'backup': str(BACKUP), 'assets': []}
    result_file = REPORTS / ('Khazan_DAS_LoopClosure_' + mode + '_20260908.json')
    try:
        if mode == 'apply':
            if BASELINE.exists():
                raise RuntimeError('Baseline already exists; inspect prior application before rerunning')
            dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
            manifest = json.loads((BACKUP / 'manifest.json').read_text(encoding='utf-8'))
            saved = {r['path']: r for r in manifest['files']}
            baseline = {'assets': [], 'protected_files': {}}
            for package, last in zip(ASSETS, EXPECTED_LAST):
                if package in dirty:
                    raise RuntimeError('Unsaved user changes: ' + package)
                relative = file_path(package).relative_to(PROJECT).as_posix()
                if HELPERS['sha'](file_path(package)) != saved[relative]['sha256']:
                    raise RuntimeError('Asset changed since backup: ' + package)
                if HELPERS['sha'](BACKUP / relative) != saved[relative]['sha256']:
                    raise RuntimeError('Backup hash mismatch: ' + package)
                row = capture(unreal.load_asset(package))
                if row['info']['frames'] != last or len(row['names']) != 226 or row['info']['curve_counts'] != [0, 0]:
                    raise RuntimeError('Unexpected sequence layout: ' + package)
                baseline['assets'].append(row)
            previous = json.loads((HELPERS['BACKUP'] / 'manifest.json').read_text(encoding='utf-8'))
            target_files = {file_path(p).relative_to(PROJECT).as_posix() for p in ASSETS}
            for row in previous['files'] + manifest['files']:
                relative = row['path']
                if relative.startswith('Content/') and relative not in target_files:
                    baseline['protected_files'][relative] = HELPERS['sha'](PROJECT / relative)
            BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

            for before in baseline['assets']:
                asset = unreal.load_asset(before['path'])
                controller = unreal.AnimationDataController.cast(asset.controller)
                controller.open_bracket('Restore DAS loop first pose at final frame', True)
                try:
                    for index, name in enumerate(before['names']):
                        values = [f[index] for f in before['frames']]
                        values[-1] = values[0]
                        positions = [unreal.Vector(*v[:3]) for v in values]
                        rotations = [unreal.Quat(*v[3:7]) for v in values]
                        scales = [unreal.Vector(*v[7:]) for v in values]
                        if not controller.set_bone_track_keys(name, positions, rotations, scales, True):
                            raise RuntimeError('Could not set final pose for ' + name)
                finally:
                    controller.close_bracket(True)
                row = verify_one(before)
                if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError('Save failed: ' + before['path'])
                row['compressed_endpoint_max_error'] = verify_compressed(before)
                row['file_sha256'] = HELPERS['sha'](file_path(before['path']))
                result['assets'].append(row)
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                print('LOOP_END_RESTORED ' + before['path'])
        else:
            baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
            result['commandlet'] = '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
            for before in baseline['assets']:
                row = verify_one(before)
                row['compressed_endpoint_max_error'] = verify_compressed(before)
                row['file_sha256'] = HELPERS['sha'](file_path(before['path']))
                result['assets'].append(row)

        for relative, digest in baseline['protected_files'].items():
            if HELPERS['sha'](PROJECT / relative) != digest:
                raise RuntimeError('Unrelated asset changed: ' + relative)
        result['protected_files_unchanged'] = len(baseline['protected_files'])
        result['status'] = 'passed'
    except Exception as exc:
        result['status'] = 'failed'
        result['error'] = str(exc)
        raise
    finally:
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('DAS_LOOP_CLOSURE ' + json.dumps({'status': result['status'], 'assets': len(result['assets']), 'report': str(result_file)}))


if __name__ == '__main__':
    run(globals().get('LOOP_CLOSURE_MODE', 'verify'))
