"""Ensure recovered mesh emitters actually consume the authored material."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';fx=u.FXConverterUtilitiesLibrary;report=[]
for path in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True)+u.EditorAssetLibrary.list_assets(root+'/OriginalObjects',recursive=True):
    p=u.load_asset(path)
    if not isinstance(p,u.ParticleSystem):continue
    changed=False
    for e in fx.get_cascade_system_emitters(p):
        for li in range(len(p.get_editor_property('lod_distances'))):
            lod=fx.get_cascade_emitter_lod_level(e,li);typ=fx.get_lod_level_type_data_module(lod)
            if not isinstance(typ,u.ParticleModuleTypeDataMesh):continue
            mat=fx.get_lod_level_required_module(lod).get_editor_property('material')
            if mat and mat.get_path_name().startswith(root+'/Materials/') and not typ.get_editor_property('override_material'):
                typ.set_editor_property('override_material',True);changed=True
                report.append({'system':path,'lod':li,'type_data':typ.get_path_name(),'material':mat.get_path_name(),'reason':'Engine bOverrideMaterial selects Required.Material instead of static-mesh slot material'})
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'MeshMaterialBindingRepair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
