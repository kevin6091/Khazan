"""Bind the local radial blur to the existing Main Guard ability only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

root = Path(__file__).resolve().parents[2]
out = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
base = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
guard_path = '/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'
guard_file = root / 'Content/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.uasset'
before = hashlib.sha256(guard_file.read_bytes()).hexdigest()
assert before == '4aafc68f3279daeeba50010a6a85ec9126222c8b6727b2fb17a1b72f0520e8c4', before
shutil.copy2(guard_file, out / 'GA_Player_Guard_Before.uasset')
material = u.load_asset(base + '/M_Parry_ScreenRadialBlur')
guard = u.load_asset(guard_path)
assert material and guard
cls = u.EditorAssetLibrary.load_blueprint_class(guard_path)
defaults = u.get_default_object(cls)
assert defaults.get_editor_property('ParryImpactEffect').get_path_name().endswith('/PP_Player_Parry_Reference.PP_Player_Parry_Reference')
assert defaults.get_editor_property('ParryCameraShake')
defaults.set_editor_property('ParryScreenDistortion', material)
u.BlueprintEditorLibrary.compile_blueprint(guard)
assert u.EditorAssetLibrary.save_loaded_asset(guard, only_if_is_dirty=False)
defaults = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(guard_path))
report = {
    'status': 'saved', 'guard_before_sha256': before,
    'guard_after_sha256': hashlib.sha256(guard_file.read_bytes()).hexdigest(),
    'screen_material': defaults.get_editor_property('ParryScreenDistortion').get_path_name(),
    'impact': defaults.get_editor_property('ParryImpactEffect').get_path_name(),
    'camera': str(defaults.get_editor_property('ParryCameraShake')),
    'camera_feedback_scale_temporary': defaults.get_editor_property('ParryCameraFeedbackScale'),
    'screen_lifetime_source_calculated_seconds': defaults.get_editor_property('ParryScreenDistortionLifetimeSeconds'),
}
(out / 'Binding.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
