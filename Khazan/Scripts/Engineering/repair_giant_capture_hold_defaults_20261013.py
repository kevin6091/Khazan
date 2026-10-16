"""Save the source stationary hold key on the four grab Ability defaults."""
from pathlib import Path
import json
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / "Metadata/GiantGrabs_20261013/HoldDefaultsRepair.json"
report = {"saved": [], "errors": []}
try:
    for family, skill in (("ApesStoneHandElite", "Dodge_A"),
                          ("ApesStoneHandElite", "Level_DashAtk_New"),
                          ("Yetuga", "CloseGrab"), ("Yetuga", "RushGrab")):
        path = f"/Game/Monsters/{family}/Abilities/GA_Original_{skill}"
        bp = unreal.load_asset(path)
        assert bp
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        cls = unreal.load_class(None, bp.get_path_name() + "_C")
        obj = unreal.get_default_object(cls)
        # Recovered source: 40 evaluated frames at 30 fps; body motion continues
        # beyond root frame 10, so pause on the final evaluated frame 39.
        obj.set_editor_property("victim_capture_hold_time_seconds", 39.0 / 30.0)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
        report["saved"].append(path)
except Exception:
    report["errors"].append(traceback.format_exc())
finally:
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_HOLD_DEFAULTS " + json.dumps(report, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
