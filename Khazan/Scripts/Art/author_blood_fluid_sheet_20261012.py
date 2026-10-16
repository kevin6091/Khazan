"""Original sixteen-frame fluid atlas, with an explicitly reconstructed packed-channel adapter."""
from pathlib import Path
import unreal,os,json,traceback
ROOT=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(ROOT)
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary;d={'status':'running'}
def node(m,c,**props):
    n=lib.create_material_expression(m,c)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def connect(a,b,pin,out=''):assert lib.connect_material_expressions(a,out,b,pin)
def custom(m,code,names,output):
    inputs=[]
    for name in names:i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    return node(m,unreal.MaterialExpressionCustom,code=code,inputs=inputs,output_type=output)
try:
    source=unreal.load_asset('/Game/_Art/Effects/Shared/Textures/SubUV/FT_Subuv_Fluid_001');assert source
    name='FT_Monster_HitBloodFluid';texture=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,'/Game/_Art/Effects/Combat/Blood',source);assert texture
    texture.set_editor_property('srgb',False);assert unreal.EditorAssetLibrary.save_loaded_asset(texture,only_if_is_dirty=False)
    name='M_Monster_HitBloodFluid';m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/_Art/Effects/Combat/Blood',unreal.Material,unreal.MaterialFactoryNew());assert m
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('two_sided',True)
    uv=node(m,unreal.MaterialExpressionTextureCoordinate);age=node(m,unreal.MaterialExpressionParticleRelativeTime)
    frames=custom(m,'float f=floor(saturate(Age)*15);return (UV+float2(fmod(f,4),floor(f/4)))/4;',['UV','Age'],unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    connect(uv,frames,'UV');connect(age,frames,'Age')
    tex=node(m,unreal.MaterialExpressionTextureSampleParameter2D,parameter_name='BloodFluidAtlas',texture=texture,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    connect(frames,tex,'UVs')
    color=node(m,unreal.MaterialExpressionParticleColor)
    opacity=custom(m,'return saturate(pow(saturate(max(T.r,T.b)),Power)*Density)*Alpha;',['T','Power','Density','Alpha'],unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    connect(tex,opacity,'T','RGB');connect(color,opacity,'Alpha','A')
    for name,v in [('BloodMaskPower',.45),('BloodMaskDensity',2.5)]:connect(node(m,unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=v),opacity,'Power' if name.endswith('Power') else 'Density')
    assert lib.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
    base=node(m,unreal.MaterialExpressionVectorParameter,parameter_name='BloodColor',default_value=unreal.LinearColor(.06,.0008,.002,1))
    assert lib.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for name,v,p in [('BloodRoughness',.14,unreal.MaterialProperty.MP_ROUGHNESS),('BloodMetallic',.25,unreal.MaterialProperty.MP_METALLIC)]:
        assert lib.connect_material_property(node(m,unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=v),'',p)
    lib.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES);lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    d.update(status='passed',saved=[texture.get_path_name(),m.get_path_name()],source=source.get_path_name(),grid={'rows':4,'columns':4,'status':'calculated from exported atlas, not original native shader'},mask='max(R,B); G has solid green background and is excluded',temporary={'BloodMaskPower':.45,'BloodMaskDensity':2.5,'BloodColor_linear':[.06,.0008,.002],'roughness':.14})
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'FluidAuthor.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
