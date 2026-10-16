"""Inspect native reflected array access in the task-owned import process."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
meta = root / 'Content/_Art/Effects/Metadata/Extraction_20261006'
rows = json.loads((meta / 'AssetManifest.json').read_text())
out = []
for row in rows:
    if row['source_type'] != 'CurveLinearColor':
        continue
    asset = unreal.load_asset(row['destination'])
    for key in ('float_curves', 'FloatCurves'):
        try:
            value = asset.get_editor_property(key)
            out.append({'asset': row['destination'], 'key': key, 'type': str(type(value)), 'value': str(value),
                        'export_text': value.export_text() if hasattr(value, 'export_text') else None})
        except Exception as e:
            out.append({'asset': row['destination'], 'key': key, 'error': str(e)})
row = next(r for r in rows if r['name'] == 'PP_AtkEx_Guard')
asset = unreal.load_asset(row['destination'])
obj = unreal.find_object(asset, 'ParticleModuleColorScaleOverLife_3')
raw = obj.get_editor_property('color_scale_over_life')
try:
    table = raw.get_editor_property('table')
    values = table.get_editor_property('values')
    out.append({'raw_type': str(type(raw)), 'table_type': str(type(table)), 'values_type': str(type(values)),
                'values': list(values), 'entry_count': table.get_editor_property('entry_count')})
except Exception as e:
    out.append({'raw_error': str(e)})
(meta / 'NumericReflectionProbe.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print('KZFX_NUMERIC_REFLECTION_PROBE', str(out)[:5000], flush=True)
