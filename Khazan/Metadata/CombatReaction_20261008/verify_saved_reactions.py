"""Fresh caller-owned Work/Main saved asset audit; no saves, compiles or PIE.

Overrides: COMBAT_REACTION_OUTPUT_PATH / KZ_COMBAT_REACTION_OUTPUT,
COMBAT_REACTION_METADATA_DIR / KZ_COMBAT_REACTION_METADATA_DIR.
Caller launches the fresh process. This script only reads exact plan assets.
Unavailable required reflection is a failure, never a receipt-derived pass.
"""
from collections import Counter, defaultdict
from pathlib import Path
import datetime
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
import re
import struct
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
ROOT = Path(unreal.Paths.project_dir()).resolve()
META = Path(globals().get('COMBAT_REACTION_METADATA_DIR') or
            os.environ.get('KZ_COMBAT_REACTION_METADATA_DIR') or
            ROOT / 'Metadata/CombatReaction_20261008').resolve()
OUTPUT = Path(globals().get('COMBAT_REACTION_OUTPUT_PATH') or
              os.environ.get('KZ_COMBAT_REACTION_OUTPUT') or
              META / 'SavedReactionReadback.json').resolve()
TOL = 1e-5  # Serialization comparison tolerance; not a gameplay tuning value.
VECTOR_TOL = 1e-3  # UE float vector serialization tolerance, centimetres.
REPORT = dict(schema='Khazan.CombatReaction.SavedReload.v1', success=False,
              project=str(ROOT), pid=os.getpid(), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              output=str(OUTPUT), read_only=True, no_editor_control=True,
              process_freshness='Caller must launch fresh; script checks project and no game world, not a receipt PID.',
              checks=0, failures=[], unavailable_required=[], inputs={}, api_fallbacks={},
              definitions=[], montages=[], player_copies=[], sources=[], guard_combos=[], collision_assets=[],
              limitations=['Saved assets only; actual Ability/Task/motion/landing/cancellation is separate native PIE QA.',
                           'Raw equality compares actual stored legacy bone keys or Sequencer numeric channels and key times; not compressed runtime poses.',
                           'Source non-dirty is current fresh-process state; it does not prove an earlier process never saved it.',
                           'No global asset scan, reimport, sequence option changes or animation controller mutation.'])
LOADED = {}
EXPORTS = {}
MODEL_AUDITS = {}


def need(condition, message):
    REPORT['checks'] += 1
    if not condition:
        raise AssertionError(message)


def close(actual, expected, label, tolerance=TOL):
    need(math.isfinite(float(actual)) and math.isfinite(float(expected)) and
         abs(float(actual) - float(expected)) <= tolerance,
         f'{label}: actual={actual!r}, expected={expected!r}')


def prop(obj, name):
    # get_editor_property resolves generated aliases; raw C++ names also work for
    # UPROPERTY fields without a generated snake_case alias (UE Python plugin source).
    camel = ''.join(part[:1].upper() + part[1:] for part in name.split('_'))
    candidates = list(dict.fromkeys((name, camel, 'b' + camel)))
    errors = []
    for candidate in candidates:
        try:
            result = obj.get_editor_property(candidate)
            if candidate != name:
                REPORT['api_fallbacks'][name] = candidate
            return result
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError(f'Required reflected property {type(obj).__name__}.{name}: {errors}')


def object_path(obj):
    return obj.get_path_name() if obj is not None else 'None'


def package_path(value):
    return str(value).split('.')[0]


def load(asset_path):
    key = package_path(asset_path)
    if key not in LOADED:
        obj = unreal.load_asset(asset_path)
        need(obj is not None, 'Missing selected asset: ' + str(asset_path))
        LOADED[key] = obj
    return LOADED[key]


def read_json(name):
    filename = META / name
    raw = filename.read_bytes()
    REPORT['inputs'][name] = dict(path=str(filename), sha256=hashlib.sha256(raw).hexdigest())
    return json.loads(raw.decode('utf-8-sig'))


def run_case(label, callback):
    try:
        callback()
    except Exception as error:
        row = dict(case=label, error=str(error), traceback=traceback.format_exc())
        REPORT['failures'].append(row)
        if not isinstance(error, AssertionError):
            REPORT['unavailable_required'].append(dict(case=label, error=str(error)))
        unreal.log_error('ReactionSavedReadback: ' + label + ': ' + str(error))


