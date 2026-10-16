"""Owned fresh-process, read-only saved graph query for Native8 white decals.

No PIE, material compilation, node edits, or package save. Root owns launch.
Output is a new Saved report; this is graph evidence, not pixel attribution.
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
assert Path(unreal.Paths.project_dir()).resolve() == WORK
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
ROOT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/DecalWhiteRectangleReadback'
OUT = Path(os.environ.get('KZ_MONSTER_VFX_DECAL_QUERY_OUT', str(ROOT / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))).resolve()
assert OUT.is_relative_to(ROOT.resolve()) and OUT != ROOT.resolve()
OUT.mkdir(parents=True, exist_ok=False)
TARGETS = [
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/MI_Decal_Deferred_D_00',
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/FMI_Decal_Deferred_D_02',
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/Mi_PD_Blood_SuperRound',
    '/Game/_Art/Effects/Monsters/Materials/PD_Blood_SuperRound_MonsterCurve_cadb0406',
]
REPORT = {'schema': 'Khazan.MonsterVFX.DecalWhiteRectangleReadback.v1',
    'status': 'running', 'project': str(WORK), 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'pid': os.getpid(), 'asset_mutations': 0, 'package_saves': 0, 'compile_api_calls': 0,
    'targets': [], 'graphs': [], 'sha256_before': {}, 'sha256_after': {},
    'boundary': 'Saved exact graph readback only. Native8 did not inventory live decals; no pixel ownership or visual pass asserted.'}
LIB = unreal.MaterialEditingLibrary


def path(obj):
    return obj.get_path_name() if obj else None


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def remember(obj):
    package = obj.get_path_name().split('.')[0]
    assert package.startswith('/Game/')
    file = WORK / ('Content/' + package.removeprefix('/Game/') + '.uasset')
    assert file.is_file()
    REPORT['sha256_before'].setdefault(str(file), sha(file))


def graph(master):
    remember(master)
    result = {'material': path(master), 'material_domain': str(master.get_editor_property('material_domain')),
        'blend_mode': str(master.get_editor_property('blend_mode')),
        'shading_model': str(master.get_editor_property('shading_model')),
        'use_material_attributes': master.get_editor_property('use_material_attributes'),
        'property_roots': {}, 'nodes': []}
    roots = {}
    for name, prop in [('BaseColor', unreal.MaterialProperty.MP_BASE_COLOR),
                       ('EmissiveColor', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                       ('Opacity', unreal.MaterialProperty.MP_OPACITY),
                       ('OpacityMask', unreal.MaterialProperty.MP_OPACITY_MASK),
                       ('Normal', unreal.MaterialProperty.MP_NORMAL)]:
        node = LIB.get_material_property_input_node(master, prop)
        roots[name] = node
        result['property_roots'][name] = {'node': path(node), 'output': LIB.get_material_property_input_node_output_name(master, prop)}
    for node in LIB.get_material_expressions(master):
        names = list(LIB.get_material_expression_input_names(node))
        inputs = list(LIB.get_inputs_for_material_expression(master, node))
        assert len(names) == len(inputs)
        row = {'node': path(node), 'class': node.get_class().get_name(), 'inputs': []}
        for name, child in zip(names, inputs):
            row['inputs'].append({'pin': name, 'node': path(child),
                'output': str(LIB.get_input_node_output_name_for_material_expression(node, child)) if child else None})
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter,
                             unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionTextureObjectParameter)):
            row['parameter_name'] = str(node.get_editor_property('parameter_name'))
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter)):
            value = node.get_editor_property('default_value')
            row['default_value'] = [value.r, value.g, value.b, value.a] if isinstance(value, unreal.LinearColor) else value
        if isinstance(node, (unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionTextureObjectParameter)):
            row['texture'] = path(node.get_editor_property('texture'))
        if isinstance(node, unreal.MaterialExpressionCustom):
            row['code'] = node.get_editor_property('code')
        result['nodes'].append(row)
    for name, node in roots.items():
        reached = set()
        def visit(current):
            if current is None or path(current) in reached:
                return
            reached.add(path(current))
            for child in LIB.get_inputs_for_material_expression(master, current):
                visit(child)
        visit(node)
        result[name.lower() + '_reachable_nodes'] = sorted(reached)
    return result


try:
    masters = {}
    instances = []
    for name in TARGETS:
        obj = unreal.load_asset(name)
        assert isinstance(obj, unreal.MaterialInstanceConstant), name
        chain = []
        current = obj
        while isinstance(current, unreal.MaterialInstanceConstant):
            remember(current)
            assert path(current) not in chain
            chain.append(path(current))
            current = current.get_editor_property('parent')
        assert isinstance(current, unreal.Material)
        masters.setdefault(path(current), current)
        row = {'material': path(obj), 'parent_chain': chain + [path(current)],
            'base_property_overrides_export_text': obj.get_editor_property('base_property_overrides').export_text(),
            'parameter_arrays_export_text': {field: [item.export_text() for item in obj.get_editor_property(field)]
                for field in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')},
            'effective_textures': {}, 'effective_scalars': {}, 'effective_vectors': {}}
        instances.append((obj, current, row))
    for obj in masters.values():
        REPORT['graphs'].append(graph(obj))
    graphs = {row['material']: row for row in REPORT['graphs']}
    for obj, master, row in instances:
        for node in graphs[path(master)]['nodes']:
            name = node.get('parameter_name')
            if not name:
                continue
            if node['class'] in ('MaterialExpressionTextureSampleParameter2D', 'MaterialExpressionTextureObjectParameter'):
                row['effective_textures'][name] = path(LIB.get_material_instance_texture_parameter_value(obj, name))
            elif node['class'] == 'MaterialExpressionScalarParameter':
                row['effective_scalars'][name] = LIB.get_material_instance_scalar_parameter_value(obj, name)
            elif node['class'] == 'MaterialExpressionVectorParameter':
                value = LIB.get_material_instance_vector_parameter_value(obj, name)
                row['effective_vectors'][name] = [value.r, value.g, value.b, value.a]
        REPORT['targets'].append(row)
    REPORT['sha256_after'] = {file: sha(Path(file)) for file in REPORT['sha256_before']}
    assert REPORT['sha256_after'] == REPORT['sha256_before'], 'Package bytes changed during read-only query'
    REPORT['status'] = 'passed'
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
finally:
    (OUT / 'Readback.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('Monster VFX white-decal readback: ' + str(OUT / 'Readback.json') + ' status=' + REPORT['status'])
    if os.environ.get('KZ_MONSTER_VFX_DECAL_QUERY_QUIT_OWN_PROCESS') == '1':
        unreal.SystemLibrary.quit_editor()
