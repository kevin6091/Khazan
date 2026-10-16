"""Scoped saved reload audit. Run in a fresh caller-owned Work/Main Python commandlet.

Reads selected assets and author receipts only; never compiles, saves, spawns or runs PIE.
The only output is MonsterStaminaSavedReloadJSON=<JSON> on stdout, including on failure.
Raw bone/pose equivalence belongs to the separate C++ author audit, not this reload audit.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import os
import re
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
ROOT = Path(unreal.Paths.project_dir()).resolve()
TOL = 1e-5  # Serialization/comparison tolerance, seconds or scalar; not gameplay tuning.
REPORT = dict(schema='Khazan.MonsterStamina.SavedReload.v1', project=str(ROOT),
              pid=os.getpid(), read_only=True, success=False, tolerance=TOL,
              verification_scope='Readable saved settings/references/segments/notifies/autoBlendOut/options only; unverified_required is separate native QA.',
              receipts={}, definitions=[], effects=[], montages=[], clips=[],
              attacks=[], bodies=[], unverified_required=[
                  'Saved default NextSectionName links and direct section clocks are not exposed to Python; native autoplay QA must cover them.',
                  'ABP pin connection topology is not read by this script; native idle/montage pose QA must cover it.'], limitations=[
                  'Caller must launch a fresh owned process; this script does not reload an existing editor.',
                  'No PIE/ability execution, compressed/raw pose comparison or original-game runtime equivalence.',
                  'Skeleton slot registration/reference bones are author C++ evidence; reload checks montage/clip skeleton identity.',
                  'Existing Definition contents are enumerated; author receipt contains counts, not a full pre-author field snapshot.'])


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def prop(obj, name):
    return obj.get_editor_property(name)


def path(obj):
    return obj.get_path_name() if obj is not None else 'None'


def close(actual, expected, context):
    need(math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= TOL,
         f'{context}: actual={actual}, expected={expected}')


def tag(value):
    match = re.search(r'TagName="([^"]*)"', value.export_text())
    need(match is not None, 'Unreadable GameplayTag: ' + value.export_text())
    return match.group(1)


def tags(value):
    return sorted(re.findall(r'TagName="([^"]+)"', value.export_text()))


def load(asset_path):
    obj = unreal.load_asset(asset_path)
    need(obj is not None, 'Missing selected asset: ' + asset_path)
    return obj


def blueprint(asset_path):
    bp = load(asset_path)
    cls = unreal.EditorAssetLibrary.load_blueprint_class(asset_path)
    need(cls is not None, 'Missing generated class: ' + asset_path)
    need(prop(bp, 'status') == unreal.BlueprintStatus.BS_UP_TO_DATE, 'Blueprint not compiled: ' + asset_path)
    return bp, cls, unreal.get_default_object(cls)


def receipt(name):
    candidates = (ROOT / 'Saved/MonsterStamina' / name,
                  ROOT / 'Metadata/MonsterStamina_20261008' / name)
    filename = next((p for p in candidates if p.is_file()), None)
    need(filename is not None, 'Missing author receipt ' + name)
    raw = filename.read_bytes()
    value = json.loads(raw.decode('utf-8-sig'))
    need(value.get('status') == 'AuthoredInWorkOnly_NoPIE', 'Invalid author receipt: ' + name)
    REPORT['receipts'][name] = dict(file=str(filename), sha256=hashlib.sha256(raw).hexdigest())
    return value


def grants(definition):
    return [dict(ability=path(prop(g, 'ability_class')), input=tag(prop(g, 'input_tag')))
            for g in prop(definition, 'initial_ability_grants')]


def linked_time(element):
    # The copied notify struct export includes UPROPERTY-only fields Python cannot read directly.
    # Same absolute conversion as FAnimLinkableElement::GetTime; no receipt-derived clock.
    exported = element.export_text()
    # Ignore nested EndLink fields: a point event's unlinked EndLink has LinkValue=0.
    fields = {}; depth = 0; start = 1
    for index, char in enumerate(exported):
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 1:
                key, separator, value = exported[start:index].partition('=')
                if separator: fields[key.strip()] = value.strip()
            depth -= 1
        elif char == ',' and depth == 1:
            key, separator, value = exported[start:index].partition('=')
            if separator: fields[key.strip()] = value.strip()
            start = index + 1
    def field(name):
        need(name in fields, 'Unreadable notify export field ' + name + ': ' + exported)
        return fields[name]
    method = field('CachedLinkMethod').lower()
    value = float(field('LinkValue'))
    if 'proportional' in method:
        return float(field('SegmentBeginTime')) + value * float(field('SegmentLength'))
    if 'relative' in method:
        return float(field('SegmentBeginTime')) + value
    need('absolute' in method, 'Unknown animation link method: ' + method)
    return value


def notify_duration(element):
    match = re.search(r'(?:^|[,(])\s*Duration=([^,()]+)', element.export_text())
    need(match is not None, 'Unreadable notify Duration export')
    return float(match.group(1))


def registry_rows(registry):
    rows = []
    for group, asset_set in prop(registry, 'asset_group_name_to_set').items():
        for entry in prop(asset_set, 'asset_entries'):
            # FSoftObjectPath::ExportTextItem emits its real ToString path; avoids an unexposed make/break helper.
            exported_path = prop(entry, 'asset_path').export_text()
            asset_path = json.loads(exported_path) if exported_path.startswith('"') else exported_path
            need(asset_path.startswith('/Game/'), 'Unexpected registry object path export: ' + exported_path)
            rows.append(dict(group=str(group), tag=tag(prop(entry, 'asset_name')),
                             asset=asset_path,
                             labels=sorted(tag(t) for t in prop(entry, 'asset_labels'))))
    return rows


def registry_set(rows):
    return Counter((r['group'], r['tag'], r['asset'], tuple(sorted(r['labels']))) for r in rows)


def audit():
    need(ROOT in (MAIN, WORK), 'Unexpected project for stamina saved reload')
    need(os.getpid() not in (13700, 30120), 'Existing user/external editor is forbidden')
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    need(subsystem.get_game_world() is None, 'Saved reload requires no PIE')
    need(not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() and
         not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Fresh audit must start with no dirty packages')
    author, bodies = receipt('Authoring.json'), receipt('BodiesAuthoring.json')
    need(len(author['montage_audits']) == 20 and len(author['clip_audits']) == 47 and
         len(author['monster_attack_audits']) == 35 and len(bodies['families']) == 2, 'Unexpected scoped receipt counts')
    animation = getattr(unreal, 'AnimationLibrary', None) or getattr(unreal, 'AnimationBlueprintLibrary', None)
    need(animation is not None, 'Read-only AnimationLibrary API is unavailable')
    player_base = '/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/'
    policy_path = '/Game/Monsters/Effects/GE_MonsterStaminaPolicy'
    dead_path = '/Game/Monsters/Effects/GE_DeadState'
    damage_path = '/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C'
    _, policy_class, _ = blueprint(policy_path)
    _, dead_class, _ = blueprint(dead_path)
    for asset_path, expected in ((policy_path, ['Block.StaminaRegen']),
                                 (dead_path, ['Block.Movement.Input', 'State.Dead'])):
        _, cls, cdo = blueprint(asset_path)
        components = [c for c in prop(cdo, 'ge_components')
                      if c.get_class().get_name() == 'TargetTagsGameplayEffectComponent']
        need(len(components) == 1, 'Exactly one target-tag component: ' + asset_path)
        container = None; selected_field = None; field_errors = {}
        # UE's private editor field has DisplayName="Add Tags"; use only these exact known aliases.
        for field in ('InheritableGrantedTagsContainer', 'inheritable_granted_tags_container', 'add_tags', 'AddTags'):
            try:
                container = prop(components[0], field); selected_field = field; break
            except Exception as error:
                field_errors[field] = str(error)
        combined = tags(prop(container, 'combined_tags')) if container is not None else None
        if combined is not None:
            need(combined == sorted(expected), 'Configured combined granted tags differ: ' + asset_path)
        else:
            REPORT['unverified_required'].append(asset_path + ': target-tag editor container unexposed; actual native ASC tag QA required.')
        need(prop(cdo, 'duration_policy') == unreal.GameplayEffectDurationType.INFINITE and not prop(cdo, 'modifiers'),
             'Tag-only Infinite effect differs: ' + asset_path)
        REPORT['effects'].append(dict(asset=path(cls), duration=str(prop(cdo, 'duration_policy')),
                                      configured_combined_tags=combined, configured_field=selected_field,
                                      unavailable_field_errors=field_errors if container is None else {}, modifiers=0))
    for entry in author['definition_audits']:
        family = entry['family']; base = '/Game/Monsters/' + family
        definition = load(base + '/Data/DA_Character_' + family)
        settings = prop(definition, 'monster_stamina')
        need(prop(settings, 'enabled'), 'Stamina setting disabled: ' + family)
        actual = {key: float(prop(settings, field)) for key, field in (
            ('parry_damage', 'parry_stamina_damage'), ('exhaustion_seconds', 'exhaustion_seconds'),
            ('brutal_hp_damage', 'brutal_hp_damage'), ('brutal_range_cm', 'brutal_attack_range'),
            ('alignment_distance_cm', 'brutal_alignment_distance'))}
        for key, value in actual.items(): close(value, entry[key], family + ':' + key)
        expected_refs = dict(exhaustion_montage=base + '/Animations/AM_Exhaustion',
                             brutal_front_player_montage=player_base + 'AM_DAS_BrutalFront',
                             brutal_back_player_montage=player_base + 'AM_DAS_BrutalBack',
                             brutal_front_victim_montage=base + '/Animations/AM_BrutalVictimFront',
                             brutal_back_victim_montage=base + '/Animations/AM_BrutalVictimBack')
        refs = {field: path(prop(settings, field)) for field in expected_refs}
        for field, expected in expected_refs.items(): need(prop(settings, field) == load(expected), family + ':' + field)
        need(path(prop(settings, 'damage_effect')) == damage_path and prop(settings, 'dead_state_effect') == dead_class,
             'Damage/death effect ref differs: ' + family)
        items = grants(definition); effects = [path(e) for e in prop(definition, 'initial_effects')]
        need(items.count(dict(ability='/Script/Khazan.KZExhaustionAbility', input='')) == 1,
             'Exactly one native Exhaustion grant: ' + family)
        need(len(items) == entry['initial_grant_count_after'] and len(effects) == entry['initial_effect_count_after'],
             'Saved grant/effect counts differ: ' + family)
        need(effects.count(path(policy_class)) == 1, 'Exactly one policy effect: ' + family)
        REPORT['definitions'].append(dict(family=family, asset=path(definition), enabled=True,
                                         settings=actual, montage_refs=refs, damage_effect=damage_path,
                                         dead_effect=path(dead_class), grants=items, initial_effects=effects))
    player = load('/Game/Data/Character/DA_CharacterDefinition_Player'); items = grants(player)
    need(items.count(dict(ability='/Script/Khazan.KZBrutalAttackAbility', input='Input.Action.X')) == 1 and
         len(items) == author['player_grant_count_after'], 'Saved Player native Brutal input grant differs')
    REPORT['player'] = dict(definition=path(player), grants=items,
                            initial_effects=[path(e) for e in prop(player, 'initial_effects')])
    for entry in author['montage_audits']:
        asset = load(entry['asset']); expected_sections = entry['sections']
        sections = [str(asset.get_section_name(i)) for i in range(asset.get_num_sections())]
        need(sections == [s['name'] for s in expected_sections], 'Section count/names differ: ' + entry['asset'])
        tracks = prop(asset, 'slot_anim_tracks')
        need(len(tracks) == 1 and str(prop(tracks[0], 'slot_name')) == 'DefaultSlot', 'Expected single DefaultSlot')
        segments = prop(prop(tracks[0], 'anim_track'), 'anim_segments')
        need(len(segments) == len(sections), 'Segment/section count differs: ' + entry['asset'])
        actual_sections = []
        for section, segment, expected in zip(sections, segments, expected_sections):
            clip = prop(segment, 'anim_reference')
            row = dict(name=section, clip=path(clip), segment_start=float(prop(segment, 'start_pos')),
                       source_start=float(prop(segment, 'anim_start_time')), source_end=float(prop(segment, 'anim_end_time')),
                       play_rate=float(prop(segment, 'anim_play_rate')), loops=int(prop(segment, 'looping_count')))
            need(row['name'] == expected['name'] and row['clip'] == expected['clip'], 'Section names/segment refs differ')
            close(row['segment_start'], expected['start_seconds'], 'Saved segment position')
            close(row['source_start'], 0, 'Full clip start'); close(row['source_end'], clip.get_play_length(), 'Full clip end')
            close(row['play_rate'], 1, 'Segment rate'); need(row['loops'] == 1, 'Segment loop count differs')
            need(prop(asset, 'skeleton') == prop(clip, 'skeleton'), 'Montage/clip skeleton differs')
            actual_sections.append(row)
        actual_notifies = []
        for event in animation.get_animation_notify_events(asset):
            notify = prop(event, 'notify')
            actual_notifies.append(dict(name=str(prop(event, 'notify_name')), time_seconds=linked_time(event),
                                        class_path=path(notify.get_class()) if notify else 'None',
                                        native_name=str(prop(notify, 'notify_name')) if notify else 'None',
                                        state_class=path(prop(event, 'notify_state_class')),
                                        duration=notify_duration(event), tick=str(prop(event, 'montage_tick_type'))))
        actual_notifies.sort(key=lambda row: row['time_seconds'])
        need(len(actual_notifies) == len(entry['notifies']), 'Saved notify count differs: ' + entry['asset'])
        for row, expected in zip(actual_notifies, entry['notifies']):
            need(row['name'] == expected['name'] == row['native_name'] and
                 row['class_path'] == '/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify' and
                 row['state_class'] == 'None' and 'BRANCHINGPOINT' in row['tick'].upper().replace('_', ''), 'Native point notify contract differs')
            close(row['time_seconds'], expected['time_seconds'], 'Notify position'); close(row['duration'], 0, 'Point notify duration')
        template = load(entry['blend_template']) if entry['blend_template'] != 'None' else None
        auto = bool(prop(asset, 'enable_auto_blend_out')); trigger = float(prop(asset, 'blend_out_trigger_time'))
        need(auto == (bool(prop(template, 'enable_auto_blend_out')) if template else True), 'Critical autoBlendOut differs: ' + entry['asset'])
        close(trigger, prop(template, 'blend_out_trigger_time') if template else 0, 'BlendOutTriggerTime')
        close(asset.get_default_blend_in_time(), entry['blend_in_seconds'], 'BlendIn')
        close(asset.get_default_blend_out_time(), entry['blend_out_seconds'], 'BlendOut')
        if template:
            for field in ('blend_mode_in', 'blend_mode_out', 'blend_profile_in', 'blend_profile_out'):
                need(prop(asset, field) == prop(template, field), 'Player template blend field differs: ' + field)
        close(prop(asset, 'rate_scale'), 1, 'Montage RateScale'); close(asset.get_play_length(), entry['seconds'], 'Montage length')
        REPORT['montages'].append(dict(asset=path(asset), skeleton=path(prop(asset, 'skeleton')), slot='DefaultSlot',
                                       sections=actual_sections, notifies=actual_notifies, auto_blend_out=auto,
                                       blend_out_trigger_time=trigger, blend_in=asset.get_default_blend_in_time(),
                                       blend_out=asset.get_default_blend_out_time(), seconds=asset.get_play_length()))
    for entry in author['clip_audits'] + bodies['idle_copy_audits']:
        source, copy = load(entry['source']), load(entry['destination']); options = {}
        for field in ('rate_scale', 'enable_root_motion', 'force_root_lock', 'use_normalized_root_motion_scale', 'root_motion_root_lock'):
            need(prop(source, field) == prop(copy, field), 'Saved source/copy options differ: ' + entry['destination'])
            options[field] = str(prop(copy, field)) if field == 'root_motion_root_lock' else prop(copy, field)
        need(prop(source, 'skeleton') == prop(copy, 'skeleton'), 'Saved source/copy skeleton differs')
        close(source.get_play_length(), copy.get_play_length(), 'Saved source/copy duration')
        frames, keys = animation.get_num_frames(copy), animation.get_num_keys(copy)
        need(frames == animation.get_num_frames(source) and keys == animation.get_num_keys(source), 'Saved source/copy frame/key counts differ')
        REPORT['clips'].append(dict(source=path(source), copy=path(copy), skeleton=path(prop(copy, 'skeleton')),
                                    seconds=copy.get_play_length(), read_options=options,
                                    frames=frames, keys=keys))
    for entry in author['monster_attack_audits']:
        cdo = unreal.get_default_object(unreal.load_class(None, entry['ability']))
        need(cdo is not None and prop(cdo, 'cost_gameplay_effect_class') is None and
             prop(cdo, 'OnEndAbilityGameplayEffect') is None, 'Saved Monster attack cost/regen differs: ' + entry['ability'])
        REPORT['attacks'].append(dict(family=entry['family'], ability=entry['ability'], cost=None, on_end=None))
    for entry in bodies['families']:
        bp, _, cdo = blueprint(entry['gameplay_bp']); abp, _, anim = blueprint(entry['animation_bp'].split('.')[0])
        need(path(unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)) == '/Script/Khazan.KZMonster' and
             path(unreal.BlueprintEditorLibrary.get_blueprint_parent_class(abp)) == '/Script/Khazan.KZAnimInstance', 'Body BP/ABP native parents differ')
        capsule, mesh = prop(cdo, 'capsule_component'), prop(cdo, 'mesh'); evidence = entry['body_audit_evidence']['components'][0]
        close(capsule.get_unscaled_capsule_radius(), entry['capsule_radius_cm'], 'Capsule radius')
        close(capsule.get_unscaled_capsule_half_height(), entry['capsule_half_height_cm'], 'Capsule halfheight')
        need(tag(prop(cdo, 'CharacterDefinitionAssetName')) == entry['definition_tag'] and
             path(mesh.get_skeletal_mesh_asset()) == evidence['mesh'] and
             prop(mesh, 'anim_class') == unreal.EditorAssetLibrary.load_blueprint_class(entry['animation_bp'].split('.')[0]), 'Body mesh/Definition/ABP refs differ')
        need(path(prop(abp, 'target_skeleton')) == evidence['skeleton'] and
             prop(anim, 'root_motion_mode') == unreal.RootMotionMode.ROOT_MOTION_FROM_MONTAGES_ONLY, 'ABP skeleton/rootMotionMode differs')
        need(prop(cdo, 'AIStateTree') is None and prop(cdo, 'AlertAbility') is None and not prop(cdo, 'AttackAbilities'), 'New families unexpectedly have expanded AI patterns')
        graph = unreal.BlueprintEditorLibrary.find_graph(abp, 'AnimGraph')
        need(graph is not None, 'Missing selected AnimGraph')
        # EdGraph.Nodes is protected; enumerate only loaded AnimGraphNode_Base objects and filter this exact graph.
        nodes = [n for n in unreal.ObjectIterator(unreal.AnimGraphNode_Base) if n.get_outer() == graph]
        classes = sorted(n.get_class().get_name() for n in nodes)
        need(classes == sorted(('AnimGraphNode_SequencePlayer', 'AnimGraphNode_Slot', 'AnimGraphNode_Inertialization', 'AnimGraphNode_Root')), 'Minimal ABP node inventory differs')
        sequence = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_SequencePlayer')
        idle_node = prop(sequence, 'node'); need(prop(idle_node, 'sequence') == load(entry['idle_copy']) and prop(idle_node, 'loop_animation'), 'ABP idle/loop differs')
        close(prop(idle_node, 'play_rate'), 1, 'ABP idle rate')
        REPORT['bodies'].append(dict(family=entry['family'], bp=path(bp), abp=path(abp), mesh=evidence['mesh'],
                                     skeleton=evidence['skeleton'], capsule_radius=capsule.get_unscaled_capsule_radius(),
                                     capsule_half_height=capsule.get_unscaled_capsule_half_height(), definition_tag=entry['definition_tag'],
                                     root_motion_mode=str(prop(anim, 'root_motion_mode')), node_inventory=classes,
                                     idle=path(prop(idle_node, 'sequence')), idle_loop=True, idle_rate=float(prop(idle_node, 'play_rate'))))
    rows = registry_rows(load('/Game/Data/PDA_AssetData')); actual = registry_set(rows)
    need(actual == registry_set(bodies['registry_after']), 'Saved PDA differs from scoped appended entry set')
    before = registry_set(bodies['registry_before']); need(not (before - actual), 'Preexisting PDA entries changed/lost')
    REPORT['registry'] = dict(actual=rows, preexisting_preserved=True, added=list((actual - before).elements()))
    REPORT['dirty_content'] = [path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    REPORT['dirty_map'] = [path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    need(not REPORT['dirty_content'] and not REPORT['dirty_map'], 'Read-only verification dirtied packages')
    REPORT['counts'] = dict(definitions=6, player_definitions=1, montages=len(REPORT['montages']),
                            sequence_copies=len(REPORT['clips']), attack_bps=len(REPORT['attacks']), bodies=len(REPORT['bodies']))
    REPORT['success'] = True


try:
    audit()
except Exception as error:
    REPORT['error'] = str(error)
    REPORT['traceback'] = traceback.format_exc()
    print('MonsterStaminaSavedReloadJSON=' + json.dumps(REPORT, ensure_ascii=False, separators=(',', ':')))
    raise
else:
    print('MonsterStaminaSavedReloadJSON=' + json.dumps(REPORT, ensure_ascii=False, separators=(',', ':')))
