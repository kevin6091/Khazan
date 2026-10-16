"""Root-launched private RHI: natural Apes Death D00 decal pixel isolation.

No asset/shader saves, damage or gameplay edits. Default has no warm-up.
Optional QA flag finishes only the eight actual particle material resources
before BP spawn/PIE; it never rebuilds a material graph or changes particle data.
SceneComponent visibility is restored in finally; engine CaptureScene pushes
deferred render state before rendering (SceneCaptureComponent.cpp:831-835).
"""
from pathlib import Path
import ctypes
import hashlib
import json
import math
import os
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
REPORT_ROOT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA'
OUT = Path(os.environ['KZ_MONSTER_VFX_DECAL_REPORT']).resolve()
assert OUT.is_relative_to(REPORT_ROOT.resolve()) and OUT != REPORT_ROOT.resolve()
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT / 'Driver.json').exists(), 'Fresh diagnostic output required'
assert not any(OUT.glob('*.png')), 'Fresh image output required'
BP = '/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite.BP_Monster_ApesStoneHandElite_C'
SOURCE = '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Death/Death_Die_F'
EVENT = 'KZMVFX_d3f1b3f723e1c147b406fa5c'
TAG = 'KZOwnedMonsterDecalIsolation20261010'
PREPARE_PARTICLE_SHADERS_RAW = os.environ.get('KZ_MONSTER_VFX_DECAL_PREPARE_PARTICLE_SHADERS', '0')
assert PREPARE_PARTICLE_SHADERS_RAW in ('0', '1')
PREPARE_PARTICLE_SHADERS = PREPARE_PARTICLE_SHADERS_RAW == '1'
# QA sampling/staging only; source windows and lifetime remain unchanged.
QA_MARGIN = 1.
PLAN_PATH = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json'
PLAN = json.loads(PLAN_PATH.read_text(encoding='utf-8-sig'))
SOURCE_EVENT = next(e for e in PLAN['events'] if e['event_id'] == EVENT)
assert SOURCE_EVENT['asset'] == SOURCE
assert SOURCE_EVENT['effect_fields']['DecalLifeSpan'] == 9.
LIFETIME = SOURCE_EVENT['effect_fields']['DecalLifeSpan']
CURVE_REGISTRY_PATH = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources/DecalCurveRegistry.json'
CURVE_REGISTRY = json.loads(CURVE_REGISTRY_PATH.read_text(encoding='utf-8-sig'))
CURVE = next(c for c in CURVE_REGISTRY if c['index'] == SOURCE_EVENT['effect_fields']['DecalOpacityCurveIndex'])
assert CURVE['source_package'] == SOURCE_EVENT['decal_opacity_curve']
assert hashlib.sha256(Path(CURVE['source_json']).read_bytes()).hexdigest() == CURVE['source_sha256']
PEAK_KEY = max(CURVE['keys'], key=lambda k: k['Value'])
# Existing GPU adapter: curve_t = saturate(age * TimeScale / LifeSpan) * last_key_time.
# Observe the highest serialized source key, not an inferred cubic maximum.
QA_POSE = SOURCE_EVENT['start_time'] + LIFETIME * PEAK_KEY['Time'] / CURVE['last_time_seconds']
assert SOURCE_EVENT['start_time'] < QA_POSE < SOURCE_EVENT['source']['length']
# Entire clip also creates a blood decal with original LifeSpan30s. Preserve
# each source lifetime; QA checks D00 at9+margin, all decals at max+margin.
CLIP_DECAL_EVENTS = [e for e in PLAN['events'] if e['asset'] == SOURCE
                     and e.get('effect_fields', {}).get('DecalMaterial')]
CLIP_DECAL_LIFETIME_PROOFS = []
for decal_event in CLIP_DECAL_EVENTS:
    raw_lifetime = decal_event['source']['properties']['DecalCreateData']['LifeSpan']
    assert raw_lifetime > 0 and raw_lifetime == decal_event['effect_fields']['DecalLifeSpan']
    CLIP_DECAL_LIFETIME_PROOFS.append({
        'event_id': decal_event['event_id'],
        'material': decal_event['effect_fields']['DecalMaterial'],
        'source_package': decal_event['source']['source_package'],
        'source_field': decal_event['source']['field'] + '.DecalCreateData.LifeSpan',
        'source_sha256': decal_event['source']['source_sha256'],
        'window_start_seconds': decal_event['start_time'],
        'window_end_seconds': decal_event['end_time'],
        'raw_lifetime_seconds': raw_lifetime})
ALL_DECALS_LIFETIME = max(p['raw_lifetime_seconds'] for p in CLIP_DECAL_LIFETIME_PROOFS)


def path(obj):
    return obj.get_path_name() if obj else None


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def asset_file(package):
    return WORK / ('Content/' + package.split('.')[0].removeprefix('/Game/') + '.uasset')


MASK_TEXTURE = '/Game/_Art/Effects/Shared/Textures/MonsterHuman/FT_Line_01'
MASK_CENTER_PROOF = {
    'confirmed_both_actual_masks_center_white': True,
    'expected_actual_textures': {name: MASK_TEXTURE + '.FT_Line_01' for name in ('MaskTex', 'MaskATex')},
    'source_package': 'BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Shock/FT_Line_01',
    'source_png': str(MAIN / 'Metadata/MonsterVFX_20261008/HumanOriginal/Payload/BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Shock/FT_Line_01.png'),
    'source_png_sha256': '0d0d6eb10a961dd1158899aabbf3730b39cfeb6581d1386acedb421c2f912a14',
    'native_texture_sha256': '28e753086d97766c40364580c9a87deda55ea3c806184ee9d1ccbca8c551006b',
    'source_png_dimensions': [512, 512],
    'UV_0_5_bilinear_source_texels': [[255, 255], [256, 255], [255, 256], [256, 256]],
    'source_RGBA_each': [255, 255, 255, 255],
    'boundary': 'Source PNG white center + exact imported asset SHA. Actual GPU texel readback not performed. No texture replacement.'}
