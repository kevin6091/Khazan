"""Private, option-only repair with exact backups and a disposable duplicate probe."""
from pathlib import Path
import os,json,hashlib,traceback,unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
TASK=MAIN/'Metadata/MonsterRootCollisionRepair_20261012';OUT=Path(os.environ['KZ_MONSTER_CONTACT_OUT'])
plan=json.loads((TASK/'RootLockPlan.json').read_text(encoding='utf-8'))
before_rows=json.loads((TASK/'RootPreservationBefore01/RootPoses.json').read_text(encoding='utf-8'))
assert len(before_rows)>300 and {r['asset'] for r in plan['assets']}<=set(r['asset'] for r in before_rows)
report={'status':'running','changed':[],'raw_channels_written':0,'allowlist':['AnimSequence.RootMotionRootLock'],'backup':'RootAssetsBefore','probe':{}}
probe_path='/Game/__CodexMonsterContactProbe_20261012/ChargeTackleEnd'
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def raw_roots(a):
    options=unreal.AnimPoseEvaluationOptions(evaluation_type=unreal.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False,incorporate_root_motion_into_pose=True)
    return [dict(translation=vec(t.translation),rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=vec(t.scale3d)) for t in (unreal.AnimPoseExtensions.get_anim_pose_at_time(a,x,options).get_bone_pose('Root',unreal.AnimPoseSpaces.WORLD) for x in [0,a.get_play_length()*.5,a.get_play_length()])]
def metadata(a):
    values={k:a.get_editor_property(k) for k in ['enable_root_motion','force_root_lock','use_normalized_root_motion_scale','rate_scale','skeleton','additive_anim_type','ref_pose_type','ref_frame_index','bone_compression_settings','curve_compression_settings']}
    return {k:v.get_path_name() if isinstance(v,unreal.Object) else str(v) for k,v in values.items()}
try:
    for row in plan['assets']:
        assert hashlib.sha256((WORK/row['package_file']).read_bytes()).hexdigest()==row['before_sha256'],row['asset']
    # First test on a duplicate; never modify imported root channels or child bones.
    assert not unreal.EditorAssetLibrary.does_asset_exist(probe_path)
    original=unreal.load_asset('/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_ChargeTackle_End')
    probe=unreal.EditorAssetLibrary.duplicate_asset(original.get_path_name(),probe_path);assert probe
    roots=raw_roots(probe);probe.set_editor_property('root_motion_root_lock',unreal.RootMotionRootLock.REF_POSE)
    assert raw_roots(probe)==roots
    assert unreal.EditorAssetLibrary.save_loaded_asset(probe,only_if_is_dirty=False)
    probe=unreal.load_asset(probe_path);assert probe.get_editor_property('root_motion_root_lock')==unreal.RootMotionRootLock.REF_POSE
    assert raw_roots(probe)==roots
    report['probe']={'path':probe_path,'saved':True,'root_keys_unchanged':True,'save_readback':'REF_POSE','later_validation':'fresh native full-body pose test'}
    assert unreal.EditorAssetLibrary.delete_asset(probe_path);report['probe']['deleted']=True
    for row in plan['assets']:
        a=unreal.load_asset(row['asset']);assert a
        roots=raw_roots(a);settings=metadata(a)
        assert a.get_editor_property('enable_root_motion') and a.get_editor_property('force_root_lock')
        a.set_editor_property('root_motion_root_lock',unreal.RootMotionRootLock.REF_POSE)
        after_roots=raw_roots(a);after_settings=metadata(a)
        if after_roots!=roots or after_settings!=settings:
            report['preservation_difference']={'asset':row['asset'],'roots_before':roots,'roots_after':after_roots,'settings_before':settings,'settings_after':after_settings}
        assert after_roots==roots and after_settings==settings,row['asset']
        assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
        report['changed'].append(dict(row,after_sha256=hashlib.sha256((WORK/row['package_file']).read_bytes()).hexdigest(),raw_root_samples_unchanged=True,other_settings_unchanged=True,complete_data_model_and_notifies='pending fresh native digest comparison'))
    report['status']='applied_private_pending_fresh_native_validation'
except Exception:
    report.update(status='failed',error=traceback.format_exc());unreal.log_error(report['error'])
(OUT/'Applied.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ROOT_LOCK_APPLIED',report['status'],len(report['changed']))