def export_fields(element):
    """Parse only top-level USTRUCT fields, preserving nested EndLink clocks."""
    value = (element if isinstance(element, str) else element.export_text()).strip()
    need(value.startswith('(') and value.endswith(')'), 'Unreadable struct export: ' + value[:160])
    fields, parts = {}, []
    depth = 0
    quoted = escaped = False
    begin = 1
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == '\\' and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        if quoted:
            continue
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 1:
                parts.append(value[begin:index])
            depth -= 1
        elif char == ',' and depth == 1:
            parts.append(value[begin:index])
            begin = index + 1
    for part in parts:
        key, separator, content = part.partition('=')
        if separator:
            fields[key.strip()] = content.strip()
    return fields


def linked_time(element):
    fields = export_fields(element)
    # ObjectExporterT3D suppresses fields equal to native struct defaults.
    # FAnimLinkableElement ctor: Absolute, SegmentBegin/Length/LinkValue=0.
    method = fields.get('CachedLinkMethod', 'Absolute').lower()
    value = float(fields.get('LinkValue', 0))
    if 'proportional' in method:
        return float(fields.get('SegmentBeginTime', 0)) + value * float(fields.get('SegmentLength', 0))
    if 'relative' in method:
        return float(fields.get('SegmentBeginTime', 0)) + value
    need('absolute' in method, 'Unknown animation link method: ' + method)
    return value


def export_object(obj):
    key = object_path(obj)
    if key not in EXPORTS:
        directory = OUTPUT.parent / (OUTPUT.stem + '_LiveExports')
        directory.mkdir(parents=True, exist_ok=True)
        filename = directory / (obj.get_name() + '_' + hashlib.sha256(key.encode()).hexdigest()[:12] + '.t3d')
        task = unreal.AssetExportTask()
        task.object = obj
        task.filename = str(filename)
        task.exporter = unreal.ObjectExporterT3D()
        task.automated, task.prompt, task.replace_identical = True, False, True
        need(unreal.Exporter.run_asset_export_task(task), 'Fresh object export failed: ' + key)
        raw = filename.read_bytes()
        EXPORTS[key] = raw.decode('utf-8-sig')
        REPORT.setdefault('live_exports', []).append(dict(object=key, file=str(filename),
                                      sha256=hashlib.sha256(raw).hexdigest(), no_asset_save=True))
    return EXPORTS[key]


def sections(montage):
    # Protected CompositeSections cannot be read with get_editor_property.
    # Export THIS loaded object through the stock native exporter, not an old receipt.
    result = []
    for index, text in re.findall(r'^\s*CompositeSections\((\d+)\)=(.*)$', export_object(montage), re.MULTILINE):
        need(int(index) == len(result), 'Composite section export indices differ')
        fields = export_fields(text)
        result.append(dict(name=fields['SectionName'].strip('"'),
                           next=fields.get('NextSectionName', 'None').strip('"'), time=linked_time(text)))
    need(len(result) == montage.get_num_sections(), 'Saved reflected section count differs')
    return result


def data_model(clip):
    errors = []
    for name in ('data_model_interface', 'data_model'):
        try:
            model = prop(clip, name)
            if model is not None:
                # UE Python interfaces normally pythonize their underlying UObject.
                if hasattr(model, 'get_object'):
                    model = model.get_object()
                if model is not None:
                    need(model.get_num_bone_tracks() > 0, 'Actual model contains no bone tracks')
                    return model
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError('Required actual animation data model inaccessible: ' + '; '.join(errors))


def model_shape(model):
    fps = model.get_frame_rate()
    return dict(frames=int(model.get_number_of_frames()), keys=int(model.get_number_of_keys()),
                fps=[int(prop(fps, 'numerator')), int(prop(fps, 'denominator'))],
                tracks=int(model.get_num_bone_tracks()),
                bone_track_names=[str(name) for name in model.get_bone_track_names()])


