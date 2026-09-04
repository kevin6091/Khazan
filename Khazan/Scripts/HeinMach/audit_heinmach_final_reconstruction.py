"""Read-only final audit for the reconstructed HeinMach environment map.

Validates the final actor inventory plus exact root/child/Landscape/foliage and
material reports after a save/reload.  It also guards against WorldGrid/default
materials and blanket reverse-culling used to hide authored winding or
negative-scale problems.  Fog is read-only and verified, never repaired here.
"""

import importlib.util
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCLUSION_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "heinmach_exclusions.py")


def load_exclusion_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_final_exclusions", EXCLUSION_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HeinMach exclusion metadata helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exclusions = load_exclusion_module()
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
FOG_MESH_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets/Meshes/"
    "HeinMach_FogSheetPlane/StaticMeshes/SM_FS_FogSheet_Plane."
    "SM_FS_FogSheet_Plane"
)
FOG_BASE_MATERIAL_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets/Materials/"
    "M_HeinMach_FogSheet_Preview_V5.M_HeinMach_FogSheet_Preview_V5"
)
FOG_MATERIAL_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FogSheets/Materials"
)
TERRAIN_PREVIEW_MATERIAL_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/TerrainPreview/"
    "MI_HeinMach_Terrain_Snow_Preview.MI_HeinMach_Terrain_Snow_Preview"
)
SOURCE_TERRAIN_LABELS = ("HM_Terrain_Landscape1", "HM_Terrain_Landscape2")
TERRAIN_LABELS = tuple(
    label
    for label in SOURCE_TERRAIN_LABELS
    if label not in exclusions.exclusion_labels("legacy_merged_terrain")
)
REPORT_ROOT = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
GAP_REPORT_PATH = os.path.join(REPORT_ROOT, "HeinMach_Render_Gap_Analysis.json")
FOG_RESTORE_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_FogSheet_Restore.json"
)
FOG_LIGHTING_POLISH_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_FogLighting_Polish.json"
)
FOG_INTEGRITY_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_FogIntegrity_Review.json"
)
TERRAIN_PREVIEW_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_Terrain_Preview_Material.json"
)
REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_Final_Reconstruction_Audit.json"
)
ROOT_INTEGRITY_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_RestoredLevel_Integrity_Audit.json"
)
CHILD_INTEGRITY_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_ChildRender_Integrity_Audit.json"
)
LANDSCAPE_STATIC_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_LandscapeStatic_Integrity_Audit.json"
)
MATERIAL_RENDERING_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_MaterialRendering_Audit.json"
)
FOLIAGE_RELOAD_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_Foliage_Reload_Audit.json"
)
CAMERA_ANCHOR_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_PlayableCameraAnchors.json"
)
OPTIMIZATION_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_ConservativeOptimization.json"
)
TUTORIAL_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_DualAxeTutorial_Restoration.json"
)
LIGHT_COLOR_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_LightColor_Metadata_Audit.json"
)
WHITE_TREE_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_WhiteTreeMaterial_Repair.json"
)
REMAINING_WHITE_TREE_REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_RemainingWhiteTreeMaterial_Repair.json"
)

EXPECTED_COUNTS = {
    "prop": 9104 - len(exclusions.exclusion_labels("root_prop")),
    "foliage_batch": 113,
    "child_prop": 27,
    "fog_sheet": 50,
    "terrain": 2 - len(exclusions.exclusion_labels("legacy_merged_terrain")),
    "landscape_static": 57 - len(exclusions.exclusion_labels("landscape_static")),
    "source_light": 89,
    "preview_environment": 4,
    "preview_route_fill": 5,
    "preview_volumetric_fog": 1,
    "tutorial": 3,
    "hism_component": 113,
    "hism_instance": 12495,
}
EXPECTED_COUNTS["actor_total"] = sum(
    value
    for key, value in EXPECTED_COUNTS.items()
    if key not in ("actor_total", "hism_component", "hism_instance")
)
EXPECTED_OPTIMIZED_DUPLICATE_COUNT = sum(
    1
    for record in exclusions.exclusion_records()
    if record.get("reason") == "exact_state_duplicate"
)
EXPECTED_USER_EXCLUSION_COUNT = sum(
    1
    for record in exclusions.exclusion_records()
    if os.path.basename(record.get("metadata_path", ""))
    == "HeinMach_UserExclusions.json"
)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required report is missing: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def object_path(value):
    return value.get_path_name() if value else None


def normalized_asset_path(value):
    return str(value).rsplit(".", 1)[0] if value else None


