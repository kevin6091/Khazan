"""Keep the original JustGuard halo/refraction/light, removing requested sparks."""

from pathlib import Path
import hashlib
import json
import os
import re
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
SOURCE = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success'
DEST = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_JustGuard_Halo'
ROLES = ROOT / 'Metadata/ParryVFXRebuild_20261013/SourceEmitterRoles.json'
KEEP = {'flare_circle2', 'refrac', 'light'}
EAL = u.EditorAssetLibrary
report = {'status': 'running', 'source': SOURCE, 'destination': DEST, 'emitters': []}

def asset_file(path):
    return ROOT / ('Content/' + path.removeprefix('/Game/') + '.uasset')

try:
    assert not EAL.does_asset_exist(DEST), 'Never overwrite an existing task asset'
    source_file = asset_file(SOURCE)
    report['source_sha256'] = hashlib.sha256(source_file.read_bytes()).hexdigest()
    roles = json.loads(ROLES.read_text(encoding='utf-8'))['PP_AtkEx_JustGuard']['emitters']
    assert len(roles) == 13
    # Existing editor helper uses Unreal's native ImportText for protected Cascade
    # properties and only rebuilds this task-owned duplicate.
    H = {}
    helper = (ROOT / 'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
    exec(compile(helper, 'cascade_helpers', 'exec'), H)
    H['DEST'] = DEST
    H['OUT'] = OUT
    particle = EAL.duplicate_asset(SOURCE, DEST)
    assert particle
    for role in roles:
        name = role['source_emitter']
        emitter = u.load_object(None, particle.get_path_name() + ':' + name)
        assert emitter, name
        lod = u.load_object(None, emitter.get_path_name() + '.ParticleLODLevel_0')
        assert lod, name
        retain = role['enabled'] and role['display_name'] in KEEP
        H['set_owned'](lod, 'bEnabled', 'True' if retain else 'False')
        report['emitters'].append({'source_emitter': name, 'source_name': role['display_name'], 'source_enabled': role['enabled'], 'active_after': retain})
    assert sorted(r['source_name'] for r in report['emitters'] if r['active_after']) == sorted(KEEP)
    H['rebuild'](particle)
    EAL.set_metadata_tag(particle, 'KZSourcePackage',
        'BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Attack/PP_AtkEx_JustGuard')
    EAL.set_metadata_tag(particle, 'KZParryEmitterPolicy',
        'Source-derived. Keep flare_circle2, refrac, light; disable spark and line roles per user request. Source material, distributions, lifetime and alpha unchanged.')
    assert EAL.save_loaded_asset(particle, only_if_is_dirty=False)
    rendered = H['export'](particle, 'JustGuardHaloSaved.t3d')
    assert len(re.findall(r'^   Emitters\(\d+\)=', rendered, re.M)) == 13
    report['destination_sha256'] = hashlib.sha256(asset_file(DEST).read_bytes()).hexdigest()
    report['status'] = 'saved'
except Exception as exc:
    report['status'] = 'failed'
    report['error'] = repr(exc)
    raise
finally:
    (OUT / 'JustGuardHaloAuthor.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
