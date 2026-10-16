"""Local fallback for stripped refraction: additive alpha cannot occlude the scene."""
from pathlib import Path
import json, os, unreal as u
ROOT=Path(u.Paths.project_dir()).resolve(); MAIN=Path(os.environ['KZ_PARRY_MAIN']); OUT=Path(os.environ['KZ_PARRY_OUT'])
assert ROOT==MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan'
rows=[]
for name in ['FMI_fluid_A_133','FMI_fluid_A_11','FMI_fluid_A_13','FMI_fluid_A_15','FMI_Subuv_Atlas_B_01']:
    path='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/'+name
    mi=u.load_asset(path); assert mi
    props=mi.get_editor_property('base_property_overrides');before=props.export_text()
    props.set_editor_property('override_blend_mode',True)
    props.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    mi.set_editor_property('base_property_overrides',props)
    u.MaterialEditingLibrary.update_material_instance(mi)
    u.EditorAssetLibrary.set_metadata_tag(mi,'KZParryRefractionAdapter',
        'TEMP: stripped original shader graphs cannot be recovered exactly; additive continuous alpha prevents black mask/refraction pixels from occluding the scene. Original particle timing, mesh, textures and parameters retained.')
    assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
    rows.append({'path':path,'before':before,'after':mi.get_editor_property('base_property_overrides').export_text()})
(OUT/'RefractionBlend.json').write_text(json.dumps({'status':'passed','materials':rows},indent=2),encoding='utf-8')