def sequencer_channel_sha256(model):
    # This UE5.8 model stores FK transform float channels, NOT BoneAnimationTracks.
    # Its deprecated GetBoneAnimationTracks/GetBoneTrackByIndex return empty stubs.
    # Discover its real section from a fresh native export, then read native
    # SequencerScripting key getters without text-rounding key values.
    exported = export_object(model)
    paths = set(re.findall(r'Class=/Script/ControlRig\.MovieSceneControlRigParameterSection[^\n]*'
                           r'ExportPath="[^\']*\'([^\']+)\'"', exported))
    need(len(paths) == 1, 'Expected one actual FK parameter section in current model export')
    section_path = next(iter(paths))
    section = unreal.find_object(None, section_path)
    need(section is not None, 'Exported actual FK section not found in this process: ' + section_path)
    extension = getattr(unreal, 'MovieSceneSectionExtensions', None)
    need(extension is not None, 'SequencerScripting plugin required for exact current channel key readback')
    channels = extension.get_all_channels(section)
    need(len(channels) >= model.get_num_bone_tracks() * 9, 'FK channel proxy does not cover all nine bone transform channels')
    named = sorted(((str(prop(channel, 'channel_name')), channel) for channel in channels), key=lambda pair: pair[0])
    need(len({name for name, _ in named}) == len(named), 'Duplicate actual FK channel names')
    digest = hashlib.sha256()
    total_keys = 0
    classes = Counter()
    for name, channel in named:
        encoded = name.encode('utf-8')
        digest.update(struct.pack('<I', len(encoded)))
        digest.update(encoded)
        class_name = channel.get_class().get_name()
        classes[class_name] += 1
        # Native FK transform data is float; optional non-transform numeric channels
        # are included too. Class identity is included so float/double cannot alias.
        digest.update(class_name.encode('utf-8') + b'\0')
        need(hasattr(channel, 'get_keys') and hasattr(channel, 'has_default'), 'Non-numeric FK channel cannot be audited')
        has_default = bool(channel.has_default())
        digest.update(bytes([has_default]))
        if has_default:
            digest.update(struct.pack('<d', float(channel.get_default())))
        keys = channel.get_keys()
        digest.update(struct.pack('<I', len(keys)))
        for key in keys:
            time = key.get_time(unreal.MovieSceneTimeUnit.TICK_RESOLUTION)
            frame = int(prop(prop(time, 'frame_number'), 'value'))
            sub_frame = float(prop(time, 'sub_frame'))
            value = float(key.get_value())
            need(math.isfinite(value), 'Non-finite actual FK numeric key')
            digest.update(struct.pack('<idd', frame, sub_frame, value))
        total_keys += len(keys)
    need(total_keys > 0, 'No actual FK bone channel keys read')
    # Also compare current serialized interpolation/tangent payloads. Exact numeric
    # key values/time above are binary getter reads; T3D float spelling is not used
    # to claim their bit identity.
    payload = '\n'.join(line.strip() for line in exported.splitlines()
                        if line.strip().startswith('TransformParameterNamesAndCurves('))
    need(payload, 'Current FK transform channel serialization absent')
    digest.update(payload.encode('utf-8'))
    MODEL_AUDITS[object_path(model)] = dict(algorithm='SequencerFKChannelNamesDefaultsKeyTimesValuesBinaryPlusSerializedInterpolation.v1',
        section=section_path, channels=len(channels), numeric_keys=total_keys, channel_classes=dict(classes),
        serialized_transform_sha256=hashlib.sha256(payload.encode('utf-8')).hexdigest(),
        interpolation_precision='T3D native serialized text precision; numeric key times/values compared with actual binary getter values')
    return digest.hexdigest()


def raw_track_sha256(model):
    """Actual stored FVector3f/FQuat4f keys; no no-op deprecated RawTrack API.

    Hash includes track names/order/bone indices/array lengths and IEEE float32
    values. This differs deliberately from author's expanded FTransform MD5.
    """
    if model.get_class().get_name() == 'AnimationSequencerDataModel':
        return sequencer_channel_sha256(model)
    digest = hashlib.sha256()
    for track in prop(model, 'bone_animation_tracks'):
        name = str(prop(track, 'name')).encode('utf-8')
        digest.update(struct.pack('<I', len(name)))
        digest.update(name)
        digest.update(struct.pack('<i', int(prop(track, 'bone_tree_index'))))
        raw = prop(track, 'internal_track_data')
        for field, components in (('pos_keys', ('x', 'y', 'z')),
                                  ('rot_keys', ('x', 'y', 'z', 'w')),
                                  ('scale_keys', ('x', 'y', 'z'))):
            keys = prop(raw, field)
            digest.update(struct.pack('<I', len(keys)))
            for key in keys:
                values = [float(getattr(key, axis)) for axis in components]
                need(all(math.isfinite(number) for number in values), 'Non-finite actual raw bone key')
                digest.update(struct.pack('<' + 'f' * len(values), *values))
    return digest.hexdigest()


def clip_options(clip):
    return dict(asset=object_path(clip), seconds=float(clip.get_play_length()),
                skeleton=object_path(prop(clip, 'skeleton')), rate=float(prop(clip, 'rate_scale')),
                enabled=bool(prop(clip, 'enable_root_motion')), forced=bool(prop(clip, 'force_root_lock')),
                lock=str(prop(clip, 'root_motion_root_lock')),
                normalized=bool(prop(clip, 'use_normalized_root_motion_scale')))


