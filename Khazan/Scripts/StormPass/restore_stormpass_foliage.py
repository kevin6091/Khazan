"""Restore exact StormPass Foliage PointInstancer data as managed HISMs.

The authoritative transforms come from FModel's world USDA PointInstancers and
were already decoded and bounds-validated into StormPass_FoliageInstances.json.
Each serialized FoliageInstancedStaticMeshComponent becomes one managed actor
with one component.  Gameplay, collision content, lighting, and Fog are not
created by this pass.
"""

from __future__ import annotations

import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreFoliageRestore"
)
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_FoliageInstances.json",
)
ASSET_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Foliage_AssetPreparation.json",
)
MATERIAL_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_FoliageOverrideMaterial_Restoration.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Foliage_Restoration.json",
)
MANAGED_LABEL_PREFIX = "SP_Foliage_"
MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/Foliage"
EXPECTED_BASE_ACTOR_COUNT = 14057
EXPECTED_COMPONENT_COUNT = 218
EXPECTED_INSTANCE_COUNT = 21259
EXPECTED_MESH_COUNT = 19
EXPECTED_OVERRIDE_MATERIAL_COUNT = 5
EXPECTED_OVERRIDE_REFERENCE_COUNT = 50
EXPECTED_FOG_COUNT = 0
INSTANCE_CHUNK_SIZE = 2048
LOCATION_TOLERANCE_CM = 0.02
SCALE_TOLERANCE = 0.0002
ROTATION_TOLERANCE_DEGREES = 0.02


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOLIAGE_RESTORE: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def managed_label(record):
    return "{}{}_{}_{}".format(
        MANAGED_LABEL_PREFIX,
        record["source_level"],
        record["actor_object_index"],
        record["component_object_index"],
    )


def set_actor_folder(actor, path):
    try:
        actor.set_folder_path(path)
    except Exception:
        actor.set_editor_property("folder_path", path)


