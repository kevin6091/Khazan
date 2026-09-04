"""Import the exact FModel-exported StormPass Landscape component meshes.

This pass is deliberately asset-only.  It does not load, save, or modify the
StormPass map and it never creates Landscape, light, foliage, or Fog actors.
The 456 component USDA files are imported in restart-safe batches and each
result is checked against the source SectionBase + CachedLocalBox bounds.
"""

import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeComponents.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Landscape_MeshImport.json",
)
DESTINATION_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Landscape/Meshes"
)
LANDSCAPE_GROUPS = {
    "StormPass_Landscape": "Main",
    "StormPass_Boss_Phase_2": "Boss",
}
EXPECTED_LANDSCAPES = {
    "StormPass_Landscape": ("Landscape_mainfield", 440),
    "StormPass_Boss_Phase_2": ("Landscape_0", 16),
}
EXPECTED_COMPONENT_COUNT = 456
BOUND_TOLERANCE = 0.02


def log(message):
    unreal.log("KHAZAN_STORMPASS_LANDSCAPE_IMPORT: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_inventory():
    metadata = load_json(METADATA_PATH)
    records = []
    landscape_summary = []
    levels = metadata.get("levels") or []
    if len(levels) != len(EXPECTED_LANDSCAPES):
        raise RuntimeError("StormPass Landscape level inventory changed")

    for level in levels:
        source_level = str(level.get("source_level"))
        if source_level not in EXPECTED_LANDSCAPES:
            raise RuntimeError("Unexpected Landscape source level: " + source_level)
        expected_name, expected_count = EXPECTED_LANDSCAPES[source_level]
        landscape_name = str(level.get("landscape_name"))
        components = level.get("components") or []
        if landscape_name != expected_name or len(components) != expected_count:
            raise RuntimeError(
                "Landscape inventory changed for {}: {} / {}".format(
                    source_level, landscape_name, len(components)
                )
            )
        group = LANDSCAPE_GROUPS[source_level]
        for component in components:
            record = dict(component)
            record["source_level"] = source_level
            record["landscape_name"] = landscape_name
            record["destination_group"] = group
            source_usd = os.path.normpath(str(record.get("source_usd", "")))
            if not os.path.isfile(source_usd):
                raise RuntimeError("Missing Landscape component USDA: " + source_usd)
            record["source_usd"] = source_usd
            records.append(record)
        landscape_summary.append(
            {
                "source_level": source_level,
                "landscape_name": landscape_name,
                "destination_group": group,
                "component_count": len(components),
            }
        )

    if len(records) != EXPECTED_COMPONENT_COUNT:
        raise RuntimeError(
            "StormPass Landscape component count changed: {} != {}".format(
                len(records), EXPECTED_COMPONENT_COUNT
            )
        )
    keys = [
        (record["source_level"], record["component_name"]) for record in records
    ]
    if len(set(keys)) != len(keys):
        raise RuntimeError("Duplicate StormPass Landscape component key")
    return metadata, landscape_summary, records


def destination_parent(record):
    return "{}/{}".format(DESTINATION_ROOT, record["destination_group"])


def destination_component_root(record):
    return "{}/{}".format(destination_parent(record), record["component_name"])


def asset_class_name(path):
    data = unreal.EditorAssetLibrary.find_asset_data(path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        return "Invalid"


def component_mesh_path(record):
    parent = destination_parent(record)
    component_name = record["component_name"]
    direct_candidates = [
        "{}/{}".format(parent, component_name),
        "{}/{}/{}".format(parent, component_name, component_name),
    ]
    paths = []
    for path in direct_candidates:
        if (
            unreal.EditorAssetLibrary.does_asset_exist(path)
            and asset_class_name(path) == "StaticMesh"
        ):
            paths.append(path)

    root = destination_component_root(record)
    if unreal.EditorAssetLibrary.does_directory_exist(root):
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        ):
            if asset_class_name(path) == "StaticMesh":
                paths.append(path)

    unique_paths = sorted(set(paths))
    if len(unique_paths) > 1:
        raise RuntimeError(
            "Multiple StaticMeshes found for {}: {}".format(
                component_name, unique_paths
            )
        )
    return unique_paths[0] if unique_paths else None


def component_mesh(record):
    path = component_mesh_path(record)
    return unreal.EditorAssetLibrary.load_asset(path) if path else None


def landscape_import_options():
    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", False)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", ["/"])
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("prim_path_folder_structure", False)
    options.set_editor_property("merge_identical_material_slots", False)
    options.set_editor_property("interpret_lods", False)
    options.set_editor_property(
        "existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE
    )
    return options


def close_enough(actual, expected):
    return abs(float(actual) - float(expected)) <= BOUND_TOLERANCE


