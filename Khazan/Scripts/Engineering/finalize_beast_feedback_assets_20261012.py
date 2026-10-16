"""Apply visually reviewed presentation scales; no source VFX package is changed."""
import json
import os
from pathlib import Path
import unreal

work=Path(unreal.Paths.project_dir()).resolve()
assert 'Khazan_BeastDodgeWork_20261012' in str(work)
paths=[]
registry=unreal.AssetRegistryHelpers.get_asset_registry()
for data in registry.get_assets_by_path('/Game/Bluprints/AbilitySystem/Abilities/Player/Dodge',recursive=True):
    if str(data.asset_class_path.asset_name)!='Blueprint':continue
    bp=data.get_asset();defaults=unreal.get_default_object(unreal.load_class(None,bp.get_path_name()+'_C'))
    if not isinstance(defaults,unreal.KZDodgeAbility):continue
    defaults.set_editor_property('dodge_effect_scale',.12)
    defaults.set_editor_property('success_effect_scale',.15)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
    paths.append(bp.get_path_name())
assert len(paths)==8
report={'status':'saved','dodge_scale':.12,'success_scale':.15,'source_status':'Assistant TEMP presentation tuning, reduced after rendered review to keep the character readable','saved':paths}
(Path(os.environ['KZ_BEAST_OUT'])/'FeedbackScale.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
