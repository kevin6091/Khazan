"""Audit and repair HeinMach light color against cached FModel metadata.

The authoritative source color is the serialized sRGB ``FColor`` in
HeinMach_LevelData.json.  The earlier reconstruction normalized those bytes
and passed them through an additional sRGB conversion, whitening all 89 source
lights.  This pass writes the source bytes directly and verifies the declared
preview route-fill colors separately.
"""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
RECONSTRUCT_PATH = os.path.join(SCRIPT_DIR, "reconstruct_heinmach_environment.py")
POLISH_PATH = os.path.join(SCRIPT_DIR, "polish_heinmach_fog_lighting.py")
LEVEL_DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_LevelData.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_LightColor_Metadata_Audit.json",
)
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
SOURCE_PREFIX = "HM_SourceLight_"
ROUTE_PREFIX = "HM_PreviewRouteFill_"
EXPECTED_SOURCE_COUNT = 89
FLOAT_TOLERANCE = 0.001
ROUTE_COLOR_BYTE_TOLERANCE = 0.005


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load helper module: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def light_source_properties(record):
    for component in record.get("components", []):
        if "LightComponent" in str(component.get("type", "")):
            properties = component.get("properties", {})
            return properties if isinstance(properties, dict) else {}
    return {}


def source_color(properties):
    color = properties.get("LightColor", {}) or {}
    return tuple(int(color.get(channel, 255)) for channel in ("R", "G", "B", "A"))


def actual_color(component):
    color = safe_property(component, "light_color")
    if not color:
        return None
    return tuple(int(getattr(color, channel)) for channel in ("r", "g", "b", "a"))


def nearly_equal(left, right, tolerance=FLOAT_TOLERANCE):
    return abs(float(left) - float(right)) <= tolerance


def transform_signature(actors):
    records = []
    for actor in actors:
        if not actor.get_actor_label().startswith(SOURCE_PREFIX):
            continue
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        records.append(
            {
                "label": actor.get_actor_label(),
                "location": [location.x, location.y, location.z],
                "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
                "scale": [scale.x, scale.y, scale.z],
            }
        )
    records.sort(key=lambda item: item["label"])
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def component_for(actor, record):
    component_class = (
        unreal.SpotLightComponent
        if record.get("actor_type") == "xxSpotLight"
        else unreal.PointLightComponent
    )
    return actor.get_component_by_class(component_class) if actor else None


