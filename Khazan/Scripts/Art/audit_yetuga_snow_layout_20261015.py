"""Read the existing Yetuga dust manifest and current all-LOD renderer bindings."""
import hashlib
import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/YetugaSnowLayout_20261015'
OUT.mkdir(parents=True, exist_ok=True)
OLD = ROOT / 'Metadata/GiantVFX_20261013'
mapping = json.loads((OLD / 'AssetAuthor02/Author.json').read_text())['particles']
targets = {source: current for source, current in mapping.items()
           if 'Yetuga' in source and any(term in source.lower() for term in ('dust', 'footstep'))}
FX = u.FXConverterUtilitiesLibrary
LIB = u.MaterialEditingLibrary
report = {'status': 'running', 'project': str(ROOT), 'saved_packages': 0, 'particles': [], 'materials': [], 'textures': [], 'guard_files': {}}


def path(obj):
    return obj.get_path_name() if obj else None


def guard(asset_path):
    file = ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')
    report['guard_files'][str(file.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(file.read_bytes()).hexdigest()


def export(obj, directory, extension='t3d'):
    file = OUT / directory / (obj.get_name() + '.' + extension)
    file.parent.mkdir(parents=True, exist_ok=True)
    task = u.AssetExportTask()
    task.object = obj
    task.filename = str(file)
    task.automated = True
    task.prompt = False
    if extension == 't3d':
        task.exporter = u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(task), path(obj)
    return str(file.relative_to(OUT)).replace('\\', '/')


try:
    materials = {}
    textures = {}
    for original, current in targets.items():
        system = u.load_asset(current)
        assert isinstance(system, u.ParticleSystem)
        guard(current)
        record = {'original': original, 'current': current, 'export': export(system, 'ParticleExports'), 'renderers': []}
        for index, emitter in enumerate(FX.get_cascade_system_emitters(system)):
            for level in range(max(1, len(system.get_editor_property('lod_distances')))):
                lod = FX.get_cascade_emitter_lod_level(emitter, level)
                required = FX.get_lod_level_required_module(lod)
                material = required.get_editor_property('Material')
                if material:
                    materials[path(material)] = material
                record['renderers'].append({'emitter': index, 'lod': level, 'enabled': FX.get_lod_level_is_enabled(lod),
                                             'required': path(required), 'material': path(material),
                                             'subimages_x': required.get_editor_property('SubImages_Horizontal'),
                                             'subimages_y': required.get_editor_property('SubImages_Vertical'),
                                             'local_space': required.get_editor_property('bUseLocalSpace'),
                                             'type_data': path(FX.get_lod_level_type_data_module(lod)),
                                             'modules': [path(module) for module in FX.get_lod_level_modules(lod)]})
        report['particles'].append(record)
    exported = set()
    for reference, instance in sorted(materials.items()):
        guard(reference)
        record = {'reference': reference, 'exports': [], 'parameters': {}, 'texture': None}
        if isinstance(instance, u.MaterialInstanceConstant):
            for parameter in ('AtlasColumns', 'AtlasRows', 'ParticleTintInfluence', 'VolumeDensity'):
                record['parameters'][parameter] = LIB.get_material_instance_scalar_parameter_value(instance, parameter)
            texture = LIB.get_material_instance_texture_parameter_value(instance, 'Tex_Opa')
            record['texture'] = path(texture)
            if texture:
                textures[path(texture)] = texture
        material = instance
        while material:
            if path(material) not in exported:
                guard(path(material))
                record['exports'].append(export(material, 'MaterialExports'))
                exported.add(path(material))
            if isinstance(material, u.MaterialInstanceConstant):
                material = material.get_editor_property('parent')
            else:
                if isinstance(material, u.Material):
                    record['parent'] = path(material)
                    for expression in LIB.get_material_expressions(material):
                        if isinstance(expression, u.MaterialExpressionTextureSampleParameter2D) and str(expression.get_editor_property('parameter_name')) == 'Tex_Opa':
                            texture = expression.get_editor_property('texture')
                            if texture:
                                textures[path(texture)] = texture
                break
        report['materials'].append(record)
    for reference, texture in sorted(textures.items()):
        guard(reference)
        report['textures'].append({'reference': reference, 'png': export(texture, 'Textures', 'png')})
    for relative, expected in report['guard_files'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
(OUT / 'SavedAudit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
print('YETUGA_SNOW_LAYOUT_AUDIT_PASSED', len(report['particles']), len(report['materials']), flush=True)
