"""Fire-specific recovery graphs using the original atlases and parameters."""
from pathlib import Path
import ast
import json
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
# Load only the reusable authoring definitions; do not rerun import stages.
p=ROOT/'Scripts/Art/heinmach_tutorial_fires_import.py'
t=ast.parse(p.read_text(encoding='utf-8'));t.body=[n for n in t.body if not isinstance(n,ast.Try)]
ctx={'__file__':str(p)};exec(compile(t,str(p),'exec'),ctx);g=ctx['g']
LIB=unreal.MaterialEditingLibrary
rows=ctx['all_rows'];own=[r for r in rows if not r['reuse_existing']]
report={'materials':[],'temporary_native_values':{'FireRadianceGain':256.,'NativeFireReferenceGain':256.,'reason':'Existing native outdoor HDR gain used as a brightness reference; original shader radiance unavailable. EyeAdaptationInverse cancels the current exposure after normalizing by this reference, so EV4 caves do not blow out the same fire. Adjustable native parameters, not original radiance.'},'smoke_opacity':'R density from original DXT1 grayscale atlas, not its constant opaque A.'}


def material(row):
    m=unreal.load_asset(row['destination']);assert m
    LIB.delete_all_material_expressions(m)
    props=g['source'](row).get('Properties',{});defaults=ctx['parameters'](g['source'](row))
    for child in own:
        if child['source_type']!='MaterialInstanceConstant':continue
        cp=g['source'](child).get('Properties',{})
        if cp.get('Parent',{}).get('ObjectPath','').split('.')[0]!=row['source_package']:continue
        for field,slot in [('ScalarParameterValues','ScalarValues'),('VectorParameterValues','VectorValues'),('TextureParameterValues','TextureValues')]:
            for v in cp.get(field,[]):defaults[slot].setdefault(v['ParameterInfo']['Name'],v['ParameterValue'])
    idx=0
    def node(cls,**kw):
        nonlocal idx
        n=LIB.create_material_expression(m,cls,-800+(idx%5)*220,(idx//5)*140);idx+=1
        for k,v in kw.items():n.set_editor_property(k,v)
        return n
    def con(a,out,b,pin):assert LIB.connect_material_expressions(a,out,b,pin)
    def custom(code,pins,kind=unreal.CustomMaterialOutputType.CMOT_FLOAT1):
        n=node(unreal.MaterialExpressionCustom,code=code,output_type=kind,inputs=[g['custom_input'](x) for x in pins]);return n
    def scalar(name,value=1.):return s.get(name) or node(unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    def emissive(color):
        normalize=custom('return Color/max(ReferenceGain,0.0001);',['Color','ReferenceGain'],unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        con(color,'',normalize,'Color');con(scalar('NativeFireReferenceGain',256.),'',normalize,'ReferenceGain')
        adapt=node(unreal.MaterialExpressionEyeAdaptationInverse)
        con(normalize,'',adapt,'LightValueInput');LIB.connect_material_property(adapt,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    s={name:node(unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=value) for name,value in defaults['ScalarValues'].items()}
    v={name:node(unreal.MaterialExpressionVectorParameter,parameter_name=name,default_value=unreal.LinearColor(value['R'],value['G'],value['B'],value.get('A',1))) for name,value in defaults['VectorValues'].items()}
    tex={}
    for name,value in defaults['TextureValues'].items():
        asset=g['ref'](value)
        if not asset or not isinstance(asset,unreal.Texture2D):continue
        tex[name]=node(unreal.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=asset,sampler_type=g['sampler'](asset))
    uv=node(unreal.MaterialExpressionTextureCoordinate);age=node(unreal.MaterialExpressionParticleRelativeTime);time=node(unreal.MaterialExpressionTime);pc=node(unreal.MaterialExpressionParticleColor)
    name=row['name'];world=name=='FM_World_SubUV_color_A';flame=name=='FM_SubUV_color_B';mini=name=='FM_SubUv_Smoke_A';smoke=world;burn=name=='Base_Decal_BottomCrack'
    if world or flame or mini:
        cols=scalar('Col' if mini else 'SubUV_U');rs=scalar('Row' if mini else 'SubUV_V')
        speed=scalar('Speed' if mini else 'looping_speed',1.)
        atlas=custom('float2 grid=max(float2(Cols,Rows),1); float count=grid.x*grid.y; float f=FracLoop>0.5?frac(Time*Speed+Age)*count:min(Age*count*Speed,count-1); float frame=floor(f); return (UV+float2(fmod(frame,grid.x),floor(frame/grid.x)))/grid;',['UV','Age','Time','Cols','Rows','Speed','FracLoop'],unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        for a,pin in ((uv,'UV'),(age,'Age'),(time,'Time'),(cols,'Cols'),(rs,'Rows'),(speed,'Speed'),(node(unreal.MaterialExpressionConstant, r=1. if flame else 0.),'FracLoop')):con(a,'',atlas,pin)
        for key in ('Tex_SubUV','Tex_Emi','Tex_Opa','Main_Tex_Gray','Main_tex_RGB'):
            if key in tex:con(atlas,'',tex[key],'UVs')
    if burn:
        # Original packed footprint has an opaque A. Reconstruct the charred
        # footprint from its RGB masks, retaining source strengths/fade controls.
        # This is a native recovery formula; the original panning shader is stripped.
        opa=custom('float mask=saturate(Mask.r*RStrength+Mask.g*GStrength+Mask.b*BStrength); return pow(mask,max(FadePower,0.0001))*(1-saturate(Fadeout));',['Mask','RStrength','GStrength','BStrength','FadePower','Fadeout'])
        for a,out,pin in ((tex['Texture'],'RGB','Mask'),(scalar('01_R_Power'),'','RStrength'),(scalar('02_G_Power'),'','GStrength'),(scalar('03_B_Power'),'','BStrength'),(scalar('FadePower'),'','FadePower'),(scalar('Fadeout'),'','Fadeout')):con(a,out,opa,pin)
        LIB.connect_material_property(v['Color'],'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        LIB.connect_material_property(scalar('RoughPower'),'',unreal.MaterialProperty.MP_ROUGHNESS)
        LIB.connect_material_property(node(unreal.MaterialExpressionConstant,r=0.),'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    elif smoke:
        t=tex['Tex_SubUV'];rgb=node(unreal.MaterialExpressionMultiply);con(t,'RGB',rgb,'A');con(pc,'RGB',rgb,'B')
        opa=custom('return saturate(Mask*Strength)*Alpha;',['Mask','Strength','Alpha']);con(t,'R',opa,'Mask');con(scalar('Opa_Str'),'',opa,'Strength');con(pc,'A',opa,'Alpha')
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        m.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
        LIB.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    elif flame:
        rgb=custom('return pow(max(Color,0),max(Power,0.0001))*Strength*Particle*Gain;',['Color','Power','Strength','Particle','Gain'],unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        for a,out,pin in ((tex['Tex_Emi'],'RGB','Color'),(scalar('EMI_Pow'),'','Power'),(scalar('EMI_Str'),'','Strength'),(pc,'RGB','Particle'),(scalar('FireRadianceGain',256.),'','Gain')):con(a,out,rgb,pin)
        opa=custom('return saturate(pow(max(Mask,0),max(Power,0.0001))*Strength)*Alpha;',['Mask','Power','Strength','Alpha'])
        for a,out,pin in ((tex['Tex_Opa'],'R','Mask'),(scalar('OPA_Pow'),'','Power'),(scalar('OPA_Str'),'','Strength'),(pc,'A','Alpha')):con(a,out,opa,pin)
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);emissive(rgb)
    elif mini:
        rgb=custom('float q=saturate(pow(max(Mask,0),Power)*Strength); return lerp(lerp(C1,C2,saturate(q*2)),C3,saturate(q*2-1))*q*Particle*Gain;',['Mask','Power','Strength','C1','C2','C3','Particle','Gain'],unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        for a,out,pin in ((tex['Main_Tex_Gray'],'G','Mask'),(scalar('Main_Pow'),'','Power'),(scalar('Main_Str'),'','Strength'),(v['BaseColor1'],'RGB','C1'),(v['BaseColor2'],'RGB','C2'),(v['BaseColor3'],'RGB','C3'),(pc,'RGB','Particle'),(scalar('FireRadianceGain',256.),'','Gain')):con(a,out,rgb,pin)
        opa=node(unreal.MaterialExpressionMultiply);con(tex['Main_Tex_Gray'],'G',opa,'A');con(pc,'A',opa,'B')
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);emissive(rgb)
    else:
        rgb=custom('return Color*Gain;',['Color','Gain'],unreal.CustomMaterialOutputType.CMOT_FLOAT3);con(pc,'RGB',rgb,'Color');con(scalar('FireRadianceGain',256.),'',rgb,'Gain')
        opa=node(unreal.MaterialExpressionMultiply);con(pc,'A',opa,'A')
        if tex:
            t=tex.get('Tex') or tex.get('Texture') or next(iter(tex.values()));con(t,'R',opa,'B')
        else:
            mask=custom('float2 p=(UV-0.5)*2;return pow(saturate(1-dot(p,p)),2);',['UV']);con(uv,'',mask,'UV');con(mask,'',opa,'B')
        emissive(rgb)
    if 'DepthFade' in s and not burn:
        fade=node(unreal.MaterialExpressionDepthFade);con(opa,'',fade,'Opacity');con(s['DepthFade'],'',fade,'FadeDistance');opa=fade
    LIB.connect_material_property(opa,'',unreal.MaterialProperty.MP_OPACITY)
    m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',False)
    m.set_editor_property('translucency_pass',unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    unreal.EditorAssetLibrary.set_metadata_tag(m,'KZFXRecoveryBoundary','Original fire atlases/parameters; native shader reconstruction. Frame timing, soft intersections and exposure adaptation are native; original custom shader graph unavailable.')
    errors=list(LIB.recompile_material(m));assert not errors,errors;ctx['save'](m)
    report['materials'].append({'asset':m.get_path_name(),'source':row['source_package'],'role':'ground_burn' if burn else 'lit_smoke' if smoke else 'flame_or_ember','errors':errors})


for row in own:
    if row['source_type']=='Material' and row['name']!='M_WorldProp':material(row)
ctx['world_master'](next(r for r in own if r['name']=='M_WorldProp'))
g['write']('FireShaderRecovery',report)
print('KZ_HM_FIRES_SHADERS_PASSED')
