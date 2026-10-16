"""Read back every original raw distribution in a selected native particle graph."""
from pathlib import Path
import json
import re
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
row = next(r for r in json.loads((META / 'AssetManifest.json').read_text()) if r['name'] == 'PP_AtkEx_Guard')
asset = unreal.load_asset(row['destination'])
data = json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig'))
report = []
for export in data:
    fields = {k: v for k, v in export.get('Properties', {}).items() if isinstance(v, dict) and 'Distribution' in v and 'Table' in v}
    if not fields:
        continue
    obj = unreal.find_object(asset, export['Name'])
    if not obj:
        continue
    for key, original in fields.items():
        try:
            native = obj.get_editor_property(key).export_text()
            values = re.search(r'Values=\(([^()]*)\)', native)
            values = [float(v) for v in values.group(1).split(',')] if values else []
            count = re.search(r'EntryCount=(\d+)', native)
            stride = re.search(r'EntryStride=(\d+)', native)
            item = {'object': obj.get_path_name(), 'property': key,
                    'original_count': len(original['Table'].get('Values', [])),
                    'native_count': len(values), 'native_entry_count': int(count.group(1)) if count else 0,
                    'native_stride': int(stride.group(1)) if stride else 0, 'native_text': native}
            item['valid_range'] = item['native_count'] >= item['native_entry_count'] * item['native_stride']
            report.append(item)
        except Exception as e:
            report.append({'object': obj.get_path_name(), 'property': key, 'error': str(e)})
(META / 'GuardDistributionReadback.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('KZFX_GUARD_DISTRIBUTIONS', len(report), 'invalid', [v for v in report if v.get('valid_range') is False], flush=True)
