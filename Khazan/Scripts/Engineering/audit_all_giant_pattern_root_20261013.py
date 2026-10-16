"""Read-only root/track audit of every current Apes and Yetuga pattern clip."""
from pathlib import Path
import json
import runpy
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / "Metadata/GiantGrabs_20261013"
inventory_path = out / "AllPatternClipInventory.json"
audit_path = out / "AllPatternRootAudit.json"
report = {"project": str(root), "read_only": True, "nodes": [], "assets": [], "errors": []}

try:
    for family in ("ApesStoneHandElite", "Yetuga"):
        definition = unreal.load_asset(f"/Game/Monsters/{family}/Data/DA_OriginalPatterns_{family}")
        assert definition, family
        for node in definition.get_editor_property("nodes"):
            montage = node.get_editor_property("montage")
            section = node.get_editor_property("section_name")
            assert montage, (family, str(node.get_editor_property("node_id")))
            index = montage.get_section_index(section)
            assert index >= 0, (family, str(section))
            track = montage.get_editor_property("slot_anim_tracks")[0].get_editor_property("anim_track")
            clip = track.get_editor_property("anim_segments")[index].get_editor_property("anim_reference")
            assert clip and clip.get_class().get_name() == "AnimSequence", (family, str(section))
            report["nodes"].append({
                "family": family,
                "node": str(node.get_editor_property("node_id")),
                "skill": str(node.get_editor_property("pattern_skill")),
                "clip": clip.get_path_name(),
                "blend_seconds": float(node.get_editor_property("pattern_blend_seconds")),
            })
    paths = sorted({row["clip"] for row in report["nodes"]})
    specs = [{"asset": path, "expects_root_motion": False, "motion_bones": ["Root"]} for path in paths]
    runpy.run_path(
        r"C:/Users/user/.codex/skills/unreal-root-motion-repair/scripts/audit_root_motion.py",
        init_globals={"ROOT_MOTION_AUDIT_ASSETS": specs, "ROOT_MOTION_AUDIT_REPORT": str(audit_path)},
        run_name="__main__",
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    report["assets"] = [{"asset": row["asset"], "status": row["status"],
                         "root_motion_enabled": row.get("root_motion_settings", {}).get("enable_root_motion"),
                         "root_track_first": row.get("facts", {}).get("skeleton_root_track_is_first"),
                         "engine_extraction_has_motion": row.get("facts", {}).get("engine_extraction_has_motion"),
                         "findings": row.get("findings", []),
                         "error": row.get("error")}
                        for row in audit["assets"]]
    assert audit["status"] == "passed", audit["status"]
    report["status"] = "passed"
except Exception:
    report["errors"].append(traceback.format_exc())
    report["status"] = "failed"
finally:
    out.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("ALL_GIANT_PATTERN_ROOT_AUDIT " + json.dumps({
        "status": report["status"], "nodes": len(report["nodes"]),
        "assets": len(report["assets"]), "errors": report["errors"]}, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