def audit_source_lights(records, actors_by_label):
    mismatches = []
    color_pairs = collections.Counter()
    missing = []
    property_counts = collections.Counter()
    for record in records:
        label = SOURCE_PREFIX + str(record.get("actor_name", "Unknown"))
        actor = actors_by_label.get(label)
        component = component_for(actor, record)
        if not actor or not component:
            missing.append(label)
            continue
        source = light_source_properties(record)
        expected_color = source_color(source)
        observed_color = actual_color(component)
        color_pairs[(expected_color, observed_color)] += 1

        expected = {
            "light_color": expected_color,
            "intensity": max(
                500.0,
                min(
                    50000.0,
                    float(source.get("Intensity", 2.0))
                    * float(reconstruct.SOURCE_INTENSITY_TO_LUMENS),
                ),
            ),
            "attenuation_radius": float(source.get("AttenuationRadius", 2000.0)),
            "volumetric_scattering_intensity": float(
                source.get("VolumetricScatteringIntensity", 1.0)
            ),
            "specular_scale": float(source.get("SpecularScale", 0.0)),
            "cast_shadows": bool(source.get("CastShadows", False)),
            "use_inverse_squared_falloff": bool(
                source.get("bUseInverseSquaredFalloff", True)
            ),
        }
        if record.get("actor_type") == "xxSpotLight":
            expected["outer_cone_angle"] = float(source.get("OuterConeAngle", 44.0))
        for source_name, property_name in (
            ("LightFalloffExponent", "light_falloff_exponent"),
            ("MaxDrawDistance", "max_draw_distance"),
            ("MaxDistanceFadeRange", "max_distance_fade_range"),
            ("IndirectLightingIntensity", "indirect_lighting_intensity"),
        ):
            if source_name in source:
                expected[property_name] = float(source[source_name])

        for property_name, expected_value in expected.items():
            actual_value = (
                observed_color
                if property_name == "light_color"
                else safe_property(component, property_name)
            )
            equal = (
                actual_value == expected_value
                if isinstance(expected_value, (tuple, bool))
                else actual_value is not None and nearly_equal(actual_value, expected_value)
            )
            if not equal:
                property_counts[property_name] += 1
                mismatches.append(
                    {
                        "label": label,
                        "property": property_name,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )
    color_pair_records = [
        {
            "source_rgba": list(expected),
            "actual_rgba": list(actual) if actual else None,
            "light_count": count,
        }
        for (expected, actual), count in sorted(
            color_pairs.items(), key=lambda item: (item[0][0], item[0][1] or ())
        )
    ]
    return {
        "source_light_count": len(records),
        "missing_light_labels": missing,
        "mismatch_count": len(mismatches),
        "mismatch_by_property": dict(sorted(property_counts.items())),
        "mismatches": mismatches,
        "color_pairs": color_pair_records,
    }


def audit_route_fills(polish, actors_by_label):
    mismatches = []
    records = []
    for spec in polish.ROUTE_FILL_SPECS:
        label = ROUTE_PREFIX + spec["tag"]
        actor = actors_by_label.get(label)
        component = (
            actor.get_component_by_class(unreal.PointLightComponent) if actor else None
        )
        expected = tuple(float(value) for value in spec["color_linear"])
        actual = None
        if component:
            value = component.get_light_color()
            actual = (float(value.r), float(value.g), float(value.b))
        if not actual or any(
            not nearly_equal(a, b, ROUTE_COLOR_BYTE_TOLERANCE)
            for a, b in zip(actual, expected)
        ):
            mismatches.append(
                {"label": label, "expected_linear_rgb": expected, "actual_linear_rgb": actual}
            )
        records.append(
            {
                "label": label,
                "expected_linear_rgb": expected,
                "actual_linear_rgb": actual,
                "source_status": "preview approximation; no direct source-light record",
            }
        )
    return {"count": len(records), "mismatch_count": len(mismatches), "lights": records}


def load_level_if_needed():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    return level_subsystem


def main(apply_changes=False):
    global reconstruct
    reconstruct = load_module("khazan_light_reconstruct", RECONSTRUCT_PATH)
    polish = load_module("khazan_light_polish", POLISH_PATH)
    data = load_json(LEVEL_DATA_PATH)
    records = [
        record
        for record in data.get("lights", [])
        if record.get("source_level") == "HeinMach_Light"
        and record.get("actor_type") in ("xxPointLight", "xxSpotLight")
    ]
    if len(records) != EXPECTED_SOURCE_COUNT:
        raise RuntimeError("Source light inventory changed: {}".format(len(records)))

    level_subsystem = load_level_if_needed()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    by_label_before = {actor.get_actor_label(): actor for actor in actors_before}
    transform_before = transform_signature(actors_before)
    audit_before = audit_source_lights(records, by_label_before)
    route_before = audit_route_fills(polish, by_label_before)
    property_failures = []
    repaired_labels = []
    route_fill_repaired_labels = []

    if apply_changes:
        if audit_before["missing_light_labels"]:
            raise RuntimeError("Cannot repair missing source-light actors")
        for record in records:
            label = SOURCE_PREFIX + str(record.get("actor_name", "Unknown"))
            actor = by_label_before[label]
            component = component_for(actor, record)
            reconstruct.apply_source_light(
                component, light_source_properties(record), property_failures
            )
            repaired_labels.append(label)
        if route_before["mismatch_count"]:
            route_results = polish.create_route_fill_lights(
                actor_subsystem, actors_before
            )
            route_fill_repaired_labels = [item["label"] for item in route_results]
        if property_failures:
            raise RuntimeError("Source light property repair failed: {}".format(property_failures[0]))
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save source-light color repair")

    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    by_label_after = {actor.get_actor_label(): actor for actor in actors_after}
    transform_after = transform_signature(actors_after)
    audit_after = audit_source_lights(records, by_label_after)
    route_after = audit_route_fills(polish, by_label_after)
    if apply_changes and transform_after != transform_before:
        raise RuntimeError("Source-light transforms changed during color repair")
    if apply_changes and audit_after["mismatch_count"]:
        raise RuntimeError("Source-light metadata mismatches remain after repair")
    if apply_changes and route_after["mismatch_count"]:
        raise RuntimeError("Declared route-fill colors do not match the live map")

    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "source_metadata": LEVEL_DATA_PATH,
        "apply_changes": bool(apply_changes),
        "source_light_transform_before": transform_before,
        "source_light_transform_after": transform_after,
        "source_light_audit_before": audit_before,
        "source_light_audit_after": audit_after,
        "route_fill_audit_before": route_before,
        "route_fill_audit_after": route_after,
        "repaired_label_count": len(repaired_labels),
        "route_fill_repaired_labels": route_fill_repaired_labels,
        "property_failures": property_failures,
        "color_policy": (
            "FModel LightColor R/G/B/A bytes are written directly to ULightComponent.light_color. "
            "Do not normalize then call SetLightColor with bSRGB=True."
        ),
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    try:
        main(False)
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        raise
