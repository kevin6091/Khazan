"""Local colour/distortion separation; no shared or gameplay assets are saved."""
from pathlib import Path
import hashlib,json,os,re,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
for f in (ROOT/'Content/_Art/Effects/Combat/GuardParry/PlayerParry/Reference').glob('*.uasset'):
    (OUT/'Before').mkdir(exist_ok=True);shutil.copy2(f,OUT/'Before'/f.name)
H={};source=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
source=source.replace("'bEnabled':'FBoolProperty'","'bEnabled':'FBoolProperty','Material':'FObjectPropertyBase'")
exec(compile(source,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);before=H['export'](ps,'Before.t3d')
def node(m,cls):return LIB.create_material_expression(m,cls)
def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
def custom(m,code,names,typ):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',typ)
    pins=[]
    for name in names:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins);return n
def save(a):assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
for name in ['MI_FMI_fluid_A_11','MI_FMI_fluid_A_12','MI_FMI_fluid_A_13','MI_FMI_fluid_A_15','MI_Parry_PurpleHalo','MI_FMI_SubUV_color_A_16']:
    mi=u.load_asset(BASE+'/'+name);o=mi.get_editor_property('base_property_overrides')
    o.set_editor_property('override_blend_mode',True);o.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);mi.set_editor_property('base_property_overrides',o)
    if name=='MI_Parry_PurpleHalo':LIB.set_material_instance_vector_parameter_value(mi,'ParryPhotoTint',u.LinearColor(2.6,.12,1.8,1))
    LIB.update_material_instance(mi);save(mi)
distpath=BASE+'/M_Parry_Distortion';assert not EAL.does_asset_exist(distpath)
m=EAL.duplicate_asset(BASE+'/M_FM_fluid_A',distpath);assert m
LIB.delete_all_material_expressions(m)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('refraction_method',u.RefractionMode.RM_PIXEL_NORMAL_OFFSET)
uv=node(m,u.MaterialExpressionTextureCoordinate);pc=node(m,u.MaterialExpressionParticleColor)
noise=node(m,u.MaterialExpressionTextureSampleParameter2D);noise.set_editor_property('parameter_name','Tex_Refrac')
noise.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/Noise/FT_PerlinNoise_RG'));noise.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
strength=node(m,u.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','ParryRefractionIOROffset');strength.set_editor_property('default_value',.06)
mask=custom(m,'float r=length(UV*2-1);return exp(-4*r*r)*(1-smoothstep(.82,1,r))*saturate(Alpha);',['UV','Alpha'],u.CustomMaterialOutputType.CMOT_FLOAT1)
mask.set_editor_property('description','Assistant TEMP circular distortion envelope; exactly flat normal/IOR1 at card border; source shader stripped')
link(uv,'',mask,'UV');link(pc,'A',mask,'Alpha')
normal=custom(m,'return normalize(float3((Noise.rg*2-1)*Mask,1));',['Noise','Mask'],u.CustomMaterialOutputType.CMOT_FLOAT3)
link(noise,'RGB',normal,'Noise');link(mask,'',normal,'Mask');assert LIB.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
ior=custom(m,'return 1+Strength*Mask;',['Strength','Mask'],u.CustomMaterialOutputType.CMOT_FLOAT1)
link(strength,'',ior,'Strength');link(mask,'',ior,'Mask');assert LIB.connect_material_property(ior,'',u.MaterialProperty.MP_REFRACTION)
zero=node(m,u.MaterialExpressionConstant);zero.set_editor_property('r',0)
assert LIB.connect_material_property(zero,'',u.MaterialProperty.MP_OPACITY)
assert LIB.connect_material_property(zero,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert not list(LIB.recompile_material(m));save(m)
mi=u.load_asset(BASE+'/MI_FMI_fluid_A_162');LIB.set_material_instance_parent(mi,m)
o=mi.get_editor_property('base_property_overrides');o.set_editor_property('override_blend_mode',True);o.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mi.set_editor_property('base_property_overrides',o);LIB.update_material_instance(mi);save(mi)
changes=[]
for idx in [2,13]:
    block=next(x.group(0) for x in re.finditer(r'^      Begin Object Name="([^\"]+)" .*?^      End Object',before,re.M|re.S) if ('ParticleSpriteEmitter_'+str(idx)+'.ParticleLODLevel') in x.group(0)[:500])
    path=re.search(r"ExportPath=\"[^']+'([^']+)'",block).group(1);lod=u.load_object(None,path)
    refs=re.findall(r'Modules\(\d+\)="[^\x27]+\x27([^\x27]+)\x27"',block)
    modules=[u.load_object(None,p if p.startswith('/') else ps.get_path_name()+':'+p.split(':')[-1]) for p in refs];assert all(modules)
    removed=[x.get_path_name() for x in modules if x.get_class().get_name()=='ParticleModuleCameraOffset']
    modules=[x for x in modules if x.get_class().get_name()!='ParticleModuleCameraOffset']
    H['set_owned'](lod,'Modules','('+','.join(H['token'](x) for x in modules)+')');changes+=removed
H['rebuild'](ps);save(ps);H['export'](ps,'After.t3d')
(OUT/'Layers.json').write_text(json.dumps({'status':'passed','removed_camera_offset_modules':changes,'removed_offset_source_cm':200,'adaptation':'Keep source 250cm sizes/life/growth at actual world contact in current camera; source camera coupling not recreated. Assistant reconstruction, not native parity.','distortion_method':str(m.get_editor_property('refraction_method')),'distortion_opacity':0,'temporary_ior_offset':.06,'outer_tint_temporary':[2.6,.12,1.8]},indent=2),encoding='utf-8')
