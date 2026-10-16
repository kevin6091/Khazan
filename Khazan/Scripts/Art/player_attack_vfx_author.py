"""Append source-backed playback markers in the private VFX work project only."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re
import runpy
import shutil
import struct
import traceback
import unreal

WORK = Path(unreal.Paths.project_dir()).resolve()
MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008/Authoring'
OUT.mkdir(parents=True, exist_ok=True)
PLAN = json.loads((OUT.parent / 'PreparedPlaybackPlan.json').read_text(encoding='utf-8'))
BASELINE = json.loads((OUT.parent / 'WorkBaseline.json').read_text(encoding='utf-8'))['sha256']
CLASS = unreal.load_class(None, '/Script/Khazan.KZAnimNotify_CombatEffect')
assert CLASS
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
REPORT = {'status': 'running', 'project': str(WORK), 'montages': [], 'events': [], 'sequence_writes': 0,
          'data_blueprint_writes': 0, 'preserved': 'All existing notifies/sections/segments and sequence pose data.'}
ARRAY_BRIDGE = runpy.run_path(str(MAIN / 'Scripts/Animation/setup_guard_20261002.py'))['import_guard_array']
ARRAY_BRIDGE.__globals__['GUARD'] = '/Game/_Art/Player/Animation/InGame/DAS'
REPORT['notifies_serializer'] = {'source': 'Scripts/Animation/setup_guard_20261002.py:import_guard_array',
    'sha256': hashlib.sha256((MAIN / 'Scripts/Animation/setup_guard_20261002.py').read_bytes()).hexdigest(),
    'scope': 'Only the six private prepared montages; UE property serializer, no memory layout writes.'}

def vector(value):
    return unreal.Vector(*(value.get(a, 0.0) for a in ('X', 'Y', 'Z')))

def decimal(value):
    return format(Decimal(str(value)), 'f')

def transform(value):
    q = value.get('Rotation', {'X': 0, 'Y': 0, 'Z': 0, 'W': 1})
    t = value.get('Translation', {'X': 0, 'Y': 0, 'Z': 0})
    s = value.get('Scale3D', {'X': 1, 'Y': 1, 'Z': 1})
    text = '(Rotation=(' + ','.join(a+'='+decimal(q[a]) for a in 'XYZW') + '),Translation=(' + \
           ','.join(a+'='+decimal(t[a]) for a in 'XYZ') + '),Scale3D=(' + \
           ','.join(a+'='+decimal(s[a]) for a in 'XYZ') + '))'
    result = unreal.Transform()
    result.import_text(text)
    return result

def surface_text(value):
    # Custom physical surfaces are hidden enum members, so Python's cast(int)
    # cannot construct them. UE's reflected struct parser resolves their native
    # serialized names and returns the typed property value without guessing.
    name = 'SurfaceType_Default' if value == 0 else 'SurfaceType' + str(value)
    return '(Surface=' + name + ')'

def routes(values):
    result = []
    for value in values:
        row = unreal.KZCombatEffectSurfaceRoute()
        row.import_text(surface_text(value['Surface']))
        assert value['Surface'] == 0 or 'Surface=SurfaceType' + str(value['Surface']) in row.export_text()
        row.set_editor_property('ParticleTemplate', unreal.load_asset(value['ParticleTemplate']))
        assert row.get_editor_property('ParticleTemplate')
        row.set_editor_property('FloatParameters', float_parameters(value.get('FloatParameters', [])))
        result.append(row)
    return result

def float_parameters(values):
    result = []
    for value in values:
        row = unreal.KZCombatEffectFloatParameter()
        for key in ('ParameterName', 'Minimum', 'Maximum', 'bRandomInteger'):
            if key in value:
                row.set_editor_property(key, value[key])
        result.append(row)
    return result

def assign(notify, fields):
    for key, value in fields.items():
        if key in ('RelativeLocation', 'Scale3D', 'DecalSize', 'DecalSizeRandomMin', 'DecalSizeRandomMax',
                   'RelativeLocationRandomMin', 'RelativeLocationRandomMax'):
            value = vector(value)
        elif key in ('RelativeRotation', 'RelativeRotationRandomMin', 'RelativeRotationRandomMax'):
            value = unreal.Rotator(pitch=value.get('Pitch', 0), yaw=value.get('Yaw', 0), roll=value.get('Roll', 0))
        elif key in ('ParticleTemplate', 'DecalMaterial'):
            value = unreal.load_asset(value)
            assert value
        elif key == 'SourceCorrectionTransform':
            value = transform(value)
        elif key == 'SurfaceRoutes':
            value = routes(value)
        elif key == 'InstanceParameters':
            value = float_parameters(value)
        elif key == 'SurfaceOverride':
            unreal.SystemLibrary.set_byte_property_by_name(notify, key, value)
            continue
        notify.set_editor_property(key, value)

def guid(value):
    return re.search(r'Guid=([A-Fa-f0-9]+)', value).group(1)

def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]

def trigger(event):
    assert 'ABSOLUTE' in str(event.get_editor_property('link_method')).upper()
    return unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event)

def core_event(value):
    # At a same-time input collision only its data object becomes a subclass.
    # Every gameplay event field, including GUID, time, offset, name and track,
    # must remain identical. The notify's actual input name is verified separately.
    return re.sub(r'Notify="[^"]*"', 'Notify="<data-object>"', value)

def precise_time_text(event, absolute_time, offset):
    # FAnimNotifyEvent export rounds numeric text. Replace only its top-level
    # time fields before UE ImportText to retain the actual native float32 time.
    body = event.export_text()[1:-1]
    depth = 0
    quoted = False
    start = 0
    fields = []
    for index, char in enumerate(body):
        if char == '"':
            quoted = not quoted
        elif not quoted:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                fields.append(body[start:index])
                start = index + 1
    fields.append(body[start:])
    fields = [field for field in fields if field.split('=', 1)[0] not in ('LinkValue', 'TriggerTimeOffset')]
    fields.extend(['LinkValue=' + decimal(absolute_time), 'TriggerTimeOffset=' + decimal(offset)])
    return '(' + ','.join(fields) + ')'

def export(asset, filename):
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = str(filename)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(task)

try:
    groups = {}
    for event in PLAN['events']:
        groups.setdefault(event['montage'], []).append(event)
    for path, events in groups.items():
        package = path.split('.')[0]
        relative = 'Content/' + package.removeprefix('/Game/') + '.uasset'
        file = WORK / relative
        assert file.resolve().is_relative_to(WORK), 'Shared package write blocked'
        before_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        assert before_hash == BASELINE[relative], 'Preserve an independently changed private montage'
        backup = OUT / 'Before' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
        montage = unreal.load_asset(path)
        assert montage
        old_events = list(unreal.AnimationLibrary.get_animation_notify_events(montage))
        old = [n.export_text() for n in old_events]
        old_actual_triggers = {guid(n.export_text()): trigger(n) for n in old_events}
        precise_events = {}
        for n in old_events:
            match = re.search(r'(?:^\(|,)TriggerTimeOffset=([-+0-9.eE]+)', n.export_text())
            offset = f32(float(match.group(1))) if match else 0.0
            absolute_time = f32(trigger(n) - offset)
            assert f32(absolute_time + offset) == trigger(n), 'Cannot reconstruct exact original trigger'
            precise_events[guid(n.export_text())] = (absolute_time, offset)
        export(montage, OUT / (montage.get_name() + '_Before.t3d'))
        track = 'CombatFX'
        assert not unreal.AnimationLibrary.is_valid_anim_notify_track_name(montage, track)
        unreal.AnimationLibrary.add_animation_notify_track(montage, track, unreal.LinearColor(0.2, 0.6, 1.0, 1.0))
        # CompositeSections is not exposed to Python in UE 5.8. Read the same
        # absolute LinkValue fields from UE's own lossless object export.
        before_text = (OUT / (montage.get_name() + '_Before.t3d')).read_text(encoding='utf-8-sig')
        section_times = [f32(float(m.group(1)) if m else 0.0)
                         for line in before_text.splitlines() if line.strip().startswith('CompositeSections(')
                         for m in [re.search(r'\bLinkValue=([-+0-9.eE]+)', line)]]
        assert section_times
        by_trigger = {trigger(n): n for n in old_events}
        assert len(by_trigger) == len(old_events), 'Existing gameplay markers overlap'
        batches = {}
        input_replacements = {}
        for event in sorted(events, key=lambda e: (e['start_time'], e['event_id'])):
            assert 0 <= event['start_time'] < event['end_time'] <= montage.get_play_length() + 1e-5
            for ending, time in ((False, event['start_time']), (True, event['end_time'])):
                time = f32(time)
                boundary = time == 0 or time == f32(montage.get_play_length()) or any(abs(time - s) <= 1e-4 for s in section_times)
                # UE's notify endpoint offset, not a gameplay tuning delay. Starts
                # at an entry section must be after it; ends must precede it.
                offset = f32((-1 if ending else 1) * 1e-4) if boundary else 0.0
                actual = f32(time + offset)
                batch = batches.setdefault(actual, {'time': time, 'offset': offset, 'entries': []})
                batch['entries'].append((ending, event))
            REPORT['events'].append({'id': event['event_id'], 'montage': path, 'start': event['start_time'],
                                     'end': event['end_time'], 'fields': event['notify_fields']})
        marker_count = 0
        for actual, batch in sorted(batches.items()):
            original = by_trigger.get(actual)
            if original is not None:
                original_notify = original.get_editor_property('notify')
                input_name = str(original_notify.get_editor_property('notify_name'))
                notify = unreal.new_object(CLASS, outer=montage)
                notify.set_editor_property('notify_name', input_name)
                original.set_editor_property('notify', notify)
                input_replacements[guid(original.export_text())] = input_name
            else:
                notify = unreal.AnimationLibrary.add_animation_notify_event(montage, track, batch['time'], CLASS)
                marker_count += 1
                added = next(n for n in unreal.AnimationLibrary.get_animation_notify_events(montage)
                             if n.get_editor_property('notify') == notify)
                # TriggerTimeOffset is serialized but not Python-editable.
                # Struct import uses the engine's property parser and retains
                # its exact object references/GUID and other original fields.
                added_text = added.export_text()
                added_text = re.sub(r'(?<=,)TriggerTimeOffset=[-+0-9.eE]+,?', '', added_text)
                if added_text.startswith('(TriggerTimeOffset='):
                    added_text = re.sub(r'^\(TriggerTimeOffset=[-+0-9.eE]+,?', '(', added_text)
                added.import_text('(TriggerTimeOffset=' + decimal(batch['offset']) + ',' + added_text[1:])
                old_events.append(added)
                precise_events[guid(added.export_text())] = (batch['time'], batch['offset'])
            assert notify
            children = []
            for ending, event in sorted(batch['entries'], key=lambda e: (not e[0], e[1]['event_id'])):
                child = unreal.new_object(CLASS, outer=notify)
                assign(child, event['notify_fields'])
                child.set_editor_property('EventId', event['event_id'])
                child.set_editor_property('bEndEvent', ending)
                child.set_editor_property('WindowStartTime', event['start_time'])
                child.set_editor_property('WindowEndTime', event['end_time'])
                children.append(child)
            notify.set_editor_property('BatchedEffects', children)
        assert path in groups and WORK == Path(unreal.Paths.project_dir()).resolve()
        ARRAY_BRIDGE(montage, 'Notifies', [precise_time_text(n, *precise_events[guid(n.export_text())]) for n in old_events])
        # The imported markers must populate branching-point caches as well.
        refresh = '__CombatFXCacheRefresh'
        unreal.AnimationLibrary.add_animation_notify_track(montage, refresh)
        unreal.AnimationLibrary.remove_animation_notify_track(montage, refresh)
        current = [n.export_text() for n in unreal.AnimationLibrary.get_animation_notify_events(montage)]
        by_guid = {guid(n): n for n in current}
        assert all(core_event(by_guid.get(guid(n), '')) == core_event(n) if guid(n) in input_replacements
                   else by_guid.get(guid(n)) == n for n in old), 'An existing gameplay notify field changed'
        assert len(current) == len(old) + marker_count
        actual_times = [trigger(n) for n in unreal.AnimationLibrary.get_animation_notify_events(montage)]
        assert len(set(actual_times)) == len(actual_times), 'UE would drop a simultaneous branching marker'
        assert all(trigger(n) == old_actual_triggers[guid(n.export_text())]
                   for n in unreal.AnimationLibrary.get_animation_notify_events(montage)
                   if guid(n.export_text()) in old_actual_triggers), 'An existing gameplay trigger changed precision'
        assert unreal.EditorAssetLibrary.save_loaded_asset(montage, False)
        export(montage, OUT / (montage.get_name() + '_After.t3d'))
        REPORT['montages'].append({'path': path, 'relative': relative, 'before_sha256': before_hash,
            'after_sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'before_count': len(old),
            'after_count': len(current), 'added_markers': marker_count, 'source_entries': len(events)*2,
            'input_subclass_replacements': input_replacements, 'old_gameplay_fields_equal': True,
            'old_actual_trigger_times': old_actual_triggers, 'old_actual_trigger_times_equal': True,
            'unique_branching_trigger_times': True})
    REPORT['status'] = 'passed'
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
    unreal.log_error(REPORT['error'])
(OUT / 'PrivateAuthoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
print('KZ_PLAYER_ATTACK_VFX_AUTHOR_' + REPORT['status'].upper(), flush=True)
