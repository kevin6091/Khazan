"""Target visibly broken fog cards and pink mesh shards in owned systems only."""
from pathlib import Path
import json,os
import unreal as u

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
folder='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials'
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
catalog=json.loads((main/'Metadata/GiantVFX_20261013/ParticleObjectCatalog.json').read_text(encoding='utf-8'))
report={'materials':[],'replaced':[],'temporary_visual_values':{'particle_alpha_bound':1,'cloud_depth_fade_cm':12,'ice_tint':[.24,.48,.65]}}
def material(name):
    assert not u.EditorAssetLibrary.does_asset_exist(folder+'/'+name)
    return tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
def connect(a,ap,b,bp):assert lib.connect_material_expressions(a,ap,b,bp)
cloud=material('M_KZGiant_SoftSnowMist');cloud.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);cloud.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
cloud.set_editor_property('two_sided',True)
pc=lib.create_material_expression(cloud,u.MaterialExpressionParticleColor)
uv=lib.create_material_expression(cloud,u.MaterialExpressionTextureCoordinate)
texture=lib.create_material_expression(cloud,u.MaterialExpressionTextureSampleParameterSubUV)
texture.set_editor_property('parameter_name','Tex_Opa');texture.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/SubUV/T_Smoke03_SubUV_9x9'))
alpha=lib.create_material_expression(cloud,u.MaterialExpressionCustom)
inputs=[]
for name in ['UV','Density','ParticleAlpha']:
    i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
alpha.set_editor_property('inputs',inputs);alpha.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
alpha.set_editor_property('code','float2 p=UV*2.0-1.0; float spatial=pow(saturate(1.0-dot(p,p)),2.0); return spatial*saturate(Density)*saturate(ParticleAlpha);')
alpha.set_editor_property('description','TEMP: bounded particle alpha times source R density and soft card support; avoids unrecovered Opa_Str gain/DP opacity formula.')
connect(uv,'',alpha,'UV');connect(texture,'R',alpha,'Density');connect(pc,'A',alpha,'ParticleAlpha')
fade=lib.create_material_expression(cloud,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',12)
connect(alpha,'',fade,'Opacity');assert lib.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
# Native particle colour supplies the original grey/blue palette; no bloom-only fill.
assert lib.connect_material_property(pc,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
ice=material('M_KZGiant_IceDebris');ice.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);ice.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
tint=lib.create_material_expression(ice,u.MaterialExpressionConstant3Vector);tint.set_editor_property('constant',u.LinearColor(.24,.48,.65,1))
assert lib.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
rough=lib.create_material_expression(ice,u.MaterialExpressionConstant);rough.set_editor_property('r',.35);assert lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
for mat in [cloud,ice]:
    assert not list(lib.recompile_material(mat));assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False);report['materials'].append(mat.get_path_name())
for original,dest in author['particles'].items():
    source=u.load_asset(original);system=u.load_asset(dest)
    for old_path,node in catalog[source.get_name()+'.t3d'].items():
        if not node['class'] or not node['class'].endswith('.ParticleModuleRequired'):continue
        req=u.load_object(None,old_path.replace(source.get_path_name(),system.get_path_name(),1));mat=req.get_editor_property('Material')
        original_mat=next((k for k,v in author['materials'].items() if mat and v==mat.get_path_name()),mat.get_path_name().split('.',1)[0] if mat else '')
        if 'FMI_World_SubUV_color_A_yetuga_' in original_mat:
            name='MI_KZGiant_'+original_mat.rsplit('/',1)[-1]
            mi=u.load_asset(folder+'/'+name)
            if not mi:
                mi=tools.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());lib.set_material_instance_parent(mi,cloud)
                old=u.load_asset(original_mat);tex=lib.get_material_instance_texture_parameter_value(old,'Tex_Opa')
                if tex:lib.set_material_instance_texture_parameter_value(mi,'Tex_Opa',tex)
                lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
            req.set_editor_property('Material',mi);report['replaced'].append({'system':dest,'module':req.get_path_name(),'reason':'RHI full fog card; source mask + bounded alpha rebuilt','material':mi.get_path_name()})
        elif original_mat.endswith('/WM_SKL_Ice_Special_008'):
            req.set_editor_property('Material',ice);report['replaced'].append({'system':dest,'module':req.get_path_name(),'reason':'RHI pink unlit ice polygons; shaded 3D debris','material':ice.get_path_name()})
    assert u.EditorAssetLibrary.save_loaded_asset(system,only_if_is_dirty=False)
(out/'CleanSurfaceMaterials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('GIANT_CLEAN_SURFACE_MATERIALS: '+str(len(report['replaced']))+' target renderers')
