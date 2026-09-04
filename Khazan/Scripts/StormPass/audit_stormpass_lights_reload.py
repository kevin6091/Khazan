"""Leave and reload StormPass, then audit the saved source-light restoration."""

from __future__ import annotations

import collections
import importlib.util
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
RESTORE_PATH = os.path.join(SCRIPT_DIR, "restore_stormpass_lights.py")
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Light_ReloadAudit.json",
)
DEV_MAP_PATH = "/Game/Maps/DevMap"


def load_restore_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_light_reload_helpers", RESTORE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Light restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_restore_module()


def log(message):
    unreal.log("KHAZAN_STORMPASS_LIGHT_RELOAD_AUDIT: " + str(message))


def main():
    _metadata, records, expected_labels = restore.source_inventory()
    profile_report, profile = restore.prepared_profile()
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
    fog = restore.fog_actors(actors)
    if len(fog) != restore.EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog appeared during Light reload audit")
    expected_actor_count = (
        restore.EXPECTED_BASE_ACTOR_COUNT + restore.EXPECTED_SOURCE_LIGHT_COUNT
    )
    if len(actors) != expected_actor_count:
        raise RuntimeError(
            "Reloaded StormPass actor count differs: {}".format(len(actors))
        )

    managed_list = [
        actor
        for actor in actors
        if actor
        and actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
    ]
    managed = {actor.get_actor_label(): actor for actor in managed_list}
    missing_labels = sorted(expected_labels - set(managed))
    extra_labels = sorted(set(managed) - expected_labels)
    duplicate_count = len(managed_list) - len(managed)
    if missing_labels or extra_labels or duplicate_count:
        raise RuntimeError(
            "Reloaded Light actor set mismatch: missing={} extra={} duplicate={}".format(
                len(missing_labels), len(extra_labels), duplicate_count
            )
        )

    failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
        "maximum_property_float_delta": 0.0,
    }
    type_counts = collections.Counter()
    counts_by_level = collections.Counter()
    ies_binding_count = 0
    for record in records:
        label = restore.managed_label(record)
        actor = managed[label]
        issues, deltas = restore.validate_actor(actor, record, profile)
        for name in maxima:
            maxima[name] = max(maxima[name], deltas[name])
        is_spot = record["actor_type"] == "xxSpotLight"
        component = restore.get_light_component(actor, is_spot)
        uses_ies = restore.expected_values(record)["uses_ies"]
        if uses_ies:
            ies_binding_count += int(
                component.get_editor_property("ies_texture") == profile
            )
        type_counts["spot" if is_spot else "point"] += 1
        counts_by_level[record["source_level"]] += 1
        if issues:
            failures.append({"label": label, "issues": issues})
    if (
        failures
        or type_counts["point"] != restore.EXPECTED_POINT_LIGHT_COUNT
        or type_counts["spot"] != restore.EXPECTED_SPOT_LIGHT_COUNT
        or ies_binding_count != restore.EXPECTED_IES_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Reloaded Light validation failed: actors={} ies={}".format(
                len(failures), ies_binding_count
            )
        )

    report = {
        "status": "passed",
        "operation": "saved_map_leave_and_reload_source_light_audit",
        "dev_map_path": DEV_MAP_PATH,
        "map_path": restore.MAP_PATH,
        "world_path": world.get_path_name() if world else None,
        "total_actor_count": len(actors),
        "managed_light_actor_count": len(managed),
        "point_light_count": type_counts["point"],
        "spot_light_count": type_counts["spot"],
        "validated_ies_binding_count": ies_binding_count,
        "counts_by_level": dict(sorted(counts_by_level.items())),
        "validation_failure_count": len(failures),
        "validation_failures": failures,
        "maximum_deltas": maxima,
        "missing_label_count": len(missing_labels),
        "extra_label_count": len(extra_labels),
        "duplicate_label_count": duplicate_count,
        "profile_asset_path": profile.get_path_name(),
        "profile_source_range": {
            "min": profile_report["source_min"],
            "max": profile_report["source_max"],
            "samples": profile_report["source_sample_count"],
            "nonzero_samples": profile_report[
                "source_nonzero_sample_count"
            ],
        },
        "source_metadata_path": restore.METADATA_PATH,
        "restoration_report_path": restore.REPORT_PATH,
        "profile_report_path": restore.PROFILE_REPORT_PATH,
        "fog_actor_count": len(fog),
        "fog_policy": "deferred_until_final_pass",
    }
    restore.write_json(REPORT_PATH, report)
    log(
        "RESULT actors={} lights={} point={} spot={} ies={} failures=0 fog=0 report={}".format(
            len(actors),
            len(managed),
            type_counts["point"],
            type_counts["spot"],
            ies_binding_count,
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
            "KHAZAN_STORMPASS_LIGHT_RELOAD_AUDIT: " + str(exception)
        )
        raise
