"""Promote the readback-verified audio-only combo asset into Main."""

import hashlib
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset"
PREPARED = ROOT / "Saved/ImportReports/GameplayAudio_20261011/PlayerImpactReview_20261013/Prepared/Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset"
BACKUP = Path(__file__).resolve().parent / "Before/Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset"
TEMP = MAIN.with_name(MAIN.name + ".MainApplyTmp")
BEFORE_SHA = "0dbdfd3f8b97ca0aba6a6f530d0ea9e26fbcddd238fb99164b09280a3e6493df"
PREPARED_SHA = "6835a1677640ece0f64fa5dd4f5704fb1bd4c25fb2e53489b580158268edcad7"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


assert MAIN.resolve().is_relative_to(ROOT)
assert PREPARED.resolve().is_relative_to(ROOT)
assert BACKUP.resolve().is_relative_to(ROOT)
assert TEMP.resolve().is_relative_to(ROOT)
assert sha(MAIN) == BEFORE_SHA, "Main asset changed; merge instead of replacing"
assert sha(PREPARED) == PREPARED_SHA, "Prepared asset changed"
assert not BACKUP.exists(), "Backup already exists"
assert not TEMP.exists(), "Temporary file already exists"

BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, BACKUP)
assert sha(BACKUP) == BEFORE_SHA

try:
    shutil.copy2(PREPARED, TEMP)
    assert sha(TEMP) == PREPARED_SHA
    os.replace(TEMP, MAIN)
finally:
    TEMP.unlink(missing_ok=True)

assert sha(MAIN) == PREPARED_SHA
print(json.dumps({"main_sha256": sha(MAIN), "backup_sha256": sha(BACKUP), "backup": str(BACKUP)}))