def audit_definition(body):
    obj = load(body['definition'])
    setting = prop(obj, 'hit_reactions')
    row = dict(body=body['body'], asset=object_path(obj), pools={})
    for pool, field in (('ShortHits', 'short_hits'), ('Knockbacks', 'knockbacks'),
                        ('Launches', 'launches'), ('ShieldBlocks', 'shield_blocks')):
        actual = [package_path(object_path(m)) for m in prop(setting, field)]
        expected = [m['destination'] for m in body['montages'] if m['pool'] == pool]
        need(actual == expected, f'{body["body"]}.{pool}: saved pool references/order differ')
        row['pools'][pool] = actual
        if body['body'] == 'Player':
            need(all(p.startswith('/Game/_Art/Player/Animation/InGame/DAS/Reaction/') for p in actual),
                 'Player reaction pool contains non-InGame generated montage')
    grants = [g for g in prop(obj, 'initial_ability_grants')
              if object_path(prop(g, 'ability_class')) == '/Script/Khazan.KZHitReactionAbility']
    need(len(grants) == 1, 'Expected exactly one native reaction grant: ' + body['body'])
    exported_tag = prop(grants[0], 'input_tag').export_text()
    need(not re.findall(r'TagName="([^\"]+)"', exported_tag), 'Event reaction grant has input binding')
    row['reaction_grant'] = '/Script/Khazan.KZHitReactionAbility'
    row['system_guard_on_lockon'] = bool(prop(setting, 'system_guard_on_lock_on'))
    need(row['system_guard_on_lockon'] == body['system_guard_on_lockon'], 'Shield passive policy differs')
    if body['system_guard_on_lockon']:
        close(prop(setting, 'system_guard_front_angle'), body['system_guard_front_angle'], 'Shield full cone')
    row['motion_settings_cm'] = {field: float(prop(setting, field)) for field in
                                ('knockback_distance', 'launch_distance', 'launch_height')}
    if body['body'] != 'Player':
        stamina = prop(obj, 'monster_stamina')
        row['brutal_hp_damage'] = float(prop(stamina, 'brutal_hp_damage'))
        close(row['brutal_hp_damage'], 50, 'User temporary total Brutal HP at Hit2')
    REPORT['definitions'].append(row)


def audit_montage(plan):
    obj = load(plan['destination'])
    actual_sections = sections(obj)
    need([s['name'] for s in actual_sections] == [s['name'] for s in plan['sections']], 'Section names/order differ')
    tracks = prop(obj, 'slot_anim_tracks')
    need(len(tracks) == 1 and str(prop(tracks[0], 'slot_name')) == 'DefaultSlot', 'Expected one DefaultSlot')
    segments = prop(prop(tracks[0], 'anim_track'), 'anim_segments')
    need(len(segments) == len(plan['sections']), 'Section/segment count differs')
    position = 0.0
    rows = []
    for index, (section, segment, expected) in enumerate(zip(actual_sections, segments, plan['sections'])):
        clip = prop(segment, 'anim_reference')
        need(package_path(object_path(clip)) == expected['clip'], 'Saved reaction clip reference differs')
        close(prop(segment, 'start_pos'), position, 'Segment start')
        close(section['time'], position, 'Actual composite section clock')
        close(prop(segment, 'anim_start_time'), 0, 'Source segment start')
        end = min(float(expected.get('source_end_seconds', clip.get_play_length())), float(clip.get_play_length()))
        close(prop(segment, 'anim_end_time'), end, 'Source segment end/crop')
        close(prop(segment, 'anim_play_rate'), 1, 'Segment rate')
        need(int(prop(segment, 'looping_count')) == 1, 'Finite segment loops differ')
        rate = float(prop(clip, 'rate_scale'))
        need(math.isfinite(rate) and rate > 0, 'Invalid saved sequence rate')
        need(prop(obj, 'skeleton') == prop(clip, 'skeleton'), 'Saved reaction skeleton differs')
        need(bool(prop(clip, 'enable_root_motion')) and bool(prop(clip, 'force_root_lock')), 'Clip root options differ')
        following = plan['sections'][index + 1]['name'] if index + 1 < len(plan['sections']) else 'None'
        need(section['next'] == following, 'Saved section default link differs: ' + plan['destination'])
        if 'source_end_seconds' in expected:
            need(section['name'] == 'Loop' and 0 < end <= .3 + TOL, 'Temporary .3 Loop segment crop differs')
        rows.append(dict(section=section['name'], next=section['next'], start=position,
                         clip=object_path(clip), source_end=end, rate=rate,
                         cropped='source_end_seconds' in expected))
        position += end / abs(rate)
    # Montage data model rounds length to authored FPS; section/segment clocks above
    # remain exact. End length is allowed one source frame rounding, not another hold.
    first_model = data_model(prop(segments[0], 'anim_reference'))
    fps = model_shape(first_model)['fps']
    frame = fps[1] / fps[0]
    close(obj.get_play_length(), position, 'Saved montage length/frame rounding', frame / 2 + TOL)
    close(prop(obj, 'rate_scale'), 1, 'Montage rate')
    need(bool(prop(obj, 'enable_auto_blend_out')), 'Finite reaction auto blend out disabled')
    events = ANIMATION.get_animation_notify_events(obj)
    expected_land = plan.get('hit_land_section', '')
    need(len(events) == (1 if expected_land else 0), 'Reaction point-notify count differs')
    land = None
    if expected_land:
        event = events[0]
        notify = prop(event, 'notify')
        need(str(prop(event, 'notify_name')) == 'HitLand' and notify is not None and
             str(prop(notify, 'notify_name')) == 'HitLand', 'HitLand native name differs')
        need(object_path(notify.get_class()) == '/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify' and
             prop(event, 'notify_state_class') is None, 'HitLand is not native point notify')
        need('BRANCHINGPOINT' in str(prop(event, 'montage_tick_type')).upper().replace('_', ''), 'HitLand is not branching point')
        land = linked_time(event)
        close(land, next(s['time'] for s in actual_sections if s['name'] == expected_land), 'HitLand section boundary')
    REPORT['montages'].append(dict(asset=object_path(obj), sections=rows, segment_total=position,
                                   saved_length=float(obj.get_play_length()), hit_land_seconds=land))