def validate_mesh_bound(record, mesh):
    bounds = mesh.get_bounding_box()
    local_box = record["cached_local_box"]
    section = record["section_base"]
    expected_min = (
        float(section["x"]) + float(local_box["min"]["x"]),
        float(section["y"]) + float(local_box["min"]["y"]),
        float(local_box["min"]["z"]),
    )
    expected_max = (
        float(section["x"]) + float(local_box["max"]["x"]),
        float(section["y"]) + float(local_box["max"]["y"]),
        float(local_box["max"]["z"]),
    )
    actual_min = (bounds.min.x, bounds.min.y, bounds.min.z)
    actual_max = (bounds.max.x, bounds.max.y, bounds.max.z)
    valid = all(
        close_enough(actual, expected)
        for actual, expected in zip(
            actual_min + actual_max, expected_min + expected_max
        )
    )
    return valid, {
        "component_name": record["component_name"],
        "destination_group": record["destination_group"],
        "mesh_asset": mesh.get_path_name(),
        "actual_min": list(actual_min),
        "actual_max": list(actual_max),
        "expected_min": list(expected_min),
        "expected_max": list(expected_max),
    }


def configure_collision(mesh):
    body_setup = mesh.get_editor_property("body_setup")
    if not body_setup:
        return False, False
    target = unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    current = body_setup.get_editor_property("collision_trace_flag")
    changed = current != target
    if changed:
        mesh.modify()
        body_setup.set_editor_property("collision_trace_flag", target)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
    return True, changed


def current_world_snapshot():
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor.get_editor_world()
        world_path = world.get_path_name() if world else None
        actors = unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).get_all_level_actors()
        fog = []
        for actor in actors:
            if not actor:
                continue
            label = actor.get_actor_label()
            class_name = actor.get_class().get_name()
            if label.startswith("SP_Fog_") or "Fog" in class_name:
                fog.append({"label": label, "class": class_name})
        return {
            "world_path": world_path,
            "actor_count": len(actors),
            "fog_actor_count": len(fog),
            "fog_actors": fog,
        }
    except Exception as exc:
        return {"snapshot_error": str(exc)}


def import_records(records):
    missing = [record for record in records if not component_mesh_path(record)]
    tasks = []
    for record in missing:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", record["source_usd"])
        task.set_editor_property("destination_path", destination_parent(record))
        task.set_editor_property("destination_name", record["component_name"])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("options", landscape_import_options())
        task.set_editor_property("factory", unreal.UsdStageImportFactory())
        tasks.append(task)

    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    imported_paths = [path for task in tasks for path in task.imported_object_paths]
    unresolved = [
        record["component_name"]
        for record in records
        if not component_mesh_path(record)
    ]
    if unresolved:
        raise RuntimeError(
            "Landscape USD batch left a component unresolved: " + unresolved[0]
        )

    bounds = []
    bound_failures = []
    for record in records:
        mesh = component_mesh(record)
        if not mesh:
            raise RuntimeError("Unable to load imported Landscape StaticMesh")
        valid, detail = validate_mesh_bound(record, mesh)
        bounds.append(detail)
        if not valid:
            bound_failures.append(detail)
    if bound_failures:
        raise RuntimeError(
            "Landscape component bound mismatch: "
            + bound_failures[0]["component_name"]
        )
    return {
        "missing_before_count": len(missing),
        "task_count": len(tasks),
        "imported_object_path_count": len(imported_paths),
        "validated_bound_count": len(bounds),
        "bound_failure_count": 0,
        "bounds": bounds,
    }


def inventory_snapshot(records):
    resolved = []
    unresolved = []
    by_group = {}
    for record in records:
        path = component_mesh_path(record)
        group = record["destination_group"]
        counts = by_group.setdefault(group, {"resolved": 0, "unresolved": 0})
        if path:
            resolved.append(path)
            counts["resolved"] += 1
        else:
            unresolved.append(
                "{}:{}".format(record["source_level"], record["component_name"])
            )
            counts["unresolved"] += 1
    return {
        "resolved_component_count": len(resolved),
        "unresolved_component_count": len(unresolved),
        "resolved_asset_path_count": len(set(resolved)),
        "by_group": by_group,
        "first_unresolved": unresolved[:10],
    }


