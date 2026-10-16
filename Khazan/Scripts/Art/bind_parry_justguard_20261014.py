"""Bind the reviewed source-derived JustGuard halo on the existing Guard GA."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
GUARD = '/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'
EFFECT = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_JustGuard_Halo'
FILE = ROOT / ('Content/' + GUARD.removeprefix('/Game/') + '.uasset')
EXPECTED_SHA = '68c42789e10fe06654b4fb13e5a5e1a9a8ab6d2feb358159b80efe73793c2271'
report = {'status': 'running', 'guard': GUARD, 'effect': EFFECT}

try:
    before_sha = hashlib.sha256(FILE.read_bytes()).hexdigest()
    assert before_sha == EXPECTED_SHA, ('Guard GA changed since reviewed in-memory test', before_sha)
    shutil.copy2(FILE, OUT/'GA_Player_Guard_Before.uasset')
    guard = u.load_asset(GUARD)
    effect = u.load_asset(EFFECT)
    assert guard and effect
    cdo = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(guard.get_path_name()))
    before = cdo.get_editor_property('ParryImpactEffect')
    assert before and 'PP_Player_Parry_Reference' in before.get_path_name(), before
    shake = cdo.get_editor_property('ParryCameraShake')
    distortion = cdo.get_editor_property('ParryScreenDistortion')
    assert shake and distortion
    cdo.set_editor_property('ParryImpactEffect', effect)
    u.BlueprintEditorLibrary.compile_blueprint(guard)
    assert u.EditorAssetLibrary.save_loaded_asset(guard, only_if_is_dirty=False)
    assert cdo.get_editor_property('ParryImpactEffect') == effect
    assert cdo.get_editor_property('ParryCameraShake') == shake
    assert cdo.get_editor_property('ParryScreenDistortion') == distortion
    report.update(status='saved', before_sha256=before_sha,
                  after_sha256=hashlib.sha256(FILE.read_bytes()).hexdigest(),
                  before_effect=before.get_path_name(),
                  after_effect=effect.get_path_name(),
                  camera_shake=shake.get_path_name(),
                  screen_distortion=distortion.get_path_name())
except Exception as exc:
    report.update(status='failed', error=repr(exc))
    raise
finally:
    (OUT/'GuardBinding.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
