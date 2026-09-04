"""Restore the 53 source-authored StormPass local lights.

Only visual Level content is created by this pass.  It uses the same verified
source-intensity conversion and raw FColor policy as HeinMach, preserves exact
source transforms and supported component properties, and binds the native
JellyFish IES profile reconstructed from FModel's cooked lookup.  StormPass Fog
remains strictly deferred.
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
    "L_StormPass_Environment_PreLightRestore"
)
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_SourceLights.json",
)
PROFILE_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_LightProfile_AssetPreparation.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Light_Restoration.json",
)
PROFILE_ASSET_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/LightAssets/IES/"
    "TLP_JellyFish"
)
MANAGED_LABEL_PREFIX = "SP_SourceLight_"
MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/SourceLights"
SOURCE_INTENSITY_TO_LUMENS = 750.0
EXPECTED_BASE_ACTOR_COUNT = 14275
EXPECTED_SOURCE_LIGHT_COUNT = 53
EXPECTED_POINT_LIGHT_COUNT = 52
EXPECTED_SPOT_LIGHT_COUNT = 1
EXPECTED_IES_REFERENCE_COUNT = 42
EXPECTED_ANIMATED_LIGHT_COUNT = 23
EXPECTED_FOG_COUNT = 0
EXPECTED_COUNTS_BY_LEVEL = {
    "StormPass_Boss_Phase_1": 13,
    "StormPass_Boss_Phase_2": 11,
    "StormPass_Light": 24,
    "StormPass_SubLV03": 4,
    "StormPass_SubLV11": 1,
}
LOCATION_TOLERANCE_CM = 0.001
ROTATION_TOLERANCE_DEGREES = 0.002
SCALE_TOLERANCE = 0.000001
FLOAT_TOLERANCE = 0.001

SUPPORTED_SOURCE_PROPERTIES = {
    "Intensity",
    "AttenuationRadius",
    "VolumetricScatteringIntensity",
    "SpecularScale",
    "LightFalloffExponent",
    "MaxDrawDistance",
    "MaxDistanceFadeRange",
    "IndirectLightingIntensity",
    "LightColor",
    "bUseInverseSquaredFalloff",
    "OuterConeAngle",
    "IESTexture",
}
STRUCTURAL_SOURCE_PROPERTIES = {
    "AttachParent",
    "RelativeLocation",
    "RelativeRotation",
    "RelativeScale3D",
    "PrimaryComponentTick",
}
CUSTOM_ANIMATION_PROPERTIES = {
    "bUseLightAnimation",
    "AnimationSpeed",
    "LightAnimationIntensity",
    "AnimationMaxDistance",
}


def log(message):
    unreal.log("KHAZAN_STORMPASS_LIGHT_RESTORE: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def managed_label(record):
    return "{}{}_{}_{}".format(
        MANAGED_LABEL_PREFIX,
        record["source_level"],
        record["source_object_index"],
        record["actor_name"],
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
        raise RuntimeError("Failed to create pre-Light StormPass map backup")
    if not unreal.EditorAssetLibrary.save_asset(
        BACKUP_MAP_PATH, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save pre-Light StormPass map backup")
    return True


def light_component_record(record):
    matches = [
        component
        for component in record.get("components", [])
        if "LightComponent" in str(component.get("type", ""))
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one source LightComponent for {} but found {}".format(
                managed_label(record), len(matches)
            )
        )
    return matches[0]


def light_properties(record):
    properties = light_component_record(record).get("properties", {})
    if not isinstance(properties, dict):
        raise RuntimeError("Source light properties are not an object")
    return properties


def source_inventory():
    metadata = load_json(METADATA_PATH)
    records = list(metadata.get("lights", []))
    if (
        metadata.get("schema_version") != 1
        or metadata.get("level") != "StormPass"
        or len(records) != EXPECTED_SOURCE_LIGHT_COUNT
    ):
        raise RuntimeError("StormPass source-light metadata is incomplete")

    labels = [managed_label(record) for record in records]
    if len(set(labels)) != len(labels):
        raise RuntimeError("StormPass source lights create duplicate managed labels")
    point_count = sum(
        record.get("actor_type") == "xxPointLight" for record in records
    )
    spot_count = sum(
        record.get("actor_type") == "xxSpotLight" for record in records
    )
    if (
        point_count != EXPECTED_POINT_LIGHT_COUNT
        or spot_count != EXPECTED_SPOT_LIGHT_COUNT
        or point_count + spot_count != len(records)
    ):
        raise RuntimeError("StormPass source-light type inventory changed")

    counts_by_level = collections.Counter(
        record.get("source_level") for record in records
    )
    if dict(sorted(counts_by_level.items())) != EXPECTED_COUNTS_BY_LEVEL:
        raise RuntimeError("StormPass source-light level inventory changed")
    ies_count = sum("IESTexture" in light_properties(record) for record in records)
    animated_count = sum(
        bool(light_properties(record).get("bUseLightAnimation", False))
        for record in records
    )
    if ies_count != EXPECTED_IES_REFERENCE_COUNT:
        raise RuntimeError("StormPass JellyFish IES reference inventory changed")
    if animated_count != EXPECTED_ANIMATED_LIGHT_COUNT:
        raise RuntimeError("StormPass animated-light inventory changed")
    for record in records:
        transform = record.get("transform", {})
        scale = transform.get("scale", {})
        if any(
            abs(float(scale.get(axis, 1.0)) - 1.0) > SCALE_TOLERANCE
            for axis in ("x", "y", "z")
        ):
            raise RuntimeError("Unexpected non-unit source Light actor scale")
        source_ies = light_properties(record).get("IESTexture")
        if source_ies and "JellyFish" not in str(source_ies.get("ObjectPath", "")):
            raise RuntimeError("Unexpected source IES package")
    return metadata, records, set(labels)


def prepared_profile():
    report = load_json(PROFILE_REPORT_PATH)
    state = report.get("profile_state", {})
    if (
        report.get("status") != "passed"
        or report.get("map_modified") is not False
        or int(report.get("source_sample_count", -1)) != 256
        or int(report.get("source_nonzero_sample_count", -1)) != 128
        or abs(float(report.get("source_min", -1.0)) - 0.0) > 1.0e-7
        or abs(float(report.get("source_max", -1.0)) - 0.6640625) > 1.0e-7
        or state.get("class") != "TextureLightProfile"
        or int(state.get("built_size_x", -1)) != 256
        or int(state.get("built_size_y", -1)) != 256
        or abs(float(state.get("texture_multiplier", -1.0)) - 1.0) > 1.0e-7
    ):
        raise RuntimeError("StormPass JellyFish profile report is incomplete")
    profile = unreal.EditorAssetLibrary.load_asset(PROFILE_ASSET_PATH)
    if not profile or profile.get_class().get_name() != "TextureLightProfile":
        raise RuntimeError("Reconstructed JellyFish TextureLightProfile is missing")
    minimum, maximum = profile.compute_texture_source_channel_min_max()
    built_size = profile.blueprint_get_built_texture_size()
    if (
        int(built_size.x) != 256
        or int(built_size.y) != 256
        or abs(float(minimum.r)) > 1.0e-7
        or abs(float(maximum.r) - 0.6640625) > 1.0e-7
        or abs(float(profile.get_editor_property("texture_multiplier")) - 1.0)
        > 1.0e-7
    ):
        raise RuntimeError("Live JellyFish TextureLightProfile validation failed")
    return report, profile


def vector(values, default=0.0):
    return unreal.Vector(
        x=float(values.get("x", default)),
        y=float(values.get("y", default)),
        z=float(values.get("z", default)),
    )


def rotator(values):
    return unreal.Rotator(
        pitch=float(values.get("pitch", 0.0)),
        yaw=float(values.get("yaw", 0.0)),
        roll=float(values.get("roll", 0.0)),
    )


def expected_values(record):
    source = light_properties(record)
    source_intensity = float(source.get("Intensity", 2.0))
    lumens = max(
        500.0, min(50000.0, source_intensity * SOURCE_INTENSITY_TO_LUMENS)
    )
    color = source.get("LightColor", {})
    values = {
        "intensity_source": source_intensity,
        "intensity_lumens": lumens,
        "attenuation_radius": float(source.get("AttenuationRadius", 2000.0)),
        "volumetric_scattering_intensity": float(
            source.get("VolumetricScatteringIntensity", 1.0)
        ),
        "specular_scale": float(source.get("SpecularScale", 0.0)),
        "cast_shadows": bool(source.get("CastShadows", False)),
        "use_inverse_squared_falloff": bool(
            source.get("bUseInverseSquaredFalloff", True)
        ),
        "max_draw_distance": float(source.get("MaxDrawDistance", 0.0)),
        "max_distance_fade_range": float(
            source.get("MaxDistanceFadeRange", 0.0)
        ),
        "indirect_lighting_intensity": float(
            source.get("IndirectLightingIntensity", 1.0)
        ),
        "light_color": (
            int(color.get("R", 255)),
            int(color.get("G", 255)),
            int(color.get("B", 255)),
            int(color.get("A", 255)),
        ),
        "uses_ies": "IESTexture" in source,
    }
    if "LightFalloffExponent" in source:
        values["light_falloff_exponent"] = float(
            source["LightFalloffExponent"]
        )
    if record.get("actor_type") == "xxSpotLight":
        values["outer_cone_angle"] = float(source.get("OuterConeAngle", 44.0))
        values["inner_cone_angle"] = 0.0
    return values


def safe_set(component, property_name, value, failures):
    try:
        component.set_editor_property(property_name, value)
        return True
    except Exception as exception:
        failures.append(
            {
                "object": component.get_path_name(),
                "property": property_name,
                "value": str(value),
                "error": str(exception),
            }
        )
        return False


def apply_light(component, record, profile, failures):
    values = expected_values(record)
    safe_set(component, "mobility", unreal.ComponentMobility.MOVABLE, failures)
    safe_set(component, "intensity", values["intensity_lumens"], failures)
    safe_set(
        component,
        "attenuation_radius",
        values["attenuation_radius"],
        failures,
    )
    safe_set(
        component,
        "volumetric_scattering_intensity",
        values["volumetric_scattering_intensity"],
        failures,
    )
    safe_set(component, "specular_scale", values["specular_scale"], failures)
    safe_set(component, "cast_shadows", values["cast_shadows"], failures)
    safe_set(
        component,
        "use_inverse_squared_falloff",
        values["use_inverse_squared_falloff"],
        failures,
    )
    if "light_falloff_exponent" in values:
        safe_set(
            component,
            "light_falloff_exponent",
            values["light_falloff_exponent"],
            failures,
        )
    safe_set(
        component, "max_draw_distance", values["max_draw_distance"], failures
    )
    safe_set(
        component,
        "max_distance_fade_range",
        values["max_distance_fade_range"],
        failures,
    )
    safe_set(
        component,
        "indirect_lighting_intensity",
        values["indirect_lighting_intensity"],
        failures,
    )

    red, green, blue, alpha = values["light_color"]
    safe_set(
        component,
        "light_color",
        unreal.Color(r=red, g=green, b=blue, a=alpha),
        failures,
    )
    safe_set(
        component,
        "ies_texture",
        profile if values["uses_ies"] else None,
        failures,
    )
    # bUseIESBrightness is absent from all source instances and the stock
    # component default is false.  Keep authored Intensity as the controlling
    # value and use JellyFish strictly as the source profile mask.
    safe_set(component, "use_ies_brightness", False, failures)
    safe_set(component, "ies_brightness_scale", 1.0, failures)

    if isinstance(component, unreal.SpotLightComponent):
        safe_set(
            component,
            "outer_cone_angle",
            values["outer_cone_angle"],
            failures,
        )
        safe_set(
            component,
            "inner_cone_angle",
            values["inner_cone_angle"],
            failures,
        )
    return values


def actor_type_matches(actor, is_spot):
    if is_spot:
        return isinstance(actor, unreal.SpotLight)
    return isinstance(actor, unreal.PointLight) and not isinstance(
        actor, unreal.SpotLight
    )


def get_light_component(actor, is_spot):
    component_class = (
        unreal.SpotLightComponent if is_spot else unreal.PointLightComponent
    )
    component = actor.get_component_by_class(component_class)
    if not component:
        raise RuntimeError("Managed Light actor has no expected component")
    return component


def canonical_quaternion(rotation):
    quat = rotation if isinstance(rotation, unreal.Quat) else rotation.quaternion()
    values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
    length = math.sqrt(sum(value * value for value in values))
    if length <= 1.0e-12:
        raise RuntimeError("Encountered a zero Light quaternion")
    values = [value / length for value in values]
    if values[3] < 0.0:
        values = [-value for value in values]
    return values


def rotation_delta_degrees(actual, expected):
    actual_values = canonical_quaternion(actual)
    expected_values_ = canonical_quaternion(expected)
    dot = min(
        1.0,
        abs(sum(a * b for a, b in zip(actual_values, expected_values_))),
    )
    return math.degrees(2.0 * math.acos(dot))


def color_tuple(color):
    return (int(color.r), int(color.g), int(color.b), int(color.a))


def float_property_issue(component, name, expected, issues):
    actual = float(component.get_editor_property(name))
    delta = abs(actual - expected)
    if delta > FLOAT_TOLERANCE:
        issues.append(name)
    return delta


def validate_actor(actor, record, profile):
    transform = record["transform"]
    expected_location = vector(transform["location_cm"])
    expected_rotation = rotator(transform["rotation_degrees"])
    expected_scale = vector(transform["scale"], default=1.0)
    actual_location = actor.get_actor_location()
    actual_scale = actor.get_actor_scale3d()
    location_delta = math.sqrt(
        (float(actual_location.x) - float(expected_location.x)) ** 2
        + (float(actual_location.y) - float(expected_location.y)) ** 2
        + (float(actual_location.z) - float(expected_location.z)) ** 2
    )
    scale_delta = max(
        abs(float(actual_scale.x) - float(expected_scale.x)),
        abs(float(actual_scale.y) - float(expected_scale.y)),
        abs(float(actual_scale.z) - float(expected_scale.z)),
    )
    rotation_delta = rotation_delta_degrees(
        actor.get_actor_rotation(), expected_rotation
    )
    issues = []
    if location_delta > LOCATION_TOLERANCE_CM:
        issues.append("actor_location")
    if rotation_delta > ROTATION_TOLERANCE_DEGREES:
        issues.append("actor_rotation")
    if scale_delta > SCALE_TOLERANCE:
        issues.append("actor_scale")

    is_spot = record["actor_type"] == "xxSpotLight"
    if not actor_type_matches(actor, is_spot):
        issues.append("actor_class")
        return issues, {
            "location_delta_cm": location_delta,
            "rotation_delta_degrees": rotation_delta,
            "scale_delta": scale_delta,
            "maximum_property_float_delta": 0.0,
        }
    component = get_light_component(actor, is_spot)
    values = expected_values(record)
    property_deltas = []
    if component.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE:
        issues.append("mobility")
    for name in (
        "intensity_lumens",
        "attenuation_radius",
        "volumetric_scattering_intensity",
        "specular_scale",
        "max_draw_distance",
        "max_distance_fade_range",
        "indirect_lighting_intensity",
    ):
        property_name = "intensity" if name == "intensity_lumens" else name
        property_deltas.append(
            float_property_issue(component, property_name, values[name], issues)
        )
    if "light_falloff_exponent" in values:
        property_deltas.append(
            float_property_issue(
                component,
                "light_falloff_exponent",
                values["light_falloff_exponent"],
                issues,
            )
        )
    if bool(component.get_editor_property("cast_shadows")) != values["cast_shadows"]:
        issues.append("cast_shadows")
    if (
        bool(component.get_editor_property("use_inverse_squared_falloff"))
        != values["use_inverse_squared_falloff"]
    ):
        issues.append("use_inverse_squared_falloff")
    if color_tuple(component.get_editor_property("light_color")) != values["light_color"]:
        issues.append("light_color")
    actual_ies = component.get_editor_property("ies_texture")
    expected_ies = profile if values["uses_ies"] else None
    if actual_ies != expected_ies:
        issues.append("ies_texture")
    if bool(component.get_editor_property("use_ies_brightness")):
        issues.append("use_ies_brightness")
    property_deltas.append(
        float_property_issue(component, "ies_brightness_scale", 1.0, issues)
    )
    if is_spot:
        property_deltas.append(
            float_property_issue(
                component,
                "outer_cone_angle",
                values["outer_cone_angle"],
                issues,
            )
        )
        property_deltas.append(
            float_property_issue(
                component,
                "inner_cone_angle",
                values["inner_cone_angle"],
                issues,
            )
        )
    return issues, {
        "location_delta_cm": location_delta,
        "rotation_delta_degrees": rotation_delta,
        "scale_delta": scale_delta,
        "maximum_property_float_delta": max(property_deltas or [0.0]),
    }


def source_property_audit(records):
    property_counts = collections.Counter()
    unhandled_counts = collections.Counter()
    custom_counts = collections.Counter()
    animation_records = []
    unhandled_records = []
    for record in records:
        properties = light_properties(record)
        property_counts.update(properties.keys())
        custom = {
            name: value
            for name, value in properties.items()
            if name.startswith("BBQ") or name in CUSTOM_ANIMATION_PROPERTIES
        }
        custom_counts.update(custom)
        if bool(properties.get("bUseLightAnimation", False)):
            animation_records.append(
                {
                    "label": managed_label(record),
                    "source_level": record["source_level"],
                    "source_actor_name": record["actor_name"],
                    "bUseLightAnimation": True,
                    "AnimationSpeed": properties.get("AnimationSpeed"),
                    "LightAnimationIntensity": properties.get(
                        "LightAnimationIntensity"
                    ),
                    "AnimationMaxDistance": properties.get(
                        "AnimationMaxDistance"
                    ),
                }
            )
        unhandled = sorted(
            name
            for name in properties
            if name not in SUPPORTED_SOURCE_PROPERTIES
            and name not in STRUCTURAL_SOURCE_PROPERTIES
            and name not in CUSTOM_ANIMATION_PROPERTIES
            and not name.startswith("BBQ")
        )
        unhandled_counts.update(unhandled)
        if unhandled:
            unhandled_records.append(
                {"label": managed_label(record), "properties": unhandled}
            )
    return {
        "serialized_property_counts": dict(sorted(property_counts.items())),
        "custom_property_counts": dict(sorted(custom_counts.items())),
        "animated_source_light_count": len(animation_records),
        "animated_source_lights": animation_records,
        "other_unhandled_property_counts": dict(sorted(unhandled_counts.items())),
        "other_unhandled_records": unhandled_records,
        "custom_visual_behavior_policy": (
            "xxPointLight/xxSpotLight animation and BBQCartoon fields belong to "
            "the unavailable game-native component classes. Their serialized "
            "values are retained in metadata/report only; no gameplay C++, "
            "Blueprint tick, or invented animation was introduced."
        ),
    }


def main():
    metadata, records, expected_labels = source_inventory()
    profile_report, profile = prepared_profile()
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
        raise RuntimeError("Fog boundary differs before Light restoration")
    managed_before_list = [
        actor
        for actor in actors_before
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    ]
    labels_before = [actor.get_actor_label() for actor in managed_before_list]
    duplicate_labels = sorted(
        label
        for label, count in collections.Counter(labels_before).items()
        if count > 1
    )
    if duplicate_labels:
        raise RuntimeError("Duplicate managed Light label: " + duplicate_labels[0])
    managed = {actor.get_actor_label(): actor for actor in managed_before_list}
    unexpected = sorted(set(managed) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected managed Light actor exists: " + unexpected[0])
    base_actor_count = len(actors_before) - len(managed)
    if base_actor_count != EXPECTED_BASE_ACTOR_COUNT:
        raise RuntimeError(
            "StormPass pre-Light actor inventory changed: {}".format(
                base_actor_count
            )
        )

    backup_created = backup_map_once()
    counters = collections.Counter()
    property_failures = []
    placement_records = []
    for index, record in enumerate(records, start=1):
        label = managed_label(record)
        is_spot = record["actor_type"] == "xxSpotLight"
        actor = managed.get(label)
        if actor and not actor_type_matches(actor, is_spot):
            if not actor_subsystem.destroy_actor(actor):
                raise RuntimeError("Failed to replace wrong managed Light class")
            actor = None
            managed.pop(label, None)
            counters["replaced_wrong_class"] += 1
        if actor:
            counters["reused_actors"] += 1
        else:
            actor_class = unreal.SpotLight if is_spot else unreal.PointLight
            actor = actor_subsystem.spawn_actor_from_class(
                actor_class, unreal.Vector(), unreal.Rotator()
            )
            if not actor:
                raise RuntimeError("Failed to spawn managed Light: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            counters["created_actors"] += 1

        transform = record["transform"]
        actor.set_actor_location(vector(transform["location_cm"]), False, False)
        actor.set_actor_rotation(rotator(transform["rotation_degrees"]), False)
        actor.set_actor_scale3d(vector(transform["scale"], default=1.0))
        set_actor_folder(
            actor, MANAGED_FOLDER_ROOT + "/" + record["source_level"]
        )
        component = get_light_component(actor, is_spot)
        values = apply_light(component, record, profile, property_failures)
        counters["point_lights" if not is_spot else "spot_lights"] += 1
        counters["ies_bindings"] += int(values["uses_ies"])
        placement_records.append(
            {
                "label": label,
                "source_level": record["source_level"],
                "source_object_index": record["source_object_index"],
                "source_actor_name": record["actor_name"],
                "actor_class": actor.get_class().get_name(),
                "component_class": component.get_class().get_name(),
                "intensity_source": values["intensity_source"],
                "intensity_lumens": values["intensity_lumens"],
                "uses_ies": values["uses_ies"],
            }
        )
        if index % 10 == 0 or index == len(records):
            log("Placed {}/{} source lights".format(index, len(records)))

    if property_failures:
        raise RuntimeError(
            "Supported Light property application failed {} times".format(
                len(property_failures)
            )
        )
    if (
        counters["point_lights"] != EXPECTED_POINT_LIGHT_COUNT
        or counters["spot_lights"] != EXPECTED_SPOT_LIGHT_COUNT
        or counters["ies_bindings"] != EXPECTED_IES_REFERENCE_COUNT
    ):
        raise RuntimeError("Placed Light inventory differs from source")

    actors_after = list(actor_subsystem.get_all_level_actors())
    fog_after = fog_actors(actors_after)
    if fog_after != fog_before:
        raise RuntimeError("Fog boundary changed during Light restoration")
    managed_after_list = [
        actor
        for actor in actors_after
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    ]
    managed_after = {
        actor.get_actor_label(): actor for actor in managed_after_list
    }
    if (
        len(managed_after_list) != len(managed_after)
        or set(managed_after) != expected_labels
    ):
        raise RuntimeError("Final managed Light actor set differs from metadata")
    if len(actors_after) != EXPECTED_BASE_ACTOR_COUNT + EXPECTED_SOURCE_LIGHT_COUNT:
        raise RuntimeError("Final StormPass actor count is unexpected")

    validation_failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
        "maximum_property_float_delta": 0.0,
    }
    validated_ies_count = 0
    for record in records:
        label = managed_label(record)
        actor = managed_after[label]
        issues, deltas = validate_actor(actor, record, profile)
        for name in maxima:
            maxima[name] = max(maxima[name], deltas[name])
        if expected_values(record)["uses_ies"]:
            component = get_light_component(
                actor, record["actor_type"] == "xxSpotLight"
            )
            validated_ies_count += int(
                component.get_editor_property("ies_texture") == profile
            )
        if issues:
            validation_failures.append({"label": label, "issues": issues})
    if validation_failures or validated_ies_count != EXPECTED_IES_REFERENCE_COUNT:
        raise RuntimeError(
            "Light validation failed: actors={} ies={}".format(
                len(validation_failures), validated_ies_count
            )
        )

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass after Light restoration")
    counts_by_level = collections.Counter(
        record["source_level"] for record in records
    )
    report = {
        "status": "restored",
        "operation": "exact_supported_source_local_light_restoration",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_metadata_path": METADATA_PATH,
        "profile_report_path": PROFILE_REPORT_PATH,
        "profile_asset_path": profile.get_path_name(),
        "profile_source_range": {
            "min": profile_report["source_min"],
            "max": profile_report["source_max"],
            "samples": profile_report["source_sample_count"],
            "nonzero_samples": profile_report[
                "source_nonzero_sample_count"
            ],
        },
        "source_light_count": len(records),
        "point_light_count": counters["point_lights"],
        "spot_light_count": counters["spot_lights"],
        "ies_binding_count": counters["ies_bindings"],
        "counts_by_level": dict(sorted(counts_by_level.items())),
        "placement_counters": dict(counters),
        "placement_records": placement_records,
        "property_application_failures": property_failures,
        "validation": {
            "managed_actor_count": len(managed_after),
            "failure_count": len(validation_failures),
            "failures": validation_failures,
            "validated_ies_binding_count": validated_ies_count,
            "maximum_deltas": maxima,
            "location_tolerance_cm": LOCATION_TOLERANCE_CM,
            "rotation_tolerance_degrees": ROTATION_TOLERANCE_DEGREES,
            "scale_tolerance": SCALE_TOLERANCE,
            "float_tolerance": FLOAT_TOLERANCE,
        },
        "source_property_audit": source_property_audit(records),
        "actor_counts": {
            "before": len(actors_before),
            "after": len(actors_after),
            "delta": len(actors_after) - len(actors_before),
            "base_without_managed_lights": base_actor_count,
        },
        "intensity_policy": {
            "source_to_lumens_multiplier": SOURCE_INTENSITY_TO_LUMENS,
            "minimum_lumens": 500.0,
            "maximum_lumens": 50000.0,
            "reason": "Same verified visual conversion used for HeinMach",
        },
        "color_policy": (
            "FModel ULightComponent LightColor bytes are assigned directly as "
            "unreal.Color to avoid a second sRGB transfer"
        ),
        "ies_policy": (
            "42 serialized JellyFish references use the native reconstructed "
            "TextureLightProfile with bUseIESBrightness=false; the exact "
            "source-authored intensity remains authoritative"
        ),
        "fog_boundary": {
            "status": "unchanged_and_deferred_until_final_pass",
            "before": fog_before,
            "after": fog_after,
        },
        "excluded_content": [
            "All StormPass Fog/Mist actors and materials",
            "Gameplay, character, enemy, spawn, quest, cinema and audio content",
            "Unavailable native xxLight tick animation and BBQCartoon renderer extensions",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT actors={} lights={} point={} spot={} ies={} failures=0 fog=0 report={}".format(
            len(actors_after),
            len(managed_after),
            counters["point_lights"],
            counters["spot_lights"],
            validated_ies_count,
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
        unreal.log_error("KHAZAN_STORMPASS_LIGHT_RESTORE: " + str(exception))
        raise
