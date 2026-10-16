"""Real-RHI compile of the imported packs' material graphs; never save assets."""
from pathlib import Path
import json
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012'
ROOTS = ('/Game/Cursed_Magic/', '/Game/NiagaraVFXBundle/', '/Game/ARPGVFXPack03/')
ROWS = [r for r in json.loads((META / 'StageDependencies.json').read_text())['assets'] if r['class'] == 'Material' and r['package'].startswith(ROOTS)]
report = {'status': 'running', 'actual_rhi': True, 'project': str(Path(unreal.Paths.project_dir()).resolve()), 'material_count': len(ROWS), 'materials': [], 'errors': [], 'asset_saves': 0, 'scope': 'Material graph shader compilation only; no effect screenshots, particle simulation, gameplay routing or shipping performance validation.'}
out = META / 'MainShaders.json'
start = time.monotonic()
try:
    for index, row in enumerate(ROWS):
        item = {'package': row['package']}
        try:
            asset = unreal.load_asset(row['object_path'])
            assert isinstance(asset, unreal.Material), row
            errors = list(unreal.MaterialEditingLibrary.recompile_material(asset))
            stats = unreal.MaterialEditingLibrary.get_statistics(asset)
            item.update(compile_errors=[str(e) for e in errors], pixel_instructions=stats.num_pixel_shader_instructions, vertex_instructions=stats.num_vertex_shader_instructions)
            item['status'] = 'failed' if errors else 'passed'
            if errors:
                report['errors'].append(item)
        except Exception:
            item.update(status='failed', error=traceback.format_exc())
            report['errors'].append(item)
        report['materials'].append(item)
        report.update(processed=index+1, elapsed_seconds=round(time.monotonic()-start, 2))
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if index % 25 == 0:
            print('FAB_VFX_SHADERS ' + json.dumps({'processed': index+1, 'total': len(ROWS), 'errors': len(report['errors'])}), flush=True)
    report['status'] = 'failed' if report['errors'] else 'passed'
except Exception:
    report['status'] = 'failed'
    report['errors'].append({'error': traceback.format_exc()})
out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('FAB_VFX_SHADERS_FINAL ' + json.dumps({k: v for k, v in report.items() if k != 'materials'}), flush=True)
