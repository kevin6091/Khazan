"""Prepare the exact current Grapple5/Brutal2 scope; preserve the existing 347 plan."""
import ast
import bisect
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
HEADER = WORK / 'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = sha(OUT / 'PreparedPlaybackPlan.json')
stamina = ROOT / 'Metadata/MonsterStamina_20261008'
animation, saved = read(stamina / 'AnimationPlan.json'), read(stamina / 'MainSavedReload_ConcurrentBuild.json')
assert saved['success'] and not saved['dirty_content'] and not saved['dirty_map']
delivery = read(stamina / 'PreparedDeliveryManifest.json')
baselines = {r['relative']: r['after'] for r in delivery['rows'] if '/DAS/BrutalAttack/' in r['relative']}
assert len(baselines) == 7
for relative, digest in baselines.items(): assert sha(ROOT / relative) == sha(WORK / relative) == digest
clips = {r['proposed_duplicate_path']: r for r in animation['player_clips']}
native = {r['copy'].split('.')[0]: r for r in saved['clips']}
catalog = read(META / 'AnimationEffectNotifies.json')
windows, source_timing, segments = [], {}, []

def interpolate(time, positions):
    index = bisect.bisect_right([r['T_Original'] for r in positions], time)
    if index == 0: return positions[0]['T_Dilation']
    if index == len(positions): return positions[-1]['T_Dilation']
    a, b = positions[index - 1:index + 1]
    return a['T_Dilation'] + (time - a['T_Original']) / (b['T_Original'] - a['T_Original']) * (b['T_Dilation'] - a['T_Dilation'])

montages = [m for m in saved['montages'] if '/DAS/BrutalAttack/AM_DAS_Brutal' in m['asset']]
assert len(montages) == 2
for montage in montages:
    for index, segment in enumerate(montage['sections']):
        key = segment['clip'].split('.')[0]
        clip, observed = clips[key], native[key]
        assert observed['read_options']['rate_scale'] == segment['play_rate'] == segment['loops'] == 1
        source_package = clip['original_package']
        file = META / 'Bindings/Source' / (source_package + '.json')
        props = next(e['Properties'] for e in read(file) if e.get('Type') == 'AnimComposite')
        source_timing[source_package] = {'source_file': file.relative_to(ROOT).as_posix(), 'sha256': sha(file), 'properties': props}
        active = clip['dilation_active_under_existing_bake_rule']
        positions = props.get('DilationCurve', {}).get('DilationAnimPositions', [])
        authored = clip['source_authored_playback_seconds']
        exact60 = clip['derived_exact60_playback_seconds']
        assert abs(observed['seconds'] - exact60) < 1e-6 and abs(segment['source_end'] - observed['seconds']) < 1e-6
        if active: assert positions and props['DilationCurve'].get('BakedDilationCurveName')
        mapping = lambda time: (interpolate(time, positions) if active else max(0, min(time, authored))) * exact60 / authored
        segments.append({'montage': montage['asset'], 'segment_index': index, 'native_segment': segment,
                         'source_package': source_package, 'dilation_applied_by_existing_bake': active,
                         'source_authored_seconds': authored, 'exact60_seconds': exact60,
                         'actual_saved_seconds': observed['seconds'], 'source_properties': props})
        for event in [r for r in catalog if r['source_package'] == source_package]:
            raw = event['event']
            start = raw['LinkValue'] + raw.get('TriggerTimeOffset', 0)
            end = raw['EndLink']['LinkValue'] + raw.get('EndTriggerTimeOffset', 0)
            a, b = mapping(start), mapping(end)
            row = {'montage': montage['asset'], 'segment_index': index, 'sequence': segment['clip'],
                   'source_package': source_package, 'source_sha256': event['source_sha256'], 'field': event['field'],
                   'notify_type': event['notify_type'], 'notify_object': event['notify_object'],
                   'native_start_sec': a, 'native_end_sec': b, 'montage_start_sec': segment['segment_start'] + a,
                   'clipped_montage_end_sec': segment['segment_start'] + min(b, segment['source_end']),
                   'within_native_segment': 0 <= a < segment['source_end'],
                   'event_raw': raw, 'notify_properties_raw': event['notify_properties'],
                   'mapping_proof': 'Exact Main saved reload hash identity; copied CompositePlayback baked source dilation, then exact60/authored quantization; no extra crop normalization.'}
            if raw['LinkValue'] == 0 and raw.get('TriggerTimeOffset', 0) < 0:
                row['boundary_adapter'] = 'Raw negative first-frame offset retained; source locator clamps to first sample, author engine endpoint offset applies.'
            windows.append(row)
