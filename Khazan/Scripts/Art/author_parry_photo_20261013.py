"""Parry-only source particle clone; continuous alpha and neutral edge refraction."""
from pathlib import Path
import hashlib, json, os, re, unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
DEST=BASE+'/PP_Player_Parry_Reference'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
H={}
s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("'bEnabled':'FBoolProperty'", "'bEnabled':'FBoolProperty','Material':'FObjectPropertyBase'")
exec(compile(s,'existing_cascade_serializer','exec'),H);H.update(OUT=OUT,DEST=DEST)
manifest=json.loads((ROOT/'Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json').read_text(encoding='utf-8-sig'))
names=['FMI_fluid_A_162','FMI_fluid_A_15','FMI_fluid_A_12','FMI_fluid_A_11','FMI_fluid_A_13',
       'FMI_SubUV_color_A_16','FMI_Subuv_Atlas_B_01','FM_Subuv_Lightning_Spark_002']
report={'status':'running','source':'/Game/_Art/Effects/Combat/GuardParry/PP_AtkEx_Parry',
        'assets':[],'materials':[],'temporary_shader_tuning':{'edge_uv':.04,'edge_pixels':1.25,
        'refraction_ior_offset':.06,'photo_inner_tint':[2.4,.12,.55],'photo_outer_tint':[1.1,.10,2.6]},
        'original_shader_graph':'stripped; local shader reconstruction, not original pixel parity'}

def pathfile(a):return ROOT/('Content/'+a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
def duplicate(src,dst):
    assert not EAL.does_asset_exist(dst),dst
    a=EAL.duplicate_asset(src,dst);assert a;return a
def node(m,cls,x=0,y=0):return LIB.create_material_expression(m,cls,x,y)
def link(a,out,b,p):assert LIB.connect_material_expressions(a,out,b,p),(a,b,p)
def scalar(m,name,value):
    a=node(m,u.MaterialExpressionScalarParameter);a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',value);return a
def custom(m,code,names):
    a=node(m,u.MaterialExpressionCustom);a.set_editor_property('code',code)
    ins=[]
    for name in names:
        i=u.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
    a.set_editor_property('inputs',ins);return a
def compile_save(a):
    if isinstance(a,u.Material):assert not list(LIB.recompile_material(a))
    assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
    report['assets'].append({'path':a.get_path_name(),'sha256':hashlib.sha256(pathfile(a).read_bytes()).hexdigest()})

try:
    ps=duplicate(report['source'],DEST)
    parents={};materials={}
    for name in names:
        row=next(x for x in manifest if x['name']==name)
        src=u.load_asset(row['destination']);assert src,name
        parent=src.get_editor_property('parent');key=parent.get_path_name()
        if key not in parents:
            m=duplicate(key,BASE+'/M_'+parent.get_name())
            m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
            nodes=list(LIB.get_material_expressions(m))
            uv=node(m,u.MaterialExpressionTextureCoordinate)
            edge=custom(m,'float2 d=min(UV,1-UV); float w=max(Width,max(fwidth(UV.x),fwidth(UV.y))*Pixels); return smoothstep(0,max(w,0.00001),min(d.x,d.y));',['UV','Width','Pixels'])
            edge.set_editor_property('description','Parry photo TEMP continuous card edge; UV .04/min 1.25 pixels')
            link(uv,'',edge,'UV');link(scalar(m,'ParryEdgeFeatherUV',.04),'',edge,'Width');link(scalar(m,'ParryEdgePixels',1.25),'',edge,'Pixels')
            opacity=LIB.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
            opout=LIB.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY)
            if not opacity:opacity=scalar(m,'ParryOpacityFallback',1);opout=''
            bounded=node(m,u.MaterialExpressionSaturate);link(opacity,opout,bounded,'')
            alpha=node(m,u.MaterialExpressionMultiply);link(bounded,'',alpha,'A');link(edge,'',alpha,'B')
            assert LIB.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
            color=LIB.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
            cout=LIB.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
            if color:
                tint=node(m,u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','ParryPhotoTint');tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
                grade=custom(m,'return max(Color.r,max(Color.g,Color.b))*Tint;',['Color','Tint']);grade.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
                grade.set_editor_property('description','Assistant TEMP photo hue; source emission magnitude retained; isolated parry shader')
                link(color,cout,grade,'Color');link(tint,'',grade,'Tint');assert LIB.connect_material_property(grade,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            parents[key]=m
            compile_save(m)
        mi=duplicate(src.get_path_name(),BASE+'/MI_'+name)
        LIB.set_material_instance_parent(mi,parents[key])
        # Only local instances have a photo palette. Source textures/modules remain untouched.
        rgb=(1.1,.10,2.6) if name in ['FMI_fluid_A_13','FMI_SubUV_color_A_16'] else (2.4,.12,.55)
        LIB.set_material_instance_vector_parameter_value(mi,'ParryPhotoTint',u.LinearColor(*rgb,1))
        overrides=mi.get_editor_property('base_property_overrides');overrides.set_editor_property('override_blend_mode',True);overrides.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mi.set_editor_property('base_property_overrides',overrides)
        compile_save(mi);materials[src.get_path_name()]=mi
        report['materials'].append({'source':src.get_path_name(),'local':mi.get_path_name(),'parent':parents[key].get_path_name()})
    text=H['export'](ps,'Particle_Before.t3d')
    replaced=0
    for match in re.finditer(r'^   Begin Object Name="([^\"]+)" .*?^   End Object',text,re.M|re.S):
        block=match.group(0)
        if not match.group(1).startswith('ParticleModuleRequired'):continue
        ref=re.search(r'Material="[^\x27]+\x27([^\x27]+)\x27"',block)
        if ref and ref.group(1) in materials:
            obj=u.load_object(None,ps.get_path_name()+':'+match.group(1));assert obj
            H['set_owned'](obj,'Material',H['token'](materials[ref.group(1)]));replaced+=1
    assert replaced>=8,replaced
    H['rebuild'](ps);compile_save(ps)
    H['export'](ps,'Particle_After.t3d');report['rebound_required_modules']=replaced
    EAL.set_metadata_tag(ps,'KZParryPhoto','Original PP_AtkEx_Parry 12-emitter closure; photo hue/alpha shaders are assistant TEMP; not native shader parity')
    assert EAL.save_loaded_asset(ps,only_if_is_dirty=False)
    report['status']='passed'
except Exception as exc:
    report['status']='failed';report['error']=str(exc);raise
finally:
    (OUT/'Author.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