assert sha(MASK_CENTER_PROOF['source_png']) == MASK_CENTER_PROOF['source_png_sha256']
assert sha(asset_file(MASK_TEXTURE)) == MASK_CENTER_PROOF['native_texture_sha256']


PROTECTED = [asset_file(SOURCE), asset_file(BP),
    asset_file(SOURCE_EVENT['effect_fields']['DecalMaterial']),
    asset_file('/Game/_Art/Effects/Shared/Materials/MonsterHuman/M_New_Decal_Deferred_D')]
PROTECTED_BEFORE = {str(p): sha(p) for p in PROTECTED}
manifest_file = WORK / 'Binaries/Win64/UnrealEditor.modules'
manifest = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
module_name = manifest['Modules']['Khazan']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
module_handle = kernel.GetModuleHandleW(module_name)
assert module_handle, 'Selected native module is not loaded'
module_buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(module_handle, module_buffer, len(module_buffer))
module_path = Path(module_buffer.value).resolve()
assert module_path == (WORK / 'Binaries/Win64' / module_name).resolve()
REPORT = {'schema': 'Khazan.MonsterVFX.ApesDeathDecalIsolation.v1', 'status': 'running',
    'project': str(WORK), 'blueprint': BP, 'source_sequence': SOURCE, 'expected_event': EVENT,
    'captures': [], 'initialization_observations': [], 'component_samples': [],
    'package_saves': 0, 'asset_mutations': 0, 'shader_writes': 0,
    'overall_visual_pass': False, 'regular_suite_pass_claim': False,
    'verification': 'private_candidate_same_pose_decal_pixel_isolation',
    'source_evidence': {'plan': str(PLAN_PATH), 'plan_sha256': sha(PLAN_PATH),
        'source_package': SOURCE_EVENT['source']['source_package'],
        'source_field': SOURCE_EVENT['source']['field'],
        'source_sha256': SOURCE_EVENT['source']['source_sha256'],
        'window_start': SOURCE_EVENT['start_time'], 'window_end': SOURCE_EVENT['end_time'],
        'effect_fields': SOURCE_EVENT['effect_fields'],
        'all_clip_decal_lifetime_proofs': CLIP_DECAL_LIFETIME_PROOFS},
    'qa_settings': {'requested_sequence_pose_seconds': QA_POSE,
        'observation_time_proof': {'curve_registry': str(CURVE_REGISTRY_PATH), 'curve_registry_sha256': sha(CURVE_REGISTRY_PATH),
            'source_package': CURVE['source_package'], 'source_json': CURVE['source_json'],
            'source_sha256': CURVE['source_sha256'], 'highest_serialized_key': PEAK_KEY,
            'last_key_time': CURVE['last_time_seconds'], 'lifetime_seconds': LIFETIME,
            'source_notify_start_seconds': SOURCE_EVENT['start_time'],
            'formula': 'source_notify_start + source_lifetime * highest_serialized_key.Time / last_key_time; current sequence RateScale1. Actual spawn/dilation/age are read from the live MID, not assumed equal to the request.',
            'boundary': 'QA observation derived from source keys and existing GPU time normalization; not a source event/lifetime edit or a proof of the continuous cubic maximum.'},
        'lifetime_seconds_source': LIFETIME, 'tail_scheduling_margin_seconds': QA_MARGIN,
        'all_clip_max_lifetime_seconds_source': ALL_DECALS_LIFETIME,
        'all_clip_tail_wait_formula': 'max(original clip DecalCreateData.LifeSpan) + QA_MARGIN after natural clip end; conservative even for last occurrence.',
        'staging_distance_cm': 2000., 'fill_intensity': 50., 'fov_degrees': 50.,
        'boundary': 'Sampling/camera/fill/margin are disclosed assistant QA settings, not original gameplay tuning.'},
    'loaded_native_module': {'path': str(module_path), 'name': module_name,
        'sha256': sha(module_path), 'manifest_sha256': sha(manifest_file),
        'build_id': manifest['BuildId'], 'verification': 'Win32 actual loaded module path'},
    'render_boundary': 'Original four masks show owned body/owned PSCs and exact saved DevMap Floor receiver. Extra NoParticles masks show body/floor receiver only without PSC state changes. Decals are SceneComponents: temporary runtime visibility, no primitive-list cast or material replacement.',
    'protected_saved_sha_before': PROTECTED_BEFORE}
REPORT['runtime_mid_mask_center_evidence'] = MASK_CENTER_PROOF
REPORT['particle_shader_preparation'] = {
    'enabled': PREPARE_PARTICLE_SHADERS, 'status': 'pending' if PREPARE_PARTICLE_SHADERS else 'disabled',
    'boundary': 'Optional technical first-use shader readiness comparison only; no source pixel parity, graph edits, particle simulation warm-up or asset saves.'}
START = time.monotonic()
REQUESTED = BUSY = FINISHED = False
FOCUS = MESH = CAPTURE = TARGET = SEQUENCE = FLOOR = None
LIGHTS = []
OWN_NAME = None
BASELINE_MATERIALS = []
BASELINE_OVERLAY = None
PHASE = 'setup'
LAST_SLOT = -1
END_TIME = None
ISOLATED = False


def world_decals(world):
    return [c for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            for c in a.get_components_by_class(unreal.DecalComponent)]


def own(component):
    tags = [str(t) for t in component.get_editor_property('component_tags')]
    return OWN_NAME in tags and 'KZCombatEffect' in tags