def fog_actors(actors):
    return sorted(
        (
            (actor.get_actor_label(), actor.get_class().get_name())
            for actor in actors
            if actor
            and (
                actor.get_actor_label().startswith("SP_Fog_")
                or "Fog" in actor.get_class().get_name()
            )
        )
    )


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create pre-Foliage StormPass map backup")
    if not unreal.EditorAssetLibrary.save_asset(
        BACKUP_MAP_PATH, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save pre-Foliage StormPass map backup")
    return True


def source_inventory():
    metadata = load_json(METADATA_PATH)
    summary = metadata.get("summary", {})
    components = list(metadata.get("components", []))
    if (
        metadata.get("status") != "passed"
        or int(summary.get("point_instancer_component_count", -1))
        != EXPECTED_COMPONENT_COUNT
        or int(summary.get("instance_count", -1)) != EXPECTED_INSTANCE_COUNT
        or int(summary.get("unique_static_mesh_count", -1)) != EXPECTED_MESH_COUNT
        or int(summary.get("override_material_package_count", -1))
        != EXPECTED_OVERRIDE_MATERIAL_COUNT
        or len(components) != EXPECTED_COMPONENT_COUNT
        or sum(int(item.get("instance_count", 0)) for item in components)
        != EXPECTED_INSTANCE_COUNT
        or int(summary.get("missing_mesh_usd_count", -1)) != 0
    ):
        raise RuntimeError("StormPass Foliage source metadata is incomplete")
    labels = [managed_label(item) for item in components]
    if len(set(labels)) != len(labels):
        raise RuntimeError("StormPass Foliage source creates duplicate managed labels")
    if any(
        item.get("component_type") != "FoliageInstancedStaticMeshComponent"
        for item in components
    ):
        raise RuntimeError("Non-Foliage component entered the HISM inventory")
    if any(
        item.get("settings", {}).get("collision_profile_name") != "NoCollision"
        for item in components
    ):
        raise RuntimeError("Unexpected collision profile entered Foliage inventory")
    return metadata, components, set(labels)


def prepared_assets(components):
    report = load_json(ASSET_REPORT_PATH)
    if (
        report.get("status") != "passed"
        or int(report.get("resolved_static_mesh_count", -1)) != EXPECTED_MESH_COUNT
        or int(
            report.get("material_repair_summary", {}).get(
                "material_error_count", -1
            )
        )
        != 0
    ):
        raise RuntimeError("StormPass Foliage asset preparation is incomplete")
    mesh_paths = dict(report.get("mesh_assets", {}))
    required_packages = {item["static_mesh_package"] for item in components}
    if set(mesh_paths) != required_packages:
        raise RuntimeError("Prepared Foliage mesh package inventory changed")
    meshes = {}
    for package, path in mesh_paths.items():
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not mesh or mesh.get_class().get_name() != "StaticMesh":
            raise RuntimeError("Prepared Foliage StaticMesh is missing: " + package)
        meshes[package] = mesh
    slot_maps = {
        item["mesh_package"]: {
            int(assignment["source_slot"]): int(assignment["ue_slot"])
            for assignment in item.get("assignments", [])
        }
        for item in report.get("mesh_slot_mappings", [])
    }
    if set(slot_maps) != required_packages:
        raise RuntimeError("Prepared Foliage slot mapping inventory changed")
    return report, meshes, slot_maps


def prepared_materials(components):
    report = load_json(MATERIAL_REPORT_PATH)
    if (
        report.get("status") != "restored"
        or int(report.get("material_count", -1))
        != EXPECTED_OVERRIDE_MATERIAL_COUNT
        or int(report.get("missing_asset_count", -1)) != 0
    ):
        raise RuntimeError("StormPass Foliage override materials are incomplete")
    materials = {}
    for item in report.get("material_results", []):
        material = unreal.EditorAssetLibrary.load_asset(item["material_path"])
        if not material:
            raise RuntimeError("Prepared Foliage material is missing: " + item["package"])
        materials[item["package"]] = material
    required = {
        package
        for component in components
        for package in component.get("settings", {}).get(
            "override_material_packages", []
        )
        if package
    }
    if set(materials) != required:
        raise RuntimeError("Prepared Foliage override material inventory changed")
    return report, materials


def normalized_quat(values):
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm < 1.0e-12:
        raise RuntimeError("Foliage source contains an invalid quaternion")
    return unreal.Quat(*(value / norm for value in values))


def instance_transform(record):
    location = record["location_cm"]
    rotation = record["rotation_quaternion"]
    scale = record["scale"]
    transform = unreal.Transform()
    transform.set_editor_property(
        "translation",
        unreal.Vector(
            float(location["x"]), float(location["y"]), float(location["z"])
        ),
    )
    transform.set_editor_property(
        "rotation",
        normalized_quat(
            (
                float(rotation["x"]),
                float(rotation["y"]),
                float(rotation["z"]),
                float(rotation["w"]),
            )
        ),
    )
    transform.set_editor_property(
        "scale3d",
        unreal.Vector(float(scale["x"]), float(scale["y"]), float(scale["z"])),
    )
    return transform


def create_hism_component(actor):
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_instance(actor)
    if not handles:
        raise RuntimeError("Unable to gather actor subobject handles")
    actor_data = library.get_data(handles[0])
    actor_object = library.get_object(actor_data)
    if actor_object != actor:
        raise RuntimeError("Unexpected actor subobject root handle")
    params = unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", handles[0])
    params.set_editor_property("new_class", unreal.FoliageInstancedStaticMeshComponent)
    params.set_editor_property("blueprint_context", None)
    params.set_editor_property("conform_transform_to_parent", True)
    handle, failure_reason = subsystem.add_new_subobject(params)
    data = library.get_data(handle)
    component = library.get_object(data)
    if (
        not component
        or component.get_class().get_name()
        != "FoliageInstancedStaticMeshComponent"
    ):
        raise RuntimeError("Failed to add Foliage HISM: " + str(failure_reason))
    return component


def managed_component(actor):
    components = list(
        actor.get_components_by_class(unreal.FoliageInstancedStaticMeshComponent)
    )
    if len(components) > 1:
        raise RuntimeError(
            "Managed Foliage actor contains multiple HISM components: "
            + actor.get_actor_label()
        )
    return components[0] if components else create_hism_component(actor)


def configure_component(component, record, mesh, slot_map, materials, counters):
    settings = record["settings"]
    component.modify()
    component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    if not component.set_static_mesh(mesh):
        # set_static_mesh returns False when the same mesh is already assigned.
        if component.get_editor_property("static_mesh") != mesh:
            raise RuntimeError("Failed to assign Foliage StaticMesh")
    if hasattr(component, "set_collision_enabled"):
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if hasattr(component, "set_collision_object_type"):
        component.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_STATIC)
    # Setting either low-level collision field marks the profile as Custom, so
    # restore the serialized profile name only after those exact values.
    component.set_collision_profile_name("NoCollision")

    component.set_editor_property(
        "cast_shadow",
        True if settings.get("cast_shadow") is None else bool(settings["cast_shadow"]),
    )
    component.set_editor_property(
        "affect_dynamic_indirect_lighting",
        bool(settings.get("affect_dynamic_indirect_lighting", True)),
    )
    component.set_editor_property(
        "affect_distance_field_lighting",
        True
        if settings.get("affect_distance_field_lighting") is None
        else bool(settings["affect_distance_field_lighting"]),
    )
    component.set_editor_property(
        "receives_decals",
        True
        if settings.get("receives_decals") is None
        else bool(settings["receives_decals"]),
    )
    component.set_editor_property(
        "instance_start_cull_distance",
        int(settings["instance_start_cull_distance"]),
    )
    component.set_editor_property(
        "instance_end_cull_distance", int(settings["instance_end_cull_distance"])
    )
    component.set_editor_property(
        "ld_max_draw_distance", float(settings.get("cached_max_draw_distance") or 0.0)
    )
    component.set_editor_property(
        "instancing_random_seed", int(settings["instancing_random_seed"])
    )
    try:
        component.set_editor_property(
            "enable_density_scaling", bool(settings["enable_density_scaling"])
        )
        counters["density_scaling_property_applied"] += 1
    except Exception:
        counters["density_scaling_property_unexposed"] += 1

    try:
        component.set_editor_property("override_materials", [])
    except Exception:
        component.empty_override_materials()
    for source_slot, package in enumerate(
        settings.get("override_material_packages", [])
    ):
        if not package:
            continue
        counters["source_override_references"] += 1
        ue_slot = slot_map.get(source_slot)
        if ue_slot is None:
            counters["non_render_override_references"] += 1
            continue
        material = materials.get(package)
        if not material:
            raise RuntimeError("Unresolved Foliage override material: " + package)
        component.set_material(ue_slot, material)
        actual = component.get_material(ue_slot)
        if not actual or actual.get_path_name() != material.get_path_name():
            raise RuntimeError("Failed to verify Foliage override material assignment")
        counters["applied_override_references"] += 1