def audit_source(row):
    clip = load(row['CurrentAsset'])
    actual = clip_options(clip)
    close(actual['rate'], float(row['RateScale']), 'Original enemy rate')
    close(actual['seconds'], float(row['Seconds']), 'Original enemy sequence duration')
    need(actual['enabled'] == (str(row['EnableRootMotion']).lower() == 'true') and
         actual['forced'] == (str(row['ForceRootLock']).lower() == 'true'), 'Original enemy root options differ')
    need(str(row['RootLock']).replace('_', '').upper() in actual['lock'].replace('_', '').upper(), 'Original enemy RootLock differs')
    REPORT['sources'].append(actual)


def audit_player_copy(plan):
    source, copy = load(plan['source']), load(plan['destination'])
    before, after = clip_options(source), clip_options(copy)
    need(plan['destination'].startswith('/Game/_Art/Player/Animation/InGame/DAS/Reaction/Clips/'), 'Player copy is outside InGame')
    for key in ('seconds', 'rate', 'skeleton', 'normalized'):
        need(before[key] == after[key], 'Player source/copy option or rate differs: ' + key)
    source_model, copy_model = data_model(source), data_model(copy)
    shape = model_shape(source_model)
    need(shape == model_shape(copy_model), 'Player source/copy raw model timeline differs')
    original_hash, copy_hash = raw_track_sha256(source_model), raw_track_sha256(copy_model)
    need(original_hash == copy_hash, 'Player stored raw root/bone keys differ')
    need(after['enabled'] and after['forced'], 'Player InGame root options disabled')
    template = load(REACTION_PLAN['blend_template'])
    root_clip = prop(prop(prop(template, 'slot_anim_tracks')[0], 'anim_track'), 'anim_segments')[0]
    root_clip = prop(root_clip, 'anim_reference')
    need(prop(copy, 'root_motion_root_lock') == prop(root_clip, 'root_motion_root_lock'), 'Player RootLock template differs')
    disk = ROOT / 'Content' / (plan['source'].removeprefix('/Game/') + '.uasset')
    disk_hash = hashlib.sha256(disk.read_bytes()).hexdigest()
    need(disk_hash == plan['source_disk_sha256'], 'Original Player source disk changed since author plan')
    REPORT['sources'].append(before)
    REPORT['player_copies'].append(dict(source=before, copy=after, model=shape,
                                       raw_model_sha256=original_hash, copy_raw_model_sha256=copy_hash,
                                       model_storage_audit=MODEL_AUDITS.get(object_path(source_model),
                                                                    {'algorithm': 'LegacyStoredFloat32BoneTrack.v1'}),
                                       source_disk_sha256=disk_hash))


def nodes_by_id(obj):
    result = {str(prop(node, 'node_id')): node for node in prop(obj, 'nodes')}
    need(len(result) == len(prop(obj, 'nodes')), 'Duplicate saved Combo node IDs')
    return result


