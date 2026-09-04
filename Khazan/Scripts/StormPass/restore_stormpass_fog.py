"""Restore the final 53 StormPass Fog-sheet objects from FModel metadata.

This is the deliberately-last map mutation pass.  It creates only managed
StaticMeshActors and MaterialInstanceConstants, preserves the exact source
transforms/component flags/dynamic parameters, and uses the audited preview
parents prepared by ``prepare_stormpass_fog_assets.py``.
"""

from __future__ import annotations

import collections
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
    "L_StormPass_Environment_PreFogRestore"
)
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_FogMaterials.json",
)
ASSET_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Fog_AssetPreparation.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Fog_Restoration.json",
)
FOG_ASSET_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/FogAssets"
MATERIAL_INSTANCE_ROOT = FOG_ASSET_ROOT + "/MaterialInstances"
NOISE_TEXTURE_PATH = FOG_ASSET_ROOT + "/Textures/T_FTW_Smoke_Noise_001"
MESH_PATHS = {
    "WBP_FogSheet_C": (
        FOG_ASSET_ROOT
        + "/Meshes/Standard/StormPass_FogSheet_Standard/StaticMeshes/"
        "SM_FS_FogSheet_Plane"
    ),
    "WBP_FogSheet_Local_C": (
        FOG_ASSET_ROOT
        + "/Meshes/Local/StormPass_FogSheet_Local/StaticMeshes/"
        "SM_FS_W_FogSheet_Plane"
    ),
}
PARENT_PATHS = {
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_02": (
        FOG_ASSET_ROOT + "/Materials/M_SP_FogSheet_FMI_02_OneSided_V2"
    ),
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_01": (
        FOG_ASSET_ROOT + "/Materials/M_SP_FogSheet_FMI_01_TwoSided_V2"
    ),
    (
        "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/BBQ_Material/World/"
        "FM_FogSheet_Local"
    ): FOG_ASSET_ROOT + "/Materials/M_SP_FogSheet_Local_TwoSided_V2",
}
MANAGED_LABEL_PREFIX = "SP_Fog_"
MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/FogSheets"
EXPECTED_BASE_ACTOR_COUNT = 14355
EXPECTED_FINAL_ACTOR_COUNT = 14408
EXPECTED_FOG_COUNT = 53
EXPECTED_TYPE_COUNTS = {"WBP_FogSheet_C": 51, "WBP_FogSheet_Local_C": 2}
EXPECTED_LEVEL_COUNTS = {
    "StormPass_Boss_Phase_2": 7,
    "StormPass_Boss_Phase_Clear": 12,
    "StormPass_Light": 34,
}
EXPECTED_PARENT_COUNTS = {
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_01": 6,
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_02": 45,
    (
        "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/BBQ_Material/World/"
        "FM_FogSheet_Local"
    ): 2,
}
LOCATION_TOLERANCE_CM = 0.001
ROTATION_TOLERANCE_DEGREES = 0.002
SCALE_TOLERANCE = 0.000001
PARAMETER_ABSOLUTE_TOLERANCE = 0.0001
PARAMETER_RELATIVE_TOLERANCE = 0.000001


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOG_RESTORE: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def managed_label(record):
    return (
        "{}{}_{:05d}_{}".format(
            MANAGED_LABEL_PREFIX,
            record["source_level"],
            int(record["source_actor_object_index"]),
            record["source_actor_name"],
        )
    )[:220]


def instance_asset_name(record):
    return (
        "MI_SP_Fog_{}_{:05d}_{}".format(
            record["source_level"],
            int(record["source_actor_object_index"]),
            record["source_actor_name"],
        )
    )[:180]


def set_actor_folder(actor, path):
    try:
        actor.set_folder_path(path)
    except Exception:
        actor.set_editor_property("folder_path", path)


