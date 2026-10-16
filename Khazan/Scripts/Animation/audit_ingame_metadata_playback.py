"""Read-only fresh-editor audit of the source-backed InGame playback correction."""

import hashlib
import json
import pathlib
import re
import runpy
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / 'Saved/Extracted/InGame_Playback_20261002'
REPORT = ROOT / 'FreshProcessAudit.json'
API = runpy.run_path(str(PROJECT / 'Scripts/Animation/retime_ingame_from_metadata.py'), run_name='ingame_audit_helpers')
HELPERS = API['HELPERS']
PLAN = API['PLAN']
EAL = unreal.EditorAssetLibrary


def stable(value):
    return re.sub(r' \(0x[0-9A-Fa-f]+\)', '', str(value))


def assert_properties(seq, expected):
    for key, value in expected.items():
        actual = seq.get_editor_property(key)
        if isinstance(value, str):
            equal = stable(actual) == stable(value)
        else:
            equal = actual == value
        if not equal:
            raise RuntimeError('Authored property changed: ' + seq.get_path_name() + ' ' + key)


def assert_times(expected, actual):
    a, b = API['fields'](expected), API['fields'](actual)
    for key in ('LinkValue', 'SegmentBeginTime', 'SegmentLength', 'Duration', 'TriggerTimeOffset', 'EndTriggerTimeOffset'):
        if abs(float(a.get(key, 0)) - float(b.get(key, 0))) > 1e-5:
            raise RuntimeError('Saved montage timing differs: ' + key)
    for key in ('Guid', 'SectionName', 'NextSectionName', 'NotifyName', 'MontageTickType', 'TrackIndex', 'SegmentIndex'):
        if a.get(key, '0' if key in ('TrackIndex', 'SegmentIndex') else None) != b.get(key, '0' if key in ('TrackIndex', 'SegmentIndex') else None):
            raise RuntimeError('Saved montage identity differs: ' + key)
    if 'EndLink' in a:
        assert_times(a['EndLink'], b['EndLink'])


def assert_slots(expected, actual):
    if len(expected) != len(actual):
        raise RuntimeError('Saved montage slot count differs')
    for text, slot in zip(expected, actual):
        before = unreal.SlotAnimationTrack()
        before.import_text(text)
        if before.get_editor_property('slot_name') != slot.get_editor_property('slot_name'):
            raise RuntimeError('Saved montage slot name differs')
        a = list(before.get_editor_property('anim_track').get_editor_property('anim_segments'))
        b = list(slot.get_editor_property('anim_track').get_editor_property('anim_segments'))
        if len(a) != len(b):
            raise RuntimeError('Saved montage segment count differs')
        for left, right in zip(a, b):
            for key in ('start_pos', 'anim_start_time', 'anim_end_time', 'cached_play_length', 'anim_play_rate', 'looping_count'):
                if abs(float(left.get_editor_property(key)) - float(right.get_editor_property(key))) > 1e-5:
                    raise RuntimeError('Saved montage segment value differs: ' + key)
            if left.get_editor_property('anim_reference').get_path_name() != right.get_editor_property('anim_reference').get_path_name():
                raise RuntimeError('Saved montage source reference differs')


