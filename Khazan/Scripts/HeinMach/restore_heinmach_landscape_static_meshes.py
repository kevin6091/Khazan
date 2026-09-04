"""Restore the two omitted HeinMach Landscapes as static-mesh terrain proxies.

FModel exported the original Landscape render geometry as 57 component USDA
files (18 + 39).  The earlier root-StaticMesh reconstruction could not see
LandscapeComponent geometry, leaving the walkable ground absent.  Each source
component already stores its absolute section coordinates; after USD axis
conversion it must receive only the original Landscape root transform.

The original layered Landscape materials require weightmap-aware Landscape
shaders and cannot be bound directly to a StaticMesh.  A deterministic
slope-based recovery material is therefore used until the weight layers are
rebuilt.  Fog remains a hard no-edit boundary.
"""

import hashlib
import importlib.util
import json
import math
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXCLUSION_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "heinmach_exclusions.py")
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
FMODEL_LEVEL_ROOT = os.path.join(
    FMODEL_ROOT, "BBQ", "Content", "_Kazan_", "Level", "HeinMach"
)
FMODEL_EXPORT_LEVEL_ROOT = os.path.join(
    FMODEL_ROOT,
    "Exports",
    "BBQ",
    "Content",
    "_Kazan_",
    "Level",
    "HeinMach",
)
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreLandscapeStaticRestore"
)
DESTINATION_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/LandscapeStatic"
)
MATERIAL_PATH = DESTINATION_ROOT + "/Materials/M_HeinMach_Landscape_Recovery"
RECOVERY_MATERIAL_VERSION = 2
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_LandscapeStatic_Restoration.json",
)
MANAGED_LABEL_PREFIX = "HM_Landscape_"
MANAGED_FOLDER_ROOT = "HeinMach/Reconstructed/Landscape"
FOG_LABEL_PREFIX = "HM_FogSheet_"
EXPECTED_COMPONENT_COUNTS = {"Landscape1": 18, "Landscape2": 39}
EXPECTED_TOTAL_COMPONENT_COUNT = 57
EXPECTED_FOG_COUNT = 50
EXPECTED_FOG_SHA256 = "3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48"
BOUND_TOLERANCE = 0.02
TRANSFORM_TOLERANCE = 0.02
LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")


def load_exclusion_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_landscape_exclusions", EXCLUSION_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HeinMach exclusion metadata helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exclusions = load_exclusion_module()


