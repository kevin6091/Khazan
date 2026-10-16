"""Targeted read-only original skill audit for the four requested DevMap enemies."""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
META = ROOT / 'Content/_Art/Enemies/HeinMach/Metadata'
SOURCE = META / 'Expansion_20260909/Source'
EMPIRE = SOURCE / 'BBQ/Content/_Kazan_/Design/Monster/Human/Empire'
OUT = ROOT / 'Metadata/MonsterAI_20261006'
OUT.mkdir(parents=True, exist_ok=True)
library = {r['OriginalPackage']: r for r in csv.DictReader((META / 'AnimationStructure_20260909/AnimationLibrary.csv').open(encoding='utf-8-sig'))}
events = json.loads((META / 'Expansion_20260909/PlaybackEventTimes.json').read_text(encoding='utf-8-sig'))['events']
skill_names = {
    'Swordsman': ('EmpireSword', ['SB_EmpireSword_Early_Slash', 'SB_EmpireSword_Early_Smash', 'SB_EmpireSword_Pierce', 'SB_EmpireSword_Vigilant_FreakOut_Armed']),
    'SwordShield': ('Empire_SwordShield', ['SB_Empire_SwordShield_SwordCombo', 'SB_Empire_SwordShield_Pierce', 'SB_Empire_SwordShield_ShieldCrash', 'SB_Empire_SwordShield_Vigilant_FreakOut_Armed']),
    'HeavySwordsman': ('Empire_SwordHArmor', ['SB_EmpireSwordHArmor_SwordSwing_01', 'SB_EmpireSwordHArmor_SwordSwing_02', 'SB_EmpireSwordHArmor_SwordSwing_03', 'SB_EmpireSwordHArmor_SwordSting', 'SB_Empire_SwordHArmor_Vigilant_FreakOut_Armed']),
    'HalberdElite': ('EmpireHalberd_E', ['SB_EmpireHalberd_E_Early_Swing', 'SB_EmpireHalberd_E_Early_Pierce', 'SB_EmpireHalberd_E_Early_Push', 'SB_EmpireHalberd_E_RoundAttack', 'SB_EmpireHalberd_E_Vigilant_FreakOut_Armed']),
}

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def reference_package(ref):
    return ref['ObjectPath'].rsplit('.', 1)[0]

def summarize_skill(path):
    objects = load(path)
    cdo = next(o for o in objects if o['Name'].startswith('Default__'))
    by_id = {str(i): o for i, o in enumerate(objects)}
    steps = []
    for entry in cdo.get('Properties', {}).get('SubStateInfos', []):
        value = entry['Value']
        if not value.get('SkillAnimation'):
            continue
        package = reference_package(value['SkillAnimation'])
        clip = library.get(package)
        if not clip:
            raise RuntimeError('Missing saved playback for ' + package)
        ac = load(SOURCE / (package + '.json'))
        ac_id = {str(i): o for i, o in enumerate(ac)}
        transitions = []
        for ev in value.get('SkillEventMap', []):
            for ref in ev['Value'].get('Funcs', []):
                fn = by_id[ref['ObjectPath'].rsplit('.', 1)[1]]
                if fn['Type'] != 'xxChangeNextStepFunc':
                    continue
                event_tag_ref = ev['Value'].get('SkillTag')
                tag = by_id[event_tag_ref['ObjectPath'].rsplit('.', 1)[1]] if event_tag_ref else {}
                for timed in [e for e in events if e['source_package'] == package]:
                    notify_ref = timed.get('source_type')
                    if not notify_ref:
                        continue
                    notify = ac_id.get(notify_ref['ObjectPath'].rsplit('.', 1)[1], {})
                    if notify.get('Properties', {}).get('Index') == ev['Key']:
                        transitions.append({'event_index': ev['Key'], 'event_tag_properties': tag.get('Properties'), 'next_step': fn['Properties'].get('NextSubStateStep'), 'playback_seconds': timed['playback_start_seconds'], 'playback_end_seconds': timed['playback_end_seconds'], 'original_seconds': timed['original_start_seconds'], 'function': fn['Name'], 'notify_properties': notify.get('Properties')})
        steps.append({'step': entry['Key'], 'package': package, 'playback': clip['PlaybackAsset'], 'seconds': float(clip['Seconds']), 'fps': clip['FPS'], 'rate_scale': float(clip['RateScale']), 'anim_play_rate': value.get('AnimPlayRate'), 'anim_loop_count': value.get('AnimLoopCount'), 'blend_alpha': value.get('AnimBlendAlpha'), 'next_step': value.get('NextSubStateStep'), 'event_transitions': transitions})
    return {'skill': path.stem, 'source_file': str(path.relative_to(ROOT)).replace('\\', '/'), 'steps': steps}

