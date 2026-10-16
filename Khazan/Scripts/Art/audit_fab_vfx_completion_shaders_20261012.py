"""Compile all relocated material graphs in real RHI without saving them."""
from pathlib import Path
import json
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012/Completion'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
LABEL = 'Main' if PROJECT == MAIN else 'Stage'
PLAN = [r for r in json.loads((META / 'RenamePlan.json').read_text()) if r['class'] == 'Material']
report = {'status': 'running', 'project': str(PROJECT), 'actual_rhi': True, 'asset_saves': 0, 'materials': [], 'errors': [], 'total': len(PLAN)}
start = time.monotonic()
try:
    for index, row in enumerate(PLAN):
        item = {'package': row['new_package']}
        try:
            asset = unreal.load_asset(row['new_object_path'])
            assert isinstance(asset, unreal.Material), row
            errors = [str(e) for e in unreal.MaterialEditingLibrary.recompile_material(asset)]
            stats = unreal.MaterialEditingLibrary.get_statistics(asset)
            item.update(errors=errors, pixel_instructions=stats.num_pixel_shader_instructions, vertex_instructions=stats.num_vertex_shader_instructions)
            assert not errors and stats.num_pixel_shader_instructions > 0, item
            item['status'] = 'passed'
        except Exception:
            item.update(status='failed', error=traceback.format_exc())
            report['errors'].append(item)
        report['materials'].append(item)
        if index % 10 == 9:
            asset = None
            unreal.SystemLibrary.collect_garbage()
        report.update(processed=index+1, elapsed_seconds=round(time.monotonic()-start, 2))
        (META / (LABEL + 'Shaders.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
        if index % 25 == 0:
            print('VFX_COMPLETION_SHADERS ' + json.dumps({'processed':index+1,'total':len(PLAN),'errors':len(report['errors'])}), flush=True)
    report['status'] = 'passed' if not report['errors'] else 'failed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append({'error': traceback.format_exc()})
(META / (LABEL + 'Shaders.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_COMPLETION_SHADERS_FINAL ' + json.dumps({k:v for k,v in report.items() if k != 'materials'}), flush=True)
