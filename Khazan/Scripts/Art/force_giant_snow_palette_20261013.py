import unreal as u
from pathlib import Path
import os,json
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials';out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary
rows=[]
for path in u.EditorAssetLibrary.list_assets(root,recursive=True):
    m=u.load_asset(path)
    if isinstance(m,u.MaterialInstanceConstant) and m.get_editor_property('parent').get_name()=='M_KZGiant_SoftSnowMist':
        lib.set_material_instance_vector_parameter_value(m,'SnowTint',u.LinearColor(.68,.74,.8,1));lib.set_material_instance_scalar_parameter_value(m,'ParticleTintInfluence',0)
        lib.update_material_instance(m);assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);rows.append(m.get_path_name())
(out/'ExplicitSnowPalette.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
