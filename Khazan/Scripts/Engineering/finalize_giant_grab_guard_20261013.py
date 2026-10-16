"""Apply only the source Armageddon landing bDontJustGuard flag after C++ rebuild."""
from pathlib import Path
import json
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / "Metadata/GiantGrabs_20261013/GuardFinalizer.json"
report = {"project": str(root), "saved": False, "errors": []}
try:
    asset = unreal.load_asset("/Game/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga")
    assert asset
    nodes = list(asset.get_editor_property("nodes"))
    for name in ("Armageddon_Step3", "Armageddon_Step4"):
        matches = [n for n in nodes if str(n.get_editor_property("node_id")) == name]
        assert len(matches) == 1
        windows = list(matches[0].get_editor_property("attack_windows"))
        assert len(windows) == 1 and abs(windows[0].get_editor_property("extent").x - 2000.0) < 0.01
        windows[0].set_editor_property("disallow_perfect_guard", True)
        matches[0].set_editor_property("attack_windows", windows)
    asset.set_editor_property("nodes", nodes)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    report["saved"] = True
except Exception:
    report["errors"].append(traceback.format_exc())
finally:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_GRAB_GUARD_FINALIZER " + json.dumps(report, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
