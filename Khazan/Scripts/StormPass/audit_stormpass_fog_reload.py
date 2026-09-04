"""Leave/reload StormPass and audit all 53 saved Fog sheets and exact MIDs."""

from __future__ import annotations

import importlib.util
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
RESTORE_PATH = os.path.join(SCRIPT_DIR, "restore_stormpass_fog.py")
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Fog_ReloadAudit.json",
)
DEV_MAP_PATH = "/Game/Maps/DevMap"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_fog_reload_helpers", RESTORE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Fog restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_module()


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOG_RELOAD_AUDIT: " + str(message))


def main():
    metadata, records, expected_labels = restore.source_inventory()
    asset_report, meshes, parents, texture = restore.prepared_assets()
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(DEV_MAP_PATH):
        raise RuntimeError("Failed to leave StormPass through DevMap")
    if not level_subsystem.load_level(restore.MAP_PATH):
        raise RuntimeError("Failed to reload StormPass environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    materials = {}
    missing_materials = []
    for record in records:
        label = restore.managed_label(record)
        path = (
            restore.MATERIAL_INSTANCE_ROOT
            + "/"
            + restore.instance_asset_name(record)
        )
        instance = unreal.EditorAssetLibrary.load_asset(path)
        if not instance:
            missing_materials.append(path)
        else:
            materials[label] = instance
    if missing_materials:
        raise RuntimeError(
            "Reloaded Fog MIC is missing: " + missing_materials[0]
        )

    validation = restore.validate_all(
        records,
        expected_labels,
        meshes,
        materials,
        parents,
        texture,
        actor_subsystem,
    )
    if validation["failure_count"]:
        raise RuntimeError(
            "Reloaded StormPass Fog validation failed: "
            + str(validation["failures"][0])
        )
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    report = {
        "status": "passed",
        "operation": "saved_map_leave_and_reload_fog_audit",
        "dev_map_path": DEV_MAP_PATH,
        "map_path": restore.MAP_PATH,
        "world_path": world.get_path_name() if world else None,
        "source_metadata_path": restore.METADATA_PATH,
        "restoration_report_path": restore.REPORT_PATH,
        "asset_report_path": restore.ASSET_REPORT_PATH,
        "loaded_material_instance_count": len(materials),
        "validation": validation,
        "fog_stage_policy": "final_stage_saved_and_reloaded",
        "map_modified": False,
    }
    restore.write_json(REPORT_PATH, report)
    log(
        "RESULT actors={} fog={} failures={} max_location={} max_rotation={} "
        "max_scale={} report={}".format(
            validation["total_actor_count"],
            validation["managed_fog_actor_count"],
            validation["failure_count"],
            validation["maximum_transform_deltas"]["location_delta_cm"],
            validation["maximum_transform_deltas"]["rotation_delta_degrees"],
            validation["maximum_transform_deltas"]["scale_delta"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        restore.write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
                "map_modified": False,
            },
        )
        unreal.log_error(
            "KHAZAN_STORMPASS_FOG_RELOAD_AUDIT: " + str(exception)
        )
        raise