def audit_guard(path, plan_rows):
    obj = load(path)
    nodes = nodes_by_id(obj)
    grouped = defaultdict(list)
    for row in plan_rows:
        grouped[row['node_id']].append(row)
    actual = []
    for node_id, node in nodes.items():
        windows = prop(node, 'system_guard_windows')
        expected = grouped.get(node_id, [])
        need(len(windows) == len(expected), 'Unexpected saved SystemGuard window count')
        for value, row in zip(windows, expected):
            close(value.x, row['clipped_local_start_seconds'], 'Guard local start')
            close(value.y, row['clipped_local_end_seconds'], 'Guard local end')
            montage = prop(node, 'montage')
            need(package_path(object_path(montage)) == row['montage'], 'Guard node montage differs')
            need(str(prop(node, 'section_name')) == row['section'], 'Guard node section differs')
            section = next(s for s in sections(montage) if s['name'] == row['section'])
            close(section['time'], row['montage_segment_start_seconds'], 'Guard actual section offset')
            actual.append(dict(node=node_id, start=float(value.x), end=float(value.y), section_start=section['time']))
    REPORT['guard_combos'].append(dict(asset=object_path(obj), windows=actual))


def enum_name(value):
    # UE EnumBase string uses '<KZHitReactionType.SHORT: 1>', not Python IntEnum's
    # simple 'Type.SHORT'. Preserve the actual reflected enum member spelling.
    text = str(value)
    match = re.search(r'\.([A-Za-z][A-Za-z0-9_]*)', text)
    return (match.group(1) if match else text).replace('_', '').upper()


def vector_values(value):
    return [float(value.x), float(value.y), float(value.z)]


def compare_vector(actual, expected, label):
    for axis, a, b in zip('xyz', vector_values(actual), expected):
        close(a, b, label + '.' + axis, VECTOR_TOL)


def audit_collision(pattern):
    obj = load(pattern['definition'])
    nodes = nodes_by_id(obj)
    need(object_path(prop(obj, 'attack_damage_effect')) ==
         '/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C', 'Monster damage GE differs')
    row = dict(asset=object_path(obj), monster=True, nodes=[])
    kinds = Counter()
    for expected_node in pattern['nodes']:
        node = nodes[expected_node['node_id']]
        windows = prop(node, 'attack_windows')
        expected = expected_node['windows']
        need(len(windows) == len(expected), 'Monster saved collision window count differs')
        keys_total = 0
        for window, planned in zip(windows, expected):
            close(prop(window, 'start_time'), planned['start_time'], 'Monster window start')
            close(prop(window, 'end_time'), planned['end_time'], 'Monster window end')
            compare_vector(prop(window, 'extent'), planned['extent'], 'Monster half extent')
            need(enum_name(prop(window, 'shape')) == planned['shape'].upper(), 'Monster collision shape differs')
            kind = enum_name(prop(window, 'hit_reaction'))
            need(kind == planned['reaction'].upper(), 'Monster hit kind differs')
            kinds[planned['reaction']] += 1
            close(prop(window, 'hp_damage'), planned['hp_damage'], 'Monster temporary HP damage')
            close(prop(window, 'stamina_damage'), planned['stamina_damage'], 'Monster temporary Stamina damage')
            need(bool(prop(window, 'blockable')) == planned['blockable'], 'Monster blockable differs')
            need(str(prop(window, 'source')) == planned['source'], 'Monster collision provenance differs')
            keys = prop(window, 'keys')
            need(len(keys) == len(planned['keys']), 'Monster saved collision key count differs')
            for key, expected_key in zip(keys, planned['keys']):
                close(prop(key, 'time'), expected_key['time'], 'Collision key time')
                compare_vector(prop(key, 'center'), expected_key['center'], 'Collision key center')
                quat = prop(key, 'rotation').quaternion()
                values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
                wanted = expected_key['quaternion']
                # Quaternions q and -q encode the same rotation.
                error = min(max(abs(a - b) for a, b in zip(values, wanted)),
                            max(abs(a + b) for a, b in zip(values, wanted)))
                need(error <= TOL, 'Collision key quaternion differs')
            keys_total += len(keys)
        row['nodes'].append(dict(node=expected_node['node_id'], windows=len(windows), keys=keys_total))
    row['kind_counts'] = dict(kinds)
    REPORT['collision_assets'].append(row)


