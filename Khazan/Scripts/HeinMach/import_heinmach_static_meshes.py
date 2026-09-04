"""Import extracted HeinMach prop meshes and rebuild their level placements.

This consumes the compact placement manifest produced by analyze_heinmach.py.
Only environment layers are accepted; cinematic, character, spawn, sound, and
the barehanded staggering scene are never read or placed.
"""

import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCLUSION_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "heinmach_exclusions.py")
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreSurfaceFix"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed"
# The first reconstruction used USD asset sharing and material-slot merging.
# Keep those assets untouched as a rollback source and import a corrected,
# isolated library for the live reconstructed map.
DESTINATION_ROOT = RECONSTRUCTED_ROOT + "/CorrectedSourceAssets"
STAGE_NAME = "HeinMach_StaticMeshLibrary_Corrected"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
PLACEMENT_PATH = os.path.join(
    unreal.Paths.project_content_dir(),
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_RenderableStaticMeshPlacements.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_StaticMesh_Reconstruction_Corrected.json",
)

MANAGED_LABEL_PREFIX = "HM_Prop_"
MANAGED_FOLDER_ROOT = "HeinMach/Reconstructed/Props"
EXPECTED_PLACEMENT_COUNT = 2665
EXPECTED_MESH_COUNT = 183

ENVIRONMENT_LEVELS = {
    "HeinMach_Chrcollision",
    "HeinMach_Landscape2",
    "HeinMach_Landscape1",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_Blizzard_2",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV07_BG",
    "HeinMach_SubLV05_Escape_1",
}


def load_exclusion_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_exclusions", EXCLUSION_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HeinMach exclusion metadata helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exclusions = load_exclusion_module()
TRANSFORM_OVERRIDES = exclusions.transform_overrides("root_prop")


def log(message):
    unreal.log("KHAZAN_HEINMACH_PROPS: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_PROPS: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required metadata does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create placement backup map: " + BACKUP_MAP_PATH)
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def load_map():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach map: " + MAP_PATH)
    return level_subsystem


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def source_usd_path(package):
    return os.path.join(FMODEL_ROOT, *str(package).split("/")) + ".usda"


def accepted_placements(payload):
    placements = []
    for placement in payload.get("placements", []):
        if placement.get("source_level") not in ENVIRONMENT_LEVELS:
            continue
        if placement.get("visible") is False:
            continue
        if not placement.get("static_mesh_package"):
            continue
        placements.append(placement)
    return placements


def unique_source_packages(placements):
    return sorted({str(item["static_mesh_package"]) for item in placements})


def write_mesh_stage(packages):
    missing = [source_usd_path(package) for package in packages if not os.path.isfile(source_usd_path(package))]
    if missing:
        raise RuntimeError(
            "Missing {} required static-mesh USD files; first: {}".format(
                len(missing), missing[0]
            )
        )

    sublayers = ["        @{}@".format(source_usd_path(package).replace("\\", "/")) for package in packages]
    stage_text = "\n".join(
        [
            "#usda 1.0",
            "(",
            "    metersPerUnit = 0.01",
            '    upAxis = "Z"',
            "    subLayers = [",
            ",\n".join(sublayers),
            "    ]",
            ")",
            "",
        ]
    )
    os.makedirs(os.path.dirname(GENERATED_STAGE_PATH), exist_ok=True)
    with open(GENERATED_STAGE_PATH, "w", encoding="utf-8", newline="\n") as output:
        output.write(stage_text)
    return [source_usd_path(package) for package in packages]


def imported_assets_by_class():
    result = {}
    if not unreal.EditorAssetLibrary.does_directory_exist(DESTINATION_ROOT):
        return result
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        DESTINATION_ROOT, recursive=True, include_folder=False
    ):
        class_name = asset_class_name(asset_path)
        result.setdefault(class_name, []).append(asset_path)
    return result


def normalized_asset_names(asset):
    name = asset.get_name()
    names = {name}
    for prefix in ("SM_", "MI_", "M_"):
        if name.startswith(prefix):
            names.add(name[len(prefix) :])
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


def expected_meshes_present(packages, class_assets):
    static_mesh_index = loaded_asset_index(class_assets.get("StaticMesh", []))
    missing = [package for package in packages if package_basename(package) not in static_mesh_index]
    return static_mesh_index, missing


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
    # Placement metadata resolves meshes by the original package basename.
    # Preserve one asset per named prim even when USD considers geometry identical.
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("prim_path_folder_structure", False)
    # Section indices in FModel's USDA are the authoritative material-slot
    # layout. Merging slots changes that layout and assigns textures to the
    # wrong mesh sections, so it must remain disabled.
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


def managed_label(placement):
    label = "{}{}_{}_{}".format(
        MANAGED_LABEL_PREFIX,
        placement.get("source_level", "Unknown"),
        placement.get("source_object_index", 0),
        placement.get("actor_name", "Actor"),
    )
    return label[:220]


def restoration_exclusion_labels(category="root_prop"):
    return exclusions.exclusion_labels(category)


