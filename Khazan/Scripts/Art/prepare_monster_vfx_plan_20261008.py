"""Normalize saved original six-family VFX contracts. No engine or asset writes."""
from collections import Counter, defaultdict
from pathlib import Path
import ast
import bisect
import hashlib
import json
import re
import zipfile

MAIN=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
OUT=MAIN/'Saved/ImportReports/MonsterVFX_20261008'
META=MAIN/'Content/_Art/Effects/Metadata/Extraction_20261006'
FAMILIES=('Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga')

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# Reuse the established pure player conversion helpers, without executing its
# authoring entry point or importing unreal.
PLAYER_HELPER=MAIN/'Scripts/Art/prepare_player_attack_vfx_plan.py'
tree=ast.parse(PLAYER_HELPER.read_text(encoding='utf-8-sig'))
helpers={'source_package','physical_surface','parameter'}
ns={'re':re}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),str(PLAYER_HELPER),'exec'),ns)
physical_surface,parameter=ns['physical_surface'],ns['parameter']

def package(ref):
    raw=(ref or {}).get('ObjectPath',(ref or {}).get('AssetPathName',''))
    if raw.startswith('/Game/'):
        raw='BBQ/Content/'+raw[6:]
    return re.sub(r'\.[^/]+$','',raw)

def relative_file(asset):
    return 'Content/'+asset.split('.')[0].removeprefix('/Game/')+'.uasset'

def interpolate(t,points):
    pairs=sorted((float(p['T_Original']),float(p['T_Dilation'])) for p in points)
    if not pairs:
        return t
    if t<=pairs[0][0]:
        return pairs[0][1]
    if t>=pairs[-1][0]:
        return pairs[-1][1]
    i=bisect.bisect_right([p[0] for p in pairs],t)-1;a,b=pairs[i:i+2]
    return a[1]+(t-a[0])*(b[1]-a[1])/(b[0]-a[0])