def add_instances(component, records):
    component.clear_instances()
    for start in range(0, len(records), INSTANCE_CHUNK_SIZE):
        transforms = [
            instance_transform(item)
            for item in records[start : start + INSTANCE_CHUNK_SIZE]
        ]
        component.add_instances(
            transforms,
            should_return_indices=False,
            world_space=True,
            update_navigation=False,
        )
    if component.get_instance_count() != len(records):
        raise RuntimeError(
            "Foliage HISM instance count mismatch: actual={} expected={}".format(
                component.get_instance_count(), len(records)
            )
        )


def vector_delta(actual, expected):
    return max(
        abs(float(actual.x) - float(expected["x"])),
        abs(float(actual.y) - float(expected["y"])),
        abs(float(actual.z) - float(expected["z"])),
    )


def quaternion_angle_degrees(actual, expected):
    values = (
        float(expected["x"]),
        float(expected["y"]),
        float(expected["z"]),
        float(expected["w"]),
    )
    norm = math.sqrt(sum(value * value for value in values))
    source = tuple(value / norm for value in values)
    actual_values = (
        float(actual.x),
        float(actual.y),
        float(actual.z),
        float(actual.w),
    )
    actual_norm = math.sqrt(sum(value * value for value in actual_values))
    normalized_actual = tuple(value / actual_norm for value in actual_values)
    dot = min(
        1.0,
        abs(sum(a * b for a, b in zip(normalized_actual, source))),
    )
    return math.degrees(2.0 * math.acos(dot))