def filter_excluded_placements(placements):
    excluded = restoration_exclusion_labels("root_prop")
    return [placement for placement in placements if managed_label(placement) not in excluded]


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def spawn_static_mesh_actor(actor_subsystem, mesh, location, rotation):
    try:
        actor = actor_subsystem.spawn_actor_from_object(mesh, location, rotation)
    except Exception:
        actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        if actor:
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_static_mesh(mesh)
    if not actor:
        raise RuntimeError("Failed to spawn static mesh actor for " + mesh.get_name())
    return actor


def place_meshes(placements, static_mesh_index, material_index):
    placements = filter_excluded_placements(placements)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors())
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    created_count = 0
    reused_count = 0
    material_assignment_count = 0
    unresolved_materials = {}

    for index, placement in enumerate(placements, start=1):
        mesh_package = str(placement["static_mesh_package"])
        mesh_name = package_basename(mesh_package)
        mesh = static_mesh_index.get(mesh_name)
        if not mesh:
            raise RuntimeError("Imported static mesh is unresolved: " + mesh_package)

        label = managed_label(placement)
        override = TRANSFORM_OVERRIDES.get(label, {})
        transform = override.get("preserved_transform", placement.get("transform", {}))
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
            "{}/{}".format(MANAGED_FOLDER_ROOT, placement.get("source_level", "Unknown")),
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Placed actor has no StaticMeshComponent: " + label)
        if component.get_editor_property("static_mesh") != mesh:
            component.set_static_mesh(mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        component.set_editor_property("cast_shadow", bool(placement.get("cast_shadow", True)))

        # Reused actors can retain overrides from the legacy imported mesh.
        # Clear them before applying the sparse original override slots.
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            try:
                component.empty_override_materials()
            except Exception:
                pass

        for slot_index, material_package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if not material_package:
                continue
            material_name = package_basename(material_package)
            material = material_index.get(material_name)
            if material:
                component.set_material(slot_index, material)
                material_assignment_count += 1
            else:
                unresolved_materials[material_package] = (
                    unresolved_materials.get(material_package, 0) + 1
                )

        if index % 250 == 0:
            log("Placed {}/{} environment props".format(index, len(placements)))

    final_managed_count = sum(
        actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    )
    return {
        "created_count": created_count,
        "reused_count": reused_count,
        "final_managed_actor_count": final_managed_count,
        "material_assignment_count": material_assignment_count,
        "unresolved_override_materials": [
            {"package": package, "placement_count": count}
            for package, count in sorted(unresolved_materials.items())
        ],
    }


def main():
    placement_payload = load_json(PLACEMENT_PATH)
    source_placements = accepted_placements(placement_payload)
    source_packages = unique_source_packages(source_placements)
    if (
        len(source_placements) != EXPECTED_PLACEMENT_COUNT
        or len(source_packages) != EXPECTED_MESH_COUNT
    ):
        raise RuntimeError(
            "Unexpected environment placement inventory: placements={} meshes={}".format(
                len(source_placements), len(source_packages)
            )
        )
    placements = filter_excluded_placements(source_placements)
    packages = unique_source_packages(placements)

    source_files = write_mesh_stage(packages)
    class_assets_before = imported_assets_by_class()
    static_mesh_index, missing_before = expected_meshes_present(packages, class_assets_before)
    imported_object_paths = []
    if missing_before:
        imported_object_paths = import_mesh_library()

    class_assets_after = imported_assets_by_class()
    static_mesh_index, missing_after = expected_meshes_present(packages, class_assets_after)
    if missing_after:
        raise RuntimeError(
            "USD import did not create {} required static meshes; first: {}".format(
                len(missing_after), missing_after[0]
            )
        )

    material_paths = []
    for class_name in ("Material", "MaterialInstanceConstant"):
        material_paths.extend(class_assets_after.get(class_name, []))
    material_index = loaded_asset_index(material_paths)

    backup_created = backup_map_once()
    level_subsystem = load_map()
    placement_result = place_meshes(placements, static_mesh_index, material_index)
    if placement_result["final_managed_actor_count"] != len(placements):
        raise RuntimeError(
            "Placed actor validation failed: expected {} got {}".format(
                len(placements), placement_result["final_managed_actor_count"]
            )
        )

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save reconstructed HeinMach map")
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "reconstructed",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "generated_stage": GENERATED_STAGE_PATH,
        "source_usd_count": len(source_files),
        "required_static_mesh_count": len(packages),
        "placement_count": len(placements),
        "source_placement_count": len(source_placements),
        "excluded_placement_count": len(source_placements) - len(placements),
        "destination_root": DESTINATION_ROOT,
        "imported_asset_class_counts": {
            class_name: len(paths)
            for class_name, paths in sorted(class_assets_after.items())
        },
        "imported_object_path_count": len(imported_object_paths),
        "placement_result": placement_result,
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} placements={} created={} reused={} report={}".format(
            report["status"],
            len(packages),
            len(placements),
            placement_result["created_count"],
            placement_result["reused_count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "error": str(exception),
            "status": "failed",
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        error(str(exception))
        error(failure["traceback"])
        raise
