"""Bind the manually reviewed limited floor QA to exact current art candidates."""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
FOLDER = OUT / 'DecalFloorQA_50e7f5e33f71411eb3785da5645f3c47'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
review = json.loads((FOLDER / 'FloorVisualReview.json').read_text(encoding='utf-8'))
raw = json.loads((FOLDER / 'DecalFloorPreview.json').read_text(encoding='utf-8'))
art = json.loads((OUT / 'ResourceAudit/ArtCandidateManifest.json').read_text(encoding='utf-8'))
assert review['status'] == 'passed_limited_visual_QA' and raw['status'] == 'passed'
assert review['actual_floor_visible'] and review['opaque_ribbon_rectangle_removed']
assert review['blood_decal_mask_visible'] and review['crack_mask_visible'] and not review['opaque_decal_quad_visible']
assert art['status'] == 'passed_private_art_QA'
for row in art['rows']:
    assert sha(Path(row['private_file'])) == row['expected_private_sha256']
result = {'status': 'passed', 'visual_review_passed': True,
          'selected_asset_hashes': {r['asset']: r['expected_private_sha256'] for r in art['rows']},
          'review_sha256': sha(FOLDER / 'FloorVisualReview.json'),
          'raw_receipt_sha256': sha(FOLDER / 'DecalFloorPreview.json'),
          'images': {name: sha(FOLDER / name) for name in review['inspected_images']},
          'root_viewed': ['LitBloodTrail_40.png', 'Decal_6_Life0.4.png', 'Decal_5_Life0.4.png', 'Decal_3_Life0.4.png'],
          'boundary': 'Visible textured silhouettes, source tint and transparent gaps only. Blood density/strength and source native opacity-time evaluation remain inferred; no original-game pixel parity claim.'}
(OUT / 'ReviewedFloorProof.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('Bound limited visual QA to', len(result['selected_asset_hashes']), 'exact private candidates')