def audit_player_collision():
    obj = load(COLLISION_PLAN['player_definition'])
    nodes = nodes_by_id(obj)
    row = dict(asset=object_path(obj), monster=False, nodes=[])
    kinds = Counter()
    for expected in COLLISION_PLAN['player_reaction_nodes']:
        windows = prop(nodes[expected['node_id']], 'attack_windows')
        need(len(windows) == expected['expected_window_count_saved_author'], 'Player window count changed')
        node_kinds = []
        for planned in expected['windows']:
            window = windows[planned['window_index']]
            kind = enum_name(prop(window, 'hit_reaction'))
            need(kind == planned['reaction'].upper(), 'Player mapped reaction kind differs')
            # This author changed reaction kind only; read actual amounts, never
            # reapply an old receipt's 10/5 over a later user decision.
            start, end = planned['current_window_seconds_saved_author']
            close(prop(window, 'start_time'), start, 'Player preserved window start')
            close(prop(window, 'end_time'), end, 'Player preserved window end')
            kinds[planned['reaction']] += 1
            node_kinds.append(dict(index=planned['window_index'], kind=kind,
                                   hp_damage=float(prop(window, 'hp_damage')),
                                   stamina_damage=float(prop(window, 'stamina_damage')),
                                   keys=len(prop(window, 'keys'))))
        row['nodes'].append(dict(node=expected['node_id'], windows=len(windows), kinds=node_kinds))
    need(dict(kinds) == COLLISION_PLAN['summary']['player_project_reaction_counts'], 'Player60 kind totals differ')
    row['kind_counts'] = dict(kinds)
    REPORT['collision_assets'].append(row)


