from pathlib import Path
import json,os,re,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
m=u.load_asset(BASE+'/M_FM_fluid_A');nodes=list(LIB.get_material_expressions(m))
pc=next(n for n in nodes if isinstance(n,u.MaterialExpressionParticleColor))
tint=next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='ParryPhotoTint')
edge=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'Parry photo TEMP continuous card edge' in str(n.get_editor_property('description')))
uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
role=LIB.create_material_expression(m,u.MaterialExpressionScalarParameter);role.set_editor_property('parameter_name','ParryHaloRole');role.set_editor_property('default_value',0)
def custom(code,names,typ):
    c=LIB.create_material_expression(m,u.MaterialExpressionCustom);c.set_editor_property('code',code);c.set_editor_property('output_type',typ)
    pins=[]
    for name in names:
        i=u.CustomInput();i.set_editor_property('input_name',name);pins.append(i)
    c.set_editor_property('inputs',pins);return c
def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
shape=custom('float2 p=UV*2-1;float r=length(p);float rim=1-smoothstep(.82,1,r);float ring=exp(-pow((r-.72)/.16,2));float core=exp(-5*r*r);return lerp(core,ring,saturate(Role))*rim;',['UV','Role'],u.CustomMaterialOutputType.CMOT_FLOAT1)
shape.set_editor_property('description','Assistant TEMP photo halo reconstruction; analytic circular alpha makes all card corners zero; original 250cm circle extent retained')
link(uv,'',shape,'UV');link(role,'',shape,'Role')
alpha=custom('return saturate(Alpha)*Shape*Edge;',['Alpha','Shape','Edge'],u.CustomMaterialOutputType.CMOT_FLOAT1)
link(pc,'A',alpha,'Alpha');link(shape,'',alpha,'Shape');link(edge,'',alpha,'Edge');assert LIB.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
color=custom('return Shape*max(Color.r,max(Color.g,Color.b))*Tint;',['Shape','Color','Tint'],u.CustomMaterialOutputType.CMOT_FLOAT3)
link(shape,'',color,'Shape');link(pc,'RGB',color,'Color');link(tint,'',color,'Tint');assert LIB.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
for n in nodes:
    if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('code')).startswith(('return normalize(float3','return 1.0+Strength')):link(alpha,'',n,'Mask')
assert not list(LIB.recompile_material(m));assert EAL.save_loaded_asset(m,only_if_is_dirty=False)
outer_path=BASE+'/MI_Parry_PurpleHalo'
outer=EAL.duplicate_asset(BASE+'/MI_FMI_fluid_A_13',outer_path);assert outer
LIB.set_material_instance_scalar_parameter_value(outer,'ParryHaloRole',1)
LIB.set_material_instance_vector_parameter_value(outer,'ParryPhotoTint',u.LinearColor(1.1,.1,2.6,1))
assert EAL.save_loaded_asset(outer,only_if_is_dirty=False)
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("'bEnabled':'FBoolProperty'","'bEnabled':'FBoolProperty','Material':'FObjectPropertyBase'")
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);text=H['export'](ps,'Before.t3d')
block=next(x.group(0) for x in re.finditer(r'^      Begin Object Name="([^\"]+)" .*?^      End Object',text,re.M|re.S) if 'ParticleSpriteEmitter_13.ParticleLODLevel' in x.group(0)[:500])
ref=re.search(r'RequiredModule="[^\x27]+\x27([^\x27]+)\x27"',block).group(1)
req=u.load_object(None,ref if ref.startswith('/') else ps.get_path_name()+':'+ref.split(':')[-1]);assert req
H['set_owned'](req,'Material',H['token'](outer));H['rebuild'](ps);assert EAL.save_loaded_asset(ps,only_if_is_dirty=False)
for name in ['M_FM_Subuv_Atlas_B','M_Base_SubUV']:
    p=u.load_asset(BASE+'/'+name);p.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    assert not list(LIB.recompile_material(p));assert EAL.save_loaded_asset(p,only_if_is_dirty=False)
for name in ['MI_FMI_Subuv_Atlas_B_01','MI_FM_Subuv_Lightning_Spark_002']:
    mi=u.load_asset(BASE+'/'+name);o=mi.get_editor_property('base_property_overrides');o.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);mi.set_editor_property('base_property_overrides',o)
    assert EAL.save_loaded_asset(mi,only_if_is_dirty=False)
(OUT/'Halo.json').write_text(json.dumps({'status':'passed','source_circle_extent_cm':250,'circle_extent_source':'PP_AtkEx_Parry ParticleSpriteEmitter_2/13 ParticleModuleSize.StartSize.X=250','temporary_ring_radius_uv':.72,'temporary_ring_width_uv':.16,'temporary_edge_radius_uv':.82,'original_additive_sparks_restored':True},indent=2),encoding='utf-8')
