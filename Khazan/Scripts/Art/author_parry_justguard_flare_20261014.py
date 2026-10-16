"""Recover the source JustGuard flare texture/alpha contract in a local material."""

from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry'
PS = BASE + '/PP_Player_JustGuard_Halo'
MATERIAL = BASE + '/M_Parry_JustGuardFlare'
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
report = {'status': 'running', 'particle': PS, 'material': MATERIAL}

def node(material, cls, **props):
    result = LIB.create_material_expression(material, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result

def link(source, output, target, input_name):
    assert LIB.connect_material_expressions(source, output, target, input_name)

try:
    assert not EAL.does_asset_exist(MATERIAL)
    particle = u.load_asset(PS)
    assert particle
    ps_file = ROOT / ('Content/' + PS.removeprefix('/Game/') + '.uasset')
    report['particle_before_sha256'] = hashlib.sha256(ps_file.read_bytes()).hexdigest()
    shutil.copy2(ps_file, OUT / 'JustGuardHaloBeforeMaterial.uasset')
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(
        MATERIAL.rsplit('/', 1)[-1], BASE, u.Material, u.MaterialFactoryNew())
    assert material
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    flare = node(material, u.MaterialExpressionTextureSampleParameter2D,
        parameter_name='Tex_Emi', texture=u.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Flare/FT_Flare_004_LSY'),
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    mask = node(material, u.MaterialExpressionTextureSampleParameter2D,
        parameter_name='Tex_OPA', texture=u.load_asset('/Game/_Art/Effects/Shared/Textures/External/T_GradientGlow'),
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    assert flare.get_editor_property('texture') and mask.get_editor_property('texture')
    color = node(material, u.MaterialExpressionParticleColor)
    uv = node(material, u.MaterialExpressionTextureCoordinate)
    strength = node(material, u.MaterialExpressionScalarParameter, parameter_name='SourceEmiPow', default_value=.8)
    custom = node(material, u.MaterialExpressionCustom)
    custom.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins = []
    for name in ['Flare', 'Mask', 'Particle', 'Alpha', 'UV', 'Strength']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    custom.set_editor_property('code',
        'float2 border=min(UV,1-UV);'
        'float feather=smoothstep(0,0.04,min(border.x,border.y));'
        'return Flare*Particle*Strength*saturate(Mask)*saturate(Alpha)*feather;')
    custom.set_editor_property('description',
        'Source Tex_Emi, Tex_OPA, ParticleColor and Emi_pow .8; existing TEMP .04 UV edge feather. Cooked source shader topology unavailable.')
    link(flare, 'RGB', custom, 'Flare')
    link(mask, 'R', custom, 'Mask')
    link(color, 'RGB', custom, 'Particle')
    link(color, 'A', custom, 'Alpha')
    link(uv, '', custom, 'UV')
    link(strength, '', custom, 'Strength')
    assert LIB.connect_material_property(custom, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = node(material, u.MaterialExpressionCustom)
    alpha.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in ['Mask', 'Alpha', 'UV']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    alpha.set_editor_property('inputs', pins)
    alpha.set_editor_property('code',
        'float2 border=min(UV,1-UV);return saturate(Mask)*saturate(Alpha)*smoothstep(0,0.04,min(border.x,border.y));')
    link(mask, 'R', alpha, 'Mask')
    link(color, 'A', alpha, 'Alpha')
    link(uv, '', alpha, 'UV')
    assert LIB.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
    LIB.set_material_usage(material, u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES)
    errors = list(LIB.recompile_material(material))
    assert not errors, errors
    EAL.set_metadata_tag(material, 'KZSourceMaterial',
        'BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Fluid/FMI_fluid_A_15; source texture/opacity references and Emi_pow=.8. Shader graph stripped; emissive topology is an adapter.')
    assert EAL.save_loaded_asset(material, only_if_is_dirty=False)
    H = {}
    helper = (ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
    helper = helper.replace("'bEnabled':'FBoolProperty'", "'bEnabled':'FBoolProperty','Material':'FObjectPropertyBase'")
    exec(compile(helper, 'cascade_helpers', 'exec'), H)
    H['DEST'] = PS
    H['OUT'] = OUT
    required = u.load_object(None, particle.get_path_name() + ':ParticleModuleRequired_4')
    assert required
    H['set_owned'](required, 'Material', H['token'](material))
    H['rebuild'](particle)
    assert EAL.save_loaded_asset(particle, only_if_is_dirty=False)
    exported = H['export'](particle, 'JustGuardHaloWithFlare.t3d')
    assert MATERIAL in exported
    report['particle_after_sha256'] = hashlib.sha256(ps_file.read_bytes()).hexdigest()
    report['material_sha256'] = hashlib.sha256((ROOT / ('Content/' + MATERIAL.removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()
    report['status'] = 'saved'
except Exception as exc:
    report['status'] = 'failed'
    report['error'] = repr(exc)
    raise
finally:
    (OUT/'JustGuardFlareAuthor.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
