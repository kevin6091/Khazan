"""Remove the obsolete first-pass USD actor tree from the HeinMach map.

The authoritative reconstruction places every renderable prop as an
``HM_Prop_*`` actor.  The earlier all-in-one USD import remains useful for its
two merged landscape meshes, but its PointInstancer batches render the same
props a second time and create large floating/overlapping clusters.

This script creates a one-time map backup, preserves and names the two terrain
actors, and removes only the verified legacy generic Actor tree.  Imported
assets are intentionally retained as rollback/source data.
"""

import json
import os
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeLegacyCleanup"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Legacy_Actor_Cleanup.json",
)

LEGACY_STAGE_LABEL = "HeinMach_EnvironmentOnly"
LEGACY_ASSET_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Imported/"
    "HeinMach_EnvironmentOnly/StaticMeshes/"
)
TERRAIN_FOLDER = "HeinMach/Reconstructed/Terrain"

TERRAIN_SPECS = {
    LEGACY_ASSET_ROOT + "SM_RootComponent0.SM_RootComponent0": {
        "label": "HM_Terrain_Landscape1",
        "source_layer": "HeinMach_Landscape1",
        "location": (-25200.0, -25200.0, 100.0),
        "scale": (100.0, 100.0, 100.0),
    },
    LEGACY_ASSET_ROOT + "SM_RootComponent.SM_RootComponent": {
        "label": "HM_Terrain_Landscape2",
        "source_layer": "HeinMach_Landscape2",
        "location": (-11970.0, -23220.0, -3868.3093),
        "scale": (100.0, 100.0, 100.0),
    },
}


