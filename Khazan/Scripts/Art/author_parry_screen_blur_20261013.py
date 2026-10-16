"""Author the missing JustGuard radial screen blur as a local postprocess adapter."""
from pathlib import Path
import json
import os
import unreal as u

out = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
base = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
path = base + '/M_Parry_ScreenRadialBlur'
eal = u.EditorAssetLibrary
lib = u.MaterialEditingLibrary
assert not eal.does_asset_exist(path), path
material = u.AssetToolsHelpers.get_asset_tools().create_asset(
    'M_Parry_ScreenRadialBlur', base, u.Material, u.MaterialFactoryNew())
assert material
material.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
material.set_editor_property('blendable_location', u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)

scene = lib.create_material_expression(material, u.MaterialExpressionSceneTexture)
scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
clock = lib.create_material_expression(material, u.MaterialExpressionTime)

def scalar(name, value):
    node = lib.create_material_expression(material, u.MaterialExpressionScalarParameter)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    return node

start = scalar('ParryBlurStartTime', 0.0)
strength = scalar('ParryRadialBlurStrength', 0.2)
duration = scalar('ParryBlurHoldSeconds', 0.16745299)
blend_in = scalar('ParryBlurBlendInSeconds', 0.02)
blend_out = scalar('ParryBlurBlendOutSeconds', 0.3)
center = lib.create_material_expression(material, u.MaterialExpressionVectorParameter)
center.set_editor_property('parameter_name', 'ParryBlurCenter')
center.set_editor_property('default_value', u.LinearColor(.5, .5, 0, 1))

blur = lib.create_material_expression(material, u.MaterialExpressionCustom)
blur.set_editor_property('description',
    'Assistant radial sample reconstruction. Timing and final scalar are from Just_L xxPP_RadialBlur; cooked shader is unavailable.')
blur.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
blur.set_editor_property('code', r'''
float age = Now - Start;
if (age <= 0 || age >= Hold + FadeOut) return SceneColor.rgb;
float envelope = saturate(age / max(FadeIn, 0.0001)) *
                 (1 - saturate((age - Hold) / max(FadeOut, 0.0001)));
float amount = saturate(Strength * envelope);
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 travel = (Center.rg - uv) * amount;
float3 result = SceneColor.rgb;
[unroll] for (int i = 1; i <= 4; ++i)
    result += SceneTextureLookup(saturate(uv + travel * (i / 4.0)), 14, false).rgb;
return result * 0.2;
''')
sources = [('SceneColor', scene, 'Color'), ('Now', clock, ''),
           ('Start', start, ''), ('Strength', strength, ''),
           ('Hold', duration, ''), ('FadeIn', blend_in, ''),
           ('FadeOut', blend_out, ''), ('Center', center, 'RGB')]
pins = []
for name, node, output in sources:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    pins.append(pin)
blur.set_editor_property('inputs', pins)
for name, node, output in sources:
    assert lib.connect_material_expressions(node, output, blur, name), name
assert lib.connect_material_property(blur, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
errors = list(lib.recompile_material(material))
assert not errors, errors
assert eal.save_loaded_asset(material, only_if_is_dirty=False)
(out / 'RadialBlur.json').write_text(json.dumps({
    'status': 'saved', 'path': path,
    'source': 'AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L.json / xxPP_RadialBlur',
    'source_direct': {'notify_link_s': 0, 'duration_s': .16745299,
                      'blend_in_s': .02, 'blend_out_s': .3, 'end_scalar_value': .2},
    'adapter': 'screen radial multi-sample around contact; LDR after tonemapping; source shader unavailable',
    'shader_errors': errors, 'rhi_visual_pending': True
}, indent=2), encoding='utf-8')
