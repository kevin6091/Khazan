"""Cold saved-material readback and actual RHI compile, without asset writes."""
from pathlib import Path
import json
import os
import time
import traceback
import unreal

start = time.monotonic()
out = Path(os.environ['KZ_COMBAT_UI_OUTPUT'])
source = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Art/soften_combat_ui_brutal_alpha_20261011.py')
os.environ['KZ_COMBAT_UI_ALPHA_MODE'] = 'inspect'
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'))
alpha = next(n for n in masks if n.get_editor_property('a'))
assert [alpha.get_editor_property(c) for c in 'rgba'] == [False, False, False, True]
assert report['edge_parameters'] == [{'name': 'EdgeSoftnessPixels', 'default': 1.25}]
assert 'smoothstep(0.49 - edge, 0.49, d)' in report['custom_code']
assert 'smoothstep(0.38, 0.38 + edge, d)' in report['custom_code']
errors = list(LIB.recompile_material(mat))
assert not errors, errors
unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 30')
finished = False

def tick(delta):
    global finished
    if finished or time.monotonic() - start < 15:
        return
    try:
        stats = LIB.get_statistics(mat)
        if stats.num_pixel_shader_instructions <= 0 and time.monotonic() - start < 90:
            return
        assert stats.num_pixel_shader_instructions > 0, 'RHI shader statistics unavailable'
        text = (out / 'Editor.log').read_text(encoding='utf-8', errors='replace')
        bad = [line for line in text.splitlines() if 'Failed to compile Material' in line
               or 'Default Material will be used' in line or 'Missing ComponentMask input' in line]
        assert not bad, bad
        result = dict(status='passed', asset=PATH, project=str(ROOT), sha256=report['sha256'],
                      mask_rgba=[False, False, False, True], edge_softness_pixels=1.25,
                      pixel_instructions=stats.num_pixel_shader_instructions,
                      compile_errors=errors, material_fallbacks=bad, asset_saves=0,
                      seconds=time.monotonic() - start)
    except Exception:
        result = dict(status='failed', error=traceback.format_exc())
        unreal.log_error(result['error'])
    finished = True
    (out / 'SavedAlphaRHI.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.SystemLibrary.quit_editor()

handle = unreal.register_slate_post_tick_callback(tick)
