"""Audit saved VFX packages in a fresh private editor process; never saves assets."""
from pathlib import Path
from decimal import Decimal
import collections
import hashlib
import json
import os
import re
import struct
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
EXPECTED_WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
EXPORTS = OUT / 'SavedAssetAuditExports'
REPORT = {'status': 'running', 'pid': os.getpid(), 'project': str(unreal.Paths.project_dir()),
          'asset_saves': 0, 'source_writes': 0, 'montages': [], 'checked_event_ids': 0,
          'checked_start_markers': 0, 'checked_end_markers': 0, 'field_checks': 0,
          'engine_link_cache_normalizations': [],
          'rotator_constructor_conversion': {'source': 'UE5.8 NoExportTypes.h HasNativeMake -> KismetMathLibrary.MakeRotator(float Roll,float Pitch,float Yaw)',
              'comparison': 'Exact float32 constructor result; no tolerance', 'examples': [], 'max_absolute_source_residual_degrees': 0.0},
          'fresh_process_requirement': 'Run in a NEW private editor; loaded-before flags disclose startup dependency loads.'}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
f32 = lambda value: struct.unpack('f', struct.pack('f', value))[0]
VECTOR_FIELDS = {'RelativeLocation', 'Scale3D', 'DecalSize', 'DecalSizeRandomMin', 'DecalSizeRandomMax',
                 'RelativeLocationRandomMin', 'RelativeLocationRandomMax'}
