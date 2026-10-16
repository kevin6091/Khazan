"""Use the project's established camera exposure compensation on owned snow."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials';lib=u.MaterialEditingLibrary;report=[]
for name in ['M_KZGiant_SoftSnowMist','M_KZGiant_SoftPowder']:
    m=u.load_asset(root+'/'+name);nodes=list(lib.get_material_expressions(m));assert not any(isinstance(n,u.MaterialExpressionEyeAdaptationInverse) for n in nodes)
    colour=next(n for n in nodes if isinstance(n,u.MaterialExpressionLinearInterpolate)) if name.endswith('Mist') else next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='SnowTint')
    inv=lib.create_material_expression(m,u.MaterialExpressionEyeAdaptationInverse);names=list(lib.get_material_expression_input_names(inv));u.log('SNOW_EXPOSURE_INPUTS '+str(names))
    one=lib.create_material_expression(m,u.MaterialExpressionConstant);one.set_editor_property('r',1)
    assert lib.connect_material_expressions(colour,'' if name.endswith('Mist') else 'RGB',inv,next(n for n in names if 'Light' in n))
    assert lib.connect_material_expressions(one,'',inv,next(n for n in names if 'Alpha' in n))
    assert lib.connect_material_property(inv,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=list(lib.recompile_material(m));assert not errors,errors
    assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    report.append({'material':m.get_path_name(),'camera_policy':'DefaultEngine.ini physical lighting + EyeAdaptationInverse; Alpha=1 is full engine compensation, not gameplay tuning'})
for path in u.EditorAssetLibrary.list_assets(root,recursive=True):
    mi=u.load_asset(path)
    if isinstance(mi,u.MaterialInstanceConstant) and mi.get_editor_property('parent').get_name() in ['M_KZGiant_SoftSnowMist','M_KZGiant_SoftPowder']:
        lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
(out/'SnowExposureRepair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
