"""Map original sound occurrences onto existing baked sequences, without retiming poses."""
from pathlib import Path
from collections import Counter
import bisect
import hashlib
import json
from prepare_gameplay_audio_scope import ROOT, OUT, EXTRACT, SourceCache, read, package, refs

def interpolate(t, points):
    pairs=sorted((float(p['T_Original']),float(p['T_Dilation'])) for p in points)
    if not pairs:return t
    if t<=pairs[0][0]:return pairs[0][1]
    if t>=pairs[-1][0]:return pairs[-1][1]
    i=bisect.bisect_right([p[0] for p in pairs],t)-1
    a,b=pairs[i:i+2]
    return a[1]+(t-a[0])*(b[1]-a[1])/(b[0]-a[0])

def main():
    cache=SourceCache()
    human=read(ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalHumanVFXManifest.json')['clips']
    apes=read(ROOT/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json')
    current=read(OUT/'CurrentAssets03/CurrentAssets.json')['assets']
    by_asset={}
    for c in human+apes['clips']:
        p=ROOT/('Content/'+c['CurrentAsset'].split('.')[0].removeprefix('/Game/')+'.uasset')
        if p.exists():
            by_asset[c['CurrentAsset'].split('.')[0]]={'asset':c['CurrentAsset'].split('.')[0],
                'family':c['Family'],'original':c['OriginalPackage'],'seconds':float(c['Seconds']),
                'timing':c.get('source_timing'), 'derivation':c['TimelineDerivation']}
    for alias in apes['gameplay_copy_aliases']:
        original=by_asset[alias['source_current_art']]
        by_asset[alias['gameplay_copy']]=dict(original,asset=alias['gameplay_copy'])
    player_sources={c['sequence'].split('.')[0]:c['OriginalPackage'] for c in
        read(ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/CurrentSegmentTimingPlan.json') if c.get('OriginalPackage')}
    for e in read(ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPreparedPlaybackPlan.json')['events']:
        player_sources.setdefault(e['sequence'].split('.')[0], e['source']['package'])
    rootprefix='BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/'
    loop_sources={'DAS_Player_Walk_Loop':'CA_P_Kazan_DualAxeSword_Walk_F',
                  'DAS_Player_Run_Loop':'CA_P_Kazan_DualAxeSword_Run_F',
                  'DAS_Player_Sprint_Loop':'CA_P_Kazan_DualAxeSword_Sprint_F'}
    skipped=[]
    for c in current:
        if c['type']!='AnimSequence':continue
        asset=c['asset'].split('.')[0]
        if asset in by_asset:
            by_asset[asset]['seconds']=c['seconds']
            continue
        meta=c['metadata']
        source=player_sources.get(asset) or meta.get('OriginalPackage') or meta.get('SourcePackage')
        name=asset.rsplit('/',1)[-1]
        if not source and '/Player/' in asset:
            if name in loop_sources:source=rootprefix+loop_sources[name]
            elif c.get('import_source'):
                imported=c['import_source'].replace('\\','/').rsplit('/',1)[-1].rsplit('.',1)[0]
                if imported.startswith('CA_P_'):source=rootprefix+imported
            elif name.startswith('AC_Kazan_'):
                sub='Style/Yaksha/SpinningBeast/' if '_SpinningBeast_' in name else 'Common/Grapple/'
                source='BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/'+sub+name
        if source:
            by_asset[asset]={'asset':asset,'family':'Player' if '/Player/' in asset else asset.split('/')[3],
                'original':source,'seconds':c['seconds'],'timing':meta.get('TimingContract'),
                'derivation':'CompositePlayback' if source in player_sources.values() else meta.get('PlaybackDerivation','DirectOriginalTimeline'),
                'current_fps':c['model_fps'],'current_frames':c['model_frames'],
                'legacy_loop_clock':name in loop_sources}
        else:skipped.append({'asset':asset,'reason':'No verified original source mapping in current metadata/manifests.'})
    pointtypes={'xxAnimNotify_AkEvent','xxAnimNotify_Footstep'}
    statetypes={'xxAnimNotifyState_PostAudioEvent','xxAnimNotifyState_AkEventUntilAnimEnd','xxAnimNotifyState_CondAkEvent'}
    collected={}
    def collect(p, ancestry=(), apply_dilation=None):
        key=(p,apply_dilation)
        if key in collected:return collected[key]
        result=cache.get(p)
        if not result or p in ancestry:return []
        exports,proof=result
        top=next((o for o in exports if o.get('Type') in ('AnimSequence','AnimComposite','xxAnimComposite')),exports[0])
        prop=top.get('Properties',{})
        curve=top.get('DilationCurve',prop.get('DilationCurve',{})) or {}
        # Original dumps have both table spellings. Current baked imports record
        # whether this source curve was applied; raw imports keep their raw clock.
        points=curve.get('SourceDilationCurve',curve.get('DilationAnimPositions',[])) if isinstance(curve,dict) else []
        if apply_dilation is False or prop.get('bApplyDilationCurve') is False:points=[]
        rows=[]
        for i,n in enumerate(prop.get('Notifies',[])):
            ref=n.get('Notify') or n.get('NotifyStateClass')
            if not ref:continue
            try:idx=int(ref['ObjectPath'].rsplit('.',1)[-1]); notify=exports[idx]
            except (KeyError,ValueError,IndexError):continue
            typ=notify.get('Type','')
            if typ not in pointtypes|statetypes:continue
            start=float(n.get('LinkValue',n.get('Time',0)))
            end=float(n.get('EndLink',{}).get('LinkValue',start+float(n.get('Duration',0))))
            rows.append({'type':typ,'properties':notify.get('Properties',{}),'source_package':p,
                'field':f'Exports[{idx}].Properties / Notifies[{i}]','proof':proof,'raw_notify':n,
                'raw_start':start,'raw_end':end,'start':interpolate(start,points),'end':interpolate(end,points),
                'timing':{'dilation_points':points,'raw_start':start,'raw_end':end}})
        for i,segment in enumerate(prop.get('AnimationTrack',{}).get('AnimSegments',[])):
            child=package(segment.get('AnimReference'))
            start=float(segment.get('StartPos',0)); trim=float(segment.get('AnimStartTime',0))
            limit=float(segment.get('AnimEndTime',0)); rate=float(segment.get('AnimPlayRate',1))
            if not child or rate==0:continue
            duration=(limit-trim)/abs(rate)
            for occurrence in range(int(segment.get('LoopingCount',1))):
                for e in collect(child,ancestry+(p,)):
                    if not trim<=e['start']<limit:continue
                    a=start+duration*occurrence+(e['start']-trim)/abs(rate)
                    b=start+duration*occurrence+(min(e['end'],limit)-trim)/abs(rate)
                    rows.append(dict(e,start=interpolate(a,points),end=interpolate(b,points),
                        field=e['field']+f' / {p}.AnimationTrack.AnimSegments[{i}] loop={occurrence}',
                        timing={'segment':segment,'loop_occurrence':occurrence,'parent_dilation_points':points,'child':e['timing']}))
        collected[key]=rows
        return rows
    events=[]; requests=set()
    foot='BBQ/Content/_Kazan_/Sound/Player/Player_Common/PlayerLocomotion/Play_PLYR_Footsteps'
    for clip in by_asset.values():
        source=clip['original']
        timing=clip.get('timing')
        use=timing.get('dilation_used_from_saved_import_contract') if isinstance(timing,dict) else None
        occurrences=collect(source,apply_dilation=use)
        if not cache.get(source):
            skipped.append({'asset':clip['asset'],'reason':'Source metadata pending','source':source});continue
        # Raw imported reactions use their original composite's sound, mapped back
        # through the exact matching raw animation segment (no duration normalization).
        if clip['family']=='Player' and '/Reaction/' in clip['asset']:
            basename=clip['asset'].rsplit('/',1)[-1].replace('CA_P_','AC_',1)
            parent='BBQ/Content/_Kazan_/Design/Kazan/Reaction/DualAxeSword/'+basename
            result=cache.get(parent)
            if result:
                props=result[0][0].get('Properties',{})
                segments=props.get('AnimationTrack',{}).get('AnimSegments',[])
                if len(segments)==1:
                    seg=segments[0]
                    # Some original direction names reference the opposite raw pose.
                    # Preserve actual current raw pose and label this voice-only adaptation.
                    for e in collect(parent):
                        if e['type']=='xxAnimNotify_AkEvent':
                            a=float(seg.get('AnimStartTime',0))+(e['raw_start']-float(seg.get('StartPos',0)))*float(seg.get('AnimPlayRate',1))
                            occurrences.append(dict(e,start=a,end=a,
                                timing={'original_segment':seg,'voice_only_raw_reaction_adapter':True,'raw_time':e['raw_start']}))
        if clip.get('legacy_loop_clock'):
            top=cache.get(source)[0][0]['Properties']
            original_fps=(top['NumFrames']-1)/top['SequenceLength']
            current_fps=clip['current_fps'][0]/clip['current_fps'][1]
            clock=original_fps/current_fps
            # These three current loops remain legacy 24-fps FBX tracks at rate1.25.
            # Convert original 30-fps notify frame positions to their current clock;
            # do not stretch the full source to the shorter current crop.
            occurrences=[dict(e,start=e['start']*clock,end=e['end']*clock,
                timing={'source_num_frames':top['NumFrames'],'source_seconds':top['SequenceLength'],
                        'source_fps_calculated':original_fps,'current_fps':clip['current_fps'],
                        'clock_ratio':clock,'formula':'source_notify_seconds * original_fps / current_fps',
                        'prefix_crop':True,'child':e['timing']}) for e in occurrences]
        for e in occurrences:
            if e['start']<0 or e['start']>=clip['seconds']:
                continue
            p=e['properties']; typ=e['type']
            if typ=='xxAnimNotify_Footstep':
                if clip['family']!='Player':continue
                event=foot; endevent=''
                anchor='Bip001-L-Toe0' if p.get('bUseLeftFootCommonBone') else 'Bip001-R-Toe0'
                follow=True;ground=True
            else:
                event=package(p.get('Event') or p.get('AudioEvent') or p.get('BeginAudioEvent'))
                endevent=package(p.get('EndAudioEvent'))
                anchor=p.get('AttachName','');follow=p.get('AttachOnMeshComponent',p.get('Follow',False))
                ground=p.get('SetGroundMaterialSwitch',False)
            if not event:continue
            requests.add(event)
            if endevent:requests.add(endevent)
            end=min(clip['seconds'],max(e['start'],e['end']))
            if typ=='xxAnimNotifyState_AkEventUntilAnimEnd':end=clip['seconds']
            ident=[clip['asset'],e['source_package'],e['field'],event]
            events.append({'event_id':'KZA_'+hashlib.sha256(json.dumps(ident).encode()).hexdigest()[:24],
                'asset':clip['asset'],'family':clip['family'],'event_package':event,'end_event_package':endevent,
                'start':e['start'],'end':end,'is_state':typ in statetypes,'anchor':anchor,'follow':follow,
                'ground_switch':ground,'source':e,'clip':clip,
                'adapter_notes': ['Native common player footstep event selected; native xxFootstep CDO code unavailable.'] if typ=='xxAnimNotify_Footstep' else []})
    unique={e['event_id']:e for e in events}
    plan={'clips':list(by_asset.values()),'events':list(unique.values()),'skipped':skipped,'missing_source':sorted(cache.missing),
          'counts':{'clips':len(by_asset),'events':len(unique),'family_events':dict(Counter(e['family'] for e in unique.values()))}}
    (OUT/'PlaybackPlan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (EXTRACT/'PlaybackEventRequests.json').write_text(json.dumps(sorted(requests),indent=2),encoding='utf-8')
    (EXTRACT/'PlaybackSourceRequests.json').write_text(json.dumps(sorted(cache.missing),indent=2),encoding='utf-8')
    print('PLAYBACK',plan['counts'],'missing source',len(cache.missing),'unmapped',len(skipped),flush=True)
    for name in loop_sources:
        c=next((c for c in by_asset.values() if c['asset'].endswith('/'+name)),None)
        if c:
            result=cache.get(c['original'])
            print('LOOP',name,'current',c['seconds'],'source top',list(result[0][0]) if result else None,
                  'audio',[(e['start'],e['source']['type']) for e in unique.values() if e['asset']==c['asset']])

if __name__=='__main__':main()
