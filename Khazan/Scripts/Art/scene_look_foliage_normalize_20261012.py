"""Keep neutral native PBR; stock foliage-transmission trial was visually rejected."""
from pathlib import Path
import json,os,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_LOOK_MAIN']);OUT=Path(os.environ['KZ_LOOK_OUT']);assert ROOT!=MAIN
BASE=MAIN/'Metadata/SceneLook_20261012';lib=unreal.MaterialEditingLibrary;assets=unreal.EditorAssetLibrary
before=json.loads((BASE/'MainBeforeParameters01/SavedAudit.json').read_text())['materials']
rows=json.loads((BASE/'FoliageFinish03/FoliageFinish.json').read_text())['leaf_changes']
report={'success':False,'saved':[],'leaf_changes':[],'transmission_trial_reverted':True}
root=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/SceneLook/M_HM_PBR_Masked');assert root
lib.disconnect_material_property(root,unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
assert not lib.recompile_material(root)
assert assets.save_loaded_asset(root,False);report['saved'].append(root.get_path_name().split('.')[0])
for row in rows:
    m=unreal.load_asset(row['material']);assert m
    overrides=m.get_editor_property('base_property_overrides')
    overrides.import_text(before[row['material']]['overrides'])
    m.set_editor_property('base_property_overrides',overrides)
    lib.update_material_instance(m)
    assert lib.get_material_instance_scalar_parameter_value(m,'UseEmissiveColorTexture')==0.0
    assert assets.save_loaded_asset(m,False);report['saved'].append(m.get_path_name().split('.')[0])
    report['leaf_changes'].append({'material':row['material'],'source_two_sided_foliage':row['source_value'],
        'native_final':'Existing DefaultLit; source model documented, stock transmission trial rejected',
        'TEMP_raw_emission_after':0.0,'original_base_overrides_restored':True})
report['success']=True
(OUT/'FoliageNormalize.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