report = {}
for family, (folder, names) in skill_names.items():
    found = {p.stem: p for p in (EMPIRE / folder / 'Skill').rglob('SB_*.json')}
    report[family] = {'skills': [], 'missing': [], 'cb': []}
    for name in names:
        if name not in found:
            report[family]['missing'].append(name)
            continue
        report[family]['skills'].append(summarize_skill(found[name]))
    for path in (EMPIRE / folder / 'Base_Setting').glob('CB_*.json'):
        report[family]['cb'].append({'file': str(path.relative_to(ROOT)).replace('\\', '/'), 'objects': [{'name': o['Name'], 'type': o['Type'], 'properties': {k: v for k, v in o.get('Properties', {}).items() if any(w in k.lower() for w in ('speed', 'acceleration', 'braking', 'rotation', 'capsule', 'aidata', 'scale'))}} for o in load(path) if o.get('Properties')]})
path = OUT / 'OriginalSkillAudit.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for family, data in report.items():
    print(family, 'missing=', data['missing'])
    for skill in data['skills']:
        print(' ', skill['skill'])
        for step in skill['steps']:
            print('   ', step['step'].split('::')[-1], pathlib.PurePosixPath(step['playback']).name, 'length=', round(step['seconds'], 5), 'events=', [(e['next_step'].split('::')[-1], round(e['playback_seconds'], 5)) for e in step['event_transitions']])

