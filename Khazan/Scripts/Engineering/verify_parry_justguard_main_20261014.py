"""Read saved Main binding, then run the actual 17-case HeinMach parry test."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
paths = {
    'guard': '/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard',
    'effect': '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_JustGuard_Halo',
    'material': '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/M_Parry_JustGuardFlare',
}
assets = {key: u.load_asset(path) for key, path in paths.items()}
assert all(assets.values())
cdo = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(assets['guard'].get_path_name()))
assert cdo.get_editor_property('ParryImpactEffect') == assets['effect']
assert cdo.get_editor_property('ParryCameraShake')
assert cdo.get_editor_property('ParryScreenDistortion')
assert u.MaterialEditingLibrary.get_statistics(assets['material']).num_pixel_shader_instructions > 0
report = {'status': 'saved_readback_passed', 'assets': {}, 'asset_saves': False}
for key, path in paths.items():
    file = ROOT / ('Content/' + path.removeprefix('/Game/') + '.uasset')
    report['assets'][key] = {'path': path, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
report['guard_camera_shake'] = cdo.get_editor_property('ParryCameraShake').get_path_name()
report['guard_screen_distortion'] = cdo.get_editor_property('ParryScreenDistortion').get_path_name()
(OUT/'SavedReadback.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
driver = ROOT/'Scripts/Engineering/parry_photo_validation_driver_20261013.py'
exec(compile(driver.read_text(encoding='utf-8'), str(driver), 'exec'), globals())
