"""Native world-space volume support also masks CPU/GPU card boundaries."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials';lib=u.MaterialEditingLibrary;report=[]
for name in ['M_KZGiant_SoftSnowMist','M_KZGiant_SoftPowder']:
    m=u.load_asset(root+'/'+name);nodes=list(lib.get_material_expressions(m));assert not any(isinstance(n,u.MaterialExpressionSphericalParticleOpacity) for n in nodes)
    alpha=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom))
    sphere=lib.create_material_expression(m,u.MaterialExpressionSphericalParticleOpacity)
    density=lib.create_material_expression(m,u.MaterialExpressionScalarParameter);density.set_editor_property('parameter_name','VolumeDensity');density.set_editor_property('default_value',1)
    assert lib.connect_material_expressions(density,'',sphere,'Density')
    inputs=list(alpha.get_editor_property('inputs'));i=u.CustomInput();i.set_editor_property('input_name','VolumeSupport');inputs.append(i);alpha.set_editor_property('inputs',inputs)
    code=alpha.get_editor_property('code');assert code.endswith(';');alpha.set_editor_property('code',code[:-1]+'*saturate(VolumeSupport);')
    assert lib.connect_material_expressions(sphere,'',alpha,'VolumeSupport')
    alpha.set_editor_property('description','TEMP: source density/alpha with atlas support and native spherical extinction. VolumeDensity1 is editable presentation tuning; original shader parity unconfirmed.')
    assert not list(lib.recompile_material(m));assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    report.append({'material':m.get_path_name(),'VolumeDensity':1,'source_status':'TEMP presentation density; native world radius/scene depth use actual particles, not original shader recovery'})
for path in u.EditorAssetLibrary.list_assets(root,recursive=True):
    mi=u.load_asset(path)
    if isinstance(mi,u.MaterialInstanceConstant) and mi.get_editor_property('parent').get_name() in ['M_KZGiant_SoftSnowMist','M_KZGiant_SoftPowder']:
        lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
(out/'SnowVolumeSupport.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
