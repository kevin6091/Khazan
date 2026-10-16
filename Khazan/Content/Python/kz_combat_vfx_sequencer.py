"""Visual combat Niagara authoring. Sequencer is the source; Apply bakes existing notify data."""
import json
import math
import uuid
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
TAG = 'KZCombatVFX'
WEAK02 = '/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/DAS_Player_WeakAttack02'
WEAK_MONTAGE = '/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo'
PLAYER = '/Game/_Art/Player/Character/Bluprints/BP_Player'
FOLDER = '/Game/Tools/CombatVFX'
_preview_handle = None
_preview_state = {}
_preview_capture = False
_preview_error = None


def _guid(binding):
    return binding.get_id().export_text()


def _metadata(sequence):
    text = u.EditorAssetLibrary.get_metadata_tag(sequence, TAG)
    if not text:
        raise RuntimeError('Open a Khazan VFX editing sequence first.')
    return json.loads(text)


def _notify_data(montage):
    for event in u.AnimationLibrary.get_animation_notify_events(montage):
        parent = event.get_editor_property('Notify')
        if isinstance(parent, u.KZAnimNotify_CombatEffect):
            for data in [parent] + list(parent.get_editor_property('BatchedEffects')):
                if not data.get_editor_property('bEndEvent') and data.get_editor_property('NiagaraTemplate'):
                    yield data


def _segment(montage, animation):
    for slot in montage.get_editor_property('SlotAnimTracks'):
        for segment in slot.get_editor_property('AnimTrack').get_editor_property('AnimSegments'):
            if segment.get_editor_property('AnimReference') == animation:
                rate = segment.get_editor_property('AnimPlayRate')
                loops = segment.get_editor_property('LoopingCount')
                if rate <= 0 or loops != 1:
                    raise RuntimeError('Select a forward, single-occurrence attack segment.')
                start = segment.get_editor_property('StartPos')
                trim = segment.get_editor_property('AnimStartTime')
                duration = (segment.get_editor_property('AnimEndTime') - trim) / rate
                return start, duration, trim, rate
    raise RuntimeError('The selected animation is not in that montage.')


def _spawn(sequence, cls, label, setup=None):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(cls, u.Vector())
    actor.set_actor_label(label)
    try:
        if setup:
            setup(actor)
        binding = u.get_editor_subsystem(u.LevelSequenceEditorSubsystem).add_spawnable_from_instance(sequence, actor)
        binding.set_display_name(label)
        rate = sequence.get_display_rate()
        for track in binding.get_tracks():
            if isinstance(track, u.MovieSceneSpawnTrack):
                for section in track.get_sections():
                    section.set_range_seconds(0, sequence.get_playback_end_seconds() + rate.denominator / rate.numerator)
        return binding, binding.get_object_template()
    finally:
        actors.destroy_actor(actor)


def _component_binding(sequence, actor_binding, component):
    u.LevelSequenceEditorBlueprintLibrary.force_update()
    actors = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(actor_binding))
    if not actors:
        raise RuntimeError('The Sequencer preview actor did not spawn.')
    live = next((c for c in actors[0].get_components_by_class(u.SceneComponent) if c.get_name() == component.get_name()), None)
    if not live:
        raise RuntimeError('The preview component could not be resolved.')
    binding = sequence.add_possessable(live)
    binding.set_parent(actor_binding)
    return binding


def _transform(sequence, binding, duration, keys):
    tracks = [t for t in binding.get_tracks() if isinstance(t, u.MovieScene3DTransformTrack)]
    track = tracks[0] if tracks else binding.add_track(u.MovieScene3DTransformTrack)
    for section in list(track.get_sections()):
        track.remove_section(section)
    section = track.add_section()
    section.set_range_seconds(0, duration)
    channels = section.get_all_channels()[:9]
    for axis, channel in enumerate(channels):
        channel.set_default(1 if axis >= 6 else 0)
    tick = sequence.get_tick_resolution()
    resolution = tick.numerator / tick.denominator
    for key in keys:
        for axis, value in enumerate(key['location'] + key['rotation'] + key['scale']):
            channel = channels[axis]
            channel.add_key(u.FrameNumber(round(key['time'] * resolution)), value,
                            time_unit=u.MovieSceneTimeUnit.TICK_RESOLUTION,
                            interpolation=u.MovieSceneKeyInterpolation.LINEAR)
    return section


