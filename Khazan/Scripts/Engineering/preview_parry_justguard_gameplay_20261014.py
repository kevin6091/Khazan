"""Actual HeinMach parry with an unsaved GA CDO swap while Main GA is locked."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
GUARD = '/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'
EFFECT = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_JustGuard_Halo'
guard = u.load_asset(GUARD)
effect = u.load_asset(EFFECT)
assert guard and effect
cdo = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(guard.get_path_name()))
before = cdo.get_editor_property('ParryImpactEffect')
assert before and 'PP_Player_Parry_Reference' in before.get_path_name(), before
cdo.set_editor_property('ParryImpactEffect', effect)
assert cdo.get_editor_property('ParryImpactEffect') == effect
material = u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/M_Parry_JustGuardFlare')
assert u.MaterialEditingLibrary.get_statistics(material).num_pixel_shader_instructions > 0
file = ROOT / ('Content/' + GUARD.removeprefix('/Game/') + '.uasset')
(OUT/'UnsavedGuardOverride.json').write_text(json.dumps({
    'guard_file_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    'before': before.get_path_name(), 'unsaved_effect': effect.get_path_name(),
    'asset_saves': False, 'boundary': 'Owned validation process CDO only; Main Guard package remains locked/unchanged.'
}, indent=2), encoding='utf-8')
driver = ROOT / 'Scripts/Engineering/parry_photo_validation_driver_20261013.py'
exec(compile(driver.read_text(encoding='utf-8'), str(driver), 'exec'), globals())
