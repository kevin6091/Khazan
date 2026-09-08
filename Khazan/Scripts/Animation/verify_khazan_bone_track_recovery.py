"""Read-only verification, intended for a fresh Unreal Python commandlet."""

import hashlib
import json
import math
import runpy
from pathlib import Path

import unreal


project = Path(unreal.Paths.project_dir()).resolve()
helpers = runpy.run_path(str(project / 'Scripts/Animation/recover_khazan_missing_bone_tracks.py'),
                        run_name='recovery_verification_helpers')
applied = json.loads((helpers['REPORTS'] / 'Khazan_SkeletonRecovery_apply_20260908.json').read_text(encoding='utf-8'))
if applied['status'] != 'passed':
    raise RuntimeError('Recovery application has not passed')

report = {'status': 'in_progress', 'fresh_process': True, 'assets': [], 'protected_files': []}
report_path = helpers['REPORTS'] / 'Khazan_SkeletonRecovery_FreshAudit_20260908.json'
raw_options = helpers['evaluation_options']()
mesh = unreal.load_asset('/Game/_Art/Kazan/Character/Meshs/SKM_Khazan')
runtime_options = helpers['evaluation_options'](unreal.AnimDataEvalType.COMPRESSED, mesh)
runtime_options.should_retarget = True
probe_bones = ['bip001', 'bip001-pelvis', 'bip001-spine2', 'bip001-l-foot',
               'bip001-r-foot', 'bip001-l-hand', 'bip001-r-hand']

try:
    for row in applied['assets']:
        asset = unreal.load_asset(row['target'])
        source = unreal.load_asset(row['source'])
        if helpers['fingerprint'](asset) != row['retained']:
            raise RuntimeError('Saved settings/markers changed: ' + row['target'])
        names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(asset)]
        source_names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(source)]
        if len(names) != 226 or set(names) != set(source_names):
            raise RuntimeError('Saved bone tracks mismatch: ' + row['target'])
        maxima = [0.0, 0.0, 0.0]
        root_keys = []
        count = row['retained']['keys']
        for frame in range(count):
            actual = helpers['sample'](asset, frame, raw_options)
            expected = helpers['sample'](source, frame, raw_options)
            root_keys.append(helpers['components'](actual.get_bone_pose('root')))
            for name in names:
                if name.lower() == 'root':
                    continue
                delta = helpers['errors'](actual.get_bone_pose(name), expected.get_bone_pose(name))
                maxima = [max(x, y) for x, y in zip(maxima, delta)]
        if maxima[0] > 0.001 or maxima[1] > 0.02 or maxima[2] > 0.0001:
            raise RuntimeError('Saved RAW pose mismatch: ' + str(maxima))
        root_hash = hashlib.sha256(json.dumps(root_keys).encode()).hexdigest()
        if root_hash != row['root_pose_sha256']:
            raise RuntimeError('Saved root keys changed: ' + row['target'])

        runtime_maxima = [0.0, 0.0, 0.0]
        for frame in sorted({0, 3, 8, count // 2, count - 2, count - 1}):
            actual = helpers['sample'](asset, frame, runtime_options)
            expected = helpers['sample'](source, frame, runtime_options)
            for name in probe_bones:
                delta = helpers['errors'](actual.get_bone_pose(name), expected.get_bone_pose(name))
                runtime_maxima = [max(x, y) for x, y in zip(runtime_maxima, delta)]
        if runtime_maxima[0] > 0.1 or runtime_maxima[1] > 0.2 or runtime_maxima[2] > 0.001:
            raise RuntimeError('Compressed pose differs from healthy source: ' + str(runtime_maxima))
        first = helpers['sample'](asset, 0, runtime_options)
        later = helpers['sample'](asset, 8, runtime_options)
        foot_rotation_delta = max(helpers['errors'](first.get_bone_pose(name), later.get_bone_pose(name))[1]
                                  for name in ['bip001-l-foot', 'bip001-r-foot'])
        if foot_rotation_delta < 0.1:
            raise RuntimeError('Compressed feet do not animate: ' + row['target'])
        report['assets'].append({
            'path': row['target'], 'tracks': len(names), 'settings_markers_root_preserved': True,
            'keys_per_track_checked': count, 'raw_max_errors': maxima,
            'compressed_local_max_errors_vs_healthy_source': runtime_maxima,
            'compressed_foot_rotation_change_degrees_frame0_to8': foot_rotation_delta,
            'file_sha256': helpers['sha'](project / ('Content/' + row['target'][6:].split('.')[0] + '.uasset')),
        })

    manifest = json.loads((helpers['BACKUP'] / 'manifest.json').read_text(encoding='utf-8'))
    changed = {'Content/' + (helpers['TARGET_BASE'] + rel)[6:] + '.uasset' for rel, _ in helpers['PAIRS']}
    for row in manifest['files']:
        if not row['path'].startswith('Content/') or row['path'] in changed:
            continue
        if helpers['sha'](project / row['path']) != row['sha256']:
            raise RuntimeError('Unrelated protected asset changed: ' + row['path'])
        report['protected_files'].append(row['path'])
    report['status'] = 'passed'
except Exception as exc:
    report['status'] = 'failed'
    report['error'] = str(exc)
    raise
finally:
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('KHAZAN_RECOVERY_FRESH_AUDIT ' + json.dumps({'status': report['status'], 'assets': len(report['assets']),
                                                'protected_files': len(report['protected_files']), 'report': str(report_path)}))
