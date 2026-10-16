"""Expose one temporary scene-visibility gain without changing source hue/curves."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
PATH = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/M_Parry_JustGuardFlare'
FILE = ROOT / ('Content/' + PATH.removeprefix('/Game/') + '.uasset')
material = u.load_asset(PATH)
assert material
before = hashlib.sha256(FILE.read_bytes()).hexdigest()
shutil.copy2(FILE, OUT/'JustGuardFlareBeforeGain.uasset')
lib = u.MaterialEditingLibrary
nodes = list(lib.get_material_expressions(material))
emissive = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                and n.get_editor_property('output_type') == u.CustomMaterialOutputType.CMOT_FLOAT3)
gain = next((n for n in nodes if isinstance(n, u.MaterialExpressionScalarParameter)
             and str(n.get_editor_property('parameter_name')) == 'ParryVisibilityGain'), None)
if gain is None:
    gain = lib.create_material_expression(material, u.MaterialExpressionScalarParameter)
    gain.set_editor_property('parameter_name', 'ParryVisibilityGain')
    pin = u.CustomInput()
    pin.set_editor_property('input_name', 'Gain')
    emissive.set_editor_property('inputs', list(emissive.get_editor_property('inputs')) + [pin])
    emissive.set_editor_property('code', emissive.get_editor_property('code').replace(
        '*saturate(Alpha)*feather;', '*saturate(Alpha)*feather*Gain;'))
    assert lib.connect_material_expressions(gain, '', emissive, 'Gain')
gain.set_editor_property('default_value', 16.0)
assert '*Gain' in emissive.get_editor_property('code')
assert not list(lib.recompile_material(material))
u.EditorAssetLibrary.set_metadata_tag(material, 'KZParryVisibilityGain',
    'Assistant TEMP 16x emissive scene visibility gain; source FMI_fluid_A_15 Emi_pow=.8 remains a separate parameter. Tuned against original combat frame.')
assert u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
(OUT/'VisibilityGain.json').write_text(json.dumps({
    'status': 'saved', 'before_sha256': before,
    'after_sha256': hashlib.sha256(FILE.read_bytes()).hexdigest(),
    'temporary_gain': 16.0, 'unit': 'linear emissive multiplier',
    'reason': 'Source texture/colour curve visibly lost against HeinMach snow in actual parry viewport',
    'source_gain': 'unconfirmed; native cooked shader graph unavailable'
}, indent=2), encoding='utf-8')