def validate_component(component, record, mesh, slot_map, materials):
    settings = record["settings"]
    failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    if component.get_editor_property("static_mesh") != mesh:
        failures.append("static_mesh")
    if str(component.get_collision_profile_name()) != "NoCollision":
        failures.append("collision_profile")
    expected_settings = {
        "cast_shadow": True
        if settings.get("cast_shadow") is None
        else bool(settings["cast_shadow"]),
        "affect_dynamic_indirect_lighting": bool(
            settings.get("affect_dynamic_indirect_lighting", True)
        ),
        "affect_distance_field_lighting": True
        if settings.get("affect_distance_field_lighting") is None
        else bool(settings["affect_distance_field_lighting"]),
        "receives_decals": True
        if settings.get("receives_decals") is None
        else bool(settings["receives_decals"]),
        "instance_start_cull_distance": int(
            settings["instance_start_cull_distance"]
        ),
        "instance_end_cull_distance": int(settings["instance_end_cull_distance"]),
        "instancing_random_seed": int(settings["instancing_random_seed"]),
    }
    for name, expected in expected_settings.items():
        if component.get_editor_property(name) != expected:
            failures.append(name)
    actual_max_draw = float(component.get_editor_property("ld_max_draw_distance"))
    expected_max_draw = float(settings.get("cached_max_draw_distance") or 0.0)
    if abs(actual_max_draw - expected_max_draw) > 0.01:
        failures.append("ld_max_draw_distance")

    override_count = 0
    for source_slot, package in enumerate(
        settings.get("override_material_packages", [])
    ):
        if not package:
            continue
        ue_slot = slot_map.get(source_slot)
        if ue_slot is None:
            continue
        override_count += 1
        actual = component.get_material(ue_slot)
        expected = materials[package]
        if not actual or actual.get_path_name() != expected.get_path_name():
            failures.append("override_material_{}".format(source_slot))

    if component.get_instance_count() != record["instance_count"]:
        failures.append("instance_count")
        return failures, maxima, override_count, 0
    transform_failure_count = 0
    for index, source in enumerate(record["instances"]):
        actual = component.get_instance_transform(index, world_space=True)
        if not actual:
            transform_failure_count += 1
            continue
        location_delta = vector_delta(actual.translation, source["location_cm"])
        scale_delta = vector_delta(actual.scale3d, source["scale"])
        rotation_delta = quaternion_angle_degrees(
            actual.rotation, source["rotation_quaternion"]
        )
        maxima["location_delta_cm"] = max(
            maxima["location_delta_cm"], location_delta
        )
        maxima["scale_delta"] = max(maxima["scale_delta"], scale_delta)
        maxima["rotation_delta_degrees"] = max(
            maxima["rotation_delta_degrees"], rotation_delta
        )
        if (
            location_delta > LOCATION_TOLERANCE_CM
            or scale_delta > SCALE_TOLERANCE
            or rotation_delta > ROTATION_TOLERANCE_DEGREES
        ):
            transform_failure_count += 1
    if transform_failure_count:
        failures.append("instance_transforms")
    return failures, maxima, override_count, transform_failure_count