ROTATOR_FIELDS = {'RelativeRotation', 'RelativeRotationRandomMin', 'RelativeRotationRandomMax'}
NAME_FIELDS = {'EventId', 'SourceSocket', 'CorrectionBoneName'}
FLOAT_FIELDS = {'CustomTimeDilation', 'DecalLifeSpan', 'WindowStartTime', 'WindowEndTime'}
INTEGER_FIELDS = {'TranslucencySortPriority', 'DecalOpacityCurveIndex'}
OBJECT_FIELDS = {'ParticleTemplate', 'DecalMaterial'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical_asset(path):
    return path if '.' in path.rsplit('/', 1)[-1] else path + '.' + path.rsplit('/', 1)[-1]


def transform(value):
    number = lambda x: format(Decimal(str(x)), 'f')
    q = value.get('Rotation', dict(X=0, Y=0, Z=0, W=1))
    t = value.get('Translation', dict(X=0, Y=0, Z=0))
    s = value.get('Scale3D', dict(X=1, Y=1, Z=1))
    text = '(Rotation=(' + ','.join(a + '=' + number(q[a]) for a in 'XYZW') + \
           '),Translation=(' + ','.join(a + '=' + number(t[a]) for a in 'XYZ') + \
           '),Scale3D=(' + ','.join(a + '=' + number(s[a]) for a in 'XYZ') + '))'
    result = unreal.Transform()
    result.import_text(text)
    return result


def native_surface(exported, field, expected, context):
    # Custom physical-surface enum entries are hidden from Python. Inspect the
    # native serializer's enum name instead of Pythonizing the ByteProperty.
    match = re.search(r'\b' + re.escape(field) + r'=([^,)]+)', exported)
    actual = match.group(1) if match else 'SurfaceType_Default'
    name = 'SurfaceType_Default' if expected == 0 else 'SurfaceType' + str(expected)
    require(actual == name, context + ': native enum ' + actual + ' != ' + name)


def check_float_parameters(actual, expected, context):
    require(len(actual) == len(expected), context + ': parameter count')
    for index, (row, source) in enumerate(zip(actual, expected)):
        where = context + '[' + str(index) + ']'
        require(isinstance(row, unreal.KZCombatEffectFloatParameter), where + ': reflected struct type')
        require(row.get_editor_property('ParameterName') == unreal.Name(source['ParameterName']), where + ': name')
        for key in ('Minimum', 'Maximum'):
            require(row.get_editor_property(key) == f32(source.get(key, 0.0)), where + ': ' + key)
        require(row.get_editor_property('bRandomInteger') is source.get('bRandomInteger', False), where + ': integer policy')


def check_routes(actual, expected, context):
    require(len(actual) == len(expected), context + ': route count')
    for index, (row, source) in enumerate(zip(actual, expected)):
        where = context + '[' + str(index) + ']'
        require(isinstance(row, unreal.KZCombatEffectSurfaceRoute), where + ': reflected struct type')
        native_surface(row.export_text(), 'Surface', source['Surface'], where)
        resource = row.get_editor_property('ParticleTemplate')
        require(isinstance(resource, unreal.ParticleSystem), where + ': Cascade resource type')
        require(resource.get_path_name() == canonical_asset(source['ParticleTemplate']), where + ': resource path')
        check_float_parameters(row.get_editor_property('FloatParameters'), source.get('FloatParameters', []), where)


def check_fields(notify, fields, context, exported_properties):
    for key, expected in fields.items():
        where = context + '.' + key
        if key == 'SurfaceOverride':
            native_surface(exported_properties, key, expected, where)
            REPORT['field_checks'] += 1
            continue
        actual = notify.get_editor_property(key)
        if key in VECTOR_FIELDS:
            require(isinstance(actual, unreal.Vector), where + ': FVector type')
            for axis in 'XYZ':
                require(getattr(actual, axis.lower()) == float(expected.get(axis, 0.0)), where + ': ' + axis)
        elif key in ROTATOR_FIELDS:
            require(isinstance(actual, unreal.Rotator), where + ': FRotator type')
            for axis in ('Pitch', 'Yaw', 'Roll'):
                raw = float(expected.get(axis, 0.0))
                engine_expected = f32(raw)
                observed = getattr(actual, axis.lower())
                require(observed == engine_expected, where + ': ' + axis + ' actual=' + repr(observed) + ' engine_expected=' + repr(engine_expected))
                residual = observed - raw
                conversion = REPORT['rotator_constructor_conversion']
                conversion['max_absolute_source_residual_degrees'] = max(conversion['max_absolute_source_residual_degrees'], abs(residual))
                if residual != 0.0 and len(conversion['examples']) < 8:
                    conversion['examples'].append({'field': where + '.' + axis, 'source_decimal': raw,
                        'actual': observed, 'expected_constructor_float32': engine_expected, 'actual_minus_source_degrees': residual})
        elif key == 'SourceCorrectionTransform':
            require(isinstance(actual, unreal.Transform), where + ': FTransform type')
            require(actual.export_text() == transform(expected).export_text(), where + ': native transform roundtrip')
        elif key == 'SurfaceRoutes':
            check_routes(actual, expected, where)
        elif key == 'InstanceParameters':
            check_float_parameters(actual, expected, where)
        elif key in OBJECT_FIELDS:
            expected_type = unreal.ParticleSystem if key == 'ParticleTemplate' else unreal.MaterialInterface
            require(isinstance(actual, expected_type), where + ': reflected resource class')
            require(actual.get_path_name() == canonical_asset(expected), where + ': resource path')
        elif key in NAME_FIELDS:
            require(isinstance(actual, unreal.Name), where + ': FName type')
            require(actual == unreal.Name(expected), where + ': FName value')
        elif key in FLOAT_FIELDS:
            require(isinstance(actual, float) and actual == f32(expected), where + ': exact float32')
        elif key in INTEGER_FIELDS:
            require(type(actual) is int and actual == expected, where + ': int32 value')
        elif type(expected) is bool:
            require(type(actual) is bool and actual is expected, where + ': bool value')
        elif isinstance(expected, str):
            require(type(actual) is str and actual == expected, where + ': FString value')
        else:
            raise AssertionError(where + ': unhandled expected reflection type')
        REPORT['field_checks'] += 1


def export(asset, path):
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = str(path)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.ObjectExporterT3D()
    require(unreal.Exporter.run_asset_export_task(task), 'Fresh saved T3D export failed: ' + str(path))
    return path.read_text(encoding='utf-8-sig')


def event_lines(text):
    result = {}
    for line in text.splitlines():
        if line.strip().startswith('Notifies('):
            event = re.sub(r'^\s*Notifies\(\d+\)=', '', line)
            guid = re.search(r'\bGuid=([A-Fa-f0-9]+)', event)
            require(guid is not None, 'Exported notify is missing GUID')
            require(guid.group(1) not in result, 'Exported notify GUID is duplicated')
            result[guid.group(1)] = event
    return result


def object_properties(text):
    stack, properties, classes = [], {}, {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('Begin Object'):
            name = re.search(r'\bName="([^"]+)"', stripped)
            require(name is not None, 'Unnamed native T3D object')
            stack.append(name.group(1))
            properties.setdefault(stack[-1], [])
            cls = re.search(r'\bClass=([^ ]+)', stripped)
            if cls:
                classes[stack[-1]] = cls.group(1)
        elif stripped == 'End Object':
            stack.pop()
        elif stack:
            properties[stack[-1]].append(stripped)
    return {name: '\n'.join(lines) for name, lines in properties.items()}, classes


def gameplay_core(text):
    return re.sub(r'\bNotify="[^"]*"', 'Notify="<data-object>"', text)


def top_fields(text):
    body = text[1:-1]
    depth, quoted, start, fields = 0, False, 0, []
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
    return fields


def field_map(text):
    return dict(field.split('=', 1) for field in top_fields(text) if '=' in field)


def exported_slot_segments(text, slot_index):
    line = next(line.strip() for line in text.splitlines() if line.strip().startswith('SlotAnimTracks(' + str(slot_index) + ')='))
    marker = 'AnimSegments=('
    start = line.index(marker) + len(marker)
    depth, quoted, end = 1, False, start
    while depth:
        char = line[end]
        if char == '"':
            quoted = not quoted
        elif not quoted:
            depth += (char == '(') - (char == ')')
        end += 1
    return [field_map(segment) for segment in top_fields('(' + line[start:end - 1] + ')')]


def accept_link_cache_normalization(montage, guid, old, fresh, before_text, fresh_text):
    old_fields, new_fields = field_map(old), field_map(fresh)
    require(old_fields.get('LinkMethod', 'Absolute') == new_fields.get('LinkMethod', 'Absolute') == 'Absolute',
            'Only Absolute links permit the proven load cache normalization: ' + guid)
    old_cache = old_fields.pop('SegmentBeginTime', '0.000000')
    new_cache = new_fields.pop('SegmentBeginTime', '0.000000')
    require(old_cache != new_cache and old_fields == new_fields,
            'Gameplay fields differ beyond SegmentBeginTime: ' + guid)
    slot = int(old_fields.get('SlotIndex', '0'))
    segment = int(old_fields.get('SegmentIndex', '-1'))
    require(segment >= 0, 'Cache normalization needs a valid original segment: ' + guid)
    old_segments = exported_slot_segments(before_text, slot)
    new_segments = exported_slot_segments(fresh_text, slot)
    require(old_segments == new_segments, 'Cache normalization cannot change saved slot/segment data: ' + guid)
    exported_start = old_segments[segment].get('StartPos', '0.000000')
    require(float(new_cache) == float(exported_start), 'Fresh cache is not the unchanged slot StartPos: ' + guid)
    # SlotAnimTracks is BlueprintReadOnly and readable, unlike protected
    # FAnimLinkableElement time/cache properties. Read the actual saved float.
    native_slot = montage.get_editor_property('slot_anim_tracks')[slot]
    native_segment = native_slot.get_editor_property('anim_track').get_editor_property('anim_segments')[segment]
    native_start = native_segment.get_editor_property('start_pos')
    require(format(native_start, '.6f') == format(float(exported_start), '.6f'), 'Saved native StartPos disagrees with unchanged export: ' + guid)
    REPORT['engine_link_cache_normalizations'].append({'montage': montage.get_path_name(), 'guid': guid,
        'field': 'SegmentBeginTime', 'before_export_value': old_cache, 'fresh_export_value': new_cache,
        'unchanged_slot_index': slot, 'unchanged_segment_index': segment,
        'unchanged_slot_StartPos_export': exported_start, 'real_saved_native_slot_StartPos': native_start,
        'export_precision': 'Six decimal digits; exact native BP trigger snapshot is checked separately.',
        'engine_source': 'AnimMontage.cpp PostLoad: Notify.Link before Track.ValidateSegmentTimes; AnimLinkableElement.cpp Link copies Segment.StartPos. Absolute GetTime uses LinkValue.'})


try:
    WORK = Path(unreal.Paths.project_dir()).resolve()
    require(WORK == EXPECTED_WORK, 'Only the private AttackVFX Work project is authorized')
    require(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'Do not audit during PIE')
    EXPORTS.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / 'PreparedPlaybackPlan.json'
    author_path = OUT / 'Authoring/PrivateAuthoring.json'
    PLAN = json.loads(plan_path.read_text(encoding='utf-8'))
    AUTHOR = json.loads(author_path.read_text(encoding='utf-8'))
    require(AUTHOR['status'] == 'passed', 'Authoring must have passed first')
    paths = sorted({e['montage'] for e in PLAN['events']})
    require(len(paths) == 6 and len(PLAN['events']) == 347, 'Expected six authored montages and 347 source windows')
    class_path = '/Script/Khazan.KZAnimNotify_CombatEffect'
    require(unreal.load_class(None, class_path) is not None, 'Native combat-effect class is missing')
    author_rows = {row['path']: row for row in AUTHOR['montages']}
    before_hashes = {}
    for path in paths:
        relative = author_rows[path]['relative']
        stage_file, main_file = WORK / relative, MAIN / relative
        require(stage_file.resolve().is_relative_to(WORK), 'Shared authored package rejected')
        before_hashes[relative] = {'stage': sha(stage_file), 'main': sha(main_file)}
        require(before_hashes[relative]['stage'] == author_rows[path]['after_sha256'], 'Saved package changed after authoring')
    REPORT['inputs'] = {'plan_sha256': sha(plan_path), 'authoring_sha256': sha(author_path)}
    all_ids = set()
    for path in paths:
        name = path.rsplit('.', 1)[1]
        previously_loaded = unreal.find_object(None, path) is not None
        montage = unreal.load_asset(path)
        require(isinstance(montage, unreal.AnimMontage), 'Saved montage type: ' + path)
        fresh = export(montage, EXPORTS / (name + '_FreshSaved.t3d'))
        before = (OUT / 'Authoring' / (name + '_Before.t3d')).read_text(encoding='utf-8-sig')
        after = (OUT / 'Authoring' / (name + '_After.t3d')).read_text(encoding='utf-8-sig')
        before_events, fresh_events = event_lines(before), event_lines(fresh)
        old_objects, old_classes = object_properties(before)
        fresh_objects, _ = object_properties(fresh)
        native_events = list(unreal.AnimationLibrary.get_animation_notify_events(montage))
        native_by_guid = {re.search(r'\bGuid=([A-Fa-f0-9]+)', e.export_text()).group(1): e for e in native_events}
        replacements = author_rows[path]['input_subclass_replacements']
        original_triggers = author_rows[path]['old_actual_trigger_times']
        require(set(original_triggers) == set(before_events), name + ': original exact trigger snapshot GUID coverage')
        require(author_rows[path]['old_actual_trigger_times_equal'] is True, name + ': author original trigger preservation failed')
        for guid, old in before_events.items():
            require(guid in fresh_events and guid in native_by_guid, name + ': missing original gameplay GUID ' + guid)
            actual_old_trigger = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(native_by_guid[guid])
            expected_old_trigger = original_triggers[guid]
            require(actual_old_trigger == expected_old_trigger,
                    name + ': original gameplay trigger changed GUID=' + guid +
                    ' actual=' + repr(actual_old_trigger) + ' expected_snapshot=' + repr(expected_old_trigger) +
                    ' residual_seconds=' + repr(actual_old_trigger - expected_old_trigger))
            old_core = gameplay_core(old) if guid in replacements else old
            fresh_core = gameplay_core(fresh_events[guid]) if guid in replacements else fresh_events[guid]
            if old_core != fresh_core:
                accept_link_cache_normalization(montage, guid, old_core, fresh_core, before, fresh)
            old_ref = re.search(r'\bNotify="[^\']*\'([^\']+)\'"', old)
            require(old_ref is not None, name + ': unsupported original notify reference')
            old_name = old_ref.group(1).rsplit(':', 1)[-1]
            original_name = re.search(r'^NotifyName="([^"]*)"$', old_objects.get(old_name, ''), re.M)
            native_notify = native_by_guid[guid].get_editor_property('notify')
            if original_name:
                require(native_notify.get_editor_property('notify_name') == unreal.Name(original_name.group(1)), name + ': input name changed')
            else:
                old_class = unreal.load_class(None, old_classes[old_name])
                default_name = unreal.get_default_object(old_class).get_editor_property('notify_name')
                require(native_notify.get_editor_property('notify_name') == default_name, name + ': default input name changed')
            if guid not in replacements:
                require(native_notify.get_class().get_path_name() == old_classes[old_name], name + ': old notify class changed')
            else:
                require(native_notify.get_class().get_path_name() == class_path, name + ': input replacement class')
                require(str(native_notify.get_editor_property('notify_name')) == replacements[guid], name + ': input replacement name')
        geometry_lines = lambda text: [line for line in text.splitlines()
                                      if line.strip().startswith(('CompositeSections(', 'SlotAnimTracks('))]
        require(geometry_lines(before) == geometry_lines(after) == geometry_lines(fresh), name + ': section/slot/segment rows changed')
        section_times = [f32(float(match.group(1)) if match else 0.0)
                         for line in before.splitlines() if line.strip().startswith('CompositeSections(')
                         for match in [re.search(r'\bLinkValue=([-+0-9.eE]+)', line)]]
        trigger_times = [unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e) for e in native_events]
        require(len(trigger_times) == len(set(trigger_times)), name + ': overlapping native branching triggers')
        expected_events = {e['event_id']: e for e in PLAN['events'] if e['montage'] == path}
        found = collections.defaultdict(list)
        for native_event in native_events:
            parent = native_event.get_editor_property('notify')
            if parent is None or parent.get_class().get_path_name() != class_path:
                continue
            entries = list(parent.get_editor_property('BatchedEffects'))
            if str(parent.get_editor_property('EventId')) != 'None':
                entries.insert(0, parent)
            endings = [child.get_editor_property('bEndEvent') for child in entries]
            require(endings == sorted(endings, reverse=True), name + ': batched End must precede Start')
            for child in entries:
                require(child.get_class().get_path_name() == class_path, name + ': wrong child notify class')
                require(len(child.get_editor_property('BatchedEffects')) == 0, name + ': nested batch is unsupported')
                event_id = str(child.get_editor_property('EventId'))
                require(event_id in expected_events, name + ': unknown source EventId ' + event_id)
                source = expected_events[event_id]
                require(child.get_editor_property('WindowStartTime') == f32(source['start_time']), event_id + ': exact float32 WindowStartTime')
                require(child.get_editor_property('WindowEndTime') == f32(source['end_time']), event_id + ': exact float32 WindowEndTime')
                ending = child.get_editor_property('bEndEvent')
                require(type(ending) is bool, event_id + ': bEndEvent reflection type')
                time = f32(source['end_time'] if ending else source['start_time'])
                boundary = time == 0 or time == f32(montage.get_play_length()) or any(abs(time - s) <= 1e-4 for s in section_times)
                offset = f32((-1 if ending else 1) * 1e-4) if boundary else 0.0
                actual_trigger = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(native_event)
                expected_trigger = f32(time + offset)
                require(actual_trigger == expected_trigger,
                        event_id + ': actual engine trigger differs from authored float32 boundary policy' +
                        ' end=' + repr(ending) + ' actual=' + repr(actual_trigger) +
                        ' expected=' + repr(expected_trigger) + ' residual_seconds=' + repr(actual_trigger - expected_trigger) +
                        ' expected_LinkValue=' + repr(time) + ' expected_offset=' + repr(offset) +
                        ' native_event_export_text_rounded=' + native_event.export_text())
                check_fields(child, source['notify_fields'], event_id, fresh_objects.get(child.get_name(), ''))
                found[event_id].append({'end': ending, 'trigger': actual_trigger})
        require(set(found) == set(expected_events), name + ': missing source EventIds')
        for event_id, entries in found.items():
            require(len(entries) == 2 and sum(e['end'] for e in entries) == 1, event_id + ': expected exactly one Start and one End')
            require(event_id not in all_ids, 'EventId is shared across montages: ' + event_id)
            all_ids.add(event_id)
        row = author_rows[path]
        require(len(native_events) == row['after_count'] and len(before_events) == row['before_count'], name + ': notify count')
        REPORT['montages'].append({'path': path, 'loaded_before_script': previously_loaded,
            'saved_sha256': before_hashes[row['relative']]['stage'], 'source_windows': len(found),
            'start_markers': len(found), 'end_markers': len(found), 'native_marker_count': len(native_events),
            'unique_actual_trigger_times': True, 'all_actual_triggers_equal_authored_boundary_policy': True,
            'original_gameplay_guid_core_input_names_equal': True, 'original_exact_trigger_snapshot_equal': True,
            'section_slot_segment_export_rows_equal': True, 'all_authored_field_types_values_equal': True})
        REPORT['checked_event_ids'] += len(found)
        REPORT['checked_start_markers'] += len(found)
        REPORT['checked_end_markers'] += len(found)
    require(REPORT['checked_event_ids'] == 347, 'Total source window coverage')
    for relative, hashes in before_hashes.items():
        require(sha(WORK / relative) == hashes['stage'] and sha(MAIN / relative) == hashes['main'], 'Audit changed package bytes: ' + relative)
    REPORT['package_bytes_unchanged'] = True
    REPORT['status'] = 'passed'
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
    unreal.log_error(REPORT['error'])
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'SavedAssetAudit.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
print('KZ_PLAYER_ATTACK_VFX_SAVED_AUDIT_' + REPORT['status'].upper(), flush=True)