def dirty_state():
    return dict(content=[object_path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
                maps=[object_path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])


def own_loaded_module():
    """Only this Python process. No OpenProcess/debugger/foreign PID access."""
    manifest_file = ROOT / 'Binaries/Win64/UnrealEditor.modules'
    raw = manifest_file.read_bytes()
    manifest = json.loads(raw.decode('utf-8-sig'))
    selected = manifest['Modules']['Khazan']
    expected = (manifest_file.parent / selected).resolve()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetModuleFileNameW.restype = wintypes.DWORD
    handle = kernel.GetModuleHandleW(expected.name)
    need(bool(handle), 'Selected project module is not loaded in this process: ' + expected.name)
    buffer = ctypes.create_unicode_buffer(32768)  # Windows extended path capacity; not gameplay tuning.
    size = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
    need(0 < size < len(buffer), 'Cannot read own loaded module absolute filename')
    loaded = Path(buffer.value).resolve()
    need(loaded == expected, 'Own loaded Khazan module differs from current project manifest')
    cls = unreal.load_class(None, '/Script/Khazan.KZHitReactionAbility')
    need(cls is not None and object_path(cls) == '/Script/Khazan.KZHitReactionAbility',
         'New native HitReaction class absent in actual loaded module')
    native_enum = getattr(unreal, 'KZHitReactionType', None)
    need(native_enum is not None, 'New native reflected KZHitReactionType absent')
    REPORT['loaded_module'] = dict(path=str(loaded), sha256=hashlib.sha256(loaded.read_bytes()).hexdigest(),
        selected=selected, manifest=str(manifest_file), manifest_sha256=hashlib.sha256(raw).hexdigest(),
        build_id=manifest.get('BuildId'), own_process_only=True, native_ability_class=object_path(cls),
        native_hit_reaction_enum=str(native_enum))


def audit():
    global REACTION_PLAN, COLLISION_PLAN, ANIMATION
    need(ROOT in (MAIN, WORK), 'Unexpected project; exact isolated Work or Main required')
    own_loaded_module()
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    need(subsystem.get_game_world() is None, 'Saved readback requires no PIE/game world')
    REPORT['initial_dirty'] = dirty_state()
    need(not REPORT['initial_dirty']['content'] and not REPORT['initial_dirty']['maps'], 'Fresh process already dirty')
    REACTION_PLAN = read_json('ReactionAuthoringPlan.json')
    COLLISION_PLAN = read_json('MonsterAttackCollisionPlan.json')
    ANIMATION = getattr(unreal, 'AnimationLibrary', None) or getattr(unreal, 'AnimationBlueprintLibrary', None)
    need(ANIMATION is not None, 'Engine AnimationLibrary unavailable')
    all_plans = [m for body in REACTION_PLAN['bodies'] for m in body['montages']]
    unique_plans = {}
    for montage in all_plans:
        key = montage['destination']
        if key in unique_plans:
            need(unique_plans[key]['sections'] == montage['sections'] and
                 unique_plans[key]['hit_land_section'] == montage['hit_land_section'], 'Shared fallback alias differs')
        unique_plans[key] = montage
    need(len(REACTION_PLAN['bodies']) == 7 and len(all_plans) == 65 and len(unique_plans) == 63, 'Latest reaction plan counts differ')
    need(len(REACTION_PLAN['enemy_source_audit']) == 221 and len(REACTION_PLAN['player_copies']) == 24, 'Source plan245 scope differs')
    need(sum('source_end_seconds' in section for montage in unique_plans.values()
             for section in montage['sections']) == 16, 'Expected16 cropped Loop sections')
    for body in REACTION_PLAN['bodies']:
        run_case('Definition:' + body['body'], lambda body=body: audit_definition(body))
    for name, montage in unique_plans.items():
        run_case('Montage:' + name, lambda montage=montage: audit_montage(montage))
    for source in REACTION_PLAN['enemy_source_audit']:
        run_case('EnemySource:' + source['CurrentAsset'], lambda source=source: audit_source(source))
    for copy in REACTION_PLAN['player_copies']:
        run_case('PlayerCopy:' + copy['destination'], lambda copy=copy: audit_player_copy(copy))
    guards = defaultdict(list)
    for window in REACTION_PLAN['system_guard_windows']:
        guards[window['combo_definition']].append(window)
    need(len(guards) == 3 and sum(map(len, guards.values())) == 9, 'SystemGuard3/9 scope differs')
    for name, windows in guards.items():
        run_case('GuardCombo:' + name, lambda name=name, windows=windows: audit_guard(name, windows))
    need(len(COLLISION_PLAN['monster_patterns']) == 35, 'Collision35 monster definition plan differs')
    for pattern in COLLISION_PLAN['monster_patterns']:
        run_case('MonsterCollision:' + pattern['definition'], lambda pattern=pattern: audit_collision(pattern))
    run_case('PlayerCollision', audit_player_collision)
    monsters = [r for r in REPORT['collision_assets'] if r['monster']]
    need(len(monsters) == 35 and len(REPORT['collision_assets']) == 36, 'Collision36 saved definitions not all verified')
    windows = sum(n['windows'] for a in monsters for n in a['nodes'])
    keys = sum(n['keys'] for a in monsters for n in a['nodes'])
    need(windows == 113 and keys == 1498, 'Collision113 windows/1498 keys differ')
    planned_monster_kinds = Counter(window['reaction'] for pattern in COLLISION_PLAN['monster_patterns']
                                    for node in pattern['nodes'] for window in node['windows'])
    actual_monster_kinds = Counter()
    for asset in monsters:
        actual_monster_kinds.update(asset['kind_counts'])
    need(actual_monster_kinds == planned_monster_kinds, 'Monster planned/saved kind totals differ')
    need(dict(planned_monster_kinds) == dict(Short=109, Knockback=2, Launch=2),
         'Latest four-window temporary Monster kind map is absent')
    need(len(REPORT['definitions']) == 7 and len(REPORT['montages']) == 63 and
         len(REPORT['player_copies']) == 24 and len(REPORT['sources']) == 245 and
         len(REPORT['guard_combos']) == 3, 'Required readback scope incomplete')
    REPORT['counts'] = dict(definitions=7, brutal_damage_50_monsters=6, montage_plan_rows=65,
                            unique_montages=63, trimmed_loops=16, raw_equal_player_copies=24,
                            sources=245, guard_combos=3, guard_windows=9,
                            collision_definitions=36, monster_windows=windows, monster_keys=keys,
                            monster_reaction_kinds=dict(actual_monster_kinds),
                            player_windows=sum(n['windows'] for r in REPORT['collision_assets'] if not r['monster'] for n in r['nodes']))


try:
    audit()
except Exception as error:
    REPORT['failures'].append(dict(case='Audit', error=str(error), traceback=traceback.format_exc()))
finally:
    try:
        REPORT['final_dirty'] = dirty_state()
        if REPORT['final_dirty']['content'] or REPORT['final_dirty']['maps']:
            REPORT['failures'].append(dict(case='ReadOnly', error='Read-only audit dirtied packages', dirty=REPORT['final_dirty']))
        REPORT['source_dirty_packages'] = [p for p in REPORT['final_dirty']['content']
            if package_path(p) in {package_path(s['asset']) for s in REPORT['sources']}]
    except Exception as error:
        REPORT['failures'].append(dict(case='DirtyReadback', error=str(error)))
    REPORT['success'] = not REPORT['failures'] and not REPORT['unavailable_required']
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(OUTPUT.name + '.partial.' + str(os.getpid()))
    temporary.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, OUTPUT)
    print('CombatReactionSavedReloadJSON=' + json.dumps(dict(success=REPORT['success'], output=str(OUTPUT),
          pid=os.getpid(), checks=REPORT['checks'], failures=len(REPORT['failures']),
          unavailable_required=len(REPORT['unavailable_required']), counts=REPORT.get('counts', {}))))
