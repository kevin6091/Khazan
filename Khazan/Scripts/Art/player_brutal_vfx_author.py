"""Use the proven authoring implementation for only two private Brutal montages."""
import hashlib
import json
from pathlib import Path
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
original = read(OUT / 'Authoring/PrivateAuthoring.json')
plan = read(OUT / 'PreparedBrutalPlaybackPlan.json')
allowed = {'/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalFront.AM_DAS_BrutalFront',
           '/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalBack.AM_DAS_BrutalBack'}
assert original['status'] == 'passed' and len(original['montages']) == 6
assert len(plan['events']) == 54 and {e['montage'] for e in plan['events']} == allowed
preserved = {r['relative']: sha(WORK / r['relative']) for r in original['montages']}
assert all(preserved[r['relative']] == r['after_sha256'] for r in original['montages'])
source = MAIN / 'Scripts/Art/player_attack_vfx_author.py'
code = source.read_text(encoding='utf-8-sig')
replacements = {"PlayerAttackVFX_20261008/Authoring'": "PlayerAttackVFX_20261008/BrutalAuthoring'",
                "'PreparedPlaybackPlan.json'": "'PreparedBrutalPlaybackPlan.json'",
                "'WorkBaseline.json'": "'BrutalAssetBaseline.json'"}
for before, after in replacements.items():
    assert code.count(before) == 1
    code = code.replace(before, after)
scope = {'__name__': '__main__', '__file__': str(source)}
exec(compile(code, str(source), 'exec'), scope)
authored = read(OUT / 'BrutalAuthoring/PrivateAuthoring.json')
assert authored['status'] == 'passed' and {r['path'] for r in authored['montages']} == allowed
assert len(authored['events']) == 54
assert all(sha(WORK / rel) == digest for rel, digest in preserved.items())
combined = dict(original)
combined['montages'] = original['montages'] + authored['montages']
combined['events'] = original['events'] + authored['events']
combined['combined_inputs'] = {'original_author_sha256': sha(OUT / 'Authoring/PrivateAuthoring.json'),
    'brutal_author_sha256': sha(OUT / 'BrutalAuthoring/PrivateAuthoring.json'), 'author_helper_sha256': sha(source)}
combined['original_six_package_bytes_unchanged'] = True
combined['before_export_directories'] = {r['path']: 'BrutalAuthoring' if r['path'] in allowed else 'Authoring' for r in combined['montages']}
assert len(combined['montages']) == 8 and len(combined['events']) == 401
(OUT / 'Authoring/CombinedPrivateAuthoring.json').write_text(json.dumps(combined, indent=2), encoding='utf-8')
print('KZ_PLAYER_BRUTAL_VFX_AUTHOR_PASSED', flush=True)