def main():
    results = []
    for row in PLAN['assets']:
        seq = unreal.load_asset(row['path'])
        if not isinstance(seq, unreal.AnimSequence):
            raise RuntimeError('Missing sequence: ' + row['path'])
        model = seq.controller.get_model_interface()
        old = row['previous']
        properties = dict(old['properties'])
        if row['action'] == 'rate_scale':
            properties['rate_scale'] = row['target_rate_scale']
        assert_properties(seq, properties)
        value = {'asset': row['path'], 'action': row['action'], 'status': 'passed'}
        if row['action'] == 'retime':
            expected = json.loads((ROOT / ('Expected_' + seq.get_name() + '.json')).read_text(encoding='utf-8'))
            assert_properties(seq, expected['properties'])
            checkpoints = {int(frame): pose for frame, pose in expected['checkpoints'].items()}
            names = [unreal.Name(name) for name in expected['tracks']]
            value.update(HELPERS['verify_replacement'](seq, row['path'], names, row['target_frames'], row['target_duration'], checkpoints, {}))
            if EAL.get_metadata_tag(seq, 'DASTimingVersion') != API['VERSION']:
                raise RuntimeError('Saved retime provenance is missing')
            if model.get_number_of_float_curves() or model.get_number_of_transform_curves():
                raise RuntimeError('Unexpected non-bone curves')
        else:
            if (API['frame_rate'](seq) != old['fps'] or int(model.get_number_of_frames()) != old['frames']
                    or int(model.get_number_of_keys()) != old['keys'] or abs(seq.get_play_length() - old['duration']) > 1e-5):
                raise RuntimeError('Preserved sequence grid/crop changed: ' + row['path'])
            if [event.export_text() for event in unreal.AnimationLibrary.get_animation_notify_events(seq)] != old['notify_events']:
                raise RuntimeError('Preserved notify data changed')
            if [str(n) for n in unreal.AnimationLibrary.get_animation_notify_track_names(seq)] != old['tracks']:
                raise RuntimeError('Preserved notify tracks changed')
        results.append(value)

    for row in PLAN['standalone']:
        source, copy = unreal.load_asset(row['source']), unreal.load_asset(row['destination'])
        model = source.controller.get_model_interface()
        frames = int(model.get_number_of_frames())
        names = list(model.get_bone_track_names())
        properties = {n: source.get_editor_property(n) for n in HELPERS['COPY_PROPERTIES']}
        # Read-only source evaluation; no outside package is saved.
        _, _, _, checkpoints = HELPERS['sample_tracks'](source, names, frames, source.get_play_length())
        value = HELPERS['verify_replacement'](copy, row['destination'], names, frames, source.get_play_length(), checkpoints, properties)
        results.append({'asset': row['destination'], 'action': 'standalone_copy', 'status': 'passed', **value})

    montages = []
    snapshots = json.loads((PROJECT / 'Saved/ImportReports/InGame_Playback_MontageSnapshot_20261002.json').read_text(encoding='utf-8'))
    for snapshot in snapshots:
        m = unreal.load_asset(snapshot['path'])
        if not isinstance(m, unreal.AnimMontage):
            raise RuntimeError('Missing montage')
        path = ROOT / ('Expected_' + m.get_name() + '.json')
        if path.exists():
            expected = json.loads(path.read_text(encoding='utf-8'))
            if abs(m.get_play_length() - expected['duration']) > 1e-5:
                raise RuntimeError('Saved montage length differs')
            actual_slots = [s.export_text() for s in m.get_editor_property('slot_anim_tracks')]
            assert_slots(expected['slots'], list(m.get_editor_property('slot_anim_tracks')))
            text = API['montage_export'](m)
            sections = re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$', text, re.MULTILINE)
            notifies = [event.export_text() for event in unreal.AnimationLibrary.get_animation_notify_events(m)]
            if len(sections) != len(expected['sections']) or len(notifies) != len(expected['notifies']):
                raise RuntimeError('Saved montage array counts differ')
            for a, b in zip(expected['sections'], sections):
                assert_times(a, b)
            for a, b in zip(expected['notifies'], notifies):
                assert_times(a, b)
            markers = re.findall(r'^\s*BranchingPointMarkers\(\d+\)=(.*)$', text, re.MULTILINE)
            events = list(unreal.AnimationLibrary.get_animation_notify_events(m))
            for marker in markers:
                fields = API['fields'](marker)
                trigger = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(events[int(fields.get('NotifyIndex', 0))])
                if abs(float(fields.get('TriggerTime', 0)) - trigger) > 1e-5:
                    raise RuntimeError('Branching point cache differs from notify time')
            montages.append({'asset': snapshot['path'], 'status': 'passed', 'remapped': True, 'sections': len(sections), 'notifies': len(notifies), 'branching_markers': len(markers)})
        else:
            montages.append({'asset': snapshot['path'], 'status': 'loaded', 'remapped': False})

    assets = [unreal.load_asset(path) for path in EAL.list_assets(PLAN['scope'], recursive=True, include_folder=False)]
    sequence_count = sum(isinstance(a, unreal.AnimSequence) for a in assets)
    montage_count = sum(isinstance(a, unreal.AnimMontage) for a in assets)
    if sequence_count != len(PLAN['assets']) + len(PLAN['standalone']) or montage_count != len(snapshots):
        raise RuntimeError('Scope inventory differs or a probe remains')
    result = {'status': 'passed', 'scope': PLAN['scope'], 'sequences': sequence_count, 'montages': montage_count,
              'retimed_sequences': sum(r['action'] == 'retime' for r in results),
              'rate_only_sequences': sum(r['action'] == 'rate_scale' for r in results),
              'copied_playbacks': len(PLAN['standalone']), 'sequence_results': results, 'montage_results': montages,
              'raw_and_compressed_checkpoints_per_retimed_sequence': 5, 'all_bones_at_each_checkpoint': True,
              'spatial_scale_modified': False, 'runtime_original_match_verified': False,
              'plan_sha256': hashlib.sha256(API['PLAN_PATH'].read_bytes()).hexdigest()}
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print({k: result[k] for k in ('status', 'sequences', 'montages', 'retimed_sequences', 'rate_only_sequences', 'copied_playbacks')})


try:
    main()
except Exception:
    REPORT.write_text(json.dumps({'status': 'failed', 'error': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
    raise