def prepare_batch(offset=0, limit=25):
    _metadata, landscapes, records = load_inventory()
    offset = int(offset)
    limit = int(limit)
    if offset < 0 or limit <= 0:
        raise ValueError("offset must be >= 0 and limit must be > 0")
    selected = records[offset : offset + limit]
    if not selected:
        raise ValueError("Landscape batch selection is empty")

    world_before = current_world_snapshot()
    batch_result = import_records(selected)
    snapshot = inventory_snapshot(records)
    world_after = current_world_snapshot()
    if world_after != world_before:
        raise RuntimeError("Editor world state changed during asset-only import")

    status = (
        "passed"
        if snapshot["resolved_component_count"] == EXPECTED_COMPONENT_COUNT
        else "in_progress"
    )
    report = {
        "status": status,
        "operation": "asset_only_landscape_component_usd_import",
        "map_modified": False,
        "fog_policy": "deferred_until_final_pass",
        "metadata_path": METADATA_PATH,
        "destination_root": DESTINATION_ROOT,
        "source_landscapes": landscapes,
        "source_component_count": len(records),
        "source_usd_total_bytes": sum(
            int(record.get("source_usd_bytes", 0)) for record in records
        ),
        "batch": {
            "offset": offset,
            "requested_limit": limit,
            "selected_count": len(selected),
            "first_component": selected[0]["component_name"],
            "last_component": selected[-1]["component_name"],
            "result": batch_result,
        },
        "inventory": snapshot,
        "world_before": world_before,
        "world_after": world_after,
    }
    write_json(REPORT_PATH, report)
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )
    try:
        unreal.SystemLibrary.collect_garbage()
    except Exception:
        pass
    log(
        "BATCH offset={} selected={} imported={} resolved={}/{} status={} report={}".format(
            offset,
            len(selected),
            batch_result["missing_before_count"],
            snapshot["resolved_component_count"],
            EXPECTED_COMPONENT_COUNT,
            status,
            REPORT_PATH,
        )
    )
    return report


def audit_all():
    _metadata, landscapes, records = load_inventory()
    snapshot = inventory_snapshot(records)
    bound_failures = []
    validated = 0
    if snapshot["unresolved_component_count"] == 0:
        for record in records:
            mesh = component_mesh(record)
            valid, detail = validate_mesh_bound(record, mesh)
            validated += 1
            if not valid:
                bound_failures.append(detail)
    report = {
        "status": (
            "passed"
            if snapshot["unresolved_component_count"] == 0 and not bound_failures
            else "failed"
        ),
        "operation": "asset_only_landscape_component_mesh_audit",
        "map_modified": False,
        "fog_policy": "deferred_until_final_pass",
        "metadata_path": METADATA_PATH,
        "destination_root": DESTINATION_ROOT,
        "source_landscapes": landscapes,
        "source_component_count": len(records),
        "inventory": snapshot,
        "validated_bound_count": validated,
        "bound_failure_count": len(bound_failures),
        "bound_failures": bound_failures[:10],
        "world": current_world_snapshot(),
    }
    write_json(REPORT_PATH, report)
    log(
        "AUDIT resolved={}/{} bounds={} failures={} status={}".format(
            snapshot["resolved_component_count"],
            EXPECTED_COMPONENT_COUNT,
            validated,
            len(bound_failures),
            report["status"],
        )
    )
    return report


def finalize_assets():
    _metadata, landscapes, records = load_inventory()
    snapshot = inventory_snapshot(records)
    if snapshot["unresolved_component_count"]:
        raise RuntimeError("Cannot finalize unresolved Landscape component assets")

    world_before = current_world_snapshot()
    bound_failures = []
    collision_ready = 0
    collision_changed = 0
    collision_failures = []
    for record in records:
        mesh = component_mesh(record)
        valid, detail = validate_mesh_bound(record, mesh)
        if not valid:
            bound_failures.append(detail)
            continue
        ready, changed = configure_collision(mesh)
        if ready:
            collision_ready += 1
        else:
            collision_failures.append(
                {
                    "destination_group": record["destination_group"],
                    "component_name": record["component_name"],
                    "mesh_asset": mesh.get_path_name(),
                }
            )
        if changed:
            collision_changed += 1

    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )
    world_after = current_world_snapshot()
    if world_after != world_before:
        raise RuntimeError("Editor world state changed during asset finalization")

    status = (
        "passed"
        if not bound_failures
        and not collision_failures
        and collision_ready == EXPECTED_COMPONENT_COUNT
        else "failed"
    )
    report = {
        "status": status,
        "operation": "asset_only_landscape_component_mesh_finalization",
        "map_modified": False,
        "fog_policy": "deferred_until_final_pass",
        "metadata_path": METADATA_PATH,
        "destination_root": DESTINATION_ROOT,
        "source_landscapes": landscapes,
        "source_component_count": len(records),
        "source_usd_total_bytes": sum(
            int(record.get("source_usd_bytes", 0)) for record in records
        ),
        "inventory": snapshot,
        "validated_bound_count": len(records) - len(bound_failures),
        "bound_failure_count": len(bound_failures),
        "bound_failures": bound_failures[:10],
        "collision_complex_as_simple_count": collision_ready,
        "collision_changed_this_run": collision_changed,
        "collision_failure_count": len(collision_failures),
        "collision_failures": collision_failures[:10],
        "world_before": world_before,
        "world_after": world_after,
    }
    write_json(REPORT_PATH, report)
    if status != "passed":
        raise RuntimeError("StormPass Landscape mesh finalization failed")
    log(
        "FINALIZED meshes={} bounds={} collision={} changed={} fog={}".format(
            snapshot["resolved_component_count"],
            report["validated_bound_count"],
            collision_ready,
            collision_changed,
            world_after.get("fog_actor_count"),
        )
    )
    return report


if __name__ == "__main__":
    try:
        prepare_batch(0, 25)
    except Exception:
        log(traceback.format_exc())
        raise
