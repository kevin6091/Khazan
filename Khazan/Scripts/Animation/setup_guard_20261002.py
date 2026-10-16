"""Author Guard assets in UE 5.8.2, preserving current pose/root/playback data.

Run once via runpy, then setup(). Gameplay is owned by KZGuardAbility.
Original-derived InputEnd candidates and explicit project policies are archived.
"""
import ctypes
import json
import pathlib
import runpy
import uuid

import unreal

PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
GUARD = '/Game/_Art/Player/Animation/InGame/DAS/Guard'
REPORT = PROJECT / 'Saved/GuardImplementation_20261002'
EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
BP = unreal.BlueprintEditorLibrary


def import_guard_array(asset, property_name, texts):
    """Use UE's audited property serializer, with exact Guard path/type whitelist.

    No UObject memory layout writes, property flag changes or global SET commands.
    FArrayProperty::ImportText_Internal ABI matches the existing playback helper.
    """
    if not asset.get_path_name().startswith(GUARD + '/') or property_name not in ('Notifies', 'CompositeSections'):
        raise RuntimeError('Guard authoring scope violation')
    if not isinstance(asset, unreal.AnimSequenceBase) or (property_name == 'CompositeSections' and not isinstance(asset, unreal.AnimMontage)):
        raise RuntimeError('Unexpected Guard array owner')
    if not unreal.SystemLibrary.get_engine_version().startswith('5.8.2-') or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError('Requires audited Win64 UE 5.8.2')
    class StringView(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_int32)]
    dlls = pathlib.Path(unreal.Paths.engine_dir()).resolve() / 'Binaries/Win64'
    core = ctypes.WinDLL(str(dlls / 'UnrealEditor-Core.dll'))
    objects = ctypes.WinDLL(str(dlls / 'UnrealEditor-CoreUObject.dll'))
    find = getattr(objects, '?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes, find.restype = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(StringView), ctypes.c_uint32], ctypes.c_void_p
    def exact(path):
        buffer = ctypes.create_unicode_buffer(path)
        view = StringView(ctypes.cast(buffer, ctypes.c_void_p), len(path))
        return find(None, None, ctypes.byref(view), 0)
    obj, cls = exact(asset.get_path_name()), exact('/Script/Engine.AnimSequenceBase')
    if property_name == 'CompositeSections':
        cls = exact('/Script/Engine.AnimMontage')
    ctor = getattr(core, '??0FName@@QEAA@PEB_W@Z')
    ctor.argtypes, ctor.restype = [ctypes.c_void_p, ctypes.c_wchar_p], ctypes.c_void_p
    name = ctypes.create_string_buffer(16)
    ctor(name, property_name)
    fp = getattr(objects, '?FindPropertyByName@UStruct@@QEBAPEAVFProperty@@VFName@@@Z')
    fp.argtypes, fp.restype = [ctypes.c_void_p, ctypes.c_void_p], ctypes.c_void_p
    prop = fp(cls, name)
    if not obj or not prop:
        raise RuntimeError('Exact Guard object/property not found')
    importer = getattr(objects, '?ImportText_Internal@FArrayProperty@@MEBAPEB_WPEB_WU?$TNotNull@PEAX@@W4EPropertyPointerType@@PEAVUObject@@HPEAVFOutputDevice@@@Z')
    importer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
    importer.restype = ctypes.c_void_p
    body = '(' + ','.join(texts) + ')'
    buffer = ctypes.create_unicode_buffer(body)
    errors = ctypes.c_void_p.in_dll(core, '?GWarn@@3PEAVFFeedbackContext@@EA').value
    if importer(prop, buffer, obj, 1, obj, 0, errors) != ctypes.addressof(buffer) + len(body) * ctypes.sizeof(ctypes.c_wchar):
        raise RuntimeError('Guard array import was incomplete')


def guid_text():
    return uuid.uuid4().hex.upper()


def refresh_notifies(asset):
    track = '__GuardNotifyCacheRefresh'
    AL.add_animation_notify_track(asset, track)
    AL.remove_animation_notify_track(asset, track)


def save(asset):
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


def input_end_plan():
    helpers = runpy.run_path(str(PROJECT / 'Scripts/Animation/retime_ingame_from_metadata.py'), run_name='guard_timing_reader')
    rows = helpers['ROWS']
    metadata = PROJECT / 'Saved/Extracted/InGame_Playback_20261002/Metadata'
    result = []
    for data in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(GUARD, recursive=True):
        if str(data.asset_class_path.asset_name) != 'AnimSequence':
            continue
        path = str(data.package_name)
        row = rows[path]
        asset = data.get_asset()
        name = str(data.asset_name)
        raw, field, source = 0.0, 'User policy: held poses are immediately interruptible', None
        if name == 'Player_Guard_End':
            source = 'BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard/AC_Kazan_DualAxeSword_Com_Guard_End'
        elif name == 'Player_Guard_Start' or name.startswith('Player_Guard_Suc_'):
            source = row['selected_composites'][0]['package']
        if source:
            exports = json.loads((metadata / (source + '.json')).read_text(encoding='utf-8'))
            comp = next(e for e in exports if e['Type'] == 'AnimComposite')
            candidates = [(i, n) for i, n in enumerate(comp['Properties']['Notifies'])
                          if n['NotifyName'] == ('xxCancelGroupAnimTiming' if name == 'Player_Guard_Start' else 'xxEnableCancelSK')
                          and n['LinkValue'] > 0]
            index, event = min(candidates, key=lambda x: x[1]['LinkValue'])
            raw, field = event['LinkValue'], 'Properties.Notifies[%d].LinkValue (%s)' % (index, event['NotifyName'])
        t = helpers['source_to_playback'](row, raw)
        if 'GuardBreak' in name and not name.endswith('_Loop'):
            # GuardBreak 원작 취소 경계 미확인. 아직 소비하지 않는 모션의 임시 authoring 정책.
            t = AL.get_sequence_length(asset) * 0.8
            field = 'Temporary tuning: 80% of current clip duration; GuardBreak runtime not implemented'
        result.append(dict(path=path, source=source, field=field, raw_seconds=raw if source else None,
                           input_end_seconds=t, category='original-derived project mapping' if source else 'project policy / temporary'))
    return sorted(result, key=lambda x: x['path'])


def author_sequence_markers(plan, repair_owned=False):
    for row in plan:
        seq = EAL.load_asset(row['path'])
        existing = list(AL.get_animation_notify_events(seq))
        if any(str(n.get_editor_property('notify_name')) == 'InputEnd' for n in existing) and not repair_owned:
            raise RuntimeError('Preserve existing InputEnd: ' + row['path'])
        tracks = list(AL.get_animation_notify_track_names(seq))
        if repair_owned:
            existing = [n for n in existing if str(n.get_editor_property('notify_name')) != 'InputEnd']
        if 'GuardInputEnd' not in [str(t) for t in tracks]:
            AL.add_animation_notify_track(seq, 'GuardInputEnd')
        track_index = [str(t) for t in AL.get_animation_notify_track_names(seq)].index('GuardInputEnd')
        notify = unreal.AnimNotifyEvent()
        notify.import_text('(NotifyName="InputEnd",Guid=%s,TrackIndex=%d,LinkValue=%.9f,TriggerTimeOffset=%.6f)' %
                           (guid_text(), track_index, row['input_end_seconds'], 0.0001 if row['input_end_seconds'] == 0 else 0.0))
        import_guard_array(seq, 'Notifies', [n.export_text() for n in existing] + [notify.export_text()])
        refresh_notifies(seq)
        save(seq)


def author_montage(plan, repair_owned=False):
    path = GUARD + '/AM_DAS_Player_Guard'
    if EAL.does_asset_exist(path) and not repair_owned:
        raise RuntimeError('Preserve existing Guard montage')
    start_seq = EAL.load_asset(GUARD + '/Player_Guard_Start')
    factory = unreal.AnimMontageFactory()
    factory.set_editor_property('target_skeleton', start_seq.get_editor_property('skeleton'))
    m = EAL.load_asset(path) if repair_owned else unreal.AssetToolsHelpers.get_asset_tools().create_asset('AM_DAS_Player_Guard', GUARD, unreal.AnimMontage, factory)
    segments, sections, events = [], [], []
    offset = 0.0
    times = {row['path']: row for row in plan}
    for index, (section, sequence) in enumerate([('Start','Player_Guard_Start'),('Suc_F','Player_Guard_Suc_F'),
                                               ('Suc_L','Player_Guard_Suc_L'),('Suc_R','Player_Guard_Suc_R'),('End','Player_Guard_End')]):
        seq = EAL.load_asset(GUARD + '/' + sequence)
        length = AL.get_sequence_length(seq)
        seg = unreal.AnimSegment()
        seg.import_text('(AnimReference="/Script/Engine.AnimSequence\'%s\'",StartPos=%.9f,AnimStartTime=0,AnimEndTime=%.9f,AnimPlayRate=1,LoopingCount=1)' % (seq.get_path_name(), offset, length))
        segments.append(seg)
        sections.append('(SectionName="%s",NextSectionName="None",LinkValue=%.9f,LinkedMontage="/Script/Engine.AnimMontage\'%s\'",SlotIndex=0,SegmentIndex=%d,SegmentBeginTime=%.9f,SegmentLength=%.9f,LinkMethod=Absolute,CachedLinkMethod=Absolute)' % (section,offset,m.get_path_name(),index,offset,length))
        notify_obj = unreal.find_object(None,m.get_path_name()+':InputEnd_'+section)
        if not notify_obj:
            notify_obj = unreal.new_object(unreal.AnimNotify_PlayMontageNotify, outer=m, name='InputEnd_' + section)
        notify_obj.set_editor_property('notify_name', 'InputEnd')
        notify = unreal.AnimNotifyEvent()
        notify.import_text('(NotifyName="InputEnd",Notify="/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify\'%s\'",Guid=%s,MontageTickType=BranchingPoint,TrackIndex=0,LinkValue=%.9f,LinkedMontage="/Script/Engine.AnimMontage\'%s\'",SlotIndex=0,SegmentIndex=%d,SegmentBeginTime=%.9f,SegmentLength=%.9f)' % (notify_obj.get_path_name(),guid_text(),offset+times[GUARD+'/'+sequence]['input_end_seconds'],m.get_path_name(),index,offset,length))
        events.append(notify.export_text())
        offset += length
    m.set_editor_property('slot_anim_tracks', [unreal.SlotAnimationTrack(slot_name='DefaultSlot',anim_track=unreal.AnimTrack(anim_segments=segments))])
    rate = m.controller.get_model_interface().get_frame_rate()
    m.controller.set_number_of_frames(unreal.FrameNumber(round(offset * rate.numerator / rate.denominator)), False)
    # Explicit project tuning, not an original verified blend time.
    for prop in ('blend_in', 'blend_out'):
        blend = m.get_editor_property(prop)
        blend.set_editor_property('blend_time', 0.1)
        m.set_editor_property(prop, blend)
    m.set_editor_property('blend_out_trigger_time', 0.0)
    # Controller frame changes move existing notify links. Author exact links after length/property changes.
    import_guard_array(m, 'CompositeSections', sections)
    import_guard_array(m, 'Notifies', events)
    refresh_notifies(m)
    save(m)
    return m


def resample_guard_blendspace(bs):
    """Rebuild derived segment indices through UE's public editor API.

    Replacing SampleData does not call ResampleData in UE 5.8.2's
    PostEditChangeProperty. Duplicated segment indices must not be retained.
    Python does not expose this non-UFUNCTION; call its exported Win64 method
    for this exact Guard asset only. No UObject layout or cache memory writes.
    """
    path = GUARD + '/Locomotion/BS_DAS_Player_Guard.BS_DAS_Player_Guard'
    if bs.get_path_name() != path or not isinstance(bs, unreal.BlendSpace):
        raise RuntimeError('Unexpected Guard Blend Space')
    if not unreal.SystemLibrary.get_engine_version().startswith('5.8.2-') or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError('Requires audited Win64 UE 5.8.2')
    class StringView(ctypes.Structure):
        _fields_ = [('data', ctypes.c_void_p), ('size', ctypes.c_int32)]
    dlls = pathlib.Path(unreal.Paths.engine_dir()).resolve() / 'Binaries/Win64'
    objects = ctypes.WinDLL(str(dlls / 'UnrealEditor-CoreUObject.dll'))
    engine = ctypes.WinDLL(str(dlls / 'UnrealEditor-Engine.dll'))
    find = getattr(objects, '?StaticFindObject@@YAPEAVUObject@@PEAVUClass@@PEAV1@V?$TStringView@_W@@W4EFindObjectFlags@@@Z')
    find.argtypes, find.restype = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(StringView), ctypes.c_uint32], ctypes.c_void_p
    buffer = ctypes.create_unicode_buffer(path)
    view = StringView(ctypes.cast(buffer, ctypes.c_void_p), len(path))
    obj = find(None, None, ctypes.byref(view), 0)
    if not obj:
        raise RuntimeError('Exact Guard Blend Space object not found')
    resample = getattr(engine, '?ResampleData@UBlendSpace@@QEAAXXZ')
    resample.argtypes, resample.restype = [ctypes.c_void_p], None
    resample(obj)


