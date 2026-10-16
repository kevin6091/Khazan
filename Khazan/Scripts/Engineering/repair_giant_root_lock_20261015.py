"""Four-package option-only repair. Prove on a duplicate before production."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
BASE = ROOT / 'Metadata/GiantRootUsage_20261015'
PHASE = os.environ['KZ_GIANT_ROOT_PHASE']
OUT = BASE / {'probe': 'Probe', 'apply': 'Applied', 'cleanup': 'ProbeCleanup'}[PHASE]
OUT.mkdir(parents=True, exist_ok=True)
PLAN = json.loads((BASE / 'RepairPlan.json').read_text(encoding='utf-8'))
PROBE = '/Game/__CodexGiantRootProbe_20261015/PartGroggyLoop'
report = {'status': 'running', 'phase': PHASE, 'allowlist': ['AnimSequence.RootMotionRootLock'], 'raw_channels_written': 0, 'saved': []}

def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()

def settings(clip):
    keys = ('enable_root_motion', 'force_root_lock', 'use_normalized_root_motion_scale', 'rate_scale', 'skeleton',
            'additive_anim_type', 'ref_pose_type', 'ref_frame_index', 'ref_pose_seq', 'bone_compression_settings', 'curve_compression_settings')
    result = {}
    for key in keys:
        value = clip.get_editor_property(key)
        result[key] = value.get_path_name() if isinstance(value, unreal.Object) else str(value)
    result['notifies'] = [event.export_text() for event in unreal.AnimationLibrary.get_animation_notify_events(clip)]
    return result

def raw_snapshot(clip):
    model = clip.controller.get_model_interface()
    names = list(clip.get_editor_property('skeleton').get_reference_pose().get_bone_names())
    keys = int(model.get_number_of_keys())
    digest = hashlib.sha256()
    options = unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW, should_retarget=False,
        extract_root_motion=False, incorporate_root_motion_into_pose=True)
    # Exhaustive RAW frame/bone sampling, independent of root locking.
    for frame in range(keys):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(clip, frame, options)
        for name in names:
            t = pose.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
            digest.update(struct.pack('<10d', t.translation.x, t.translation.y, t.translation.z,
                t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, t.scale3d.x, t.scale3d.y, t.scale3d.z))
    return {'all_frame_local_pose_sha256': digest.hexdigest(), 'frames': keys, 'bones': len(names),
            'tracks': [str(x) for x in model.get_bone_track_names()], 'length': clip.get_play_length(), 'settings': settings(clip)}

def preflight():
    dirty = {str(package.get_name()) for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    result = []
    for row in PLAN['assets']:
        assert sha(row['file']) == row['before_sha256'], row['asset']
        assert row['asset'].split('.')[0] not in dirty, 'Unsaved target: ' + row['asset']
        assert sha(row['backup']) == row['before_sha256']
        clip = unreal.load_asset(row['asset'])
        assert clip and clip.get_editor_property('enable_root_motion') and clip.get_editor_property('force_root_lock')
        assert clip.get_editor_property('root_motion_root_lock') == unreal.RootMotionRootLock.ANIM_FIRST_FRAME
        result.append((row, clip))
    return result

try:
    assert len(PLAN['assets']) == 4 and PLAN['allowlist'] == report['allowlist']
    if PHASE == 'probe':
        preflight()
        assert not unreal.EditorAssetLibrary.does_asset_exist(PROBE), 'Probe already exists; inspect its receipt first'
        source = next(row for row in PLAN['assets'] if row['family'] == 'Yetuga' and 'Loop.' in row['asset'])
        clip = unreal.EditorAssetLibrary.duplicate_asset(source['asset'], PROBE)
        assert clip
        before = raw_snapshot(clip)
        clip.set_editor_property('root_motion_root_lock', unreal.RootMotionRootLock.REF_POSE)
        after = raw_snapshot(clip)
        assert before == after, 'Probe changed raw frames/metadata'
        assert unreal.EditorAssetLibrary.save_loaded_asset(clip, only_if_is_dirty=False)
        report.update(status='probe_saved_pending_fresh_native', probe=PROBE, raw_before=before, raw_after=after)
        report['saved'].append(PROBE)
    elif PHASE == 'apply':
        native = json.loads((BASE / 'ProbeNative/Driver.json').read_text(encoding='utf-8-sig'))
        assert native['status'] == 'passed' and all(x['passed'] for x in native['tests'])
        assert json.loads((BASE / 'ProbeNative/RootPoses.json').read_text(encoding='utf-8-sig'))[0]['root_offset_cm'] <= .01
        assert not (OUT / 'Applied.json').exists(), 'Inspect prior application before running again'
        targets = preflight()
        before = {row['asset']: raw_snapshot(clip) for row, clip in targets}
        for row, clip in targets:
            clip.set_editor_property('root_motion_root_lock', unreal.RootMotionRootLock.REF_POSE)
            assert raw_snapshot(clip) == before[row['asset']], row['asset']
        for row, clip in targets:
            assert unreal.EditorAssetLibrary.save_loaded_asset(clip, only_if_is_dirty=False), row['asset']
            report['saved'].append(dict(row, after_sha256=sha(row['file']), preserved=before[row['asset']]))
        report['status'] = 'main_applied_pending_fresh_validation'
    else:
        assert unreal.EditorAssetLibrary.does_asset_exist(PROBE)
        assert unreal.EditorAssetLibrary.delete_asset(PROBE)
        report.update(status='probe_deleted', probe=PROBE)
except Exception:
    report.update(status='failed', error=traceback.format_exc())
    unreal.log_error(report['error'])
    if PHASE == 'apply' and report['saved']:
        # Only exact named Content targets; replace whole files, never truncate hardlinks.
        restored = []
        for row in PLAN['assets']:
            target = Path(row['file']).resolve()
            assert target.is_relative_to((ROOT / 'Content').resolve())
            try:
                temp = target.with_suffix('.uasset.GiantRootRollback')
                shutil.copy2(row['backup'], temp)
                assert sha(temp) == row['before_sha256']
                os.replace(temp, target)
                restored.append({'asset': row['asset'], 'restored': sha(target) == row['before_sha256']})
            except Exception:
                restored.append({'asset': row['asset'], 'restored': False, 'error': traceback.format_exc()})
        report['rollback'] = restored
finally:
    (OUT / {'probe': 'Probe.json', 'apply': 'Applied.json', 'cleanup': 'Cleanup.json'}[PHASE]).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('GIANT_ROOT_OPTION_REPAIR ' + report['status'])
    unreal.SystemLibrary.quit_editor()
