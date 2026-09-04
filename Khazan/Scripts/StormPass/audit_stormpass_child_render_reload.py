"""Reload-audit all flattened StormPass child render components."""

from __future__ import annotations

import importlib.util
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
RESTORE_SCRIPT = os.path.join(
    SCRIPT_DIR, "restore_stormpass_child_render_meshes.py"
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildRender_ReloadAudit.json",
)
DEV_MAP_PATH = "/Game/Maps/DevMap"


def load_restore():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_child_reload_helpers", RESTORE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass child restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    restore = load_restore()
    restore.configure_shared()
    restore.shared.expected_world_transform = restore.expected_world_transform
    source = restore.shared.load_json(restore.AUDIT_PATH)
    records, packages, expected_labels = restore.accepted_records(source)
    restoration = restore.shared.load_json(restore.REPORT_PATH)
    if restoration.get("status") != "restored":
        raise RuntimeError("StormPass child restoration report is incomplete")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(DEV_MAP_PATH):
        raise RuntimeError("Failed to load neutral map before child reload audit")
    if not level_subsystem.load_level(restore.MAP_PATH):
        raise RuntimeError("Failed to reload StormPass environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    managed = {
        actor.get_actor_label(): actor
        for actor in all_actors
        if actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
    }
    duplicate_count = sum(
        count - 1
        for count in __import__("collections").Counter(
            actor.get_actor_label()
            for actor in all_actors
            if actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
        ).values()
        if count > 1
    )
    missing_labels = sorted(expected_labels - set(managed))
    unexpected_labels = sorted(set(managed) - expected_labels)

    placement_failures = restore.shared.validate_placements(records, managed)
    material_result = restoration.get("material_restoration", {})
    slot_maps = {
        item["mesh_package"]: {
            int(assignment["source_slot"]): int(assignment["ue_slot"])
            for assignment in item.get("assignments", [])
        }
        for item in material_result.get("mesh_slot_mappings", [])
    }
    material_paths = {
        item["package"]: item["material_path"]
        for item in material_result.get("material_resolution", [])
    }
    override_checks = 0
    non_render_references = 0
    material_mismatches = []
    for record in records:
        actor = managed.get(restore.shared.managed_label(record))
        if not actor:
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mapping = slot_maps.get(record["static_mesh_package"], {})
        for source_slot, package in enumerate(
            record.get("override_material_packages", [])
        ):
            if not package:
                continue
            ue_slot = mapping.get(source_slot)
            if ue_slot is None:
                non_render_references += 1
                continue
            override_checks += 1
            expected = material_paths.get(package)
            actual_material = component.get_material(ue_slot) if component else None
            actual = actual_material.get_path_name() if actual_material else None
            if actual != expected:
                material_mismatches.append(
                    {
                        "label": restore.shared.managed_label(record),
                        "source_slot": source_slot,
                        "ue_slot": ue_slot,
                        "package": package,
                        "expected": expected,
                        "actual": actual,
                    }
                )

    fog = restore.shared.fog_signature(actor_subsystem)
    root_actor_count = sum(
        actor.get_actor_label().startswith("SP_Prop_") for actor in all_actors
    )
    report = {
        "status": "passed",
        "map_path": restore.MAP_PATH,
        "reload_cycle": [DEV_MAP_PATH, restore.MAP_PATH],
        "source_component_count": len(records),
        "source_mesh_count": len(packages),
        "managed_actor_count": len(managed),
        "root_actor_count": root_actor_count,
        "duplicate_label_count": duplicate_count,
        "missing_actor_count": len(missing_labels),
        "unexpected_actor_count": len(unexpected_labels),
        "placement_mismatch_count": len(placement_failures),
        "material_override_check_count": override_checks,
        "material_mismatch_count": len(material_mismatches),
        "non_render_lod_or_unused_reference_count": non_render_references,
        "fog_boundary": fog,
        "missing_labels": missing_labels,
        "unexpected_labels": unexpected_labels,
        "placement_failures": placement_failures,
        "material_mismatches": material_mismatches,
    }
    failed = any(
        (
            len(managed) != restore.EXPECTED_COMPONENT_COUNT,
            root_actor_count != 13050,
            duplicate_count,
            missing_labels,
            unexpected_labels,
            placement_failures,
            override_checks != restore.EXPECTED_OVERRIDE_REFERENCE_COUNT,
            material_mismatches,
            non_render_references,
            fog != restore.EXPECTED_FOG_SIGNATURE,
        )
    )
    if failed:
        report["status"] = "failed"
    restore.shared.write_json(REPORT_PATH, report)
    if failed:
        raise RuntimeError("StormPass child reload audit failed: " + REPORT_PATH)
    unreal.log(
        "KHAZAN_STORMPASS_CHILD_RELOAD_AUDIT: RESULT actors={} roots={} "
        "placements={} materials={} fog={} report={}".format(
            len(managed),
            root_actor_count,
            len(placement_failures),
            override_checks,
            fog["count"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    main()