def _effect(sequence, manifest, system, effect_id, start, end, keys, weapon=False, drain=False):
    def setup(actor):
        component = actor.get_editor_property('NiagaraComponent')
        component.set_asset(system)
        component.set_auto_activate(False)
        u.KZAnimNotify_CombatEffect.configure_sequencer_preview(component, weapon)
    binding, template = _spawn(sequence, u.NiagaraActor, 'VFX | ' + effect_id, setup)
    component = template.get_editor_property('NiagaraComponent')
    component.set_asset(system)
    component.set_auto_activate(False)
    u.KZAnimNotify_CombatEffect.configure_sequencer_preview(component, weapon)
    original = _transform(sequence, binding, manifest['duration'], keys)
    original.set_is_locked(True)
    adjustment = original.get_outer().add_section()
    adjustment.set_range_seconds(0, manifest['duration'])
    adjustment.set_row_index(1)
    adjustment.set_blend_type(u.MovieSceneBlendType.ADDITIVE)
    for channel in adjustment.get_all_channels()[:9]:
        channel.set_default(0)
        channel.add_key(u.FrameNumber(0), 0, interpolation=u.MovieSceneKeyInterpolation.LINEAR)
    body_binding = next(b for b in sequence.get_bindings() if _guid(b) == manifest['body_binding'])
    attach = binding.add_track(u.MovieScene3DAttachTrack).add_section()
    attach.set_range_seconds(0, manifest['duration'])
    attach.set_constraint_binding_id(sequence.get_binding_id(body_binding))
    attach.set_editor_property('AttachmentLocationRule', u.AttachmentRule.KEEP_RELATIVE)
    attach.set_editor_property('AttachmentRotationRule', u.AttachmentRule.KEEP_RELATIVE)
    attach.set_editor_property('AttachmentScaleRule', u.AttachmentRule.KEEP_RELATIVE)
    child = _component_binding(sequence, binding, component)
    section = child.add_track(u.MovieSceneNiagaraSystemTrack).add_section()
    section.set_range_seconds(start, end)
    section.set_age_update_mode(u.NiagaraAgeUpdateMode.DESIRED_AGE)
    section.set_section_end_behavior(u.NiagaraSystemSpawnSectionEndBehavior.SET_SYSTEM_INACTIVE if drain
                                    else u.NiagaraSystemSpawnSectionEndBehavior.DEACTIVATE)
    manifest['bindings'][_guid(binding)] = {'id': effect_id, 'weapon': weapon}
    manifest['managed_ids'].append(effect_id)
    return binding