def decal_inventory(component):
    material = component.get_decal_material()
    parent = None
    if material:
        try:
            parent = path(material.get_editor_property('parent'))
        except Exception:
            pass  # Material base interfaces have no instance parent.
    scalars = {}
    if isinstance(material, unreal.MaterialInstanceDynamic):
        for name in ('KZDecalSpawnTime', 'KZDecalTimeScale', 'KZDecalLifeSpan', 'KZDecalCurveIndex'):
            scalars[name] = material.get_scalar_parameter_value(unreal.Name(name))
    return {'component': path(component), 'owner': path(component.get_owner()),
        'class': component.get_class().get_name(),
        'tags': [str(t) for t in component.get_editor_property('component_tags')],
        'owned_focus': own(component), 'visible_flag': component.get_editor_property('visible'),
        'hidden_in_game': component.get_editor_property('hidden_in_game'),
        'actually_visible': component.is_visible(), 'active': component.is_active(),
        'decal_material': path(material), 'material_parent': parent,
        'live_mid_scalar_parameters': scalars,
        'world_transform_export_text': component.get_world_transform().export_text(),
        'decal_size': component.get_editor_property('decal_size').export_text(),
        'fade_start_delay': component.get_fade_start_delay(), 'fade_duration': component.get_fade_duration()}


def own_pscs(world):
    return [c for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            for c in a.get_components_by_class(unreal.ParticleSystemComponent) if own(c)]


def apply_decal_visibility(decals, baseline, selected):
    """Change raw visible flag only; no child propagation, transforms or lifespan."""
    for c in decals:
        c.set_visibility(baseline[path(c)] and c in selected, False)


def mid_parameter_readback(material):
    assert isinstance(material, unreal.MaterialInstanceDynamic)
    scalars = {name: material.get_scalar_parameter_value(unreal.Name(name)) for name in
        ('KZDecalSpawnTime', 'KZDecalTimeScale', 'KZDecalLifeSpan', 'KZDecalCurveIndex', 'FadeOut')}
    vectors = {}
    for name in ('Param', 'MaskTexUV', 'MaskATexUV'):
        value = material.get_vector_parameter_value(unreal.Name(name))
        vectors[name] = [value.r, value.g, value.b, value.a]
    textures = {name: path(material.get_texture_parameter_value(unreal.Name(name)))
        for name in ('MaskTex', 'MaskATex')}
    return {'material': path(material), 'scalars': scalars, 'vectors': vectors, 'textures': textures}


def psc_capture_readback(component):
    fields, unavailable = {}, {}
    for name in ('visible', 'hidden_in_game', 'render_in_main_pass', 'render_in_depth_pass', 'cast_shadow'):
        try:
            fields[name] = component.get_editor_property(name)
        except Exception as error:
            unavailable[name] = str(error)
    count_getter = getattr(component, 'get_num_materials', None)
    material_getter = getattr(component, 'get_material', None)
    material_api = callable(count_getter) and callable(material_getter)
    count = count_getter() if material_api else None
    return {'component': path(component), 'owner': path(component.get_owner()),
        'tags': [str(t) for t in component.get_editor_property('component_tags')],
        'template': path(component.get_editor_property('template')), 'active': component.is_active(),
        'renderer_fields': fields, 'unavailable_renderer_fields': unavailable,
        'material_api_available': material_api, 'material_count': count,
        'materials': [path(material_getter(i)) for i in range(count)] if material_api else None}


def capture(world, label, position, decal_target):
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
        light.set_actor_location(origin + FOCUS.get_actor_forward_vector()*radius*(1.8 if index == 0 else -1.8)
            + FOCUS.get_actor_right_vector()*radius + unreal.Vector(0, 0, radius*.5), False, False)
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_attenuation_radius(radius*6.)
        lc.set_intensity(50.)
    # Only the owned QA camera uses the actual floor decal volume. Fill lights
    # keep the previous mesh-bounds calculation above, with no intensity edit.
    camera_origin = decal_target.get_world_transform().translation
    decal_size = decal_target.get_editor_property('decal_size')
    camera_radius = max(abs(decal_size.x), abs(decal_size.y), abs(decal_size.z))
    assert math.isfinite(camera_radius) and camera_radius > 0
    for view, forward, right in (('FrontOblique', 3.8, 1.5), ('Side', .8, 3.8)):
        location = camera_origin + FOCUS.get_actor_forward_vector()*camera_radius*forward + FOCUS.get_actor_right_vector()*camera_radius*right + unreal.Vector(0, 0, camera_radius*.55)
        CAPTURE.set_actor_location(location, False, False)
        CAPTURE.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, camera_origin), False)
        component.set_editor_property('fov_angle', 50.)
        component.capture_scene()
        name = str(len(REPORT['captures'])).zfill(4) + '_Apes_Death_Die_F_' + label + '_' + view + '.png'
        unreal.RenderingLibrary.export_render_target(world, TARGET, str(OUT), name)
        rotation = CAPTURE.get_actor_rotation()
        REPORT['captures'].append({'image': str(OUT/name), 'label': label, 'view': view,
            'position_seconds': position, 'actual_mesh_position_seconds': MESH.get_position(),
            'game_time': unreal.GameplayStatics.get_time_seconds(world),
            'camera_location': [location.x, location.y, location.z],
            'camera_rotation': [rotation.pitch, rotation.yaw, rotation.roll],
            'camera_target_component': path(decal_target),
            'camera_target_world_cm': [camera_origin.x, camera_origin.y, camera_origin.z],
            'camera_radius_cm': camera_radius, 'actual_decal_size_cm': [decal_size.x, decal_size.y, decal_size.z],
            'camera_radius_formula': 'max(abs(actual DecalComponent.DecalSize.X/Y/Z)); unchanged view ratios and FOV50',
            'decals': [decal_inventory(c) for c in world_decals(world)],
            'show_only_primitive_paths': REPORT.get('capture_primitive_paths', [])})


