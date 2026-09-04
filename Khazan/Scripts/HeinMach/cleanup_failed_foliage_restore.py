"""Remove only unsaved/partial corrected foliage duplicates from the main map."""

import json
import os
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
EXPECTED_BASE_ACTOR_COUNT = 2760
IMPORT_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Batch_Import.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Failed_Foliage_Restore_Cleanup.json",
)


def write_json(payload):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def main():
    with open(IMPORT_REPORT_PATH, "r", encoding="utf-8-sig") as source:
        import_report = json.load(source)
    expected_mesh_paths = {
        row["mesh_path"] for row in import_report.get("batch_records", [])
    }
    if len(expected_mesh_paths) != 113:
        raise RuntimeError("Unexpected corrected foliage mesh inventory")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach main map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    targets = []
    target_rows = []
    for actor in actors_before:
        matched_meshes = []
        for component in actor.get_components_by_class(unreal.ActorComponent):
            if not component or not hasattr(component, "get_instance_count"):
                continue
            try:
                mesh = component.get_editor_property("static_mesh")
            except Exception:
                continue
            mesh_path = mesh.get_path_name() if mesh else None
            if mesh_path in expected_mesh_paths:
                matched_meshes.append(mesh_path)
        if matched_meshes:
            targets.append(actor)
            target_rows.append(
                {
                    "label": actor.get_actor_label(),
                    "actor_path": actor.get_path_name(),
                    "mesh_paths": matched_meshes,
                }
            )

    if targets and not actor_subsystem.destroy_actors(targets):
        raise RuntimeError("Failed to remove partial foliage duplicate actors")
    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    if len(actors_after) != EXPECTED_BASE_ACTOR_COUNT:
        raise RuntimeError(
            "Post-cleanup main actor count is {} instead of {}".format(
                len(actors_after), EXPECTED_BASE_ACTOR_COUNT
            )
        )
    if targets and not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save cleaned HeinMach main map")

    report = {
        "status": "clean",
        "map_path": MAP_PATH,
        "actor_count_before": len(actors_before),
        "removed_actor_count": len(targets),
        "actor_count_after": len(actors_after),
        "removed_actors": target_rows,
    }
    write_json(report)
    unreal.log(
        "KHAZAN_HEINMACH_FOLIAGE_CLEANUP: removed={} actors={} report={}".format(
            len(targets), len(actors_after), REPORT_PATH
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            }
        )
        unreal.log_error("KHAZAN_HEINMACH_FOLIAGE_CLEANUP: " + str(exception))
        raise
