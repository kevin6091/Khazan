"""Preserve concurrently authored attack VFX while applying the same clock conversion."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parents[2];O=P/'Metadata/AnimationTimingKnockback_20261012';W=P.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
assert not (O/'AssetMergeBaseline.json').exists()
def read(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
conflicts=read('DeliveryPreflight.json')['conflicts'];plan=read('Plan.json');by={s['asset']:s for s in plan['sequences']};rows=[];files={}
for c in conflicts:
 r=c['file'];assert r.startswith('Content/') and r.endswith('.uasset')
 asset='/Game/'+r.removeprefix('Content/').removesuffix('.uasset');assert asset in by
 files[r]=hashlib.sha256((P/r).read_bytes()).hexdigest();assert files[r]==c['current']
 for prefix,root in [('MainBeforeAssetMerge',P),('PrivateBeforeAssetMerge',W)]:
  d=O/prefix/r;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/r,d)
 shutil.copyfile(P/r,W/r);rows.append(by[asset])
(O/'MergePlan.json').write_text(json.dumps(dict(plan,sequences=rows,montages=[]),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'AssetMergeBaseline.json').write_text(json.dumps({'files':files,'preserved':'Concurrent ARCH-95 approved Niagara attack effects / new notify children. No earlier asset rollback.'},indent=2)+'\n',encoding='utf-8')
print('LATEST_MAIN_ANIMATION_MERGE_STAGED',len(rows))