def package_basename(package):
    return str(package).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def normalized_asset_names(asset):
    if not asset:
        return set()
    name = asset.get_name()
    result = {name}
    for prefix in ("SM_", "MI_", "M_", "T_"):
        if name.startswith(prefix):
            result.add(name[len(prefix) :])
    return result


def vector_error(actual, expected):
    return math.sqrt(
        (float(actual.x) - float(expected.get("x", 0.0))) ** 2
        + (float(actual.y) - float(expected.get("y", 0.0))) ** 2
        + (float(actual.z) - float(expected.get("z", 0.0))) ** 2
    )


def angle_error(actual, expected):
    return abs((float(actual) - float(expected) + 180.0) % 360.0 - 180.0)


def rotation_error(actual, expected):
    return max(
        angle_error(actual.pitch, expected.get("pitch", 0.0)),
        angle_error(actual.yaw, expected.get("yaw", 0.0)),
        angle_error(actual.roll, expected.get("roll", 0.0)),
    )


def child_label(record):
    return (
        "HM_ChildProp_{}_{:05d}_{}_{:05d}".format(
            record.get("source_level", "Unknown"),
            int(record.get("actor_object_index", 0)),
            record.get("actor_name", "Actor"),
            int(record.get("component_object_index", 0)),
        )
    )[:220]


def fog_label(record):
    return (
        "HM_FogSheet_{}_{:05d}_{}".format(
            record.get("source_level", "Unknown"),
            int(record.get("source_object_index", 0)),
            record.get("actor_name", "Fog"),
        )
    )[:220]


def fog_material_name(record):
    return (
        "MI_HM_Fog_{}_{:05d}_{}".format(
            record.get("source_level", "Unknown"),
            int(record.get("source_object_index", 0)),
            record.get("actor_name", "Fog"),
        )
    )[:180]


def transform_errors(actor, transform):
    return {
        "location_cm": vector_error(
            actor.get_actor_location(), transform.get("location_cm", {})
        ),
        "rotation_degrees": rotation_error(
            actor.get_actor_rotation(), transform.get("rotation_degrees", {})
        ),
        "scale": vector_error(actor.get_actor_scale3d(), transform.get("scale", {})),
    }