def open_animation(animation, montage=None):
    if montage is None:
        registry = u.AssetRegistryHelpers.get_asset_registry()
        refs = registry.get_referencers(animation.get_path_name().split('.')[0],
            u.AssetRegistryDependencyOptions(include_hard_package_references=True))
        montages = [a for a in (u.load_asset(str(p)) for p in refs) if isinstance(a, u.AnimMontage)]
        if len(montages) != 1:
            raise RuntimeError('Select an animation with one attack montage; ambiguous montage references require an explicit selection.')
        montage = montages[0]
    origin, duration, trim, play_rate = _segment(montage, animation)
    name = 'LS_' + animation.get_name() + '_VFX'
    path = FOLDER + '/' + name
    sequence = u.load_asset(path)
    if sequence:
        manifest = _metadata(sequence)
        if manifest.get('version') == 1:
            for binding in sequence.get_bindings():
                tracks = [t for t in binding.get_tracks() if isinstance(t, u.MovieScene3DTransformTrack)]
                if len(tracks) == 2:
                    binding.remove_track(tracks[0])
            manifest['version'] = 2
            u.EditorAssetLibrary.set_metadata_tag(sequence, TAG, json.dumps(manifest))
            u.EditorAssetLibrary.save_loaded_asset(sequence)
        u.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
        return sequence
    tools = u.AssetToolsHelpers.get_asset_tools()
    sequence = tools.create_asset(name, FOLDER, u.LevelSequence, u.LevelSequenceFactoryNew())
    if not sequence:
        raise RuntimeError('Could not create the VFX sequence.')
    frame_rate = animation.controller.get_model_interface().get_frame_rate()
    sequence.set_display_rate(frame_rate)
    sequence.set_playback_start_seconds(0)
    sequence.set_playback_end_seconds(duration)
    u.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    u.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
    manifest = {'version': 2, 'montage': montage.get_path_name(), 'animation': animation.get_path_name(),
                'origin': origin, 'duration': duration, 'trim': trim, 'play_rate': play_rate,
                'bindings': {}, 'managed_ids': []}
    player_class = u.EditorAssetLibrary.load_blueprint_class(PLAYER)
    body_binding, template = _spawn(sequence, player_class, 'Player | ' + animation.get_name())
    body = template.get_editor_property('Mesh')
    manifest['body_binding'] = _guid(body_binding)
    starts = u.EditorLevelLibrary.get_all_level_actors()
    start_actor = next((a for a in starts if isinstance(a, u.PlayerStart)), None)
    origin_location = start_actor.get_actor_location() if start_actor else u.Vector()
    _transform(sequence, body_binding, duration, [{'time': 0, 'location': [origin_location.x, origin_location.y, origin_location.z],
                'rotation': [0, 0, 0], 'scale': [1, 1, 1]}])
    section = body_binding.add_track(u.MovieSceneSkeletalAnimationTrack).add_section()
    section.set_range_seconds(0, duration)
    params = section.get_editor_property('Params')
    params.set_editor_property('Animation', animation)
    params.set_editor_property('PlayRate', u.MovieSceneTimeWarpExtensions.make_time_warp(play_rate))
    tick = sequence.get_tick_resolution()
    params.set_editor_property('StartFrameOffset', u.FrameNumber(round(trim * tick.numerator / tick.denominator)))
    params.set_editor_property('bForceCustomMode', True)
    params.set_editor_property('bSkipAnimNotifiers', True)
    section.set_editor_property('Params', params)
    imported = ROOT / 'Metadata/CombatVFXSequencer_20261013/ImportedMotion.json'
    initial = json.loads(imported.read_text(encoding='utf-8')) if imported.exists() else {}
    for data in _notify_data(montage):
        start = data.get_editor_property('WindowStartTime') - origin
        end = data.get_editor_property('WindowEndTime') - origin
        if not 0 <= start < duration or end > duration:
            continue
        effect_id = str(data.get_editor_property('EventId'))
        keys = initial.get(effect_id, [])
        if not keys:
            location = data.get_editor_property('RelativeLocation')
            rotation = data.get_editor_property('RelativeRotation')
            scale = data.get_editor_property('Scale3D')
            keys = [{'time': start, 'location': [location.x, location.y, location.z],
                     'rotation': [rotation.roll, rotation.pitch, rotation.yaw], 'scale': [scale.x, scale.y, scale.z]}]
        _effect(sequence, manifest, data.get_editor_property('NiagaraTemplate'), effect_id, start, end, keys,
                data.get_editor_property('bAlignToWeaponSweep'),
                data.get_editor_property('bDestroyOnNotifyEndDeactived'))
    u.EditorAssetLibrary.set_metadata_tag(sequence, TAG, json.dumps(manifest))
    u.EditorAssetLibrary.save_loaded_asset(sequence)
    u.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    u.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
    u.LevelSequenceEditorBlueprintLibrary.force_update()
    return sequence


def open_weak02():
    return open_animation(u.load_asset(WEAK02), u.load_asset(WEAK_MONTAGE))


def open_selected():
    assets = u.EditorUtilityLibrary.get_selected_assets()
    animations = [a for a in assets if isinstance(a, u.AnimSequence)]
    if len(animations) != 1:
        raise RuntimeError('Select one attack AnimSequence in the Content Browser.')
    montages = [a for a in assets if isinstance(a, u.AnimMontage)]
    return open_animation(animations[0], montages[0] if len(montages) == 1 else None)


def add_selected_niagara():
    sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    manifest = _metadata(sequence)
    systems = [a for a in u.EditorUtilityLibrary.get_selected_assets() if isinstance(a, u.NiagaraSystem)]
    if len(systems) != 1:
        raise RuntimeError('Select one Niagara System in the Content Browser.')
    effect_id = 'KZSequencer_' + uuid.uuid4().hex
    _effect(sequence, manifest, systems[0], effect_id, 0, manifest['duration'],
            [{'time': 0, 'location': [0, 0, 0], 'rotation': [0, 0, 0], 'scale': [1, 1, 1]}])
    u.EditorAssetLibrary.set_metadata_tag(sequence, TAG, json.dumps(manifest))
    u.EditorAssetLibrary.save_loaded_asset(sequence)
    u.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()


