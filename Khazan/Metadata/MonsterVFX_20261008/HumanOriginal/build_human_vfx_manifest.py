"""Read-only targeted human animation/effect provenance. Writes this report folder only."""
from pathlib import Path
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import bisect
import csv
import hashlib
import json
import os
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
FAMILIES = ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite')
FX = ROOT/'Content/_Art/Effects/Metadata/Extraction_20261006'
CACHE_ROOTS = [OUT/'Source', FX/'Bindings/Source', ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Source',
               ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source',
               ROOT/'Saved/Extracted/CombatEffects_20261006/Bindings/Source',
               ROOT/'Saved/Extracted/InGame_Playback_20261002/Metadata',
               ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/DecalCurveExtraction',
               ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/DecalDependencyExtraction',
               ROOT/'Saved/Extracted/CombatEffects_20261006/Source']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name,value):
    path=OUT/name
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def package(ref):
    return re.sub(r'\.\d+$','',ref.get('ObjectPath','')) if isinstance(ref,dict) else ''


def references(value,prefix='Properties'):
    if isinstance(value,dict):
        if 'ObjectPath' in value:
            yield {'field':prefix,'source_reference':value,'source_package':package(value)}
        else:
            for k,v in value.items():
                yield from references(v,prefix+'.'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value):
            yield from references(v,f'{prefix}[{i}]')


def interpolate(time,points):
    if not points:
        return time
    pairs=sorted((float(p['T_Original']),float(p['T_Dilation'])) for p in points)
    if time<=pairs[0][0]:
        return pairs[0][1]
    if time>=pairs[-1][0]:
        return pairs[-1][1]
    i=bisect.bisect_right([p[0] for p in pairs],time)-1
    a,b=pairs[i:i+2]
    return a[1]+(time-a[0])*(b[1]-a[1])/(b[0]-a[0])


