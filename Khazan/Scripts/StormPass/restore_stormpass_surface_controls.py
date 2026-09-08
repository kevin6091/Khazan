"""Restore cooked WorldProp surface controls using a StormPass-only native graph.

The cooked BBQ shading implementation is not a stock engine feature. This
adapter retains USD UV/texture/alpha inputs, but restores inherited numeric
surface controls rather than treating every packed mask as unscaled metal.
It does not invent emissive lighting or overwrite the engine USD material.
"""
import hashlib
import json
import os
import runpy

try:
    import unreal
except ImportError:
    unreal = None  # Source metadata preparation can run without an editor.

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
META = os.path.join(ROOT, 'Content/_Art/Kazan/Environment/StormPass/Metadata')
RAW = os.path.join(ROOT, 'Saved/Extracted/StormPass/AdditionalMetadata_20260907')
PARENT = '/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Surfaces/M_SP_WorldSurface_Native'
PLAN = os.path.join(META, 'StormPass_InheritedSurfaceControls_20260907.json')
MASTER = 'BBQ/Content/BaseMaterials/WorldProp/WorldPropMaster/M_WorldProp'
CONTROL_NAMES = ('MetallicAdjust', 'Metallic_Min', 'Metallic_Max', 'RoughnessAdjust', 'Diffuse_Intensity')


def read(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def source_package(info):
    if info.get('package'):
        return info['package']
    path = (info.get('json_path') or '').replace('\\', '/')
    offset = path.lower().find('/bbq/content/')
    return 'BBQ/Content/' + path[offset + 13:-5] if offset >= 0 else None


def resolve(package, seen=()):
    if package in seen:
        raise RuntimeError('Source inheritance cycle: ' + package)
    path = os.path.join(RAW, package + '.json')
    rows = read(path)
    row = next(r for r in rows if r.get('Type') in ('Material', 'MaterialInstanceConstant'))
    props = row.get('Properties') or {}
    parent = (props.get('Parent') or {}).get('ObjectPath', '').split('.')[0]
    result = resolve(parent, seen + (package,)) if parent else {'chain': [], 'scalars': {}, 'vectors': {}, 'textures': {}, 'switches': {}, 'shading': None}
    result['chain'].append({'package': package, 'sha256': hashlib.sha256(open(path, 'rb').read()).hexdigest()})
    cached = (props.get('CachedExpressionData') or {}).get('Parameters') or {}
    infos = (cached.get('RuntimeEntries') or {}).get('ParameterInfos') or []
    result['scalars'].update({v['Name']: cached['ScalarValues'][i] for i, v in enumerate(infos)})
    vector_infos = (cached.get('RuntimeEntries[1]') or {}).get('ParameterInfos') or []
    result['vectors'].update({v['Name']: cached['VectorValues'][i] for i, v in enumerate(vector_infos)})
    texture_infos = (cached.get('RuntimeEntries[2]') or {}).get('ParameterInfos') or []
    result['textures'].update({v['Name']: cached['TextureValues'][i] for i, v in enumerate(texture_infos)})
    for kind, destination in (('ScalarParameterValues', 'scalars'), ('VectorParameterValues', 'vectors'), ('TextureParameterValues', 'textures')):
        result[destination].update({v['ParameterInfo']['Name']: v.get('ParameterValue', 0) for v in props.get(kind, [])})
    result['switches'].update({v['ParameterInfo']['Name']: v.get('Value', False) for v in (props.get('StaticParameters') or {}).get('StaticSwitchParameters', []) if v.get('bOverride')})
    overrides = props.get('BasePropertyOverrides') or {}
    if row['Type'] == 'Material':
        result['shading'] = props.get('ShadingModel')
    if overrides.get('bOverride_ShadingModel'):
        result['shading'] = overrides.get('ShadingModel', 'MSM_Unlit')
    return result


def prepare_plan():
    source_audit = read(os.path.join(ROOT, 'Saved/ImportReports/StormPass_SurfaceRendering_Audit_20260907.json'))
    profile = read(os.path.join(META, 'StormPass_EnvironmentProfile.json'))
    globals_ = {v['ParameterName']: v['ScalarValue'] for v in profile['profiles']['outside']['components']['environment_material']['properties']['ScalarValues']}
    rows, unresolved = [], []
    for material in source_audit['materials']:
        package = source_package(material.get('source_policy') or {})
        if not package:
            unresolved.append(material['path'])
            continue
        resolved = resolve(package)
        if MASTER.lower() not in {v['package'].lower() for v in resolved['chain']}:
            continue
        controls = {n: float(resolved['scalars'][n]) for n in CONTROL_NAMES}
        rows.append({'asset': material['path'], 'source_package': package, 'source_chain': resolved['chain'],
                     'controls': controls, 'source_shading': resolved['shading'],
                     'source_camera_light': resolved['scalars'].get('CameraLightIntensity'),
                     'source_emissive_on': resolved['scalars'].get('EmissiveOn', 0),
                     'source_use_sss': resolved['switches'].get('UseSSS', False),
                     'sss_mask': resolved['textures'].get('Tex_E'),
                     'sss_color': resolved['vectors'].get('SSS_DiffuseColor'),
                     'sss_opacity': resolved['scalars'].get('SSS_Opacity', 1),
                     'sss_intensity': resolved['scalars'].get('SSS_Mask_Intensity', 0)})
    payload = {'adapter_boundary': 'Native surface response; BBQHalfCartoon/covering/wind shader bytecode not recreated.',
               'global_controls': {n: globals_[n] for n in ('GlobalMetallic', 'GlobalRoughness', 'GlobalSpecular')},
               'materials': rows, 'unresolved': unresolved}
    write(PLAN, payload)
    print(json.dumps({'worldprop_materials': len(rows), 'unresolved': unresolved}))
    return payload


def expression(material, cls):
    node = unreal.MaterialEditingLibrary.create_material_expression(material, cls)
    if not node:
        raise RuntimeError('Cannot create ' + cls.__name__)
    return node


def connect(source, output, target, input_name):
    if not unreal.MaterialEditingLibrary.connect_material_expressions(source, output, target, input_name):
        raise RuntimeError('Failed graph connection: ' + input_name)


def scalar(material, name, value):
    node = expression(material, unreal.MaterialExpressionScalarParameter)
    node.set_editor_property('parameter_name', 'SP_' + name)
    node.set_editor_property('default_value', float(value))
    return node


def binary(material, cls, left, right, left_output=''):
    node = expression(material, cls)
    connect(left, left_output, node, 'A')
    connect(right, '', node, 'B')
    return node


def output(material, node, prop):
    if not unreal.MaterialEditingLibrary.connect_material_property(node, '', prop):
        raise RuntimeError('Failed property connection: ' + str(prop))


def build_parent():
    material = unreal.load_asset(PARENT)
    if material:
        tag = unreal.EditorAssetLibrary.get_metadata_tag(material, 'StormPassSurfaceAdapter')
        if tag == 'v1':
            return material
        if tag != 'v1_building':
            raise RuntimeError('Refusing to overwrite unrecognized native parent')
        unreal.MaterialEditingLibrary.delete_unused_expressions(material)
    else:
        unreal.EditorAssetLibrary.make_directory(PARENT.rsplit('/', 1)[0])
        material = unreal.EditorAssetLibrary.duplicate_asset('/USDCore/Materials/UsdPreviewSurface', PARENT)
    if not material:
        raise RuntimeError('USD parent duplication failed')
    mel = unreal.MaterialEditingLibrary
    mul, add = unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd
    for prop, adjust, global_name in ((unreal.MaterialProperty.MP_METALLIC, 'MetallicAdjust', 'GlobalMetallic'),
                                      (unreal.MaterialProperty.MP_ROUGHNESS, 'RoughnessAdjust', 'GlobalRoughness')):
        original = mel.get_material_property_input_node(material, prop)
        pin = mel.get_material_property_input_node_output_name(material, prop)
        first = binary(material, add if adjust == 'MetallicAdjust' else mul, original,
                       scalar(material, adjust, 0 if adjust == 'MetallicAdjust' else 1), pin)
        value = binary(material, mul, first, scalar(material, global_name, .4 if adjust == 'MetallicAdjust' else .6))
        clamp = expression(material, unreal.MaterialExpressionClamp)
        connect(value, '', clamp, '')
        if adjust == 'MetallicAdjust':
            connect(scalar(material, 'Metallic_Min', 0), '', clamp, 'Min')
            connect(scalar(material, 'Metallic_Max', 1), '', clamp, 'Max')
        output(material, clamp, prop)
    base = mel.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    pin = mel.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, binary(material, mul, base, scalar(material, 'Diffuse_Intensity', 1), pin), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, scalar(material, 'GlobalSpecular', .2), unreal.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(material)
    mel.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'StormPassSurfaceAdapter', 'v1')
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Native parent save failed')
    return material


