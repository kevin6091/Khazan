"""Reload-safe final audit for the HeinMach HISM foliage transfer."""

import json
import os
import sys
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import restore_heinmach_foliage_batches as restore


AUDIT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Reload_Audit.json",
)


def main():
    transfer_report = restore.load_json(restore.REPORT_PATH)
    if transfer_report.get("status") not in (
        "transferred_pending_reload_validation",
        "restored",
        "validation_failed",
    ):
        raise RuntimeError("Foliage transfer report is not ready for reload audit")
    baseline = restore.load_json(restore.BASELINE_PATH)
    if (
        baseline.get("status") != "baseline_saved"
        or baseline.get("batch_count") != restore.EXPECTED_BATCH_COUNT
        or baseline.get("instance_count") != restore.EXPECTED_INSTANCE_COUNT
    ):
        raise RuntimeError("Foliage transform baseline is incomplete")
    baseline_by_mesh = {
        row["mesh_path"]: {
            "instance_count": int(row["instance_count"]),
            "instance_transform_digest": row["instance_transform_digest"],
            "instance_world_transforms": row["instance_world_transforms"],
        }
        for row in baseline["batches"]
    }
    if len(baseline_by_mesh) != restore.EXPECTED_BATCH_COUNT:
        raise RuntimeError("Foliage transform baseline is not one-to-one")

    import_report = restore.load_json(restore.IMPORT_REPORT_PATH)
    source_meshes = restore.corrected_source_mesh_index()
    mappings, prototype_vertex_counts, _requirements = restore.build_mappings(
        import_report, source_meshes
    )
    material_results = restore.repair_assigned_materials(mappings)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_path = current_world.get_path_name().split(".")[0] if current_world else None
    if current_path != restore.MAP_PATH:
        if not level_subsystem.load_level(restore.MAP_PATH):
            raise RuntimeError("Failed to load foliage-restored HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    validation = restore.validate_main_map(
        actor_subsystem, mappings, baseline_by_mesh
    )

    status = "restored"
    if (
        len(validation["index"]) != restore.EXPECTED_BATCH_COUNT
        or validation["total_instance_count"] != restore.EXPECTED_INSTANCE_COUNT
        or validation["mesh_mismatches"]
        or validation["instance_count_mismatches"]
        or validation["instance_transform_mismatches"]
        or validation["actor_transform_mismatches"]
        or validation["material_mismatches"]
        or any(not row["matches"] for row in material_results)
        or any(len(values) != 1 for values in prototype_vertex_counts.values())
    ):
        status = "validation_failed"

    final_report = dict(transfer_report)
    final_report.update(
        {
            "status": status,
            "reload_audit_path": AUDIT_PATH,
            "final_batch_actor_count": len(validation["index"]),
            "final_instance_count": validation["total_instance_count"],
            "final_actor_count": len(validation["actors"]),
            "global_actor_count_policy": (
                "Informational only; later root, Landscape and preview-light "
                "passes are validated by their dedicated audits"
            ),
            "material_surface_validation_count": len(material_results),
            "material_surface_mismatch_count": sum(
                not row["matches"] for row in material_results
            ),
            "mesh_mismatches": validation["mesh_mismatches"],
            "instance_count_mismatches": validation[
                "instance_count_mismatches"
            ],
            "instance_transform_mismatches": validation[
                "instance_transform_mismatches"
            ],
            "actor_transform_mismatches": validation[
                "actor_transform_mismatches"
            ],
            "material_mismatches": validation["material_mismatches"],
            "material_surface_validation": material_results,
            "batches": validation["batches"],
        }
    )
    restore.write_json(restore.REPORT_PATH, final_report)
    restore.write_json(AUDIT_PATH, final_report)
    if status == "restored":
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save audited HeinMach main map")
    unreal.log(
        "KHAZAN_HEINMACH_FOLIAGE_AUDIT: status={} batches={} instances={} "
        "actors={} report={}".format(
            status,
            final_report["final_batch_actor_count"],
            final_report["final_instance_count"],
            final_report["final_actor_count"],
            AUDIT_PATH,
        )
    )
    if status != "restored":
        raise RuntimeError("Foliage reload audit failed; see " + AUDIT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        existing = {}
        if os.path.isfile(AUDIT_PATH):
            try:
                existing = restore.load_json(AUDIT_PATH)
            except Exception:
                existing = {}
        if existing.get("status") == "validation_failed":
            existing["terminal_error"] = str(exception)
            existing["terminal_traceback"] = traceback.format_exc()
            restore.write_json(AUDIT_PATH, existing)
        else:
            restore.write_json(
                AUDIT_PATH,
                {
                    "status": "failed",
                    "error": str(exception),
                    "traceback": traceback.format_exc(),
                },
            )
        unreal.log_error("KHAZAN_HEINMACH_FOLIAGE_AUDIT: " + str(exception))
        raise
