"""Suppress recovered authoring helpers at every LOD; preserve effect modules."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';lib=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();fx=u.FXConverterUtilitiesLibrary
m=at.create_asset('M_KZGiant_TechnicalHidden',root+'/Materials',u.Material,u.MaterialFactoryNew());assert m
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);m.set_editor_property('two_sided',True)
zero=lib.create_material_expression(m,u.MaterialExpressionConstant);zero.set_editor_property('r',0)
for prop in [u.MaterialProperty.MP_OPACITY,u.MaterialProperty.MP_EMISSIVE_COLOR]:assert lib.connect_material_property(zero,'',prop)
for usage in [u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES,u.MaterialUsage.MATUSAGE_MESH_PARTICLES]:lib.set_material_usage(m,usage)
assert not list(lib.recompile_material(m));assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
report=[]
for path in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True)+u.EditorAssetLibrary.list_assets(root+'/OriginalObjects',recursive=True):
    p=u.load_asset(path)
    if not isinstance(p,u.ParticleSystem):continue
    changed=False
    for e in fx.get_cascade_system_emitters(p):
        for li in range(len(p.get_editor_property('lod_distances'))):
            lod=fx.get_cascade_emitter_lod_level(e,li);req=fx.get_lod_level_required_module(lod);old=req.get_editor_property('material');typ=fx.get_lod_level_type_data_module(lod)
            mesh=typ.get_editor_property('mesh') if isinstance(typ,u.ParticleModuleTypeDataMesh) else None
            if (old and old.get_name()=='Base_Axis') or (mesh and mesh.get_name()=='FS_axis'):
                req.set_editor_property('material',m);changed=True;report.append({'system':path,'lod':lod.get_path_name(),'reason':'source technical axis, opacity0 at every LOD; no relying on transient solo flags'})
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'TechnicalAxisSuppression.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
