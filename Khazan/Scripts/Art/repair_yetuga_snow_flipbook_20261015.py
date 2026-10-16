"""Give the two 9x9 snow atlas instances a scoped, single-frame density sampler."""
import hashlib
import json
import shutil
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/YetugaSnowLayout_20261015'
AUDIT = json.loads((OUT / 'SavedAudit.json').read_text())
assert AUDIT['status'] == 'passed'
assert json.loads((OUT / 'BeforeRHI02/Driver.json').read_text())['status'] == 'passed'
FOLDER = '/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials'
ORIGINAL = FOLDER + '/M_KZGiant_SoftSnowMist'
NAME = 'M_KZGiant_SnowFlipbook9x9'
TARGETS = [item['reference'] for item in AUDIT['materials']
           if 'MI_Atlas_MI_KZGiant_Snow_FMI_World_SubUV_color_A_05_1x1.' in item['reference']
           or 'MI_Atlas_MI_KZGiant_Snow_FMI_World_SubUV_color_A_06_1x1.' in item['reference']]
assert len(TARGETS) == 2
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
report = {'status': 'running', 'project': str(ROOT), 'saved': [], 'new_materials': [], 'reparented': [],
          'source_changes': 0, 'particle_module_changes': 0, 'animation_changes': 0,
          'atlas_grid': {'columns': 9, 'rows': 9, 'frames': 81, 'source_texture': '/Game/_Art/Effects/Shared/Textures/BBQ_Texture/SubUV/T_Smoke03_SubUV_9x9',
                         'basis': 'Existing imported texture and visually verified 9x9 cells; UV layout correction, not gameplay tuning'},
          'frame_clock': {'status': 'TEMP reconstruction', 'mapping': 'normalized particle age * (81 - 1)',
                          'reason': 'Original custom flipbook shader is unavailable; use the existing particle lifetime without changing spawn, velocity or alpha'}}


def file(asset):
    return ROOT / 'Content' / (asset.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(obj):
    target = OUT / 'RepairedExports' / (obj.get_name() + '.t3d')
    target.parent.mkdir(parents=True, exist_ok=True)
    task = u.AssetExportTask()
    task.object = obj
    task.filename = str(target)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task)


