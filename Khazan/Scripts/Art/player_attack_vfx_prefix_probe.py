"""Verify trimmed current WeakAttack prefixes against immutable full bake backups."""
from pathlib import Path
import json
import math
import hashlib
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert ROOT != MAIN
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008/CurrentAssets'
assert ROOT.name == 'Khazan' and ROOT.parent.name == 'Khazan_AttackVFXWork_20261008'
report = {'status': 'running', 'product_asset_saves': False, 'scratch_skeleton_duplicate_only': False,
          'startup_exact_skeleton_redirect_required': True, 'rows': [], 'overfury_rows': []}
options = unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,
    should_retarget=False, extract_root_motion=False, incorporate_root_motion_into_pose=True)
try:
    expected_skeleton = unreal.load_asset('/Game/_Art/Player/Character/Meshs/SK_Player')
    assert expected_skeleton
    def transform_values(t):
        return [float(t.translation.x), float(t.translation.y), float(t.translation.z),
                float(t.rotation.x), float(t.rotation.y), float(t.rotation.z), float(t.rotation.w),
                float(t.scale3d.x), float(t.scale3d.y), float(t.scale3d.z)]
    def differences(x, y):
        qx, qy = x.rotation, y.rotation
        dot = abs(qx.x*qy.x + qx.y*qy.y + qx.z*qy.z + qx.w*qy.w)
        norm = math.sqrt((qx.x*qx.x+qx.y*qx.y+qx.z*qx.z+qx.w*qx.w) *
                         (qy.x*qy.x+qy.y*qy.y+qy.z*qy.z+qy.w*qy.w))
        return [x.translation.distance(y.translation), 2*math.acos(min(1.0, dot/norm)),
                x.scale3d.distance(y.scale3d)]
    def model_info(asset):
        model = asset.controller.get_model_interface()
        rate = model.get_frame_rate()
        return {'frames': model.get_number_of_frames(), 'keys': model.get_number_of_keys(),
                'frame_rate': [rate.numerator, rate.denominator], 'length': model.get_play_length(),
                'bone_tracks': [str(n) for n in model.get_bone_track_names()]}
    def compare(current, full, mapping, full_exact_duration=None):
        assert current and full
        assert current.get_editor_property('Skeleton') == expected_skeleton
        assert full.get_editor_property('Skeleton') == expected_skeleton
        ainfo, binfo = model_info(current), model_info(full)
        names = ainfo['bone_tracks']
        assert names and set(names) == set(binfo['bone_tracks'])
        assert ainfo['keys'] > 1 and binfo['keys'] > 1
        duration = current.get_play_length()
        count = ainfo['keys']
        maxima = [0.0, 0.0, 0.0]
        variation = [0.0, 0.0, 0.0]
        first_a, first_b, samples = {}, {}, []
        digest_a, digest_b = hashlib.sha256(), hashlib.sha256()
        peak = {}
        for key in range(count):
            time = key * ainfo['length'] / (count-1)
            if time > duration + 1e-7:
                continue
            backup_time = time * full.get_play_length() / full_exact_duration if full_exact_duration else time
            a = unreal.AnimPoseExtensions.get_anim_pose_at_time(current, time, options)
            b = unreal.AnimPoseExtensions.get_anim_pose_at_time(full, backup_time, options)
            assert a.is_valid() and b.is_valid()
            local_max = [0.0, 0.0, 0.0]
            for name in names:
                x = a.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
                y = b.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
                digest_a.update(json.dumps([name, key, transform_values(x)]).encode())
                digest_b.update(json.dumps([name, key, transform_values(y)]).encode())
                d = differences(x, y)
                for axis in range(3):
                    local_max[axis] = max(local_max[axis], d[axis])
                    if d[axis] > maxima[axis]:
                        maxima[axis] = d[axis]
                        peak[str(axis)] = {'bone': name, 'time': time, 'backup_time': backup_time,
                                          'current': transform_values(x), 'backup': transform_values(y)}
                if name not in first_a:
                    first_a[name], first_b[name] = x, y
                else:
                    va, vb = differences(first_a[name], x), differences(first_b[name], y)
                    variation[0] = max(variation[0], va[0], vb[0])
                    variation[1] = max(variation[1], va[1], vb[1])
                    variation[2] = max(variation[2], va[2], vb[2])
            if key in (0, count//4, count//2, count*3//4, count-1):
                samples.append({'key': key, 'time': time, 'backup_time': backup_time, 'max_differences': local_max})
        assert variation[0] > 1e-6 or variation[1] > 1e-6, 'Ref-pose/static result is not animation evidence'
        row = {'current': current.get_path_name(), 'backup': full.get_path_name(), 'mapping': mapping,
               'current_length': duration, 'backup_length': full.get_play_length(),
               'current_skeleton': expected_skeleton.get_path_name(), 'backup_skeleton': full.get_editor_property('Skeleton').get_path_name(),
               'current_model': ainfo, 'backup_model': binfo, 'all_bone_key_comparison': True,
               'maximum_position_model_units': maxima[0], 'maximum_rotation_radians': maxima[1], 'maximum_scale': maxima[2],
               'temporal_variation_position_rotation_scale': variation, 'samples': samples, 'peak': peak,
               'pose_sha256_current': digest_a.hexdigest(), 'pose_sha256_backup': digest_b.hexdigest()}
        return row
    for index in range(1, 6):
        current = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/DAS_Player_WeakAttack%02d' % index)
        full = unreal.load_asset('/Game/__AttackVFXQA/Prefix/DAS_Khazan_WeakAtk%02d' % index)
        current_meta = {str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(current).items()}
        contract = json.loads(current_meta['TimingContract'])
        full_exact60_duration = contract['duration']
        row = compare(current, full, 'backup_time=current_time*backup_full_duration/full_exact60_duration; no trim-length normalization', full_exact60_duration)
        row['full_exact60_duration'] = full_exact60_duration
        report['rows'].append(row)
    original = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/OverFury/CA_P_Kazan_DASword_B_OverFury_02')
    for suffix in ('_2', '_3'):
        copy = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/OverFury/CA_P_Kazan_DASword_B_OverFury_02' + suffix)
        report['overfury_rows'].append(compare(copy, original, 'same local source time; native RateScale deliberately excluded from raw pose comparison'))
    report['status'] = 'sampled'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    unreal.log_error(report['error'])
(OUT / 'WeakPrefixPoseProof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KZ_ATTACK_VFX_PREFIX_' + report['status'].upper(), flush=True)
