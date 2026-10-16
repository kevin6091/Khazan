"""Reduce discrete image copies while keeping the source radial-blur timing."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

root = Path(__file__).resolve().parents[2]
out = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
file = root / 'Content/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/M_Parry_ScreenRadialBlur.uasset'
before = hashlib.sha256(file.read_bytes()).hexdigest()
assert before == '7d6e0c3455ae21029abbd20f8115ef8d1d2d8a22dbf220946d4700f632fad979', before
shutil.copy2(file, out / 'M_Parry_ScreenRadialBlur_Before.uasset')
material = u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/M_Parry_ScreenRadialBlur')
lib = u.MaterialEditingLibrary
blur = next(n for n in lib.get_material_expressions(material) if isinstance(n, u.MaterialExpressionCustom))
code = str(blur.get_editor_property('code'))
assert 'float amount = saturate(Strength * envelope);' in code
assert 'i <= 4' in code and 'return result * 0.2;' in code
code = code.replace('float amount = saturate(Strength * envelope);',
                    'float amount = saturate(Strength * envelope) * UVScale;')
code = code.replace('i <= 4', 'i <= 8').replace('i / 4.0', 'i / 8.0')
code = code.replace('return result * 0.2;', 'return result / 9.0;')
blur.set_editor_property('code', code)
scale = lib.create_material_expression(material, u.MaterialExpressionScalarParameter)
scale.set_editor_property('parameter_name', 'ParryBlurUVScale')
scale.set_editor_property('default_value', .12)
pins = list(blur.get_editor_property('inputs'))
pin = u.CustomInput()
pin.set_editor_property('input_name', 'UVScale')
pins.append(pin)
blur.set_editor_property('inputs', pins)
assert lib.connect_material_expressions(scale, '', blur, 'UVScale')
errors = list(lib.recompile_material(material))
assert not errors, errors
assert u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
(out / 'Refinement.json').write_text(json.dumps({
    'status': 'saved', 'before_sha256': before,
    'after_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    'source_direct_unchanged': {'strength': .2, 'hold_s': .16745299,
                                'blend_in_s': .02, 'blend_out_s': .3},
    'assistant_temporary_uv_scale': .12,
    'purpose': 'Narrow each radial offset and use eight taps for smooth blur instead of four separated image copies',
    'shader_errors': errors, 'rhi_visual_pending': True
}, indent=2), encoding='utf-8')
