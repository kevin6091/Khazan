"""Targeted cached metadata only; emits data for the Work-only definition author."""
from pathlib import Path
import bisect
import collections
import csv
import hashlib
import importlib.util
import json
import sys

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = BASE / 'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source'

def read(relative):
    return json.loads((BASE / relative).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ref_package(ref):
    return (ref or {}).get('ObjectPath', '').rsplit('.', 1)[0]

spec = importlib.util.spec_from_file_location('box_semantics', BASE / 'Metadata/PlayerAttackCollision_20261008/Original/check_box_semantics.py')
box = importlib.util.module_from_spec(spec)
spec.loader.exec_module(box)

old = read('Metadata/MonsterAI_20261006/AuthoringPlan.json')
new = read('Metadata/EnemyAnimationOrganization_20261007/AttackExpansionPlan.json')
renames = {r['old']: r['new'] for r in read('Metadata/EnemyAnimationOrganization_20261007/MontageRenameApplied.json')}
library = list(csv.DictReader((BASE / 'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv').open(encoding='utf-8-sig', newline='')))
game_clips = {(r['Family'], r['OriginalPackage']): r['CurrentAsset'] for r in library if '/Animations/InGame/Attack/' in r['CurrentAsset']}
manifest = {r['source_package']: r for r in read('Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AnimationImportManifest.json') if r.get('kind') == 'PlaybackClip'}
events = {(e['source_package'], e['notify_index']): e for e in read('Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/PlaybackEventTimes.json')['events']}
sources = {}

def source(package):
    if package in sources:
        return sources[package]
    path = SOURCE / (package + '.json')
    exports = json.loads(path.read_text(encoding='utf-8-sig'))
    props = exports[0]['Properties']
    imp = manifest[package]
    table = (props.get('DilationCurve') or {}).get('DilationAnimPositions') or []
    xs = [float(p['T_Original']) for p in table]
    ys = [float(p['T_Dilation']) for p in table]
    def mapped(t):
        if not imp.get('dilation_applied') or not xs:
            return t
        if t <= xs[0]:
            return ys[0]
        if t >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, t) - 1
        return ys[i] + (ys[i+1] - ys[i]) * (t - xs[i]) / (xs[i+1] - xs[i])
    windows = []
    for ni, notify in enumerate(props.get('Notifies', [])):
        ref = (notify.get('NotifyStateClass') or {}).get('ObjectPath', '')
        if not ref:
            continue
        ei = int(ref.rsplit('.', 1)[1])
        export = exports[ei]
        if export.get('Type') != 'xxAnimNotifyState_Attack':
            continue
        p = export.get('Properties') or {}
        raw_start = float(notify['LinkValue'])
        raw_end = float((notify.get('EndLink') or {}).get('LinkValue', raw_start + notify.get('Duration', 0)))
        event = events.get((package, ni))
        start = event['playback_start_seconds'] if event else mapped(raw_start)
        end = event['playback_end_seconds'] if event else mapped(raw_end)
        clean = p.get('PostCleaningAttackInfo') or {}
        keys = [{'time_seconds_raw': float(k['Key']), 'local_center_pos_raw': (k.get('Value') or {}).get('LocalCenterPos'),
                 'local_rotator_degrees_raw': (k.get('Value') or {}).get('LocalRotator')} for k in clean.get('AttackBoxList', [])]
        w = {'notify_index': ni, 'attack_export_index': ei, 'attack_export_name': export['Name'],
             'original_window_seconds': [raw_start, raw_end], 'baked_window_seconds': [start, end],
             'shape_raw': p.get('Shape'), 'size_raw': p.get('Size'), 'relative_offset_raw': p.get('RelativeOffset'),
             'absolute_offset_raw': p.get('AbsoluteOffset'), 'relative_rotation_raw': p.get('RelativeRotatoion'),
             'baked_bounds_raw': clean.get('Bounds'), 'baked_keys': keys, 'attack_properties_raw': p,
             'original_absolute_HP_damage': None, 'original_absolute_stamina_damage': None,
             'author_supported': False, 'skip_reason': 'Shape/center/height convention not established; AttackDirections is not collision center geometry.'}
        if w['shape_raw'] == 'EAttackShape::AttackBoxComponent' and keys and (w['baked_bounds_raw'] or {}).get('IsValid'):
            models = []
            for order in ('raw_then_relative', 'relative_then_raw'):
                for combined in (False, True):
                    error, mn, mx = box.bounds_error(w, rotation_order=order, offset_uses_relative=combined)
                    models.append({'rotation_order': order, 'offset_rotated_by_combined_relative_rotation': combined,
                                   'max_bounds_error_cm': error, 'calculated_bounds_min': mn, 'calculated_bounds_max': mx})
            best = min(models, key=lambda m: m['max_bounds_error_cm'])
            w['geometry_model'] = best
            w['author_supported'] = best['max_bounds_error_cm'] < .001
            w['skip_reason'] = None if w['author_supported'] else 'Reconstructed source bounds do not match within numerical tolerance.'
            w['derived_geometry_keys'] = []
            for k in keys:
                center, quaternion, unused = box.geometry(w, k, rotation_order=best['rotation_order'], offset_uses_relative=best['offset_rotated_by_combined_relative_rotation'])
                w['derived_geometry_keys'].append({'original_time_seconds': k['time_seconds_raw'], 'baked_time_seconds': mapped(k['time_seconds_raw']),
                                                   'center_cm': center, 'quaternion_xyzw': quaternion})
        windows.append(w)
    result = {'package': package, 'source_file': path.relative_to(BASE).as_posix(), 'source_sha256': sha(path),
              'dilation_applied_saved_manifest': imp.get('dilation_applied'), 'rate_scale_saved_manifest': imp.get('rate_scale'),
              'rate_scale_status': imp.get('rate_scale_status'), 'dilation_field': 'Properties.DilationCurve.DilationAnimPositions',
              'dilation_time_per_frame_seconds': (props.get('DilationCurve') or {}).get('TimePerFrame'),
              'time_mapping': 'Stored PlaybackEventTimes endpoints; original key times piecewise-linearly mapped through saved dilation table when baked manifest applies it; endpoints clamped as existing event mapper.',
              'windows': windows}
    sources[package] = result
    return result