def main():
    human=read(MAIN/'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalHumanVFXManifest.json')
    apes=read(MAIN/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json')
    schema=read(MAIN/'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json')
    baseline=read(OUT/'WorkBaseline.json')['main_sha256']
    lookup={r['source_package']:r for r in read(META/'AssetManifest.json')}
    for folder in ('HumanOriginal','ApesYetugaOriginal'):
        for r in read(MAIN/'Metadata/MonsterVFX_20261008'/folder/'ImportReadyAssetManifest.json'):
            if r['source_package'] not in lookup or not lookup[r['source_package']].get('destination'):
                lookup[r['source_package']]=r
    resources=WORK/'Saved/ImportReports/MonsterVFX_20261008/Resources'
    amapfile=resources/'NativeAdapterMap.json';curvefile=resources/'DecalCurveRegistry.json'
    adapters={r['source_package']:r for r in read(amapfile)['adapters']} if amapfile.exists() else {}
    curve_data=read(curvefile) if curvefile.exists() else None
    curve_rows=curve_data if isinstance(curve_data,list) else (curve_data or {}).get('rows',(curve_data or {}).get('curves',[]))
    curve_proofs=[]
    for r in curve_rows:
        source=Path(r['source_json']);source=source if source.is_absolute() else MAIN/source
        assert source.exists() and sha(source)==r['source_sha256'],('GPU curve source SHA mismatch',r['source_package'])
        original=next(o['Properties']['FloatCurve']['Keys'] for o in read(source) if o.get('Type')=='CurveFloat')
        assert original==r['keys'],('GPU curve registry keys differ from exact source',r['source_package'])
        curve_proofs.append(dict(r,source_sha256_verified=True,all_rich_keys_verified=True))
    adapter_proofs=[]
    for a in adapters.values():
        source=a.get('source_json') or (lookup.get(a['source_package']) or {}).get('source_json')
        if source:
            source=Path(source);source=source if source.is_absolute() else MAIN/source
            assert source.exists() and sha(source)==a['source_sha256'],('Native adapter source SHA mismatch',a['source_package'])
        adapter_proofs.append({'source_package':a['source_package'],'source_sha256':a['source_sha256'],
            'source_json':str(source) if source else None,'source_sha256_verified':bool(source),
            'native_destination':a['native_destination'],'adapter_kind':a['adapter_kind']})
    curve_indices={r['source_package']:r['index'] for r in curve_rows}
    execution_evidence=read(MAIN/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ApesExecutionMaterialEvidence.json')
    execution_overrides=[]
    for r in execution_evidence['materials']:
        a=adapters.get(r['source_package'])
        dest=(a or {}).get('native_destination') or '/Game/_Art/Effects/Monsters/Execution/'+r['native_destination'].rsplit('/',1)[-1]+'_Execution'
        execution_overrides.append({'SourceMaterial':r['native_destination'],'ReplacementMaterial':dest})
    old_curves=['FC_Decal_FadeOut','FC_Decal_FadeOut_SlowIn','FC_Decal_FastIn_SlowOut','FC_Decal_FadeOut_Fast']
    for i,n in enumerate(old_curves):
        curve_indices.setdefault('BBQ/Content/_Kazan_/Art/VFX/VFX_Data/Curve/BBQ_Curve/'+n,i)
    for i,n in enumerate(['FC_Decal_FadeInFadeOut_Fast','FC_Decal_FadeOut_SlowIn_2','FC_Fade_Out'],4):
        curve_indices.setdefault('BBQ/Content/_Kazan_/Art/VFX/VFX_Data/Curve/BBQ_Curve/'+n,i)

    def resolve(ref,kind):
        p=package(ref);a=adapters.get(p);r=lookup.get(p)
        dest=(a or {}).get('native_destination') or (r or {}).get('destination')
        typ=(a or {}).get('native_type') or (r or {}).get('source_type')
        expected={'particle':('ParticleSystem',),'material':('Material','MaterialInstanceConstant'),
            'mesh':('StaticMesh',)}[kind]
        f=WORK/relative_file(dest) if dest else None
        return {'source_package':p,'source_reference':ref,'source_type':(r or {}).get('source_type'),
            'native_destination':dest,'native_type':typ,'available':bool(f and f.exists() and typ in expected),
            'native_sha256':sha(f) if f and f.exists() else None,'adapter':a,
            'reason':None if f and f.exists() and typ in expected else 'Native resource/adaptor pending or incompatible type.'}

    def source_exports(e):
        if e.get('source_file'):
            return read(MAIN/e['source_file'])
        with zipfile.ZipFile(MAIN/e['source_zip']) as z:
            return json.loads(z.read(e['source_zip_entry']).decode('utf-8-sig'))

    clips=[];normalized=[]
    for c in human['clips']:
        clips.append({k:v for k,v in c.items() if k not in ('mapped_events','source_timing')})
        for e in c['mapped_events']:
            normalized.append({'asset':c['CurrentAsset'],'family':c['Family'],'category':c['Category'],
                'type':e['notify_type'],'properties':e['notify_properties_raw'],'raw_notify':e['event_raw'],
                'start':e['current_clip_start_seconds'],'end':e['current_clip_end_seconds'],
                'source_start':e['raw_start_seconds'],'source_end':e['raw_end_seconds'],'rate':e['current_rate_scale'],
                'length':e['current_crop_seconds'],'source_package':e['source_package'],'source_sha256':e['source_sha256'],
                'source_file':e['source_file'],'field':e['field'],'leaf_occurrence':e['leaf_occurrence'],
                'source_timing':c['source_timing'],'timing_proof':e.get('saved_event_time_evidence') or e.get('timing_mapping'),
                'within_clip':e['within_current_clip']})
    for c in apes['clips']:
        clips.append(dict(c))
    for c in clips:
        c['visual_owner_kind']='source_prop' if c['Category']=='Prop' else 'monster_character'
        if c['Category']=='Prop':
            c['visual_owner_limitation']='YetugaRock B_Rock/source Rock skeleton, separate prop lifecycle. Data authoring only; exclude monster-body pose representatives. Projectile/summon gameplay is not implemented by this presentation task.'
    by_asset={c['CurrentAsset']:c for c in clips}
    aliases={a['gameplay_copy']:a for a in apes['gameplay_copy_aliases']}
    for asset,a in aliases.items():
        source=a['source_current_art'];c=dict(by_asset[source],CurrentAsset=asset,current_clone_source=source)
        clips.append(c);by_asset[asset]=c
    for e in apes['effect_windows']:
        t=e['timing']
        row={'asset':e['current_asset'],'family':e['family'],'category':e['category'],'type':e['source_export_type'],
            'properties':e['raw_properties'],'raw_notify':e['raw_notify'],'start':max(0,t['baked_sequence_start_seconds']),
            'end':min(t['current_clip_seconds'],t['baked_sequence_end_seconds']),
            'source_start':t['original_start_seconds'],'source_end':t['original_end_seconds'],'rate':t['current_rate_scale'],
            'length':t['current_clip_seconds'],'source_package':e['original_package'],'source_sha256':e['source_metadata_sha256'],
            'source_zip':e['source_zip'],'source_zip_entry':e['source_zip_entry'],
            'field':f"Exports[{e['source_export_index']}].Properties/Notifies[{e['notify_index']}]",
            'timing_proof':t,'within_clip':not t['out_of_clip'],'leaf_occurrence':None}
        normalized.append(row)
        for asset,a in aliases.items():
            if a['source_current_art']==e['current_asset']:
                normalized.append(dict(row,asset=asset,clone_source=e['current_asset']))
    assert len(by_asset)==len(clips), 'Duplicate current sequence identity'
    events=[];unsupported=[];skipped=[];blocking=[]
    for e in normalized:
        if e['type']=='xxAnimNotify_RimLight' and e['properties'].get('Duration') is not None:
            # This is a one-shot notify with a separately serialized visual
            # lifespan; zero FAnimNotifyEvent.Duration is not an empty effect.
            source_end=e['source_start']+e['properties']['Duration']
            points=e.get('source_timing',{}).get('dilation_curve_raw',{}).get('SourceDilationCurve',[])
            e=dict(e,end=min(e['length'],interpolate(source_end,points)),payload_duration_source_seconds=e['properties']['Duration'])
        identity=[e['asset'],e['source_package'],e['field'],e['leaf_occurrence']]
        eid='KZMVFX_'+hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
        common={'event_id':eid,'asset':e['asset'],'family':e['family'],'category':e['category'],
            'notify_type':e['type'],'start_time':e['start'],'end_time':e['end'],
            'source':e,'effect_fields':{'EventId':eid,'SourcePackage':e['source_package'],'SourceField':e['field'],
                'WindowStartTime':e['start'],'WindowEndTime':e['end']},'state_fields':{},'limitations':[]}
        if not e['within_clip'] or e['end']<=e['start']:
            common['reason']='Outside current sequence/cropped empty interval; no duration stretching.'
            skipped.append(common);continue
        p=e['properties'];fields=common['effect_fields'];state=common['state_fields'];resolved=[]
        for flag in ('bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','bDestroyOnAnimEnd','bOnAttackSuccessed','bOnlyStartAttach','OnNotifyEndDeattach'):
            if flag in p:
                fields[flag]=p[flag]
        if e['type']=='xxAnimNotifyState_Particle':
            info=p.get('ParticleInfo',{});mode=info.get('ParticleMode','direct_reference')
            for a,b in {'AttachSocketName':'SourceSocket','RelativeLocation':'RelativeLocation','RelativeRotation':'RelativeRotation',
                'CustomTimeDilation':'CustomTimeDilation','bAttached':'bAttached','bAbsoluteRotation':'bAbsoluteRotation',
                'TranslucencySortPriority':'TranslucencySortPriority','bSpawnOnFloor':'bSpawnOnFloor'}.items():
                if a in info:
                    fields[b]=info[a]
            if 'Scale3D' in info:
                fields['Scale3D']=info['Scale3D']
            elif 'Scale' in info:
                fields['Scale3D']=dict.fromkeys('XYZ',info['Scale'])
            fields['InstanceParameters']=[parameter(x) for x in info.get('ParticleFloatParams',[]) if x.get('bUseOverrideParam') is True and parameter(x)]
            if mode in ('MaterialEffect','StatusEffectParticle'):
                data=lookup.get(package(info.get('EffectData')))
                exports=read(MAIN/data['source_json']) if data else []
                candidates=[v for o in exports for v in o.get('Properties',{}).get('EffectList',[])]
                common['routing_candidates_raw']=candidates
                if mode=='StatusEffectParticle':
                    candidates=[r for r in candidates if r.get('Attribute') in ('EStatusEffectAttribute::None','None')]
                    common['limitations'].append('Only source None status route: original status/enchant producer not implemented; conditional variants retained in raw report.')
                    if len(candidates)==1:
                        r=resolve(candidates[0].get('Particle') or candidates[0].get('NiagaraParticle'),'particle');resolved.append(r)
                        if r['native_destination']:
                            fields['ParticleTemplate']=r['native_destination']
                    else:
                        common['limitations'].append('None status route absent or ambiguous; no invented status selection.')
                else:
                    fields['SurfaceRoutes']=[]
                    for c in candidates:
                        number=physical_surface(c.get('SurfaceType'))
                        if number is not None and 'Particle' in c and 'NiagaraParticle' in c and c['Particle'] is None and c['NiagaraParticle'] is None:
                            fields['SurfaceRoutes'].append({'Surface':number,'ParticleTemplate':None,'bSuppressParticle':True})
                            resolved.append({'source_package':package(info.get('EffectData')),'native_destination':None,'available':True,
                                'status':'explicit_original_null_surface_route','surface':number,'raw_entry':c})
                            continue
                        r=resolve(c.get('Particle') or c.get('NiagaraParticle'),'particle');resolved.append(r)
                        if number is not None and r['native_destination']:
                            fields['SurfaceRoutes'].append({'Surface':number,'ParticleTemplate':r['native_destination']})
                    assert len({r['Surface'] for r in fields['SurfaceRoutes']})==len(fields['SurfaceRoutes'])
                    common['limitations'].append('Exact original EPhysicalSurface route, sampled actual project substrate; no unconditional merging or arbitrary surface override.')
            else:
                r=resolve(info.get('NiagaraParticle') if mode=='Niagara' else info.get('Particle'),'particle');resolved.append(r)
                if r['native_destination']:
                    fields['ParticleTemplate']=r['native_destination']
            for raw in info.get('ParticlePhysicalFloatParams',[]):
                number=physical_surface(raw.get('Key'));params=[parameter(x) for x in raw.get('Value',{}).get('Values',[]) if x.get('bUseOverrideParam') is True and parameter(x)]
                if number is None or not params:
                    continue
                routes=fields.setdefault('SurfaceRoutes',[]);route=next((r for r in routes if r['Surface']==number),None)
                if route is None and fields.get('ParticleTemplate'):
                    route={'Surface':number,'ParticleTemplate':fields['ParticleTemplate']};routes.append(route)
                if route is not None:
                    route.setdefault('FloatParameters',[]).extend(params)
                else:
                    common['limitations'].append('Conditional float override has no authored particle route; raw retained.')
            if info.get('bUseEnvVolumeDependent') and package(info.get('EnvVolumeBundleAsset')).endswith('/EnvVolumeBundle_Winter'):
                fields['bWinterOnly']=True
            if p.get('CorrectionInfos') or any('Correction' in k for k in p):
                common['limitations'].append('Correction snapshots/curves retained in Source. Missing valid CorrectionBoneName does not imply root/world anchor.')
            if not fields.get('ParticleTemplate') and not fields.get('SurfaceRoutes'):
                blocking.append({'event_id':eid,'reason':'No source-resolved particle or surface route','source':e['source_package'],'mode':mode})
        elif e['type']=='xxAnimNotifyState_Decal':
            d=p['DecalCreateData']
            if d.get('DecalMode')=='DecalMode_MaterialEffect':
                source_data=lookup[package(d['MaterialEffect'])];exports=read(MAIN/source_data['source_json'])
                candidates=[v for o in exports for v in o.get('Properties',{}).get('EffectList',[])]
                common['routing_candidates_raw']=candidates;fields['SurfaceRoutes']=[]
                for c in candidates:
                    number=physical_surface(c.get('SurfaceType'));assert number is not None,c
                    if c.get('Material') is None and 'Material' in c:
                        fields['SurfaceRoutes'].append({'Surface':number,'DecalMaterial':None,'bSuppressDecal':True})
                        resolved.append({'source_package':package(d['MaterialEffect']),'native_destination':None,'available':True,
                            'status':'explicit_original_null_decal_surface_route','surface':number,'raw_entry':c})
                    else:
                        r=resolve(c['Material'],'material');resolved.append(r)
                        fields['SurfaceRoutes'].append({'Surface':number,'DecalMaterial':r['native_destination']})
                assert len({r['Surface'] for r in fields['SurfaceRoutes']})==len(fields['SurfaceRoutes'])
                common['limitations'].append('Exact original MaterialEffect surface selector and explicit null suppression; current actual ground trace is the project surface consumer, not proof of proprietary source trace/target semantics.')
            else:
                reference=d.get('DecalMaterial')
                if reference is None and e['family']=='Yetuga' and e['asset'].endswith('/Attack_Armageddon_Start') and 'DecalMode' not in d:
                    candidate=next(n for n in normalized if n['family']=='Yetuga' and n['asset'].endswith('/Death_Die_F')
                        and n['type']=='xxAnimNotifyState_Decal' and package(n['properties']['DecalCreateData'].get('DecalMaterial')).endswith('/FMI_Decal_Deferred_D_02'))
                    reference=candidate['properties']['DecalCreateData']['DecalMaterial']
                    common['temporary_decal_material_fallback']={'status':'assistant-selected temporary rendering fallback; original Armageddon material/CDO unknown',
                        'chosen_source_package':candidate['source_package'],'chosen_source_sha256':candidate['source_sha256'],
                        'chosen_source_field':candidate['field'],'chosen_raw_material_reference':reference,
                        'selection_reason':'Only saved directly referenced non-blood Yetuga decal. Same-family ground presentation fallback; same Armageddon pattern material is unverified.',
                        'preserved_fields':'Exact source Armageddon interval, size/cm, location/cm, rotation/degrees, lifespan/seconds and all opacity curve keys remain unchanged.',
                        'qa':'Inspect ground footprint, size, orientation/color and fade in isolated RHI; replace when original CDO/material evidence is recovered.'}
                r=resolve(reference,'material');resolved.append(r)
                if r['native_destination']:
                    fields['DecalMaterial']=r['native_destination']
            if 'LifeSpan' in d:
                fields['DecalLifeSpan']=d['LifeSpan']
            fields['bSpawnOnFloor']=True
            fields.setdefault('bOnAttackSuccessed','Blood' in package(d.get('DecalMaterial')) or any('Blood' in package(c.get('Material')) for c in common.get('routing_candidates_raw',[])))
            common['limitations'].append('Ground projection/random additive endpoints and absent blood CDO hit guard are disclosed project adapters.')
            for a,b,base,mi,ma in [('RandomDecalScale','DecalSize','BasedVector','DecalSizeRandomMin','DecalSizeRandomMax'),
                ('RandomPosition','RelativeLocation','BasedVector','RelativeLocationRandomMin','RelativeLocationRandomMax'),
                ('RandomRotator','RelativeRotation','BasedRotator','RelativeRotationRandomMin','RelativeRotationRandomMax')]:
                v=d.get(a,{})
                if base in v:
                    fields[b]=v[base]
                for src,dest in [('MinRotator' if base=='BasedRotator' else 'MinVector',mi),('MaxRotator' if base=='BasedRotator' else 'MaxVector',ma)]:
                    if src in v:
                        fields[dest]=v[src]
            fields['InstanceParameters']=[]
            for param in d.get('RandomScalarParams',[]):
                v=param['Value']
                if v.get('ScalarType','').endswith('::Random'):
                    fields['InstanceParameters'].append({'ParameterName':param['Key'],'Minimum':v['RandomMin'],'Maximum':v['RandomMax'],'bRandomInteger':v.get('bRandomFloat') is False})
                elif 'DefaultValue' in v:
                    fields['InstanceParameters'].append({'ParameterName':param['Key'],'Minimum':v['DefaultValue'],'Maximum':v['DefaultValue']})
            curve=package(d.get('OpacityCurve'))
            if curve:
                if curve not in curve_indices:
                    blocking.append({'event_id':eid,'reason':'Missing exact GPU curve registry','source':curve})
                else:
                    fields['DecalOpacityCurveIndex']=curve_indices[curve]
                    common['decal_opacity_curve']=curve
        elif e['type']=='xxAnimNotifyState_SurfaceTrail':
            r=resolve(p.get('TrailMesh'),'mesh');resolved.append(r)
            fields.update(TrailMesh=r['native_destination'],TrailIntensity=p['Intensity'],TrailBlendTime=p['BlendTime'],
                SourceSocket=p['AttachSocketName'],Scale3D=p['Scale'],bAttached=True)
            common['limitations'].append('Static trail mesh source intensity/scale/end BlendTime retained. Mesh material default retained; no guessed intensity shader parameter.')
        elif e['type'] in ('xxAnimNotifyState_SetBoneLocationToMaterialParam','xxAnimNotifyState_SetMaterialParamByCurve'):
            state['MaterialOverrides']=execution_overrides
            for override in execution_overrides:
                f=WORK/relative_file(override['ReplacementMaterial'])
                resolved.append({'source_package':override['SourceMaterial'],'native_destination':override['ReplacementMaterial'],
                    'available':f.exists(),'native_sha256':sha(f) if f.exists() else None,'kind':'source_execution_dissolve_shader_adapter'})
            common['limitations'].append('Five source body MI identities retained; transient Effects-only source-parameter GPU consumer overrides are a disclosed reconstructed shader adapter.')
            if 'BoneName' in p:
                state.update(BoneName=p['BoneName'],VectorParameterName=p['MaterialParamName'])
                common['limitations'].append('Bone world XYZ into source vector parameter; existing alpha/radius retained, native original code unknown.')
            else:
                name=p['CurveName'];exports=source_exports(e)
                curves=[c for o in exports for c in o.get('Properties',{}).get('RawCurveData',{}).get('FloatCurves',[])]
                curve=next((c['FloatCurve'] for c in curves if c.get('Name',{}).get('DisplayName','').lower()==name.lower()),None)
                if not curve:
                    blocking.append({'event_id':eid,'reason':'Source material float curve absent','name':name})
                else:
                    state.update(ScalarCurveName=name,ScalarParameterName=name,bUseScalarCurve=True,ScalarCurve={'EditorCurveData':curve})
                    common['limitations'].append('Scalar parameter name equals original CurveName: disclosed adapter because native source setter code unavailable; exact rich keys preserved.')
        elif e['type']=='xxAnimNotify_RimLight':
            adapter=next((a for a in adapters.values() if a.get('adapter_kind')=='source_rim_overlay'),None)
            dest=(adapter or {}).get('native_destination') or '/Game/_Art/Effects/Monsters/Rim/MI_MonsterRim'
            f=WORK/relative_file(dest);resolved.append({'source_package':e['source_package'],'native_destination':dest,
                'available':f.exists(),'native_sha256':sha(f) if f.exists() else None,'adapter':adapter})
            start,end=e['start'],e['end']
            # Source BlendIn=0 and BlendOut=Duration=1.2: exact linear fade
            # envelope. A shader weight parameter is a disclosed project adapter.
            assert p['BlendIn']['BlendTime']==0 and p['BlendOut']['BlendTime']==p['Duration']
            scalar={'Keys':[{'InterpMode':'RCIM_Linear','TangentMode':'RCTM_Auto','TangentWeightMode':'RCTWM_WeightedNone',
                'Time':start,'Value':1,'ArriveTangent':0,'LeaveTangent':0},
                {'InterpMode':'RCIM_Linear','TangentMode':'RCTM_Auto','TangentWeightMode':'RCTWM_WeightedNone',
                'Time':end,'Value':0,'ArriveTangent':0,'LeaveTangent':0}],
                'PreInfinityExtrap':'RCCE_Constant','PostInfinityExtrap':'RCCE_Constant'}
            state.update(MaterialOverlay=dest,ScalarParameterName='KZVisualRimWeight',bUseScalarCurve=True,
                ScalarCurve={'EditorCurveData':scalar})
            common['limitations'].append('Exact source red(2,0,0), selfmesh and 1.2s fade timing. Additive Fresnel/weight shader is a disclosed temporary render adapter; original alpha0 is retained in source and not used as additive opacity.')
        else:
            common['reason']={'xxAnimNotifyState_SurfaceTrailDeepSnow':'Original snow render-target owner; preserve raw writing props and use current snow owner, no unconditional particle duplication.',
                'xxAnimNotify_WaterSurfaceTrail':'Requires actual water intersection/surface owner.',
                'xxAnimNotifyState_ChangeStatus':'Gameplay status producer context only; no gameplay AI/status implementation authorized.',
                'xxAnimNotifyState_CameraMod':'Original camera owner contract not implemented.',
                'xxAnimNotify_RimLight':'Original rim-light shader owner contract not implemented.'}.get(e['type'],'Original custom notify runtime contract not supported.')
            unsupported.append(common);continue
        common['resource_resolution']=resolved
        common['resource_ready']=all(r['available'] for r in resolved)
        if not common['resource_ready']:
            blocking.append({'event_id':eid,'reason':'Resource pending native import or honest adapter','resources':[r['source_package'] for r in resolved if not r['available']]})
        events.append(common)
    # Explicit assistant-selected temporary presentation fallback, authorized
    # by parent/user policy: only PA_W_Half's ten empty cooked default rows.
    # Preserve their original timing, scale, attachment and lifecycle fields.
    fallback_events=[]
    for e in events:
        if e['notify_type']!='xxAnimNotifyState_Particle' or e['effect_fields'].get('ParticleTemplate') or e['effect_fields'].get('SurfaceRoutes'):
            continue
        info=e['source']['properties'].get('ParticleInfo',{})
        if not package(info.get('EffectData')).endswith('/PA_W_Half'):
            continue
        candidates=[c for c in events if c['asset']==e['asset'] and c['source']['source_package']==e['source']['source_package']
            and any(r['Surface']==0 and r['ParticleTemplate'] and '/Dust/' in r['ParticleTemplate'] and 'Blood' not in r['ParticleTemplate'] for r in c['effect_fields'].get('SurfaceRoutes',[]))]
        assert candidates,'No established same-attack non-blood grounded particle fallback'
        choice=min(candidates,key=lambda c:abs(c['start_time']-e['start_time']))
        e['effect_fields']['SurfaceRoutes']=[dict(r) for r in choice['effect_fields']['SurfaceRoutes']]
        e['resource_resolution']=list(choice['resource_resolution']);e['resource_ready']=choice['resource_ready']
        e['temporary_visual_fallback']={'status':'assistant-selected temporary visual route; PA_W_Half original route unverified',
            'original_empty_data':package(info.get('EffectData')),'chosen_same_attack_source_package':choice['source']['source_package'],
            'chosen_source_field':choice['source']['field'],'chosen_source_sha256':choice['source']['source_sha256'],
            'chosen_effect_data_reference':choice['source']['properties']['ParticleInfo']['EffectData'],
            'chosen_raw_surface_candidates':choice.get('routing_candidates_raw'),
            'selection_formula':'Closest mapped source start time among same-attack same-current-sequence established non-blood grounded dust routes.',
            'reason':'Cooked PA_W_Half has no Properties/EffectList. Grounded contact feedback uses adjacent established same-family route.',
            'units_and_impact':'Source seconds/cm/dimensionless scale retained; resource selection only, no gameplay hit or damage added.',
            'qa':'Inspect ground placement, opacity/dust size and actual surface selection in isolated RHI; replace route when original CDO is recovered.'}
        fallback_events.append(e['event_id'])
    assert len(fallback_events)==10,len(fallback_events)
    blocking=[b for b in blocking if not (b.get('event_id') in fallback_events and b['reason'].startswith('No source-resolved'))]
    for e in events:
        if e['event_id'] in fallback_events and not e['resource_ready']:
            blocking.append({'event_id':e['event_id'],'reason':'Temporary fallback native resources pending','resources':[r['source_package'] for r in e['resource_resolution'] if not r['available']]})
    death=[]
    for family in FAMILIES:
        choices=[c for c in clips if c['Family']==family and c['Category']=='Death']
        basename='Death_Down_Die_F' if family in ('Swordsman','SwordShield') else 'Death_Die_F'
        selected=next(c for c in choices if c['CurrentAsset'].endswith('/'+basename))
        death.append({'family':family,'source_sequence':selected['CurrentAsset'],'original_package':selected['OriginalPackage'],
            'seconds':float(selected['Seconds']),'montage':'/Game/Monsters/'+family+'/Animations/AM_DeathPresentation_'+family,
            'definition':'/Game/Monsters/'+family+'/Data/DA_Character_'+family,'slot':'DefaultSlot',
            'enable_auto_blend_out':False,'selection_provenance':'Project default front/down-front direction adapter, not recovered original death selection.',
            'blend_provenance':'Reuse actual same-family existing ExhaustionMontage blend settings; not asserted original death values.'})
    assert len({e['event_id'] for e in events+unsupported+skipped})==len(normalized)
    lifetime=[]
    for asset in sorted({e['asset'] for e in events}):
        c=by_asset[asset];length=float(c['Seconds'])
        # Engine endpoint epsilon is a lifecycle-only adapter, never a gameplay
        # or original event delay. Source effect windows remain unchanged.
        epsilon=1e-4
        lifetime.append({'event_id':'KZMVFX_CONTEXT_'+hashlib.sha256(asset.encode()).hexdigest()[:24],
            'asset':asset,'family':c['Family'],'category':c['Category'],'start_time':epsilon,'end_time':length-epsilon,
            'effect_fields':{},'state_fields':{'bAnimationContextBoundary':True},'resource_ready':True,
            'project_adapter_kind':'full_sequence_visual_lifetime_context',
            'logical_full_clip_seconds':[0,length],'engine_endpoint_epsilon_seconds':epsilon,
            'epsilon_provenance':'UE5.8 Engine/Source/Runtime/Engine/Private/Animation/AnimTypes.cpp NOTIFY_TRIGGER_OFFSET=UE_KINDA_SMALL_NUMBER; endpoint-only lifecycle adapter.',
            'source':'Project presentation cleanup; source animation identity only. This is not an additional original VFX window.'})
    summary={'sequence_targets':len(clips),'source_event_occurrences':len(normalized),'authorable_windows':len(events),
        'write_sequence_targets':len({e['asset'] for e in events}),'supported_types':dict(Counter(e['notify_type'] for e in events)),
        'unsupported_types':dict(Counter(e['notify_type'] for e in unsupported)),'empty_or_cropped_windows':len(skipped),
        'resource_pending_events':sum(not e['resource_ready'] for e in events),'blocking_rows':len(blocking),
        'default_death_montages':len(death),'temporary_visual_fallback_windows':len(fallback_events),
        'temporary_decal_material_fallback_windows':sum('temporary_decal_material_fallback' in e for e in events),
        'lifetime_sentinel_states':len(lifetime),
        'success_gated_windows':sum(e['effect_fields'].get('bOnAttackSuccessed') is True for e in events)}
    result={'schema':'Khazan.MonsterVFX.PreparedPlaybackPlan.v1','status':'prepared_not_authored','work':str(WORK),
        'source_helper':{'path':str(PLAYER_HELPER.relative_to(MAIN)),'sha256':sha(PLAYER_HELPER),'reused_pure_functions':sorted(helpers)},
        'runtime_schema':schema,'resource_adapter_report':str(amapfile),'gpu_curve_registry_report':str(curvefile),
        'source_inputs':{str(p):sha(p) for p in [
            MAIN/'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalHumanVFXManifest.json',
            MAIN/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json',
            MAIN/'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json',
            MAIN/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ApesExecutionMaterialEvidence.json',
            amapfile,curvefile] if p.exists()},
        'gpu_curve_source_proofs':curve_proofs,'native_adapter_source_proofs':adapter_proofs,
        'resource_reports_present':amapfile.exists() and curvefile.exists(),'clips':clips,'events':events,'lifetime_sentinels':lifetime,
        'unsupported_source_windows':unsupported,'skipped_source_windows':skipped,'blockers':blocking,'death_presentations':death,
        'asset_baseline':{relative_file(c['CurrentAsset']):baseline.get(relative_file(c['CurrentAsset'])) for c in clips},
        'definition_baseline':{relative_file(d['definition']):baseline[relative_file(d['definition'])] for d in death},
        'summary':summary,'timing_contract':'Saved original offsets and import dilation included once. Clip-local seconds retained and only cropped; no stretch. RateScale affects wall clock, montage segment/live rates remain actual runtime responsibility.',
        'limitations':['Prepared metadata is not asset authoring/runtime/render parity proof. Original custom CDO defaults/native code unavailable.',
            'ActorVisualBindings are condition/context, not automatic spawn recipes. Existing gameplay ability and AI policy preserved.',
            'All existing notify GUIDs/triggers/tracks, raw animation keys/curves/settings must be checked by private author and fresh saved audit.']}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'PreparedPlaybackPlan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts=Counter(e['asset'] for e in events)
    cases=['asset\tfamily\tcategory\teventcount\trepresentative']
    represented=set()
    for c in clips:
        role=(c['Family'],c['Category'])
        special=any(e['asset']==c['CurrentAsset'] and e['notify_type'] in ('xxAnimNotifyState_SurfaceTrail','xxAnimNotifyState_SetMaterialParamByCurve') for e in events)
        representative=bool(c['visual_owner_kind']!='source_prop' and counts[c['CurrentAsset']] and (role not in represented or special))
        if representative:
            represented.add(role)
        cases.append('\t'.join([c['CurrentAsset'],c['Family'],c['Category'],str(counts[c['CurrentAsset']]),'1' if representative else '0']))
    text='\n'.join(cases)+'\n'
    (OUT/'NativePlaybackCases.tsv').write_text(text,encoding='utf-8')
    private_reports=WORK/'Saved/ImportReports/MonsterVFX_20261008'
    private_reports.mkdir(parents=True,exist_ok=True)
    (private_reports/'NativePlaybackCases.tsv').write_text(text,encoding='utf-8')
    print(json.dumps(summary))

if __name__=='__main__':
    main()