def collect_edits(sequence):
    global _preview_capture
    manifest = _metadata(sequence)
    rate = sequence.get_display_rate()
    fps = rate.numerator / rate.denominator
    result = {'managed_ids': manifest['managed_ids'], 'effects': []}
    targets = []
    for binding in sequence.get_bindings():
        entry = manifest['bindings'].get(_guid(binding))
        if not entry:
            continue
        transforms = [t for t in binding.get_tracks() if isinstance(t, u.MovieScene3DTransformTrack)]
        children = [b for b in sequence.get_bindings() if _guid(b.get_parent()) == _guid(binding)]
        life = [s for b in children for t in b.get_tracks() if isinstance(t, u.MovieSceneNiagaraSystemTrack) for s in t.get_sections()]
        if not life:
            continue  # Removing a lifecycle section removes that effect when Apply is pressed.
        if not transforms or len(life) != 1:
            raise RuntimeError('Each VFX needs a Transform track and one Life Cycle section.')
        start, end = life[0].get_start_frame_seconds(), life[0].get_end_frame_seconds()
        if not 0 <= start < end <= manifest['duration']:
            raise RuntimeError('Keep each Life Cycle within the attack animation.')
        template = binding.get_object_template()
        system = template.get_editor_property('NiagaraComponent').get_asset()
        behavior = life[0].get_section_end_behavior()
        if behavior == u.NiagaraSystemSpawnSectionEndBehavior.NONE:
            raise RuntimeError('Life Cycle End must deactivate or finish existing particles.')
        row = {'id': entry['id'], 'system': system.get_path_name(),
                                 'start': manifest['origin'] + start, 'end': manifest['origin'] + end,
                                 'drain': behavior == u.NiagaraSystemSpawnSectionEndBehavior.SET_SYSTEM_INACTIVE,
                                 'keys': []}
        result['effects'].append(row)
        targets.append((binding, row))
    # Evaluate the editor itself: attachments, additive sections, easing and gizmo
    # edits are included. No second implementation of Sequencer's blend math.
    body_binding = next(b for b in sequence.get_bindings() if _guid(b) == manifest['body_binding'])
    saved_time = u.LevelSequenceEditorBlueprintLibrary.get_global_position()
    tick = sequence.get_tick_resolution()
    last = manifest['duration'] - tick.denominator / tick.numerator
    times = [f / fps for f in range(math.ceil(manifest['duration'] * fps))]
    if not times or times[-1] < last:
        times.append(last)
    _preview_capture = True
    try:
        for time in times:
            # Subframes keep source event clocks separate from the display grid.
            params = u.MovieSceneSequencePlaybackParams()
            params.set_editor_property('Frame', u.FrameTime(u.FrameNumber(math.floor(time * fps)), time * fps % 1))
            params.set_editor_property('PositionType', u.MovieScenePositionType.FRAME)
            u.LevelSequenceEditorBlueprintLibrary.set_global_position(params)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            bodies = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(body_binding))
            if not bodies:
                raise RuntimeError('Player preview binding is not available; reopen the editing sequence.')
            parent = bodies[0].get_actor_transform()
            for binding, row in targets:
                actors = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(binding))
                if not actors:
                    raise RuntimeError('A Niagara preview binding could not be evaluated.')
                local = u.MathLibrary.make_relative_transform(actors[0].get_actor_transform(), parent)
                p, r, s = local.translation, local.rotation.rotator(), local.scale3d
                rotation = [r.roll, r.pitch, r.yaw]
                if row['keys']:
                    previous = row['keys'][-1]['rotation']
                    rotation = [x + 360 * round((previous[a] - x) / 360) for a, x in enumerate(rotation)]
                row['keys'].append({'time': manifest['origin'] + time, 'location': [p.x, p.y, p.z],
                                    'rotation': rotation, 'scale': [s.x, s.y, s.z]})
    finally:
        try:
            u.LevelSequenceEditorBlueprintLibrary.set_global_position(saved_time)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
        finally:
            _preview_capture = False
    return manifest, result


def apply_current():
    sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
    manifest, edits = collect_edits(sequence)
    montage = u.load_asset(manifest['montage'])
    error = u.KZAnimNotify_CombatEffect.apply_sequencer_edits(montage, json.dumps(edits))
    if error:
        raise RuntimeError(error)
    u.EditorAssetLibrary.save_loaded_asset(sequence)
    u.EditorAssetLibrary.save_loaded_asset(montage)
    u.log('Khazan VFX: applied %d Niagara effects to %s' % (len(edits['effects']), montage.get_name()))
    return edits