def log(message):
    unreal.log("KHAZAN_HEINMACH_LANDSCAPE: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def local_index(reference):
    path = reference.get("ObjectPath") if isinstance(reference, dict) else None
    match = LOCAL_INDEX_RE.search(str(path)) if path else None
    return int(match.group(1)) if match else None


def source_level_json(level_name):
    return os.path.join(FMODEL_EXPORT_LEVEL_ROOT, level_name + ".json")


def source_component_usd(level_name, landscape_name, component_name):
    return os.path.join(
        FMODEL_LEVEL_ROOT,
        level_name,
        "PersistentLevel",
        landscape_name,
        component_name + ".usda",
    )


def axis_vector(value, defaults):
    value = value if isinstance(value, dict) else {}
    return {
        axis: float(value.get(axis.upper(), default))
        for axis, default in zip(("x", "y", "z"), defaults)
    }


def load_landscape_inventory():
    landscapes = []
    all_components = []
    for suffix in (1, 2):
        level_name = "HeinMach_Landscape{}".format(suffix)
        json_path = source_level_json(level_name)
        if not os.path.isfile(json_path):
            raise RuntimeError("Missing Landscape Properties JSON: " + json_path)
        objects = load_json(json_path)
        landscape_candidates = [
            item
            for item in objects
            if isinstance(item, dict) and item.get("Type") == "Landscape"
        ]
        if len(landscape_candidates) != 1:
            raise RuntimeError("Expected one Landscape actor in " + level_name)
        actor = landscape_candidates[0]
        properties = actor.get("Properties", {})
        landscape_name = str(actor.get("Name"))
        root_index = local_index(properties.get("RootComponent"))
        if root_index is None or not (0 <= root_index < len(objects)):
            raise RuntimeError("Landscape root reference is invalid: " + level_name)
        root_properties = objects[root_index].get("Properties", {}) or {}
        root_transform = {
            "location_cm": axis_vector(
                root_properties.get("RelativeLocation"), (0.0, 0.0, 0.0)
            ),
            "rotation_degrees": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "scale": axis_vector(
                root_properties.get("RelativeScale3D"), (1.0, 1.0, 1.0)
            ),
        }
        components = []
        for reference in properties.get("LandscapeComponents", []):
            object_index = local_index(reference)
            if object_index is None or not (0 <= object_index < len(objects)):
                raise RuntimeError("Landscape component reference is invalid")
            component = objects[object_index]
            component_properties = component.get("Properties", {}) or {}
            component_name = str(component.get("Name"))
            cached_box = component_properties.get("CachedLocalBox", {}) or {}
            # FModel omits serialized zero-valued fields on several Landscape2
            # edge components.  Missing SectionBase axes are therefore zero.
            section_x = int(component_properties.get("SectionBaseX", 0))
            section_y = int(component_properties.get("SectionBaseY", 0))
            source_path = source_component_usd(
                level_name, landscape_name, component_name
            )
            if not os.path.isfile(source_path):
                raise RuntimeError("Missing Landscape component USDA: " + source_path)
            component_record = {
                "source_level": level_name,
                "landscape_name": landscape_name,
                "component_name": component_name,
                "source_object_index": object_index,
                "source_usd": source_path,
                "source_usd_bytes": os.path.getsize(source_path),
                "section_base": {"x": section_x, "y": section_y},
                "component_size_quads": int(
                    component_properties.get("ComponentSizeQuads", 63)
                ),
                "cached_local_box": {
                    "min": axis_vector(cached_box.get("Min"), (0.0, 0.0, 0.0)),
                    "max": axis_vector(cached_box.get("Max"), (63.0, 63.0, 0.0)),
                },
                "heightmap_texture": (
                    component_properties.get("HeightmapTexture", {}) or {}
                ).get("ObjectPath"),
                "weightmap_texture_count": len(
                    component_properties.get("WeightmapTextures", []) or []
                ),
                "weightmap_layer_count": len(
                    component_properties.get("WeightmapLayerAllocations", []) or []
                ),
                "root_transform": root_transform,
            }
            components.append(component_record)
            all_components.append(component_record)
        expected_count = EXPECTED_COMPONENT_COUNTS[landscape_name]
        if len(components) != expected_count:
            raise RuntimeError(
                "Landscape component count changed for {}: {} != {}".format(
                    landscape_name, len(components), expected_count
                )
            )
        landscapes.append(
            {
                "source_level": level_name,
                "landscape_name": landscape_name,
                "source_json": json_path,
                "source_material_package": (
                    properties.get("LandscapeMaterial", {}) or {}
                ).get("ObjectPath"),
                "component_count": len(components),
                "component_size_quads": int(properties.get("ComponentSizeQuads", 63)),
                "root_transform": root_transform,
            }
        )
    if len(all_components) != EXPECTED_TOTAL_COMPONENT_COUNT:
        raise RuntimeError("Total Landscape component inventory changed")
    return landscapes, all_components


def destination_component_root(record):
    return "{}/{}/{}".format(
        DESTINATION_ROOT, record["landscape_name"], record["component_name"]
    )


def asset_class_name(path):
    data = unreal.EditorAssetLibrary.find_asset_data(path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        return "Invalid"


def component_mesh(record):
    root = destination_component_root(record)
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return None
    paths = [
        path
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        )
        if asset_class_name(path) == "StaticMesh"
    ]
    if len(paths) > 1:
        raise RuntimeError("Multiple StaticMeshes in Landscape component folder: " + root)
    return unreal.EditorAssetLibrary.load_asset(paths[0]) if paths else None


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
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)
    return options


