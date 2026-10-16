"""Repair the remaining snow card family and split Apes stone from Yetuga ice."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish'
lib=u.MaterialEditingLibrary;fx=u.FXConverterUtilitiesLibrary;at=u.AssetToolsHelpers.get_asset_tools()
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
reverse={v:k for k,v in author['materials'].items()}
mist=u.load_asset(root+'/Materials/M_KZGiant_SoftSnowMist');ice=u.load_asset(root+'/Materials/M_KZGiant_IceDebris')
report={'snow_renderers':[],'stone_renderers':[],'temporary_values':{'stone_tint':[.17,.18,.20],'stone_roughness':.8}}
for p in author['particles'].values():
    ps=u.load_asset(p);changed=False
    for emitter in fx.get_cascade_system_emitters(ps):
        lod=fx.get_cascade_emitter_lod_level(emitter,0);typ=fx.get_lod_level_type_data_module(lod)
        if isinstance(typ,u.ParticleModuleTypeDataMesh):continue
        req=fx.get_lod_level_required_module(lod);mat=req.get_editor_property('Material')
        original=reverse.get(mat.get_path_name(),'') if mat else ''
        name=original.rsplit('/',1)[-1]
        if not any(x in name for x in ['FMI_World_SubUV_color_A_','FMI_World_Fluid_A_','FMI_World_fluid_B_']):continue
        path=root+'/Materials/MI_KZGiant_Snow_'+name
        mi=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else at.create_asset('MI_KZGiant_Snow_'+name,root+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi,mist)
        source=u.load_asset(original);texture=lib.get_material_instance_texture_parameter_value(source,'Tex_Opa')
        if texture:lib.set_material_instance_texture_parameter_value(mi,'Tex_Opa',texture)
        lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
        req.set_editor_property('Material',mi);changed=True
        report['snow_renderers'].append({'required':req.get_path_name(),'original_material':original,'density_texture':texture.get_path_name() if texture else 'source shared smoke default','material':mi.get_path_name()})
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
# Stone uses the same source burst/motion timing, but genuine volumetric rock
# fragments rather than the frost horn meshes belonging to Yetuga.
path=root+'/Materials/M_KZGiant_StoneDebris'
assert not u.EditorAssetLibrary.does_asset_exist(path)
stone=at.create_asset('M_KZGiant_StoneDebris',root+'/Materials',u.Material,u.MaterialFactoryNew())
stone.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
tint=lib.create_material_expression(stone,u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','StoneTint');tint.set_editor_property('default_value',u.LinearColor(.17,.18,.20,1))
rough=lib.create_material_expression(stone,u.MaterialExpressionScalarParameter);rough.set_editor_property('parameter_name','StoneRoughness');rough.set_editor_property('default_value',.8)
assert lib.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR);assert lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
lib.set_material_usage(stone,u.MaterialUsage.MATUSAGE_MESH_PARTICLES);assert not list(lib.recompile_material(stone));assert u.EditorAssetLibrary.save_loaded_asset(stone,only_if_is_dirty=False)
source=next(v for k,v in author['particles'].items() if k.endswith('FP_Boss_Yetuga_Rock_Explosion_01.FP_Boss_Yetuga_Rock_Explosion_01'))
assert not u.EditorAssetLibrary.does_asset_exist(root+'/Particles/KZ_Apes_StoneImpact')
ps=at.duplicate_asset('KZ_Apes_StoneImpact',root+'/Particles',u.load_asset(source));mesh=u.load_asset('/Game/_Art/Effects/Shared/Meshes/FS_Rock_01');assert mesh
for emitter in fx.get_cascade_system_emitters(ps):
    lod=fx.get_cascade_emitter_lod_level(emitter,0);typ=fx.get_lod_level_type_data_module(lod)
    if not isinstance(typ,u.ParticleModuleTypeDataMesh):continue
    req=fx.get_lod_level_required_module(lod)
    if req.get_editor_property('Material')==ice:
        typ.set_editor_property('Mesh',mesh);typ.set_editor_property('bOverrideMaterial',True);req.set_editor_property('Material',stone)
        report['stone_renderers'].append({'module':typ.get_path_name(),'mesh':mesh.get_path_name(),'material':stone.get_path_name()})
assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
da=u.load_asset('/Game/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite');objects=list(da.get_editor_property('pattern_objects'))
target=next(x for x in objects if str(x.get_editor_property('Id'))=='COI_ApesStoneHand_E_FastBall_OBJ');target.set_editor_property('ImpactEffect',ps)
da.set_editor_property('pattern_objects',objects);assert u.EditorAssetLibrary.save_loaded_asset(da,only_if_is_dirty=False)
(out/'SnowStoneSurfaces.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('GIANT_SNOW_STONE_SURFACES_COMPLETE: '+str(len(report['snow_renderers'])))
