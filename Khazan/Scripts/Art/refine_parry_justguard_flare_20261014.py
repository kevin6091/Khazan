"""Preserve the source flare ring and the separate soft central gradient."""
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
shutil.copy2(FILE, OUT / 'JustGuardFlareBefore.uasset')
nodes = [node for node in u.MaterialEditingLibrary.get_material_expressions(material)
         if isinstance(node, u.MaterialExpressionCustom)]
assert len(nodes) == 2
emissive = next(node for node in nodes if node.get_editor_property('output_type') == u.CustomMaterialOutputType.CMOT_FLOAT3)
opacity = next(node for node in nodes if node is not emissive)
emissive.set_editor_property('code',
    'float2 border=min(UV,1-UV);'
    'float feather=smoothstep(0,0.04,min(border.x,border.y));'
    'float3 sourceLayers=Flare*(1+saturate(Mask));'
    'return sourceLayers*Particle*Strength*saturate(Alpha)*feather;')
opacity.set_editor_property('code',
    'float2 border=min(UV,1-UV);'
    'return saturate(Alpha)*smoothstep(0,0.04,min(border.x,border.y));')
# Opacity also needs the source flare input, previously only the core mask.
pins = list(opacity.get_editor_property('inputs'))
if not any(str(pin.get_editor_property('input_name')) == 'Flare' for pin in pins):
    flare_pin = u.CustomInput()
    flare_pin.set_editor_property('input_name', 'Flare')
    pins.append(flare_pin)
    opacity.set_editor_property('inputs', pins)
flare = next(node for node in u.MaterialEditingLibrary.get_material_expressions(material)
             if isinstance(node, u.MaterialExpressionTextureSampleParameter2D)
             and str(node.get_editor_property('parameter_name')) == 'Tex_Emi')
mask = next(node for node in u.MaterialEditingLibrary.get_material_expressions(material)
            if isinstance(node, u.MaterialExpressionTextureSampleParameter2D)
            and str(node.get_editor_property('parameter_name')) == 'Tex_OPA')
mask.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
assert u.MaterialEditingLibrary.connect_material_expressions(flare, 'RGB', opacity, 'Flare')
errors = list(u.MaterialEditingLibrary.recompile_material(material))
assert not errors, errors
u.EditorAssetLibrary.set_metadata_tag(material, 'KZParryFlareAdapter',
    'Source Tex_Emi and Tex_OPA soft layers combined by max, not multiplied; source ParticleColor/Emi_pow retained. Existing TEMP .04 UV feather; cooked native shader topology unavailable.')
assert u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
(OUT/'JustGuardFlareRefine.json').write_text(json.dumps({
    'status': 'saved', 'before_sha256': before,
    'after_sha256': hashlib.sha256(FILE.read_bytes()).hexdigest(),
    'source_texture_roles': {'Tex_Emi': 'soft outer flare', 'Tex_OPA': 'soft central gradient'},
    'native_shader_parity': 'unconfirmed; source cooked graph unavailable'
}, indent=2), encoding='utf-8')
