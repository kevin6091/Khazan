"""Bind the exact four asset writes to saved pose and actual gameplay evidence."""
from pathlib import Path
import copy
import datetime
import hashlib
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def read(relative):
    return json.loads((BASE / relative).read_text(encoding='utf-8-sig'))

def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()

usage_before, usage_after = read('AuditBefore/Usage.json'), read('AuditAfter/Usage.json')
roots_before, roots_after = read('AuditBefore/RootAudit.json'), read('AuditAfter/RootAudit.json')
plan, applied, state = read('RepairPlan.json'), read('Applied/Applied.json'), read('ResumeState.json')
native, rhi = read('RuntimeAfter/Driver.json'), read('ActualPartRHI/Driver.json')
before_poses = {r['asset']: r for r in read('RuntimeBefore02/RootPoses.json')}
after_poses = {r['asset']: r for r in read('RuntimeAfter/RootPoses.json')}
before_files = {r['asset']: r for r in usage_before['sequences']}
after_files = {r['asset']: r for r in usage_after['sequences']}
changed = {r['asset'] for r in plan['assets']}
assert len(changed) == 4 and len(after_poses) == len(before_poses) == len(after_files) == 170
assert changed == {k for k in before_files if before_files[k]['sha256'] != after_files[k]['sha256']}
assert applied['status'] == 'main_applied_pending_fresh_validation' and len(applied['saved']) == 4
for run in (native, rhi):
    assert run['status'] == 'passed' and all(r['passed'] for r in run['tests'])
assert all(r['status'] == 'passed' for r in (usage_after, roots_after))
assert read('ProbeCleanup/Cleanup.json')['status'] == 'probe_deleted'
assert not (ROOT / 'Content/__CodexGiantRootProbe_20261015/PartGroggyLoop.uasset').exists()
assert max(r['root_offset_cm'] for r in after_poses.values()) <= .01
assert all(before_poses[k]['data_model_sha1'] == after_poses[k]['data_model_sha1'] for k in after_poses)
assert all(before_poses[k]['notifies_sha1'] == after_poses[k]['notifies_sha1'] for k in after_poses)
old_roots, new_roots = ({r['asset']: r for r in d['assets']} for d in (roots_before, roots_after))
for key in old_roots:
    old, new = copy.deepcopy(old_roots[key]), copy.deepcopy(new_roots[key])
    old_lock = old['root_motion_settings'].pop('root_motion_root_lock')
    new_lock = new['root_motion_settings'].pop('root_motion_root_lock')
    assert old == new, key
    assert (old_lock != new_lock) == (key in changed)
for row in usage_after['sequences']:
    assert sha(row['file']) == row['sha256'], row['asset']
for file, expected in state['source_baseline'].items():
    assert sha(ROOT / file) == expected, file
captures = read('ActualPartRHI/PartCaptures.json')
assert len(captures) == 6 and all(Path(row['file']).exists() for row in captures.values())
assert all(row['root_offset_cm'] <= .01 for row in captures.values())
runtime_rows = read('ActualPartRHI/RuntimeRoots.json')['rows']
part_rows = [r for r in runtime_rows if r['montage'] and 'PartGroggy' in r['montage']]
assert part_rows and max(r['maximum_root_offset_cm'] for r in part_rows) <= .01
assets = []
for row in applied['saved']:
    assert sha(row['file']) == row['after_sha256']
    assert sha(row['backup']) == row['before_sha256']
    assets.append(dict(row, before_pose=before_poses[row['asset']], after_pose=after_poses[row['asset']]))