def isolate(world, position):
    single = MESH.get_anim_instance()
    assert isinstance(single, unreal.AnimSingleNodeInstance) and single.get_animation_asset() == SEQUENCE
    decals = world_decals(world)
    baseline = {path(c): c.get_editor_property('visible') for c in decals}
    hidden = {path(c): c.get_editor_property('hidden_in_game') for c in decals}
    own_decals = [c for c in decals if own(c)]
    target = [c for c in own_decals if EVENT in [str(t) for t in c.get_editor_property('component_tags')]]
    assert len(target) == 1, 'Expected one exact own D00 occurrence: ' + json.dumps([decal_inventory(c) for c in decals])
    assert baseline[path(target[0])] and target[0].is_visible(), 'Actual D00 is not initially visible'
    cc = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
    before = {'playing': MESH.is_playing(), 'position': MESH.get_position(), 'rate': MESH.get_play_rate(),
        'pause_anims': MESH.get_editor_property('pause_anims'),
        'mode': cc.get_editor_property('primitive_render_mode'),
        'show_only_actors': list(cc.get_editor_property('show_only_actors')),
        'location': CAPTURE.get_actor_location(), 'rotation': CAPTURE.get_actor_rotation(), 'fov': cc.get_editor_property('fov_angle'),
        'post_process_settings_text': cc.get_editor_property('post_process_settings').export_text(),
        'post_process_blend_weight': cc.get_editor_property('post_process_blend_weight')}
    assert not before['show_only_actors'] and before['position'] == position
    row = {'actual_sequence_pose_seconds': position, 'game_time_before': unreal.GameplayStatics.get_time_seconds(world),
        'all_live_decals_before': [decal_inventory(c) for c in decals],
        'exact_D00_components': [path(c) for c in target], 'captures': []}
    REPORT['decal_isolation'] = row
    row['read_only_render_time_cvars_before_capture'] = {
        'r.RenderTimeFrozen': unreal.SystemLibrary.get_console_variable_int_value('r.RenderTimeFrozen'),
        'r.Test.OverrideTimeMaterialExpressions': unreal.SystemLibrary.get_console_variable_float_value('r.Test.OverrideTimeMaterialExpressions')}
    receiver_primitives = [MESH] + list(FLOOR.get_components_by_class(unreal.PrimitiveComponent))
    primitives = receiver_primitives + own_pscs(world)
    mode_names = [name for name in dir(unreal.SceneCapturePrimitiveRenderMode) if name.endswith('USE_SHOW_ONLY_LIST')]
    assert len(mode_names) == 1
    manual_names = [name for name in dir(unreal.AutoExposureMethod) if name.endswith('MANUAL')]
    assert len(manual_names) == 1
    manual_method = getattr(unreal.AutoExposureMethod, manual_names[0])
    qa_pp = unreal.PostProcessSettings()
    qa_pp.import_text(before['post_process_settings_text'])
    exposure = {'override_auto_exposure_method': True, 'auto_exposure_method': manual_method,
        'override_auto_exposure_apply_physical_camera_exposure': True,
        'auto_exposure_apply_physical_camera_exposure': False,
        'override_auto_exposure_bias': True, 'auto_exposure_bias': 0.,
        'override_auto_exposure_bias_curve': True, 'auto_exposure_bias_curve': None}
    for field, value in exposure.items():
        qa_pp.set_editor_property(field, value)
        assert qa_pp.get_editor_property(field) == value
    row['owned_camera_exposure'] = {'method': manual_names[0], 'physical_camera_exposure': False,
        'bias': 0., 'bias_curve': None, 'blend_weight': 1.,
        'lens_attenuation_read_only': unreal.SystemLibrary.get_console_variable_float_value('r.EyeAdaptation.LensAttenuation'),
        'before_post_process_export_text': before['post_process_settings_text'],
        'qa_post_process_export_text': qa_pp.export_text(),
        'engine_basis': 'SceneCaptureComponent2D.h:86-91 local PostProcessSettings/BlendWeight; Scene.h:913,937,940,946,1951; PostProcessEyeAdaptation.cpp:520-529 gives physical EV1000 when physical exposure false. Bias0/null curve are neutral technical QA settings. Default LensAttenuation0.78 gives manual white-point luminance1; no global exposure CVar or source material edit.'}
    try:
        cc.set_editor_property('post_process_settings', qa_pp)
        cc.set_editor_property('post_process_blend_weight', 1.)
        assert cc.get_editor_property('post_process_settings').export_text() == qa_pp.export_text()
        single.set_playing(False)
        assert MESH.get_anim_instance() == single and MESH.get_position() == position and not MESH.is_playing()
        cc.clear_show_only_components()
        for primitive in primitives:
            cc.show_only_component(primitive)
        cc.set_editor_property('primitive_render_mode', getattr(unreal.SceneCapturePrimitiveRenderMode, mode_names[0]))
        REPORT['capture_primitive_paths'] = [path(c) for c in primitives]
        for label, selected, no_particles in [('Normal', decals, False), ('OnlyOwnDecal', own_decals, False),
                ('WithoutOwnD00', [c for c in decals if c not in target], False), ('OnlyOwnD00', target, False),
                ('OnlyOwnD00NoParticles', target, True),
                ('WithoutOwnD00NoParticles', [c for c in decals if c not in target], True),
                ('NoDecalsNoParticles', [], True)]:
            # QA-only occluder isolation: original four masks keep owned PSCs.
            # Extra masks render the same body/floor receiver, no PSC state edits.
            if no_particles:
                cc.clear_show_only_components()
                for primitive in receiver_primitives:
                    cc.show_only_component(primitive)
                REPORT['capture_primitive_paths'] = [path(c) for c in receiver_primitives]
            apply_decal_visibility(decals, baseline, selected)
            first = len(REPORT['captures'])
            capture(world, label, position, target[0])
            row['captures'].append({'label': label, 'images': [c['image'] for c in REPORT['captures'][first:]],
                'visible_component_paths': [path(c) for c in decals if c.get_editor_property('visible')],
                'particles_excluded_from_capture': no_particles,
                'show_only_primitive_paths': list(REPORT['capture_primitive_paths']),
                'pose': MESH.get_position(), 'game_time': unreal.GameplayStatics.get_time_seconds(world),
                'camera_by_view': {c['view']: [c['camera_location'], c['camera_rotation']] for c in REPORT['captures'][first:]}})
        # Diagnostic overrides are confined to this exact live D00 MID. Original
        # 14 captures above keep their original values and conditions unchanged.
        mid = target[0].get_decal_material()
        assert isinstance(mid, unreal.MaterialInstanceDynamic)
        required_mid_apis = ('get_scalar_parameter_value', 'get_vector_parameter_value',
            'get_texture_parameter_value', 'set_scalar_parameter_value', 'set_vector_parameter_value')
        assert all(callable(getattr(mid, name, None)) for name in required_mid_apis)
        mid_before = mid_parameter_readback(mid)
        vector_before = {name: mid.get_vector_parameter_value(unreal.Name(name))
            for name in ('Param', 'MaskTexUV', 'MaskATexUV')}
        diagnostic = {'before': mid_before, 'groups': [], 'api_preflight': list(required_mid_apis),
            'boundary': 'Temporary runtime MID QA isolation only: curve bypass -1, white Param1, constant texture UV. No source/asset/shader settings or natural lifespan changes.'}
        row['runtime_mid_diagnostics'] = diagnostic
        try:
            apply_decal_visibility(decals, baseline, target)
            for label in ('ACurveBypass', 'BCurveBypassWhiteParam', 'CCurveBypassWhiteParamConstantMaskUV',
                    'DCurveBypassSourceRGBAlpha1', 'ECurveBypassWhiteRGBAlpha0'):
                mid.set_scalar_parameter_value(unreal.Name('KZDecalCurveIndex'), -1.)
                if label != 'ACurveBypass':
                    mid.set_vector_parameter_value(unreal.Name('Param'), unreal.LinearColor(1., 1., 1., 1.))
                if label == 'CCurveBypassWhiteParamConstantMaskUV':
                    # Texture-center white is verified in the source PNG; GPU
                    # texel readback remains unmeasured. Do not replace textures.
                    assert MASK_CENTER_PROOF['confirmed_both_actual_masks_center_white']
                    assert mid_before['textures'] == MASK_CENTER_PROOF['expected_actual_textures']
                    for name in ('MaskTexUV', 'MaskATexUV'):
                        mid.set_vector_parameter_value(unreal.Name(name), unreal.LinearColor(0., 0., .5, .5))
                if label in ('DCurveBypassSourceRGBAlpha1', 'ECurveBypassWhiteRGBAlpha0'):
                    # Remove C's constant-UV override before each alpha test.
                    for name in ('MaskTexUV', 'MaskATexUV'):
                        mid.set_vector_parameter_value(unreal.Name(name), vector_before[name])
                    value = vector_before['Param']
                    alpha_test = (unreal.LinearColor(value.r, value.g, value.b, 1.)
                        if label == 'DCurveBypassSourceRGBAlpha1' else unreal.LinearColor(1., 1., 1., 0.))
                    mid.set_vector_parameter_value(unreal.Name('Param'), alpha_test)
                actual = mid_parameter_readback(mid)
                assert actual['scalars']['KZDecalCurveIndex'] == -1.
                assert all(actual['scalars'][name] == mid_before['scalars'][name] for name in
                    ('KZDecalSpawnTime', 'KZDecalTimeScale', 'KZDecalLifeSpan', 'FadeOut'))
                assert actual['textures'] == mid_before['textures']
                if label in ('BCurveBypassWhiteParam', 'CCurveBypassWhiteParamConstantMaskUV'):
                    assert actual['vectors']['Param'] == [1., 1., 1., 1.]
                if label == 'CCurveBypassWhiteParamConstantMaskUV':
                    assert all(actual['vectors'][name] == [0., 0., .5, .5] for name in ('MaskTexUV', 'MaskATexUV'))
                if label in ('DCurveBypassSourceRGBAlpha1', 'ECurveBypassWhiteRGBAlpha0'):
                    assert all(actual['vectors'][name] == mid_before['vectors'][name] for name in ('MaskTexUV', 'MaskATexUV'))
                    expected = (mid_before['vectors']['Param'][:3] + [1.]
                        if label == 'DCurveBypassSourceRGBAlpha1' else [1., 1., 1., 0.])
                    assert actual['vectors']['Param'] == expected
                first = len(REPORT['captures'])
                capture(world, label, position, target[0])
                group = {'label': label, 'actual_parameters': actual,
                    'images': [c['image'] for c in REPORT['captures'][first:]],
                    'visible_component_paths': [path(c) for c in decals if c.get_editor_property('visible')],
                    'particles_excluded_from_capture': True,
                    'show_only_primitive_paths': list(REPORT['capture_primitive_paths']),
                    'pose': MESH.get_position(), 'game_time': unreal.GameplayStatics.get_time_seconds(world),
                    'camera_by_view': {c['view']: [c['camera_location'], c['camera_rotation']] for c in REPORT['captures'][first:]}}
                diagnostic['groups'].append(group)
                row['captures'].append(group)
        finally:
            mid.set_scalar_parameter_value(unreal.Name('KZDecalCurveIndex'), mid_before['scalars']['KZDecalCurveIndex'])
            for name, value in vector_before.items():
                mid.set_vector_parameter_value(unreal.Name(name), value)
            diagnostic['after_restore'] = mid_parameter_readback(mid)
            diagnostic['restored_before_visibility_finally_and_natural_tail'] = diagnostic['after_restore'] == mid_before
            assert diagnostic['restored_before_visibility_finally_and_natural_tail'], 'Runtime D00 MID restoration failed'
        # Source state/parameters stay untouched; isolate only the capture list.
        pscs = sorted(own_pscs(world), key=path)
        assert len(pscs) == 3, 'Fresh actual tagged own PSC set differs; inspect before drawing producer conclusions'
        psc_before = [psc_capture_readback(c) for c in pscs]
        row['own_PSC_isolation'] = {'before': psc_before, 'groups': [],
            'boundary': 'Same-pose NoDecals, actual Mesh+Floor+one exact tagged PSC. No PSC visibility/state/material edits, warm-up/statistics or source-failure attribution.'}
        apply_decal_visibility(decals, baseline, [])
        for index, psc in enumerate(pscs):
            cc.clear_show_only_components()
            for primitive in receiver_primitives + [psc]:
                cc.show_only_component(primitive)
            REPORT['capture_primitive_paths'] = [path(c) for c in receiver_primitives + [psc]]
            label = 'OnlyOwnPSC' + str(index).zfill(2) + 'NoDecals'
            first = len(REPORT['captures'])
            capture(world, label, position, target[0])
            group = {'label': label, 'actual_PSC_readback': psc_capture_readback(psc),
                'images': [c['image'] for c in REPORT['captures'][first:]],
                'visible_component_paths': [path(c) for c in decals if c.get_editor_property('visible')],
                'show_only_primitive_paths': list(REPORT['capture_primitive_paths']),
                'pose': MESH.get_position(), 'game_time': unreal.GameplayStatics.get_time_seconds(world),
                'camera_by_view': {c['view']: [c['camera_location'], c['camera_rotation']] for c in REPORT['captures'][first:]}}
            assert not group['visible_component_paths']
            row['own_PSC_isolation']['groups'].append(group)
            row['captures'].append(group)
        row['own_PSC_isolation']['after'] = [psc_capture_readback(c) for c in pscs]
        row['own_PSC_isolation']['original_PSC_state_unchanged'] = row['own_PSC_isolation']['after'] == psc_before
        assert row['own_PSC_isolation']['original_PSC_state_unchanged']
        row['same_pose'] = MESH.get_position() == position and all(c['pose'] == position for c in row['captures'])
        row['game_time_after'] = unreal.GameplayStatics.get_time_seconds(world)
        row['same_game_time'] = row['game_time_before'] == row['game_time_after'] and all(c['game_time'] == row['game_time_before'] for c in row['captures'])
        row['same_camera_per_view'] = all(c['camera_by_view'] == row['captures'][0]['camera_by_view'] for c in row['captures'])
        assert row['same_pose'] and row['same_game_time'] and row['same_camera_per_view']
    finally:
        for c in decals:
            c.set_visibility(baseline[path(c)], False)
        cc.clear_show_only_components()
        cc.set_editor_property('show_only_actors', before['show_only_actors'])
        cc.set_editor_property('primitive_render_mode', before['mode'])
        cc.set_editor_property('fov_angle', before['fov'])
        restored_pp = unreal.PostProcessSettings()
        restored_pp.import_text(before['post_process_settings_text'])
        cc.set_editor_property('post_process_settings', restored_pp)
        cc.set_editor_property('post_process_blend_weight', before['post_process_blend_weight'])
        CAPTURE.set_actor_location(before['location'], False, False)
        CAPTURE.set_actor_rotation(before['rotation'], False)
        single.set_playing(before['playing'])
        row['restore'] = {'all_decal_visible_flags': all(c.get_editor_property('visible') == baseline[path(c)] for c in decals),
            'all_decal_hidden_flags': all(c.get_editor_property('hidden_in_game') == hidden[path(c)] for c in decals),
            'animation_instance': MESH.get_anim_instance() == single, 'asset': single.get_animation_asset() == SEQUENCE,
            'position': MESH.get_position() == before['position'], 'playing': MESH.is_playing() == before['playing'],
            'rate': MESH.get_play_rate() == before['rate'], 'pause_anims': MESH.get_editor_property('pause_anims') == before['pause_anims'],
            'capture_mode': cc.get_editor_property('primitive_render_mode') == before['mode'],
            'show_only_actors': list(cc.get_editor_property('show_only_actors')) == before['show_only_actors'],
            'capture_location': CAPTURE.get_actor_location() == before['location'],
            'capture_rotation': CAPTURE.get_actor_rotation() == before['rotation'], 'fov': cc.get_editor_property('fov_angle') == before['fov'],
            'post_process_settings': cc.get_editor_property('post_process_settings').export_text() == before['post_process_settings_text'],
            'post_process_blend_weight': cc.get_editor_property('post_process_blend_weight') == before['post_process_blend_weight']}
        assert all(row['restore'].values()), 'Diagnostic visibility/pose/camera restoration failed'


