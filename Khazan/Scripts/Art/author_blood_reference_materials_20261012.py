"""Private material variants using original packed RGB blood masks, without altering original textures."""
from pathlib import Path
import unreal, os, json, traceback
ROOT=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(ROOT)
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary
d={'status':'running','saved':[],'original_masks':[],'temporary_parameters':{}}
def node(m,c,**props):
    n=lib.create_material_expression(m,c)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def connect(a,b,pin,out=''):assert lib.connect_material_expressions(a,out,b,pin)
def prop(a,p,out=''):assert lib.connect_material_property(a,out,p)
def scalar(m,name,v):return node(m,unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=v)
def custom(m,code,names):
    inputs=[]
    for name in names:
        i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    return node(m,unreal.MaterialExpressionCustom,code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,inputs=inputs)
def material(name,domain):
    path='/Game/_Art/Effects/Combat/Blood/'+name
    assert not unreal.load_asset(path),'Use a new private trial instead of deleting rooted expressions: '+path
    m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/_Art/Effects/Combat/Blood',unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('material_domain',domain);m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    if domain==unreal.MaterialDomain.MD_SURFACE:m.set_editor_property('two_sided',True)
    return m
def sample(m,name,path):
    texture=unreal.load_asset(path);assert texture,path;d['original_masks'].append(texture.get_path_name())
    return node(m,unreal.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=texture,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
def shade(m,color,rough,metal):
    prop(node(m,unreal.MaterialExpressionVectorParameter,parameter_name='BloodColor',default_value=unreal.LinearColor(*color,1)),unreal.MaterialProperty.MP_BASE_COLOR)
    prop(scalar(m,'BloodRoughness',rough),unreal.MaterialProperty.MP_ROUGHNESS)
    prop(scalar(m,'BloodMetallic',metal),unreal.MaterialProperty.MP_METALLIC)
def save(m):
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);d['saved'].append(m.get_path_name())
try:
    m=material('M_Monster_HitBloodGround',unreal.MaterialDomain.MD_DEFERRED_DECAL)
    tex=sample(m,'BloodMask','/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Decal/FT_Decal_Blood_A_003')
    mask=custom(m,'float a=Channel<.5?Mask.r:(Channel<1.5?Mask.g:Mask.b);return saturate(pow(saturate(a),Power)*Density)*Fade;',['Mask','Channel','Power','Density','Fade'])
    connect(tex,mask,'Mask','RGB');connect(scalar(m,'BloodMaskChannel',0),mask,'Channel')
    connect(scalar(m,'BloodMaskPower',.6),mask,'Power');connect(scalar(m,'BloodMaskDensity',2.4),mask,'Density')
    connect(node(m,unreal.MaterialExpressionDecalLifetimeOpacity),mask,'Fade');prop(mask,unreal.MaterialProperty.MP_OPACITY)
    shade(m,(.032,.0008,.0015),.12,.25);save(m)
    m=material('M_Monster_HitBloodSheet',unreal.MaterialDomain.MD_SURFACE)
    tex=sample(m,'BloodMask','/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Decal/FT_Decal_Blood_004')
    particle=node(m,unreal.MaterialExpressionParticleColor)
    mask=custom(m,'return saturate(pow(saturate(max(Mask.r,max(Mask.g,Mask.b))),Power)*Density)*Alpha;',['Mask','Power','Density','Alpha'])
    connect(tex,mask,'Mask','RGB');connect(scalar(m,'BloodMaskPower',.65),mask,'Power');connect(scalar(m,'BloodMaskDensity',1.8),mask,'Density');connect(particle,mask,'Alpha','A');prop(mask,unreal.MaterialProperty.MP_OPACITY)
    shade(m,(.065,.001,.0025),.16,.25);save(m)
    d['temporary_parameters']={'ground':{'BloodColor_linear':[.032,.0008,.0015],'BloodMaskPower':.6,'BloodMaskDensity':2.4,'BloodRoughness':.12},'sheet':{'BloodColor_linear':[.065,.001,.0025],'BloodMaskPower':.65,'BloodMaskDensity':1.8,'BloodRoughness':.16},'metallic_original_PD_Blood_Base_MetalPower':.25}
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'MaterialAuthor.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
