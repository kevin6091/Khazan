"""Read-only saved Giant SFX audit against the established source-event plan."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import os
import re
import traceback
import unreal as u

ROOT = Path(os.environ['KZ_AUDIO_MAIN'])
OUT = Path(os.environ['KZ_AUDIO_OUTPUT'])
SOURCE = ROOT / 'Saved/ImportReports/GameplayAudio_20261011'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
lib = u.EditorAssetLibrary
families = ('ApesStoneHandElite', 'Yetuga')
plan = read(SOURCE / 'AudioAuthoringPlan01.json')
bindings = read(SOURCE / 'BindingAuthor02_Persistent/Bindings.json')
by_asset = defaultdict(list)
for item in plan['events']:
    if item['family'] in families:
        by_asset[item['asset']].append(item)

report = {'success': False, 'saved_packages': 0, 'source_plan': str(SOURCE / 'AudioAuthoringPlan01.json'),
          'families': {}, 'events': [], 'combos': [], 'definitions': [], 'errors': []}
try:
    for family in families:
        report['families'][family] = {'source_events': 0, 'source_clips': 0, 'matched_events': 0,
                                      'missing_events': 0, 'extra_events': 0, 'null_sounds': 0,
                                      'wrong_cues': 0, 'time_shifts': 0, 'retimed_under_one_60hz_frame': 0,
                                      'intentional_stop_only': 0, 'only_local_or_locked': 0}
    for asset, expected in sorted(by_asset.items()):
        seq = lib.load_asset(asset)
        if not seq:
            report['errors'].append({'kind': 'missing_animation', 'asset': asset})
            continue
        current = {}
        for event in u.AnimationLibrary.get_animation_notify_events(seq):
            obj = event.get_editor_property('notify') or event.get_editor_property('notify_state_class')
            if not isinstance(obj, (u.KZAnimNotify_PlayAudio, u.KZAnimNotifyState_PlayAudio)):
                continue
            playback = obj.get_editor_property('playback') if isinstance(obj, u.KZAnimNotifyState_PlayAudio) else obj
            value = playback.get_editor_property('sound')
            text = event.export_text()
            times = re.findall(r'LinkValue=([-+0-9.eE]+)', text)
            current[obj.get_name()] = {'sound': value.get_path_name().split('.')[0] if value else None,
                                       'class': obj.get_class().get_name(),
                                       'start': float(times[-1]) if times else None,
                                       'only_local_or_locked': playback.get_editor_property('only_for_local_or_locked_target')}
        family = expected[0]['family']
        count = report['families'][family]
        count['source_clips'] += 1
        count['source_events'] += len(expected)
        wanted = {e['event_id'] for e in expected}
        for name in sorted(set(current) - wanted):
            count['extra_events'] += 1
            report['events'].append({'family': family, 'asset': asset, 'id': name,
                                     'issue': 'extra_current_audio', 'current': current[name]})
        for e in expected:
            item = current.get(e['event_id'])
            row = {'family': family, 'asset': asset, 'id': e['event_id'],
                   'source_package': e['event_package'], 'source_time': e['start'],
                   'expected_cue': e['cue'], 'current': item, 'issues': []}
            if not item:
                count['missing_events'] += 1
                row['issues'].append('missing_audio_notify')
            else:
                count['matched_events'] += 1
                if not item['sound']:
                    if not e['cue'] and e['stop_sounds']:
                        count['intentional_stop_only'] += 1
                    else:
                        count['null_sounds'] += 1
                        row['issues'].append('null_sound')
                elif item['sound'] != e['cue']:
                    count['wrong_cues'] += 1
                    row['issues'].append('wrong_cue')
                if item['start'] is None or abs(item['start'] - e['start']) > 1 / 60:
                    count['time_shifts'] += 1
                    row['issues'].append('time_shift_requires_current_playback_review')
                elif abs(item['start'] - e['start']) > .001:
                    # Prior integer-FPS animation repair moved the native link by
                    # less than one 60 Hz frame. Record it; do not undo saved timing.
                    count['retimed_under_one_60hz_frame'] += 1
                if item['only_local_or_locked']:
                    count['only_local_or_locked'] += 1
            report['events'].append(row)
    for binding in bindings['combos']:
        if not any(f in binding['asset'] for f in families):
            continue
        obj = lib.load_asset(binding['asset'])
        row = {'asset': binding['asset'], 'expected_windows': binding['windows'],
               'expected_objects': binding['objects'], 'windows': 0, 'guards': 0,
               'objects': 0, 'object_guards': 0, 'projectile_sounds': 0, 'issues': []}
        if not obj:
            row['issues'].append('missing_combo_asset')
        else:
            for node in obj.get_editor_property('nodes'):
                for window in node.get_editor_property('attack_windows'):
                    row['windows'] += 1
                    row['guards'] += int(bool(window.get_editor_property('guard_sound')))
            for obj_data in obj.get_editor_property('pattern_objects'):
                row['objects'] += 1
                row['object_guards'] += int(bool(obj_data.get_editor_property('guard_sound')))
                row['projectile_sounds'] += int(bool(obj_data.get_editor_property('projectile_sound')))
            row['new_current_windows'] = max(row['windows'] - row['expected_windows'], 0)
            if row['windows'] < row['expected_windows']:
                row['issues'].append('window_count_changed')
            if row['guards'] != row['windows']:
                row['issues'].append('attack_guard_sound_missing')
            if row['objects'] != row['expected_objects']:
                row['issues'].append('object_count_changed')
            if row['object_guards'] != row['objects']:
                row['issues'].append('object_guard_sound_missing')
        report['combos'].append(row)
    for binding in bindings['definitions']:
        if not any(f in binding['asset'] for f in families):
            continue
        obj = lib.load_asset(binding['asset'])
        sound = obj.get_editor_property('hit_reactions').get_editor_property('impact_sound') if obj else None
        report['definitions'].append({'asset': binding['asset'], 'expected_sound': binding['sound'],
                                      'current_sound': sound.get_path_name() if sound else None,
                                      'issue': None if sound and sound.get_path_name() == binding['sound'] else 'impact_sound_missing_or_changed'})
    report['success'] = not report['errors']
except Exception:
    report['errors'].append(traceback.format_exc())
    u.log_error(report['errors'][-1])
(OUT / 'GiantSFXAudit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['success'], report['errors']
