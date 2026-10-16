"""Read saved original collision metadata; preserve source fields without runtime guesses."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAVED = ROOT / 'Saved/Extracted/InGame_Playback_20261002/Metadata'
FAMILIES = ('/WeakAtk/', '/StrongAtk/', '/DodgeAtk/', '/SpinningBeast/', '/OverFury/')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def provenance(path, package):
    return {'package': package, 'metadata_file': str(path.relative_to(ROOT)).replace('\\', '/'),
            'metadata_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    skills = []
    for p in sorted((OUT / 'Source').rglob('SI_*.json')):
        a = read(p)
        obj = next(e for e in a if e['Type'] == 'xxSkillInfo')
        props = obj.get('Properties', {})
        package = str(p.relative_to(OUT / 'Source')).replace('\\', '/').removesuffix('.json')
        skills.append({**provenance(p, package), 'export_index': a.index(obj), 'name': obj['Name'],
                       'damage_infos': props.get('DamageInfos', []),
                       'skill_input_type_raw': props.get('SkillInputType'),
                       'skill_name': props.get('SkillName'), 'attack_type_raw': props.get('AttackType')})
    skill_by_family = {}
    for s in skills:
        for f in FAMILIES:
            if f in s['package'] and (f != '/DodgeAtk/' or s['name'].endswith('_DodgeAtk')):
                skill_by_family[f] = s

    damages = []
    for p in sorted((OUT / 'Source').rglob('SD_*.json')):
        a = read(p)
        obj = next(e for e in a if e['Type'] == 'xxDamageInfo')
        props = obj.get('Properties', {})
        package = str(p.relative_to(OUT / 'Source')).replace('\\', '/').removesuffix('.json')
        damages.append({**provenance(p, package), 'export_index': a.index(obj), 'name': obj['Name'],
                        'attack_info_raw': props.get('AttackInfo'),
                        'skill_functions_raw': props.get('SkillFuncInfoMap'),
                        'all_properties_raw': props})

    composites = []
    shapes = Counter()
    descriptions = Counter()
    for p in sorted(SAVED.rglob('AC_*.json')):
        package = str(p.relative_to(SAVED)).replace('\\', '/').removesuffix('.json')
        family = next((f for f in FAMILIES if f in package), None)
        if not family:
            continue
        a = read(p)
        root = next(e for e in a if e['Type'] == 'AnimComposite')
        props = root.get('Properties', {})
        attack_exports = {str(i): (i, e) for i, e in enumerate(a)
                          if e.get('Type') in ('xxAnimNotifyState_Attack', 'xxAnimNotify_Attack')}
        windows = []
        for ni, n in enumerate(props.get('Notifies', [])):
            obj = n.get('NotifyStateClass') or n.get('Notify') or {}
            oi = obj.get('ObjectPath', '').rsplit('.', 1)[-1]
            if oi not in attack_exports:
                continue
            i, e = attack_exports[oi]
            ep = e.get('Properties', {})
            desc = ep.get('AttackIntervalDesc', '')
            start = n.get('LinkValue')
            end = n.get('EndLink', {}).get('LinkValue')
            baked = ep.get('PostCleaningAttackInfo', {}).get('AttackBoxList', [])
            keys = [{'time_seconds_raw': float(k['Key']), 'time_key_raw': k['Key'],
                     'local_center_pos_raw': k['Value']['LocalCenterPos'],
                     'local_rotator_degrees_raw': k['Value']['LocalRotator']} for k in baked]
            nonzero = any(any(abs(float(x)) > 0 for x in k['local_center_pos_raw'].values()) or
                          any(abs(float(x)) > 0 for x in k['local_rotator_degrees_raw'].values()) for k in keys)
            count_match = re.search(r'(\d+)회 공격', desc)
            interval_match = re.search(r'(\d+)msec 간격', desc)
            group_match = re.search(r'그룹(\d+)', desc)
            si = skill_by_family.get(family)
            damage_index = ep.get('DamageInfoIndex')
            dmg = None
            # Omitted index is preserved as unknown native default. The text and
            # SI index0 may inform an authoring choice but are not direct evidence.
            if si is not None and damage_index is not None and damage_index < len(si['damage_infos']):
                dmg = si['damage_infos'][damage_index]
            shapes[ep.get('Shape', 'OMITTED_NATIVE_DEFAULT_UNKNOWN')] += 1
            descriptions[desc] += 1
            windows.append({'notify_index': ni, 'attack_export_index': i,
                            'attack_export_name': e['Name'], 'attack_export_type': e['Type'],
                            'start_seconds_raw': start, 'end_seconds_raw': end,
                            'duration_seconds_raw': n.get('Duration'),
                            'trigger_time_offset_raw': n.get('TriggerTimeOffset'),
                            'end_trigger_time_offset_raw': n.get('EndTriggerTimeOffset'),
                            'notify_guid_raw': n.get('Guid'), 'notify_fields_raw': n,
                            'shape_raw': ep.get('Shape'), 'size_raw': ep.get('Size'),
                            'bone_name_raw': ep.get('BoneName'),
                            'relative_offset_raw': ep.get('RelativeOffset'),
                            'absolute_offset_raw': ep.get('AbsoluteOffset'),
                            'relative_rotation_raw': ep.get('RelativeRotatoion'),
                            'cylinder_shape_info_raw': ep.get('CylinderShapeInfo'),
                            'attack_box_component_group_raw': ep.get('AttackBoxComponentGroup'),
                            'hit_group_raw': ep.get('Group'),
                            'edit_group_interval_raw': ep.get('bEditGroupInterval'),
                            'attack_interval_description_raw': desc,
                            'attack_count_raw': ep.get('AttackCount'),
                            'attack_count_from_description': int(count_match[1]) if count_match else None,
                            'interval_milliseconds_from_description': int(interval_match[1]) if interval_match else None,
                            'group_number_from_description': int(group_match[1]) if group_match else None,
                            'damage_info_index_raw': damage_index,
                            'resolved_damage_info_reference_if_index_explicit': dmg,
                            'candidate_skill_info_package': si['package'] if si else None,
                            'baking_enabled_raw': ep.get('bBakingAttackComponent'),
                            'baked_keys': keys, 'baked_key_count': len(keys),
                            'baked_keys_contain_nonzero_transform': nonzero,
                            'baked_bounds_raw': ep.get('PostCleaningAttackInfo', {}).get('Bounds'),
                            'attack_properties_raw': {k: v for k, v in ep.items()
                                                      if k not in ('PostCleaningAttackInfo', 'BakingAttackDirections')}})
        windows.sort(key=lambda w: (w['start_seconds_raw'], w['attack_export_index']))
        composites.append({**provenance(p, package), 'name': root['Name'], 'export_index': a.index(root),
                           'family': family, 'sequence_length_raw': props.get('SequenceLength'),
                           'animation_track_raw': props.get('AnimationTrack'),
                           'composite_timing_raw': {k: v for k, v in props.items()
                                                    if 'Dilation' in k or 'SequenceLength' in k},
                           'attack_window_count': len(windows), 'attack_windows': windows})

    limits = {
        'source': 'CUE4Parse metadata from the configured local FModel snapshot; saved original AC is reused, SI/SD freshly targeted.',
        'time': 'Raw LinkValue/EndLink/Duration and baked Key are seconds in the original AnimComposite timeline. Current sequence/montage mapping must apply the actual selected segment and current timing contract; raw key*60 is not a current montage frame.',
        'units': 'Rotator fields use Unreal degree representation. Box Size half-extents in cm and offset/rotation composition are proven by116/116 reconstructed original Bounds comparisons; see BoxSemantics.json. Cylinder axis/height convention remains unverified; all34 targeted Cylinder windows lack valid baked Bounds.',
        'coordinate_frame': 'Field names LocalCenterPos/LocalRotator indicate local transforms. Original PSA/current native pose corroborate root-motion-removed ground origin already rotated to actor-forward; see CoordinateCrosscheck.json. Native reference-frame code remains unavailable. Add current BP ground-origin offset once, no second mesh yaw or metadata scale .01.',
        'damage': 'SkillPowerBonus/StaminaAttackRate are original raw integer tuning fields. Their divisors and original absolute HP/stamina damage formula are not verified. Do not call them HP points or silently divide by10000/100000. Any seeded project damage is explicit temporary balancing.',
        'omitted_properties': 'An omitted property is a native/class default, not a proven value. All raw None fields are intentionally unresolved. Authoring may use a documented assumption.',
        'baked_zero_samples': 'Some Cylinder/default shapes have two zero baked transforms despite bBakingAttackComponent. They are not evidence of a meaningful moving collider trajectory; use explicit offsets and pose verification.',
        'hit_policy': 'Duration windows and descriptions1회 공격/group numbers are directly observed. The project inference is one hit per recipient per window/shared group, with separate windows enabling multi-hit. Original C++ per-recipient dedup, trace channel/visibility obstruction, immunity/team filter and event order are not extracted.',
        'special_interval': 'SpinningBeast_UltimateSlash_Loop export5 explicitly AttackCount6 and description43msec 간격,6회 공격, window .54829955–.8s. This auxiliary action is not automatically part of current SpinningAttack01/02. Its native rounding rule is unverified.',
        'scope': 'All already saved AC under the five current-player attack families are indexed for reuse, including variants not chosen by the current project. This is not new broad FModel extraction and does not mean every variant should be implemented.'
    }
    result = {'schema': 1, 'utc': datetime.now(timezone.utc).isoformat(), 'limitations_and_contracts': limits,
              'composites': composites, 'skills': skills, 'damages': damages,
              'summary': {'composite_count': len(composites),
                          'attack_window_count': sum(c['attack_window_count'] for c in composites),
                          'baked_key_count': sum(w['baked_key_count'] for c in composites for w in c['attack_windows']),
                          'skill_count': len(skills), 'damage_count': len(damages),
                          'shape_counts': dict(shapes), 'interval_description_counts': dict(descriptions)}}
    write('SourceAttackWindows.json', result)
    write('ExtractionEvidence.json', {'utc': result['utc'], 'summary': result['summary'],
                                   'request_files': [str(p.relative_to(ROOT)).replace('\\', '/') for p in OUT.glob('*Requests.json')],
                                   'extractor': 'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.exe',
                                   'read_only_source_and_assets': True, 'native_policy_verified': False,
                                   'limitations_and_contracts': limits})
    print(json.dumps(result['summary'], ensure_ascii=True))


if __name__ == '__main__':
    main()