def apply_batch(offset=0, limit=50, only_paths=None):
    helper = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/repair_stormpass_surface_rendering.py'))
    helper['actors']()
    plan = read(PLAN)
    parent = build_parent()
    rows = plan['materials'][offset:offset + limit] if only_paths is None else [r for r in plan['materials'] if r['asset'] in only_paths]
    repaired = []
    for row in rows:
        material = unreal.load_asset(row['asset'])
        values = dict(plan['global_controls'], **row['controls'])
        if material.get_editor_property('parent') == parent and all(
            abs(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, 'SP_' + n) - v) <= .00001
            for n, v in values.items()
        ):
            continue
        helper['fixer'].backup_asset(row['asset'])
        unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
        unreal.MaterialEditingLibrary.update_material_instance(material)
        for name, value in values.items():
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material, 'SP_' + name, value)
            actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, 'SP_' + name)
            if abs(actual - value) > .00001:
                raise RuntimeError('Native control readback failed: ' + name)
        # ChannelSelector normalizes its vector: a non-unit vector cannot scale
        # intensity. Surface scaling belongs after the channel sample.
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(material, 'MetallicTextureComponent', unreal.LinearColor(0, 0, 1, 0))
        unreal.MaterialEditingLibrary.update_material_instance(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('MI save failed: ' + row['asset'])
        repaired.append(row['asset'])
    write(os.path.join(ROOT, 'Saved/ImportReports/StormPass_NativeSurfaceBatch_%04d.json' % offset), {'assets': repaired})
    print(json.dumps({'offset': offset, 'repaired': len(repaired)}))


def audit():
    plan = read(PLAN)
    failures = []
    for row in plan['materials']:
        material = unreal.load_asset(row['asset'])
        parent_path = material.get_editor_property('parent').get_path_name().split('.')[0]
        allowed = {PARENT}
        if row['source_use_sss']:
            allowed.update(PARENT.rsplit('/', 1)[0] + '/M_SP_WorldSurface_Subsurface_' + s for s in ('Color', 'Linear'))
        if parent_path not in allowed:
            failures.append(row['asset'] + ': parent')
            continue
        for name, value in dict(plan['global_controls'], **row['controls']).items():
            actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, 'SP_' + name)
            if abs(actual - value) > .00001:
                failures.append(row['asset'] + ': ' + name)
    result = {'material_count': len(plan['materials']), 'failures': failures}
    write(os.path.join(ROOT, 'Saved/ImportReports/StormPass_NativeSurfaceControls_Audit.json'), result)
    print(json.dumps({'material_count': len(plan['materials']), 'failure_count': len(failures)}))
    return result
