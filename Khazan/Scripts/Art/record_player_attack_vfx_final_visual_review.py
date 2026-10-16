"""Bind root's limited actual attack review and unchanged lit-floor evidence."""
from pathlib import Path
import hashlib
import json

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
review_path = OUT / 'RuntimePIE/RootVisualReview.json'
review = read(review_path)
driver = read(OUT / 'RuntimePIE/Driver.json')
floor_path = OUT / 'ReviewedFloorProof.json'
floor = read(floor_path)
art_path = OUT / 'ResourceAudit/ArtCandidateManifest.json'
art = read(art_path)
assert review['status'] == 'passed_limited_actual_attack_visual_review'
assert review['checkerboard_default_material_absent'] and review['opaque_ribbon_quad_absent']
assert review['original_game_pixel_parity_verified'] is False
assert driver['status'] == 'passed' and driver['material_compile_failures'] == []
assert 'Success' in driver['native_completion']
assert read(OUT / 'RuntimePIE/Exit.json')['exit_code'] == 0
assert floor['status'] == 'passed' and floor['visual_review_passed'] is True
selected = {r['asset']: r['expected_private_sha256'] for r in art['rows']}
assert len(selected) == art['candidate_count'] == 15
for row in art['rows']:
    assert sha(Path(row['private_file'])) == row['expected_private_sha256']
floor_assets = {asset for asset in floor['selected_asset_hashes'] if any(name in asset for name in
    ('FM_blood_trail', 'Base_Blood_Decal', 'Base_Decal_BottomCrack', '/Decal/', '/PhysicsDecal/'))}
assert len(floor_assets) == 8
for asset in floor_assets:
    assert selected[asset] == floor['selected_asset_hashes'][asset], 'Do not reuse floor evidence after a floor material change'
capture_names = {Path(r['image']).name for r in driver['captures']}
images = {}
for row in review['inspected_images']:
    name = row['file']
    assert Path(name).name == name and name in capture_names
    images[name] = sha(OUT / 'RuntimePIE' / name)
assert all(any(kind in name for name in images) for kind in
    ('WeakAttack', 'StrongAttack', 'SpinningAttack', 'OverFury', 'BrutalFront', 'BrutalBack'))
result = dict(status='passed', visual_review_passed=True, selected_asset_hashes=selected,
    review_sha256=sha(review_path), attack_driver_sha256=sha(OUT / 'RuntimePIE/Driver.json'),
    attack_log_sha256=sha(OUT / 'RuntimePIE/PrivatePIE.log'),
    reviewed_actual_attack_images=images, reused_floor_proof_sha256=sha(floor_path),
    unchanged_floor_assets=sorted(floor_assets), floor_images=floor['images'],
    original_game_pixel_parity_verified=False,
    boundary='Limited actual in-project attack silhouettes/transparency and zero SM6 fallback, plus unchanged lit-floor masks. Authored timings/fields are source based; cooked shader graph/native condition reconstruction and original-game pixel parity remain unverified.')
(OUT / 'ReviewedAttackAndFloorProof.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
art['status'] = 'passed_private_art_QA'
art['actual_attack_review_sha256'] = sha(review_path)
art['reviewed_attack_and_floor_proof_sha256'] = sha(OUT / 'ReviewedAttackAndFloorProof.json')
art_path.write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding='utf-8')
print('Bound actual attack and unchanged floor review to', len(selected), 'exact art candidates')
