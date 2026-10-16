"""Owned, unsaved actual Halberd Rim playback QA; no native or package edits."""
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
VERIFY_MAIN = os.environ.get('KZ_MONSTER_VFX_RIM_VERIFY_MAIN') == '1'
DIAGNOSTIC = os.environ.get('KZ_MONSTER_VFX_RIM_DIAGNOSTIC') == '1'
assert WORK == (MAIN if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan'))
OUT = Path(os.environ['KZ_MONSTER_VFX_RIM_REPORT']).resolve()
assert OUT.is_relative_to((MAIN / 'Saved/ImportReports/MonsterVFX_20261008' / ('MainRimQA' if VERIFY_MAIN else 'PrivateRimQA')).resolve())
ASSET = '/Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Animations/Damage/Damage_Disease'
BP = '/Game/Bluprints/Monsters/BP_Monster_HalberdElite.BP_Monster_HalberdElite_C'
TAG = 'KZOwnedMonsterRimQA20261010'
REPORT = {'status': 'running', 'project': str(WORK), 'asset': ASSET, 'blueprint': BP,
    'verification': 'fresh_saved_Main_targeted_rim_real_rhi' if VERIFY_MAIN else 'private_candidate_targeted_rim_real_rhi', 'package_saves': 0,
    'asset_mutations': 0, 'captures': [], 'overlay_samples': [],
    'boundary': 'Unsaved actor in own PIE only. Weapon closeup cameras, disabled QA fill lights, cadence, stage and deadline are QA settings. Original level lighting and native full-suite requirement remain unchanged.',
    'qa_camera_and_light': {'closeup_origin': 'actual weapon bounds center + 0.4*world extent.z',
        'closeup_radius': '0.55*max actual weapon world extent', 'distance_radius_multiplier': 3.0, 'fov_degrees': 38.0,
        'azimuth_directions': 'owner +/-forward+right, and 0.15*forward+right grazing view', 'fill_light_intensity': 0.0,
        'fill_revision_reason': 'Attempt3 used 5000 candelas and clipped the white weapon. Disable supplemental fill to inspect original red2 additive Rim under unchanged level lighting.',
        'fill_attenuation_radius': '6*max actual weapon world extent', 'source': 'Assistant QA settings; no original/gameplay claim'}}
REPORT['diagnostic_mode'] = DIAGNOSTIC
manifest_path = WORK / 'Binaries/Win64/UnrealEditor.modules'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
module_name = manifest['Modules']['Khazan']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
handle = kernel.GetModuleHandleW(module_name)
assert handle, 'Selected native module is not loaded'
buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(handle, buffer, len(buffer))
module_path = Path(buffer.value).resolve()
assert module_path == (WORK / 'Binaries/Win64' / module_name).resolve()
REPORT['loaded_native_module'] = {'path': str(module_path), 'name': module_name,
    'sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(), 'build_id': manifest['BuildId'],
    'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'verification': 'Win32 GetModuleHandleW/GetModuleFileNameW of actual loaded module'}
sequence_path = WORK / ('Content/' + ASSET.removeprefix('/Game/') + '.uasset')
REPORT['sequence_sha256'] = hashlib.sha256(sequence_path.read_bytes()).hexdigest()
START = time.monotonic()
REQUESTED = BUSY = FINISHED = PLAYING = SEEN = False
FOCUS = MESH = CAPTURE = TARGET = SEQUENCE = None
LIGHTS = []
BASELINE = None
CAPTURE_SLOT = -1
DIAGNOSTIC_DONE = False
MATERIAL_HASHES = {}


def object_path(obj):
    return obj.get_path_name() if obj else None


def saved_shader_readback(report_key='saved_shader_readback', filename='SavedShaderReadback.json'):
    """Read actual saved graph links, without opening an editor or changing nodes."""
    lib = unreal.MaterialEditingLibrary
    master_path = '/Game/_Art/Effects/Monsters/Rim/M_MonsterRim'
    instance_path = '/Game/_Art/Effects/Monsters/Rim/MI_MonsterRim'
    master = unreal.load_asset(master_path)
    instance = unreal.load_asset(instance_path)
    assert isinstance(master, unreal.Material) and isinstance(instance, unreal.MaterialInstanceConstant)
    for path in (master_path, instance_path):
        file = WORK / ('Content/' + path.removeprefix('/Game/') + '.uasset')
        actual_sha = hashlib.sha256(file.read_bytes()).hexdigest()
        MATERIAL_HASHES.setdefault(str(file), actual_sha)
        assert actual_sha == MATERIAL_HASHES[str(file)], 'Saved shader bytes changed since initial readback'
    graph = {'master': object_path(master), 'instance': object_path(instance),
        'actual_instance_parent': object_path(instance.get_editor_property('parent')),
        'blend_mode': str(master.get_editor_property('blend_mode')),
        'shading_model': str(master.get_editor_property('shading_model')),
        'material_domain': str(master.get_editor_property('material_domain')),
        'use_material_attributes': master.get_editor_property('use_material_attributes'),
        'instance_base_property_overrides_export_text': instance.get_editor_property('base_property_overrides').export_text(),
        'instance_parameter_arrays_export_text': {field: [item.export_text() for item in instance.get_editor_property(field)]
            for field in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')},
        'skeletal_usage': lib.has_material_usage(master, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH),
        'sha256_before': dict(MATERIAL_HASHES), 'property_roots': {}, 'nodes': []}
    roots = {}
    for name, prop in [('EmissiveColor', unreal.MaterialProperty.MP_EMISSIVE_COLOR), ('Opacity', unreal.MaterialProperty.MP_OPACITY)]:
        root = lib.get_material_property_input_node(master, prop)
        roots[name] = root
        graph['property_roots'][name] = {'node': object_path(root),
            'output': lib.get_material_property_input_node_output_name(master, prop)}
    for node in lib.get_material_expressions(master):
        names = list(lib.get_material_expression_input_names(node))
        inputs = list(lib.get_inputs_for_material_expression(master, node))
        assert len(names) == len(inputs), 'Actual graph input index contract differs'
        row = {'node': object_path(node), 'class': node.get_class().get_name(), 'inputs': []}
        for name, connected in zip(names, inputs):
            output = lib.get_input_node_output_name_for_material_expression(node, connected) if connected else None
            row['inputs'].append({'pin': name, 'node': object_path(connected), 'output_getter_result': str(output) if output is not None else None})
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter)):
            row['parameter_name'] = str(node.get_editor_property('parameter_name'))
            value = node.get_editor_property('default_value')
            row['default_value'] = [value.r, value.g, value.b, value.a] if isinstance(value, unreal.LinearColor) else value
        if isinstance(node, unreal.MaterialExpressionFresnel):
            row['exponent'] = node.get_editor_property('exponent')
            row['base_reflect_fraction'] = node.get_editor_property('base_reflect_fraction')
        if isinstance(node, unreal.MaterialExpressionMultiply):
            row['const_a'] = node.get_editor_property('const_a')
            row['const_b'] = node.get_editor_property('const_b')
        if isinstance(node, unreal.MaterialExpressionConstant):
            row['r'] = node.get_editor_property('r')
        graph['nodes'].append(row)
    reached = set()
    def visit(node):
        if node is None or object_path(node) in reached:
            return
        reached.add(object_path(node))
        for child in lib.get_inputs_for_material_expression(master, node):
            visit(child)
    visit(roots['EmissiveColor'])
    graph['emissive_reachable_nodes'] = sorted(reached)
    graph['emissive_consumes_parameters'] = {name: any(row.get('parameter_name') == name and row['node'] in reached for row in graph['nodes'])
        for name in ('KZVisualRimWeight', 'KZVisualRimColor')}
    REPORT[report_key] = graph
    (OUT / filename).write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
    return graph


def mesh_material_inventory():
    skinned = MESH.get_skeletal_mesh_asset()
    slots = list(MESH.get_material_slot_names())
    return {'component': object_path(MESH), 'predicted_lod': MESH.get_predicted_lod_level(),
        'asset_nanite_enabled': skinned.get_editor_property('nanite_settings').get_editor_property('enabled'),
        'component_disallow_nanite': MESH.get_editor_property('disallow_nanite'),
        'component_force_disable_nanite': None,
        'global_overlay': object_path(MESH.get_overlay_material()),
        'asset_global_overlay': object_path(skinned.get_overlay_material()),
        'component_overlay_slots': [object_path(item) for item in MESH.get_editor_property('material_slots_overlay_material')],
        'slots': [{'index': index, 'name': str(name), 'base_material': object_path(MESH.get_material(index)),
            'component_get_overlay_material_slot': object_path(MESH.get_overlay_material(True, index)),
            'asset_overlay_material': object_path(item.get_editor_property('overlay_material_interface'))}
            for index, (name, item) in enumerate(zip(slots, skinned.get_editor_property('materials')))]}


def compare_same_mid(world, position, overlay, weight):
    """Temporary own-actor slots only. Same actual MID, source weight/RGB, same pose."""
    global DIAGNOSTIC_DONE
    DIAGNOSTIC_DONE = True
    originals = [MESH.get_material(i) for i in range(len(MESH.get_material_slot_names()))]
    slot_overlays = list(MESH.get_editor_property('material_slots_overlay_material'))
    paused = MESH.get_editor_property('pause_anims')
    disallow_nanite = MESH.get_editor_property('disallow_nanite')
    assert isinstance(disallow_nanite, bool), 'Actual editable disallow Nanite baseline is not bool'
    before = mesh_material_inventory()
    result = {'position_seconds': position, 'actual_mid': object_path(overlay), 'actual_weight': weight,
        'actual_color': [getattr(overlay.get_vector_parameter_value('KZVisualRimColor'), field) for field in ('r', 'g', 'b', 'a')],
        'before': before, 'forced_parameters': [], 'source_parameters_unchanged': True,
        'visual_classification': 'Pending Root PNG review; runtime state is not shader/render-pass visual proof.'}
    REPORT['same_mid_diagnostic'] = result
    try:
        MESH.set_editor_property('pause_anims', True, unreal.PropertyAccessChangeNotifyMode.NEVER)
        capture(world, 'Diagnostic_SourceOverlay', position, overlay, weight)
        MESH.set_overlay_material(None)
        for index in range(len(originals)):
            MESH.set_material(index, overlay)
        result['same_mid_base'] = mesh_material_inventory()
        result['base_only_valid'] = result['same_mid_base']['global_overlay'] is None and not any(result['same_mid_base']['component_overlay_slots']) and not any(s['asset_overlay_material'] for s in result['same_mid_base']['slots'])
        capture(world, 'Diagnostic_SameMIDBase', position, None, weight)
        for index, original in enumerate(originals):
            MESH.set_material(index, original)
            MESH.set_overlay_material(overlay, True, index)
        MESH.set_overlay_material(overlay)
        result['explicit_per_slot_overlay'] = mesh_material_inventory()
        capture(world, 'Diagnostic_ExplicitPerSlotOverlay', position, overlay, weight)
        for index, original in enumerate(originals):
            MESH.set_material(index, original)
        MESH.set_editor_property('material_slots_overlay_material', slot_overlays, unreal.PropertyAccessChangeNotifyMode.NEVER)
        # Avoid Editor PostEditChange's full actor construction rerun. Changing
        # the overlay below explicitly dirties render state (MeshComponent.cpp
        # SetOverlayMaterial), so ShouldNaniteSkin re-evaluates this owned flag.
        MESH.set_editor_property('disallow_nanite', True, unreal.PropertyAccessChangeNotifyMode.NEVER)
        MESH.set_overlay_material(None)
        MESH.set_overlay_material(overlay)
        result['nanite_mutation_performed'] = True
        result['classic_source_overlay'] = mesh_material_inventory()
        result['classic_source_overlay_boundary'] = 'Own transient editable disallow_nanite=true only. Hidden force-disable field is never accessed or changed. Source MID RGB/weight and original base/per-slot identities preserved. QA comparison, not metadata value.'
        capture(world, 'Diagnostic_ClassicSourceOverlay', position, overlay, weight)
        # Fifth comparison changes only this owned capture's exposure. Return
        # the owned mesh to its actual source overlay/render flags first.
        MESH.set_editor_property('disallow_nanite', disallow_nanite, unreal.PropertyAccessChangeNotifyMode.NEVER)
        MESH.set_overlay_material(None)
        MESH.set_overlay_material(overlay)
        camera_component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        original_pp = camera_component.get_editor_property('post_process_settings').copy()
        original_pp_text = original_pp.export_text()
        original_blend_weight = camera_component.get_editor_property('post_process_blend_weight')
        method_override = unreal.SystemLibrary.get_console_variable_int_value('r.EyeAdaptation.MethodOverride')
        assert method_override not in (1, 2), 'Global exposure CVar overrides Manual QA camera: ' + str(method_override)
        manual_pp = original_pp.copy()
        for field, value in (('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL),
                ('auto_exposure_apply_physical_camera_exposure', False), ('auto_exposure_bias', 0.),
                ('auto_exposure_bias_curve', None)):
            manual_pp.set_editor_property(field, value)
            manual_pp.set_editor_property('override_' + field, True)
        result['manual_ev0_source_overlay'] = {'actual_material_inventory': mesh_material_inventory(),
            'post_process_settings_before_export_text': original_pp_text,
            'post_process_settings_qa_export_text': manual_pp.export_text(),
            'post_process_blend_weight_before': original_blend_weight,
            'method_override_cvar': method_override,
            'lens_attenuation_cvar': unreal.SystemLibrary.get_console_variable_float_value('r.EyeAdaptation.LensAttenuation'),
            'boundary': 'Assistant camera-only QA: AEM_MANUAL, physical camera exposure=false gives engine EV100=0; bias=0, bias curve=None, blend weight=1. Source MID RGB/weight and assets unchanged. This is not original exposure/radiance metadata.',
            'exposure_measurement_limit': 'SceneCapture exposes settings, not reflected final GPU exposure. PNG comparison is actual rendered evidence; no measured GPU exposure value is claimed.'}
        try:
            camera_component.set_editor_property('post_process_settings', manual_pp, unreal.PropertyAccessChangeNotifyMode.NEVER)
            camera_component.set_editor_property('post_process_blend_weight', 1., unreal.PropertyAccessChangeNotifyMode.NEVER)
            capture(world, 'Diagnostic_ManualEV0_SourceOverlay', position, overlay, weight)
            # Same pose, camera and manual exposure without the overlay lets
            # Root isolate its signal from the other source disease particles.
            MESH.set_overlay_material(BASELINE)
            capture(world, 'Diagnostic_ManualEV0_SamePoseBaseline', position, BASELINE, None)
        finally:
            MESH.set_overlay_material(overlay)
            camera_component.set_editor_property('post_process_settings', original_pp, unreal.PropertyAccessChangeNotifyMode.NEVER)
            camera_component.set_editor_property('post_process_blend_weight', original_blend_weight, unreal.PropertyAccessChangeNotifyMode.NEVER)
        manual_result = result['manual_ev0_source_overlay']
        manual_result['post_process_settings_restored'] = camera_component.get_editor_property('post_process_settings').export_text() == original_pp_text
        manual_result['post_process_blend_weight_restored'] = camera_component.get_editor_property('post_process_blend_weight') == original_blend_weight
        assert manual_result['post_process_settings_restored'] and manual_result['post_process_blend_weight_restored'], 'Own camera postprocess baseline was not exactly restored'
        # Compile only in this owned process, then discard dirty memory on exit.
        # UE GetStatistics submits missing jobs and FinishCompilation() blocks
        # on their completion (MaterialEditingLibrary.cpp 2120-2127).
        master = unreal.load_asset('/Game/_Art/Effects/Monsters/Rim/M_MonsterRim')
        instance = unreal.load_asset('/Game/_Art/Effects/Monsters/Rim/MI_MonsterRim')
        lib = unreal.MaterialEditingLibrary
        recompile = {'boundary': 'Owned-process QA only: RecompileMaterial marks master dirty in memory and updates child parameter caches; no nodes/defaults/parameters are edited, no packages are saved. Graph and disk SHA comparisons are separate from Root visual review.',
            'master': object_path(master), 'instance': object_path(instance), 'actual_mid': object_path(overlay),
            'mid_before': {'weight': overlay.get_scalar_parameter_value('KZVisualRimWeight'),
                'color': [getattr(overlay.get_vector_parameter_value('KZVisualRimColor'), f) for f in ('r', 'g', 'b', 'a')]},
            'dirty_content_packages_before': [object_path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
            'graph_before': saved_shader_readback('shader_before_memory_recompile', 'BeforeMemoryRecompileShaderReadback.json')}
        result['in_memory_recompile_diagnostic'] = recompile
        REPORT['asset_mutations_scope'] = 'Serialized asset edits: zero. The diagnostic in-memory material recompile/dirty state is reported explicitly and discarded without save.'
        stats_start = time.monotonic()
        recompile['statistics_before_export_text'] = {name: lib.get_statistics(obj).export_text()
            for name, obj in [('master', master), ('instance', instance), ('actual_mid', overlay)]}
        recompile['statistics_before_elapsed_seconds'] = time.monotonic()-stats_start
        # This additional capture distinguishes finishing pre-existing missing
        # compilation from the explicit subsequent recompilation.
        capture(world, 'Diagnostic_StatisticsSynced_SourceOverlay', position, overlay, weight)
        compilation_start = time.monotonic()
        recompile['recompile_returned_errors'] = list(lib.recompile_material(master))
        recompile['statistics_after_export_text'] = {name: lib.get_statistics(obj).export_text()
            for name, obj in [('master', master), ('instance', instance), ('actual_mid', overlay)]}
        recompile['recompile_and_statistics_elapsed_seconds'] = time.monotonic()-compilation_start
        assert not recompile['recompile_returned_errors'], 'Explicit in-memory material compilation returned errors'
        recompile['graph_after'] = saved_shader_readback('shader_after_memory_recompile', 'AfterMemoryRecompileShaderReadback.json')
        recompile['graph_readback_unchanged'] = recompile['graph_before'] == recompile['graph_after']
        recompile['mid_after'] = {'weight': overlay.get_scalar_parameter_value('KZVisualRimWeight'),
            'color': [getattr(overlay.get_vector_parameter_value('KZVisualRimColor'), f) for f in ('r', 'g', 'b', 'a')]}
        recompile['same_actual_mid_parameters_preserved'] = recompile['mid_before'] == recompile['mid_after']
        assert recompile['same_actual_mid_parameters_preserved'], 'In-memory compilation changed source MID parameters'
        recompile['dirty_content_packages_after'] = [object_path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        recompile['shader_package_sha256_after'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in MATERIAL_HASHES}
        recompile['shader_package_bytes_unchanged'] = recompile['shader_package_sha256_after'] == MATERIAL_HASHES
        assert recompile['shader_package_bytes_unchanged'], 'In-memory compilation saved shader package bytes'
        for exposure_name, qa_pp, qa_blend in [('OriginalExposure', original_pp, original_blend_weight),
                ('ManualEV0', manual_pp, 1.)]:
            try:
                camera_component.set_editor_property('post_process_settings', qa_pp, unreal.PropertyAccessChangeNotifyMode.NEVER)
                camera_component.set_editor_property('post_process_blend_weight', qa_blend, unreal.PropertyAccessChangeNotifyMode.NEVER)
                MESH.set_overlay_material(overlay)
                capture(world, 'Diagnostic_Recompiled_' + exposure_name + '_SourceOverlay', position, overlay, weight)
                MESH.set_overlay_material(None)
                for index in range(len(originals)):
                    MESH.set_material(index, overlay)
                capture(world, 'Diagnostic_Recompiled_' + exposure_name + '_SameMIDBase', position, None, weight)
                for index, original in enumerate(originals):
                    MESH.set_material(index, original)
                MESH.set_overlay_material(BASELINE)
                capture(world, 'Diagnostic_Recompiled_' + exposure_name + '_SamePoseBaseline', position, BASELINE, None)
            finally:
                for index, original in enumerate(originals):
                    MESH.set_material(index, original)
                MESH.set_overlay_material(overlay)
                camera_component.set_editor_property('post_process_settings', original_pp, unreal.PropertyAccessChangeNotifyMode.NEVER)
                camera_component.set_editor_property('post_process_blend_weight', original_blend_weight, unreal.PropertyAccessChangeNotifyMode.NEVER)
        recompile['camera_postprocess_restored'] = camera_component.get_editor_property('post_process_settings').export_text() == original_pp_text
        recompile['camera_blend_weight_restored'] = camera_component.get_editor_property('post_process_blend_weight') == original_blend_weight
        assert recompile['camera_postprocess_restored'] and recompile['camera_blend_weight_restored']
    finally:
        for index, original in enumerate(originals):
            MESH.set_material(index, original)
        # Component-only array restoration. Never touch skinned asset material slots.
        MESH.set_editor_property('material_slots_overlay_material', slot_overlays, unreal.PropertyAccessChangeNotifyMode.NEVER)
        MESH.set_editor_property('disallow_nanite', disallow_nanite, unreal.PropertyAccessChangeNotifyMode.NEVER)
        MESH.set_overlay_material(None)
        MESH.set_overlay_material(overlay)
        MESH.set_editor_property('pause_anims', paused, unreal.PropertyAccessChangeNotifyMode.NEVER)
    result['after'] = mesh_material_inventory()
    result['restored_base_objects'] = all(MESH.get_material(i) == original for i, original in enumerate(originals))
    result['restored_slot_overlay_objects'] = list(MESH.get_editor_property('material_slots_overlay_material')) == slot_overlays
    result['restored_global_overlay_object'] = MESH.get_overlay_material() == overlay
    result['restored_animation_pause'] = MESH.get_editor_property('pause_anims') == paused
    result['restored_disallow_nanite'] = MESH.get_editor_property('disallow_nanite') == disallow_nanite
    assert all(result[name] for name in ('restored_base_objects', 'restored_slot_overlay_objects', 'restored_global_overlay_object', 'restored_animation_pause', 'restored_disallow_nanite'))
    assert overlay.get_scalar_parameter_value('KZVisualRimWeight') == weight, 'Diagnostic unexpectedly modified source MID weight'


def capture(world, label, position, overlay, weight):
    global TARGET
    component = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
    if TARGET is None:
        TARGET = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        component.set_editor_property('texture_target', TARGET)
        component.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        component.set_editor_property('capture_every_frame', False)
        component.set_editor_property('always_persist_rendering_state', True)
    origin, extent, sphere = unreal.SystemLibrary.get_component_bounds(MESH)
    full_radius = max(extent.x, extent.y, extent.z, 1.)
    target_origin = origin + unreal.Vector(0., 0., extent.z*.4)
    radius = full_radius*.55
    for index, light in enumerate(LIGHTS):
        sign = 1. if index == 0 else -1.
        light.set_actor_location(target_origin + FOCUS.get_actor_forward_vector()*sign*full_radius*1.2 + FOCUS.get_actor_right_vector()*full_radius*.8 + unreal.Vector(0., 0., full_radius*.3), False, False)
        light_component = light.get_component_by_class(unreal.PointLightComponent)
        light_component.set_attenuation_radius(full_radius*6.)
        # QA-only fill is disabled: preserve contrast for source red2 Rim.
        light_component.set_intensity(0.)
    REPORT['qa_fill_light_units'] = [str(light.get_component_by_class(unreal.PointLightComponent).get_editor_property('intensity_units')) for light in LIGHTS]
    views = [('WeaponFrontOblique', 1., .7071067811865476), ('WeaponBackOblique', -1., .7071067811865476),
        ('WeaponGrazing', .15, .9889363528682975)]
    for view, sign, normalization in views:
        direction = (FOCUS.get_actor_forward_vector()*sign + FOCUS.get_actor_right_vector())*normalization
        location = target_origin + direction*radius*3. + unreal.Vector(0, 0, radius*.15)
        CAPTURE.set_actor_location(location, False, False)
        CAPTURE.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target_origin), False)
        component.set_editor_property('fov_angle', 38.)
        component.capture_scene()
        filename = str(len(REPORT['captures'])).zfill(3) + '_Halberd_Rim_' + label + '_' + view + '.png'
        unreal.RenderingLibrary.export_render_target(world, TARGET, str(OUT), filename)
        REPORT['captures'].append({'image': str(OUT / filename), 'label': label, 'view': view, 'position_seconds': position,
            'overlay': object_path(overlay), 'rim_weight': weight, 'actor': FOCUS.get_path_name(),
            'actual_weapon_bounds': {'origin': [origin.x, origin.y, origin.z], 'extent': [extent.x, extent.y, extent.z], 'sphere_radius': sphere},
            'camera_location': [location.x, location.y, location.z]})


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
    if MATERIAL_HASHES:
        REPORT['shader_package_sha256_after'] = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in MATERIAL_HASHES}
        REPORT['shader_packages_unchanged'] = REPORT['shader_package_sha256_after'] == MATERIAL_HASHES
        if not REPORT['shader_packages_unchanged']:
            error = (error or '') + '\nSaved shader package bytes changed during readonly/transient QA'
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (OUT / 'Driver.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    global REQUESTED, BUSY, FOCUS, MESH, CAPTURE, SEQUENCE, BASELINE, PLAYING, SEEN, CAPTURE_SLOT
    if BUSY or FINISHED:
        return
    BUSY = True
    try:
        elapsed = time.monotonic()-START
        if elapsed > 150:
            finish('Owned Rim PIE QA timed out'); return
        if elapsed < 8:
            return
        if not REQUESTED:
            # These reflected names follow UE 5.8 UFUNCTION ScriptName and
            # PyGenUtil::GetFunctionPythonName/PythonizeName. Check the actual
            # loaded Python types before any unsaved actor/PIE mutation.
            api = {
                'Controller.un_possess': callable(getattr(unreal.Controller, 'un_possess', None)),
                'Pawn.get_controller': callable(getattr(unreal.Pawn, 'get_controller', None)),
                'SkeletalMeshComponent.get_skeletal_mesh_asset': callable(getattr(unreal.SkeletalMeshComponent, 'get_skeletal_mesh_asset', None)),
                'SkeletalMeshComponent.get_position': callable(getattr(unreal.SkeletalMeshComponent, 'get_position', None)),
                'SkeletalMeshComponent.play_animation': callable(getattr(unreal.SkeletalMeshComponent, 'play_animation', None)),
                'MeshComponent.get_overlay_material': callable(getattr(unreal.MeshComponent, 'get_overlay_material', None)),
                'MaterialInstanceDynamic.get_scalar_parameter_value': callable(getattr(unreal.MaterialInstanceDynamic, 'get_scalar_parameter_value', None)),
                'MaterialInstanceDynamic.get_vector_parameter_value': callable(getattr(unreal.MaterialInstanceDynamic, 'get_vector_parameter_value', None)),
                'MeshComponent.get_overlay_material_max_draw_distance': callable(getattr(unreal.MeshComponent, 'get_overlay_material_max_draw_distance', None)),
                'SystemLibrary.get_component_bounds': callable(getattr(unreal.SystemLibrary, 'get_component_bounds', None)),
                'PointLightComponent.set_intensity': callable(getattr(unreal.PointLightComponent, 'set_intensity', None)),
                'PointLightComponent.set_attenuation_radius': callable(getattr(unreal.PointLightComponent, 'set_attenuation_radius', None)),
                'SceneComponent.set_mobility': callable(getattr(unreal.SceneComponent, 'set_mobility', None)),
                'CapsuleComponent.get_scaled_capsule_half_height': callable(getattr(unreal.CapsuleComponent, 'get_scaled_capsule_half_height', None)),
                'Actor.destroy_actor': callable(getattr(unreal.Actor, 'destroy_actor', None)),
                'VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES': hasattr(unreal.VisibilityBasedAnimTickOption, 'ALWAYS_TICK_POSE_AND_REFRESH_BONES'),
            }
            REPORT['api_preflight'] = api
            if DIAGNOSTIC:
                for name in ('get_material_property_input_node', 'get_material_property_input_node_output_name', 'get_material_expressions',
                        'get_material_expression_input_names', 'get_inputs_for_material_expression', 'get_input_node_output_name_for_material_expression', 'has_material_usage'):
                    api['MaterialEditingLibrary.' + name] = callable(getattr(unreal.MaterialEditingLibrary, name, None))
                for name in ('get_material', 'set_material', 'get_material_slot_names', 'set_overlay_material'):
                    api['MeshComponent.' + name] = callable(getattr(unreal.MeshComponent, name, None))
                api['SkinnedMeshComponent.get_predicted_lod_level'] = callable(getattr(unreal.SkinnedMeshComponent, 'get_predicted_lod_level', None))
                api['PropertyAccessChangeNotifyMode.NEVER'] = hasattr(unreal.PropertyAccessChangeNotifyMode, 'NEVER')
                api['SystemLibrary.get_console_variable_int_value'] = callable(getattr(unreal.SystemLibrary, 'get_console_variable_int_value', None))
                api['SystemLibrary.get_console_variable_float_value'] = callable(getattr(unreal.SystemLibrary, 'get_console_variable_float_value', None))
                api['AutoExposureMethod.AEM_MANUAL'] = hasattr(unreal.AutoExposureMethod, 'AEM_MANUAL')
                api['PostProcessSettings.copy'] = callable(getattr(unreal.PostProcessSettings, 'copy', None))
                api['PostProcessSettings.export_text'] = callable(getattr(unreal.PostProcessSettings, 'export_text', None))
                api['MaterialEditingLibrary.recompile_material'] = callable(getattr(unreal.MaterialEditingLibrary, 'recompile_material', None))
                api['MaterialEditingLibrary.get_statistics'] = callable(getattr(unreal.MaterialEditingLibrary, 'get_statistics', None))
                api['MaterialStatistics.export_text'] = callable(getattr(unreal.MaterialStatistics, 'export_text', None))
                api['EditorLoadingAndSavingUtils.get_dirty_content_packages'] = callable(getattr(unreal.EditorLoadingAndSavingUtils, 'get_dirty_content_packages', None))
            assert all(api.values()), 'Actual reflected API preflight failed: ' + json.dumps(api)
            if DIAGNOSTIC:
                saved_shader_readback()
                REPORT['hidden_force_disable_nanite_boundary'] = 'UPROPERTY() is not exposed to Python alias/editor reads (PropertyAccessUtil.cpp CanGetPropertyValue). No getter/setter access, no guessed baseline, field remains unchanged. Editable disallow_nanite controls the fourth diagnostic.'
                REPORT['pso_console_values_readonly'] = {name: unreal.SystemLibrary.get_console_variable_int_value(name) for name in
                    ('r.PSOPrecache.Components', 'r.PSOPrecache.Resources', 'r.PSOPrecache.ProxyCreationStrategy', 'r.SkinCache.CompileShaders', 'r.Nanite.AllowSkinnedMeshes')}
            unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            cls = unreal.load_class(None, BP)
            assert cls, 'Saved Halberd BP does not load'
            actor = actors.spawn_actor_from_class(cls, unreal.Vector())
            assert actor, 'Owned Halberd QA spawn failed'
            actor.set_actor_label(TAG)
            actor.set_editor_property('tags', [unreal.Name(TAG)])
            camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
            camera.set_actor_label(TAG + '_Capture')
            for index in range(2):
                light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector())
                light.set_actor_label(TAG + '_Fill_' + str(index))
                light.get_component_by_class(unreal.PointLightComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            REQUESTED = True
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        if FOCUS is None:
            candidates = unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)
            player = unreal.GameplayStatics.get_player_character(world, 0)
            if not candidates or not player:
                return
            assert len(candidates) == 1, 'Own Rim actor identity is ambiguous'
            FOCUS = candidates[0]
            controller = FOCUS.get_controller()
            REPORT['owned_controller_before_unpossess'] = object_path(controller)
            if controller:
                controller.un_possess()
                controller.set_actor_tick_enabled(False)
            assert FOCUS.get_controller() is None, 'Own actor remains possessed'
            movement = FOCUS.get_component_by_class(unreal.CharacterMovementComponent)
            movement.stop_movement_immediately()
            movement.set_component_tick_enabled(False)
            capsule = FOCUS.get_component_by_class(unreal.CapsuleComponent)
            player_capsule = player.get_component_by_class(unreal.CapsuleComponent)
            location = player.get_actor_location() - player.get_actor_forward_vector()*1500.
            location.z += capsule.get_scaled_capsule_half_height()-player_capsule.get_scaled_capsule_half_height()
            FOCUS.set_actor_location(location, False, False)
            FOCUS.set_actor_rotation(player.get_actor_rotation(), False)
            SEQUENCE = unreal.load_asset(ASSET)
            assert SEQUENCE, 'Saved Rim sequence does not load'
            source_skeleton = SEQUENCE.get_editor_property('skeleton')
            matches = []
            inventory = []
            for candidate in FOCUS.get_components_by_class(unreal.SkeletalMeshComponent):
                skinned = candidate.get_skeletal_mesh_asset()
                skeleton = skinned.get_editor_property('skeleton') if skinned else None
                inventory.append({'component': candidate.get_path_name(), 'skeletal_mesh': object_path(skinned), 'skeleton': object_path(skeleton)})
                if skinned and skeleton == source_skeleton:
                    matches.append(candidate)
            REPORT['actual_blueprint_meshes'] = inventory
            REPORT['source_skeleton'] = object_path(source_skeleton)
            assert len(matches) == 1, 'Original Rim sequence requires one actual compatible weapon owner; matches=' + str(len(matches)) + ' inventory=' + json.dumps(inventory)
            MESH = matches[0]
            REPORT['actual_notify_owner_component'] = MESH.get_path_name()
            REPORT['source_owner_boundary'] = 'The saved source sequence uses Halberd WeaponV2 skeleton; playback remains on its actual compatible BP skeletal component, not the body.'
            REPORT['actual_owner_render_flags'] = {name: MESH.get_editor_property(name) for name in
                ('render_in_main_pass', 'hidden_in_scene_capture', 'owner_no_see', 'only_owner_see', 'use_attach_parent_bound')}
            REPORT['actual_owner_overlay_max_draw_distance'] = MESH.get_overlay_material_max_draw_distance()
            MESH.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            MESH.set_editor_property('pause_anims', False)
            BASELINE = MESH.get_overlay_material()
            CAPTURE = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)
                if a.get_actor_label() == TAG + '_Capture')
            LIGHTS.extend(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PointLight)
                if a.get_actor_label().startswith(TAG + '_Fill_'))
            assert len(LIGHTS) == 2, 'Own unsaved QA fill-light identity differs'
            REPORT['baseline_overlay'] = object_path(BASELINE)
            if DIAGNOSTIC:
                REPORT['actual_material_inventory_before_play'] = mesh_material_inventory()
            capture(world, 'Baseline', 0., BASELINE, None)
            MESH.play_animation(SEQUENCE, False)
            PLAYING = True
            return
        position = MESH.get_position()
        overlay = MESH.get_overlay_material()
        weight = overlay.get_scalar_parameter_value('KZVisualRimWeight') if isinstance(overlay, unreal.MaterialInstanceDynamic) else None
        tint = overlay.get_vector_parameter_value('KZVisualRimColor') if isinstance(overlay, unreal.MaterialInstanceDynamic) else None
        REPORT['overlay_samples'].append({'position_seconds': position, 'overlay': object_path(overlay), 'rim_weight': weight,
            'actual_rim_color': [tint.r, tint.g, tint.b, tint.a] if tint else None})
        if overlay is not None and overlay != BASELINE:
            assert isinstance(overlay, unreal.MaterialInstanceDynamic), 'Rim overlay is not an actual MID consumer'
            SEEN = True
            if DIAGNOSTIC and not DIAGNOSTIC_DONE and weight is not None and weight > 0:
                compare_same_mid(world, position, overlay, weight)
        slot = int(position*8)
        if slot != CAPTURE_SLOT and position <= 2.4:
            CAPTURE_SLOT = slot
            label = 'Active' if overlay is not None and overlay != BASELINE else 'Restored'
            capture(world, label + '_' + str(slot).zfill(2), position, overlay, weight)
        if position >= 2.4:
            assert SEEN, 'Actual saved Rim notify never applied an overlay'
            assert overlay == BASELINE, 'Rim overlay baseline was not restored after the original 1.2s window'
            weights = [s['rim_weight'] for s in REPORT['overlay_samples'] if s['rim_weight'] is not None and s['overlay'] != REPORT['baseline_overlay']]
            assert len(weights) >= 2 and max(weights) > min(weights), 'Actual Rim MID fade was not observed'
            REPORT['checks'] = {'seen_actual_overlay_mid': True, 'seen_actual_weight_fade': True, 'natural_end_baseline_restored': True,
                'owned_actor_unpossessed': FOCUS.get_controller() is None, 'package_saves_zero': True}
            if DIAGNOSTIC:
                assert DIAGNOSTIC_DONE, 'Actual active MID base/overlay diagnostic did not run'
                REPORT['checks']['same_mid_transient_comparison_restored'] = True
            capture(world, 'FinalRestored', position, overlay, weight)
            FOCUS.destroy_actor()
            REPORT['owned_actor_endplay_requested'] = True
            finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        BUSY = False


HANDLE = unreal.register_slate_post_tick_callback(tick)
