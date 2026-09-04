"""Audit the reconstructed HeinMach map inside Unreal Editor.

This script is read-only. It records actor/component counts, mesh usage,
materials, bounds, lighting actors, and USD import option capabilities so the
reconstruction can be validated without relying on Content Browser counts.
"""

import json
import os
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportReports", "HeinMach_Environment_Audit.json"
)


def object_path(value):
    return value.get_path_name() if value else None


def vector_dict(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def write_report(payload):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def mesh_details(mesh):
    materials = []
    for static_material in safe_property(mesh, "static_materials", []) or []:
        materials.append(
            object_path(safe_property(static_material, "material_interface"))
        )

    details = {
        "asset": object_path(mesh),
        "materials": materials,
        "material_slot_count": len(materials),
    }
    try:
        bounds = mesh.get_bounds()
        details["bounds_origin"] = vector_dict(bounds.origin)
        details["bounds_extent"] = vector_dict(bounds.box_extent)
        details["sphere_radius"] = float(bounds.sphere_radius)
    except Exception as exception:
        details["bounds_error"] = str(exception)

    try:
        details["lod_count"] = int(unreal.EditorStaticMeshLibrary.get_lod_count(mesh))
        details["lod0_vertices"] = int(
            unreal.EditorStaticMeshLibrary.get_number_verts(mesh, 0)
        )
    except Exception as exception:
        details["geometry_error"] = str(exception)
    return details


def usd_option_details():
    options = unreal.UsdStageImportOptions()
    names = (
        "kinds_to_collapse",
        "merge_identical_material_slots",
        "prim_path_folder_structure",
        "share_assets_for_identical_prims",
        "interpret_lods",
        "import_actors",
        "import_geometry",
        "import_materials",
    )
    result = {}
    for name in names:
        try:
            result[name] = str(options.get_editor_property(name))
        except Exception as exception:
            result[name] = "UNAVAILABLE: " + str(exception)
    return result


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load map: " + MAP_PATH)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    components = [
        component
        for component in actor_subsystem.get_all_level_actors_components()
        if component
    ]

    actor_class_counts = {}
    folder_path_counts = {}
    actor_records = []
    light_records = []
    bounds_min = unreal.Vector(float("inf"), float("inf"), float("inf"))
    bounds_max = unreal.Vector(float("-inf"), float("-inf"), float("-inf"))
    bounded_actor_count = 0

    for actor in actors:
        class_name = actor.get_class().get_name()
        actor_class_counts[class_name] = actor_class_counts.get(class_name, 0) + 1
        label = actor.get_actor_label()
        folder_path = str(actor.get_folder_path())
        folder_path_counts[folder_path] = folder_path_counts.get(folder_path, 0) + 1
        location = actor.get_actor_location()
        parent_actor = None
        try:
            parent_actor = actor.get_attach_parent_actor()
        except Exception:
            pass
        root_component = safe_property(actor, "root_component")
        record = {
            "class": class_name,
            "label": label,
            "actor_path": actor.get_path_name(),
            "folder_path": folder_path,
            "parent_label": parent_actor.get_actor_label() if parent_actor else None,
            "root_component_class": (
                root_component.get_class().get_name() if root_component else None
            ),
            "location": vector_dict(location),
            "rotation": {
                "pitch": float(actor.get_actor_rotation().pitch),
                "yaw": float(actor.get_actor_rotation().yaw),
                "roll": float(actor.get_actor_rotation().roll),
            },
            "scale": vector_dict(actor.get_actor_scale3d()),
        }
        static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if static_mesh_component:
            record["static_mesh"] = object_path(
                safe_property(static_mesh_component, "static_mesh")
            )

        try:
            origin, extent = actor.get_actor_bounds(False, True)
            if extent.x > 0.0 or extent.y > 0.0 or extent.z > 0.0:
                record["bounds_origin"] = vector_dict(origin)
                record["bounds_extent"] = vector_dict(extent)
                bounds_min.x = min(bounds_min.x, origin.x - extent.x)
                bounds_min.y = min(bounds_min.y, origin.y - extent.y)
                bounds_min.z = min(bounds_min.z, origin.z - extent.z)
                bounds_max.x = max(bounds_max.x, origin.x + extent.x)
                bounds_max.y = max(bounds_max.y, origin.y + extent.y)
                bounds_max.z = max(bounds_max.z, origin.z + extent.z)
                bounded_actor_count += 1
        except Exception as exception:
            record["bounds_error"] = str(exception)

        if "Light" in class_name or "Light" in label:
            light_records.append(record)
        actor_records.append(record)

    component_class_counts = {}
    mesh_usage = {}
    mesh_assets = {}
    material_usage = {}
    static_mesh_component_count = 0
    populated_static_mesh_component_count = 0
    hism_component_count = 0
    hism_instance_count = 0
    hism_actor_labels = set()
    hism_mesh_paths = set()

    for component in components:
        class_name = component.get_class().get_name()
        component_class_counts[class_name] = component_class_counts.get(class_name, 0) + 1
        if isinstance(component, unreal.HierarchicalInstancedStaticMeshComponent):
            hism_component_count += 1
            try:
                hism_instance_count += int(component.get_instance_count())
            except Exception:
                pass
            try:
                owner = component.get_owner()
                if owner:
                    hism_actor_labels.add(owner.get_actor_label())
            except Exception:
                pass
            hism_mesh = safe_property(component, "static_mesh")
            if hism_mesh:
                hism_mesh_paths.add(object_path(hism_mesh))
        if not isinstance(component, unreal.StaticMeshComponent):
            continue

        static_mesh_component_count += 1
        mesh = safe_property(component, "static_mesh")
        if not mesh:
            continue
        populated_static_mesh_component_count += 1
        path = object_path(mesh)
        mesh_usage[path] = mesh_usage.get(path, 0) + 1
        if path not in mesh_assets:
            mesh_assets[path] = mesh_details(mesh)

        try:
            for material in component.get_materials():
                material_path = object_path(material)
                material_usage[material_path] = material_usage.get(material_path, 0) + 1
        except Exception:
            pass

    prop_actor_count = sum(
        1 for record in actor_records if record["label"].startswith("HM_Prop_")
    )
    foliage_batch_actor_count = sum(
        1 for record in actor_records if record["label"].startswith("HM_FoliageBatch_")
    )
    child_prop_actor_count = sum(
        1 for record in actor_records if record["label"].startswith("HM_ChildProp_")
    )
    fog_sheet_actor_count = sum(
        1 for record in actor_records if record["label"].startswith("HM_FogSheet_")
    )
    terrain_actor_count = sum(
        1 for record in actor_records if record["label"].startswith("HM_Terrain_")
    )
    source_light_actor_count = folder_path_counts.get(
        "HeinMach/Reconstructed/SourceLights", 0
    )
    preview_environment_actor_count = folder_path_counts.get(
        "HeinMach/Reconstructed/PreviewLighting", 0
    )
    categorized_actor_count = (
        prop_actor_count
        + foliage_batch_actor_count
        + child_prop_actor_count
        + fog_sheet_actor_count
        + terrain_actor_count
        + source_light_actor_count
        + preview_environment_actor_count
    )

    report = {
        "status": "audited",
        "map_path": MAP_PATH,
        "actor_count": len(actors),
        "actor_class_counts": dict(sorted(actor_class_counts.items())),
        "folder_path_counts": dict(sorted(folder_path_counts.items())),
        "reconstruction_summary": {
            "prop_actor_count": prop_actor_count,
            "foliage_batch_actor_count": foliage_batch_actor_count,
            "child_prop_actor_count": child_prop_actor_count,
            "fog_sheet_actor_count": fog_sheet_actor_count,
            "hism_component_count": hism_component_count,
            "hism_actor_count": len(hism_actor_labels),
            "hism_instance_count": hism_instance_count,
            "hism_unique_static_mesh_count": len(hism_mesh_paths),
            "terrain_actor_count": terrain_actor_count,
            "source_light_actor_count": source_light_actor_count,
            "preview_environment_actor_count": preview_environment_actor_count,
            "categorized_actor_count": categorized_actor_count,
            "uncategorized_actor_count": len(actors) - categorized_actor_count,
            "expected_counts_match": (
                prop_actor_count == 2665
                and foliage_batch_actor_count == 113
                and child_prop_actor_count == 15
                and fog_sheet_actor_count == 50
                and hism_component_count == 113
                and len(hism_actor_labels) == 113
                and hism_instance_count == 12495
                and terrain_actor_count == 2
                and source_light_actor_count == 89
                and preview_environment_actor_count == 4
                and categorized_actor_count == 2938
                and len(actors) == 2938
            ),
        },
        "component_count": len(components),
        "component_class_counts": dict(sorted(component_class_counts.items())),
        "static_mesh_component_count": static_mesh_component_count,
        "populated_static_mesh_component_count": populated_static_mesh_component_count,
        "unique_used_static_mesh_count": len(mesh_usage),
        "mesh_usage": dict(sorted(mesh_usage.items())),
        "mesh_assets": [mesh_assets[path] for path in sorted(mesh_assets)],
        "material_usage": dict(sorted(material_usage.items(), key=lambda pair: str(pair[0]))),
        "light_actor_count": len(light_records),
        "light_actors": light_records,
        "bounded_actor_count": bounded_actor_count,
        "actors": actor_records,
        "usd_stage_import_defaults": usd_option_details(),
    }
    if bounded_actor_count:
        report["world_bounds_min"] = vector_dict(bounds_min)
        report["world_bounds_max"] = vector_dict(bounds_max)
        report["world_bounds_size"] = vector_dict(bounds_max - bounds_min)

    write_report(report)
    unreal.log(
        "KHAZAN_HEINMACH_AUDIT: RESULT actors={} mesh_components={} "
        "unique_meshes={} HISM={}/{} lights={} counts_match={} report={}".format(
            report["actor_count"],
            report["populated_static_mesh_component_count"],
            report["unique_used_static_mesh_count"],
            report["reconstruction_summary"]["hism_component_count"],
            report["reconstruction_summary"]["hism_instance_count"],
            report["light_actor_count"],
            report["reconstruction_summary"]["expected_counts_match"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_report(
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            }
        )
        unreal.log_error("KHAZAN_HEINMACH_AUDIT: " + str(exception))
        raise
