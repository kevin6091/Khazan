"""Prepare original-metadata playback data; no UE import, save, or source edit."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
AUDIT = OUT / 'MetadataAudit'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
HEADER = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan/Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_package(ref):
    return ref.get('ObjectPath', '').rsplit('.', 1)[0] if ref else None

windows = read(AUDIT / 'MappedOriginalEffectWindows.json')
manifest = {r['source_package']: r for r in read(META / 'AssetManifest.json')}
routing = read(META / 'EffectRoutingContracts.json')
source_timing = read(AUDIT / 'OriginalSourceTimingContracts.json')
header_text = HEADER.read_text(encoding='utf-8-sig')
header_fields = set(re.findall(r'^\s*(?:bool|float|int32|FName|FString|FVector|FRotator|FTransform|TObjectPtr<[^>]+>|TArray<[^>]+>|TEnumAsByte<[^>]+>)\s+(\w+)\s*(?:=|;)', header_text, re.M))
native_assets = {}

def particle(ref):
    package = source_package(ref)
    result = {'source_reference': ref, 'source_package': package, 'status': 'missing_reference'}
    if not package:
        return result
    entry = manifest.get(package)
    if not entry:
        result['status'] = 'missing_manifest_entry'
        return result
    result.update(source_type=entry['source_type'], source_metadata_file=entry['source_json'],
                  source_metadata_sha256=entry['source_sha256'], native_destination=entry['destination'])
    metadata = ROOT / entry['source_json']
    result['source_metadata_file_exists'] = metadata.is_file()
    if metadata.is_file():
        result['source_metadata_sha256_observed'] = sha(metadata)
        result['source_metadata_hash_matches_manifest'] = sha(metadata) == entry['source_sha256']
    if entry['source_type'] != 'ParticleSystem':
        result['status'] = 'non_cascade_source_type'
        return result
    destination = entry.get('destination')
    if not destination or not destination.startswith('/Game/'):
        result['status'] = 'missing_native_destination'
        return result
    file = ROOT / ('Content/' + destination.removeprefix('/Game/') + '.uasset')
    result['native_file'] = str(file.relative_to(ROOT))
    result['native_file_exists'] = file.is_file()
    if not file.is_file():
        result['status'] = 'missing_native_uasset'
        return result
    result.update(status='available_cascade', native_sha256=sha(file))
    native_assets[destination] = result
    return result

def physical_surface(raw):
    enum = str(raw).split('::')[-1]
    if enum == 'SurfaceType_Default':
        return 0
    match = re.fullmatch(r'SurfaceType(\d+)', enum)
    return int(match.group(1)) if match and int(match.group(1)) <= 62 else None

def parameter(raw):
    if 'ParameterName' not in raw or 'ValueMin' not in raw or 'ValueMax' not in raw:
        return None
    return {'ParameterName': raw['ParameterName'], 'Minimum': raw['ValueMin'], 'Maximum': raw['ValueMax']}

def route_rows(ref):
    package = source_package(ref)
    file = META / 'Bindings/Source' / (str(package) + '.json')
    return [r for r in routing if r['source_package'] == package], {
        'source_reference': ref, 'source_package': package, 'source_metadata_file': str(file.relative_to(ROOT)),
        'source_metadata_file_exists': file.is_file(), 'source_metadata_sha256': sha(file) if file.is_file() else None}

def occurrence_id(row):
    identity = [row['montage'], row['segment_index'], row['source_package'], row['field']]
    return 'KZFX_' + hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()[:24]

events, unsupported, skipped = [], [], []
for row in windows:
    if not row['within_native_segment']:
        skipped.append({'montage': row['montage'], 'segment_index': row['segment_index'], 'sequence': row['sequence'],
                        'source_package': row['source_package'], 'field': row['field'], 'reason': row.get('skip_reason'),
                        'raw_event': row['event_raw'], 'raw_properties': row['notify_properties_raw']})
        continue
    common = {'event_id': occurrence_id(row), 'montage': row['montage'], 'sequence': row['sequence'],
              'segment_index': row['segment_index'], 'start_time': row['montage_start_sec'],
              'end_time': row['clipped_montage_end_sec'], 'native_start_time': row['native_start_sec'],
              'native_end_time_unclipped': row['native_end_sec'], 'notify_type': row['notify_type'],
              'source': {'package': row['source_package'], 'field': row['field'], 'sha256': row['source_sha256'],
                         'metadata_file': source_timing[row['source_package']]['source_file'],
                         'metadata_file_sha256': source_timing[row['source_package']]['sha256'],
                         'raw_event': row['event_raw'], 'raw_properties': row['notify_properties_raw'],
                         'mapping_proof': row['mapping_proof'], 'boundary_adapter': row.get('boundary_adapter'),
                         'end_mapping_limit': row.get('end_mapping_limit')}}
    if row['notify_type'] == 'xxAnimNotifyState_Decal':
        props = row['notify_properties_raw']
        data = props['DecalCreateData']
        package = source_package(data['DecalMaterial'])
        existing = manifest.get(package)
        destination = existing['destination'] if existing else '/Game/_Art/Effects/Shared/Materials/BBQ_Material/' + package.split('/BBQ_Material/')[-1]
        fields = {'EventId': common['event_id'], 'SourcePackage': row['source_package'], 'SourceField': row['field'],
                  'DecalMaterial': destination, 'DecalLifeSpan': data['LifeSpan'], 'bSpawnOnFloor': True,
                  'bOnAttackSuccessed': props.get('bOnAttackSuccessed', 'Blood' in package), 'InstanceParameters': []}
        for field in ('bDestroyOnNotifyEnd', 'bDestroyOnNotifyEndDeactived', 'bDestroyOnAnimEnd'):
            if field in props:
                fields[field] = props[field]
        for original, native, base, random_min, random_max in (
            ('RandomDecalScale', 'DecalSize', 'BasedVector', 'DecalSizeRandomMin', 'DecalSizeRandomMax'),
            ('RandomPosition', 'RelativeLocation', 'BasedVector', 'RelativeLocationRandomMin', 'RelativeLocationRandomMax'),
            ('RandomRotator', 'RelativeRotation', 'BasedRotator', 'RelativeRotationRandomMin', 'RelativeRotationRandomMax')):
            value = data.get(original, {})
            if base in value:
                fields[native] = value[base]
            for source, target in (('MinRotator' if base == 'BasedRotator' else 'MinVector', random_min),
                                   ('MaxRotator' if base == 'BasedRotator' else 'MaxVector', random_max)):
                if source in value:
                    fields[target] = value[source]
        for param in data.get('RandomScalarParams', []):
            value = param['Value']
            mode = value.get('ScalarType', '')
            if mode.endswith('::Random'):
                fields['InstanceParameters'].append({'ParameterName': param['Key'], 'Minimum': value['RandomMin'],
                    'Maximum': value['RandomMax'], 'bRandomInteger': value.get('bRandomFloat') is False})
            elif 'DefaultValue' in value:
                fields['InstanceParameters'].append({'ParameterName': param['Key'], 'Minimum': value['DefaultValue'],
                                                      'Maximum': value['DefaultValue']})
        curve = source_package(data.get('OpacityCurve'))
        curves = ['FC_Decal_FadeOut', 'FC_Decal_FadeOut_SlowIn', 'FC_Decal_FastIn_SlowOut', 'FC_Decal_FadeOut_Fast']
        if curve:
            fields['DecalOpacityCurveIndex'] = curves.index(curve.split('/')[-1])
        common.update(notify_fields=fields, resolution={'authorable': True, 'mode': 'decal',
                      'source_material': package, 'native_destination': destination, 'source_opacity_curve': curve},
                      success_condition={'enabled': fields['bOnAttackSuccessed'],
                          'source_explicit': 'bOnAttackSuccessed' in props},
                      decal_adapters={'floor_projection': 'Project adapter: decals project to actual grounded substrate and sampled snow surface.',
                          'missing_blood_success_flag': 'Guard blood by confirmed damage when source CDO default is absent; original default unknown.',
                          'randomization': 'Source Based + uniform signed endpoint offsets; original native sampler code unconfirmed.',
                          'curve_time': 'Evaluate original cubic/linear keys over normalized lifespan; original native evaluation code unconfirmed.'})
        assert set(fields) <= header_fields, set(fields) - header_fields
        events.append(common)
        continue
    if row['notify_type'] != 'xxAnimNotifyState_Particle':
        common['status'] = 'original_deformation_owner' if row['notify_type'] == 'xxAnimNotifyState_SurfaceTrailDeepSnow' else 'source_notify_runtime_unsupported'
        common['reason'] = {'xxAnimNotifyState_SurfaceTrailDeepSnow': 'Original render-target snow writing must not become an unconditional particle or duplicate existing deformation.',
                            'xxAnimNotifyState_Decal': 'Exact source decal/random/lifetime/opacity data retained; current thin Cascade notify does not author decals.',
                            'xxAnimNotify_WaterSurfaceTrail': 'Original water-surface feedback requires actual water intersection; current thin Cascade notify has no water owner.'}[row['notify_type']]
        unsupported.append(common)
        continue
    props, info = row['notify_properties_raw'], row['notify_properties_raw']['ParticleInfo']
    fields = {'EventId': common['event_id'], 'SourcePackage': row['source_package'], 'SourceField': row['field']}
    explicit = {'AttachSocketName': 'SourceSocket', 'RelativeLocation': 'RelativeLocation', 'RelativeRotation': 'RelativeRotation',
                'CustomTimeDilation': 'CustomTimeDilation', 'bAttached': 'bAttached', 'bAbsoluteRotation': 'bAbsoluteRotation',
                'TranslucencySortPriority': 'TranslucencySortPriority', 'bSpawnOnFloor': 'bSpawnOnFloor'}
    for original, target in explicit.items():
        if original in info:
            fields[target] = info[original]
    for field in ('bDestroyOnNotifyEnd', 'bDestroyOnNotifyEndDeactived', 'bDestroyOnAnimEnd', 'bOnAttackSuccessed', 'bOnlyStartAttach', 'OnNotifyEndDeattach'):
        if field in props and field in header_fields:
            fields[field] = props[field]
    if 'Scale3D' in info:
        fields['Scale3D'], scale_provenance = info['Scale3D'], 'explicit Scale3D; legacy scalar not multiplied'
    elif 'Scale' in info:
        fields['Scale3D'], scale_provenance = dict.fromkeys(('X', 'Y', 'Z'), info['Scale']), 'scalar-only source converted uniformly'
    else:
        scale_provenance = 'source absent; adapter class default, original CDO default unknown'
    float_raw = info.get('ParticleFloatParams', [])
    fields['InstanceParameters'] = [parameter(p) for p in float_raw if p.get('bUseOverrideParam') is True and parameter(p)]
    physical_parameters = [{'surface_raw': r['Key'], 'surface_numeric': physical_surface(r['Key']),
                            'raw': r['Value'], 'enabled_parameters': [parameter(p) for p in r['Value'].get('Values', []) if p.get('bUseOverrideParam') is True and parameter(p)]}
                           for r in info.get('ParticlePhysicalFloatParams', [])]
    corrections = props.get('CorrectionInfos', [])
    if props.get('CorrectionBoneName') and corrections and 'TM' in corrections[0]:
        tm = corrections[0]['TM']
        fields.update(bUseSourceCorrection=True, CorrectionBoneName=props['CorrectionBoneName'],
                      SourceCorrectionTransform={'Translation': tm.get('Translation'),
                                                 'Rotation': {k: tm['Rotation'][k] for k in ('X', 'Y', 'Z', 'W')},
                                                 'Scale3D': tm.get('Scale3D')})
        common['correction_adapter'] = 'First source snapshot anchors source-local effect via source bone inverse * current bone; an explicit project adapter, not recovered original interpolation code.'
    winter = info.get('bUseEnvVolumeDependent') is True and source_package(info.get('EnvVolumeBundleAsset')) == 'BBQ/Content/Art/ArtRendering/AR_PostProcessBundle/EnvVolumeBundle_Winter'
    if winter:
        fields['bWinterOnly'] = True
        common['winter_adapter'] = 'Serialized EnvVolumeBundle_Winter condition preserved; current adapter identifies winter through the existing snow owner. Bundle internal original volume rules are unavailable.'
    mode = info.get('ParticleMode', 'direct_reference')
    resolved = {'mode': mode, 'authorable': False}
    if mode == 'direct_reference' or 'Particle' in info and mode not in ('MaterialEffect', 'StatusEffectParticle'):
        selected = particle(info.get('Particle'))
        resolved['particle'] = selected
        if selected['status'] == 'available_cascade':
            fields['ParticleTemplate'], resolved['authorable'] = selected['native_destination'], True
    elif mode in ('MaterialEffect', 'StatusEffectParticle'):
        routes, data_source = route_rows(info.get('EffectData'))
        resolved['data_source'] = data_source
        if mode == 'StatusEffectParticle':
            selected = [r for r in routes if r['raw_entry'].get('Attribute') == 'EStatusEffectAttribute::None']
            resolved['unselected_status_variants'] = [r for r in routes if r not in selected]
            resolved['selection_condition'] = 'None only; no current status/enchant producer was established. Other attributes remain unimplemented.'
            resolved['selected_source_rows'] = selected
            if len(selected) == 1:
                template = particle(selected[0]['raw_entry'].get('Particle'))
                resolved['particle'] = template
                if template['status'] == 'available_cascade':
                    fields['ParticleTemplate'], resolved['authorable'] = template['native_destination'], True
            else:
                resolved['status'] = 'missing_or_ambiguous_None_route'
        else:
            fields['SurfaceRoutes'] = []
            resolved['surface_routes'], resolved['unavailable_surface_routes'] = [], []
            for route in routes:
                raw = route['raw_entry']
                number = physical_surface(raw.get('SurfaceType'))
                template = particle(raw.get('Particle') or raw.get('NiagaraParticle'))
                entry = {'surface_raw': raw.get('SurfaceType'), 'surface_numeric': number, 'particle': template,
                         'source_field': route['field'], 'source_sha256': route['source_sha256'], 'raw_entry': raw}
                resolved['surface_routes'].append(entry)
                if number is not None and template['status'] == 'available_cascade':
                    fields['SurfaceRoutes'].append({'Surface': number, 'ParticleTemplate': template['native_destination']})
                else:
                    resolved['unavailable_surface_routes'].append(entry)
            assert len({r['Surface'] for r in fields['SurfaceRoutes']}) == len(fields['SurfaceRoutes'])
            resolved['authorable'] = bool(fields['SurfaceRoutes'])
            resolved['surface_contract'] = 'Original EPhysicalSurface numbers preserved; no project physical-material remap or arbitrary override is authored.'
    # Apply only explicitly enabled physical-surface float overrides. A sparse
    # direct/status route keeps the primary particle as fallback on other surfaces.
    for conditional in physical_parameters:
        number, parameters = conditional['surface_numeric'], conditional['enabled_parameters']
        if number is None or not parameters:
            continue
        surface_routes = fields.setdefault('SurfaceRoutes', [])
        route = next((r for r in surface_routes if r['Surface'] == number), None)
        if route is None and fields.get('ParticleTemplate'):
            route = {'Surface': number, 'ParticleTemplate': fields['ParticleTemplate']}
            surface_routes.append(route)
        if route is not None:
            route.setdefault('FloatParameters', []).extend(parameters)
        else:
            conditional['authoring_limit'] = 'No available particle route for this original physical surface; parameter data retained without inventing a particle fallback.'
    common.update(notify_fields=fields, resolution=resolved, scale_provenance=scale_provenance,
                  particle_float_parameters_raw=float_raw, conditional_surface_parameters=physical_parameters,
                  source_cdo_defaults_unknown=[v for k, v in explicit.items() if k not in info] + [k for k in ('Scale3D', 'bDestroyOnNotifyEnd', 'bDestroyOnNotifyEndDeactived', 'bDestroyOnAnimEnd', 'bOnAttackSuccessed') if k not in info and k not in props],
                  unrepresented_semantics={k: props[k] for k in ('bTopOwner', 'bOnlyStartAttach', 'OnNotifyEndDeattach', 'bDontDamagerSuperArmour', 'BattleEffectIndex') if k in props and k not in header_fields},
                  particle_info_unrepresented={k: info[k] for k in ('bApplyBaseScale',) if k in info},
                  success_condition={'enabled': props.get('bOnAttackSuccessed') is True,
                                     'producer_contract': 'ASC confirmed applied effect: SourceObject=executing ability, KZAttackHPDamage<0, sampled KZAttackMontageTime/Instance/Execution provenance; retained current-execution actual hit can enable a later source window. BattleEffectIndex mapping remains an adapter; never infer a hit from animation alone.'})
    assert set(fields) <= header_fields, set(fields) - header_fields
    assert common['end_time'] >= common['start_time']
    events.append(common)

assert len(events) == 347 and len(unsupported) == 85 and len(skipped) == 31
assert len({e['event_id'] for e in events + unsupported}) == len(events + unsupported)
assert sum(e['success_condition']['enabled'] for e in events) == 140
result = {'schema': 'KZ_PlayerAttackVFX_PreparedPlaybackPlan_20261008_V1', 'status': 'prepared_not_authored',
          'source_inputs': {str(p.relative_to(ROOT)): sha(p) for p in (AUDIT / 'MappedOriginalEffectWindows.json', AUDIT / 'CurrentSegmentTimingPlan.json', META / 'AssetManifest.json', META / 'EffectRoutingContracts.json')},
          'notify_header': {'path': str(HEADER), 'sha256': sha(HEADER)},
          'authoring_contract': {'fields_use_cpp_property_names': True, 'paired_start_end_share_EventId': True,
                                'bEndEvent_start': False, 'bEndEvent_stop': True, 'all_times_seconds': True,
                                'missing_source_fields_use_adapter_defaults_original_CDO_unknown': True,
                                'source_correction_first_snapshot_is_adapter': True},
          'events': events, 'unsupported_source_windows': unsupported, 'skipped_source_windows': skipped,
          'native_particle_assets': native_assets,
          'summary': {'particle_windows': 297, 'decal_windows': 50, 'authorable_windows': len(events),
                      'success_only_windows': 140, 'unsupported_types': dict(Counter(e['notify_type'] for e in unsupported)),
                      'skipped_reasons': dict(Counter(e['reason'] for e in skipped)), 'native_particle_templates': len(native_assets),
                      'enabled_unconditional_float_parameter_assignments': sum(len(e['notify_fields']['InstanceParameters']) for e in events),
                      'enabled_conditional_surface_parameter_assignments': sum(len(r.get('FloatParameters', [])) for e in events for r in e['notify_fields'].get('SurfaceRoutes', [])),
                      'unavailable_surface_route_occurrences': sum(len(e['resolution'].get('unavailable_surface_routes', [])) for e in events),
                      'conditional_physical_parameter_windows': sum(bool(e.get('conditional_surface_parameters')) for e in events)},
          'limits': ['OverFury B_01 matching original start events remain unconfirmed; unrelated Yaksha Start AC rejected.',
                     'Available Cascade resolution is based on manifest source_type and native file presence/hash; authoring must still validate loaded Unreal asset classes.',
                     'No full original custom CDO or notify code recovered; absent defaults and adapter interpretations remain explicit.',
                     'Physical parameter arrays are conditional and not flattened into unconditional InstanceParameters.',
                     'Prepared metadata is not proof of authoring, successful hit producer, shader fidelity, PIE, GPU cost, or shipping performance.']}
(OUT / 'PreparedPlaybackPlan.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result['summary']))
