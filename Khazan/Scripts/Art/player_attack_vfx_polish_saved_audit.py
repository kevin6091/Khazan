"""Fresh, read-only polish Art and unchanged8/401 montage saved audit.

Run only through the task-owned commandlet runner after root freezes candidates.
All exports/receipts stay in its new KZ_ATTACK_VFX_POLISH_OUTPUT directory.
No asset authoring, saves, recompiles through editing APIs or editor control.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import re
import struct
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
PRIVATE = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OLD = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
TASK = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUTPUT = Path(os.environ['KZ_ATTACK_VFX_POLISH_OUTPUT']).resolve()
FROZEN_PATH = TASK / 'FrozenCandidateManifest.json'
REPORT = dict(status='running', pid=os.getpid(), project=str(PROJECT),
    asset_saves=0, source_writes=0, rows=[], package_bytes_unchanged=False,
    read_only_compile_api='UE5.8 UMaterialEditingLibrary::GetStatistics, cpp2116: submit/finish resource jobs; no Modify/PostEdit/save.',
    boundary='Positive current-platform resource statistics and saved reflection. Actual RHI and visual parity are separate checks.')
KEEP = []


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_new(path, data):
    require(OUTPUT.is_relative_to((TASK / 'Processes').resolve()) and OUTPUT.is_dir() and
            path.resolve().is_relative_to(OUTPUT), 'Report path escapes new task process')
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def source_path(row):
    ref = row['source_evidence']
    path = (MAIN / ref['path']).resolve()
    require(path.is_relative_to((MAIN / 'Saved').resolve()) and path.is_file(), 'Original source evidence escaped Saved')
    require(sha(path) == ref['sha256'] == row['source_sha256'], 'Original source/hash provenance changed')
    return path


def disk(asset):
    require(asset.startswith('/Game/_Art/Effects/') and '.' not in asset and '..' not in Path(asset).parts,
            'Only exact frozen Effects package names are allowed')
    path = (PROJECT / 'Content' / (asset.removeprefix('/Game/') + '.uasset')).resolve()
    require(path.is_relative_to(PROJECT), 'Shared or escaping writable-package path rejected')
    return path


def export(obj, name):
    directory = OUTPUT / 'SavedArtExports'
    directory.mkdir(exist_ok=True)
    path = directory / (name + '.t3d')
    require(not path.exists(), 'Preserve existing fresh export')
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(path)
    task.exporter = unreal.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    require(unreal.Exporter.run_asset_export_task(task), 'Fresh Art export failed: ' + obj.get_path_name())
    return path, path.read_text(encoding='utf-8-sig')


def native_module():
    manifest = PROJECT / 'Binaries/Win64/UnrealEditor.modules'
    name = read(manifest)['Modules']['Khazan']
    require(Path(name).name == name, 'Unexpected native module path')
    expected = (PROJECT / 'Binaries/Win64' / name).resolve()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = (ctypes.c_wchar_p,)
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32)
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    handle = kernel.GetModuleHandleW(name)
    require(handle, 'Selected Khazan native module is not loaded')
    buffer = ctypes.create_unicode_buffer(32768)
    require(kernel.GetModuleFileNameW(handle, buffer, len(buffer)) and Path(buffer.value).resolve() == expected,
            'Actual loaded module differs from this project manifest')
    if PROJECT == MAIN:
        delivered = read(TASK / 'MainDelivery/Delivered.json')
        require(delivered['module'] == name and delivered['module_manifest_sha256'] == sha(manifest),
                'Main audit must follow the exact new polish delivery')
        expected_hash = next(row['sha256'] for row in delivered['native_files'] if row['destination'].endswith('.dll'))
    else:
        build_directory = read(FROZEN_PATH)['build_evidence_directory']
        require(build_directory.replace('_', '').isalnum(), 'Unexpected frozen build evidence path')
        expected_hash = read(TASK / build_directory / 'Exit.json')['native_binary_hashes']['UnrealEditor-Khazan.dll']
    require(sha(expected) == expected_hash, 'Loaded module bytes differ from successful build/delivery')
    return dict(path=str(expected), sha256=sha(expected), manifest_sha256=sha(manifest), pid=os.getpid())


def montage_audit():
    # Guarded adaptation of the source-audited serializer checks. Old evidence
    # is read-only input, while every new report/export points to OUTPUT.
    source = MAIN / 'Scripts/Art/player_attack_vfx_saved_audit.py'
    code = source.read_text(encoding='utf-8-sig')
    replacements = {
        "EXPECTED_WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')":
            'EXPECTED_WORK = Path(' + repr(str(PROJECT)) + ')',
        "OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'":
            'OLD = MAIN / "Saved/ImportReports/PlayerAttackVFX_20261008"\nOUT = Path(' + repr(str(OUTPUT)) + ')',
        "plan_path = OUT / 'PreparedPlaybackPlan.json'": "plan_path = OLD / 'CombinedPreparedPlaybackPlan.json'",
        "author_path = OUT / 'Authoring/PrivateAuthoring.json'": "author_path = OLD / 'Authoring/CombinedPrivateAuthoring.json'",
        "len(paths) == 6 and len(PLAN['events']) == 347": "len(paths) == 8 and len(PLAN['events']) == 401",
        'six authored montages and 347 source windows': 'eight unchanged montages and 401 source windows',
        "REPORT['checked_event_ids'] == 347": "REPORT['checked_event_ids'] == 401",
        "'SavedAssetAuditExports'": "'CombinedSavedAssetAuditExports'",
        "'SavedAssetAudit.json'": "'CombinedSavedAssetAudit.json'",
        "OUT / 'Authoring' / (name + '_Before.t3d')":
            "OLD / AUTHOR['before_export_directories'][path] / (name + '_Before.t3d')",
        "OUT / 'Authoring' / (name + '_After.t3d')":
            "OLD / AUTHOR['before_export_directories'][path] / (name + '_After.t3d')",
        'Only the private AttackVFX Work project is authorized': 'Only the actual guarded Main/private project is authorized'}
    for before, after in replacements.items():
        require(code.count(before) == 1, 'Saved-audit adapter source drift: ' + before)
        code = code.replace(before, after)
    require(not (OUTPUT / 'CombinedSavedAssetAudit.json').exists(), 'Preserve existing saved montage audit')
    scope = dict(__name__='__main__', __file__=str(source))
    exec(compile(code, str(source), 'exec'), scope)
    result = scope['REPORT']
    require(result['status'] == 'passed', 'Unchanged8/401 saved montage contract failed: ' + result.get('error', ''))
    REPORT['montage_audit'] = dict(path='CombinedSavedAssetAudit.json', sha256=sha(OUTPUT / 'CombinedSavedAssetAudit.json'),
                                 checked_event_ids=result['checked_event_ids'])


def inputs(material, node):
    lib = unreal.MaterialEditingLibrary
    return dict(zip(map(str, lib.get_material_expression_input_names(node)), lib.get_inputs_for_material_expression(material, node)))


def output_name(node, upstream):
    result = unreal.MaterialEditingLibrary.get_input_node_output_name_for_material_expression(node, upstream)
    # This engine Python binding consumes the bool success flag and returns
    # the FString output (native probe contains literal R/SubUV_frame strings).
    require(isinstance(result, str), 'Material input output-name query failed')
    return result


def world_graph(material):
    nodes = list(unreal.MaterialEditingLibrary.get_material_expressions(material))
    switches = [node for node in nodes if isinstance(node, unreal.MaterialExpressionStaticSwitchParameter) and
                str(node.get_editor_property('parameter_name')) == 'Opa_SubUV_Switch']
    require(len(switches) == 1 and switches[0].get_editor_property('default_value') is False, 'World source switch/default changed')
    switch = switches[0]
    branches = inputs(material, switch)
    require(isinstance(branches.get('True'), unreal.MaterialExpressionCustom) and
            isinstance(branches.get('False'), unreal.MaterialExpressionTextureCoordinate), 'World atlas/plain UV switch routing changed')
    atlas = branches['True']
    age = inputs(material, atlas).get('Age')
    require(isinstance(age, unreal.MaterialExpressionDynamicParameter) and
            str(age.get_editor_property('param_names')[0]) == 'SubUV_frame' and output_name(atlas, age) == 'SubUV_frame',
            'World shared frame must use original DynamicParameter0 SubUV_frame')
    samples = []
    for node in nodes:
        if not isinstance(node, unreal.MaterialExpressionTextureSampleParameter2D):
            continue
        parameter = str(node.get_editor_property('parameter_name'))
        if parameter not in ('Tex_SubUV', 'Tex_Opa'):
            continue
        uv = inputs(material, node).get('UVs')
        require(uv == (atlas if parameter == 'Tex_SubUV' else switch), 'World texture UV/frame routing changed: ' + parameter)
        samples.append(dict(node=node.get_name(), parameter=parameter, uv=uv.get_name()))
    require(len(samples) == 4, 'World exact recovered texture sample count changed')
    return dict(switch=switch.get_name(), atlas=atlas.get_name(), age_channel='SubUV_frame (DynamicParameter0)', samples=samples)


def blood_mask(material):
    lib = unreal.MaterialEditingLibrary
    nodes = {node.get_name(): node for node in lib.get_material_expressions(material)}
    texture = nodes['MaterialExpressionTextureSampleParameter2D_2']
    opacity = nodes['MaterialExpressionMultiply_4']
    pc = nodes['MaterialExpressionParticleColor_0']
    require(material.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_MASKED and
            texture.get_editor_property('texture').get_name() == 'FT_Bsse_Particle', 'Blood mask source material/texture changed')
    require(inputs(material, opacity).get('A') == texture and output_name(opacity, texture) == 'R', 'Blood density must consume grayscale texture R')
    require(lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR) == pc and
            lib.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR) == 'RGB',
            'Blood source ParticleColor RGB emissive changed')
    return dict(density_channel='R', emissive='ParticleColor RGB')


def particle_module(text, name, expected_class):
    marker = re.search(r'Begin Object Class=/Script/Engine\.' + re.escape(expected_class) +
        r' Name="' + re.escape(name) + r'" ExportPath="[^\']*\'([^\']+)\'"', text)
    require(marker is not None, 'Saved native particle subobject missing: ' + name)
    obj = unreal.find_object(None, marker.group(1))
    require(obj and obj.get_class().get_name() == expected_class, 'Particle native subobject reflection mismatch: ' + name)
    return obj


def particle_check(asset, text):
    if asset.rsplit('/', 1)[1] == 'PP_Dmg_Blood_Trail':
        module = particle_module(text, 'ParticleModuleSpawnPerUnit_2', 'ParticleModuleSpawnPerUnit')
        require(module.get_editor_property('UnitScalar') == 40.0, 'Requested denser blood UnitScalar40 not saved')
        return dict(unit_scalar_cm=40.0, origin='User-requested tuning from source80cm; density multiplier2')
    if asset.rsplit('/', 1)[1] == 'PP_Dmg_Blood_Trail_Sub':
        module = particle_module(text, 'ParticleModuleSpawn_0', 'ParticleModuleSpawn')
        bursts = list(module.get_editor_property('BurstList'))
        counts = [burst.get_editor_property('Count') for burst in bursts]
        times = [burst.get_editor_property('Time') for burst in bursts]
        f32 = lambda v: struct.unpack('f', struct.pack('f', v))[0]
        require(counts == [10, 20, 10, 4] and times == list(map(f32, [.1, .1, .2, .3])), 'Blood44 burst counts/original times not saved')
        return dict(burst_counts=counts, total_particles=sum(counts), burst_times_seconds=times,
                    origin='User-requested count2x tuning; original times preserved')
    return dict(additional_frozen_candidate=True)


def material_stats(obj):
    result = unreal.MaterialEditingLibrary.get_statistics(obj)
    values = {key:int(result.get_editor_property(key)) for key in
              ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers')}
    require(values['num_pixel_shader_instructions'] > 0 and values['num_vertex_shader_instructions'] > 0,
            'No valid compiled current-platform material resource: ' + obj.get_path_name() + ' ' + repr(values))
    return values


try:
    require(PROJECT in (MAIN, PRIVATE), 'Wrong actual project')
    require(OUTPUT.is_relative_to((TASK / 'Processes').resolve()) and OUTPUT.is_dir(), 'Only new task process output authorized')
    command = unreal.SystemLibrary.get_command_line().replace('\\', '/').lower()
    require('-run=pythonscript' in command and '-allowcommandletrendering' in command and
            Path(__file__).resolve().as_posix().lower() in command, 'Only own fresh rendering-capable commandlet is authorized')
    launch = read(OUTPUT / 'Launch.json')
    require(launch['pid'] == os.getpid() and str(PROJECT / 'Khazan.uproject') in launch['args'], 'Process ownership/project mismatch')
    require(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'Do not audit during PIE')
    dirty = lambda: [package.get_name() for package in
        list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
    require(not dirty(), 'Fresh audit begins with dirty packages')
    require(not (OUTPUT / 'SavedArtAudit.json').exists(), 'Preserve existing Art audit')
    frozen_hash = sha(FROZEN_PATH)
    frozen = read(FROZEN_PATH)
    require(frozen['status'] == 'FrozenForPolishDelivery' and frozen['producer_role'] == 'root', 'Root-frozen candidates required before audit')
    require(frozen['private_ready_sha256'] == sha(TASK / 'PrivateReady.json'), 'Frozen candidates use stale baseline')
    assets = frozen['art']
    require(len(assets) >= 9 and len({row['asset'] for row in assets}) == len(assets), 'World5+Blood4 exact frozen scope required')
    required = {'FM_World_SubUV_color_A', 'FMI_World_SubUV_color_A_05', 'FMI_World_SubUV_color_A_06',
                'FMI_World_SubUV_color_A_Breath', 'FMI_World_SubUV_color_A_Breath1', 'FM_MeshDecal',
                'PP_Dmg_Blood_Trail', 'PP_Dmg_Blood_Trail_Sub', 'Base_DefaltParticle_Masked'}
    require(required.issubset({row['asset'].rsplit('/', 1)[1] for row in assets}), 'Frozen manifest omitted current World5/Blood4 candidates')
    before = {row['asset']:sha(disk(row['asset'])) for row in assets}
    require(before == {row['asset']:row['expected_private_sha256'] for row in assets}, 'Saved bytes differ from frozen candidates')
    REPORT['actual_loaded_module'] = native_module()
    REPORT['frozen_manifest_sha256'] = frozen_hash
    definition = unreal.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
    require(definition is not None, 'Saved combo definition failed to load')
    REPORT['saved_attack_collision_debug_overlay'] = dict(asset=definition.get_path_name(),
        enabled=definition.get_editor_property('bDrawAttackCollision'),
        boundary='Read only; preserved user debug configuration, not a particle material')
    montage_audit()
    for row in assets:
        asset = row['asset']
        source_path(row)
        obj = unreal.load_asset(asset)
        require(obj is not None, 'Saved Art failed to load: ' + asset)
        KEEP.append(obj)
        item = dict(asset=asset, saved_sha256=before[asset], source_package=row['source_package'],
                    source_sha256=row['source_sha256'], reflected_class=obj.get_class().get_path_name(), compile_errors=[])
        REPORT['rows'].append(item)
        fresh, text = export(obj, str(len(REPORT['rows'])) + '_' + obj.get_name())
        item['fresh_export_sha256'] = sha(fresh)
        if isinstance(obj, unreal.MaterialInterface):
            item['resource_statistics'] = material_stats(obj)
            if isinstance(obj, unreal.Material) and obj.get_name() == 'FM_World_SubUV_color_A':
                item['graph_checks'] = world_graph(obj)
            elif isinstance(obj, unreal.MaterialInstanceConstant) and obj.get_name().startswith('FMI_World_SubUV_color_A'):
                require(unreal.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(obj, 'Opa_SubUV_Switch') is True and
                        unreal.MaterialEditingLibrary.is_material_instance_parameter_overridden(obj, 'Opa_SubUV_Switch'), 'Exact source true child switch override missing')
                item['graph_checks'] = dict(source_opacity_atlas_switch=True, override=True)
            elif isinstance(obj, unreal.Material) and obj.get_name() == 'Base_DefaltParticle_Masked':
                item['graph_checks'] = blood_mask(obj)
            elif isinstance(obj, unreal.Material) and obj.get_name() == 'FM_MeshDecal':
                customs = [node for node in unreal.MaterialEditingLibrary.get_material_expressions(obj) if isinstance(node, unreal.MaterialExpressionCustom)]
                require(len(customs) == 1 and 'min(UnitSize, 5.0 * worldScale)' in customs[0].get_editor_property('code'), 'Bounded projected blood footprint graph missing')
                item['graph_checks'] = dict(custom_code_sha256=hashlib.sha256(customs[0].get_editor_property('code').encode('utf-8')).hexdigest(), source_volume_support_bound=True)
        elif isinstance(obj, unreal.ParticleSystem):
            item['particle_checks'] = particle_check(asset, text)
            references = set(re.findall(r'\bMaterial="[^\']*\'(/Game/[^\']+)\'"', text))
            item['required_material_resources'] = []
            for reference in sorted(references):
                material = unreal.load_asset(reference)
                require(isinstance(material, unreal.MaterialInterface), 'Particle Required.Material failed to load: ' + reference)
                KEEP.append(material)
                item['required_material_resources'].append(dict(path=reference, statistics=material_stats(material)))
        else:
            require(False, 'Unexpected additional candidate reflection type: ' + obj.get_class().get_path_name())
    log = (OUTPUT / 'Editor.log').read_text(encoding='utf-8', errors='replace')
    errors = [line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used in game' in line]
    require(not errors, 'Saved resource compilation errors/default fallback: ' + '\n'.join(errors))
    # Read-only coverage for the unchanged blood-decal chain consumed by
    # actual successful attacks. SM6 compilation is a separate readiness
    # check; it does not claim an observed renderer fallback branch.
    REPORT['unchanged_runtime_decal_resources'] = []
    for asset in (
            '/Game/_Art/Effects/Shared/Materials/BBQ_Material/Base/Base_Blood_Decal',
            '/Game/_Art/Effects/Shared/Materials/BBQ_Material/PhysicsDecal/PD_Blood_Base',
            '/Game/_Art/Effects/Shared/Materials/BBQ_Material/PhysicsDecal/PD_Blood_Curve_Normal'):
        prior = sha(disk(asset))
        material = unreal.load_asset(asset)
        require(isinstance(material, unreal.MaterialInterface), 'Actual blood-decal dependency failed to load: ' + asset)
        KEEP.append(material)
        REPORT['unchanged_runtime_decal_resources'].append(dict(asset=asset,
            saved_sha256=prior, statistics=material_stats(material), asset_saved=False))
        require(sha(disk(asset)) == prior, 'Read-only blood-decal resource check changed bytes')
    require(sha(FROZEN_PATH) == frozen_hash and before == {row['asset']:sha(disk(row['asset'])) for row in assets}, 'Audit or concurrent author changed frozen bytes')
    require(not dirty(), 'Read-only audit dirtied packages')
    REPORT.update(status='passed', checked_asset_count=len(assets), package_bytes_unchanged=True)
except Exception:
    REPORT.update(status='failed', error=traceback.format_exc())
    if REPORT['rows']:
        REPORT['rows'][-1]['compile_errors'].append(REPORT['error'])
    unreal.log_error(REPORT['error'])
finally:
    write_new(OUTPUT / 'SavedArtAudit.json', REPORT)
    print('KZ_PLAYER_ATTACK_VFX_POLISH_SAVED_AUDIT_' + REPORT['status'].upper(), flush=True)
require(REPORT['status'] == 'passed', REPORT.get('error', 'Saved polish audit failed'))
