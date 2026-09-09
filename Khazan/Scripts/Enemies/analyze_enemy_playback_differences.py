"""Classify source-to-playback changes without modifying animation assets."""
import pathlib,json,csv,collections,sys,math
PROJECT=pathlib.Path(__file__).resolve().parents[2]
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Saved/ArtTools/EnemyPython'))
import numpy as np

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def pkg(v):return v.get('ObjectPath',v.get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/')
def close(a,b):return abs(a-b)<=1e-5 # Comparison tolerance for serialized float seconds, not gameplay tuning.

def main():
    manifest=read(ROOT/'AnimationImportManifest.json')
    sources={r['source_package']:r for r in manifest if r['kind']=='SourceSequence'}
    records=[]
    for row in (r for r in manifest if r['kind']=='PlaybackClip'):
        source=next(o for o in read(pathlib.Path(row['metadata_file'])) if o['Name']==row['source_package'].rsplit('/',1)[1])
        pr=source['Properties'];segments=pr['AnimationTrack']['AnimSegments'];reasons=[]
        if len(segments)!=1:reasons.append('multiple_segments')
        for s in segments:
            ref=pkg(s['AnimReference']);raw=sources.get(ref)
            if not raw:reasons.append('nested_composite')
            if not close(s['AnimPlayRate'],1):reasons.append('segment_play_rate')
            if s['LoopingCount']!=1:reasons.append('loop_count')
            if not close(s['StartPos'],0):reasons.append('segment_start_offset')
            if not close(s['AnimStartTime'],0) or (raw and not close(s['AnimEndTime'],raw['duration'])):reasons.append('source_trim')
        pairs=pr.get('DilationCurve',{}).get('DilationAnimPositions',[])
        deviation=max((abs(v['T_Original']-v['T_Dilation']) for v in pairs),default=0) if row['dilation_applied'] else 0
        if deviation>1e-5:reasons.append('dilation_time_warp')
        references=[sources[pkg(s['AnimReference'])]['destination'] if pkg(s['AnimReference']) in sources else pkg(s['AnimReference']) for s in segments]
        r={'asset':row['destination'],'original_composite':row['source_package'],'family':row['family'],'classification':'ChangedTimeline' if reasons else 'EquivalentSourceTimeline','reasons':sorted(set(reasons)),'source_assets':references,'composite_seconds':row['source_sequence_length'],'playback_seconds':row['duration'],'samples':row['samples'],'fps':row['fps'],'dilation_active':row['dilation_applied'],'max_dilation_time_difference_seconds':deviation,'source_segments':segments}
        if not reasons:
            raw=sources[pkg(segments[0]['AnimReference'])]
            a=np.load(raw['data_file'],mmap_mode='r');b=np.load(row['data_file'],mmap_mode='r')
            r['raw_sequence_seconds']=raw['duration'];r['same_sample_count']=a.shape==b.shape
            if a.shape==b.shape:
                r['maximum_key_component_differences']={'position_cm':float(np.max(np.abs(a[:,:,:3]-b[:,:,:3]))),'quaternion':float(np.max(np.minimum(np.max(np.abs(a[:,:,3:7]-b[:,:,3:7]),axis=2),np.max(np.abs(a[:,:,3:7]+b[:,:,3:7]),axis=2)))),'scale':float(np.max(np.abs(a[:,:,7:]-b[:,:,7:])))}
            r['deletion_policy']='Candidate for later source/playback consolidation after choosing the canonical asset and redirecting consumers; retained in this cleanup.'
        records.append(r)
    result={'status':'passed','comparison_tolerance_seconds':1e-5,'animation_assets_modified':0,'classification_counts':dict(collections.Counter(r['classification'] for r in records)),'reason_counts':dict(collections.Counter(k for r in records for k in r['reasons'])),'active_dilation_count':sum(r['dilation_active'] for r in records),'nonidentity_dilation_count':sum('dilation_time_warp' in r['reasons'] for r in records),'same_duration_can_still_change_timing':sum('dilation_time_warp' in r['reasons'] and close(r['composite_seconds'],r['playback_seconds']) for r in records),'clips':records}
    out=PROJECT/'Saved/ImportReports/HeinMachEnemy_PlaybackComparison_20260909.json';out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    with (ROOT/'PlaybackComparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Family','PlaybackAsset','SourceAssets','Classification','Changes','CompositeSeconds','PlaybackSeconds','FrameRate','MaxTimeWarpSeconds'])
        for r in records:w.writerow([r['family'],r['asset'],' | '.join(r['source_assets']),r['classification'],' | '.join(r['reasons']),r['composite_seconds'],r['playback_seconds'],str(r['fps']),r['max_dilation_time_difference_seconds']])
    print(json.dumps({k:v for k,v in result.items() if k!='clips'},ensure_ascii=False))

if __name__=='__main__':main()