def source_inventory():
    metadata = load_json(METADATA_PATH)
    records = list(metadata.get("fog_actors", []))
    if (
        metadata.get("schema_version") != 1
        or metadata.get("status") != "passed"
        or metadata.get("level") != "StormPass"
        or len(records) != EXPECTED_FOG_COUNT
    ):
        raise RuntimeError("StormPass Fog source metadata is incomplete")
    type_counts = collections.Counter(record.get("actor_type") for record in records)
    level_counts = collections.Counter(record.get("source_level") for record in records)
    parent_counts = collections.Counter(
        record.get("dynamic_material", {}).get("parent_package")
        for record in records
    )
    if dict(sorted(type_counts.items())) != EXPECTED_TYPE_COUNTS:
        raise RuntimeError("StormPass Fog actor-type inventory changed")
    if dict(sorted(level_counts.items())) != EXPECTED_LEVEL_COUNTS:
        raise RuntimeError("StormPass Fog level inventory changed")
    if dict(sorted(parent_counts.items())) != EXPECTED_PARENT_COUNTS:
        raise RuntimeError("StormPass Fog material-parent inventory changed")
    labels = [managed_label(record) for record in records]
    names = [instance_asset_name(record) for record in records]
    if len(set(labels)) != len(labels) or len(set(names)) != len(names):
        raise RuntimeError("StormPass Fog source metadata creates duplicate identities")
    for record in records:
        material = record.get("dynamic_material", {})
        if material.get("parent_package") not in PARENT_PATHS:
            raise RuntimeError("StormPass Fog source parent is unresolved")
        if record.get("actor_type") not in MESH_PATHS:
            raise RuntimeError("StormPass Fog source actor type is unresolved")
        expected_two_sided = material.get("parent_package", "").endswith(
            "FMI_FogSheet_01"
        ) or record.get("actor_type") == "WBP_FogSheet_Local_C"
        if bool(record.get("effective_two_sided")) != expected_two_sided:
            raise RuntimeError("StormPass Fog source Two Side policy changed")
    return metadata, records, set(labels)


def prepared_assets():
    report = load_json(ASSET_REPORT_PATH)
    if (
        report.get("status") != "prepared"
        or bool(report.get("map_modified"))
        or int(report.get("source_fog_actor_count", -1)) != EXPECTED_FOG_COUNT
        or int(report.get("material_audit_failure_count", -1)) != 0
    ):
        raise RuntimeError("StormPass Fog asset preparation report is not valid")
    meshes = {
        actor_type: unreal.EditorAssetLibrary.load_asset(path)
        for actor_type, path in MESH_PATHS.items()
    }
    parents = {
        source_parent: unreal.EditorAssetLibrary.load_asset(path)
        for source_parent, path in PARENT_PATHS.items()
    }
    texture = unreal.EditorAssetLibrary.load_asset(NOISE_TEXTURE_PATH)
    if not all(meshes.values()) or not all(parents.values()) or not texture:
        raise RuntimeError("A prepared StormPass Fog asset is missing")
    for source_parent, parent in parents.items():
        expected_two_sided = source_parent.endswith("FMI_FogSheet_01") or source_parent.endswith(
            "FM_FogSheet_Local"
        )
        if bool(parent.get_editor_property("two_sided")) != expected_two_sided:
            raise RuntimeError("Prepared Fog parent Two Side setting changed")
    return report, meshes, parents, texture


