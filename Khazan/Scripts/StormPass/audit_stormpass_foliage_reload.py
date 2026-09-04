"""Reload-audit the saved StormPass Foliage HISM restoration."""

from __future__ import annotations

import collections
import importlib.util
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
RESTORE_PATH = os.path.join(SCRIPT_DIR, "restore_stormpass_foliage.py")
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Foliage_ReloadAudit.json",
)
DEV_MAP_PATH = "/Game/Maps/DevMap"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_foliage_reload_helpers", RESTORE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Foliage restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_module()


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOLIAGE_RELOAD_AUDIT: " + str(message))


def main():
    metadata, records, expected_labels = restore.source_inventory()
    asset_report, meshes, slot_maps = restore.prepared_assets(records)
    material_report, materials = restore.prepared_materials(records)
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(DEV_MAP_PATH):
        raise RuntimeError("Failed to leave StormPass through DevMap")
    if not level_subsystem.load_level(restore.MAP_PATH):
        raise RuntimeError("Failed to reload StormPass environment map")

    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    actors = list(
        unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).get_all_level_actors()
    )
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor and actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
    }
    missing_labels = sorted(expected_labels - set(managed))
    extra_labels = sorted(set(managed) - expected_labels)
    if missing_labels or extra_labels:
        raise RuntimeError(
            "Reloaded Foliage actor set mismatch: missing={} extra={}".format(
                len(missing_labels), len(extra_labels)
            )
        )
    fog = restore.fog_actors(actors)
    if len(fog) != restore.EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog appeared during Foliage reload audit")
    expected_actor_count = (
        restore.EXPECTED_BASE_ACTOR_COUNT + restore.EXPECTED_COMPONENT_COUNT
    )
    if len(actors) != expected_actor_count:
        raise RuntimeError(
            "Reloaded StormPass actor count differs: {}".format(len(actors))
        )

    issue_counts = collections.Counter()
    issue_records = []
    transform_failure_count = 0
    validated_instance_count = 0
    validated_override_count = 0
    class_component_count = 0
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    counts_by_level = collections.Counter()
    counts_by_mesh = collections.Counter()
    instances_by_mesh = collections.Counter()
    for index, record in enumerate(records, start=1):
        label = restore.managed_label(record)
        actor = managed[label]
        components = list(
            actor.get_components_by_class(
                unreal.FoliageInstancedStaticMeshComponent
            )
        )
        class_component_count += len(components)
        if len(components) != 1:
            issue_counts["component_count"] += 1
            issue_records.append(
                {
                    "label": label,
                    "issues": ["component_count"],
                    "actual_component_count": len(components),
                }
            )
            continue
        component = components[0]
        issues, component_maxima, overrides, transform_failures = (
            restore.validate_component(
                component,
                record,
                meshes[record["static_mesh_package"]],
                slot_maps[record["static_mesh_package"]],
                materials,
            )
        )
        for issue in issues:
            issue_counts[issue] += 1
        if issues:
            issue_records.append({"label": label, "issues": issues})
        for name in maxima:
            maxima[name] = max(maxima[name], component_maxima[name])
        transform_failure_count += transform_failures
        validated_instance_count += component.get_instance_count()
        validated_override_count += overrides
        counts_by_level[record["source_level"]] += 1
        counts_by_mesh[record["static_mesh_package"]] += 1
        instances_by_mesh[record["static_mesh_package"]] += component.get_instance_count()
        if index % 40 == 0 or index == len(records):
            log("Validated {}/{} reloaded components".format(index, len(records)))

    failures = {
        "component_issue_count": len(issue_records),
        "instance_transform_failure_count": transform_failure_count,
        "missing_label_count": len(missing_labels),
        "extra_label_count": len(extra_labels),
    }
    if (
        any(failures.values())
        or class_component_count != restore.EXPECTED_COMPONENT_COUNT
        or validated_instance_count != restore.EXPECTED_INSTANCE_COUNT
        or validated_override_count != restore.EXPECTED_OVERRIDE_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Reloaded Foliage validation failed: {}".format(failures)
        )

    report = {
        "status": "passed",
        "operation": "saved_map_leave_and_reload_foliage_audit",
        "dev_map_path": DEV_MAP_PATH,
        "map_path": restore.MAP_PATH,
        "world_path": world.get_path_name() if world else None,
        "total_actor_count": len(actors),
        "managed_actor_count": len(managed),
        "foliage_component_count": class_component_count,
        "validated_instance_count": validated_instance_count,
        "validated_override_reference_count": validated_override_count,
        "component_issue_count": len(issue_records),
        "component_issue_counts_by_type": dict(issue_counts),
        "component_issues": issue_records,
        "instance_transform_failure_count": transform_failure_count,
        "maximum_transform_deltas": maxima,
        "counts_by_level": dict(sorted(counts_by_level.items())),
        "component_counts_by_mesh": dict(sorted(counts_by_mesh.items())),
        "instance_counts_by_mesh": dict(sorted(instances_by_mesh.items())),
        "fog_actor_count": len(fog),
        "fog_policy": "deferred_until_final_pass",
        "source_metadata_path": restore.METADATA_PATH,
        "restoration_report_path": restore.REPORT_PATH,
        "asset_report_path": restore.ASSET_REPORT_PATH,
        "material_report_path": restore.MATERIAL_REPORT_PATH,
    }
    restore.write_json(REPORT_PATH, report)
    log(
        "RESULT actors={} components={} instances={} overrides={} failures={} fog=0 report={}".format(
            report["total_actor_count"],
            report["foliage_component_count"],
            report["validated_instance_count"],
            report["validated_override_reference_count"],
            report["instance_transform_failure_count"],
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
                "fog_policy": "deferred_until_final_pass",
            },
        )
        unreal.log_error(
            "KHAZAN_STORMPASS_FOLIAGE_RELOAD_AUDIT: " + str(exception)
        )
        raise
