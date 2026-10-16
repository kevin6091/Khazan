"""Apply a frozen, source-backed InGame playback plan in the live UE editor.

No gameplay code, skeleton, mesh, or source-library asset is changed. The plan
and immutable package backup must exist before this module can write assets.
The existing exact-60 sampler/pose auditor is reused. Source pose order, full
current range, root scale, and asset identity are preserved by time resampling.
"""

import bisect
import ctypes
import hashlib
import json
import pathlib
import re
import runpy

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / 'Saved/Extracted/InGame_Playback_20261002'
PLAN_PATH = ROOT / 'PlaybackPlan.json'
PLAN = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
BACKUP = json.loads((ROOT / 'BackupManifest.json').read_text(encoding='utf-8'))
SCOPE = PLAN['scope'] + '/'
VERSION = '20261002_InGame_BaseBranchSegmentTimingV1'
REPORT = ROOT / 'ApplyReport.json'
EAL = unreal.EditorAssetLibrary
HELPERS = runpy.run_path(
    str(PROJECT / 'Scripts/Animation/fix_das_composite_playback_60fps.py'),
    run_name='ingame_exact60_helpers',
)
ROWS = {row['path']: row for row in PLAN['assets']}
RESULTS = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else []


def record(value):
    RESULTS.append(value)
    REPORT.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding='utf-8')
    print({key: value[key] for key in ('asset', 'action', 'status') if key in value})


def writable(asset):
    path = asset.get_path_name().split('.', 1)[0]
    if not path.startswith(SCOPE):
        raise RuntimeError('Asset outside the user-authorized InGame scope: ' + path)
    return path


def save(asset):
    writable(asset)
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


def frame_rate(asset):
    rate = asset.controller.get_model_interface().get_frame_rate()
    return [int(rate.numerator), int(rate.denominator)]