def import_missing(records):
    missing = [record for record in records if not component_mesh(record)]
    if not missing:
        return {"missing_before": 0, "imported_path_count": 0}
    tasks = []
    for record in missing:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", record["source_usd"])
        task.set_editor_property(
            "destination_path",
            "{}/{}".format(DESTINATION_ROOT, record["landscape_name"]),
        )
        task.set_editor_property("destination_name", record["component_name"])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("options", landscape_import_options())
        task.set_editor_property("factory", unreal.UsdStageImportFactory())
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    imported_paths = [path for task in tasks for path in task.imported_object_paths]
    unresolved = [record for record in records if not component_mesh(record)]
    if unresolved:
        raise RuntimeError(
            "Landscape USD import left a component unresolved: "
            + unresolved[0]["component_name"]
        )
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )
    return {
        "missing_before": len(missing),
        "imported_path_count": len(imported_paths),
    }


def prepare_assets(landscape_name=None):
    _landscapes, records = load_landscape_inventory()
    if landscape_name:
        records = [
            record for record in records if record["landscape_name"] == landscape_name
        ]
    result = import_missing(records)
    log("PREPARED {} {}".format(landscape_name or "all", result))
    return result


def create_recovery_material():
    material = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
    created = False
    if not material:
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = asset_tools.create_asset(
            "M_HeinMach_Landscape_Recovery",
            DESTINATION_ROOT + "/Materials",
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
        if not material:
            raise RuntimeError("Failed to create Landscape recovery material")
        created = True
    material_version = unreal.EditorAssetLibrary.get_metadata_tag(
        material, "KhazanLandscapeRecoveryVersion"
    )
    if (
        created
        or unreal.MaterialEditingLibrary.get_num_material_expressions(material) == 0
        or material_version != str(RECOVERY_MATERIAL_VERSION)
    ):
        library = unreal.MaterialEditingLibrary
        material.modify()
        library.delete_all_material_expressions(material)
        rock = library.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -700, -100
        )
        rock.set_editor_property("constant", unreal.LinearColor(0.045, 0.055, 0.065, 1.0))
        snow = library.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -700, 100
        )
        snow.set_editor_property("constant", unreal.LinearColor(0.30, 0.34, 0.38, 1.0))
        pixel_normal = library.create_material_expression(
            material, unreal.MaterialExpressionPixelNormalWS, -700, 300
        )
        up_vector = library.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -700, 430
        )
        up_vector.set_editor_property("constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
        slope_dot = library.create_material_expression(
            material, unreal.MaterialExpressionDotProduct, -420, 300
        )
        blend = library.create_material_expression(
            material, unreal.MaterialExpressionLinearInterpolate, -150, 50
        )
        roughness = library.create_material_expression(
            material, unreal.MaterialExpressionConstant, -150, 260
        )
        roughness.set_editor_property("r", 0.92)
        if not library.connect_material_expressions(pixel_normal, "", slope_dot, "A"):
            raise RuntimeError("Failed to connect landscape PixelNormalWS to slope dot")
        if not library.connect_material_expressions(up_vector, "", slope_dot, "B"):
            raise RuntimeError("Failed to connect landscape up vector to slope dot")
        library.connect_material_expressions(rock, "", blend, "A")
        library.connect_material_expressions(snow, "", blend, "B")
        if not library.connect_material_expressions(slope_dot, "", blend, "Alpha"):
            raise RuntimeError("Failed to connect landscape slope dot to blend alpha")
        library.connect_material_property(
            blend, "", unreal.MaterialProperty.MP_BASE_COLOR
        )
        library.connect_material_property(
            roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
        )
        material.set_editor_property("two_sided", False)
        library.layout_material_expressions(material)
        library.recompile_material(material)
        unreal.EditorAssetLibrary.set_metadata_tag(
            material,
            "KhazanLandscapeRecoveryVersion",
            str(RECOVERY_MATERIAL_VERSION),
        )
        unreal.EditorAssetLibrary.save_asset(MATERIAL_PATH, only_if_is_dirty=False)
    return material, created


def actor_transform_record(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "label": actor.get_actor_label(),
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": [scale.x, scale.y, scale.z],
    }


def fog_signature(actor_subsystem):
    records = sorted(
        (
            actor_transform_record(actor)
            for actor in actor_subsystem.get_all_level_actors()
            if actor and actor.get_actor_label().startswith(FOG_LABEL_PREFIX)
        ),
        key=lambda item: item["label"],
    )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def managed_label(record):
    return "{}{}_{}".format(
        MANAGED_LABEL_PREFIX, record["landscape_name"], record["component_name"]
    )


def filter_excluded_records(records):
    excluded = exclusions.exclusion_labels("landscape_static")
    return [record for record in records if managed_label(record) not in excluded]


def vector(value):
    return unreal.Vector(x=value["x"], y=value["y"], z=value["z"])


def set_actor_folder(actor, path):
    try:
        actor.set_folder_path(path)
    except Exception:
        actor.set_editor_property("folder_path", path)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create pre-Landscape backup map")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def close_enough(actual, expected, tolerance=BOUND_TOLERANCE):
    return abs(float(actual) - float(expected)) <= tolerance


def validate_mesh_bound(record, mesh):
    bounds = mesh.get_bounding_box()
    local_box = record["cached_local_box"]
    section = record["section_base"]
    expected_min = (
        section["x"] + local_box["min"]["x"],
        section["y"] + local_box["min"]["y"],
        local_box["min"]["z"],
    )
    expected_max = (
        section["x"] + local_box["max"]["x"],
        section["y"] + local_box["max"]["y"],
        local_box["max"]["z"],
    )
    actual_min = (bounds.min.x, bounds.min.y, bounds.min.z)
    actual_max = (bounds.max.x, bounds.max.y, bounds.max.z)
    valid = all(
        close_enough(actual, expected)
        for actual, expected in zip(actual_min + actual_max, expected_min + expected_max)
    )
    return valid, {
        "actual_min": list(actual_min),
        "actual_max": list(actual_max),
        "expected_min": list(expected_min),
        "expected_max": list(expected_max),
    }


def configure_collision(mesh):
    body_setup = mesh.get_editor_property("body_setup")
    if not body_setup:
        return False
    body_setup.set_editor_property(
        "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    )
    mesh.modify()
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
    return True


def place_components(records, material):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    expected_labels = {managed_label(record) for record in records}
    unexpected = sorted(set(existing) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected managed Landscape actor: " + unexpected[0])
    created = 0
    reused = 0
    collision_configured = 0
    bound_records = []
    for record in records:
        mesh = component_mesh(record)
        if not mesh:
            raise RuntimeError("Landscape mesh is unresolved: " + record["component_name"])
        valid_bound, bound_record = validate_mesh_bound(record, mesh)
        if not valid_bound:
            raise RuntimeError(
                "Landscape component bound mismatch: " + record["component_name"]
            )
        bound_record.update(
            {
                "landscape_name": record["landscape_name"],
                "component_name": record["component_name"],
                "mesh_asset": mesh.get_path_name(),
            }
        )
        bound_records.append(bound_record)
        if configure_collision(mesh):
            collision_configured += 1

        transform = record["root_transform"]
        label = managed_label(record)
        actor = existing.get(label)
        if actor:
            reused += 1
        else:
            actor = actor_subsystem.spawn_actor_from_object(
                mesh,
                vector(transform["location_cm"]),
                unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
            )
            if not actor:
                raise RuntimeError("Failed to spawn Landscape component: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            existing[label] = actor
            created += 1
        actor.set_actor_location(vector(transform["location_cm"]), False, False)
        actor.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), False)
        actor.set_actor_scale3d(vector(transform["scale"]))
        set_actor_folder(
            actor, "{}/{}".format(MANAGED_FOLDER_ROOT, record["landscape_name"])
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component.get_editor_property("static_mesh") != mesh:
            component.set_static_mesh(mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        component.set_editor_property("cast_shadow", False)
        component.set_editor_property("reverse_culling", False)
        component.set_collision_profile_name("BlockAll")
        component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        component.set_material(0, material)

    final = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    if set(final) != expected_labels:
        raise RuntimeError("Final managed Landscape actor set is incomplete")
    return actor_subsystem, final, bound_records, {
        "created_count": created,
        "reused_count": reused,
        "final_managed_actor_count": len(final),
        "collision_complex_as_simple_mesh_count": collision_configured,
        "final_total_actor_count": len(actor_subsystem.get_all_level_actors()),
    }


def validate_placements(records, actors, material):
    failures = []
    for record in records:
        label = managed_label(record)
        actor = actors[label]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        transform = record["root_transform"]
        expected_location = transform["location_cm"]
        expected_scale = transform["scale"]
        location = actor.get_actor_location()
        scale = actor.get_actor_scale3d()
        issues = []
        if any(
            not close_enough(actual, expected, TRANSFORM_TOLERANCE)
            for actual, expected in zip(
                (location.x, location.y, location.z),
                (expected_location["x"], expected_location["y"], expected_location["z"]),
            )
        ):
            issues.append("location")
        if any(
            not close_enough(actual, expected, TRANSFORM_TOLERANCE)
            for actual, expected in zip(
                (scale.x, scale.y, scale.z),
                (expected_scale["x"], expected_scale["y"], expected_scale["z"]),
            )
        ):
            issues.append("scale")
        if not component or component.get_editor_property("static_mesh") != component_mesh(record):
            issues.append("mesh")
        if component and component.get_material(0) != material:
            issues.append("material")
        if component and component.get_editor_property("reverse_culling"):
            issues.append("reverse_culling")
        if component and component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION:
            issues.append("collision_disabled")
        if issues:
            failures.append({"label": label, "issues": issues})
    return failures


def main():
    landscapes, source_records = load_landscape_inventory()
    records = filter_excluded_records(source_records)
    import_result = import_missing(records)
    material, material_created = create_recovery_material()

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fog_before = fog_signature(actor_subsystem)
    expected_fog = {"count": EXPECTED_FOG_COUNT, "sha256": EXPECTED_FOG_SHA256}
    if fog_before != expected_fog:
        raise RuntimeError("Fog boundary differs before Landscape restoration")
    backup_created = backup_map_once()
    actor_subsystem, actors, bound_records, placement = place_components(
        records, material
    )
    placement_failures = validate_placements(records, actors, material)
    if placement_failures:
        raise RuntimeError(
            "Landscape placement validation failed: " + str(placement_failures[0])
        )
    fog_after = fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError("Fog boundary changed during Landscape restoration")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save Landscape-restored HeinMach map")
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_landscapes": landscapes,
        "source_component_count": len(source_records),
        "active_component_count": len(records),
        "excluded_component_count": len(source_records) - len(records),
        "source_usd_total_bytes": sum(
            record["source_usd_bytes"] for record in source_records
        ),
        "import_result": import_result,
        "recovery_material": {
            "asset_path": material.get_path_name(),
            "created": material_created,
            "policy": (
                "Slope-based rock/snow proxy. Original WLM_HeinMach/WLM_HeinMach2 "
                "weightmap layer reconstruction remains a separate material pass."
            ),
        },
        "placement_result": placement,
        "component_asset_bounds": bound_records,
        "placement_validation_failure_count": len(placement_failures),
        "fog_boundary": {"status": "unchanged", "before": fog_before, "after": fog_after},
        "coordinate_policy": (
            "Component USDA vertices already contain SectionBase coordinates and "
            "USD import converts Y to UE space; apply only the original Landscape "
            "root location/rotation/scale."
        ),
        "excluded_content": [
            "Managed FogSheet actors and Fog materials",
            "Landscape foliage already restored by the dedicated foliage pass",
            "RuntimeVirtualTexture and VirtualHeightfieldMesh actors",
            "All HeinMach_Cine_* layers",
            "Barehanded staggering movement scene",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} components={} created={} reused={} imported={} fog={} report={}".format(
            report["status"],
            len(records),
            placement["created_count"],
            placement["reused_count"],
            import_result["imported_path_count"],
            fog_after["count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {"status": "failed", "error": str(exception), "traceback": traceback.format_exc()},
        )
        unreal.log_error("KHAZAN_HEINMACH_LANDSCAPE: " + str(exception))
        raise
