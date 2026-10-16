"""Install only the reviewed material using hash guards and an atomic file replacement."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Metadata/CombatUI_20261011'
OUT = BASE / 'BrutalAlphaMainDelivery'
OUT.mkdir(exist_ok=True)
author = json.loads((BASE / 'BrutalAlphaStage01/AlphaAuthoring.json').read_text(encoding='utf-8'))
review = json.loads((BASE / 'BrutalAlphaStageRHI01/SavedAlphaRHI.json').read_text(encoding='utf-8'))
assert author['status'] == 'saved' and review['status'] == 'passed'
row = author['files'][0]
target = (ROOT / row['path']).resolve()
source = Path(row['staged_file']).resolve()
assert target == (ROOT / 'Content/UI/Combat/Materials/M_UI_BrutalRing.uasset').resolve()
assert source.is_relative_to(BASE.resolve())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source) == row['after'] == review['sha256']
report = dict(status='PreparedAwaitingMainAssetUnlock', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              asset=author['asset'], before=row['before'], after=row['after'], source=str(source), target=str(target),
              changed_assets=1, runtime_source_changes=0,
              saved_material_RHI='Metadata/CombatUI_20261011/BrutalAlphaStageRHI01/SavedAlphaRHI.json',
              visual_preview='Metadata/CombatUI_20261011/BrutalAlphaPreview01/04_BrutalAvailable_B.png')
try:
    actual = sha(target)
    assert actual in [row['before'], row['after']], 'Concurrent Main material change; preserve it'
    if actual != row['after']:
        # Opening without mutation proves the file is available before preparing the replacement.
        with target.open('r+b'):
            pass
        backup = OUT / 'Before_M_UI_BrutalRing.uasset'
        if not backup.exists():
            shutil.copy2(target, backup)
        assert sha(backup) == row['before']
        pending = (OUT / 'Pending_M_UI_BrutalRing.uasset').resolve()
        assert pending.is_relative_to(OUT.resolve())
        shutil.copy2(source, pending)
        assert sha(pending) == row['after'] and sha(target) == row['before']
        os.replace(pending, target)
    assert sha(target) == row['after']
    report['status'] = 'MainMaterialDeliveredAwaitingFreshVerification'
except PermissionError as error:
    report['error'] = str(error)
except Exception as error:
    report.update(status='failed', error=str(error))
    raise
finally:
    (OUT / 'DeliveryReceipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