def load_map():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    return level_subsystem, unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create pre-Fog StormPass map backup")
    if not unreal.EditorAssetLibrary.save_asset(
        BACKUP_MAP_PATH, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save pre-Fog StormPass map backup")
    return True


def source_color(value):
    value = value or {}
    return unreal.LinearColor(
        float(value.get("R", 0.0)),
        float(value.get("G", 0.0)),
        float(value.get("B", 0.0)),
        float(value.get("A", 1.0)),
    )


def preview_pan(record):
    scalar = record["dynamic_material"]["scalar_parameters"]
    if record["actor_type"] == "WBP_FogSheet_C":
        angle = math.radians(float(scalar["Rotator"]))
        speed = float(scalar["PanningSpeed"])
        return unreal.LinearColor(
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            0.0,
            0.0,
        )
    speed = float(scalar["Noise_Speed"])
    return unreal.LinearColor(speed, speed * 0.37, 0.0, 0.0)


def create_material_instances(records, parents, texture):
    ensure_directory(MATERIAL_INSTANCE_ROOT)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    result = {}
    created_count = 0
    reused_count = 0
    updated_count = 0
    unchanged_count = 0
    scalar_assignment_count = 0
    vector_assignment_count = 0
    for index, record in enumerate(records, start=1):
        name = instance_asset_name(record)
        path = MATERIAL_INSTANCE_ROOT + "/" + name
        instance = unreal.EditorAssetLibrary.load_asset(path)
        created_instance = instance is None
        if not instance:
            instance = tools.create_asset(
                name,
                MATERIAL_INSTANCE_ROOT,
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
            if not instance:
                raise RuntimeError("Failed to create Fog MIC: " + name)
            created_count += 1
        else:
            reused_count += 1
        dynamic = record["dynamic_material"]
        parent = parents[dynamic["parent_package"]]
        needs_update = created_instance
        if not needs_update:
            needs_update = bool(
                validate_material(instance, record, parents, texture)
            )
        if needs_update:
            unreal.MaterialEditingLibrary.set_material_instance_parent(instance, parent)
            for parameter_name, value in dynamic["scalar_parameters"].items():
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, parameter_name, float(value)
                )
                scalar_assignment_count += 1
            for parameter_name, value in dynamic["vector_parameters"].items():
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                    instance, parameter_name, source_color(value)
                )
                vector_assignment_count += 1
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                instance, "PreviewPanVector", preview_pan(record)
            )
            vector_assignment_count += 1
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "NoiseTexture", texture
            )
            unreal.EditorAssetLibrary.set_metadata_tag(
                instance,
                "KhazanSourceMID",
                dynamic["source_reference_path"],
            )
            unreal.EditorAssetLibrary.set_metadata_tag(
                instance,
                "KhazanSourceParent",
                dynamic["parent_package"],
            )
            unreal.EditorAssetLibrary.save_loaded_asset(
                instance, only_if_is_dirty=False
            )
            updated_count += 1
        else:
            unchanged_count += 1
        result[managed_label(record)] = instance
        if index % 10 == 0 or index == len(records):
            log("Prepared {}/{} exact Fog MICs".format(index, len(records)))
    return result, {
        "created_count": created_count,
        "reused_count": reused_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "scalar_assignment_count": scalar_assignment_count,
        "vector_assignment_count": vector_assignment_count,
        "texture_assignment_count": len(records),
    }


def vector(value, default=0.0):
    value = value or {}
    return unreal.Vector(
        float(value.get("x", default)),
        float(value.get("y", default)),
        float(value.get("z", default)),
    )


def rotator(value):
    value = value or {}
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def configure_component(component, record, mesh, material):
    settings = record["component_settings"]
    component.modify()
    if not component.set_static_mesh(mesh) and component.get_editor_property(
        "static_mesh"
    ) != mesh:
        raise RuntimeError("Failed to assign exact Fog mesh")
    component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    component.set_editor_property("receives_decals", bool(settings["receives_decals"]))
    component.set_editor_property(
        "translucency_sort_priority", int(settings["translucency_sort_priority"])
    )
    component.set_editor_property("cast_shadow", bool(settings["cast_shadow"]))
    component.set_editor_property(
        "cast_dynamic_shadow", bool(settings["cast_dynamic_shadow"])
    )
    component.set_editor_property(
        "cast_static_shadow", bool(settings["cast_static_shadow"])
    )
    component.set_editor_property("use_as_occluder", bool(settings["use_as_occluder"]))
    component.set_editor_property(
        "affect_dynamic_indirect_lighting",
        bool(settings["affect_dynamic_indirect_lighting"]),
    )
    component.set_editor_property(
        "affect_distance_field_lighting",
        bool(settings["affect_distance_field_lighting"]),
    )
    component.set_editor_property(
        "can_ever_affect_navigation", bool(settings["can_ever_affect_navigation"])
    )
    component.set_editor_property(
        "can_character_step_up_on", unreal.CanBeCharacterBase.ECB_NO
    )
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_collision_profile_name(str(settings["collision_profile_name"]))
    try:
        component.set_editor_property("override_materials", [])
    except Exception:
        component.empty_override_materials()
    component.set_material(0, material)


