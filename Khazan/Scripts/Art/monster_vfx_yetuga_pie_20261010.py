"""Read-only saved Yetuga source playback in one owned PIE; mesh-bounds QA."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
VERIFY_MAIN = os.environ.get('KZ_MONSTER_VFX_YETUGA_VERIFY_MAIN') == '1'
DIAGNOSTIC_LATE_RECOVERY = os.environ.get('KZ_MONSTER_VFX_YETUGA_DIAGNOSTIC_LATE_RECOVERY') == '1'
DIAGNOSTIC = os.environ.get('KZ_MONSTER_VFX_YETUGA_DIAGNOSTIC') == '1' or DIAGNOSTIC_LATE_RECOVERY
assert WORK == (MAIN if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan'))
OUT = Path(os.environ['KZ_MONSTER_VFX_YETUGA_REPORT']).resolve()
assert OUT.is_relative_to((MAIN / 'Saved/ImportReports/MonsterVFX_20261008' / ('MainYetugaQA' if VERIFY_MAIN else 'PrivateYetugaQA')).resolve())
BP = '/Game/Bluprints/Monsters/BP_Monster_Yetuga.BP_Monster_Yetuga_C'
TAG = 'KZOwnedMonsterYetugaQA20261010'
ROAR02_EVENT = 'KZMVFX_f7a3c448d031f689d731840f'
ROAR02_TEMPLATE = '/Game/_Art/Effects/Monsters/ApesYetuga/FP_Boss_Yetuga_Roar_02.FP_Boss_Yetuga_Roar_02'
CASES = [
    {'asset': '/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_NormalAtk01_03',
     'source_conservative_lifetime_seconds': 6.,
     'expected_event': 'KZMVFX_825989d49f72cb1802c6905d', 'expected_kind': 'StaticMeshComponent',
     'selection': 'Original Root SurfaceTrail0.9138882517–2.3967527s, foot/hand/body dust. No NI occurrence in this source clip.'},
    {'asset': '/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_RushGrab_Slow',
     'source_conservative_lifetime_seconds': 7.,
     'expected_event': 'KZMVFX_fc87c94a96ad4b0afd491f69', 'expected_kind': 'StaticMeshComponent',
     'selection': 'Original Root SurfaceTrail1.1184531910–2.2008109434s plus RushGrab Falldown ParticleSystem. No NI occurrence in this source clip.'},
    {'asset': '/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Recovery/Recovery_StaminaRecover',
     'source_conservative_lifetime_seconds': 6.,
     'expected_event': 'KZMVFX_74aa5da30f52e254c4a12747', 'expected_kind': 'ParticleSystemComponent',
     'selection': 'Original NI renderer adapter FP_Boss_Yetuga_Roar_03, 0.6730651770–2.3531250203s. Extra case provides NI adapter positive coverage without inventing NI events in the attack clips.'},
]
REPORT = {'status': 'running', 'project': str(WORK), 'blueprint': BP, 'cases': [], 'captures': [],
    'initialization_observations': [],
    'verification': 'fresh_saved_Main_targeted_yetuga_real_rhi' if VERIFY_MAIN else 'private_candidate_targeted_yetuga_real_rhi',
    'package_saves': 0, 'asset_mutations': 0,
    'boundary': 'Saved source notifies run unchanged on actual body mesh. No fabricated hit/damage, pose/material/scale/FX tuning. Mesh-only camera and unsaved fill-light settings are QA choices; full native suite remains required.',
    'qa_settings': {'stage_distance_cm': 2000., 'camera_distance_mesh_radius': 3.8, 'fov_degrees': 50.,
                    'cadence_hz': 8., 'fill_intensity': 50., 'fill_attenuation_mesh_radius': 6.,
                    'fill_revision_reason': 'Assistant QA fill reduced to one hundredth of prior 5000-candela light to avoid white clipping; actual units are recorded. No gameplay or source lighting claim.',
                    'cleanup_scheduling_margin_seconds': 1., 'deadline_wall_seconds': 180.}}
if not DIAGNOSTIC:
    REPORT['quality_review'] = {'status': 'pending_root_visual_observation',
        'boundary': 'Runtime checks and producer counts do not certify visual quality. Root must view the actual positive captures; a clean late negative is not positive evidence.'}
if DIAGNOSTIC:
    REPORT['diagnostic_mode'] = True
    REPORT['diagnostic_isolation'] = []
    REPORT['diagnostic_material_boundary'] = 'Read actual graph/effective mask only. Shader A/B is deferred until Root visually attributes a card to an owned resource. No shader/asset writes or compile/statistics warm-up.'
    if DIAGNOSTIC_LATE_RECOVERY:
        REPORT['diagnostic_late_recovery'] = True
        REPORT['diagnostic_pose_selection_boundary'] = 'Assistant QA selection 2.2 sequence-local seconds, within Root requested 2.0-2.35s. Native8 Sequence position_seconds is world time, not an exact mesh pose; no gameplay timing change.'
TAIL_EVIDENCE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/TailLifetimeEvidence.json'
REPORT['tail_lifetime_evidence'] = {'path': str(TAIL_EVIDENCE),
    'sha256': hashlib.sha256(TAIL_EVIDENCE.read_bytes()).hexdigest(),
    'boundary': 'Original serialized LOD0 lifetime conservative upper bounds 6/7/6 seconds, including disabled emitters; not gameplay changes. Wait that bound plus assistant QA scheduling margin1 second. NI renderer adapter provenance stays separate.'}
manifest_path = WORK / 'Binaries/Win64/UnrealEditor.modules'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
module_name = manifest['Modules']['Khazan']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
module_handle = kernel.GetModuleHandleW(module_name)
assert module_handle, 'Selected native module is not loaded'
buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(module_handle, buffer, len(buffer))
module_path = Path(buffer.value).resolve()
assert module_path == (WORK / 'Binaries/Win64' / module_name).resolve()
REPORT['loaded_native_module'] = {'path': str(module_path), 'name': module_name,
    'sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(), 'build_id': manifest['BuildId'],
    'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'verification': 'Win32 GetModuleHandleW/GetModuleFileNameW of actual loaded module'}
START = time.monotonic()
REQUESTED = BUSY = FINISHED = False
FOCUS = MESH = CAPTURE = TARGET = SEQUENCE = None
LIGHTS = []
BASELINE_MATERIALS = []
BASELINE_OVERLAY = None
OWN_NAME = None
LAST_INITIALIZATION_SLOT = -1
CASE_INDEX = 2 if DIAGNOSTIC_LATE_RECOVERY else (1 if DIAGNOSTIC else 0)
PHASE = 'setup'
END_GAME_TIME = 0.
LAST_SLOT = -1
CASE_RECORD = None
DIAGNOSTIC_CASES_DONE = set()
DIAGNOSTIC_SHADER_HASHES = {}
DIAGNOSTIC_GRAPH = None
# Existing QA3 sample positions, solely for selecting an observed pose; not gameplay timing.
DIAGNOSTIC_POSES = {1: 1.376784324645996, 2: 1.1332849264144897}
if DIAGNOSTIC_LATE_RECOVERY:
    DIAGNOSTIC_POSES[2] = 2.2  # Explicit late source-pose QA selection; not an original gameplay value.
LATE_RECOVERY_TEMPLATE = '/Game/_Art/Effects/Monsters/ApesYetuga/FP_Boss_Yetuga_Roar_01.FP_Boss_Yetuga_Roar_01'


def path(obj):
    return obj.get_path_name() if obj else None


def world_pscs(world):
    return [c for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            for c in a.get_components_by_class(unreal.ParticleSystemComponent)]


def psc_inventory(component):
    tags = [str(t) for t in component.get_editor_property('component_tags')]
    return {'component': path(component), 'owner': path(component.get_owner()),
        'template': path(component.get_editor_property('template')), 'tags': tags,
        'owned_focus': OWN_NAME in tags and 'KZCombatEffect' in tags,
        'active': component.is_active(), 'active_particles': component.get_num_active_particles(),
        'world_transform_export_text': component.get_world_transform().export_text(),
        'materials': [{'slot': i, 'material': path(component.get_material(i))}
                      for i in range(component.get_num_materials())]}


def shared_shader_readback():
    """Actual saved graph connections; no material mutation or compilation API."""
    global DIAGNOSTIC_GRAPH
    if DIAGNOSTIC_GRAPH is not None:
        return DIAGNOSTIC_GRAPH
    name = '/Game/_Art/Effects/Shared/Materials/World/FM_World_SubUV_color_A'
    master = unreal.load_asset(name)
    assert isinstance(master, unreal.Material), 'Actual shared dust master is absent'
    file = WORK / ('Content/' + name.removeprefix('/Game/') + '.uasset')
    DIAGNOSTIC_SHADER_HASHES[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
    lib = unreal.MaterialEditingLibrary
    graph = {'master': path(master), 'sha256': DIAGNOSTIC_SHADER_HASHES[str(file)],
        'material_domain': str(master.get_editor_property('material_domain')),
        'blend_mode': str(master.get_editor_property('blend_mode')),
        'use_material_attributes': master.get_editor_property('use_material_attributes'),
        'property_roots': {}, 'nodes': []}
    roots = {}
    for label, prop in [('EmissiveColor', unreal.MaterialProperty.MP_EMISSIVE_COLOR), ('Opacity', unreal.MaterialProperty.MP_OPACITY)]:
        root = lib.get_material_property_input_node(master, prop)
        roots[label] = root
        graph['property_roots'][label] = {'node': path(root), 'output': lib.get_material_property_input_node_output_name(master, prop)}
    for node in lib.get_material_expressions(master):
        names = list(lib.get_material_expression_input_names(node))
        inputs = list(lib.get_inputs_for_material_expression(master, node))
        assert len(names) == len(inputs), 'Actual graph input index contract differs'
        row = {'node': path(node), 'class': node.get_class().get_name(), 'inputs': []}
        for pin, connected in zip(names, inputs):
            output = lib.get_input_node_output_name_for_material_expression(node, connected) if connected else None
            row['inputs'].append({'pin': pin, 'node': path(connected), 'output': str(output) if output is not None else None})
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter, unreal.MaterialExpressionTextureSampleParameter2D)):
            row['parameter_name'] = str(node.get_editor_property('parameter_name'))
        if isinstance(node, unreal.MaterialExpressionTextureSampleParameter2D):
            row['texture'] = path(node.get_editor_property('texture'))
        if isinstance(node, unreal.MaterialExpressionCustom):
            row['code'] = node.get_editor_property('code')
        graph['nodes'].append(row)
    for label, root in roots.items():
        reached = set()
        def visit(node):
            if node is None or path(node) in reached:
                return
            reached.add(path(node))
            for child in lib.get_inputs_for_material_expression(master, node):
                visit(child)
        visit(root)
        graph[label.lower() + '_reachable_nodes'] = sorted(reached)
    DIAGNOSTIC_GRAPH = graph
    REPORT['diagnostic_shared_shader_readback'] = graph
    (OUT / 'SharedDustShaderReadback.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
    return graph


def effective_material_readback(material):
    result = {'material': path(material), 'class': material.get_class().get_name(), 'textures': {}, 'scalars': {}}
    lib = unreal.MaterialEditingLibrary
    if isinstance(material, unreal.MaterialInstanceConstant):
        result['parent'] = path(material.get_editor_property('parent'))
        result['base_property_overrides_export_text'] = material.get_editor_property('base_property_overrides').export_text()
        result['parameter_arrays_export_text'] = {field: [v.export_text() for v in material.get_editor_property(field)]
            for field in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')}
        for name in ('Tex_Opa', 'Tex_OPA', 'Tex_SubUV'):
            result['textures'][name] = path(lib.get_material_instance_texture_parameter_value(material, name))
        for name in ('SubUV_U', 'SubUV_V', 'DepthFade', 'Opa_Str', 'Opa_Pow'):
            result['scalars'][name] = lib.get_material_instance_scalar_parameter_value(material, name)
        result['opa_subuv_switch_effective'] = lib.get_material_instance_static_switch_parameter_value(material, 'Opa_SubUV_Switch')
        result['static_switch_lookup_boundary'] = 'Library returns false when a switch is absent. Compare the saved graph declarations; this lookup is not original CDO evidence.'
        asset_file = WORK / ('Content/' + material.get_path_name().split('.')[0].removeprefix('/Game/') + '.uasset')
        if asset_file.is_file():
            DIAGNOSTIC_SHADER_HASHES[str(asset_file)] = hashlib.sha256(asset_file.read_bytes()).hexdigest()
    elif isinstance(material, unreal.MaterialInstanceDynamic):
        for name in ('Tex_Opa', 'Tex_OPA', 'Tex_SubUV'):
            result['textures'][name] = path(material.get_texture_parameter_value(name))
        for name in ('SubUV_U', 'SubUV_V', 'DepthFade', 'Opa_Str', 'Opa_Pow'):
            result['scalars'][name] = material.get_scalar_parameter_value(name)
    else:
        result['boundary'] = 'Not a material instance; no guessed effective parameter values.'
    return result


def diagnostic_isolation(world, position):
    """Same engine callback/pose/camera, owned capture filters only; exact restore."""
    capture_component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
    single = MESH.get_anim_instance()
    assert isinstance(single, unreal.AnimSingleNodeInstance), 'Owned source playback is not an actual AnimSingleNodeInstance'
    assert single.get_animation_asset() == SEQUENCE, 'Owned source playback instance has a different animation asset'
    all_pscs = world_pscs(world)
    own_pscs = [c for c in all_pscs if OWN_NAME in [str(t) for t in c.get_editor_property('component_tags')]
                and 'KZCombatEffect' in [str(t) for t in c.get_editor_property('component_tags')]]
    primitives = list(FOCUS.get_components_by_class(unreal.PrimitiveComponent))
    primitives.extend(c for c in own_pscs if c not in primitives)
    before = {'mode': capture_component.get_editor_property('primitive_render_mode'),
        'show_only_actors': list(capture_component.get_editor_property('show_only_actors')),
        'pause_anims': MESH.get_editor_property('pause_anims'),
        'animation_instance': path(single), 'animation_asset': path(single.get_animation_asset()),
        'playing': MESH.is_playing(), 'position': MESH.get_position(), 'play_rate': MESH.get_play_rate(),
        'location': CAPTURE.get_actor_location(), 'rotation': CAPTURE.get_actor_rotation(),
        'fov': capture_component.get_editor_property('fov_angle')}
    assert not before['show_only_actors'], 'New owned camera show-only actor baseline differs'
    assert before['position'] == position, 'Diagnostic source position differs before freezing playback'
    row = {'case_index': CASE_INDEX, 'asset': path(SEQUENCE), 'target_observed_qa3_pose_seconds': DIAGNOSTIC_POSES[CASE_INDEX],
        'actual_position_seconds': position, 'game_time_before': unreal.GameplayStatics.get_time_seconds(world),
        'all_world_pscs': [psc_inventory(c) for c in all_pscs], 'own_primitive_paths': [path(c) for c in primitives],
        'material_readbacks': [], 'captures': [],
        'animation_before': {key: before[key] for key in ('animation_instance', 'animation_asset', 'playing', 'position', 'play_rate', 'pause_anims')},
        'freeze_api': 'Existing AnimSingleNodeInstance.set_playing(False); no skeletal component property writes/reinitialization.',
        'show_only_component_baseline': 'Explicitly cleared when this new owned QA camera was initialized; no external camera was read or changed.',
        'shader_ab_executed': False, 'shader_ab_boundary': 'Requires Root pixel attribution from these isolation captures first.'}
    REPORT['diagnostic_isolation'].append(row)
    own_materials = {}
    for c in own_pscs:
        for i in range(c.get_num_materials()):
            m = c.get_material(i)
            if m:
                own_materials[path(m)] = m
    row['material_readbacks'] = [effective_material_readback(m) for m in own_materials.values()]
    shared_shader_readback()
    mode_type = unreal.SceneCapturePrimitiveRenderMode
    mode_names = [name for name in dir(mode_type) if name.endswith('USE_SHOW_ONLY_LIST')]
    assert len(mode_names) == 1, 'Reflected show-only enum is ambiguous'
    show_mode = getattr(mode_type, mode_names[0])
    row['actual_show_only_mode'] = str(show_mode)
    def sample(label, selected):
        capture_component.clear_show_only_components()
        for primitive in selected:
            capture_component.show_only_component(primitive)
        capture_component.set_editor_property('primitive_render_mode', show_mode)
        start = len(REPORT['captures'])
        capture(world, 'Diagnostic_' + label, position, components(world))
        row['captures'].append({'label': label, 'show_only_components': [path(c) for c in selected],
            'images': [c['image'] for c in REPORT['captures'][start:]], 'position_seconds': MESH.get_position(),
            'camera_by_view': {c['view']: {'location': c['camera_location'], 'rotation': c['diagnostic_camera_rotation']}
                               for c in REPORT['captures'][start:]},
            'game_time': unreal.GameplayStatics.get_time_seconds(world)})
    try:
        # UFUNCTION SetPlaying updates the existing proxy playback flag only for
        # this AnimSequence. Component PostEdit writes can re-register/reset it.
        single.set_playing(False)
        row['frozen_animation'] = {'same_instance': MESH.get_anim_instance() == single,
            'same_asset': single.get_animation_asset() == SEQUENCE,
            'same_position': MESH.get_position() == before['position'],
            'same_play_rate': MESH.get_play_rate() == before['play_rate'], 'not_playing': not MESH.is_playing()}
        assert all(row['frozen_animation'].values()), 'Existing source playback did not freeze without a pose/instance reset'
        capture_component.set_editor_property('primitive_render_mode', before['mode'])
        start = len(REPORT['captures'])
        capture(world, 'Diagnostic_NormalScene', position, components(world))
        row['normal_scene_images'] = [c['image'] for c in REPORT['captures'][start:]]
        row['normal_position_seconds'] = MESH.get_position()
        row['normal_camera_by_view'] = {c['view']: {'location': c['camera_location'], 'rotation': c['diagnostic_camera_rotation']}
                                       for c in REPORT['captures'][start:]}
        sample('OwnFocusAndTaggedWorldPSCs', primitives)
        sample('OwnFocusWithoutPSCs', [c for c in primitives if not isinstance(c, unreal.ParticleSystemComponent)])
        # Filter existing own primitive proxies; do not deactivate, retime, or mutate PSCs.
        templates = sorted({path(c.get_editor_property('template')) for c in own_pscs if c.is_active() and c.get_num_active_particles()})
        if DIAGNOSTIC_LATE_RECOVERY and CASE_INDEX == 2:
            matching_roar = [c for c in own_pscs if path(c.get_editor_property('template')) == LATE_RECOVERY_TEMPLATE]
            row['late_recovery_target_template'] = LATE_RECOVERY_TEMPLATE
            row['late_recovery_target_components'] = [psc_inventory(c) for c in matching_roar]
            assert matching_roar, 'Late Recovery did not retain the exact own tagged Roar_01 component'
            # Include its proxy even if the sampled active-particle count is zero.
            templates = sorted(set(templates) | {LATE_RECOVERY_TEMPLATE})
        for index, template in enumerate(templates):
            matching = [c for c in own_pscs if path(c.get_editor_property('template')) == template]
            suffix = 'Roar01' if DIAGNOSTIC_LATE_RECOVERY and template == LATE_RECOVERY_TEMPLATE else 'Template' + str(index).zfill(2)
            sample('WithoutOwn' + suffix, [c for c in primitives if c not in matching])
            row['captures'][-1]['excluded_template'] = template
            sample('OnlyOwn' + suffix, [c for c in primitives if not isinstance(c, unreal.ParticleSystemComponent)] + matching)
            row['captures'][-1]['included_template'] = template
        row['game_time_after'] = unreal.GameplayStatics.get_time_seconds(world)
        row['same_pose'] = (MESH.get_anim_instance() == single and single.get_animation_asset() == SEQUENCE
            and MESH.get_position() == position and row['normal_position_seconds'] == position
            and all(c['position_seconds'] == position for c in row['captures']))
        row['same_game_time'] = row['game_time_before'] == row['game_time_after']
        row['same_camera_per_view'] = all(c['camera_by_view'] == row['normal_camera_by_view'] for c in row['captures'])
        assert row['same_pose'] and row['same_game_time'] and row['same_camera_per_view'], 'Diagnostic comparison advanced the source pose/world time/camera'
    finally:
        capture_component.clear_show_only_components()
        capture_component.set_editor_property('show_only_actors', before['show_only_actors'])
        capture_component.set_editor_property('primitive_render_mode', before['mode'])
        capture_component.set_editor_property('fov_angle', before['fov'])
        CAPTURE.set_actor_location(before['location'], False, False)
        CAPTURE.set_actor_rotation(before['rotation'], False)
        single.set_playing(before['playing'])
        row['restore'] = {'primitive_mode': capture_component.get_editor_property('primitive_render_mode') == before['mode'],
            'show_only_actors': list(capture_component.get_editor_property('show_only_actors')) == before['show_only_actors'],
            'show_only_components': 'ClearShowOnlyComponents restored the explicitly initialized empty owned list.',
            'pause_anims': MESH.get_editor_property('pause_anims') == before['pause_anims'],
            'animation_instance': MESH.get_anim_instance() == single,
            'animation_asset': single.get_animation_asset() == SEQUENCE,
            'animation_position': MESH.get_position() == before['position'],
            'animation_play_rate': MESH.get_play_rate() == before['play_rate'],
            'animation_playing': MESH.is_playing() == before['playing'],
            'fov': capture_component.get_editor_property('fov_angle') == before['fov'],
            'camera_location': CAPTURE.get_actor_location() == before['location'],
            'camera_rotation': CAPTURE.get_actor_rotation() == before['rotation']}
        assert all(value for value in row['restore'].values()), 'Owned diagnostic camera/pose state restoration failed'


def components(world):
    """Read actual own tagged resources, including world-owned at-location PSCs."""
    result = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        for component in actor.get_components_by_class(unreal.SceneComponent):
            tags = [str(t) for t in component.get_editor_property('component_tags')]
            if OWN_NAME not in tags or 'KZCombatEffect' not in tags:
                continue
            row = {'component': component.get_path_name(), 'class': component.get_class().get_name(),
                'active': component.is_active(), 'tags': tags}
            if isinstance(component, unreal.ParticleSystemComponent):
                row['template'] = path(component.get_editor_property('template'))
                row['active_particles'] = component.get_num_active_particles()
                row['custom_time_dilation'] = component.get_editor_property('custom_time_dilation')
            if isinstance(component, unreal.StaticMeshComponent):
                row['static_mesh'] = path(component.get_editor_property('static_mesh'))
                row['render_in_main_pass'] = component.get_editor_property('render_in_main_pass')
                row['render_in_depth_pass'] = component.get_editor_property('render_in_depth_pass')
                row['cast_shadow'] = component.get_editor_property('cast_shadow')
            result.append(row)
    return result


def capture(world, label, position, owned, callback_delta_seconds=None):
    global TARGET
    component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
    if TARGET is None:
        TARGET = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        component.set_editor_property('texture_target', TARGET)
        component.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        component.set_editor_property('capture_every_frame', False)
        component.set_editor_property('always_persist_rendering_state', True)
    origin, extent, sphere = unreal.SystemLibrary.get_component_bounds(MESH)
    radius = max(extent.x, extent.y, extent.z, 1.)
    for index, light in enumerate(LIGHTS):
        sign = 1. if index == 0 else -1.
        light.set_actor_location(origin + FOCUS.get_actor_forward_vector()*radius*sign*1.8 + FOCUS.get_actor_right_vector()*radius + unreal.Vector(0, 0, radius*.5), False, False)
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_attenuation_radius(radius*6.)
        lc.set_intensity(50.)
    REPORT['qa_fill_light_units'] = [str(light.get_component_by_class(unreal.PointLightComponent).get_editor_property('intensity_units')) for light in LIGHTS]
    for view, forward, right in (('FrontOblique', 3.8, 1.5), ('Side', .8, 3.8)):
        location = origin + FOCUS.get_actor_forward_vector()*radius*forward + FOCUS.get_actor_right_vector()*radius*right + unreal.Vector(0, 0, radius*.55)
        CAPTURE.set_actor_location(location, False, False)
        CAPTURE.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, origin), False)
        component.set_editor_property('fov_angle', 50.)
        component.capture_scene()
        name = str(len(REPORT['captures'])).zfill(4) + '_Yetuga_' + SEQUENCE.get_name() + '_' + label + '_' + view + '.png'
        unreal.RenderingLibrary.export_render_target(world, TARGET, str(OUT), name)
        REPORT['captures'].append({'image': str(OUT / name), 'asset': path(SEQUENCE), 'case_index': CASE_INDEX,
            'label': label, 'view': view, 'position_seconds': position, 'components': owned,
            'sequence_position_seconds': position,
            'world_game_time_seconds': unreal.GameplayStatics.get_time_seconds(world),
            'slate_callback_delta_seconds': callback_delta_seconds,
            'actual_body_mesh_bounds': {'origin': [origin.x, origin.y, origin.z], 'extent': [extent.x, extent.y, extent.z], 'sphere_radius': sphere},
            'camera_location': [location.x, location.y, location.z]})
        if DIAGNOSTIC:
            rotation = CAPTURE.get_actor_rotation()
            REPORT['captures'][-1]['diagnostic_camera_rotation'] = [rotation.pitch, rotation.yaw, rotation.roll]


def finish(error=None):
    global FINISHED
    if FINISHED:
        return
    FINISHED = True
    log_path = OUT / 'PrivatePIE.log'
    log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    REPORT['material_compile_failures'] = [line for line in log.splitlines()
        if 'Failed to compile Material' in line or 'Default Material will be used in game' in line]
    if REPORT['material_compile_failures']:
        error = (error or '') + '\nRHI material fallback: ' + '\n'.join(REPORT['material_compile_failures'])
    if DIAGNOSTIC:
        REPORT['diagnostic_shader_sha256_after'] = {file: hashlib.sha256(Path(file).read_bytes()).hexdigest() for file in DIAGNOSTIC_SHADER_HASHES}
        REPORT['diagnostic_shader_packages_unchanged'] = REPORT['diagnostic_shader_sha256_after'] == DIAGNOSTIC_SHADER_HASHES
        if not REPORT['diagnostic_shader_packages_unchanged']:
            error = (error or '') + '\nDiagnostic shared shader/instance saved bytes changed'
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (OUT / 'Driver.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def begin_case(world):
    global SEQUENCE, CASE_RECORD, PHASE, LAST_SLOT
    case = CASES[CASE_INDEX]
    SEQUENCE = unreal.load_asset(case['asset'])
    assert SEQUENCE and SEQUENCE.get_editor_property('skeleton') == MESH.get_skeletal_mesh_asset().get_editor_property('skeleton'), 'Actual body/source skeleton mismatch'
    asset_file = WORK / ('Content/' + case['asset'].removeprefix('/Game/') + '.uasset')
    CASE_RECORD = {**case, 'sequence_sha256': hashlib.sha256(asset_file.read_bytes()).hexdigest(),
        'sequence_length_seconds': SEQUENCE.get_play_length(), 'component_samples': [], 'seen_expected_event': False,
        'drain_samples': [], 'cleanup_observation_seconds': case['source_conservative_lifetime_seconds'] + 1.}
    if CASE_INDEX == 2 and not DIAGNOSTIC:
        CASE_RECORD['roar02_positive_sampling'] = {'status': 'pending',
            'event': ROAR02_EVENT, 'template': ROAR02_TEMPLATE, 'deferred_playing_capture_samples': 0,
            'criterion': 'Actual exact event/template PSC active_particles > 1; a single source light burst is insufficient.',
            'pixel_review_status': 'pending_root_visual_observation',
            'boundary': 'Only Playing PNG exports wait for the first producer sample; source playback, PS, time, scale, tags and Baseline stay unchanged.'}
    REPORT['cases'].append(CASE_RECORD)
    capture(world, 'Baseline', 0., components(world))
    MESH.play_animation(SEQUENCE, False)
    LAST_SLOT = -1
    PHASE = 'playing'


def tick(delta):
    global REQUESTED, BUSY, FOCUS, MESH, CAPTURE, OWN_NAME, CASE_INDEX, PHASE, END_GAME_TIME, LAST_SLOT, BASELINE_OVERLAY, LAST_INITIALIZATION_SLOT
    if BUSY or FINISHED:
        return
    BUSY = True
    try:
        elapsed = time.monotonic()-START
        if elapsed > 180:
            finish('Owned Yetuga QA timed out'); return
        if elapsed < 8:
            return
        if not REQUESTED:
            api = {'Controller.un_possess': callable(getattr(unreal.Controller, 'un_possess', None)),
                'SkeletalMeshComponent.get_skeletal_mesh_asset': callable(getattr(unreal.SkeletalMeshComponent, 'get_skeletal_mesh_asset', None)),
                'SkeletalMeshComponent.get_position': callable(getattr(unreal.SkeletalMeshComponent, 'get_position', None)),
                'SkeletalMeshComponent.play_animation': callable(getattr(unreal.SkeletalMeshComponent, 'play_animation', None)),
                'SkeletalMeshComponent.stop': callable(getattr(unreal.SkeletalMeshComponent, 'stop', None)),
                'SystemLibrary.get_component_bounds': callable(getattr(unreal.SystemLibrary, 'get_component_bounds', None)),
                'PointLightComponent.set_intensity': callable(getattr(unreal.PointLightComponent, 'set_intensity', None)),
                'PointLightComponent.set_attenuation_radius': callable(getattr(unreal.PointLightComponent, 'set_attenuation_radius', None)),
                'SceneComponent.set_mobility': callable(getattr(unreal.SceneComponent, 'set_mobility', None)),
                'AnimSequence.get_play_length': callable(getattr(unreal.AnimSequence, 'get_play_length', None)),
                'VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES': hasattr(unreal.VisibilityBasedAnimTickOption, 'ALWAYS_TICK_POSE_AND_REFRESH_BONES')}
            REPORT['api_preflight'] = api
            if DIAGNOSTIC:
                for name in ('get_anim_instance', 'is_playing', 'get_play_rate'):
                    api['SkeletalMeshComponent.' + name] = callable(getattr(unreal.SkeletalMeshComponent, name, None))
                for name in ('set_playing', 'get_animation_asset'):
                    api['AnimSingleNodeInstance.' + name] = callable(getattr(unreal.AnimSingleNodeInstance, name, None))
                for name in ('show_only_component', 'clear_show_only_components'):
                    api['SceneCaptureComponent.' + name] = callable(getattr(unreal.SceneCaptureComponent, name, None))
                for name in ('get_material_property_input_node', 'get_material_property_input_node_output_name', 'get_material_expressions',
                        'get_material_expression_input_names', 'get_inputs_for_material_expression', 'get_input_node_output_name_for_material_expression',
                        'get_material_instance_texture_parameter_value', 'get_material_instance_scalar_parameter_value', 'get_material_instance_static_switch_parameter_value'):
                    api['MaterialEditingLibrary.' + name] = callable(getattr(unreal.MaterialEditingLibrary, name, None))
                api['SceneComponent.get_world_transform'] = callable(getattr(unreal.SceneComponent, 'get_world_transform', None))
                api['Transform.export_text'] = callable(getattr(unreal.Transform, 'export_text', None))
                api['ActorComponent.get_owner'] = callable(getattr(unreal.ActorComponent, 'get_owner', None))
                api['PrimitiveComponent.get_num_materials'] = callable(getattr(unreal.PrimitiveComponent, 'get_num_materials', None))
                api['SceneCapturePrimitiveRenderMode'] = hasattr(unreal, 'SceneCapturePrimitiveRenderMode')
            assert all(api.values()), 'Actual reflected API preflight failed: ' + json.dumps(api)
            unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            cls = unreal.load_class(None, BP)
            assert cls, 'Saved Yetuga BP does not load'
            # QA staging only: the giant at the origin blocks the saved PlayerStart.
            # Reuse the recorded 2000-cm unsaved QA separation; no product tuning.
            actor = actors.spawn_actor_from_class(cls, unreal.Vector(REPORT['qa_settings']['stage_distance_cm'], 0., 0.))
            assert actor, 'Own Yetuga QA actor spawn failed'
            REPORT['editor_owned_actor_initial_location'] = [actor.get_actor_location().x, actor.get_actor_location().y, actor.get_actor_location().z]
            actor.set_actor_label(TAG)
            actor.set_editor_property('tags', [unreal.Name(TAG)])
            camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
            camera.set_actor_label(TAG + '_Capture')
            if DIAGNOSTIC:
                # Establish the exact empty list on our newly created camera using
                # the exposed API; hidden UPROPERTY arrays are not guessed/read.
                camera.get_component_by_class(unreal.SceneCaptureComponent2D).clear_show_only_components()
            for index in range(2):
                light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector())
                light.set_actor_label(TAG + '_Fill_' + str(index))
                light.get_component_by_class(unreal.PointLightComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            REQUESTED = True
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        initialization_slot = int(elapsed)
        if FOCUS is None and initialization_slot != LAST_INITIALIZATION_SLOT:
            LAST_INITIALIZATION_SLOT = initialization_slot
            REPORT['initialization_observations'].append({'elapsed_seconds': elapsed, 'world': path(world),
                'owned_actor_matches': len(unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)) if world else 0,
                'player': path(unreal.GameplayStatics.get_player_character(world, 0)) if world else None})
        if not world:
            return
        if FOCUS is None:
            matches = unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)
            player = unreal.GameplayStatics.get_player_character(world, 0)
            if not matches or not player:
                return
            assert len(matches) == 1, 'Own Yetuga identity is ambiguous'
            FOCUS = matches[0]
            OWN_NAME = FOCUS.get_name()
            controller = FOCUS.get_controller()
            REPORT['owned_controller_before_unpossess'] = path(controller)
            if controller:
                controller.un_possess()
                controller.set_actor_tick_enabled(False)
            assert FOCUS.get_controller() is None, 'Own Yetuga remains possessed'
            movement = FOCUS.get_component_by_class(unreal.CharacterMovementComponent)
            movement.stop_movement_immediately()
            movement.set_component_tick_enabled(False)
            capsule = FOCUS.get_component_by_class(unreal.CapsuleComponent)
            player_capsule = player.get_component_by_class(unreal.CapsuleComponent)
            location = player.get_actor_location() - player.get_actor_forward_vector()*2000.
            location.z += capsule.get_scaled_capsule_half_height()-player_capsule.get_scaled_capsule_half_height()
            FOCUS.set_actor_location(location, False, False)
            FOCUS.set_actor_rotation(player.get_actor_rotation(), False)
            MESH = FOCUS.get_editor_property('mesh')
            assert MESH and MESH.get_skeletal_mesh_asset(), 'Actual saved Yetuga body mesh is absent'
            REPORT['actual_body_mesh_component'] = MESH.get_path_name()
            REPORT['actual_body_mesh_asset'] = MESH.get_skeletal_mesh_asset().get_path_name()
            REPORT['actual_body_skeleton'] = MESH.get_skeletal_mesh_asset().get_editor_property('skeleton').get_path_name()
            MESH.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            MESH.set_editor_property('pause_anims', False)
            BASELINE_OVERLAY = MESH.get_overlay_material()
            BASELINE_MATERIALS.extend(MESH.get_material(i) for i in range(MESH.get_num_materials()))
            REPORT['baseline_materials'] = [path(m) for m in BASELINE_MATERIALS]
            REPORT['baseline_overlay'] = path(BASELINE_OVERLAY)
            CAPTURE = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D) if a.get_actor_label() == TAG + '_Capture')
            LIGHTS.extend(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PointLight) if a.get_actor_label().startswith(TAG + '_Fill_'))
            assert len(LIGHTS) == 2, 'Own unsaved fill-light identity differs'
            begin_case(world)
            return
        if PHASE == 'playing':
            position = MESH.get_position()
            owned = components(world)
            sample = {'position_seconds': position, 'sequence_position_seconds': position,
                'world_game_time_seconds': unreal.GameplayStatics.get_time_seconds(world),
                'slate_callback_delta_seconds': float(delta), 'components': owned}
            CASE_RECORD['component_samples'].append(sample)
            if any(CASE_RECORD['expected_event'] in c['tags'] and c['class'] == CASE_RECORD['expected_kind'] for c in owned):
                CASE_RECORD['seen_expected_event'] = True
                if CASE_RECORD['expected_kind'] == 'StaticMeshComponent':
                    writers = [c for c in owned if CASE_RECORD['expected_event'] in c['tags'] and c['class'] == 'StaticMeshComponent']
                    assert all(not c['render_in_main_pass'] and not c['render_in_depth_pass'] and not c['cast_shadow'] for c in writers), 'Recovered snow field writer leaked into scene/depth/shadow rendering'
                    CASE_RECORD['writer_scene_passes_disabled'] = True
            slot = int(position*8.)
            positive_sampling = CASE_RECORD.get('roar02_positive_sampling')
            waiting_for_positive = positive_sampling is not None and positive_sampling['status'] == 'pending'
            if waiting_for_positive:
                producers = [c for c in owned if c['class'] == 'ParticleSystemComponent'
                    and ROAR02_EVENT in c['tags'] and c.get('template') == ROAR02_TEMPLATE
                    and c['active'] and c.get('active_particles', 0) > 1]
                if producers:
                    positive_sampling.update(status='producer_observed_pending_pixel_review',
                        first_positive_sample=sample, capture_start_index=len(REPORT['captures']))
                    # Normal scene, both existing views. A producer count is not a visual pass.
                    capture(world, 'Roar02Positive_Normal', position, owned, float(delta))
                    positive_sampling['capture_end_index_exclusive'] = len(REPORT['captures'])
                    LAST_SLOT = slot
                else:
                    positive_sampling['deferred_playing_capture_samples'] += 1
            elif slot != LAST_SLOT:
                LAST_SLOT = slot
                capture(world, 'Playing_' + str(slot).zfill(3), position, owned, float(delta))
            if DIAGNOSTIC and CASE_INDEX not in DIAGNOSTIC_CASES_DONE and position >= DIAGNOSTIC_POSES[CASE_INDEX]:
                diagnostic_isolation(world, position)
                DIAGNOSTIC_CASES_DONE.add(CASE_INDEX)
            if position >= SEQUENCE.get_play_length():
                assert CASE_RECORD['seen_expected_event'], 'Actual saved trail/NI adapter event was not observed: ' + CASE_RECORD['asset']
                if positive_sampling is not None and positive_sampling['status'] == 'pending':
                    positive_sampling.update(status='missing',
                        reason='No exact Roar02 event/template PSC with more than one active particle was observed during actual saved clip playback.')
                capture(world, 'AnimationEnd', position, owned, float(delta))
                CASE_RECORD['animation_end_components'] = owned
                assert all(c.get('custom_time_dilation', 1.) == 1. for c in owned), 'Source lifetime dwell requires actual PSC dilation1'
                MESH.stop()
                END_GAME_TIME = unreal.GameplayStatics.get_time_seconds(world)
                PHASE = 'cleanup'
            return
        if PHASE == 'cleanup':
            owned = components(world)
            drain_elapsed = unreal.GameplayStatics.get_time_seconds(world)-END_GAME_TIME
            if not CASE_RECORD['drain_samples'] or drain_elapsed - CASE_RECORD['drain_samples'][-1]['elapsed_game_seconds'] >= .5:
                CASE_RECORD['drain_samples'].append({'elapsed_game_seconds': drain_elapsed, 'components': owned})
            end_paths = {c['component'] for c in CASE_RECORD['animation_end_components']}
            assert all(c['component'] in end_paths for c in owned), 'New source visual component was created after animation stopped'
            if drain_elapsed < CASE_RECORD['cleanup_observation_seconds']:
                return
            assert not any(c['active'] for c in owned), 'Actual owned active visual resources survived clip cleanup: ' + json.dumps(owned)
            assert not any(c.get('active_particles', 0) for c in owned), 'Original finite particles failed to drain after source lifetime bound'
            assert MESH.get_overlay_material() == BASELINE_OVERLAY, 'Body overlay baseline changed'
            assert [MESH.get_material(i) for i in range(MESH.get_num_materials())] == BASELINE_MATERIALS, 'Body material baseline changed'
            CASE_RECORD['natural_end_and_stop_cleanup'] = {'active_owned_components': 0, 'remaining_inactive_components': owned,
                'materials_restored': True, 'overlay_restored': True, 'position_seconds': MESH.get_position()}
            capture(world, 'EndCleanup', MESH.get_position(), owned)
            CASE_INDEX += 1
            if CASE_INDEX < len(CASES):
                begin_case(world)
            else:
                FOCUS.destroy_actor()
                REPORT['owned_actor_endplay_requested'] = True
                REPORT['checks'] = {'all_three_saved_cases_played': True, 'root_trail_seen_both_attacks': True,
                    'ni_renderer_adapter_seen_recovery': True, 'baseline_materials_restored': True,
                    'no_active_owned_visuals_at_each_clip_cleanup': True, 'package_saves_zero': True}
                if DIAGNOSTIC:
                    expected_cases = {2} if DIAGNOSTIC_LATE_RECOVERY else {1, 2}
                    assert DIAGNOSTIC_CASES_DONE == expected_cases, 'Selected isolation poses were not captured'
                    REPORT['checks'].pop('all_three_saved_cases_played')
                    REPORT['checks'].pop('root_trail_seen_both_attacks')
                    REPORT['checks'].update(selected_saved_cases_played=len(expected_cases),
                        all_owned_capture_filters_restored=True, regular_proof_boundary='Diagnostic subset is not the regular three-case supplemental proof.')
                    if DIAGNOSTIC_LATE_RECOVERY:
                        REPORT['checks'].update(late_recovery_isolation_pose_captured=True, exact_owned_roar01_template_filtered=True)
                    else:
                        REPORT['checks']['both_isolation_poses_captured'] = True
                finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        BUSY = False


HANDLE = unreal.register_slate_post_tick_callback(tick)
