"""Read-only CDO comparison after a real grab PIE failure."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / "Metadata/GiantGrabs_20261013/CaptureDefaults.json"
rows = []
for family, skill in (("ApesStoneHandElite", "Dodge_A"),
                      ("ApesStoneHandElite", "Level_DashAtk_New"),
                      ("Yetuga", "CloseGrab"), ("Yetuga", "RushGrab")):
    path = f"/Game/Monsters/{family}/Abilities/GA_Original_{skill}"
    bp = unreal.load_asset(path)
    cls = unreal.load_class(None, bp.get_path_name() + "_C")
    obj = unreal.get_default_object(cls)
    fields = {}
    for name in ("capture_effect", "victim_capture_animation", "victim_capture_blend_seconds",
                 "victim_capture_hold_time_seconds", "combo_definition", "entry_node_id"):
        try:
            value = obj.get_editor_property(name)
            fields[name] = value.get_path_name() if hasattr(value, "get_path_name") else str(value)
        except Exception as exc:
            fields[name] = f"ERROR {exc}"
    rows.append({"family": family, "skill": skill, "fields": fields})
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log("GIANT_CAPTURE_DEFAULTS " + json.dumps(rows, ensure_ascii=False))
unreal.SystemLibrary.quit_editor()
