"""Root-launched private NullRHI commandlet: exact two PSC saved materials.

Read/export only. No package save, compilation/statistics, warmup, editing or PIE.
Template selection is not live component material-override/pixel attribution proof.
Original C++ property names are intentional: PyWrapperObject.cpp resolves unknown
Python aliases back to the reflected FName; protection still applies. Protected
Cascade arrays use existing native FX getters. Actual QA10 PSC slot graphs run first.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
PROJECT = Path(unreal.Paths.project_dir()).resolve()
assert PROJECT == WORK.resolve(), 'Only the MonsterVFX private project is authorized'
COMMAND = unreal.SystemLibrary.get_command_line()
assert '-nullrhi' in COMMAND.lower() and '-run=pythonscript' in COMMAND.lower(), 'Root must launch a NullRHI Python commandlet'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
BASE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/BlackCardMaterialReadback'
OUT = Path(os.environ.get('KZ_MONSTER_VFX_APESCARDS_READBACK_OUTPUT', str(BASE / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))).resolve()
assert OUT.is_relative_to(BASE.resolve()) and OUT != BASE.resolve()
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT / 'Readback.json').exists(), 'Preserve existing readback evidence'
RES = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
LIB = unreal.MaterialEditingLibrary
WORLD_FALL = '/Game/_Art/Effects/Movement/Dust/Monsters/FP_P_World_Mon_L_Default_falldown_normal'
REPORT = {'schema': 'Khazan.MonsterVFX.ApesCardsMaterialReadback.v1', 'status': 'running',
    'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'pid': os.getpid(),
    'project': str(PROJECT), 'command_line': COMMAND, 'null_rhi': True,
    'package_saves': 0, 'asset_mutations': 0, 'compile_api_calls': 0,
    'statistics_api_calls': 0, 'warmup_api_calls': 0, 'source_writes': 0,
    'targets': [], 'material_instances': [], 'material_graphs': [],
    'sha256_before': {}, 'sha256_after': {}, 'source_identity': {},
    'api_evidence': ['Engine/Classes/Particles/{ParticleSystem,ParticleEmitter,ParticleLODLevel,ParticleModuleRequired}.h',
        'Engine/Classes/Particles/TypeData/ParticleModuleTypeDataMesh.h',
        'Engine/Classes/Particles/Material/ParticleModuleMeshMaterial.h',
        'Engine/Private/Particles/ParticleLODLevel.cpp:GetUsedMaterials',
        'Engine/Classes/Engine/StaticMesh.h:GetNumSections/GetMaterial',
        'StaticMeshEditor/Public/StaticMeshEditorSubsystem.h:GetLODMaterialSlot',
        'PythonScriptPlugin/Private/PyWrapperObject.cpp:748-799,1223-1240',
        'Scripts/Art/monster_vfx_decal_white_readback_20261010.py',
        'Scripts/Art/monster_vfx_decal_visual_repair_20261010.py'],
    'boundary': 'Actual QA10 slots bind current saved graphs; FX LOD0 inventory may be partial and is explicitly reported. No shader readiness, pixel ownership or visual pass inferred.'}
KEEP = []
MATERIALS = {}
UNION = []


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def nullable_sha(file):
    return sha(file) if Path(file).is_file() else None


def read(file):
    return json.loads(Path(file).read_text(encoding='utf-8-sig'))


def path(obj):
    return obj.get_path_name() if obj else None


def remember(obj):
    if not obj:
        return
    package = path(obj).split('.')[0]
    if package in REPORT['sha256_before']:
        return
    if package.startswith('/Game/'):
        relative = 'Content/' + package.removeprefix('/Game/') + '.uasset'
        files = {'main': MAIN / relative, 'private': WORK / relative}
        assert files['private'].is_file(), ('Missing private saved package', package)
    elif package.startswith('/Engine/'):
        relative = 'Content/' + package.removeprefix('/Engine/') + '.uasset'
        files = {'engine': Path('C:/Program Files/Epic Games/UE_5.8/Engine') / relative}
    else:
        raise AssertionError(('Unexpected transient/plugin dependency', package))
    REPORT['sha256_before'][package] = {role: {'file': str(file), 'sha256': nullable_sha(file)} for role, file in files.items()}
    source_rows = [r for r in UNION if r.get('destination') == package]
    assert len(source_rows) <= 1, ('Ambiguous Union source', package)
    if source_rows:
        row = source_rows[0]
        source = MAIN / row['source_json']
        assert sha(source) == row['source_sha256']
        REPORT['source_identity'][package] = {key: row[key] for key in ('source_package', 'source_json', 'source_sha256', 'source_type') if key in row}
    KEEP.append(obj)


def export(obj, label):
    file = OUT / 'Exports' / (label + '.t3d')
    file.parent.mkdir(parents=True, exist_ok=True)
    assert not file.exists()
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(file)
    task.exporter = unreal.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    assert unreal.Exporter.run_asset_export_task(task), path(obj)
    return {'path': str(file), 'sha256': sha(file)}


def graph(master):
    remember(master)
    key = hashlib.sha256(path(master).encode()).hexdigest()[:12] + '_' + master.get_name()
    result = {'material': path(master), 'export': export(master, key + '/Material'),
        'settings': {field: str(master.get_editor_property(field)) for field in
            ('material_domain', 'blend_mode', 'shading_model', 'two_sided', 'use_material_attributes',
             'used_with_particle_sprites', 'used_with_mesh_particles')},
        'property_roots': {}, 'nodes': []}
    result['settings']['automatically_set_usage_in_editor'] = bool(master.get_editor_property('bAutomaticallySetUsageInEditor'))
    roots = {}
    for name, prop in [('BaseColor', unreal.MaterialProperty.MP_BASE_COLOR),
                       ('EmissiveColor', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                       ('Opacity', unreal.MaterialProperty.MP_OPACITY),
                       ('OpacityMask', unreal.MaterialProperty.MP_OPACITY_MASK)]:
        node = LIB.get_material_property_input_node(master, prop)
        roots[name] = node
        result['property_roots'][name] = {'node': path(node), 'output': LIB.get_material_property_input_node_output_name(master, prop)}
    for node in LIB.get_material_expressions(master):
        names = list(LIB.get_material_expression_input_names(node))
        inputs = list(LIB.get_inputs_for_material_expression(master, node))
        assert len(names) == len(inputs)
        row = {'node': path(node), 'class': node.get_class().get_name(),
            'export': export(node, key + '/Nodes/' + node.get_name()),
            'inputs': [{'pin': str(name), 'node': path(child),
                'output': str(LIB.get_input_node_output_name_for_material_expression(node, child)) if child else None}
                for name, child in zip(names, inputs)]}
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter,
                             unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionTextureObjectParameter)):
            row['parameter_name'] = str(node.get_editor_property('parameter_name'))
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter)):
            value = node.get_editor_property('default_value')
            row['default_value'] = [value.r, value.g, value.b, value.a] if isinstance(value, unreal.LinearColor) else value
        if isinstance(node, (unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionTextureObjectParameter)):
            texture = node.get_editor_property('texture')
            row['texture'] = path(texture)
            remember(texture)
        if isinstance(node, unreal.MaterialExpressionCustom):
            row['code'] = node.get_editor_property('code')
            row['code_sha256'] = hashlib.sha256(row['code'].encode()).hexdigest()
        result['nodes'].append(row)
    adjacency = {row['node']: [r['node'] for r in row['inputs'] if r['node']] for row in result['nodes']}
    for name, root in roots.items():
        reached, pending = set(), [path(root)] if root else []
        while pending:
            current = pending.pop()
            if current in reached:
                continue
            reached.add(current)
            pending.extend(adjacency.get(current, []))
        result[name.lower() + '_reachable_nodes'] = sorted(reached)
    return result


def material(obj):
    if obj is None or path(obj) in MATERIALS:
        return
    remember(obj)
    MATERIALS[path(obj)] = obj
    if isinstance(obj, unreal.MaterialInstanceConstant):
        parent = obj.get_editor_property('parent')
        assert parent and path(parent) != path(obj)
        material(parent)
        master = parent
        seen = {path(obj)}
        chain = [path(obj)]
        while isinstance(master, unreal.MaterialInstanceConstant):
            assert path(master) not in seen, 'Cyclic material parents'
            seen.add(path(master)); chain.append(path(master))
            master = master.get_editor_property('parent')
        assert isinstance(master, unreal.Material), path(master)
        chain.append(path(master))
        row = {'material': path(obj), 'parent': path(parent), 'parent_chain': chain,
            'export': export(obj, hashlib.sha256(path(obj).encode()).hexdigest()[:12] + '_' + obj.get_name() + '/Instance'),
            'base_property_overrides': obj.get_editor_property('base_property_overrides').export_text(),
            'parameter_arrays': {field: [item.export_text() for item in obj.get_editor_property(field)]
                for field in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')},
            'effective_scalars': {}, 'effective_vectors': {}, 'effective_textures': {}}
        for node in LIB.get_material_expressions(master):
            if isinstance(node, unreal.MaterialExpressionScalarParameter):
                name = str(node.get_editor_property('parameter_name'))
                row['effective_scalars'][name] = LIB.get_material_instance_scalar_parameter_value(obj, name)
            elif isinstance(node, unreal.MaterialExpressionVectorParameter):
                name = str(node.get_editor_property('parameter_name'))
                v = LIB.get_material_instance_vector_parameter_value(obj, name)
                row['effective_vectors'][name] = [v.r, v.g, v.b, v.a]
            elif isinstance(node, (unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionTextureObjectParameter)):
                name = str(node.get_editor_property('parameter_name'))
                texture = LIB.get_material_instance_texture_parameter_value(obj, name)
                row['effective_textures'][name] = path(texture)
                remember(texture)
        REPORT['material_instances'].append(row)
    else:
        assert isinstance(obj, unreal.Material), ('Unexpected saved material class', obj.get_class().get_name())
        REPORT['material_graphs'].append(graph(obj))


def live_material_binding():
    proof = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt10/Driver.json'
    expected = 'd252d3ef8e0a1fa6ea28087876724b5824ddca0743f89d3281f4e785e1baacc1'
    assert sha(proof) == expected
    data = read(proof)
    assert data['status'] == 'passed' and data['saved_bytes_unchanged'] is True
    rows = {}
    def visit(value):
        if isinstance(value, dict):
            template = value.get('template', '').split('.')[0]
            if template in (WORLD_FALL, '/Game/_Art/Effects/Monsters/Human/FP_DeathEffect') and 'materials' in value:
                assert value['material_api_available'] and value['material_count'] == len(value['materials'])
                key = value['component']
                row = {k: value[k] for k in ('component', 'owner', 'template', 'tags', 'material_count', 'materials')}
                if key in rows:
                    assert rows[key] == row
                rows[key] = row
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(data)
    assert len(rows) == 3 and sorted(r['material_count'] for r in rows.values()) == [3, 6, 6]
    names = sorted({name.split('.')[0] for r in rows.values() for name in r['materials']})
    assert len(names) == 8, 'Actual QA10 slots contain 8 unique native materials (15 slots)'
    REPORT['live_psc_slot_binding'] = {'path': str(proof), 'sha256': expected, 'components': list(rows.values()),
        'distinct_material_count': len(names), 'boundary': 'Historical QA10 actual PSC getter readback; current saved graphs queried independently below.'}
    return names


def particle(asset):
    # These FX getters are reflected UFUNCTIONs in the installed
    # NiagaraStackGraphUtilitiesAdapterLibrary.h:957-984, and existing importer/audit.
    fx = unreal.FXConverterUtilitiesLibrary
    obj = unreal.load_asset(asset)
    assert isinstance(obj, unreal.ParticleSystem), asset
    remember(obj)
    row = {'asset': path(obj), 'export': export(obj, obj.get_name() + '/ParticleSystem'),
        'scope': 'LOD0 native getter readback; full raw saved PS export retained', 'emitters': []}
    REPORT['targets'].append(row)
    for ei, emitter in enumerate(fx.get_cascade_system_emitters(obj)):
        lod = fx.get_cascade_emitter_lod_level(emitter, 0)
        required = fx.get_lod_level_required_module(lod)
        assert lod and required
        typed = fx.get_lod_level_type_data_module(lod)
        reqmat = required.get_editor_property('material')
        label = obj.get_name() + '/Emitter' + str(ei) + '/LOD0'
        erow = {'index': ei, 'object': path(emitter), 'name': str(fx.get_cascade_emitter_name(emitter)),
            'lod': 0, 'lod_enabled': fx.get_lod_level_is_enabled(lod), 'required_module': path(required),
            'required_material': path(reqmat), 'required_export': export(required, label + '/Required'),
            'type_data_module': path(typed), 'modules': []}
        row['emitters'].append(erow)
        material(reqmat)
        if typed:
            erow['type_data_class'] = typed.get_class().get_name()
            erow['type_data_export'] = export(typed, label + '/TypeData')
        for index, module in enumerate(fx.get_lod_level_modules(lod)):
            erow['modules'].append({'index': index, 'object': path(module), 'class': module.get_class().get_name(),
                'enabled': fx.get_particle_module_is_enabled(module)})


try:
    UNION = read(RES / 'UnionAssetManifest.json')
    adapter_file = RES / 'NativeAdapterMap.json'
    adapter = read(adapter_file)
    matches = [r for r in adapter['adapters'] if r.get('source_package', '').endswith('/Physics/DeathEffect/FP_DeathEffect')]
    assert len(matches) == 1
    death = matches[0]
    assert death['native_destination'] == '/Game/_Art/Effects/Monsters/Human/FP_DeathEffect'
    assert sha(MAIN / death['source_json']) == death['source_sha256']
    REPORT['native_adapter_binding'] = {'path': str(adapter_file), 'sha256': sha(adapter_file),
        'selected_row': {k: death[k] for k in ('source_package', 'source_json', 'source_sha256', 'native_destination', 'native_type', 'adapter_kind') if k in death}}
    REPORT['union_binding'] = {'path': str(RES / 'UnionAssetManifest.json'), 'sha256': sha(RES / 'UnionAssetManifest.json')}
    # Material graphs come first. Protected particle declarations cannot suppress
    # the exact actual PSC material graph evidence again.
    for name in live_material_binding():
        obj = unreal.load_asset(name)
        assert isinstance(obj, (unreal.Material, unreal.MaterialInstanceConstant)), name
        material(obj)
    REPORT['actual_psc_material_graphs_complete'] = True
    REPORT['particle_inventory_failures'] = []
    for target in (WORLD_FALL, death['native_destination']):
        try:
            particle(target)
        except Exception:
            REPORT['particle_inventory_failures'].append({'target': target, 'error': traceback.format_exc()})
    REPORT['particle_inventory_complete'] = not REPORT['particle_inventory_failures']
    REPORT['status'] = 'passed'
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
finally:
    REPORT['sha256_after'] = {package: {role: {'file': entry['file'], 'sha256': nullable_sha(entry['file'])}
        for role, entry in files.items()} for package, files in REPORT['sha256_before'].items()}
    REPORT['package_bytes_unchanged'] = REPORT['sha256_before'] == REPORT['sha256_after']
    if not REPORT['package_bytes_unchanged']:
        REPORT['status'] = 'failed'
        REPORT['error'] = REPORT.get('error', '') + '\nSaved package SHA drift during read-only query'
    with (OUT / 'Readback.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(REPORT, ensure_ascii=False, indent=2) + '\n')
    unreal.log('MonsterVFX Apes cards material readback: ' + str(OUT / 'Readback.json') + ' status=' + REPORT['status'])
if REPORT['status'] != 'passed':
    raise RuntimeError(REPORT.get('error', 'Readback failed'))
