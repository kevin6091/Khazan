"""Save native usage permutations on the newly created private materials."""
import unreal as u
from pathlib import Path
import os,json
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/'
rows=[]
for name in ['M_KZGiant_SoftSnowMist','M_KZGiant_IceDebris']:
    m=u.load_asset(root+name);assert m
    for usage in [u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES,u.MaterialUsage.MATUSAGE_MESH_PARTICLES]:
        lib.set_material_usage(m,usage)
    assert not list(lib.recompile_material(m))
    assert m.get_editor_property('used_with_particle_sprites') and m.get_editor_property('used_with_mesh_particles')
    assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    rows.append(m.get_path_name())
for name in ['MI_KZGiant_FMI_World_SubUV_color_A_yetuga_01','MI_KZGiant_FMI_World_SubUV_color_A_yetuga_02','MI_KZGiant_FMI_World_SubUV_color_A_yetuga_03']:
    m=u.load_asset(root+name);lib.update_material_instance(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    rows.append(m.get_path_name())
(out/'Usage.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
exec(compile((main/'Scripts/Art/probe_giant_original_field_renderer_20261013.py').read_text(encoding='utf-8'),'<field renderer>','exec'))