def checkpoint():
    (OUT / 'Authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


try:
    for relative, expected in AUDIT['guard_files'].items():
        assert sha(ROOT / relative) == expected, 'Concurrent asset edit: ' + relative
    assert not EAL.does_asset_exist(FOLDER + '/' + NAME), 'Do not repeat a completed or partial authoring batch'
    original = u.load_asset(ORIGINAL)
    instances = []
    for reference in TARGETS:
        instance = u.load_asset(reference)
        assert instance.get_editor_property('parent') == original
        assert LIB.get_material_instance_scalar_parameter_value(instance, 'AtlasColumns') == 1
        assert LIB.get_material_instance_scalar_parameter_value(instance, 'AtlasRows') == 1
        assert LIB.get_material_instance_texture_parameter_value(instance, 'Tex_Opa').get_name() == 'T_Smoke03_SubUV_9x9'
        source = file(reference)
        backup = OUT / 'Backup' / source.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert not backup.exists(), 'Backup already exists; resume from the existing report'
        shutil.copy2(source, backup)
        instances.append((instance,
                          [value.export_text() for value in instance.get_editor_property('scalar_parameter_values')],
                          LIB.get_material_instance_texture_parameter_value(instance, 'Tex_Opa').get_path_name()))
    parent = TOOLS.duplicate_asset(NAME, FOLDER, original)
    assert parent
    nodes = list(LIB.get_material_expressions(parent))
    alpha = next(node for node in nodes if isinstance(node, u.MaterialExpressionCustom))
    alpha_code = alpha.get_editor_property('code')
    old_texture = next(node for node in nodes if isinstance(node, u.MaterialExpressionTextureSampleParameterSubUV))
    uv = next(node for node in nodes if isinstance(node, u.MaterialExpressionTextureCoordinate))
    particle_age = LIB.create_material_expression(parent, u.MaterialExpressionParticleRelativeTime)
    texture = LIB.create_material_expression(parent, u.MaterialExpressionTextureObjectParameter)
    texture.set_editor_property('parameter_name', 'Tex_Opa')
    texture.set_editor_property('texture', u.load_asset(report['atlas_grid']['source_texture']))
    texture.set_editor_property('sampler_type', old_texture.get_editor_property('sampler_type'))
    grid = []
    for name in ('SnowTextureColumns', 'SnowTextureRows'):
        parameter = LIB.create_material_expression(parent, u.MaterialExpressionScalarParameter)
        parameter.set_editor_property('parameter_name', name)
        parameter.set_editor_property('default_value', 9)
        grid.append(parameter)
    density = LIB.create_material_expression(parent, u.MaterialExpressionCustom)
    density.set_editor_property('description', '9x9 source atlas: one blended smoke frame per existing particle; TEMP normalized-age playback')
    density.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs = []
    for name in ('UV', 'Age', 'Columns', 'Rows', 'SmokeTexture'):
        item = u.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    density.set_editor_property('inputs', inputs)
    density.set_editor_property('code', '''
// Columns/Rows are the verified source texture layout. Age is the existing particle lifetime fraction.
float2 grid = max(floor(float2(Columns, Rows)), 1.0);
float last = grid.x * grid.y - 1.0;
float frame = saturate(Age) * last;
float first = floor(frame);
float second = min(first + 1.0, last);
float2 uv = saturate(UV);
float2 cell0 = float2(fmod(first, grid.x), floor(first / grid.x));
float2 cell1 = float2(fmod(second, grid.x), floor(second / grid.x));
float a = Texture2DSample(SmokeTexture, SmokeTextureSampler, (cell0 + uv) / grid).r;
float b = Texture2DSample(SmokeTexture, SmokeTextureSampler, (cell1 + uv) / grid).r;
return lerp(a, b, frac(frame));
''')
    for source, output, name in ((uv, '', 'UV'), (particle_age, '', 'Age'),
                                 (grid[0], '', 'Columns'), (grid[1], '', 'Rows'), (texture, '', 'SmokeTexture')):
        assert LIB.connect_material_expressions(source, output, density, name)
    # The original alpha, spherical volume, depth fade, exposure compensation and tint remain the same.
    assert LIB.connect_material_expressions(density, '', alpha, 'Density')
    assert alpha.get_editor_property('code') == alpha_code
    LIB.delete_material_expression(parent, old_texture)
    EAL.set_metadata_tag(parent, 'KZSnowLayout20261015',
                         '9x9 imported T_Smoke03_SubUV_9x9 layout; one blended R-density frame per particle. TEMP relative-age playback. Original soft alpha/depth/volume/exposure/tint retained; no source shader parity claim.')
    assert not list(LIB.recompile_material(parent))
    assert EAL.save_loaded_asset(parent, only_if_is_dirty=False)
    report['new_materials'].append(parent.get_path_name())
    report['saved'].append(parent.get_path_name())
    export(parent)
    checkpoint()
    for instance, scalars, texture_path in instances:
        LIB.set_material_instance_parent(instance, parent)
        LIB.update_material_instance(instance)
        assert [value.export_text() for value in instance.get_editor_property('scalar_parameter_values')] == scalars
        assert LIB.get_material_instance_texture_parameter_value(instance, 'Tex_Opa').get_path_name() == texture_path
        assert LIB.get_material_instance_scalar_parameter_value(instance, 'ParticleTintInfluence') == 0
        assert EAL.save_loaded_asset(instance, only_if_is_dirty=False)
        report['saved'].append(instance.get_path_name())
        report['reparented'].append({'instance': instance.get_path_name(), 'before': original.get_path_name(),
                                     'after': parent.get_path_name(), 'sha256_after': sha(file(instance.get_path_name())),
                                     'scalar_overrides_unchanged': True, 'texture_override_unchanged': True})
        export(instance)
        checkpoint()
    allowed = {str(file(reference).relative_to(ROOT)).replace('\\', '/') for reference in TARGETS}
    for relative, expected in AUDIT['guard_files'].items():
        if relative not in allowed:
            assert sha(ROOT / relative) == expected, 'Protected asset changed: ' + relative
    report['protected_files_unchanged'] = len(AUDIT['guard_files']) - len(allowed)
    report['new_parent_sha256'] = sha(file(parent.get_path_name()))
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
checkpoint()
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
print('YETUGA_SNOW_FLIPBOOK_REPAIRED', len(report['saved']), flush=True)
