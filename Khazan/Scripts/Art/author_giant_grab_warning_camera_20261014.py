"""Keep the recovered grab UI readable in front of each giant's live chest socket."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import shutil
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014"
PLAN = json.loads((OUT / "WarningPlan.json").read_text(encoding="utf-8"))
PARTICLE = u.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
R = {"success": False, "assets": [], "errors": []}


def is_owned(event):
    state = event.get_editor_property("notify_state_class")
    return bool(isinstance(state, u.KZAnimNotifyState_MonsterVisual)
                and state.get_editor_property("effect")
                and state.get_editor_property("effect").get_editor_property("ParticleTemplate") == PARTICLE)

try:
    assert PARTICLE
    for row in PLAN["windows"]:
        path = row["asset"]
        asset = u.EditorAssetLibrary.load_asset(path)
        file = ROOT / "Content" / (path.removeprefix("/Game/") + ".uasset")
        assert isinstance(asset, u.AnimSequence) and file.is_file()
        events = list(u.AnimationLibrary.get_animation_notify_events(asset))
        owned = [e for e in events if is_owned(e)]
        assert len(owned) == 1, (path, len(owned))
        effect = owned[0].get_editor_property("notify_state_class").get_editor_property("effect")
        assert str(effect.get_editor_property("SourceSocket")) == "UI_Chest"
        assert effect.get_editor_property("bAttached")
        before = hashlib.sha256(file.read_bytes()).hexdigest()
        if effect.get_editor_property("bFaceCameraOutsideMeshBounds") and effect.get_editor_property("OnNotifyEndDeattach"):
            R["assets"].append({"asset": path, "status": "already_authored", "sha256": before})
            continue
        backup = OUT / "BeforeCameraFacing" / before[:12] / file.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(file, backup)
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == before
        unrelated = Counter(e.export_text() for e in events if not is_owned(e))
        effect.set_editor_property("bFaceCameraOutsideMeshBounds", True)
        effect.set_editor_property("OnNotifyEndDeattach", True)
        assert Counter(e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(asset) if not is_owned(e)) == unrelated
        assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
        R["assets"].append({"asset": path, "status": "camera_facing_authored", "before_sha256": before,
                            "after_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                            "unrelated_notifies_preserved": True})
    R["success"] = True
except Exception:
    R["errors"].append(traceback.format_exc())
    u.log_error(R["errors"][-1])
finally:
    (OUT / "CameraFacingAuthorReport.json").write_text(json.dumps(R, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if not R["success"]:
    raise RuntimeError("Grab warning camera-facing authoring failed")