def place_fog(records, expected_labels, meshes, materials, actor_subsystem):
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    managed = {
        actor.get_actor_label(): actor
        for actor in actors_before
        if actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    unexpected = sorted(set(managed) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected managed StormPass Fog actor: " + unexpected[0])
    base_count = len(actors_before) - len(managed)
    if base_count != EXPECTED_BASE_ACTOR_COUNT:
        raise RuntimeError(
            "StormPass pre-Fog actor boundary changed: {}".format(base_count)
        )

    created_count = 0
    reused_count = 0
    for index, record in enumerate(records, start=1):
        label = managed_label(record)
        transform = record["transform"]
        location = vector(transform["location_cm"])
        rotation = rotator(transform["rotation_degrees"])
        scale = vector(transform["scale"], default=1.0)
        actor = managed.get(label)
        if actor:
            if not isinstance(actor, unreal.StaticMeshActor):
                raise RuntimeError("Managed Fog actor has the wrong class: " + label)
            reused_count += 1
        else:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.StaticMeshActor, location, rotation
            )
            if not actor:
                raise RuntimeError("Failed to spawn managed Fog actor: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            created_count += 1
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, False)
        actor.set_actor_scale3d(scale)
        set_actor_folder(
            actor, MANAGED_FOLDER_ROOT + "/" + record["source_level"]
        )
        try:
            actor.set_editor_property(
                "tags",
                [
                    "StormPassReconstructedFog",
                    record["actor_type"],
                    record["source_level"],
                ],
            )
        except Exception:
            pass
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Managed Fog actor has no StaticMeshComponent")
        configure_component(
            component,
            record,
            meshes[record["actor_type"]],
            materials[label],
        )
        if index % 10 == 0 or index == len(records):
            log("Placed {}/{} Fog sheets".format(index, len(records)))
    return {
        "created_count": created_count,
        "reused_count": reused_count,
        "before_actor_count": len(actors_before),
    }


def canonical_quaternion(rotation):
    quat = rotation if isinstance(rotation, unreal.Quat) else rotation.quaternion()
    values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
    length = math.sqrt(sum(value * value for value in values))
    if length <= 1.0e-12:
        raise RuntimeError("Encountered a zero Fog quaternion")
    return [value / length for value in values]


def rotation_delta_degrees(actual, expected):
    left = canonical_quaternion(actual)
    right = canonical_quaternion(expected)
    dot = min(1.0, abs(sum(a * b for a, b in zip(left, right))))
    return math.degrees(2.0 * math.acos(dot))


def vector_delta(actual, expected):
    return max(
        abs(float(actual.x) - float(expected.x)),
        abs(float(actual.y) - float(expected.y)),
        abs(float(actual.z) - float(expected.z)),
    )


def scalar_equal(actual, expected):
    tolerance = max(
        PARAMETER_ABSOLUTE_TOLERANCE,
        abs(float(expected)) * PARAMETER_RELATIVE_TOLERANCE,
    )
    return abs(float(actual) - float(expected)) <= tolerance


def color_equal(actual, expected):
    return all(
        scalar_equal(getattr(actual, name), getattr(expected, name))
        for name in ("r", "g", "b", "a")
    )


def validate_material(instance, record, parents, texture):
    issues = []
    dynamic = record["dynamic_material"]
    expected_parent = parents[dynamic["parent_package"]]
    if instance.get_editor_property("parent") != expected_parent:
        issues.append("material_parent")
    for name, expected in dynamic["scalar_parameters"].items():
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            instance, name
        )
        if not scalar_equal(actual, expected):
            issues.append("scalar:" + name)
    for name, value in dynamic["vector_parameters"].items():
        expected = source_color(value)
        actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
            instance, name
        )
        if not color_equal(actual, expected):
            issues.append("vector:" + name)
    expected_pan = preview_pan(record)
    actual_pan = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
        instance, "PreviewPanVector"
    )
    if not color_equal(actual_pan, expected_pan):
        issues.append("vector:PreviewPanVector")
    actual_texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
        instance, "NoiseTexture"
    )
    if actual_texture != texture:
        issues.append("texture:NoiseTexture")
    return issues