patterns = []
for family in old:
    for attack in family['attacks']:
        patterns.append({'family': family['family'], 'id': attack['id'], 'continuous': False,
                         'montage': renames[f"/Game/Monsters/{family['family']}/Animations/AM_{attack['id']}"],
                         'steps': [{'step': s['step'].rsplit('::', 1)[-1], 'package': s['package'], 'clip': game_clips[(family['family'], s['package'])],
                                    'seconds': s['seconds'], 'rate': s.get('anim_play_rate', 1), 'loops': s.get('anim_loop_count', 1)} for s in attack['steps']]})
for attack in new:
    patterns.append({'family': attack['family'], 'id': attack['id'], 'continuous': attack['continuous'],
                     'montage': f"/Game/Monsters/{attack['family']}/Animations/Attack/Montages/Attack_{attack['id']}",
                     'steps': [{'step': s['step'], 'package': s['original_package'], 'clip': s['game_destination'], 'seconds': s['seconds'],
                                'rate': s.get('anim_play_rate', 1), 'loops': s.get('anim_loop_count', 1)} for s in attack['steps']]})
for pattern in patterns:
    pattern['definition'] = f"/Game/Monsters/{pattern['family']}/Data/DA_Combo_{pattern['id']}"
    pattern['nodes'] = []
    offset = 0
    for index, step in enumerate(pattern['steps']):
        assert step['rate'] > 0 and step['loops'] == 1, step
        node = pattern['nodes'][0] if pattern['continuous'] and pattern['nodes'] else {'node_id': 'Action' if pattern['continuous'] else step['step'],
                'section_name': 'Action' if pattern['continuous'] else step['step'], 'section_start_seconds': 0 if pattern['continuous'] else offset,
                'source_steps': [], 'windows': [], 'skipped_windows': []}
        if node not in pattern['nodes']:
            pattern['nodes'].append(node)
        node['source_steps'].append(dict(step, segment_start_seconds=offset))
        for w in source(step['package'])['windows']:
            identifier = f"{step['package']}#{w['attack_export_index']}"
            if not w['author_supported']:
                node['skipped_windows'].append({'source_window': identifier, 'reason': w['skip_reason'], 'shape_raw': w['shape_raw']})
                continue
            shift = offset - node['section_start_seconds']
            rate = step['rate']
            props = w['attack_properties_raw']
            group = props.get('Group')
            authored = {'source_window': identifier, 'start_time': shift + w['baked_window_seconds'][0] / rate,
                        'end_time': shift + w['baked_window_seconds'][1] / rate, 'shape': 'Box', 'extent': box.vec(w['size_raw']),
                        'hit_group': f"S{index}_{step['package'].rsplit('/',1)[-1]}_{group}" if group else '',
                        'hp_damage': 10, 'stamina_damage': 5, 'blockable': True, 'reaction': 'Short',
                        'source': f"{source(step['package'])['source_file']} SHA256={source(step['package'])['source_sha256']}; export={w['attack_export_index']}; notify={w['notify_index']}; Size half-extents and offset/rotation reconstructed against PostCleaningAttackInfo.Bounds; dilation baked then node-local montage seconds. Model-to-actor uses current mesh translation, no second bone transform or mesh scale/yaw. Actor frame calibration remains unverified. HP10/Stamina5 and blockable=true are project temporary settings; original absolute amounts and unblockable SD unavailable. Reaction Short fallback; HitGroup scoped by source occurrence as existing Player author.",
                        'keys': [dict(time=shift + k['baked_time_seconds'] / rate, center=k['center_cm'], quaternion=k['quaternion_xyzw']) for k in w['derived_geometry_keys']]}
            node['windows'].append(authored)
        offset += step['seconds'] / step['rate']
    pattern['montage_seconds_saved_plan'] = offset

