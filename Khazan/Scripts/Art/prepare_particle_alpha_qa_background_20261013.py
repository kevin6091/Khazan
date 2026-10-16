from pathlib import Path
import os,unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']);PROJECT=Path(u.Paths.project_dir()).resolve()
assert PROJECT==MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
path='/Game/__ParticleAlphaQA/M_AlphaDiagnosticSavedBg'
mat=u.load_asset(path)
if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[-1],path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
u.MaterialEditingLibrary.delete_all_material_expressions(mat);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
n=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant3Vector,0,0);n.set_editor_property('constant',u.LinearColor(.12,.12,.12,1))
assert u.MaterialEditingLibrary.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert not list(u.MaterialEditingLibrary.recompile_material(mat));assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
print('QA_ONLY_BACKGROUND_SAVED; excluded from Main delivery')
