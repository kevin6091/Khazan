"""Bounded commandlet batches of source and source-timed playback sequences."""
import unreal,pathlib,json,sys,math,time,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Saved/ArtTools/EnemyPython'))
import numpy as np
EAL=unreal.EditorAssetLibrary;TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));ROWS=json.loads((ROOT/'AnimationImportManifest.json').read_text(encoding='utf-8'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def load(p):
    x=unreal.load_asset(p)
    if not x:raise RuntimeError('Missing '+p)
    return x
def save(x):
    if not EAL.save_loaded_asset(x,only_if_is_dirty=False):raise RuntimeError('Save '+x.get_path_name())
def import_one(r):
    path=r['destination']
    if EAL.does_asset_exist(path):
        seq=load(path)
        if EAL.get_metadata_tag(seq,'EnemyTimingVersion')=='20260909_SourceAndDilationV1':return seq,False
        raise RuntimeError('Unrecognized existing animation '+path)
    skinfo=M['skeletons'][r['source_skeleton']];skel=load(skinfo['destination']);mesh=load(skinfo['preview_mesh'])
    factory=unreal.AnimSequenceFactory();factory.set_editor_property('target_skeleton',skel);factory.set_editor_property('preview_skeletal_mesh',mesh)
    folder,name=path.rsplit('/',1)
    # UE 5.8's factory marks the model populated and fixes the compression
    # sampling rate at creation. Seed both with this asset's source-derived
    # rate in this commandlet only, then restore the in-memory default. NEVER
    # suppresses property-change notifications; no project config is saved.
    settings=unreal.get_default_object(unreal.AnimationSettings)
    previous=settings.get_editor_property('default_frame_rate')
    settings.set_editor_property('default_frame_rate',unreal.FrameRate(*r['fps']),notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    try:seq=TOOLS.create_asset(name,folder,unreal.AnimSequence,factory)
    finally:settings.set_editor_property('default_frame_rate',previous,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    if not seq:raise RuntimeError('Create '+path)
    data=np.load(r['data_file']);assert data.shape==(r['samples'],len(r['bones']),10)
    controller=seq.controller;controller.open_bracket('Source Enemy animation timing',False)
    controller.set_frame_rate(unreal.FrameRate(*r['fps']),False)
    controller.set_number_of_frames(unreal.FrameNumber(r['samples']-1),False)
    for i,bone in enumerate(r['bones']):
        values=data[:,i,:].tolist()
        positions=[unreal.Vector(*v[:3]) for v in values]
        rotations=[unreal.Quat(*v[3:7]) for v in values]
        scales=[unreal.Vector(*v[7:]) for v in values]
        controller.add_bone_curve(bone,False)
        if not controller.set_bone_track_keys(bone,positions,rotations,scales,False):raise RuntimeError('Track '+bone)
    controller.close_bracket(False)
    seq.set_editor_property('rate_scale',r['rate_scale'])
    for src,dst in [('bEnableRootMotion','enable_root_motion'),('bForceRootLock','force_root_lock')]:
        if src in r['properties']:seq.set_editor_property(dst,r['properties'][src])
    if 'RootMotionRootLock' in r['properties']:
        key=r['properties']['RootMotionRootLock'].split('::')[-1];mapping={'RefPose':unreal.RootMotionRootLock.REF_POSE,'AnimFirstFrame':unreal.RootMotionRootLock.ANIM_FIRST_FRAME,'Zero':unreal.RootMotionRootLock.ZERO}
        if key in mapping:seq.set_editor_property('root_motion_root_lock',mapping[key])
    EAL.set_metadata_tag(seq,'OriginalPackage',r['source_package'])
    EAL.set_metadata_tag(seq,'EnemyTimingVersion','20260909_SourceAndDilationV1')
    EAL.set_metadata_tag(seq,'TimingContract',json.dumps({k:v for k,v in r.items() if k not in ['bones','data_file','properties']},ensure_ascii=False))
    EAL.set_metadata_tag(seq,'SourceMetadataFile','Metadata/Source/'+r['source_package']+'.json')
    EAL.set_metadata_tag(seq,'EnemyArtRole',r['kind'])
    EAL.set_metadata_tag(seq,'PlaybackUsage','Baked segment rates/dilation; play at 1x. Do not apply source DilationCurve again.' if r['kind']=='PlaybackClip' else 'Original raw sequence timing; use matching PlaybackClip for composite trims/rates/dilation.')
    save(seq)
    return seq,True
def verify(r,seq):
    length=seq.get_play_length();error=abs(length-r['duration'])
    assert error<0.00001,(r['destination'],'duration',length,r['duration'])
    assert abs(seq.get_editor_property('rate_scale')-r['rate_scale'])<0.000001
    data=np.load(r['data_file']);mesh=load(M['skeletons'][r['source_skeleton']]['preview_mesh'])
    # Timing of every asset; first, middle and last full source poses in both
    # editor/raw and runtime compressed representations.
    maximum=np.zeros(3);worst=None
    for kind in [unreal.AnimDataEvalType.RAW,unreal.AnimDataEvalType.COMPRESSED]:
        options=unreal.AnimPoseEvaluationOptions(evaluation_type=kind,should_retarget=False,extract_root_motion=False,incorporate_root_motion_into_pose=True)
        for frame in sorted(set([0,(r['samples']-1)//2,r['samples']-1])):
            pose=unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq,frame,options)
            if not pose.is_valid():raise RuntimeError('Invalid pose '+r['destination'])
            for i,bone in enumerate(r['bones']):
                t=pose.get_bone_pose(bone,unreal.AnimPoseSpaces.LOCAL);v=data[frame,i]
                p=[t.translation.x,t.translation.y,t.translation.z];q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w];s=[t.scale3d.x,t.scale3d.y,t.scale3d.z]
                e=[max(abs(a-b) for a,b in zip(p,v[:3])),min(max(abs(a-b) for a,b in zip(q,v[3:7])),max(abs(a+b) for a,b in zip(q,v[3:7]))),max(abs(a-b) for a,b in zip(s,v[7:]))]
                if e[1]>maximum[1]:worst={'bone':bone,'frame':frame,'mode':str(kind),'quaternion_component_error':float(e[1])}
                maximum=np.maximum(maximum,e)
    # Numerical validation tolerances, not original gameplay values.
    assert maximum[0]<0.05 and maximum[1]<0.003 and maximum[2]<0.001,(r['destination'],maximum.tolist(),worst)
    return {'asset':r['destination'],'kind':r['kind'],'source':r['source_package'],'samples':r['samples'],'fps':r['fps'],'duration':length,'source_target_duration':r['duration'],'duration_error_seconds':error,'dilation_applied':r.get('dilation_applied',False),'max_pose_errors_position_cm_quat_component_scale':maximum.tolist(),'worst_rotation':worst}
def main():
    command=unreal.SystemLibrary.get_command_line();start=0;count=len(ROWS)
    for part in command.split():
        if part.startswith('-EnemyStart='):start=int(part.split('=')[1])
        if part.startswith('-EnemyCount='):count=int(part.split('=')[1])
    report={'status':'running','start':start,'count':count,'assets':[]};target=PROJECT/'Saved/ImportReports/EnemyAnimationBatches'/('%04d.json'%start)
    try:
        for i,r in enumerate(ROWS[start:start+count],start):
            seq,new=import_one(r);entry=verify(r,seq);entry['created']=new;report['assets'].append(entry)
            write(target,report);print('ENEMY_ANIMATION',i+1,'/',len(ROWS),r['destination'],flush=True)
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:write(target,report)
if __name__=='__main__':main()