def _tick_preview(delta):
    """Finish Niagara simulation at the edited pose when Sequencer seeks or plays."""
    global _preview_error
    if _preview_capture:
        return
    try:
        sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        if not sequence or not u.EditorAssetLibrary.get_metadata_tag(sequence, TAG):
            _preview_state.clear()
            return
        manifest = _metadata(sequence)
        fps = sequence.get_display_rate().numerator / sequence.get_display_rate().denominator
        frame = int(u.LevelSequenceEditorBlueprintLibrary.get_current_time())
        time = frame / fps
        active_keys = set()
        for binding in sequence.get_bindings():
            entry = manifest['bindings'].get(_guid(binding))
            if not entry:
                continue
            children = [b for b in sequence.get_bindings() if _guid(b.get_parent()) == _guid(binding)]
            life = [s for child in children for track in child.get_tracks()
                    if isinstance(track, u.MovieSceneNiagaraSystemTrack) for s in track.get_sections()]
            if len(life) != 1:
                continue
            start, end = life[0].get_start_frame_seconds(), life[0].get_end_frame_seconds()
            key = (sequence.get_path_name(), entry['id'])
            if not start <= time < end:
                _preview_state.pop(key, None)
                continue
            actors = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(binding))
            components = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(children[0]))
            if not actors or not components:
                continue
            component = components[0]
            pose = actors[0].get_actor_transform()
            p, r, s = pose.translation, pose.rotation, pose.scale3d
            transform = (p.x, p.y, p.z, r.x, r.y, r.z, r.w, s.x, s.y, s.z)
            system = component.get_asset()
            state = (frame, transform, start, end, system.get_path_name() if system else None)
            active_keys.add(key)
            previous = _preview_state.get(key)
            if previous == state:
                continue
            component.set_rendering_enabled(True)
            if previous and frame == previous[0] + 1 and previous[2:] == state[2:]:
                component.advance_simulation_by_time(1.0 / fps, 1.0 / fps)
            else:
                component.reinitialize_system()
                component.advance_simulation_by_time(max(0.0, time - start), 1.0 / fps)
            _preview_state[key] = state
        for key in list(_preview_state):
            if key not in active_keys:
                del _preview_state[key]
        _preview_error = None
    except Exception as error:
        if str(error) != _preview_error:
            u.log_warning('Khazan VFX preview: ' + str(error))
            _preview_error = str(error)


@u.uclass()
class KZCombatVFXMenuEntry(u.ToolMenuEntryScript):
    @u.ufunction(override=True)
    def execute(self, context):
        try:
            {'OpenWeak02': open_weak02, 'OpenSelected': open_selected,
             'AddNiagara': add_selected_niagara, 'Apply': apply_current}[str(self.get_editor_property('Data').name)]()
        except Exception as error:
            u.log_error(str(error))
            u.EditorDialog.show_message('Khazan Combat VFX', str(error), u.AppMsgType.OK)



def register_menus():
    global _preview_handle
    menus = u.ToolMenus.get()
    tools = menus.extend_menu('LevelEditor.MainMenu.Tools')
    menu = tools.add_sub_menu('KhazanCombatVFX', 'KhazanCombatVFX', 'KhazanCombatVFX', 'Khazan VFX')
    for name, label in [('OpenWeak02', 'WeakAttack02 VFX 열기'),
                        ('OpenSelected', '선택한 공격 애니메이션 VFX 열기'),
                        ('AddNiagara', '선택한 Niagara를 현재 시퀀스에 추가'),
                        ('Apply', '현재 시퀀서를 공격에 적용')]:
        entry = KZCombatVFXMenuEntry()
        entry.init_entry('KhazanCombatVFX', menu.menu_name, 'CombatVFX', name, label, '')
        menu.add_menu_entry_object(entry)
    toolbar = menus.extend_menu('Sequencer.MainToolBar')
    entry = KZCombatVFXMenuEntry()
    entry.init_entry('KhazanCombatVFX', toolbar.menu_name, 'KhazanCombatVFX', 'Apply',
                     '공격에 적용', '현재 Niagara 배치와 Life Cycle을 공격 몽타주에 저장합니다.')
    data = entry.get_editor_property('Data')
    advanced = data.get_editor_property('Advanced')
    advanced.set_editor_property('EntryType', u.MultiBlockType.TOOL_BAR_BUTTON)
    data.set_editor_property('Advanced', advanced)
    entry.set_editor_property('Data', data)
    toolbar.add_menu_entry_object(entry)
    menus.refresh_all_widgets()
    if _preview_handle is None:
        _preview_handle = u.register_slate_post_tick_callback(_tick_preview)
