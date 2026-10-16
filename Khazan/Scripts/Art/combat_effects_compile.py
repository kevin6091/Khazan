"""Compile extraction-owned material shaders in a hidden real-RHI editor; no saves."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
REPORT = {'actual_RHI': True, 'asset_saves': False, 'user_editor_untouched': True,
          'materials': [], 'status': 'running',
          'boundary': 'Native recovery graph shader validation; not original shader equivalence.'}
START = time.monotonic()
HANDLE = None

def run(delta):
    if time.monotonic() - START < 8:
        return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    try:
        lib = unreal.MaterialEditingLibrary
        for row in ROWS:
            if row['source_type'] != 'Material':
                continue
            print('KZFX_SHADER ' + row['destination'], flush=True)
            asset = unreal.load_asset(row['destination'])
            assert isinstance(asset, unreal.Material), row
            errors = list(lib.recompile_material(asset))
            stats = lib.get_statistics(asset)
            item = {'asset': row['destination'], 'source': row['source_package'],
                    'compile_errors': errors, 'pixel_instructions': stats.num_pixel_shader_instructions,
                    'vertex_instructions': stats.num_vertex_shader_instructions}
            REPORT['materials'].append(item)
            assert not errors and stats.num_pixel_shader_instructions > 0, item
        REPORT['status'] = 'passed'
        print('KZ_COMBAT_EFFECTS_SHADERS_VERIFIED', flush=True)
    except Exception:
        REPORT['status'] = 'failed'
        REPORT['error'] = traceback.format_exc()
        unreal.log_error(REPORT['error'])
    (META / 'ShaderVerification.json').write_text(json.dumps(REPORT, indent=2) + '\n', encoding='utf-8')
    unreal.SystemLibrary.quit_editor()

HANDLE = unreal.register_slate_post_tick_callback(run)