def author_blendspace():
    path = GUARD + '/Locomotion/BS_DAS_Player_Guard'
    # Copy interpolation settings, then rebuild derived data for the new sample order.
    bs = EAL.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(
        '/Game/_Art/Player/Animation/InGame/DAS/Locomotion/LockOn/Walk/BS_DAS_Player_LockOn_Walk', path)
    if not bs:
        raise RuntimeError('Could not create Guard Blend Space')
    samples = []
    for angle, direction in [(-180,'B'),(-135,'LB'),(-90,'L'),(-45,'LF'),(0,'F'),(45,'RF'),(90,'R'),(135,'RB'),(180,'B')]:
        seq = EAL.load_asset(GUARD + '/Locomotion/Player_Guard_Wark_' + direction)
        sample = unreal.BlendSample()
        sample.import_text('(Animation="/Script/Engine.AnimSequence\'%s\'",SampleValue=(X=%s,Y=0,Z=0),RateScale=1)' % (seq.get_path_name(),angle))
        samples.append(sample)
    bs.set_editor_property('sample_data', samples)
    resample_guard_blendspace(bs)
    save(bs)
    return bs


def author_effects_and_ability(montage):
    root = '/Game/Bluprints/AbilitySystem'
    state_path = root+'/Effects/Guard/GE_State_Guard'
    state_bp = EAL.load_asset(state_path) if EAL.does_asset_exist(state_path) else EAL.duplicate_asset(root+'/Effects/GE_Player_StaminaRegenDelay',state_path)
    state = unreal.get_default_object(state_bp.generated_class())
    state.set_editor_property('duration_policy',unreal.GameplayEffectDurationType.INFINITE)
    component = state.get_editor_property('ge_components')[0]
    tags = component.get_editor_property('InheritableGrantedTagsContainer')
    tags.import_text('(CombinedTags=(GameplayTags=((TagName="State.Guarding"))),Added=(GameplayTags=((TagName="State.Guarding"))),Removed=(GameplayTags=))')
    component.set_editor_property('InheritableGrantedTagsContainer',tags)
    BP.compile_blueprint(state_bp)
    save(state_bp)

    cost_path = root+'/Effects/Guard/GE_GuardHit_Stamina'
    cost_bp = EAL.load_asset(cost_path) if EAL.does_asset_exist(cost_path) else EAL.duplicate_asset(root+'/Effects/Cost/GE_Cost_WeakAttack',cost_path)
    cost = unreal.get_default_object(cost_bp.generated_class())
    modifiers = cost.get_editor_property('modifiers')
    magnitude = modifiers[0].get_editor_property('modifier_magnitude')
    magnitude.import_text('(MagnitudeCalculationType=SetByCaller,SetByCallerMagnitude=(DataName="GuardStaminaDamage",DataTag=(TagName="")))')
    modifier = modifiers[0]
    modifier.import_text('(ModifierMagnitude=%s)' % magnitude.export_text())
    modifiers[0] = modifier
    cost.set_editor_property('modifiers',modifiers)
    BP.compile_blueprint(cost_bp)
    save(cost_bp)

    ability_path = root+'/Abilities/Player/Guard/GA_Player_Guard'
    guard_bp = EAL.load_asset(ability_path) if EAL.does_asset_exist(ability_path) else BP.create_blueprint_asset_with_parent(
        ability_path,unreal.load_class(None,'/Script/Khazan.KZGuardAbility'))
    guard = unreal.get_default_object(guard_bp.generated_class())
    guard.set_editor_property('GuardMontage',montage)
    guard.set_editor_property('GuardStateEffect',state_bp.generated_class())
    guard.set_editor_property('GuardHitStaminaEffect',cost_bp.generated_class())
    guard.set_editor_property('GuardHitRecoveryDelayEffect',EAL.load_blueprint_class(root+'/Effects/GE_Player_StaminaRegenDelay'))
    BP.compile_blueprint(guard_bp)
    save(guard_bp)
    return guard_bp


