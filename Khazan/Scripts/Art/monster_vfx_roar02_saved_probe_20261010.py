"""Read-only Roar02 particle/material identity and graph export; root launches it.

No asset save, editing, shader rebuild, Source write, or editor control API.
Only the three exact Roar02 helix producer dependency assets are loaded and exported.
"""
from pathlib import Path
import hashlib
import json
import os
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUTPUT = Path(os.environ['KZ_MONSTER_VFX_ROAR02_PROBE_OUTPUT']).resolve()
BASE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/Roar02SavedProbe'
ASSETS = [
    '/Game/_Art/Effects/Monsters/ApesYetuga/FP_Boss_Yetuga_Roar_02',
    '/Game/_Art/Effects/Shared/Materials/Trail/FM_WPO_Trail_A',
    '/Game/_Art/Effects/Shared/Materials/MonsterApesYetuga/FMI_WPO_Trail_A_18',
]
SOURCE_BASE = MAIN / 'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material'
MI_SOURCES = {ASSETS[2]: SOURCE_BASE / 'Trail/MI/FMI_WPO_Trail_A_18.json'}
REPORT = dict(schema='Khazan.MonsterVFX.Roar02SavedProbe.v1', status='running',
              project=str(PROJECT), pid=os.getpid(), asset_saves=0,
              source_writes=0, shader_edit_or_recompile_api_calls=0, rows=[])
KEEP = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(asset):
    assert asset in ASSETS
    return PROJECT / 'Content' / (asset.removeprefix('/Game/') + '.uasset')


def exported_property(obj, name):
    try:
        value = obj.get_editor_property(name)
        return value.get_path_name() if isinstance(value, unreal.Object) else str(value)
    except Exception as error:
        return dict(unexposed=True, error=str(error))


def run():
    assert PROJECT == WORK.resolve(), 'Probe is restricted to the task private project'
    assert OUTPUT.is_relative_to(BASE.resolve()) and OUTPUT != BASE.resolve()
    assert OUTPUT.is_dir(), 'Root must allocate a fresh output directory'
    assert not (OUTPUT / 'Probe.json').exists(), 'Preserve previous probe evidence'
    before = {asset: sha(disk(asset)) for asset in ASSETS}
    for index, asset in enumerate(ASSETS):
        obj = unreal.load_asset(asset)
        assert obj, asset
        KEEP.append(obj)
        path = OUTPUT / (str(index) + '_' + obj.get_name() + '.t3d')
        assert not path.exists(), 'Never overwrite an earlier export'
        task = unreal.AssetExportTask()
        task.object = obj
        task.filename = str(path)
        task.exporter = unreal.ObjectExporterT3D()
        task.automated = True
        task.prompt = False
        task.replace_identical = False
        assert unreal.Exporter.run_asset_export_task(task), asset
        row = dict(asset=obj.get_path_name(), native_file=str(disk(asset)),
                   native_sha256=before[asset], export=str(path), export_sha256=sha(path))
        if isinstance(obj, unreal.Material):
            row['material_properties'] = {key: exported_property(obj, key) for key in
                ('blend_mode', 'shading_model', 'two_sided', 'refraction_method',
                 'used_with_particle_sprites', 'used_with_mesh_particles')}
        elif isinstance(obj, unreal.MaterialInstanceConstant):
            row['parent'] = exported_property(obj, 'parent')
            row['base_property_overrides'] = exported_property(obj, 'base_property_overrides')
            source = MI_SOURCES[asset]
            props = json.loads(source.read_text(encoding='utf-8-sig'))[0]['Properties']
            row['original_source'] = dict(path=str(source), sha256=sha(source),
                base_property_overrides=props.get('BasePropertyOverrides'))
            row['effective_scalar_parameters'] = {
                value['ParameterInfo']['Name']:
                unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                    obj, value['ParameterInfo']['Name'])
                for value in props.get('ScalarParameterValues', [])
            }
            row['effective_texture_parameters'] = {}
            for value in props.get('TextureParameterValues', []):
                name = value['ParameterInfo']['Name']
                texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(obj, name)
                row['effective_texture_parameters'][name] = texture.get_path_name() if texture else None
        REPORT['rows'].append(row)
    after = {asset: sha(disk(asset)) for asset in ASSETS}
    REPORT['before'] = before
    REPORT['after'] = after
    REPORT['package_bytes_unchanged'] = before == after
    assert before == after, 'A saved asset changed during read-only loading/export'
    REPORT['status'] = 'passed'


try:
    run()
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
finally:
    assert OUTPUT.is_relative_to(BASE.resolve()) and OUTPUT.is_dir()
    with (OUTPUT / 'Probe.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(REPORT, ensure_ascii=False, indent=2) + '\n')
if REPORT['status'] != 'passed':
    raise RuntimeError(REPORT.get('error', 'Roar02 probe failed'))