locomotion = {
    'Swordsman': ['AC_EmpireSword_Basic_Loop_01', 'AC_EmpireSword_Stand_F', 'AC_EmpireSword_Walk_Peace_F', 'AC_EmpireSword_Run_F', 'AC_EmpireSword_LockOnWalk_'],
    'SwordShield': ['AC_EmpireSwordShield_Basic_Loop_01', 'AC_Empire_SwordShield_Stand_F', 'AC_Empire_SwordShield_Walk_F', 'AC_Empire_SwordShield_Run_F', 'AC_Empire_SwordShield_LockOnWalk_'],
    'HeavySwordsman': ['AC_EmpireSwordHArmor_Basic_Loop_01', 'CA_M_ESwordHArmor_Stand', 'CA_M_ESwordHArmor_Walk_F', 'CA_M_ESwordHArmor_Run_F', 'CA_M_ESwordHArmor_LockOnWalk_'],
    'HalberdElite': ['AC_EmpireHalberd_Basic_Loop_01', 'CA_M_Halberd_Stand_F', 'CA_M_Halberd_Walk_Peace_F', 'CA_M_Halberd_Run_F', 'CA_M_Halberd_LockOnWalk_'],
}
plan = []
for family, data in report.items():
    family_rows = {pathlib.PurePosixPath(r['PlaybackAsset']).name.removeprefix('A_EN_PLAY_'): r['PlaybackAsset'] for r in library.values() if r['Family'] == family}
    names = locomotion[family]
    clips = {key: family_rows[name] for key, name in zip(['idle', 'combat_idle', 'walk', 'run'], names[:4])}
    clips.update({direction: family_rows[names[4] + direction] for direction in ['F', 'R', 'B', 'L']})
    attacks = []
    alert = None
    for skill in data['skills']:
        steps = skill['steps']
        by_step = {s['step']: s for s in steps}
        if 'Vigilant' in skill['skill']:
            alert = {'id': 'Alert', 'steps': [steps[0]], 'source': skill['source_file']}
            continue
        chain = []
        step = steps[0]
        while step:
            entry = dict(step)
            # Hit-dependent Push follow-up is deliberately absent: this task has no hit producer.
            usable = [e for e in step['event_transitions'] if 'AttackSuccess' not in json.dumps(e['event_tag_properties']) and e['next_step'] in by_step]
            entry['transition_seconds'] = min(e['playback_seconds'] for e in usable) if usable else None
            entry['target_step'] = usable[0]['next_step'] if usable else None
            chain.append(entry)
            step = by_step[entry['target_step']] if entry['target_step'] else None
            if step and step['step'] in [s['step'] for s in chain]:
                raise RuntimeError('Unexpected looping attack graph')
        attacks.append({'id': skill['skill'].removeprefix('SB_'), 'steps': chain, 'source': skill['source_file']})
    if family == 'HeavySwordsman':
        single = dict(attacks[1]['steps'][0]); single['transition_seconds'] = None; single['target_step'] = None
        attacks.append({'id': 'SwordSwing_02_Single', 'steps': [single], 'source': attacks[1]['source'], 'note': 'Original first-step recovery path when conditional continuation is not selected.'})
    original_cdo = next(o for o in data['cb'][0]['objects'] if o['name'].startswith('Default__'))
    capsule = next(o for o in data['cb'][0]['objects'] if o['type'] == 'CapsuleComponent')
    scale = original_cdo['properties'].get('Scale', 1.0)
    bp_name = 'BP_EN_HalberdElite' if family == 'HalberdElite' else 'BP_EN_' + family + '_U01_L01'
    distances = {'Swordsman': (350, 240, 310), 'SwordShield': (340, 230, 300), 'HeavySwordsman': (410, 285, 365), 'HalberdElite': (540, 385, 490)}[family]
    plan.append({'family': family, 'art_bp': '/Game/_Art/Enemies/HeinMach/Humanoids/' + family + '/Blueprints/' + bp_name,
                 'clips': clips, 'attacks': attacks, 'alert': alert, 'original_cb': data['cb'][0]['file'], 'original_scale': scale,
                 'capsule_half_height': capsule['properties']['CapsuleHalfHeight'] * scale,
                 'capsule_radius': capsule['properties']['CapsuleRadius'] * scale,
                 'temporary': {'walk_speed': 180.0 if family != 'HalberdElite' else 200.0, 'run_speed': 420.0,
                               'engage_distance': distances[0], 'preferred_distance': distances[1], 'attack_distance': distances[2],
                               'blend_out_seconds': 0.2, 'locomotion_blend_seconds': 0.2, 'combo_blend_seconds': 0.1}})
(OUT / 'AuthoringPlan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')

# Keep skill-local predicates/cooldowns distinct from the missing AI controller data.
# These fields are evidence, not an automatic replacement for StateTree tuning:
# a combo FindTarget range is not necessarily the AI's initial attack range.
context = {}
for family, data in report.items():
    entries = []
    for skill in data['skills']:
        state_path = ROOT / skill['source_file']
        info_path = state_path.with_name('SI_' + state_path.stem.removeprefix('SB_') + '.json')
        for source in (state_path, info_path):
            if not source.exists():
                continue
            for export_index, obj in enumerate(load(source)):
                fields = {k: v for k, v in obj.get('Properties', {}).items()
                          if any(term in k.lower() for term in ('distance', 'cooltime', 'angle', 'attackrange'))}
                if fields:
                    entries.append({'file': str(source.relative_to(ROOT)).replace('\\', '/'),
                                    'export_index': export_index, 'type': obj['Type'],
                                    'object': obj['Name'], 'fields': fields})
    context[family] = entries
(OUT / 'OriginalSkillContext.json').write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding='utf-8')
