"""Restore the original compact impact glow, keeping travelling sparks disabled."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
PATH = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_JustGuard_Halo'
FILE = ROOT / ('Content/' + PATH.removeprefix('/Game/') + '.uasset')
particle = u.load_asset(PATH)
assert particle
before = hashlib.sha256(FILE.read_bytes()).hexdigest()
shutil.copy2(FILE, OUT/'JustGuardHaloBeforeCenter.uasset')
H = {}
helper = (ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(helper, 'cascade_helpers', 'exec'), H)
H['DEST'] = PATH
H['OUT'] = OUT
center = u.load_object(None, particle.get_path_name()+':ParticleSpriteEmitter_11.ParticleLODLevel_0')
assert center
H['set_owned'](center, 'bEnabled', 'True')
H['rebuild'](particle)
u.EditorAssetLibrary.set_metadata_tag(particle, 'KZParryEmitterPolicy',
    'Source-derived: flare_circle2, refrac, light and flare_line_center_glow active; spark_par_collision, spark_par_sphere, emitter1 and outward flare_line_glow disabled per user. Original module timing, size and colour preserved.')
assert u.EditorAssetLibrary.save_loaded_asset(particle, only_if_is_dirty=False)
(OUT/'CenterGlow.json').write_text(json.dumps({
    'status': 'saved', 'before_sha256': before,
    'after_sha256': hashlib.sha256(FILE.read_bytes()).hexdigest(),
    'enabled_original_emitter': 'ParticleSpriteEmitter_11/flare_line_center_glow',
    'source_package': 'BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Attack/PP_AtkEx_JustGuard'
}, indent=2), encoding='utf-8')