# Current Player geometry/timing/amounts are not rewritten. Reaction is the only author change.
player_source = read('Metadata/PlayerAttackCollision_20261008/Original/SourceAttackWindows.json')
source_window = {(c['package'], w['attack_export_index']): w for c in player_source['composites'] for w in c['attack_windows']}
damages = {d['package']: d for d in player_source['damages']}
skills = {s['package']: s for s in player_source['skills']}
player_nodes = []
for node in read('Metadata/PlayerAttackCollision_20261008/AuthorReport.json')['nodes']:
    values = []
    for index, current in enumerate(node['windows']):
        original = source_window.get((current['package'], current['attack_export_index'])) or {}
        damage_ref = original.get('resolved_damage_info_reference_if_index_explicit')
        relation = 'explicit serialized DamageInfoIndex' if damage_ref else 'SD relationship unavailable'
        # Native default index0 is an inference, not a serialized original value.
        if not damage_ref:
            infos = (skills.get(original.get('candidate_skill_info_package')) or {}).get('damage_infos') or []
            if infos:
                damage_ref = infos[0]
                relation = 'candidate SI index0 inference; not confirmed original native default'
        damage = damages.get(ref_package(damage_ref))
        props = (damage or {}).get('all_properties_raw') or {}
        special = props.get('SpecialDamageAniminfo') or {}
        knock = props.get('DamagerKnockData') or {}
        reaction = 'Short'
        reason = 'No resolved strength evidence; Short project fallback.'
        if special.get('DamageStrength') == 'EDamageTypeByStrength::DamageStrong':
            reaction = 'Knockback'
            reason = 'Project three-class interpretation of original DamageStrong; does not prove original full knockdown.'
        if knock.get('BounceDatas') or (node['node_id'] == 'ChargeAttack03' and float(knock.get('KnockbackHeight', 0)) > 0):
            reaction = 'Launch'
            reason = 'Project launch selection for BounceDatas or ChargeAttack03 upward force/height. UseCurve Height/Force alone does not establish native launch.'
        values.append({'window_index': index, 'source_package': current['package'], 'attack_export_index': current['attack_export_index'],
                       'current_window_seconds_saved_author': current['current_window'], 'reaction': reaction, 'mapping_status': 'project interpretation',
                       'reason': reason, 'SD_relation': relation, 'SD_package': (damage or {}).get('package'),
                       'SD_source_file': (damage or {}).get('metadata_file'), 'SD_sha256': (damage or {}).get('metadata_sha256'),
                       'special_damage_animinfo_raw': special, 'damager_knock_data_raw': knock,
                       'amount_policy': 'Preserve actual currently loaded HPDamage/StaminaDamage; historical AuthorReport10/5 are not reapplied. Current Player requested amounts remain0.'})
    player_nodes.append({'node_id': node['node_id'], 'expected_window_count_saved_author': len(values), 'windows': values})

