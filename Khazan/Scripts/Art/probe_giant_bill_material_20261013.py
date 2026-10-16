"""Read the actual mesh-override contract; never change shared meshes/materials."""
from pathlib import Path
import json, os, unreal as u

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert Path(u.Paths.project_dir()).resolve() in [main,main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan']
out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish'
fx=u.FXConverterUtilitiesLibrary
ps=u.load_asset(root+'/Particles/KZ_FP_Boss_Yetuga_CloseGrab_Smash_01_dd34695f')
rows=[]
for i,e in enumerate(fx.get_cascade_system_emitters(ps)):
    for li in range(len(ps.get_editor_property('lod_distances'))):
        lod=fx.get_cascade_emitter_lod_level(e,li)
        typ=fx.get_lod_level_type_data_module(lod)
        if not isinstance(typ,u.ParticleModuleTypeDataMesh):continue
        mesh=typ.get_editor_property('mesh')
        if not mesh or mesh.get_name()!='FS_bill':continue
        req=fx.get_lod_level_required_module(lod)
        mat=req.get_editor_property('material')
        rows.append(dict(emitter=i,lod=li,type_data=typ.get_path_name(),override_material=typ.get_editor_property('override_material'),required_material=mat.get_path_name(),mesh_materials=[x.material_interface.get_path_name() if x.material_interface else None for x in mesh.get_editor_property('static_materials')]))
assert rows
materials=[]
for path in u.EditorAssetLibrary.list_assets(root+'/Materials',recursive=True):
    m=u.load_asset(path)
    if not isinstance(m,u.MaterialInstanceConstant) or not m.get_name().startswith('KZ_FMI_MashRefractionShock_01_DepthFade_'):continue
    parent=m.get_editor_property('parent')
    materials.append(dict(path=path,parent=parent.get_path_name(),overrides=m.get_editor_property('base_property_overrides').export_text(),parent_blend=str(parent.get_editor_property('blend_mode'))))
(out/'BillMaterialProbe.json').write_text(json.dumps({'rows':rows,'materials':materials,'asset_saves':0},indent=2),encoding='utf-8')
