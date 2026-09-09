"""Preserve original sample timing and bake composite/dilation playback timelines.

All durations/rates are source metadata values. The baked clips invert the
original T_Dilation -> T_Original table. They must play at 1x; applying the same
dilation again would double the correction. Original sequences remain separate.
"""
import pathlib,sys,json,struct,math,fractions,bisect,collections
PROJECT=pathlib.Path(__file__).resolve().parents[2];ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Saved/ArtTools/EnemyPython'))
import numpy as np
H=struct.Struct('<20siii')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def pkg(v):return v.get('ObjectPath',v.get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/')
def chunks(p):
    data=p.read_bytes();off=0;out={}
    while off<len(data):
        tag,flags,size,n=H.unpack_from(data,off);off+=32;out[tag.split(b'\0')[0].decode()]=(size,n,data[off:off+size*n]);off+=size*n
    assert off==len(data);return out
def source_data(r):
    c=chunks(pathlib.Path(r['source_file']));s,n,data=c['BONENAMES'];bones=[data[i*s:i*s+64].split(b'\0')[0].decode() for i in range(n)]
    info=struct.unpack('<64s64s4i3f3i',c['ANIMINFO'][2][:168]);frames=info[-1]
    assert frames==r['properties']['NumFrames'],(r['source_package'],frames,r['properties']['NumFrames'])
    key=np.frombuffer(c['ANIMKEYS'][2],dtype='<f4').reshape(frames,n,8)
    pose=np.empty((frames,n,10),dtype=np.float32);pose[:,:,:3]=key[:,:,:3];pose[:,:,1]*=-1
    pose[:,:,3:7]=key[:,:,3:7];pose[:,:,4]*=-1;pose[:,0,6]*=-1
    norms=np.linalg.norm(pose[:,:,3:7],axis=2,keepdims=True);assert np.all(norms>0);pose[:,:,3:7]/=norms
    pose[:,:,7:10]=np.frombuffer(c['SCALEKEYS'][2],dtype='<f4').reshape(frames,n,4)[:,:,:3] if 'SCALEKEYS' in c else 1
    return bones,pose,info[8]
def interpolate(pose,seconds,length):
    f=np.clip(np.asarray(seconds,dtype=np.float64)/length*(len(pose)-1),0,len(pose)-1)
    lo=np.floor(f).astype(np.int64);hi=np.minimum(lo+1,len(pose)-1);alpha=(f-lo).astype(np.float32)[:,None,None]
    a=pose[lo];b=pose[hi].copy();dot=np.sum(a[:,:,3:7]*b[:,:,3:7],axis=2)
    b[:,:,3:7]*=np.where(dot<0,-1,1)[:,:,None]
    out=a*(1-alpha)+b*alpha;out[:,:,3:7]/=np.linalg.norm(out[:,:,3:7],axis=2,keepdims=True)
    return out
def dilation_spec(pr):
    d=pr.get('DilationCurve',{});pairs=d.get('DilationAnimPositions',[])
    active=bool(pairs and d.get('BakedDilationCurveName') and pr.get('ApplyDilationCurveType')!='EApplyDilationCurveType::None')
    if active:
        x=[v['T_Dilation'] for v in pairs];y=[v['T_Original'] for v in pairs]
        assert all(b>a for a,b in zip(x,x[1:])), 'Nonmonotonic source dilation time'
        assert all(b>=a for a,b in zip(y,y[1:])), 'Nonmonotonic source original time'
        assert abs(x[-1]-d['DilationSequenceLength'])<0.0001
    return active,d
def main():
    m=read(ROOT/'ImportManifest.json');sources={r['source_package']:r for r in m['animations']};composites={r['source_package']:r for r in m['composites']}
    cache={};rows=[];reports=[]
    def has_root_motion(p):
        if p in sources:return sources[p]['properties'].get('bEnableRootMotion',False)
        return any(has_root_motion(pkg(s['AnimReference'])) for s in composites[p]['properties']['AnimationTrack']['AnimSegments'])
    def load_source(p):
        if p not in cache:
            r=sources[p];bones,pose,psafps=source_data(r);cache[p]=(bones,pose)
            rawframes=r['properties']['NumFrames'];length=r['properties']['SequenceLength'];fps=fractions.Fraction((rawframes-1)/length).limit_denominator(1000)
            file=ROOT/'Derived/AnimationData'/('src_'+str(len(rows)).zfill(4)+'.npy');file.parent.mkdir(parents=True,exist_ok=True);np.save(file,pose)
            row={k:r[k] for k in ['source_package','source_skeleton','destination','family']}
            row.update({'kind':'SourceSequence','data_file':str(file),'bones':bones,'samples':rawframes,'duration':length,'fps':[fps.numerator,fps.denominator],'source_num_frames':rawframes,'source_sequence_length':length,'source_psa_anim_rate':psafps,'rate_scale':r['properties'].get('RateScale',1.0),'rate_scale_status':'Serialized override' if 'RateScale' in r['properties'] else 'Not serialized; engine/CUE AnimSequenceBase default 1.0, not an explicit game override','metadata_file':str(ROOT/'Metadata'/(p+'.json')),'properties':{k:v for k,v in r['properties'].items() if k in ['bEnableRootMotion','RootMotionRootLock','bForceRootLock','AdditiveAnimType','RefPoseType','RefFrameIndex']}})
            rows.append(row)
        return cache[p]
    for p in sources:load_source(p)
    def evaluate(p,times,stack=()):
        assert p not in stack,'Recursive composite '+p
        if p in sources:
            bones,pose=load_source(p);return bones,interpolate(pose,times,sources[p]['properties']['SequenceLength'])
        r=composites[p];pr=r['properties'];segments=pr['AnimationTrack']['AnimSegments'];result=None;names=None
        for i,s in enumerate(segments):
            rate=s['AnimPlayRate'];assert rate!=0
            span=s['AnimEndTime']-s['AnimStartTime'];end=s['StartPos']+span/abs(rate)*s['LoopingCount']
            selected=(times>=s['StartPos']-1e-7)&(times<=end+1e-7)
            elapsed=np.clip((times[selected]-s['StartPos'])*abs(rate),0,span*s['LoopingCount'])
            local=np.mod(elapsed,span);local=np.where(elapsed>=span*s['LoopingCount']-1e-7,span,local)
            local=s['AnimStartTime']+local if rate>0 else s['AnimEndTime']-local
            sub=pkg(s['AnimReference']);bn,values=evaluate(sub,local,stack+(p,))
            if result is None:result=np.empty((len(times),len(bn),10),dtype=np.float32);result[:]=np.nan;names=bn
            assert bn==names,'Composite skeleton/bone order mismatch '+p
            result[selected]=values
        assert result is not None and np.isfinite(result).all(),'Uncovered composite time '+p
        return names,result
    nontrivial=0;skipped=[]
    for i,r in enumerate(m['composites']):
        p=r['source_package'];pr=r['properties'];active,d=dilation_spec(pr)
        unselected=[pkg(s['AnimReference']) for s in pr['AnimationTrack']['AnimSegments'] if pkg(s['AnimReference']) not in sources and pkg(s['AnimReference']) not in composites]
        if unselected:
            skipped.append({'source':p,'inputs':unselected,'reason':'Projectile/VFX or equipment outside selected human assemblies; metadata retained, no incompatible skeleton assigned.'});continue
        if not pr.get('SequenceLength'):
            skipped.append({'source':p,'reason':'Source has no positive SequenceLength; source segment AnimEndTime is zero. Original metadata retained; no duration invented.'});continue
        duration=d['DilationSequenceLength'] if active else pr['SequenceLength']
        source_rates=[(sources[pkg(s['AnimReference'])]['properties']['NumFrames']-1)/sources[pkg(s['AnimReference'])]['properties']['SequenceLength'] for s in pr['AnimationTrack']['AnimSegments'] if pkg(s['AnimReference']) in sources]
        target_rate=1/d['TimePerFrame'] if active else max(source_rates or [30.0])
        intervals=max(1,round(duration*target_rate));fps=fractions.Fraction(intervals/duration).limit_denominator(100000)
        times=np.linspace(0,duration,intervals+1)
        source_times=np.interp(times,[v['T_Dilation'] for v in d['DilationAnimPositions']],[v['T_Original'] for v in d['DilationAnimPositions']]) if active else times
        # Rounded serialized end times may exceed SequenceLength by a few ulps.
        source_times=np.clip(source_times,0,pr['SequenceLength'])
        bones,pose=evaluate(p,source_times)
        file=ROOT/'Derived/AnimationData'/('play_'+str(i).zfill(4)+'.npy');np.save(file,pose)
        nontrivial+=int(active and abs(duration-pr['SequenceLength'])>0.0001)
        row={k:r[k] for k in ['source_package','source_skeleton','destination','family']}
        row.update({'kind':'PlaybackClip','data_file':str(file),'bones':bones,'samples':intervals+1,'duration':duration,'fps':[fps.numerator,fps.denominator],'rate_scale':pr.get('RateScale',1.0),'rate_scale_status':'Not serialized; playback is baked and must use 1x','dilation_applied':active,'apply_dilation_property':pr.get('ApplyDilationCurveType','Not serialized; active baked named table used'),'source_sequence_length':pr['SequenceLength'],'source_dilation_length':d.get('DilationSequenceLength'),'target_sample_rate_source':'DilationCurve.TimePerFrame' if active else 'Referenced sequence NumFrames and SequenceLength','segments':pr['AnimationTrack']['AnimSegments'],'metadata_file':str(ROOT/'Metadata'/(p+'.json')),'interpolation':'Translation/scale linear; shortest-path normalized linear quaternion interpolation; source dilation table inverted piecewise linearly','properties':{}})
        rows.append(row)
        row['properties']['bEnableRootMotion']=has_root_motion(p)
        row['root_motion_status']='Derived from referenced source sequence bEnableRootMotion; FAnimTrack.HasRootMotion is any contributing segment.'
        reports.append({'source':p,'destination':row['destination'],'source_seconds':pr['SequenceLength'],'playback_seconds':duration,'dilation_applied':active,'baked_curve_name':d.get('BakedDilationCurveName'),'segments':len(pr['AnimationTrack']['AnimSegments']),'fps':row['fps'],'samples':intervals+1})
        if i%100==0:print('BAKED_PLAYBACK',i,'/',len(m['composites']),flush=True)
    write(ROOT/'AnimationImportManifest.json',rows)
    write(ROOT/'AnimationTimingAudit.json',{'source_sequences':len(sources),'source_fps':dict(collections.Counter(str(r['fps']) for r in rows if r['kind']=='SourceSequence')),'playback_clips':len(reports),'changed_duration_clips':nontrivial,'metadata_only_clips':skipped,'numpy_version':np.__version__,'clips':reports,'runtime_limitations':'Actor custom time dilation, AI skill-state branches and game hit-stop cannot be determined solely from these art clips. Source SI/SB/notify metadata is archived; no gameplay logic is invented.'})
    print('ANIMATION_TIMING_READY',len(rows),'changed_duration',nontrivial)
if __name__=='__main__':main()