classification = read('Metadata/CombatReaction_20261008/AnimationClassification.json')
player_timing = classification['player']['reaction_source_clips']
flat = [w for s in sources.values() for w in s['windows']]
authored = [w for p in patterns for n in p['nodes'] for w in n['windows']]
summary = {'patterns': len(patterns), 'nodes': sum(len(p['nodes']) for p in patterns), 'unique_source_clips': len(sources),
           'original_unique_attack_windows': len(flat), 'original_shape_counts': dict(collections.Counter(str(w['shape_raw']) for w in flat)),
           'bounds_matching_box_windows': sum(w['author_supported'] for w in flat), 'authored_window_occurrences': len(authored),
           'authored_key_occurrences': sum(len(w['keys']) for w in authored), 'skipped_window_occurrences': sum(len(n['skipped_windows']) for p in patterns for n in p['nodes']),
           'player_nodes': len(player_nodes), 'player_windows': sum(len(n['windows']) for n in player_nodes),
           'player_project_reaction_counts': dict(collections.Counter(w['reaction'] for n in player_nodes for w in n['windows'])),
           'player_raw_reaction_clips': len(player_timing)}
report = {'schema': 1, 'date': '2026-10-08', 'status': 'Cached source derivation; author pending; not current UObject readback',
          'summary': summary, 'numeric_provenance': {'box_tolerance_cm': '.001 numerical QA tolerance, not gameplay tuning',
              'monster_amounts': 'Root-approved temporary project HP10/Stamina5; absolute original HP/stamina unknown',
              'blockable': 'Temporary true unless exact source SD establishes unguardable; human SD cache missing',
              'player_amounts': 'Actual loaded values preserved, requested current0; historical AuthorReport defaults not reapplied',
              'player_rate': '24 embedded timing snapshots and saved baked policy only; no fresh Unreal RateScale readback. Keep current1x and .01 spatial scale; no retime.',
              'coordinate': 'Derived source attachment-origin+offset/rotation; current mesh-relative translation provisional model-to-actor mapping. No extra source-bone transform, .01 or mesh yaw.'},
          'limitations': ['Cylinder5/Shape absent3 are skipped, not guessed. Some duplicated current pattern occurrences increase counts.',
                         'Monster source SD absolute amounts/unguardable flags unavailable; original attack count/group runtime semantics not established.',
                         'Reaction enum mappings are project interpretations of saved SD fields, not proven original fullKD/launch behavior.'],
          'monster_patterns': patterns, 'original_source_clips': list(sources.values()),
          'player_definition': '/Game/Data/ComboCommand/DA_Player_Combo_Definition', 'player_reaction_nodes': player_nodes,
          'player24_cached_timing': player_timing,
          'inputs': [{'file': p, 'sha256': sha(BASE / p)} for p in ['Metadata/MonsterAI_20261006/AuthoringPlan.json', 'Metadata/EnemyAnimationOrganization_20261007/AttackExpansionPlan.json',
                  'Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv', 'Metadata/PlayerAttackCollision_20261008/Original/SourceAttackWindows.json',
                  'Metadata/PlayerAttackCollision_20261008/AuthorReport.json', 'Metadata/CombatReaction_20261008/AnimationClassification.json']]}
(HERE / 'MonsterAttackCollisionPlan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