# Reuse the production-plan field/routing adapters without running its 347 output writer.
builder = ROOT / 'Scripts/Art/prepare_player_attack_vfx_plan.py'
tree = ast.parse(builder.read_text(encoding='utf-8'))
manifest = {r['source_package']: r for r in read(META / 'AssetManifest.json')}
routing = read(META / 'EffectRoutingContracts.json')
header_fields = set(re.findall(r'^\s*(?:bool|float|int32|FName|FString|FVector|FRotator|FTransform|TObjectPtr<[^>]+>|TArray<[^>]+>|TEnumAsByte<[^>]+>)\s+(\w+)\s*(?:=|;)', HEADER.read_text(encoding='utf-8-sig'), re.M))
native_assets, events, unsupported, skipped = {}, [], [], []
body = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
body += [n for n in tree.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'row']
exec(compile(ast.Module(body=body, type_ignores=[]), str(builder), 'exec'), globals())
assert len(events) == 54 and len(unsupported) == 4 and not skipped
assert all(e['resolution']['authorable'] for e in events)
assert len({e['event_id'] for e in events + unsupported}) == 58
result = {'schema': 'KZ_PlayerBrutalVFX_PreparedPlaybackPlan_20261008_V1', 'status': 'prepared_not_authored',
          'events': events, 'unsupported_source_windows': unsupported, 'skipped_source_windows': skipped,
          'native_particle_assets': native_assets, 'segments': segments,
          'source_inputs': {str(p.relative_to(ROOT)): sha(p) for p in (builder, stamina / 'AnimationPlan.json', stamina / 'MainSavedReload_ConcurrentBuild.json', META / 'AnimationEffectNotifies.json', META / 'AssetManifest.json', META / 'EffectRoutingContracts.json')},
          'notify_header': {'path': str(HEADER), 'sha256': sha(HEADER)},
          'authoring_contract': read(OUT / 'PreparedPlaybackPlan.json')['authoring_contract'],
          'summary': {'authorable_windows': 54, 'particle_windows': 48, 'decal_windows': 6, 'success_only_windows': sum(e['success_condition']['enabled'] for e in events),
                      'unsupported_types': dict(Counter(e['notify_type'] for e in unsupported)), 'native_particle_templates': len(native_assets)},
          'limits': ['Original absent custom CDO flags remain unknown; same explicit existing project adapters as initial347.', 'Brutal damage currently0 unassigned; success-only16 windows need actual confirmed damage and must not play from animation alone.', 'Four original snow writes belong to existing snow owner; no duplicate unconditional particles.', 'Prepared source mapping is not runtime/original visual parity proof.']}
(OUT / 'PreparedBrutalPlaybackPlan.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(OUT / 'BrutalAssetBaseline.json').write_text(json.dumps({'sha256': baselines}, indent=2), encoding='utf-8')
combined = read(OUT / 'PreparedPlaybackPlan.json')
combined['schema'] = 'KZ_PlayerAttackVFX_CombinedPreparedPlaybackPlan_20261008_V1'
combined['events'] += events
combined['unsupported_source_windows'] += unsupported
combined['native_particle_assets'].update(native_assets)
combined['combined_inputs'] = {'original347_sha256': before, 'brutal54_sha256': sha(OUT / 'PreparedBrutalPlaybackPlan.json')}
combined['summary'].update(authorable_windows=401, particle_windows=345, decal_windows=56, success_only_windows=156)
combined['summary']['unsupported_types'] = dict(Counter(e['notify_type'] for e in combined['unsupported_source_windows']))
combined['summary']['native_particle_templates'] = len(combined['native_particle_assets'])
combined['summary']['enabled_unconditional_float_parameter_assignments'] = sum(len(e['notify_fields']['InstanceParameters']) for e in combined['events'])
combined['summary']['enabled_conditional_surface_parameter_assignments'] = sum(len(r.get('FloatParameters', [])) for e in combined['events'] for r in e['notify_fields'].get('SurfaceRoutes', []))
combined['limits'] += result['limits']
assert len(combined['events']) == 401 and len({e['event_id'] for e in combined['events']}) == 401
(OUT / 'CombinedPreparedPlaybackPlan.json').write_text(json.dumps(combined, indent=2), encoding='utf-8')
for filename, rows in [('BrutalPlaybackWindows.csv', events), ('CombinedPlaybackWindows.csv', combined['events'])]:
    with (OUT / filename).open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=['event_id', 'montage', 'segment_index', 'sequence', 'type', 'source_package', 'source_field', 'raw_start_sec', 'raw_end_sec', 'native_start_sec', 'montage_start_sec', 'montage_end_sec', 'window_seconds', 'success_only', 'socket', 'custom_time_dilation', 'particle_template', 'decal_material', 'decal_lifespan_seconds'])
        writer.writeheader()
        for row in rows:
            raw, fields = row['source']['raw_event'], row['notify_fields']
            writer.writerow({'event_id': row['event_id'], 'montage': row['montage'], 'segment_index': row['segment_index'], 'sequence': row['sequence'], 'type': row['notify_type'],
                'source_package': row['source']['package'], 'source_field': row['source']['field'],
                'raw_start_sec': raw.get('LinkValue', 0) + raw.get('TriggerTimeOffset', 0),
                'raw_end_sec': raw.get('EndLink', {}).get('LinkValue', 0) + raw.get('EndTriggerTimeOffset', 0),
                'native_start_sec': row['native_start_time'], 'montage_start_sec': row['start_time'], 'montage_end_sec': row['end_time'],
                'window_seconds': row['end_time'] - row['start_time'], 'success_only': row['success_condition']['enabled'],
                'socket': fields.get('SourceSocket', '<source absent>'), 'custom_time_dilation': fields.get('CustomTimeDilation', '<source absent>'),
                'particle_template': fields.get('ParticleTemplate', '<surface routes>'), 'decal_material': fields.get('DecalMaterial', ''), 'decal_lifespan_seconds': fields.get('DecalLifeSpan', '')})
assert sha(OUT / 'PreparedPlaybackPlan.json') == before
print(json.dumps(result['summary']))
