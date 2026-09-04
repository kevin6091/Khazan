"""Restore the 15 non-root HeinMach StaticMeshComponents omitted by root-only extraction.

The source inventory and transforms come from HeinMach_Render_Gap_Analysis.json.
Only non-cinematic environment records with component type
``xxStaticMeshComponent`` are accepted.  The script is idempotent and creates a
map backup before placing actors.
"""

import json
import os
import re
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeChildRenderRestore"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed"
DESTINATION_ROOT = RECONSTRUCTED_ROOT + "/ChildRenderAssets"
CORRECTED_SOURCE_ROOT = RECONSTRUCTED_ROOT + "/CorrectedSourceAssets"
OVERRIDE_MATERIAL_ROOT = RECONSTRUCTED_ROOT + "/OverrideMaterials"
STAGE_NAME = "HeinMach_ChildRenderLibrary"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
GAP_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Render_Gap_Analysis.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Child_Render_Restore.json",
)

MANAGED_LABEL_PREFIX = "HM_ChildProp_"
MANAGED_FOLDER_ROOT = "HeinMach/Reconstructed/ChildProps"
EXPECTED_COMPONENT_COUNT = 15
EXPECTED_PACKAGE_COUNT = 3


def log(message):
    unreal.log("KHAZAN_HEINMACH_CHILD_RENDER: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required analysis report does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def source_usd_path(package):
    return os.path.join(FMODEL_ROOT, *str(package).split("/")) + ".usda"


def accepted_records(payload):
    records = [
        record
        for record in payload.get("non_root_static_mesh_components", [])
        if record.get("component_type") == "xxStaticMeshComponent"
        and record.get("visible") is not False
        and record.get("static_mesh_package")
    ]
    if len(records) != EXPECTED_COMPONENT_COUNT:
        raise RuntimeError(
            "Unexpected child render inventory: expected {} got {}".format(
                EXPECTED_COMPONENT_COUNT, len(records)
            )
        )
    packages = sorted({str(record["static_mesh_package"]) for record in records})
    if len(packages) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError(
            "Unexpected child mesh inventory: expected {} got {}".format(
                EXPECTED_PACKAGE_COUNT, len(packages)
            )
        )
    for record in records:
        local = record.get("local_transform", {})
        location = local.get("location_cm", {})
        rotation = local.get("rotation_degrees", {})
        scale = local.get("scale", {})
        values = (
            float(location.get("x", 0.0)),
            float(location.get("y", 0.0)),
            float(location.get("z", 0.0)),
            float(rotation.get("pitch", 0.0)),
            float(rotation.get("yaw", 0.0)),
            float(rotation.get("roll", 0.0)),
            float(scale.get("x", 1.0)) - 1.0,
            float(scale.get("y", 1.0)) - 1.0,
            float(scale.get("z", 1.0)) - 1.0,
        )
        if max(abs(value) for value in values) > 1.0e-6:
            raise RuntimeError(
                "Non-identity child transform requires hierarchy composition: {}".format(
                    record.get("actor_name")
                )
            )
    return records, packages


def write_mesh_stage(packages):
    source_files = [source_usd_path(package) for package in packages]
    missing = [path for path in source_files if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("Missing child render USD source: " + missing[0])
    stage_text = "\n".join(
        [
            "#usda 1.0",
            "(",
            "    metersPerUnit = 0.01",
            '    upAxis = "Z"',
            "    subLayers = [",
            ",\n".join(
                "        @{}@".format(path.replace("\\", "/"))
                for path in source_files
            ),
            "    ]",
            ")",
            "",
        ]
    )
    os.makedirs(os.path.dirname(GENERATED_STAGE_PATH), exist_ok=True)
    with open(GENERATED_STAGE_PATH, "w", encoding="utf-8", newline="\n") as output:
        output.write(stage_text)
    return source_files


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def assets_by_class(root):
    result = {}
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return result
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        root, recursive=True, include_folder=False
    ):
        result.setdefault(asset_class_name(asset_path), []).append(asset_path)
    return result


def normalized_asset_names(asset):
    names = {asset.get_name()}
    for prefix in ("SM_", "MI_", "M_"):
        if asset.get_name().startswith(prefix):
            names.add(asset.get_name()[len(prefix) :])
    return names


def loaded_asset_index(asset_paths):
    result = {}
    for asset_path in asset_paths:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            continue
        for name in normalized_asset_names(asset):
            result.setdefault(name, asset)
    return result


def import_mesh_library():
    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", False)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_only_used_materials", True)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", ["/"])
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("prim_path_folder_structure", False)
    options.set_editor_property("merge_identical_material_slots", False)
    options.set_editor_property("interpret_lods", True)
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", GENERATED_STAGE_PATH)
    task.set_editor_property("destination_path", DESTINATION_ROOT)
    task.set_editor_property("destination_name", STAGE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths"))


def ensure_meshes(packages):
    class_assets = assets_by_class(DESTINATION_ROOT)
    mesh_index = loaded_asset_index(class_assets.get("StaticMesh", []))
    missing = [package for package in packages if package_basename(package) not in mesh_index]
    imported_paths = []
    if missing:
        imported_paths = import_mesh_library()
        class_assets = assets_by_class(DESTINATION_ROOT)
        mesh_index = loaded_asset_index(class_assets.get("StaticMesh", []))
        missing = [
            package for package in packages if package_basename(package) not in mesh_index
        ]
    if missing:
        raise RuntimeError("USD import did not create child mesh: " + missing[0])
    return class_assets, mesh_index, imported_paths


def vector_from_transform(transform):
    value = transform.get("location_cm", {})
    return unreal.Vector(
        x=float(value.get("x", 0.0)),
        y=float(value.get("y", 0.0)),
        z=float(value.get("z", 0.0)),
    )


def rotator_from_transform(transform):
    value = transform.get("rotation_degrees", {})
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def scale_from_transform(transform):
    value = transform.get("scale", {})
    return unreal.Vector(
        x=float(value.get("x", 1.0)),
        y=float(value.get("y", 1.0)),
        z=float(value.get("z", 1.0)),
    )


def managed_label(record):
    return (
        "{}{}_{:05d}_{}_{:05d}".format(
            MANAGED_LABEL_PREFIX,
            record.get("source_level", "Unknown"),
            int(record.get("actor_object_index", 0)),
            record.get("actor_name", "Actor"),
            int(record.get("component_object_index", 0)),
        )
    )[:220]


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def spawn_static_mesh_actor(actor_subsystem, mesh, location, rotation):
    try:
        actor = actor_subsystem.spawn_actor_from_object(mesh, location, rotation)
    except Exception:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor, location, rotation
        )
        if actor:
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_static_mesh(mesh)
    if not actor:
        raise RuntimeError("Failed to spawn child mesh actor: " + mesh.get_name())
    return actor