report = {
    'status': 'complete_main_verified', 'generated_at_local': datetime.datetime.now().isoformat(), 'project': str(ROOT),
    'remaining': [], 'production_packages_changed': 4, 'allowlist': ['AnimSequence.RootMotionRootLock'],
    'runtime_cpp_edits': 0, 'skeleton_topology_edits': 0, 'raw_channels_written': 0, 'new_gameplay_tunings': 0,
    'cause': 'Both giants PartGroggy Loop/End used ANIM_FIRST_FRAME root lock at imported RAW frame0 [-2.670138359,-522.141235352,0] while skeleton root reference is [0,0,0]. EnableRootMotion/ForceRootLock were already true. Native pose evaluation reproduced 522.148062616cm mesh-root displacement from the capsule model origin.',
    'repair': 'RootMotionRootLock REF_POSE on the four exact source clips; no actor/mesh scaling, key rebake, notify retiming, or root hierarchy transfer.',
    'numeric_provenance': {'first_frame_field': 'AuditBefore/RootAudit.json assets[].local_motion.skeleton_root.start.translation',
        'reference_field': 'assets[].skeleton_root.reference_transform.translation',
        'formula': 'Euclidean distance(imported RAW frame0 root translation, target skeleton reference root translation), cm',
        'value_kind': 'Current imported data measurement and engine root-lock adapter, not a new original-game tuning value',
        'technical_pose_tolerance_cm': .01},
    'inventory': {'actual_sequences': 170, 'montages': 30, 'combo_definitions': 2, 'enabled_body_sequences': 162,
        'intentional_nonmoving_additive_exceptions': state['intentional_additive_root_disabled'],
        'exception_reason': 'Existing PlayHitReaction requires additive montage !HasRootMotion; enabling zero-root overlays would break the independent flinch/primary attack root owner.',
        'force_root_lock_disabled': [], 'root_track_missing_or_wrong_order': []},
    'assets': assets, 'source_unchanged': state['source_baseline'],
    'preservation': {'complete_native_data_model_sha1_equal': 170, 'complete_notify_sha1_equal': 170,
        'unrelated_sequence_files_sha256_equal': 166, 'raw_frame_bone_hashes_equal_on_changed_assets': 4,
        'saved_root_audit_difference_only_allowlisted_setting': True},
    'root_pose_result': {'samples': 510, 'maximum_all_sequence_offset_cm': max(r['root_offset_cm'] for r in after_poses.values()),
        'changed_asset_before_offset_cm': 522.1480626156842, 'changed_asset_after_offset_cm': 0},
    'native_after': native, 'actual_part_rhi': rhi, 'actual_part_reactions': read('ActualPartRHI/PIE.json'),
    'capsule_captures': captures, 'part_runtime_samples': sum(r['samples'] for r in part_rows),
    'part_runtime_maximum_root_offset_cm': max(r['maximum_root_offset_cm'] for r in part_rows),
    'before_expected_failure_and_attack_regression': read('RuntimeBefore02/Driver.json'),
    'before_attack_entries_passed': 47, 'build': 'No rebuild: gameplay C++ unchanged. Actual existing standard module/hash is bound independently in each run.',
    'probe': {'creation_and_full_raw_frames': 'Probe/Probe.json', 'fresh_native_saved_pose': 'ProbeNative/Driver.json',
        'cleanup': read('ProbeCleanup/Cleanup.json')},
    'diagnostics_not_counted_as_pass': ['RuntimeBefore native-debugger interrupted/crashed run; see DebuggerEvidence.json. Agent breakpoints and session were removed; 8 user exception breakpoints preserved.',
        'RuntimeBefore02 whole batch failed exactly 4 old root-origin cases; its 47 actual pattern entries passed independently.'],
    'visual_inspection': ['Apes Loop and Yetuga End capsule/mesh frames inspected; four Loop/End captures exist with measured zero root offset.'],
    'limits': ['510 saved-pose samples and real gameplay cases establish the stated root-origin fix; this is not an original-game pixel identity or Shipping/network performance certification.']
}
(BASE / 'FinalVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
state.update(status='complete_main_verified', updated_at_local=datetime.datetime.now().isoformat(), remaining=[],
             next='No pending delivery. Start future related work from FinalVerification and current four package hashes; do not re-run completed author/probe/import or restore old assets.')
(BASE / 'ResumeState.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
print('complete_main_verified; 4 corrected roots -> 0cm; 170 models/notifies preserved; 510 poses and actual RHI passed')
