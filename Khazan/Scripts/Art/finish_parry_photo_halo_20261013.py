"""Dedicated feathered, irregular halo shader on the existing finite emitter."""
from pathlib import Path
import json,os,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
mi=u.load_asset(BASE+'/MI_Parry_PurpleHalo');assert mi
shutil.copy2(ROOT/('Content/'+BASE.removeprefix('/Game/')+'/MI_Parry_PurpleHalo.uasset'),OUT/'HaloMI_Before.uasset')
old_role=LIB.get_material_instance_scalar_parameter_value(mi,'ParryHaloRole')
path=BASE+'/M_Parry_Halo';assert not EAL.does_asset_exist(path)
m=EAL.duplicate_asset(BASE+'/M_FM_fluid_A',path);assert m;LIB.delete_all_material_expressions(m)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);m.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
def node(cls):return LIB.create_material_expression(m,cls)
def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
def custom(code,names,typ):
    c=node(u.MaterialExpressionCustom);c.set_editor_property('code',code);c.set_editor_property('output_type',typ)
    inputs=[]
    for name in names:
        i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    c.set_editor_property('inputs',inputs);return c
uv=node(u.MaterialExpressionTextureCoordinate);pc=node(u.MaterialExpressionParticleColor)
noise=node(u.MaterialExpressionTextureSampleParameter2D);noise.set_editor_property('parameter_name','ParryHaloNoise');noise.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/Noise/FT_PerlinNoise_RG'));noise.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
shape=custom('float2 p=UV*2-1;float r=length(p);float angle=atan2(p.y,p.x);float radius=.72+.025*sin(angle*5)+(Noise.r-.5)*.045;float ring=exp(-pow((r-radius)/.15,2))*(1-smoothstep(.83,1,r));return ring*lerp(.35,1,saturate(Noise.g*1.7))*lerp(.55,1,smoothstep(-.9,.5,p.y));',['UV','Noise'],u.CustomMaterialOutputType.CMOT_FLOAT1)
shape.set_editor_property('description','Assistant TEMP photo reconstruction: irregular magenta/violet arc, continuous radial fade, exact zero outside circle; no rectangular mask')
link(uv,'',shape,'UV');link(noise,'RGB',shape,'Noise')
power=node(u.MaterialExpressionScalarParameter);power.set_editor_property('parameter_name','ParryHaloIntensity');power.set_editor_property('default_value',4)
color=custom('float t=saturate(UV.y);float3 tint=lerp(float3(3.2,.1,1.2),float3(1.1,.05,3.5),t);return Shape*tint*Intensity*max(Color.r,max(Color.g,Color.b));',['UV','Shape','Intensity','Color'],u.CustomMaterialOutputType.CMOT_FLOAT3)
link(uv,'',color,'UV');link(shape,'',color,'Shape');link(power,'',color,'Intensity');link(pc,'RGB',color,'Color')
assert LIB.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
alpha=custom('return Shape*saturate(Alpha);',['Shape','Alpha'],u.CustomMaterialOutputType.CMOT_FLOAT1);link(shape,'',alpha,'Shape');link(pc,'A',alpha,'Alpha');assert LIB.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
assert not list(LIB.recompile_material(m));assert EAL.save_loaded_asset(m,only_if_is_dirty=False)
LIB.set_material_instance_parent(mi,m);LIB.update_material_instance(mi);assert EAL.save_loaded_asset(mi,only_if_is_dirty=False)
(OUT/'Halo.json').write_text(json.dumps({'status':'saved','rhi_pending':True,'old_mi_role_readback':old_role,'parent':path,'temporary_intensity':4,'palette_temporary':[[3.2,.1,1.2],[1.1,.05,3.5]],'numeric_source':'Assistant photo reconstruction, not original shader values; original colour/lifetime/growth emitter inputs retained; CPU size contract in CPUContract01'},indent=2),encoding='utf-8')