def finish(error=None):
    global FINISHED
    if FINISHED:
        return
    FINISHED = True
    REPORT['protected_saved_sha_after'] = {str(p): sha(p) for p in PROTECTED}
    REPORT['saved_bytes_unchanged'] = REPORT['protected_saved_sha_after'] == PROTECTED_BEFORE
    if not REPORT['saved_bytes_unchanged']:
        error = (error or '') + '\nProtected saved asset/shader bytes changed'
    log = OUT/'PrivatePIE.log'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    REPORT['material_compile_failures'] = [line for line in text.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used in game' in line]
    if REPORT['material_compile_failures']:
        error = (error or '') + '\nMaterial fallback observed'
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (OUT/'Driver.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def prepare_particle_shaders():
    if not PREPARE_PARTICLE_SHADERS:
        return
    source_driver = REPORT_ROOT / 'Attempt10/Driver.json'
    source_sha = 'd252d3ef8e0a1fa6ea28087876724b5824ddca0743f89d3281f4e785e1baacc1'
    assert sha(source_driver) == source_sha
    observed = json.loads(source_driver.read_text(encoding='utf-8'))
    groups = observed['decal_isolation']['own_PSC_isolation']['before']
    assert observed['status'] == 'passed' and len(groups) == 3
    references = groups[0]['materials'] + groups[1]['materials']
    assert groups[1]['template'] == groups[2]['template'] and groups[1]['materials'] == groups[2]['materials']
    materials = list(dict.fromkeys(references))
    assert len(references) == 9 and len(materials) == 8
    lib = unreal.MaterialEditingLibrary
    assert callable(getattr(lib, 'get_statistics', None))
    fields = ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers',
        'num_pixel_texture_samples', 'num_vertex_texture_samples', 'num_virtual_texture_samples',
        'num_uv_scalars', 'num_interpolator_scalars')
    preparation = REPORT['particle_shader_preparation']
    preparation.update({'source_driver': str(source_driver), 'source_driver_sha256': source_sha,
        'original_slot_reference_count': len(references), 'unique_material_count': len(materials),
        'slot_references': references, 'rows': [],
        'engine_api_source': 'UE5.8 Engine/Source/Editor/MaterialEditor/Private/MaterialEditingLibrary.cpp:2116-2159',
        'engine_contract': 'GetStatistics gets current GMaxRHIShaderPlatform material resource, submits jobs if shader map incomplete, then FinishCompilation. No RecompileMaterial call.',
        'order': 'Before BP load/spawn and editor_request_begin_play; no particles simulated.'})
    total_start = time.monotonic()
    for material_path in materials:
        file = asset_file(material_path)
        before_sha = sha(file)
        if file not in PROTECTED:
            PROTECTED.append(file)
            PROTECTED_BEFORE[str(file)] = before_sha
        obj = unreal.load_asset(material_path)
        assert isinstance(obj, unreal.MaterialInterface) and path(obj) == material_path
        started = time.monotonic()
        stats = lib.get_statistics(obj)
        values = {field: stats.get_editor_property(field) for field in fields}
        after_sha = sha(file)
        preparation['rows'].append({'material': material_path, 'asset_file': str(file),
            'before_sha256': before_sha, 'after_preparation_sha256': after_sha,
            'statistics': values, 'statistics_export_text': stats.export_text(),
            'statistics_call_seconds': time.monotonic()-started})
        assert after_sha == before_sha, 'Particle material asset bytes changed during technical preparation'
        assert values['num_pixel_shader_instructions'] > 0 and values['num_vertex_shader_instructions'] > 0, 'No nonzero material resource statistics returned'
    preparation.update({'status': 'prepared', 'elapsed_seconds': time.monotonic()-total_start,
        'asset_bytes_unchanged_after_preparation': True, 'material_graph_recompile_calls': 0,
        'particle_simulation_warmup_calls': 0, 'asset_saves': 0})


def tick(delta):
    global REQUESTED, BUSY, FOCUS, MESH, CAPTURE, SEQUENCE, FLOOR, OWN_NAME, BASELINE_OVERLAY, PHASE, LAST_SLOT, END_TIME, ISOLATED
    if BUSY or FINISHED:
        return
    BUSY = True
    try:
        elapsed = time.monotonic()-START
        assert elapsed < 180., 'Owned Apes decal isolation timed out'
        if elapsed < 8.:
            return
        if not REQUESTED:
            apis = [(unreal.SceneComponent, 'set_visibility'), (unreal.SceneComponent, 'is_visible'),
                (unreal.DecalComponent, 'get_decal_material'), (unreal.AnimSingleNodeInstance, 'set_playing'),
                (unreal.SceneCaptureComponent, 'clear_show_only_components')]
            REPORT['api_preflight'] = {cls.__name__+'.'+name: callable(getattr(cls, name, None)) for cls, name in apis}
            assert all(REPORT['api_preflight'].values())
            unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            prepare_particle_shaders()
            actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            cls = unreal.load_class(None, BP)
            assert cls
            actor = actors.spawn_actor_from_class(cls, unreal.Vector(2000., 0., 0.))
            actor.set_actor_label(TAG)
            actor.set_editor_property('tags', [unreal.Name(TAG)])
            camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
            camera.set_actor_label(TAG+'_Capture')
            camera.get_component_by_class(unreal.SceneCaptureComponent2D).clear_show_only_components()
            for index in range(2):
                light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector())
                light.set_actor_label(TAG+'_Fill_'+str(index))
                light.get_component_by_class(unreal.PointLightComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            REQUESTED = True
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        if FOCUS is None:
            matches = unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)
            player = unreal.GameplayStatics.get_player_character(world, 0)
            if not matches or not player:
                return
            assert len(matches) == 1
            FOCUS = matches[0]
            OWN_NAME = FOCUS.get_name()
            controller = FOCUS.get_controller()
            if controller:
                controller.un_possess()
                controller.set_actor_tick_enabled(False)
            movement = FOCUS.get_component_by_class(unreal.CharacterMovementComponent)
            movement.stop_movement_immediately()
            movement.set_component_tick_enabled(False)
            capsule = FOCUS.get_component_by_class(unreal.CapsuleComponent)
            player_capsule = player.get_component_by_class(unreal.CapsuleComponent)
            location = player.get_actor_location()-player.get_actor_forward_vector()*2000.
            location.z += capsule.get_scaled_capsule_half_height()-player_capsule.get_scaled_capsule_half_height()
            FOCUS.set_actor_location(location, False, False)
            FOCUS.set_actor_rotation(player.get_actor_rotation(), False)
            MESH = FOCUS.get_editor_property('mesh')
            MESH.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            MESH.set_editor_property('pause_anims', False)
            BASELINE_MATERIALS.extend(MESH.get_material(i) for i in range(MESH.get_num_materials()))
            BASELINE_OVERLAY = MESH.get_overlay_material()
            CAPTURE = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D) if a.get_actor_label() == TAG+'_Capture')
            LIGHTS.extend(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PointLight) if a.get_actor_label().startswith(TAG+'_Fill_'))
            floors = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == 'Floor']
            assert len(floors) == 1, 'Exact saved DevMap Floor receiver is absent/ambiguous'
            FLOOR = floors[0]
            REPORT['floor_receiver'] = path(FLOOR)
            REPORT['floor_receives_decals_readback'] = {path(c): c.get_editor_property('receives_decals')
                for c in FLOOR.get_components_by_class(unreal.PrimitiveComponent)}
            REPORT['floor_geometry_readback'] = []
            for floor_component in FLOOR.get_components_by_class(unreal.PrimitiveComponent):
                bounds_origin, bounds_extent, bounds_sphere = unreal.SystemLibrary.get_component_bounds(floor_component)
                REPORT['floor_geometry_readback'].append({'component': path(floor_component),
                    'world_transform_export_text': floor_component.get_world_transform().export_text(),
                    'bounds_origin_cm': [bounds_origin.x, bounds_origin.y, bounds_origin.z],
                    'bounds_extent_cm': [bounds_extent.x, bounds_extent.y, bounds_extent.z],
                    'bounds_sphere_radius_cm': bounds_sphere,
                    'static_mesh': path(floor_component.get_editor_property('static_mesh')) if isinstance(floor_component, unreal.StaticMeshComponent) else None,
                    'boundary': 'Read-only actual bounds/transform; not a proof of triangle intersection or a geometry edit.'})
            REPORT['actual_body_mesh'] = path(MESH.get_skeletal_mesh_asset())
            SEQUENCE = unreal.load_asset(SOURCE)
            assert SEQUENCE.get_editor_property('skeleton') == MESH.get_skeletal_mesh_asset().get_editor_property('skeleton')
            REPORT['source_sequence_length'] = SEQUENCE.get_play_length()
            MESH.play_animation(SEQUENCE, False)
            PHASE = 'playing'
            return
        if PHASE == 'playing':
            position = MESH.get_position()
            decals = world_decals(world)
            slot = int(position*8.)
            if slot != LAST_SLOT:
                LAST_SLOT = slot
                REPORT['component_samples'].append({'pose': position, 'game_time': unreal.GameplayStatics.get_time_seconds(world),
                    'all_live_decals': [decal_inventory(c) for c in decals]})
            if not ISOLATED and position >= QA_POSE:
                isolate(world, position)
                ISOLATED = True
            if position >= SEQUENCE.get_play_length():
                assert ISOLATED
                MESH.stop()
                END_TIME = unreal.GameplayStatics.get_time_seconds(world)
                REPORT['natural_clip_end_game_time'] = END_TIME
                PHASE = 'tail'
            return
        if PHASE == 'tail':
            waited = unreal.GameplayStatics.get_time_seconds(world)-END_TIME
            if waited < LIFETIME+QA_MARGIN:
                return
            live = [c for c in world_decals(world) if own(c)]
            if 'target_D00_natural_tail' not in REPORT:
                target_live = [c for c in live if EVENT in [str(t) for t in c.get_editor_property('component_tags')]]
                REPORT['target_D00_natural_tail'] = {
                    'wait_after_clip_seconds': waited, 'original_lifetime_seconds': LIFETIME,
                    'qa_margin_seconds': QA_MARGIN,
                    'remaining_target_D00_decals': [decal_inventory(c) for c in target_live],
                    'remaining_other_owned_decals': [decal_inventory(c) for c in live if c not in target_live]}
                assert not target_live, 'Target D00 remains after its original lifespan plus QA margin'
            if waited < ALL_DECALS_LIFETIME+QA_MARGIN:
                return
            REPORT['natural_tail'] = {'wait_after_clip_seconds': waited, 'original_lifetime_seconds': ALL_DECALS_LIFETIME,
                'target_D00_original_lifetime_seconds': LIFETIME,
                'qa_margin_seconds': QA_MARGIN, 'remaining_owned_decals': [decal_inventory(c) for c in live]}
            assert not live, 'Original finite own decals remain after maximum clip source lifespan plus QA margin'
            assert [MESH.get_material(i) for i in range(MESH.get_num_materials())] == BASELINE_MATERIALS and MESH.get_overlay_material() == BASELINE_OVERLAY
            REPORT['checks'] = {'exact_D00_seen': True, 'natural_original_tail_drained': True,
                'target_D00_natural_tail_drained': True,
                'body_materials_and_overlay_restored': True, 'package_saves_zero': True,
                'same_pose_time_camera': True, 'all_temporary_decal_visibility_restored': True}
            FOCUS.destroy_actor()
            finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        BUSY = False


HANDLE = unreal.register_slate_post_tick_callback(tick)