def main():
    metadata, records, expected_labels = source_inventory()
    asset_report, meshes, slot_maps = prepared_assets(records)
    material_report, materials = prepared_materials(records)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = list(actor_subsystem.get_all_level_actors())
    fog_before = fog_actors(actors_before)
    if len(fog_before) != EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog boundary differs before Foliage restoration")
    managed = {
        actor.get_actor_label(): actor
        for actor in actors_before
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    unexpected = sorted(set(managed) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected managed Foliage actor exists: " + unexpected[0])
    base_actor_count = len(actors_before) - len(managed)
    if base_actor_count != EXPECTED_BASE_ACTOR_COUNT:
        raise RuntimeError(
            "StormPass pre-Foliage actor inventory changed: {}".format(
                base_actor_count
            )
        )

    backup_created = backup_map_once()
    counters = {
        "created_actors": 0,
        "reused_actors": 0,
        "source_override_references": 0,
        "applied_override_references": 0,
        "non_render_override_references": 0,
        "density_scaling_property_applied": 0,
        "density_scaling_property_unexposed": 0,
    }
    component_records = []
    for component_index, record in enumerate(records, start=1):
        label = managed_label(record)
        actor = managed.get(label)
        if actor:
            counters["reused_actors"] += 1
        else:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.Actor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator()
            )
            if not actor:
                raise RuntimeError("Failed to spawn managed Foliage actor: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            counters["created_actors"] += 1
        actor.set_actor_location(unreal.Vector(0.0, 0.0, 0.0), False, False)
        actor.set_actor_rotation(unreal.Rotator(), False)
        actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        set_actor_folder(
            actor, MANAGED_FOLDER_ROOT + "/" + record["source_level"]
        )

        component = managed_component(actor)
        mesh = meshes[record["static_mesh_package"]]
        slot_map = slot_maps[record["static_mesh_package"]]
        configure_component(
            component, record, mesh, slot_map, materials, counters
        )
        add_instances(component, record["instances"])
        component_records.append(
            {
                "label": label,
                "source_level": record["source_level"],
                "source_actor_name": record["actor_name"],
                "source_component_name": record["component_name"],
                "mesh_package": record["static_mesh_package"],
                "mesh_asset": mesh.get_path_name(),
                "instance_count": record["instance_count"],
                "override_package_count": sum(
                    bool(item)
                    for item in record["settings"].get(
                        "override_material_packages", []
                    )
                ),
            }
        )
        if component_index % 20 == 0 or component_index == len(records):
            log(
                "Placed {}/{} components ({} instances so far)".format(
                    component_index,
                    len(records),
                    sum(item["instance_count"] for item in records[:component_index]),
                )
            )

    if counters["source_override_references"] != EXPECTED_OVERRIDE_REFERENCE_COUNT:
        raise RuntimeError("Foliage source override reference count changed")
    if (
        counters["applied_override_references"]
        != EXPECTED_OVERRIDE_REFERENCE_COUNT
        or counters["non_render_override_references"]
    ):
        raise RuntimeError("Foliage override render-slot application is incomplete")

    final_managed = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    if set(final_managed) != expected_labels:
        raise RuntimeError("Final managed Foliage actor set differs from metadata")

    component_failure_records = []
    transform_failure_count = 0
    validated_instance_count = 0
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    validated_override_count = 0
    for record_index, record in enumerate(records, start=1):
        label = managed_label(record)
        actor = final_managed[label]
        components = list(
            actor.get_components_by_class(
                unreal.FoliageInstancedStaticMeshComponent
            )
        )
        if len(components) != 1:
            component_failure_records.append(
                {"label": label, "issues": ["component_count"]}
            )
            continue
        issues, component_maxima, overrides, transform_failures = validate_component(
            components[0],
            record,
            meshes[record["static_mesh_package"]],
            slot_maps[record["static_mesh_package"]],
            materials,
        )
        validated_instance_count += components[0].get_instance_count()
        validated_override_count += overrides
        transform_failure_count += transform_failures
        for name in maxima:
            maxima[name] = max(maxima[name], component_maxima[name])
        if issues:
            component_failure_records.append({"label": label, "issues": issues})
        if record_index % 40 == 0 or record_index == len(records):
            log("Validated {}/{} components".format(record_index, len(records)))

    actors_after = list(actor_subsystem.get_all_level_actors())
    fog_after = fog_actors(actors_after)
    if fog_after != fog_before:
        raise RuntimeError("Fog boundary changed during Foliage restoration")
    if len(actors_after) != EXPECTED_BASE_ACTOR_COUNT + EXPECTED_COMPONENT_COUNT:
        raise RuntimeError("Final StormPass actor count is unexpected")
    if (
        component_failure_records
        or transform_failure_count
        or validated_instance_count != EXPECTED_INSTANCE_COUNT
        or validated_override_count != EXPECTED_OVERRIDE_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Foliage validation failed: components={} transforms={} instances={} overrides={}".format(
                len(component_failure_records),
                transform_failure_count,
                validated_instance_count,
                validated_override_count,
            )
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass after Foliage restoration")

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_metadata_path": METADATA_PATH,
        "asset_report_path": ASSET_REPORT_PATH,
        "material_report_path": MATERIAL_REPORT_PATH,
        "source_component_count": EXPECTED_COMPONENT_COUNT,
        "source_instance_count": EXPECTED_INSTANCE_COUNT,
        "source_mesh_count": EXPECTED_MESH_COUNT,
        "source_override_material_count": EXPECTED_OVERRIDE_MATERIAL_COUNT,
        "source_override_reference_count": EXPECTED_OVERRIDE_REFERENCE_COUNT,
        "placement_counters": counters,
        "component_records": component_records,
        "validation": {
            "managed_actor_count": len(final_managed),
            "component_failure_count": len(component_failure_records),
            "component_failures": component_failure_records,
            "validated_instance_count": validated_instance_count,
            "instance_transform_failure_count": transform_failure_count,
            "validated_override_reference_count": validated_override_count,
            "maximum_transform_deltas": maxima,
            "location_tolerance_cm": LOCATION_TOLERANCE_CM,
            "rotation_tolerance_degrees": ROTATION_TOLERANCE_DEGREES,
            "scale_tolerance": SCALE_TOLERANCE,
        },
        "actor_counts": {
            "before": len(actors_before),
            "after": len(actors_after),
            "delta": len(actors_after) - len(actors_before),
        },
        "fog_boundary": {
            "status": "unchanged_and_deferred_until_final_pass",
            "before": fog_before,
            "after": fog_after,
        },
        "transform_policy": (
            "FModel USD PointInstancer positions reflected Y, quaternions "
            "converted as (-X,Y,-Z,W), parent stage translation already "
            "composed, and every quaternion normalized before UE insertion"
        ),
        "collision_policy": "Exact serialized NoCollision on all 218 components",
        "excluded_content": [
            "All StormPass Fog/Mist actors and materials",
            "Lights (restored in the subsequent dedicated pass)",
            "Gameplay, character, enemy, spawn, quest, cinema and audio content",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT actors={} components={} instances={} overrides={} transform_failures={} fog=0 report={}".format(
            len(actors_after),
            len(final_managed),
            validated_instance_count,
            validated_override_count,
            transform_failure_count,
            REPORT_PATH,
        )
    )
    return report


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
                "fog_policy": "deferred_until_final_pass",
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_FOLIAGE_RESTORE: " + str(exception))
        raise