def validate_component(component, record, mesh, material):
    settings = record["component_settings"]
    issues = []
    if component.get_editor_property("static_mesh") != mesh:
        issues.append("static_mesh")
    if component.get_material(0) != material:
        issues.append("material")
    expected_properties = {
        "mobility": unreal.ComponentMobility.STATIC,
        "receives_decals": bool(settings["receives_decals"]),
        "translucency_sort_priority": int(settings["translucency_sort_priority"]),
        "cast_shadow": bool(settings["cast_shadow"]),
        "cast_dynamic_shadow": bool(settings["cast_dynamic_shadow"]),
        "cast_static_shadow": bool(settings["cast_static_shadow"]),
        "use_as_occluder": bool(settings["use_as_occluder"]),
        "affect_dynamic_indirect_lighting": bool(
            settings["affect_dynamic_indirect_lighting"]
        ),
        "affect_distance_field_lighting": bool(
            settings["affect_distance_field_lighting"]
        ),
        "can_ever_affect_navigation": bool(settings["can_ever_affect_navigation"]),
        "can_character_step_up_on": unreal.CanBeCharacterBase.ECB_NO,
    }
    for name, expected in expected_properties.items():
        if component.get_editor_property(name) != expected:
            issues.append(name)
    if str(component.get_collision_profile_name()) != str(
        settings["collision_profile_name"]
    ):
        issues.append("collision_profile_name")
    return issues


def validate_all(records, expected_labels, meshes, materials, parents, texture, actor_subsystem):
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    counts_by_type = collections.Counter()
    counts_by_level = collections.Counter()
    parent_counts = collections.Counter()
    for record in records:
        label = managed_label(record)
        actor = managed.get(label)
        if not actor:
            continue
        transform = record["transform"]
        expected_location = vector(transform["location_cm"])
        expected_rotation = rotator(transform["rotation_degrees"])
        expected_scale = vector(transform["scale"], default=1.0)
        deltas = {
            "location_delta_cm": vector_delta(
                actor.get_actor_location(), expected_location
            ),
            "rotation_delta_degrees": rotation_delta_degrees(
                actor.get_actor_rotation(), expected_rotation
            ),
            "scale_delta": vector_delta(actor.get_actor_scale3d(), expected_scale),
        }
        for name, value in deltas.items():
            maxima[name] = max(maxima[name], value)
        issues = []
        if not isinstance(actor, unreal.StaticMeshActor):
            issues.append("actor_class")
        if deltas["location_delta_cm"] > LOCATION_TOLERANCE_CM:
            issues.append("actor_location")
        if deltas["rotation_delta_degrees"] > ROTATION_TOLERANCE_DEGREES:
            issues.append("actor_rotation")
        if deltas["scale_delta"] > SCALE_TOLERANCE:
            issues.append("actor_scale")
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            issues.append("component_missing")
        else:
            issues.extend(
                validate_component(
                    component,
                    record,
                    meshes[record["actor_type"]],
                    materials[label],
                )
            )
        issues.extend(
            validate_material(materials[label], record, parents, texture)
        )
        if issues:
            failures.append({"label": label, "issues": sorted(set(issues))})
        counts_by_type[record["actor_type"]] += 1
        counts_by_level[record["source_level"]] += 1
        parent_counts[record["dynamic_material"]["parent_package"]] += 1
    if len(actors) != EXPECTED_FINAL_ACTOR_COUNT:
        failures.append(
            {"label": "<world>", "issues": ["total_actor_count:" + str(len(actors))]}
        )
    if missing or extra:
        failures.append(
            {
                "label": "<managed-set>",
                "issues": ["missing:" + str(len(missing)), "extra:" + str(len(extra))],
            }
        )
    return {
        "total_actor_count": len(actors),
        "managed_fog_actor_count": len(managed),
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "missing_labels": missing,
        "extra_labels": extra,
        "failure_count": len(failures),
        "failures": failures,
        "maximum_transform_deltas": maxima,
        "counts_by_type": dict(sorted(counts_by_type.items())),
        "counts_by_level": dict(sorted(counts_by_level.items())),
        "counts_by_source_parent": dict(sorted(parent_counts.items())),
        "tolerances": {
            "location_cm": LOCATION_TOLERANCE_CM,
            "rotation_degrees": ROTATION_TOLERANCE_DEGREES,
            "scale": SCALE_TOLERANCE,
            "parameter_absolute": PARAMETER_ABSOLUTE_TOLERANCE,
            "parameter_relative": PARAMETER_RELATIVE_TOLERANCE,
        },
    }