def unchanged_package(path):
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop PIE before modifying playback assets')
    if any(p.get_path_name() == path for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve an unsaved target package: ' + path)
    filename = (PROJECT / 'Content' / path[6:]).with_suffix('.uasset')
    relative = str(filename.relative_to(PROJECT)).replace('\\', '/')
    previous = next(f for f in BACKUP['files'] if f['path'].replace('\\', '/') == relative)
    if hashlib.sha256(filename.read_bytes()).hexdigest() != previous['sha256']:
        raise RuntimeError('Preserve a target changed after the snapshot: ' + path)


def preflight():
    if hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() != BACKUP['planSha256']:
        raise RuntimeError('Plan differs from the immutable backup contract')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop PIE before editing playback assets')
    if any(p.get_path_name().startswith(SCOPE) for p in
           unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('An InGame package has unsaved changes; preserve it before editing')
    summaries = []
    for row in PLAN['assets']:
        seq = unreal.load_asset(row['path'])
        writable(seq)
        model = seq.controller.get_model_interface()
        old = row['previous']
        if frame_rate(seq) != old['fps'] or int(model.get_number_of_frames()) != old['frames']:
            raise RuntimeError('Timeline changed after snapshot: ' + row['path'])
        if abs(seq.get_editor_property('rate_scale') - old['properties']['rate_scale']) > 1e-6:
            raise RuntimeError('RateScale changed after snapshot: ' + row['path'])
        if row['action'] == 'retime':
            tracks = unreal.AnimationLibrary.get_animation_notify_track_names(seq)
            markers = sum(len(unreal.AnimationLibrary.get_animation_sync_markers_for_track(seq, t)) for t in tracks)
            if (unreal.AnimationLibrary.get_animation_notify_events(seq) or markers
                    or model.get_number_of_float_curves() or model.get_number_of_transform_curves()):
                raise RuntimeError('Authored non-bone data requires time mapping: ' + row['path'])
            names = [str(n) for n in model.get_bone_track_names()]
            if not names:
                raise RuntimeError('No bone tracks: ' + row['path'])
            summaries.append({'asset': row['path'], 'tracks': len(names), 'first_track': names[0]})
    (ROOT / 'EditorPreflight.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    print({'preflight': 'passed', 'scope_sequences': len(PLAN['assets']), 'retime_sequences': len(summaries)})


def apply_sequence(row, sequence=None, report=True):
    if sequence is None:
        unchanged_package(row['path'])
    seq = sequence or unreal.load_asset(row['path'])
    writable(seq)
    old = row['previous']
    model = seq.controller.get_model_interface()
    if frame_rate(seq) != old['fps'] or int(model.get_number_of_frames()) != old['frames']:
        raise RuntimeError('Already changed or stale source: ' + seq.get_path_name())
    names = list(model.get_bone_track_names())
    properties = {n: seq.get_editor_property(n) for n in HELPERS['COPY_PROPERTIES']}
    positions, rotations, scales, checkpoints = HELPERS['sample_tracks'](
        seq, names, row['target_frames'], old['duration'], row['source_times']
    )
    controller = unreal.AnimationDataController.cast(seq.controller)
    controller.open_bracket('Bake source-backed InGame segment timing', False)
    try:
        controller.set_frame_rate(unreal.FrameRate(60, 1), False)
        controller.set_number_of_frames(unreal.FrameNumber(row['target_frames']), False)
        # Write existing tracks in place; preserve top-root and Control Rig order.
        for index, name in enumerate(names):
            if not controller.set_bone_track_keys(str(name), positions[index], rotations[index], scales[index], False):
                raise RuntimeError('Track write failed: ' + str(name))
        platform = seq.get_editor_property('platform_target_frame_rate')
        platform.set_editor_property('default', unreal.FrameRate(60, 1))
        overrides = platform.get_editor_property('per_platform')
        if overrides:
            platform.set_editor_property('per_platform', {n: unreal.FrameRate(60, 1) for n in overrides})
    finally:
        controller.close_bracket(False)
    old_metadata = {str(k): str(v) for k, v in EAL.get_metadata_tag_values(seq).items()}
    EAL.set_metadata_tag(seq, 'InGamePreviousTimingContract', old_metadata.get('TimingContract', ''))
    EAL.set_metadata_tag(seq, 'InGamePreviousTimingVersion', old_metadata.get('DASTimingVersion', ''))
    EAL.set_metadata_tag(seq, 'DASTimingVersion', VERSION)
    EAL.set_metadata_tag(seq, 'PlaybackDerivation', 'InGameFullSourceSegmentRetime')
    concise = {k: v for k, v in row.items() if k not in ('previous', 'source_times', 'inverse_map')}
    concise.update({'mesh_component_scale_used': False, 'root_translation_rescaled': False})
    EAL.set_metadata_tag(seq, 'TimingContract', json.dumps(concise, ensure_ascii=False))
    EAL.set_metadata_tag(seq, 'PlaybackUsage', 'Base branch segment rates and Dilation baked once; RateScale/segment/task rate 1. Current full source pose range and root scale preserved. Other execution contexts use their own Composite playback.')
    save(seq)
    verification = HELPERS['verify_replacement'](
        seq, row['path'], names, row['target_frames'], row['target_duration'], checkpoints, properties
    )
    expected = {'checkpoints': checkpoints, 'properties': {n: str(v) for n, v in properties.items()}, 'tracks': [str(n) for n in names]}
    (ROOT / ('Expected_' + seq.get_name() + '.json')).write_text(json.dumps(expected, ensure_ascii=False), encoding='utf-8')
    value = {'asset': writable(seq), 'action': 'retime', 'status': 'passed', **verification}
    if report:
        record(value)
    return value


def apply_rates():
    for row in PLAN['assets']:
        if row['action'] != 'rate_scale':
            continue
        unchanged_package(row['path'])
        seq = unreal.load_asset(row['path'])
        writable(seq)
        seq.set_editor_property('rate_scale', row['target_rate_scale'])
        EAL.set_metadata_tag(seq, 'OriginalPackage', row['original'])
        EAL.set_metadata_tag(seq, 'InGameCadenceCorrection', json.dumps({
            'original_timing': row['original_timing'], 'current_grid': row['previous']['fps'],
            'rate_scale': row['target_rate_scale'], 'pose_keys_crop_padding_markers_preserved': True,
            'mesh_component_scale_used': False,
        }, ensure_ascii=False))
        save(seq)
        if frame_rate(seq) != row['previous']['fps'] or abs(seq.get_editor_property('rate_scale') - row['target_rate_scale']) > 1e-6:
            raise RuntimeError('Cadence readback mismatch: ' + row['path'])
        record({'asset': row['path'], 'action': 'rate_scale', 'status': 'passed', 'rate_scale': row['target_rate_scale']})


def standalone():
    for row in PLAN['standalone']:
        if EAL.does_asset_exist(row['destination']):
            raise RuntimeError('Preserve existing destination: ' + row['destination'])
        source = unreal.load_asset(row['source'])
        if EAL.get_metadata_tag(source, 'DASTimingVersion') != '20260917_DAS_CompositeExact60HzV5' or frame_rate(source) != [60, 1]:
            raise RuntimeError('Existing playback is not the audited exact60 contract')
        folder, name = row['destination'].rsplit('/', 1)
        copy = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, folder, source)
        if not copy:
            raise RuntimeError('Cannot copy existing complete playback')
        EAL.set_metadata_tag(copy, 'InGameCopiedPlaybackSource', row['source'])
        save(copy)
        record({'asset': row['destination'], 'action': 'standalone_copy', 'status': 'passed', 'source': row['source'], 'duration': copy.get_play_length()})


def fields(text):
    result, start, depth, quoted, escaped = {}, 1, 0, False, False
    for i, char in enumerate(text[1:-1], 1):
        if escaped:
            escaped = False
        elif char == '\\' and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            depth += (char == '(') - (char == ')')
            if char == ',' and depth == 0:
                key, value = text[start:i].split('=', 1)
                result[key] = value
                start = i + 1
    if start < len(text) - 1:
        key, value = text[start:-1].split('=', 1)
        result[key] = value
    return result


def struct_text(values):
    return '(' + ','.join(k + '=' + str(v) for k, v in values.items()) + ')'


def native_array(montage, property_name, texts):
    """Import two exact montage arrays unavailable through Python reflection.

    This bridge calls UE's exported property serializer on the game thread. It never
    writes object memory, changes property flags, or issues a global SET command.
    The ABI and exports are checked against this installed engine's headers/DLLs.
    """
    writable(montage)
    if property_name not in ('CompositeSections', 'Notifies') or not isinstance(montage, unreal.AnimMontage):
        raise RuntimeError('Only the audited montage arrays may use this bridge')
    if not unreal.SystemLibrary.get_engine_version().startswith('5.8.2-') or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError('Native property bridge requires the audited Win64 UE 5.8.2 ABI')
    class StringView(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_int32)]
    engine_dir = pathlib.Path(unreal.Paths.engine_dir()).resolve() / 'Binaries/Win64'
    core = ctypes.WinDLL(str(engine_dir / 'UnrealEditor-Core.dll'))
    objects = ctypes.WinDLL(str(engine_dir / 'UnrealEditor-CoreUObject.dll'))
    find = getattr(objects, '?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(StringView), ctypes.c_uint32]
    find.restype = ctypes.c_void_p
    def exact_object(path):
        text = ctypes.create_unicode_buffer(path)
        view = StringView(ctypes.cast(text, ctypes.c_void_p), len(path))
        return find(None, None, ctypes.byref(view), 0)
    obj, cls = exact_object(montage.get_path_name()), exact_object('/Script/Engine.AnimMontage')
    if not obj or not cls:
        raise RuntimeError('Exact native object/class lookup failed')
    name_constructor = getattr(core, '??0FName@@QEAA@PEB_W@Z')
    name_constructor.argtypes, name_constructor.restype = [ctypes.c_void_p, ctypes.c_wchar_p], ctypes.c_void_p
    name = ctypes.create_string_buffer(16)  # Win64 editor FName fits; constructed by UE.
    name_constructor(name, property_name)
    find_property = getattr(objects, '?FindPropertyByName@UStruct@@QEBAPEAVFProperty@@VFName@@@Z')
    find_property.argtypes, find_property.restype = [ctypes.c_void_p, ctypes.c_void_p], ctypes.c_void_p
    prop = find_property(cls, name)
    if not prop:
        raise RuntimeError('Exact montage array property lookup failed')
    importer = getattr(objects, '?ImportText_Internal@FArrayProperty@@MEBAPEB_WPEB_WU?$TNotNull@PEAX@@W4EPropertyPointerType@@PEAVUObject@@HPEAVFOutputDevice@@@Z')
    importer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
    importer.restype = ctypes.c_void_p
    body = '(' + ','.join(texts) + ')'
    buffer = ctypes.create_unicode_buffer(body)
    error_device = ctypes.c_void_p.in_dll(core, '?GWarn@@3PEAVFFeedbackContext@@EA').value
    consumed = importer(prop, buffer, obj, 1, obj, 0, error_device)  # Container, not a raw field pointer.
    if consumed != ctypes.addressof(buffer) + len(body) * ctypes.sizeof(ctypes.c_wchar):
        raise RuntimeError('Montage array import did not consume the complete value')


def montage_export(montage):
    destination = ROOT / (montage.get_name() + '_Readback.t3d')
    task = unreal.AssetExportTask()
    task.object, task.filename = montage, str(destination)
    task.automated, task.prompt, task.replace_identical = True, False, True
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError('Montage readback export failed')
    return destination.read_text(encoding='utf-8')


def source_to_playback(row, old_time):
    if row is None or row['action'] != 'retime':
        return old_time
    if old_time <= 0:
        return 0.0
    if old_time >= row['previous']['duration'] - 1e-6:
        return row['target_duration']
    pairs = row['inverse_map']
    index = max(1, min(bisect.bisect_right([p[1] for p in pairs], old_time), len(pairs) - 1))
    left, right = pairs[index - 1], pairs[index]
    return left[0] + (right[0] - left[0]) * (old_time - left[1]) / (right[1] - left[1])


def apply_montage(snapshot, montage=None, report=True):
    if montage is None:
        unchanged_package(snapshot['path'])
    m = montage or unreal.load_asset(snapshot['path'])
    writable(m)
    slots, spans, delta = [], [], 0.0
    if len(snapshot['slots']) != 1:
        raise RuntimeError('Multi-slot montage requires its own timing contract')
    for text in snapshot['slots']:
        slot = unreal.SlotAnimationTrack()
        slot.import_text(text)
        track = slot.get_editor_property('anim_track')
        segments = list(track.get_editor_property('anim_segments'))
        for segment in segments:
            ref = segment.get_editor_property('anim_reference')
            row = ROWS.get(ref.get_path_name().split('.', 1)[0])
            old_start = float(segment.get_editor_property('start_pos'))
            a, b = float(segment.get_editor_property('anim_start_time')), float(segment.get_editor_property('anim_end_time'))
            rate = float(segment.get_editor_property('anim_play_rate'))
            if rate <= 0 or int(segment.get_editor_property('looping_count')) != 1:
                raise RuntimeError('Montage ordering requires a separate contract')
            na, nb = source_to_playback(row, a), source_to_playback(row, b)
            length, new_length = (b - a) / rate, (nb - na) / rate
            start = old_start + delta
            spans.append((old_start, old_start + length, start, start + new_length, a, na, rate, row))
            values = fields(segment.export_text())
            values.update({'StartPos': repr(start), 'AnimStartTime': repr(na),
                           'AnimEndTime': repr(nb), 'CachedPlayLength': repr(ref.get_play_length())})
            segment.import_text(struct_text(values))
            delta += new_length - length
        values = fields(track.export_text())
        values['AnimSegments'] = '(' + ','.join(s.export_text() for s in segments) + ')'
        track.import_text(struct_text(values))
        values = fields(slot.export_text())
        values['AnimTrack'] = track.export_text()
        slot.import_text(struct_text(values))
        slots.append(slot)

    def map_time(t):
        if t <= 0:
            return 0.0
        for old_start, old_end, start, end, a, na, rate, row in spans:
            if t <= old_end + 1e-6:
                return start + (source_to_playback(row, a + (t - old_start) * rate) - na) / rate
        return t + delta

    def remap_link(text):
        values = fields(text)
        old_time = float(values.get('LinkValue', 0))
        if values.get('LinkMethod', 'Absolute') != 'Absolute':
            raise RuntimeError('Non-absolute montage linkage requires its own time contract')
        values['LinkValue'] = repr(map_time(old_time))
        linked = values.get('LinkedMontage', 'None') != 'None'
        if linked:
            values['LinkedMontage'] = '"/Script/Engine.AnimMontage\'' + m.get_path_name() + '\'"'
        if linked and 'SegmentBeginTime' in values:
            values['SegmentBeginTime'] = repr(map_time(float(values['SegmentBeginTime'])))
        if linked and 'SegmentLength' in values and int(values.get('SegmentIndex', -1)) >= 0:
            index = int(values.get('SegmentIndex', 0))
            values['SegmentLength'] = repr(spans[index][3] - spans[index][2])
        for name in ('Notify', 'NotifyStateClass'):
            if name in values:
                original_object = unreal.load_asset(snapshot['path']).get_path_name()
                values[name] = values[name].replace(original_object, m.get_path_name())
        if 'EndLink' in values:
            values['EndLink'] = remap_link(values['EndLink'])
            if 'Duration' in values:
                values['Duration'] = repr(map_time(old_time + float(values['Duration'])) - map_time(old_time))
        return struct_text(values)

    export = PROJECT / 'Saved/ImportReports/InGame_MontageExports_20261002' / (unreal.load_asset(snapshot['path']).get_name() + '.t3d')
    section_texts = re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$', export.read_text(encoding='utf-8'), re.MULTILINE)
    expected_sections = [remap_link(t) for t in section_texts]
    expected_notifies = [remap_link(t) for t in snapshot['notifies']]
    m.set_editor_property('slot_anim_tracks', slots)
    native_array(m, 'CompositeSections', expected_sections)
    native_array(m, 'Notifies', expected_notifies)
    end = spans[-1][3]
    rate = m.controller.get_model_interface().get_frame_rate()
    m.controller.set_number_of_frames(unreal.FrameNumber(round(end * rate.numerator / rate.denominator)), False)
    # These public editor APIs invoke virtual RefreshCacheData, rebuilding the
    # branching-point cache. The temporary empty last track is never saved.
    track_names = list(unreal.AnimationLibrary.get_animation_notify_track_names(m))
    refresh_track = '__InGameTimingCacheRefresh_20261002'
    if refresh_track in [str(n) for n in track_names]:
        raise RuntimeError('Preserve an existing cache-refresh track')
    unreal.AnimationLibrary.add_animation_notify_track(m, refresh_track)
    unreal.AnimationLibrary.remove_animation_notify_track(m, refresh_track)
    if list(unreal.AnimationLibrary.get_animation_notify_track_names(m)) != track_names:
        raise RuntimeError('Authored notify track names/order changed')
    save(m)
    if abs(m.get_play_length() - end) > 1e-5 or m.get_num_sections() != len(section_texts):
        raise RuntimeError('Montage length/section readback mismatch')
    if len(unreal.AnimationLibrary.get_animation_notify_events(m)) != len(snapshot['notifies']):
        raise RuntimeError('Montage notify count changed')
    readback = montage_export(m)
    actual_sections = re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$', readback, re.MULTILINE)
    actual_notifies = re.findall(r'^\s*Notifies\(\d+\)=(.*)$', readback, re.MULTILINE)
    for expected_list, actual_list in ((expected_sections, actual_sections), (expected_notifies, actual_notifies)):
        if len(expected_list) != len(actual_list):
            raise RuntimeError('Montage exported array count changed')
        for expected, actual in zip(expected_list, actual_list):
            a, b = fields(expected), fields(actual)
            for name in ('LinkValue', 'SegmentBeginTime', 'SegmentLength', 'Duration'):
                if abs(float(a.get(name, 0)) - float(b.get(name, 0))) > 1e-5:
                    raise RuntimeError('Montage exported time mismatch: ' + name)
            for name in ('SectionName', 'NextSectionName', 'Guid', 'NotifyName'):
                if a.get(name) != b.get(name):
                    raise RuntimeError('Montage authored identity changed: ' + name)
    for expected, actual in zip(slots, m.get_editor_property('slot_anim_tracks')):
        if expected.export_text() != actual.export_text():
            raise RuntimeError('Montage segment readback mismatch')
    (ROOT / ('Expected_' + m.get_name() + '.json')).write_text(json.dumps({
        'slots': [s.export_text() for s in slots], 'sections': expected_sections,
        'notifies': expected_notifies, 'duration': end,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    value = {'asset': writable(m), 'action': 'montage_timing', 'status': 'passed', 'duration': m.get_play_length(), 'sections': len(section_texts), 'notifies': len(snapshot['notifies']), 'spans': [s[:7] for s in spans]}
    if report:
        record(value)
    return value