def log(message):
    unreal.log("KHAZAN_HEINMACH_LEGACY_CLEANUP: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_LEGACY_CLEANUP: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(obj):
    return obj.get_path_name() if obj else None


def actor_static_mesh(actor):
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if not component:
        return None
    return component.get_editor_property("static_mesh")


def actor_depth(actor):
    depth = 0
    seen = set()
    current = actor
    while current:
        path = current.get_path_name()
        if path in seen:
            break
        seen.add(path)
        try:
            current = current.get_attach_parent_actor()
        except Exception:
            current = None
        if current:
            depth += 1
    return depth


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def vector(values):
    return unreal.Vector(x=values[0], y=values[1], z=values[2])


def transform_record(actor, mesh_path, spec):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "actor_path": actor.get_path_name(),
        "label": actor.get_actor_label(),
        "mesh": mesh_path,
        "source_layer": spec["source_layer"],
        "location": {"x": location.x, "y": location.y, "z": location.z},
        "rotation": {
            "pitch": rotation.pitch,
            "yaw": rotation.yaw,
            "roll": rotation.roll,
        },
        "scale": {"x": scale.x, "y": scale.y, "z": scale.z},
    }


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicate = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicate:
        raise RuntimeError("Failed to create cleanup backup: " + BACKUP_MAP_PATH)
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach map: " + MAP_PATH)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    generic_actors = [
        actor for actor in actors if actor.get_class().get_name() == "Actor"
    ]

    terrain_by_mesh = {}
    for actor in generic_actors:
        mesh_path = object_path(actor_static_mesh(actor))
        if mesh_path in TERRAIN_SPECS:
            if mesh_path in terrain_by_mesh:
                raise RuntimeError("Duplicate terrain actor for " + mesh_path)
            terrain_by_mesh[mesh_path] = actor

    missing_terrain = sorted(set(TERRAIN_SPECS) - set(terrain_by_mesh))
    if missing_terrain:
        raise RuntimeError("Missing required terrain actors: " + ", ".join(missing_terrain))

    stage_roots = [
        actor for actor in generic_actors if actor.get_actor_label() == LEGACY_STAGE_LABEL
    ]
    already_clean = (
        len(generic_actors) == len(TERRAIN_SPECS)
        and not stage_roots
        and all(
            terrain_by_mesh[path].get_actor_label() == spec["label"]
            for path, spec in TERRAIN_SPECS.items()
        )
    )

    if not already_clean:
        # The verified pre-cleanup map contains 779 generic USD-import Actors:
        # 2 terrain actors and 777 obsolete stage/component actors.  Refuse to
        # run against an unknown composition instead of deleting user content.
        if len(generic_actors) != 779 or len(stage_roots) != 1:
            raise RuntimeError(
                "Unexpected legacy actor composition: generic={} stage_roots={}".format(
                    len(generic_actors), len(stage_roots)
                )
            )

    backup_created = backup_map_once()

    terrain_before = []
    for mesh_path, spec in TERRAIN_SPECS.items():
        terrain_before.append(transform_record(terrain_by_mesh[mesh_path], mesh_path, spec))

    deleted_labels = {}
    delete_failures = []
    terrain_actors = list(terrain_by_mesh.values())
    obsolete = [actor for actor in generic_actors if actor not in terrain_actors]
    for actor in sorted(obsolete, key=actor_depth, reverse=True):
        label = actor.get_actor_label()
        deleted_labels[label] = deleted_labels.get(label, 0) + 1
        try:
            if not actor_subsystem.destroy_actor(actor):
                delete_failures.append({"label": label, "reason": "destroy_actor returned false"})
        except Exception as exception:
            delete_failures.append({"label": label, "reason": str(exception)})

    if delete_failures:
        raise RuntimeError(
            "Failed to remove {} legacy actors; first={}".format(
                len(delete_failures), delete_failures[0]
            )
        )

    terrain_after = []
    for mesh_path, spec in TERRAIN_SPECS.items():
        actor = terrain_by_mesh[mesh_path]
        actor.set_actor_label(spec["label"], mark_dirty=True)
        set_actor_folder(actor, TERRAIN_FOLDER)
        actor.set_actor_location(vector(spec["location"]), False, False)
        actor.set_actor_rotation(unreal.Rotator(), False)
        actor.set_actor_scale3d(vector(spec["scale"]))
        terrain_after.append(transform_record(actor, mesh_path, spec))

    final_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    final_generic = [
        actor for actor in final_actors if actor.get_class().get_name() == "Actor"
    ]
    legacy_render_components = []
    for component in actor_subsystem.get_all_level_actors_components():
        if not isinstance(component, unreal.StaticMeshComponent):
            continue
        mesh_path = object_path(component.get_editor_property("static_mesh"))
        if not mesh_path or not mesh_path.startswith(LEGACY_ASSET_ROOT):
            continue
        owner = component.get_owner()
        legacy_render_components.append(
            {"actor": owner.get_actor_label() if owner else None, "mesh": mesh_path}
        )

    expected_terrain_meshes = set(TERRAIN_SPECS)
    remaining_legacy_meshes = {entry["mesh"] for entry in legacy_render_components}
    status = "cleaned"
    if (
        len(final_generic) != 2
        or len(legacy_render_components) != 2
        or remaining_legacy_meshes != expected_terrain_meshes
    ):
        status = "validation_failed"

    if status == "cleaned" and not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save cleaned HeinMach map")

    report = {
        "status": status,
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "already_clean": already_clean,
        "generic_actor_count_before": len(generic_actors),
        "obsolete_actor_count": len(obsolete),
        "deleted_actor_count": len(obsolete) - len(delete_failures),
        "deleted_label_counts": dict(sorted(deleted_labels.items())),
        "delete_failures": delete_failures,
        "terrain_before": terrain_before,
        "terrain_after": terrain_after,
        "final_actor_count": len(final_actors),
        "final_generic_actor_count": len(final_generic),
        "remaining_legacy_render_components": legacy_render_components,
        "preserved_assets": LEGACY_ASSET_ROOT,
        "reason": (
            "Removed duplicate first-pass PointInstancer/component actors; "
            "authoritative HM_Prop placements and the two landscape meshes remain."
        ),
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} deleted={} terrain={} actors={} report={}".format(
            status,
            report["deleted_actor_count"],
            len(terrain_after),
            len(final_actors),
            REPORT_PATH,
        )
    )
    if status != "cleaned":
        raise RuntimeError("Legacy cleanup validation failed; see " + REPORT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        error(str(exception))
        error(failure["traceback"])
        raise