def main():
    metadata, records, expected_labels = source_inventory()
    asset_report, meshes, parents, texture = prepared_assets()
    level_subsystem, actor_subsystem = load_map()
    before_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    existing_managed = {
        actor.get_actor_label()
        for actor in before_actors
        if actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    native_or_unmanaged_fog = [
        actor.get_actor_label()
        for actor in before_actors
        if "Fog" in actor.get_class().get_name()
        and not actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
        and actor.get_actor_label() != "SP_Environment_HeightFog"
    ]
    if (
        len(before_actors) - len(existing_managed) != EXPECTED_BASE_ACTOR_COUNT
        or existing_managed.difference(expected_labels)
        or native_or_unmanaged_fog
    ):
        raise RuntimeError("StormPass final Fog boundary contains unmanaged content")

    backup_created = backup_map_once()
    materials, material_result = create_material_instances(records, parents, texture)
    placement = place_fog(
        records, expected_labels, meshes, materials, actor_subsystem
    )
    validation = validate_all(
        records,
        expected_labels,
        meshes,
        materials,
        parents,
        texture,
        actor_subsystem,
    )
    if validation["failure_count"]:
        raise RuntimeError(
            "StormPass Fog validation failed: "
            + str(validation["failures"][0])
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass after final Fog restoration")
    unreal.EditorAssetLibrary.save_directory(
        FOG_ASSET_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored",
        "operation": "final_stormpass_fog_sheet_restoration",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_metadata_path": METADATA_PATH,
        "asset_report_path": ASSET_REPORT_PATH,
        "source_fog_actor_count": len(records),
        "material_instances": material_result,
        "placement": placement,
        "validation": validation,
        "fog_stage_policy": "executed_last_after_props_landscape_foliage_and_lights",
        "content_boundary": {
            "visual_level_content_only": True,
            "gameplay_or_source_code_modified": False,
            "characters_enemies_quests_audio_navigation_modified": False,
        },
        "material_fidelity": {
            "exact_source_meshes": True,
            "exact_source_noise_texture": True,
            "exact_source_dynamic_scalar_parameters": True,
            "exact_source_dynamic_vector_parameters": True,
            "exact_source_parent_variant_and_two_sided_policy": True,
            "cooked_custom_parent_graph_available_from_fmodel": False,
            "ue5_preview_graph_used": True,
        },
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} actors={} fog={} standard={} local={} failures={} report={}".format(
            report["status"],
            validation["total_actor_count"],
            validation["managed_fog_actor_count"],
            validation["counts_by_type"].get("WBP_FogSheet_C", 0),
            validation["counts_by_type"].get("WBP_FogSheet_Local_C", 0),
            validation["failure_count"],
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
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_FOG_RESTORE: " + str(exception))
        raise