def source_slot_materials(mesh_package):
    text = open(source_usd_path(mesh_package), "r", encoding="utf-8", errors="replace").read()
    result = {}
    pattern = re.compile(
        r"unrealMaterialIndex\s*=\s*(-?\d+).*?"
        r"rel\s+material:binding\s*=\s*<.*?/Materials/([^>]+)>",
        flags=re.DOTALL,
    )
    for slot_text, material_name in pattern.findall(text):
        result[int(slot_text)] = material_name
    return result


def ue_slot_for_source_slot(mesh, mesh_package, source_slot):
    source_name = source_slot_materials(mesh_package).get(source_slot)
    materials = mesh.get_editor_property("static_materials") or []
    if source_name:
        for ue_slot, static_material in enumerate(materials):
            material = static_material.get_editor_property("material_interface")
            if material and source_name in normalized_asset_names(material):
                return ue_slot
    if len(materials) == 1:
        return 0
    raise RuntimeError(
        "Cannot map source material slot {} for {} (source material {})".format(
            source_slot, mesh_package, source_name
        )
    )


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create child-render backup map")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def place_records(records, mesh_index, material_index):
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_world_path = current_world.get_path_name() if current_world else ""
    # A failed idempotent pass may leave valid managed actors in the current
    # dirty world. Reuse them instead of reloading the same map and discarding
    # or leaking that world.
    if not current_world_path.startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    managed = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    created_count = 0
    reused_count = 0
    material_assignment_count = 0

    for record in records:
        mesh_package = str(record["static_mesh_package"])
        mesh = mesh_index[package_basename(mesh_package)]
        transform = record.get("actor_world_transform", {})
        label = managed_label(record)
        actor = managed.get(label)
        if actor:
            reused_count += 1
            actor.set_actor_location(vector_from_transform(transform), False, False)
            actor.set_actor_rotation(rotator_from_transform(transform), False)
        else:
            actor = spawn_static_mesh_actor(
                actor_subsystem,
                mesh,
                vector_from_transform(transform),
                rotator_from_transform(transform),
            )
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            created_count += 1
        actor.set_actor_scale3d(scale_from_transform(transform))
        set_actor_folder(
            actor,
            "{}/{}".format(MANAGED_FOLDER_ROOT, record.get("source_level", "Unknown")),
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component.get_editor_property("static_mesh") != mesh:
            component.set_static_mesh(mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            component.empty_override_materials()

        for source_slot, material_package in enumerate(
            record.get("override_material_packages", [])
        ):
            if not material_package:
                continue
            material = material_index.get(package_basename(material_package))
            if not material:
                raise RuntimeError("Unresolved child override material: " + material_package)
            ue_slot = ue_slot_for_source_slot(mesh, mesh_package, source_slot)
            component.set_material(ue_slot, material)
            material_assignment_count += 1

    final_actors = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    ]
    return level_subsystem, {
        "created_count": created_count,
        "reused_count": reused_count,
        "material_assignment_count": material_assignment_count,
        "final_managed_actor_count": len(final_actors),
        "final_total_actor_count": len(actor_subsystem.get_all_level_actors()),
    }


def main():
    gap_payload = load_json(GAP_REPORT_PATH)
    records, packages = accepted_records(gap_payload)
    source_files = write_mesh_stage(packages)
    class_assets, mesh_index, imported_paths = ensure_meshes(packages)

    material_paths = []
    for root in (
        DESTINATION_ROOT,
        CORRECTED_SOURCE_ROOT,
        OVERRIDE_MATERIAL_ROOT,
    ):
        assets = assets_by_class(root)
        for class_name in ("Material", "MaterialInstanceConstant"):
            material_paths.extend(assets.get(class_name, []))
    material_index = loaded_asset_index(material_paths)

    backup_created = backup_map_once()
    level_subsystem, placement_result = place_records(
        records, mesh_index, material_index
    )
    if placement_result["final_managed_actor_count"] != EXPECTED_COMPONENT_COUNT:
        raise RuntimeError(
            "Child actor count mismatch: {}".format(
                placement_result["final_managed_actor_count"]
            )
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach map after child restore")
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "destination_root": DESTINATION_ROOT,
        "generated_stage": GENERATED_STAGE_PATH,
        "source_usd_files": source_files,
        "required_static_mesh_count": len(packages),
        "source_component_count": len(records),
        "imported_object_path_count": len(imported_paths),
        "imported_asset_class_counts": {
            name: len(paths) for name, paths in sorted(class_assets.items())
        },
        "placement_result": placement_result,
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "Barehanded staggering/basic-movement protagonist scenes",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} actors={} created={} reused={} total={} report={}".format(
            report["status"],
            report["required_static_mesh_count"],
            report["source_component_count"],
            placement_result["created_count"],
            placement_result["reused_count"],
            placement_result["final_total_actor_count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        unreal.log_error("KHAZAN_HEINMACH_CHILD_RENDER: " + str(exception))
        raise
