"""Record the completed human-visible model inspection; no renderer or asset writes."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
root=Path(__file__).resolve().parents[2]/'Metadata/MonsterBloodReference_20261012/MainSnowVisual11'
assert not (root/'VisualReview.json').exists()
files=sorted(root.glob('Blood_*_[0-9][0-9].png'));assert len(files)==24
deaths=sorted(root.glob('DeathAsh_*.png'))+sorted(root.glob('LateDeathAsh_*.png'));assert len(deaths)==12
data={
    'utc':datetime.now(timezone.utc).isoformat(),'status':'passed',
    'blood_frames_reviewed':24,'death_frames_reviewed':12,
    'method':'Both contact sheets reviewed, full-size Swordsman00/SwordShield01/Yetuga01 reviewed, paired early/late death sheet reviewed; compared against Reference.png.',
    'findings':[
        'Wine/red-black body spray remains visible in the bright snow and near-fire shots; broad fluid lobes, fragments and small drops separate and drain.',
        'All six families show blood outside the body facing the attacker; the visible skin basis is the existing capsule approximation.',
        'First-hit Swordsman00 already has an irregular ground stain, without the earlier missing shader/black rectangle fallback.',
        'Native RGB mask variants have jagged streaks and different pooled silhouettes; no rectangular texture background is visible.',
        'Rendered snow side walls are excluded from the ground blood mask, while existing snow depressions and ground lighting are retained.',
        'Paired death images show existing blackening and black ash fragmentation with the world ground stain retained.'
    ],
    'limits':[
        'Visual similarity review, not exact source-game pixel/frame/shader parity.',
        'QA cameras and snow deformation can differ from the supplied original-game combat frame.',
        'Final large fluid sheets use exposure-compensated Unlit shading; ground stains keep receiver lighting.'
    ],
    'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files+deaths}
}
(root/'VisualReview.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('VISUAL_REVIEW_RECORDED',len(files),len(deaths))