def main():
    assets={r['source_package']:r for r in read(FX/'AssetManifest.json')}
    routes=defaultdict(list)
    for r in read(FX/'EffectRoutingContracts.json'):
        routes[r['source_package']].append(r)
    edges=defaultdict(list)
    for e in read(FX/'DependencyEdges.json'):
        edges[e['source']].append(e)
    imports={r['source_package']:r for r in read(ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AnimationImportManifest.json')}
    old_events=read(ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/PlaybackEventTimes.json')
    saved_event_times={(r['source_package'],r['notify_index']):r for r in old_events['events']}
    library=list(csv.DictReader((ROOT/'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv').open(encoding='utf-8-sig')))
    library=[r for r in library if r['Family'] in FAMILIES]
    by_current={r['CurrentAsset']:r for r in library}
    # Current exhaustion/grapple/death gameplay clones are newer than the organization CSV.
    authors=read(ROOT/'Metadata/MonsterStamina_20261008/Authoring.json')
    extra=[]
    for a in authors['clip_audits']:
        source=a['source'].split('.')[0]
        if source not in by_current:
            continue
        r=dict(by_current[source])
        r.update(CurrentAsset=a['destination'],LegacyAsset=source,current_clone_source=source,
                 clone_copy_options=a['copy_options'],clone_source_proof='Metadata/MonsterStamina_20261008/Authoring.json.clip_audits')
        if r['CurrentAsset'] not in by_current:
            extra.append(r)
            by_current[r['CurrentAsset']]=r
    library+=extra
    cache={}
    missing_animation=set()

    def source_file(p):
        a=assets.get(p)
        if a and (ROOT/a['source_json']).exists():
            return ROOT/a['source_json']
        return next((d/(p+'.json') for d in CACHE_ROOTS if (d/(p+'.json')).exists()),None)

    def load(p):
        if p not in cache:
            f=source_file(p)
            cache[p]=(read(f),f) if f else (None,None)
        return cache[p]

    def effect_type(t):
        return any(k.lower() in t.lower() for k in ('Particle','Decal','Trail','Camera','RimLight','PointLight','SpotLight','LensFlare'))

    source_events={}
    timing={}
    leaf_missing=set()
    # Root + exact leaf metadata only. No filename/prefix matching or family variant merging.
    def source_events_for(p,stack=()):
        if p in source_events:
            return source_events[p]
        if p in stack:
            return []
        data,file=load(p)
        if data is None:
            missing_animation.add(p)
            return []
        obj=next((e for e in data if e.get('Type') in ('AnimSequence','AnimComposite','AnimMontage') and e.get('Name')==p.rsplit('/',1)[-1]),None)
        if not obj:
            obj=next((e for e in data if e.get('Type') in ('AnimSequence','AnimComposite','AnimMontage')),None)
        if not obj:
            return []
        props=obj.get('Properties',{})
        curve=props.get('DilationCurve',{})
        imp=imports.get(p,{})
        active=bool(imp.get('dilation_applied'))
        timing[p]={'source_file':rel(file),'source_sha256':sha(file),'source_export_index':data.index(obj),
                   'source_type':obj['Type'],'raw_sequence_length':props.get('SequenceLength'),
                   'raw_rate_scale':props.get('RateScale'),'dilation_curve_raw':curve,
                   'saved_import_contract':{k:imp.get(k) for k in ('kind','duration','samples','fps','rate_scale','rate_scale_status','dilation_applied','apply_dilation_property','source_sequence_length','source_dilation_length','interpolation')},
                   'dilation_used_from_saved_import_contract':active}
        result=[]
        for ni,n in enumerate(props.get('Notifies',[])):
            reference=n.get('NotifyStateClass') or n.get('Notify') or {}
            path=reference.get('ObjectPath','')
            try:
                idx=int(path.rsplit('.',1)[-1]); notify=data[idx]
            except (ValueError,IndexError):
                continue
            if not effect_type(notify.get('Type','')):
                continue
            raw=notify.get('Properties',{})
            start=float(n.get('LinkValue',n.get('Time',0)))
            end=float(n.get('EndLink',{}).get('LinkValue',start+n.get('Duration',0)))
            # The older author event table is independently stored timing evidence.
            table=saved_event_times.get((p,ni))
            post=lambda t:interpolate(t,curve.get('DilationAnimPositions',[])) if active else t
            a,b=post(start),post(end)
            refs=list(references(raw))
            local_objects=[]
            for rr in refs:
                if rr['source_package']==p:
                    try:
                        oi=int(rr['source_reference']['ObjectPath'].rsplit('.',1)[-1])
                        o=data[oi]
                        local_objects.append({'export_index':oi,'type':o['Type'],'name':o['Name'],'properties_raw':o.get('Properties',{})})
                    except (ValueError,IndexError):
                        pass
            result.append({'source_package':p,'source_file':rel(file),'source_sha256':sha(file),
                           'field':f'Properties.Notifies[{ni}]','notify_index':ni,'notify_export_index':idx,
                           'notify_type':notify['Type'],'notify_name':notify['Name'],
                           'event_raw':n,'notify_properties_raw':raw,'raw_start_seconds':start,'raw_end_seconds':end,
                           'composite_playback_start_seconds':a,'composite_playback_end_seconds':b,
                           'saved_event_time_evidence':table,
                           'timing_mapping':'Original composite clock -> saved imported dilation contract (already baked once); direct CA is unchanged.',
                           'particle_mode_raw':raw.get('ParticleInfo',{}).get('ParticleMode'),
                           'attach_socket_raw':raw.get('ParticleInfo',{}).get('AttachSocketName'),
                           'attach_policy_and_transform_raw':raw.get('ParticleInfo'),
                           'cleanup_flags_raw':{k:v for k,v in raw.items() if any(w in k for w in ('Destroy','Detach','AnimEnd','NotifyEnd','Deact','Attached','OnAttack'))},
                           'references':refs,'local_referenced_exports':local_objects,'leaf_occurrence':None})
        # Include leaf events only where the exact source clip contributes; nested AC preserves offsets/rates.
        segments=props.get('AnimationTrack',{}).get('AnimSegments',[])
        for si,s in enumerate(segments):
            leaf=package(s.get('AnimReference'))
            if not leaf or leaf in stack+(p,):
                continue
            if load(leaf)[0] is None:
                leaf_missing.add(leaf)
                continue
            rate=float(s.get('AnimPlayRate',1))
            if rate<=0:
                timing[p].setdefault('unsupported_segment_rates',[]).append({'segment':si,'raw':s})
                continue
            for ev in source_events_for(leaf,stack+(p,)):
                la,lb=ev['composite_playback_start_seconds'],ev['composite_playback_end_seconds']
                trim_start=float(s.get('AnimStartTime',0));trim_end=float(s['AnimEndTime'])
                if lb<trim_start or la>trim_end:
                    continue
                for loop in range(int(s.get('LoopingCount',1))):
                    a=float(s.get('StartPos',0))+(max(la,trim_start)-trim_start+loop*(trim_end-trim_start))/rate
                    b=float(s.get('StartPos',0))+(min(lb,trim_end)-trim_start+loop*(trim_end-trim_start))/rate
                    a=interpolate(a,curve.get('DilationAnimPositions',[])) if active else a
                    b=interpolate(b,curve.get('DilationAnimPositions',[])) if active else b
                    copied=dict(ev,composite_playback_start_seconds=a,composite_playback_end_seconds=b,
                                leaf_occurrence={'parent_source_package':p,'segment_index':si,'loop_index':loop,'segment_raw':s},
                                timing_mapping='Leaf baked time -> exact parent source segment trim/rate/loop/offset -> parent saved dilation contract.')
                    result.append(copied)
        source_events[p]=result
        return result

    clips=[]
    event_occurrences=[]
    roots=set()
    for r in library:
        p=r['OriginalPackage'];events=source_events_for(p)
        current=r['CurrentAsset'];file=ROOT/'Content'/(current.removeprefix('/Game/')+'.uasset')
        length=float(r.get('clone_copy_options',{}).get('seconds',r['Seconds']))
        rate=float(r.get('clone_copy_options',{}).get('rate_scale',r['RateScale']))
        row=dict(r,current_asset_file=rel(file),current_asset_exists=file.exists(),current_asset_sha256=sha(file) if file.exists() else None,
                 event_count=len(events),current_seconds=length,current_rate_scale=rate,
                 timeline_status='Saved library/current clone contract; no live editor reflection. No proportional stretch to current clip length. Event bounds clipped to current duration.',
                 source_timing=timing.get(p))
        mapped=[]
        for ev in events:
            start=ev['composite_playback_start_seconds'];end=ev['composite_playback_end_seconds']
            inside=end>=0 and start<=length
            m=dict(ev,family=r['Family'],category=r['Category'],current_asset=current,
                   within_current_clip=inside,current_clip_start_seconds=max(0,start),current_clip_end_seconds=min(length,end),
                   playback_start_seconds=max(0,start)/rate,playback_end_seconds=min(length,end)/rate,
                   current_rate_scale=rate,current_crop_seconds=length)
            for ref in ev['references']:
                if ref['source_package'] and ref['source_package']!=ev['source_package']:
                    roots.add(ref['source_package'])
            for o in ev['local_referenced_exports']:
                for ref in references(o['properties_raw']):
                    if ref['source_package'] and ref['source_package']!=ev['source_package']:
                        roots.add(ref['source_package'])
            mapped.append(m)
            event_occurrences.append(m)
        row['mapped_events']=mapped
        clips.append(row)

    queue=deque(sorted(roots)); seen=set();resources=[];all_edges=[];missing_resources=[]
    while queue:
        p=queue.popleft()
        if p in seen or not p or p.startswith(('/Script/','/Engine/','Engine/')):
            continue
        seen.add(p)
        a=assets.get(p)
        data,file=load(p)
        native=a.get('destination') if a else None
        native_file=ROOT/'Content'/(native.removeprefix('/Game/')+'.uasset') if native and native.startswith('/Game/') else None
        row={'source_package':p,'source_file':rel(file) if file else None,'source_sha256':sha(file) if file else None,
             'source_types':sorted({o.get('Type','') for o in data}) if data else [],
             'native_manifest_entry':a,'native_destination':native,'native_file':rel(native_file) if native_file else None,
             'native_file_exists':bool(native_file and native_file.exists()),'native_sha256':sha(native_file) if native_file and native_file.exists() else None,
             'routing_candidates_raw':routes.get(p,[]),'requested_directly_by_notify':p in roots}
        if data is None:
            missing_resources.append(p)
        derived=[]
        if data:
            for i,o in enumerate(data):
                for ref in references(o.get('Properties',{}),f'Exports[{i}].Properties'):
                    if ref['source_package'] and ref['source_package']!=p:
                        derived.append({'source':p,'field':ref['field'],'target':ref['source_package'],'reference':ref['source_reference']})
        # Stored dependency edges provide transitive references even if an export has no editor graph.
        for e in edges.get(p,[]):
            derived.append(dict(e))
        for route in routes.get(p,[]):
            for ref in route.get('references',[]):
                target=package(ref.get('source_reference'))
                if target:
                    derived.append({'source':p,'field':route['field']+ref.get('field',''),'target':target,'routing_condition_raw':route.get('raw_entry')})
        dedup={json.dumps(e,sort_keys=True):e for e in derived}
        row['dependency_count']=len(dedup)
        resources.append(row)
        all_edges+=list(dedup.values())
        queue.extend(e['target'] for e in dedup.values() if e.get('target') and e['target']!=p)
    inputs=[ROOT/'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv',
            ROOT/'Metadata/MonsterStamina_20261008/Authoring.json',FX/'AssetManifest.json',FX/'DependencyEdges.json',
            FX/'EffectRoutingContracts.json',ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AnimationImportManifest.json',
            ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/PlaybackEventTimes.json']
    summary={'current_clips':len(clips),'older_library_clips':len(library)-len(extra),'new_stamina_gameplay_clones':len(extra),
             'unique_clip_original_packages':len({r['OriginalPackage'] for r in library}),
             'event_occurrences':len(event_occurrences),'unique_original_notify_identities':len({(e['source_package'],e['field']) for e in event_occurrences}),
             'notify_types_occurrence':dict(Counter(e['notify_type'] for e in event_occurrences)),
             'per_family':{f:{'clips':sum(r['Family']==f for r in clips),'effect_event_occurrences':sum(e['family']==f for e in event_occurrences)} for f in FAMILIES},
             'resource_packages':len(resources),'resource_native_available':sum(r['native_file_exists'] for r in resources),
             'source_missing':len(missing_resources),'animation_source_missing':len(missing_animation),'leaf_source_missing':len(leaf_missing)}
    limitations=['Read-only saved metadata/library and disk hashes. No Main/Work Source or Content edits, no editor/FModel UI use.',
                 'Native notify defaults/bytecode, dynamic status/physical-surface/attack conditions not confirmed. Preserve raw routing branches; do not choose by filename.',
                 'Sequence timing uses saved import dilation contract; current duration crops, never stretches. Current RateScale converts clip seconds to execution seconds. Montage segment offset/rate must be added by current runtime author.',
                 'Camera/light/raw surface effects are source-only until runtime owner/support is verified; missing property is unknown default.',
                 'Cooked material/particle renderer equivalence and actual visual correctness require isolated RHI/PIE QA. Existing native file existence is not a visual proof.']
    write('OriginalHumanVFXManifest.json',{'schema':'Khazan.MonsterVFX.HumanOriginal.v1','utc':datetime.now(timezone.utc).isoformat(),
                                        'status':'READ_ONLY_ORIGINAL_MAPPING','inputs':[{'file':rel(p),'sha256':sha(p)} for p in inputs],
                                        'summary':summary,'limitations':limitations,'clips':clips})
    unique_notifies={}
    for e in event_occurrences:
        identity=(e['source_package'],e['field'])
        if identity not in unique_notifies:
            unique_notifies[identity]={'source_package':e['source_package'],'source_sha256':e['source_sha256'],
                'source_file':e['source_file'],'field':e['field'],'event':e['event_raw'],
                'notify_object':e['notify_name'],'notify_type':e['notify_type'],
                'notify_export_index':e['notify_export_index'],'notify_properties':e['notify_properties_raw'],
                'local_referenced_exports':e['local_referenced_exports'],'current_occurrences':[],
                'time_contract':'Raw source and saved import dilation contract; current duration crop/rate only, no proportional stretch.'}
        unique_notifies[identity]['current_occurrences'].append({'current_asset':e['current_asset'],'family':e['family'],'category':e['category'],
            'clip_start_seconds':e['current_clip_start_seconds'],'clip_end_seconds':e['current_clip_end_seconds'],
            'playback_start_seconds':e['playback_start_seconds'],'playback_end_seconds':e['playback_end_seconds'],
            'leaf_occurrence':e['leaf_occurrence'],'within_current_clip':e['within_current_clip']})
    write('AnimationEffectNotifies.json',list(unique_notifies.values()))
    write('OriginalSourceTimingContracts.json',timing)
    write('CurrentHumanClipMap.json',[{k:v for k,v in c.items() if k not in ('mapped_events','source_timing','clone_copy_options')} for c in clips])
    write('ResourceClosure.json',{'schema':1,'roots':sorted(roots),'resources':resources,'dependency_edges':all_edges,'missing_source_packages':sorted(missing_resources)})
    needed=sorted((set(missing_resources)|missing_animation|leaf_missing)-{p for p in missing_resources if p.startswith(('/Script/','/Engine/','Engine/'))})
    write('MissingSourceRequests.json',needed)
    write('Summary.json',summary)
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':
    main()