def author_input_and_grant(guard_bp):
    ia = EAL.load_asset('/Game/Input/IA_Guard') if EAL.does_asset_exist('/Game/Input/IA_Guard') else EAL.duplicate_asset('/Game/Input/IA_Dodge','/Game/Input/IA_Guard')
    ia.set_editor_property('value_type',unreal.InputActionValueType.BOOLEAN)
    ia.set_editor_property('triggers',[])
    ia.set_editor_property('modifiers',[])
    save(ia)
    imc = EAL.load_asset('/Game/Input/IMC_Default')
    mappings = imc.get_editor_property('default_key_mappings')
    rows = list(mappings.get_editor_property('mappings'))
    for key_name in ('LeftShift','Gamepad_LeftShoulder'):
        if any(m.get_editor_property('action') == ia and m.get_editor_property('key').export_text() == key_name for m in rows):
            continue
        key = unreal.Key()
        key.import_text(key_name)
        rows.append(unreal.EnhancedActionKeyMapping(action=ia,key=key))
    mappings.set_editor_property('mappings',rows)
    imc.set_editor_property('default_key_mappings',mappings)
    save(imc)
    data = EAL.load_asset('/Game/Data/DA_InputData')
    actions = list(data.get_editor_property('InputActions'))
    row = actions[0].copy()
    row.import_text('(InputTag=(TagName="Input.Action.Guard"),InputAction="/Script/EnhancedInput.InputAction\'%s\'")' % ia.get_path_name())
    if not any(x.get_editor_property('InputAction') == ia for x in actions):
        actions.append(row)
    data.set_editor_property('InputActions',actions)
    save(data)
    definition = EAL.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    grants = list(definition.get_editor_property('InitialAbilityGrants'))
    row = grants[0].copy()
    row.import_text('(AbilityClass="/Script/Engine.BlueprintGeneratedClass\'%s\'",InputTag=(TagName="Input.Action.Guard"))' % guard_bp.generated_class().get_path_name())
    if not any(x.get_editor_property('ability_class') == guard_bp.generated_class() for x in grants):
        grants.append(row)
    definition.set_editor_property('InitialAbilityGrants',grants)
    save(definition)


def setup():
    REPORT.mkdir(parents=True,exist_ok=True)
    if EAL.does_asset_exist(GUARD+'/AM_DAS_Player_Guard'):
        raise RuntimeError('Guard assets already authored; do not repeat setup')
    plan = input_end_plan()
    (REPORT/'InputEndPlan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    author_sequence_markers(plan)
    montage = author_montage(plan)
    blendspace = author_blendspace()
    ability = author_effects_and_ability(montage)
    author_input_and_grant(ability)
    print('Guard assets authored:',montage.get_path_name(),blendspace.get_path_name(),ability.get_path_name(),'InputEnd sequences=',len(plan))


if __name__ == '__main__':
    setup()
