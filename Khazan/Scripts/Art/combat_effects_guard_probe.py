"""Read source versus effective material parameters for the guard recovery."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
meta = root / 'Content/_Art/Effects/Metadata/Extraction_20261006'
rows = json.loads((meta / 'AssetManifest.json').read_text())
lib = unreal.MaterialEditingLibrary
report = []
for row in rows:
    if row['name'] not in ('FMI_fluid_A_10', 'FMI_fluid_A_11', 'FMI_fluid_A_13', 'FMI_Subuv_Atlas_B_01'):
        continue
    obj = unreal.load_asset(row['destination'])
    original = json.loads((root / row['source_json']).read_text(encoding='utf-8-sig'))[0]['Properties']
    entry = {'asset': row['destination'], 'parameters': []}
    for key, getter in [('ScalarParameterValues', lib.get_material_instance_scalar_parameter_value),
                         ('VectorParameterValues', lib.get_material_instance_vector_parameter_value),
                         ('TextureParameterValues', lib.get_material_instance_texture_parameter_value)]:
        for item in original.get(key, []):
            name = item['ParameterInfo']['Name']
            value = getter(obj, name)
            if isinstance(value, unreal.LinearColor):
                value = dict(zip('RGBA', (value.r, value.g, value.b, value.a)))
            elif isinstance(value, unreal.Object):
                value = value.get_path_name()
            entry['parameters'].append({'name': name, 'source': item['ParameterValue'], 'effective_native': value})
    report.append(entry)
(meta / 'GuardEffectiveMaterialParameters.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('KZFX_GUARD_EFFECTIVE', json.dumps(report)[:6000], flush=True)
