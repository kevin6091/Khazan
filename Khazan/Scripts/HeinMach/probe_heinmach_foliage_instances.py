"""Inspect the corrected foliage sandbox without mutating it."""

import json
import os
import traceback

import unreal


SANDBOX_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_FoliageImportSandbox"
)
FOLIAGE_ASSET_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FoliageBatches"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Instance_Probe.json",
)


def write_json(payload):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(obj):
    return obj.get_path_name() if obj else None


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(SANDBOX_MAP_PATH):
        raise RuntimeError("Failed to load corrected foliage sandbox")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    records = []
    total_instances = 0
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        components = list(actor.get_components_by_class(unreal.ActorComponent))
        foliage_components = [
            component
            for component in components
            if component.get_class().get_name()
            in (
                "FoliageInstancedStaticMeshComponent",
                "InstancedStaticMeshComponent",
                "HierarchicalInstancedStaticMeshComponent",
            )
        ]
        for component in foliage_components:
            try:
                instance_count = int(component.get_instance_count())
            except Exception:
                instance_count = -1
            total_instances += max(instance_count, 0)
            sample_transforms = []
            for instance_index in range(min(max(instance_count, 0), 2)):
                try:
                    transform = component.get_instance_transform(
                        instance_index, world_space=False
                    )
                    sample_transforms.append(str(transform))
                except Exception as exception:
                    sample_transforms.append("ERROR: " + str(exception))
            mesh = component.get_editor_property("static_mesh")
            records.append(
                {
                    "actor_label": actor.get_actor_label(),
                    "actor_path": actor.get_path_name(),
                    "actor_class": actor.get_class().get_name(),
                    "component_class": component.get_class().get_name(),
                    "component_path": component.get_path_name(),
                    "instance_count": instance_count,
                    "mesh_path": object_path(mesh),
                    "sample_local_transforms": sample_transforms,
                }
            )

    sample_actor = actor_subsystem.get_all_level_actors()[0]
    actor_methods = [
        name
        for name in (
            "add_component_by_class",
            "finish_add_component",
            "add_instance_component",
            "get_instance_components",
        )
        if hasattr(sample_actor, name)
    ]
    subsystem_methods = [
        name
        for name in dir(actor_subsystem)
        if any(token in name.lower() for token in ("duplicate", "copy", "paste"))
    ]
    level_library_methods = []
    if hasattr(unreal, "EditorLevelLibrary"):
        level_library_methods = [
            name
            for name in dir(unreal.EditorLevelLibrary)
            if any(token in name.lower() for token in ("duplicate", "copy", "paste"))
        ]

    payload = {
        "status": "probed",
        "sandbox_map_path": SANDBOX_MAP_PATH,
        "foliage_component_count": len(records),
        "total_instance_count": total_instances,
        "actor_methods": actor_methods,
        "editor_actor_subsystem_methods": subsystem_methods,
        "duplicate_actor_doc": getattr(
            actor_subsystem.duplicate_actor, "__doc__", None
        ),
        "duplicate_actors_doc": getattr(
            actor_subsystem.duplicate_actors, "__doc__", None
        ),
        "editor_level_library_methods": level_library_methods,
        "records": records,
    }
    write_json(payload)
    unreal.log(
        "KHAZAN_HEINMACH_FOLIAGE_PROBE: components={} instances={} report={}".format(
            len(records), total_instances, REPORT_PATH
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
        unreal.log_error("KHAZAN_HEINMACH_FOLIAGE_PROBE: " + str(exception))
        raise