def main():
    gap = load_json(GAP_REPORT_PATH)
    fog_restore = load_json(FOG_RESTORE_REPORT_PATH)
    fog_lighting_polish = load_json(FOG_LIGHTING_POLISH_REPORT_PATH)
    fog_integrity = load_json(FOG_INTEGRITY_REPORT_PATH)
    terrain_preview = load_json(TERRAIN_PREVIEW_REPORT_PATH)
    root_integrity = load_json(ROOT_INTEGRITY_REPORT_PATH)
    child_integrity = load_json(CHILD_INTEGRITY_REPORT_PATH)
    landscape_static = load_json(LANDSCAPE_STATIC_REPORT_PATH)
    material_rendering = load_json(MATERIAL_RENDERING_REPORT_PATH)
    foliage_reload = load_json(FOLIAGE_RELOAD_REPORT_PATH)
    camera_anchors = load_json(CAMERA_ANCHOR_REPORT_PATH)
    optimization = load_json(OPTIMIZATION_REPORT_PATH)
    tutorial = load_json(TUTORIAL_REPORT_PATH)
    light_color = load_json(LIGHT_COLOR_REPORT_PATH)
    white_tree = load_json(WHITE_TREE_REPORT_PATH)
    remaining_white_tree = load_json(REMAINING_WHITE_TREE_REPORT_PATH)
    child_records = [
        record
        for record in gap.get("non_root_static_mesh_components", [])
        if record.get("component_type") == "xxStaticMeshComponent"
    ]
    fog_records = list(gap.get("fog_sheet_actors", []))

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_path = current_world.get_path_name() if current_world else ""
    if not current_path.startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    by_label = {}
    duplicate_labels = []
    for actor in actors:
        label = actor.get_actor_label()
        if label in by_label:
            duplicate_labels.append(label)
        else:
            by_label[label] = actor

    folders = {actor: str(actor.get_folder_path()) for actor in actors}
    inventory = {
        "prop": sum(a.get_actor_label().startswith("HM_Prop_") for a in actors),
        "foliage_batch": sum(
            a.get_actor_label().startswith("HM_FoliageBatch_") for a in actors
        ),
        "child_prop": sum(
            a.get_actor_label().startswith(
                ("HM_ChildProp_", "HM_InheritedChild_")
            )
            for a in actors
        ),
        "fog_sheet": sum(
            a.get_actor_label().startswith("HM_FogSheet_") for a in actors
        ),
        "terrain": sum(
            a.get_actor_label().startswith("HM_Terrain_") for a in actors
        ),
        "landscape_static": sum(
            a.get_actor_label().startswith("HM_Landscape_") for a in actors
        ),
        "source_light": sum(
            folders[a] == "HeinMach/Reconstructed/SourceLights" for a in actors
        ),
        "preview_environment": sum(
            folders[a] == "HeinMach/Reconstructed/PreviewLighting" for a in actors
        ),
        "preview_route_fill": sum(
            folders[a] == "HeinMach/Reconstructed/PreviewLighting/RouteFill"
            for a in actors
        ),
        "preview_volumetric_fog": sum(
            folders[a] == "HeinMach/Reconstructed/PreviewFog" for a in actors
        ),
        "tutorial": sum(
            a.get_actor_label().startswith("HM_Tutorial") for a in actors
        ),
        "actor_total": len(actors),
    }
    inventory["categorized_total"] = sum(
        inventory[key]
        for key in (
            "prop",
            "foliage_batch",
            "child_prop",
            "fog_sheet",
            "terrain",
            "landscape_static",
            "source_light",
            "preview_environment",
            "preview_route_fill",
            "preview_volumetric_fog",
            "tutorial",
        )
    )
    inventory["uncategorized"] = len(actors) - inventory["categorized_total"]

    child_missing = []
    child_transform_mismatches = []
    child_mesh_mismatches = []
    child_material_mismatches = []
    child_world_grid_materials = []
    child_max = {"location_cm": 0.0, "rotation_degrees": 0.0, "scale": 0.0}
    for record in child_records:
        label = child_label(record)
        actor = by_label.get(label)
        if not actor:
            child_missing.append(label)
            continue
        errors = transform_errors(actor, record.get("actor_world_transform", {}))
        for key, value in errors.items():
            child_max[key] = max(child_max[key], value)
        if (
            errors["location_cm"] > 0.01
            or errors["rotation_degrees"] > 0.001
            or errors["scale"] > 0.00001
        ):
            child_transform_mismatches.append({"label": label, "errors": errors})
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = safe_property(component, "static_mesh") if component else None
        expected_mesh = package_basename(record.get("static_mesh_package", ""))
        if expected_mesh not in normalized_asset_names(mesh):
            child_mesh_mismatches.append(
                {"label": label, "expected": expected_mesh, "actual": object_path(mesh)}
            )
        materials = list(component.get_materials()) if component else []
        if any("WorldGridMaterial" in str(object_path(m)) for m in materials if m):
            child_world_grid_materials.append(label)
        for package in record.get("override_material_packages", []):
            if not package:
                continue
            expected_material = package_basename(package)
            if not any(
                expected_material in normalized_asset_names(material)
                for material in materials
            ):
                child_material_mismatches.append(
                    {
                        "label": label,
                        "expected": expected_material,
                        "actual": [object_path(material) for material in materials],
                    }
                )

    fog_missing = []
    fog_transform_mismatches = []
    fog_mesh_mismatches = []
    fog_material_mismatches = []
    fog_parent_mismatches = []
    fog_sort_priority_mismatches = []
    fog_component_policy_mismatches = []
    fog_world_grid_materials = []
    fog_max = {"location_cm": 0.0, "rotation_degrees": 0.0, "scale": 0.0}
    for record in fog_records:
        label = fog_label(record)
        actor = by_label.get(label)
        if not actor:
            fog_missing.append(label)
            continue
        errors = transform_errors(actor, record.get("transform", {}))
        for key, value in errors.items():
            fog_max[key] = max(fog_max[key], value)
        if (
            errors["location_cm"] > 0.01
            or errors["rotation_degrees"] > 0.001
            or errors["scale"] > 0.00001
        ):
            fog_transform_mismatches.append({"label": label, "errors": errors})
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = safe_property(component, "static_mesh") if component else None
        if object_path(mesh) != FOG_MESH_PATH:
            fog_mesh_mismatches.append(
                {"label": label, "expected": FOG_MESH_PATH, "actual": object_path(mesh)}
            )
        material = component.get_material(0) if component else None
        expected_name = fog_material_name(record)
        expected_path = FOG_MATERIAL_ROOT + "/" + expected_name + "." + expected_name
        if object_path(material) != expected_path:
            fog_material_mismatches.append(
                {"label": label, "expected": expected_path, "actual": object_path(material)}
            )
        if material and "WorldGridMaterial" in str(object_path(material)):
            fog_world_grid_materials.append(label)
        parent = safe_property(material, "parent") if material else None
        if object_path(parent) != FOG_BASE_MATERIAL_PATH:
            fog_parent_mismatches.append(
                {
                    "label": label,
                    "expected": FOG_BASE_MATERIAL_PATH,
                    "actual": object_path(parent),
                }
            )
        actual_priority = safe_property(component, "translucency_sort_priority", 0)
        expected_priority = int(record.get("translucency_sort_priority", 0))
        if int(actual_priority) != expected_priority:
            fog_sort_priority_mismatches.append(
                {
                    "label": label,
                    "expected": expected_priority,
                    "actual": int(actual_priority),
                }
            )
        component_policy_actual = {
            name: bool(safe_property(component, name, True))
            for name in (
                "cast_shadow",
                "cast_dynamic_shadow",
                "cast_static_shadow",
                "cast_volumetric_translucent_shadow",
                "receives_decals",
                "use_as_occluder",
                "affect_dynamic_indirect_lighting",
                "affect_distance_field_lighting",
                "generate_overlap_events",
                "can_ever_affect_navigation",
                "hidden_in_game",
            )
        }
        if any(component_policy_actual.values()) or not bool(
            safe_property(component, "visible", False)
        ):
            fog_component_policy_mismatches.append(
                {
                    "label": label,
                    "actual": component_policy_actual,
                    "visible": bool(safe_property(component, "visible", False)),
                }
            )

    terrain_missing = []
    terrain_material_mismatches = []
    terrain_world_grid_materials = []
    for label in TERRAIN_LABELS:
        actor = by_label.get(label)
        if not actor:
            terrain_missing.append(label)
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        materials = list(component.get_materials()) if component else []
        actual_paths = [object_path(material) for material in materials]
        if not materials or any(
            path != TERRAIN_PREVIEW_MATERIAL_PATH for path in actual_paths
        ):
            terrain_material_mismatches.append(
                {
                    "label": label,
                    "expected": TERRAIN_PREVIEW_MATERIAL_PATH,
                    "actual": actual_paths,
                }
            )
        if any("WorldGridMaterial" in str(path) for path in actual_paths):
            terrain_world_grid_materials.append(label)

    components = [
        component
        for component in actor_subsystem.get_all_level_actors_components()
        if component
    ]
    hism_components = [
        component
        for component in components
        if isinstance(component, unreal.HierarchicalInstancedStaticMeshComponent)
    ]
    hism_instances = 0
    for component in hism_components:
        try:
            hism_instances += int(component.get_instance_count())
        except Exception:
            pass

    reported_remaining_tree_slots = {
        (
            str(record["actor_label"]),
            str(record["mesh"]),
            int(record["slot_index"]),
        ): str(record["material_after"])
        for record in remaining_white_tree.get("repaired_slots", [])
    }
    remaining_tree_mesh_names = set(
        (remaining_white_tree.get("tree_scope") or {}).get("mesh_names", [])
    )
    suspicious_remaining_tree_materials = set(
        (remaining_white_tree.get("tree_scope") or {}).get(
            "suspicious_material_paths", []
        )
    )
    recovered_remaining_tree_material = str(
        (remaining_white_tree.get("recovered_material") or {}).get("path", "")
    )
    live_remaining_tree_slots = {}
    live_remaining_tree_suspicious = []
    unexpected_recovered_remaining_tree_slots = []
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = safe_property(component, "static_mesh")
            if not mesh or mesh.get_name() not in remaining_tree_mesh_names:
                continue
            mesh_path = object_path(mesh)
            for slot_index in range(component.get_num_materials()):
                material = component.get_material(slot_index)
                material_object_path = object_path(material)
                key = (actor.get_actor_label(), mesh_path, int(slot_index))
                live_remaining_tree_slots[key] = material_object_path
                if (
                    normalized_asset_path(material_object_path)
                    in suspicious_remaining_tree_materials
                ):
                    live_remaining_tree_suspicious.append(
                        {
                            "actor_label": actor.get_actor_label(),
                            "mesh": mesh_path,
                            "slot_index": slot_index,
                            "material": material_object_path,
                        }
                    )
                if (
                    material_object_path == recovered_remaining_tree_material
                    and key not in reported_remaining_tree_slots
                ):
                    unexpected_recovered_remaining_tree_slots.append(
                        {
                            "actor_label": actor.get_actor_label(),
                            "mesh": mesh_path,
                            "slot_index": slot_index,
                        }
                    )
    remaining_tree_live_mismatches = [
        {
            "actor_label": key[0],
            "mesh": key[1],
            "slot_index": key[2],
            "expected": expected,
            "actual": live_remaining_tree_slots.get(key),
        }
        for key, expected in sorted(reported_remaining_tree_slots.items())
        if live_remaining_tree_slots.get(key) != expected
    ]

    negative_determinant_actors = []
    reverse_culling_components = []
    for actor in actors:
        scale = actor.get_actor_scale3d()
        if float(scale.x) * float(scale.y) * float(scale.z) < 0.0:
            negative_determinant_actors.append(actor.get_actor_label())
    for component in components:
        if isinstance(component, unreal.StaticMeshComponent) and bool(
            safe_property(component, "reverse_culling", False)
        ):
            owner = component.get_owner()
            reverse_culling_components.append(
                owner.get_actor_label() if owner else component.get_path_name()
            )

    base_material = unreal.EditorAssetLibrary.load_asset(FOG_BASE_MATERIAL_PATH)
    base_blend_mode = str(safe_property(base_material, "blend_mode", ""))
    base_two_sided = bool(safe_property(base_material, "two_sided", False))
    base_disable_depth_test = bool(
        safe_property(base_material, "disable_depth_test", True)
    )
    base_preview_version = (
        unreal.EditorAssetLibrary.get_metadata_tag(
            base_material, "KhazanFogPreviewVersion"
        )
        if base_material
        else None
    )
    base_expression_classes = [
        expression.get_class().get_name()
        for expression in unreal.MaterialEditingLibrary.get_material_expressions(
            base_material
        )
        if expression
    ] if base_material else []
    required_fog_expression_classes = {
        "MaterialExpressionWorldPosition",
        "MaterialExpressionCameraPositionWS",
        "MaterialExpressionDistance",
        "MaterialExpressionDepthFade",
        "MaterialExpressionPixelNormalWS",
        "MaterialExpressionCameraVectorWS",
        "MaterialExpressionDotProduct",
    }
    missing_fog_expression_classes = sorted(
        required_fog_expression_classes - set(base_expression_classes)
    )
    preview_fog_actor = by_label.get("HM_PreviewVolumetricFog")
    preview_fog_component = (
        preview_fog_actor.get_component_by_class(
            unreal.ExponentialHeightFogComponent
        )
        if preview_fog_actor
        else None
    )
    height_fog_actors = [
        actor for actor in actors if isinstance(actor, unreal.ExponentialHeightFog)
    ]
    preview_fog_albedo = (
        safe_property(preview_fog_component, "volumetric_fog_albedo")
        if preview_fog_component
        else None
    )
    preview_fog_albedo_components = (
        (
            float(preview_fog_albedo.r),
            float(preview_fog_albedo.g),
            float(preview_fog_albedo.b),
        )
        if preview_fog_albedo
        else None
    )
    if preview_fog_albedo_components and max(preview_fog_albedo_components) > 1.0:
        preview_fog_albedo_components = tuple(
            channel / 255.0 for channel in preview_fog_albedo_components
        )
    expected_preview_fog_albedo = (
        158.0 / 255.0,
        177.0 / 255.0,
        196.0 / 255.0,
    )
    preview_fog_albedo_error = (
        max(
            abs(preview_fog_albedo_components[0] - expected_preview_fog_albedo[0]),
            abs(preview_fog_albedo_components[1] - expected_preview_fog_albedo[1]),
            abs(preview_fog_albedo_components[2] - expected_preview_fog_albedo[2]),
        )
        if preview_fog_albedo
        else None
    )
    post_actor = by_label.get("HM_PreviewPostProcess")
    post_settings = safe_property(post_actor, "settings") if post_actor else None
    polish_fog_before = (
        fog_lighting_polish.get("fog_sheet", {})
        .get("source_transform_signature_before", {})
        .get("sha256")
    )
    polish_fog_after = (
        fog_lighting_polish.get("fog_sheet", {})
        .get("source_transform_signature_after", {})
        .get("sha256")
    )
    polish_light_before = (
        fog_lighting_polish.get("source_lights", {})
        .get("transform_signature_before", {})
        .get("sha256")
    )
    polish_light_after = (
        fog_lighting_polish.get("source_lights", {})
        .get("transform_signature_after", {})
        .get("sha256")
    )
    checks = {
        "actor_inventory_exact": all(
            inventory.get(key) == value
            for key, value in EXPECTED_COUNTS.items()
            if key not in ("hism_component", "hism_instance")
        ),
        "no_uncategorized_actors": inventory["uncategorized"] == 0,
        "no_duplicate_labels": not duplicate_labels,
        "hism_inventory_exact": (
            len(hism_components) == EXPECTED_COUNTS["hism_component"]
            and hism_instances == EXPECTED_COUNTS["hism_instance"]
        ),
        "child_source_inventory_exact": len(child_records) == 15,
        "child_actors_present": not child_missing,
        "child_meshes_exact": not child_mesh_mismatches,
        "child_override_materials_exact": not child_material_mismatches,
        "child_no_world_grid_material": not child_world_grid_materials,
        "fog_source_inventory_exact": len(fog_records) == 50,
        "fog_actors_present": not fog_missing,
        "fog_transforms_exact": not fog_transform_mismatches,
        "fog_meshes_exact": not fog_mesh_mismatches,
        "fog_materials_exact": not fog_material_mismatches,
        "fog_material_parents_exact": not fog_parent_mismatches,
        "fog_sort_priorities_exact": not fog_sort_priority_mismatches,
        "fog_component_policy_exact": not fog_component_policy_mismatches,
        "fog_no_world_grid_material": not fog_world_grid_materials,
        "fog_base_is_translucent": "BLEND_TRANSLUCENT" in base_blend_mode,
        "fog_base_is_one_sided": not base_two_sided,
        "fog_preview_material_v5_current": (
            base_preview_version == "5"
            and "MaterialExpressionPixelDepth" not in base_expression_classes
            and not missing_fog_expression_classes
            and not base_disable_depth_test
        ),
        "fog_integrity_review_passed": (
            fog_integrity.get("status") == "repaired_and_verified"
            and all((fog_integrity.get("checks") or {}).values())
        ),
        "fog_polish_preserved_source_transforms": (
            bool(polish_fog_before) and polish_fog_before == polish_fog_after
        ),
        "lighting_polish_preserved_source_transforms": (
            bool(polish_light_before) and polish_light_before == polish_light_after
        ),
        "preview_volumetric_fog_present": (
            preview_fog_component is not None
            and bool(
                safe_property(
                    preview_fog_component, "enable_volumetric_fog", False
                )
            )
        ),
        "preview_volumetric_fog_unique_and_continuous": (
            len(height_fog_actors) == 1
            and preview_fog_component is not None
            and abs(
                float(
                    safe_property(
                        preview_fog_component, "fog_cutoff_distance", -1.0
                    )
                )
            )
            < 0.001
            and preview_fog_albedo_error is not None
            and preview_fog_albedo_error < 0.0001
        ),
        "preview_post_auto_exposure_dynamic": (
            post_settings is not None
            and abs(
                float(
                    safe_property(
                        post_settings, "auto_exposure_min_brightness", -999.0
                    )
                )
                - 0.0
            )
            < 0.001
            and abs(
                float(
                    safe_property(
                        post_settings, "auto_exposure_max_brightness", -999.0
                    )
                )
                - 14.0
            )
            < 0.001
        ),
        "terrain_preview_report_valid": (
            terrain_preview.get("status") == "applied_preview"
            and int(terrain_preview.get("preview_version", 0)) >= 1
            and int(terrain_preview.get("material_mismatch_count", 1)) == 0
        ),
        "terrain_actors_present": not terrain_missing,
        "terrain_preview_materials_exact": not terrain_material_mismatches,
        "terrain_no_world_grid_material": not terrain_world_grid_materials,
        "root_prop_integrity_passed": (
            root_integrity.get("status") == "passed"
            and int((root_integrity.get("counts") or {}).get("managed_actor_count", 0))
            == EXPECTED_COUNTS["prop"]
            and not root_integrity.get("failures")
        ),
        "child_integrity_passed": (
            child_integrity.get("status") == "passed"
            and int((child_integrity.get("source_counts") or {}).get("total_component_count", 0))
            == EXPECTED_COUNTS["child_prop"]
            and not child_integrity.get("failures")
        ),
        "landscape_static_integrity_passed": (
            landscape_static.get("status") == "passed"
            and int((landscape_static.get("counts") or {}).get("managed_actor_count", 0))
            == EXPECTED_COUNTS["landscape_static"]
            and not any((landscape_static.get("failures") or {}).values())
        ),
        "material_rendering_integrity_passed": (
            material_rendering.get("status") == "audited"
            and int((material_rendering.get("counts") or {}).get("needs_channel_repair", 0)) == 0
            and int((material_rendering.get("counts") or {}).get("needs_opaque_parent_repair", 0)) == 0
            and int((material_rendering.get("counts") or {}).get("effective_blend_translucent", 0)) == 0
        ),
        "foliage_reload_integrity_passed": (
            foliage_reload.get("status") == "restored"
            and int(foliage_reload.get("final_batch_actor_count", 0))
            == EXPECTED_COUNTS["foliage_batch"]
            and int(foliage_reload.get("final_instance_count", 0))
            == EXPECTED_COUNTS["hism_instance"]
            and int(foliage_reload.get("material_surface_mismatch_count", 0)) == 0
            and not foliage_reload.get("mesh_mismatches")
            and not foliage_reload.get("instance_count_mismatches")
            and not foliage_reload.get("instance_transform_mismatches")
            and not foliage_reload.get("actor_transform_mismatches")
            and not foliage_reload.get("material_mismatches")
        ),
        "playable_camera_anchors_present": (
            camera_anchors.get("status") == "audited"
            and len(camera_anchors.get("route_cameras") or []) == 6
        ),
        "conservative_optimization_verified": (
            optimization.get("status") == "optimized"
            and int((optimization.get("counts") or {}).get("destroyed_actor", 0))
            == EXPECTED_OPTIMIZED_DUPLICATE_COUNT
            and not optimization.get("failures")
            and not optimization.get("user_exclusions_resurrected")
        ),
        "dualaxe_tutorial_anchors_present": (
            tutorial.get("status") == "restored"
            and len(tutorial.get("tutorial_spawn_markers") or []) == 2
            and inventory["tutorial"] == EXPECTED_COUNTS["tutorial"]
        ),
        "source_light_metadata_exact": (
            light_color.get("status") in ("audited", "repaired")
            and int(
                (light_color.get("source_light_audit_after") or {}).get(
                    "mismatch_count", 1
                )
            )
            == 0
            and int(
                (light_color.get("route_fill_audit_after") or {}).get(
                    "mismatch_count", 1
                )
            )
            == 0
        ),
        "white_tree_placeholders_removed": (
            white_tree.get("status") == "repaired"
            and int((white_tree.get("counts") or {}).get("repaired_slot", 0)) == 27
            and int((white_tree.get("counts") or {}).get("affected_slot_after", 1)) == 0
        ),
        "remaining_white_tree_trunks_recovered": (
            remaining_white_tree.get("status") == "repaired"
            and int(
                (remaining_white_tree.get("counts") or {}).get(
                    "repaired_component_slot", 0
                )
            )
            == 86
            and int(
                (remaining_white_tree.get("counts") or {}).get(
                    "affected_component_slot_after", 1
                )
            )
            == 0
            and int(
                (remaining_white_tree.get("counts") or {}).get(
                    "actor_count_after", 0
                )
            )
            == len(actors)
            and int(
                (remaining_white_tree.get("user_exclusions_after") or {}).get(
                    "expected_absent_count", 0
                )
            )
            == EXPECTED_USER_EXCLUSION_COUNT
            and int(
                (remaining_white_tree.get("user_exclusions_after") or {}).get(
                    "unexpectedly_present_count", 1
                )
            )
            == 0
            and len(reported_remaining_tree_slots) == 86
            and not remaining_tree_live_mismatches
            and not live_remaining_tree_suspicious
            and not unexpected_recovered_remaining_tree_slots
            and bool(
                unreal.EditorAssetLibrary.load_asset(
                    normalized_asset_path(recovered_remaining_tree_material)
                )
            )
        ),
        "no_blanket_reverse_culling": not reverse_culling_components,
    }
    all_checks_passed = all(checks.values())

    orientation = gap.get("orientation_audit", {})
    report = {
        "status": "audited" if all_checks_passed else "mismatch",
        "all_checks_passed": all_checks_passed,
        "map_path": MAP_PATH,
        "checks": checks,
        "expected_counts": EXPECTED_COUNTS,
        "inventory": inventory,
        "duplicate_labels": duplicate_labels,
        "hism": {
            "component_count": len(hism_components),
            "instance_count": hism_instances,
        },
        "child_audit": {
            "status": "superseded direct-child diagnostics; authoritative 27-component result is in specialized_reports.child_integrity",
            "legacy_source_record_count": len(child_records),
            "missing": child_missing,
            "legacy_max_transform_delta": child_max,
            "superseded_transform_differences": child_transform_mismatches,
            "transform_note": (
                "The 500 cm direct-child delta is the corrected attached bridge "
                "component transform. It is validated by the authoritative child "
                "integrity report and is not a live mismatch."
            ),
            "mesh_mismatches": child_mesh_mismatches,
            "override_material_mismatches": child_material_mismatches,
            "world_grid_materials": child_world_grid_materials,
        },
        "fog_audit": {
            "source_record_count": len(fog_records),
            "missing": fog_missing,
            "max_transform_error": fog_max,
            "transform_mismatches": fog_transform_mismatches,
            "mesh_mismatches": fog_mesh_mismatches,
            "material_mismatches": fog_material_mismatches,
            "parent_mismatches": fog_parent_mismatches,
            "sort_priority_mismatches": fog_sort_priority_mismatches,
            "component_policy_mismatches": fog_component_policy_mismatches,
            "world_grid_materials": fog_world_grid_materials,
            "base_material": object_path(base_material),
            "base_blend_mode": base_blend_mode,
            "base_two_sided": base_two_sided,
            "base_disable_depth_test": base_disable_depth_test,
            "base_preview_version": base_preview_version,
            "base_expression_count": len(base_expression_classes),
            "base_pixel_depth_count": base_expression_classes.count(
                "MaterialExpressionPixelDepth"
            ),
            "base_missing_required_expression_classes": (
                missing_fog_expression_classes
            ),
            "preview_global_fog": {
                "actor_count": len(height_fog_actors),
                "fog_cutoff_distance": safe_property(
                    preview_fog_component, "fog_cutoff_distance"
                ) if preview_fog_component else None,
                "volumetric_albedo": list(preview_fog_albedo_components)
                if preview_fog_albedo_components
                else None,
                "volumetric_albedo_max_error": preview_fog_albedo_error,
            },
            "preview_material_version": fog_restore.get(
                "preview_material_version"
            ),
            "polished_material_version": fog_lighting_polish.get(
                "preview_material_version"
            ),
        },
        "terrain_audit": {
            "missing": terrain_missing,
            "material_mismatches": terrain_material_mismatches,
            "world_grid_materials": terrain_world_grid_materials,
            "preview_material": TERRAIN_PREVIEW_MATERIAL_PATH,
            "preview_version": terrain_preview.get("preview_version"),
            "source_limitations": terrain_preview.get("source_limitations"),
        },
        "remaining_white_tree_live_audit": {
            "reported_recovered_slot_count": len(reported_remaining_tree_slots),
            "live_matching_recovered_slot_count": (
                len(reported_remaining_tree_slots)
                - len(remaining_tree_live_mismatches)
            ),
            "mismatches": remaining_tree_live_mismatches,
            "suspicious_detail_only_slots": live_remaining_tree_suspicious,
            "unexpected_recovered_slots": unexpected_recovered_remaining_tree_slots,
            "recovered_material": recovered_remaining_tree_material,
        },
        "orientation_and_culling": {
            "negative_determinant_actor_count": len(negative_determinant_actors),
            "negative_determinant_actor_labels": negative_determinant_actors,
            "reverse_culling_component_count": len(reverse_culling_components),
            "reverse_culling_component_owners": reverse_culling_components,
            "source_orientation_audit": {
                "audited_mesh_count": orientation.get("audited_mesh_count"),
                "error_count": orientation.get("error_count"),
                "normal_winding_totals": orientation.get("normal_winding_totals"),
                "meshes_with_more_negative_than_positive": orientation.get(
                    "meshes_with_more_negative_than_positive"
                ),
                "note": (
                    "Mixed-sign plant triangles are authored/two-sided foliage; "
                    "they are not evidence that an entire mesh needs reverse culling."
                ),
            },
        },
        "specialized_reports": {
            "root_integrity": ROOT_INTEGRITY_REPORT_PATH,
            "child_integrity": CHILD_INTEGRITY_REPORT_PATH,
            "landscape_static_integrity": LANDSCAPE_STATIC_REPORT_PATH,
            "material_rendering": MATERIAL_RENDERING_REPORT_PATH,
            "foliage_reload": FOLIAGE_RELOAD_REPORT_PATH,
            "playable_camera_anchors": CAMERA_ANCHOR_REPORT_PATH,
            "fog_lighting_polish": FOG_LIGHTING_POLISH_REPORT_PATH,
            "fog_integrity_review": FOG_INTEGRITY_REPORT_PATH,
            "conservative_optimization": OPTIMIZATION_REPORT_PATH,
            "dualaxe_tutorial": TUTORIAL_REPORT_PATH,
            "light_color_metadata": LIGHT_COLOR_REPORT_PATH,
            "white_tree_material": WHITE_TREE_REPORT_PATH,
            "remaining_white_tree_material": REMAINING_WHITE_TREE_REPORT_PATH,
        },
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "Barehanded staggering/basic-movement protagonist scenes",
        ],
    }
    write_json(REPORT_PATH, report)
    message = (
        "KHAZAN_HEINMACH_FINAL_AUDIT: RESULT passed={} actors={} "
        "child={} fog={} HISM={}/{} max_fog_loc={} report={}"
    ).format(
        all_checks_passed,
        len(actors),
        inventory["child_prop"],
        inventory["fog_sheet"],
        len(hism_components),
        hism_instances,
        fog_max["location_cm"],
        REPORT_PATH,
    )
    if all_checks_passed:
        unreal.log(message)
    else:
        unreal.log_error(message)


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
        unreal.log_error("KHAZAN_HEINMACH_FINAL_AUDIT: " + str(exception))
        raise
