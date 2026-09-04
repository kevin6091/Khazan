"""Repair and audit only HeinMach FogSheet and preview global fog content.

This intentionally does not restore missing non-fog actors, touch gameplay source,
or recalibrate any light.  User/optimization tombstones are treated as immutable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
MAP_FILE = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Maps",
    "L_HeinMach_Environment.umap",
)
BACKUP_MAP_FILE = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ArtBackups",
    "HeinMach_PreFogReview_20260904_143116",
    "Map",
    "L_HeinMach_Environment.umap",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_FogIntegrity_Review.json",
)
FOG_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "restore_heinmach_fog_sheets.py")
POLISH_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "polish_heinmach_fog_lighting.py")
EXCLUSION_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "heinmach_exclusions.py")
EXPECTED_FOG_COUNT = 50
EXPECTED_ACTOR_COUNT_AT_REVIEW = 9328
FOG_LABEL_PREFIX = "HM_FogSheet_"
GLOBAL_FOG_LABEL = "HM_PreviewVolumetricFog"


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load helper module: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def actor_transform_signature(actors):
    records = []
    for actor in actors:
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
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


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


def set_component_property(component, name, value, changed, failures):
    try:
        current = component.get_editor_property(name)
        if current != value:
            component.set_editor_property(name, value)
            changed.append(name)
    except Exception as exception:
        failures.append({"property": name, "error": str(exception)})


def apply_source_component_policy(component):
    changed = []
    failures = []
    for name, value in (
        ("cast_shadow", False),
        ("cast_dynamic_shadow", False),
        ("cast_static_shadow", False),
        ("cast_volumetric_translucent_shadow", False),
        ("receives_decals", False),
        ("use_as_occluder", False),
        ("affect_dynamic_indirect_lighting", False),
        ("affect_distance_field_lighting", False),
        ("generate_overlap_events", False),
        ("can_ever_affect_navigation", False),
        ("hidden_in_game", False),
        ("visible", True),
    ):
        set_component_property(component, name, value, changed, failures)
    try:
        if component.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            changed.append("collision_enabled")
    except Exception as exception:
        failures.append({"property": "collision_enabled", "error": str(exception)})
    return {"changed": sorted(changed), "failures": failures}


def fog_actor_audit(actors, records, fog, base_material):
    by_label = {actor.get_actor_label(): actor for actor in actors}
    expected_labels = {fog.managed_label(record) for record in records}
    actual_labels = {
        label for label in by_label if label.startswith(FOG_LABEL_PREFIX)
    }
    missing = sorted(expected_labels - actual_labels)
    unexpected = sorted(actual_labels - expected_labels)
    mismatches = []
    max_error = {"location_cm": 0.0, "rotation_degrees": 0.0, "scale": 0.0}
    component_policy = {}
    for record in records:
        label = fog.managed_label(record)
        actor = by_label.get(label)
        if not actor:
            continue
        transform = record.get("transform", {})
        errors = {
            "location_cm": vector_error(
                actor.get_actor_location(), transform.get("location_cm", {})
            ),
            "rotation_degrees": rotation_error(
                actor.get_actor_rotation(), transform.get("rotation_degrees", {})
            ),
            "scale": vector_error(actor.get_actor_scale3d(), transform.get("scale", {})),
        }
        for key, value in errors.items():
            max_error[key] = max(max_error[key], value)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            mismatches.append({"label": label, "reason": "component_missing"})
            continue
        component_policy[label] = apply_source_component_policy(component)
        mesh = component.get_editor_property("static_mesh")
        material = component.get_material(0)
        expected_name = fog.instance_asset_name(record)
        expected_material_path = (
            fog.FOG_MATERIAL_ROOT + "/" + expected_name + "." + expected_name
        )
        parent = material.get_editor_property("parent") if material else None
        reasons = []
        if (
            errors["location_cm"] > 0.01
            or errors["rotation_degrees"] > 0.001
            or errors["scale"] > 0.00001
        ):
            reasons.append("transform")
        if not mesh or mesh.get_name() != "SM_FS_FogSheet_Plane":
            reasons.append("mesh")
        if not material or material.get_path_name() != expected_material_path:
            reasons.append("material")
        if parent != base_material:
            reasons.append("parent")
        if int(component.get_editor_property("translucency_sort_priority")) != int(
            record.get("translucency_sort_priority", 0)
        ):
            reasons.append("sort_priority")
        if component_policy[label]["failures"]:
            reasons.append("component_policy")
        if reasons:
            mismatches.append({"label": label, "reasons": reasons, "errors": errors})
    return {
        "expected_count": len(expected_labels),
        "actual_count": len(actual_labels),
        "missing": missing,
        "unexpected": unexpected,
        "max_transform_error": max_error,
        "mismatches": mismatches,
        "component_policy_changed_actor_count": sum(
            bool(item["changed"]) for item in component_policy.values()
        ),
        "component_policy_changes": {
            label: item["changed"]
            for label, item in component_policy.items()
            if item["changed"]
        },
        "component_policy_failures": [
            {"label": label, "failures": item["failures"]}
            for label, item in component_policy.items()
            if item["failures"]
        ],
    }


def material_graph_audit(material):
    library = unreal.MaterialEditingLibrary
    classes = [
        node.get_class().get_name()
        for node in library.get_material_expressions(material)
        if node
    ]
    class_counts = {name: classes.count(name) for name in sorted(set(classes))}
    required = {
        "MaterialExpressionWorldPosition",
        "MaterialExpressionCameraPositionWS",
        "MaterialExpressionDistance",
        "MaterialExpressionDepthFade",
        "MaterialExpressionPixelNormalWS",
        "MaterialExpressionCameraVectorWS",
        "MaterialExpressionDotProduct",
    }
    return {
        "asset": material.get_path_name(),
        "preview_version": unreal.EditorAssetLibrary.get_metadata_tag(
            material, "KhazanFogPreviewVersion"
        ),
        "distance_model": unreal.EditorAssetLibrary.get_metadata_tag(
            material, "KhazanFogDistanceModel"
        ),
        "expression_count": int(library.get_num_material_expressions(material)),
        "expression_class_counts": class_counts,
        "missing_required_expression_classes": sorted(required - set(classes)),
        "pixel_depth_count": classes.count("MaterialExpressionPixelDepth"),
        "blend_mode": str(material.get_editor_property("blend_mode")),
        "shading_model": str(material.get_editor_property("shading_model")),
        "two_sided": bool(material.get_editor_property("two_sided")),
        "disable_depth_test": bool(material.get_editor_property("disable_depth_test")),
    }


def global_fog_audit(actors):
    matches = [actor for actor in actors if actor.get_actor_label() == GLOBAL_FOG_LABEL]
    all_height_fog = [
        actor for actor in actors if isinstance(actor, unreal.ExponentialHeightFog)
    ]
    if len(matches) != 1:
        return {
            "named_count": len(matches),
            "all_height_fog_count": len(all_height_fog),
            "mismatch": "expected exactly one managed global fog",
        }
    actor = matches[0]
    component = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    albedo = component.get_editor_property("volumetric_fog_albedo")
    expected_albedo = (158.0 / 255.0, 177.0 / 255.0, 196.0 / 255.0)
    actual_albedo = (float(albedo.r), float(albedo.g), float(albedo.b))
    if max(actual_albedo) > 1.0:
        actual_albedo = tuple(channel / 255.0 for channel in actual_albedo)
    return {
        "named_count": len(matches),
        "all_height_fog_count": len(all_height_fog),
        "actor": actor.get_path_name(),
        "location": [
            actor.get_actor_location().x,
            actor.get_actor_location().y,
            actor.get_actor_location().z,
        ],
        "fog_density": float(component.get_editor_property("fog_density")),
        "fog_height_falloff": float(
            component.get_editor_property("fog_height_falloff")
        ),
        "fog_max_opacity": float(component.get_editor_property("fog_max_opacity")),
        "start_distance": float(component.get_editor_property("start_distance")),
        "fog_cutoff_distance": float(
            component.get_editor_property("fog_cutoff_distance")
        ),
        "volumetric_enabled": bool(
            component.get_editor_property("enable_volumetric_fog")
        ),
        "volumetric_distance": float(
            component.get_editor_property("volumetric_fog_distance")
        ),
        "volumetric_albedo": list(actual_albedo),
        "volumetric_albedo_max_error": max(
            abs(actual_albedo[index] - expected_albedo[index]) for index in range(3)
        ),
        "visible": bool(component.get_editor_property("visible")),
        "hidden_in_game": bool(component.get_editor_property("hidden_in_game")),
    }


def main():
    fog = load_module("khazan_heinmach_fog_integrity_helpers", FOG_SCRIPT_PATH)
    polish = load_module("khazan_heinmach_fog_integrity_polish", POLISH_SCRIPT_PATH)
    exclusions = load_module(
        "khazan_heinmach_fog_integrity_exclusions", EXCLUSION_SCRIPT_PATH
    )

    if not os.path.isfile(BACKUP_MAP_FILE):
        raise RuntimeError("Pre-review binary backup is missing: " + BACKUP_MAP_FILE)
    if sha256_file(MAP_FILE) != sha256_file(BACKUP_MAP_FILE):
        raise RuntimeError("Live map no longer matches the pre-review safety backup")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    labels_before = {actor.get_actor_label() for actor in actors_before}
    signature_before = actor_transform_signature(actors_before)
    excluded_present_before = sorted(exclusions.exclusion_labels() & labels_before)
    if excluded_present_before:
        raise RuntimeError("A user/optimization tombstone is present before Fog repair")

    gap_report = fog.load_json(fog.GAP_REPORT_PATH)
    records = list(gap_report.get("fog_sheet_actors", []))
    if len(records) != EXPECTED_FOG_COUNT:
        raise RuntimeError("Expected exactly 50 authoritative FogSheet records")
    if any(record.get("source_level", "").startswith("HeinMach_Cine_") for record in records):
        raise RuntimeError("Cinematic FogSheet data entered the environment inventory")

    noise_texture = unreal.EditorAssetLibrary.load_asset(fog.NOISE_TEXTURE_PATH)
    if not noise_texture:
        raise RuntimeError("Recovered Fog noise texture is missing")
    base_material = polish.create_fog_material(fog, noise_texture)
    instances = polish.update_fog_material_instances(
        fog, records, base_material, noise_texture
    )
    assignment_mismatches = polish.ensure_fog_assignments(
        fog, actors_before, records, instances
    )
    if assignment_mismatches:
        raise RuntimeError("Fog material assignment validation failed")

    global_fog_change = polish.ensure_volumetric_fog(
        actor_subsystem, list(actor_subsystem.get_all_level_actors())
    )
    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    fog_audit = fog_actor_audit(actors_after, records, fog, base_material)
    graph_audit = material_graph_audit(base_material)
    global_audit = global_fog_audit(actors_after)
    signature_after = actor_transform_signature(actors_after)
    labels_after = {actor.get_actor_label() for actor in actors_after}
    excluded_present_after = sorted(exclusions.exclusion_labels() & labels_after)

    checks = {
        "pre_review_actor_count_matches": len(actors_before)
        == EXPECTED_ACTOR_COUNT_AT_REVIEW,
        "actor_count_preserved": len(actors_after) == len(actors_before),
        "all_actor_transforms_preserved": signature_after == signature_before,
        "actor_labels_preserved": labels_after == labels_before,
        "all_tombstones_absent_before": not excluded_present_before,
        "all_tombstones_absent_after": not excluded_present_after,
        "fog_count_exact": fog_audit["actual_count"] == EXPECTED_FOG_COUNT,
        "fog_placement_exact": not fog_audit["missing"]
        and not fog_audit["unexpected"]
        and not fog_audit["mismatches"],
        "fog_component_policy_exact": not fog_audit[
            "component_policy_failures"
        ],
        "fog_v5_graph_complete": not graph_audit[
            "missing_required_expression_classes"
        ],
        "fog_pixel_depth_absent": graph_audit["pixel_depth_count"] == 0,
        "fog_depth_test_enabled": not graph_audit["disable_depth_test"],
        "fog_material_one_sided": not graph_audit["two_sided"],
        "global_fog_unique": global_audit.get("named_count") == 1
        and global_audit.get("all_height_fog_count") == 1,
        "global_fog_continuous": global_audit.get("fog_cutoff_distance") == 0.0,
        "global_fog_albedo_channels_correct": global_audit.get(
            "volumetric_albedo_max_error", 1.0
        )
        < 0.0001,
        "global_volumetric_fog_enabled": bool(global_audit.get("volumetric_enabled")),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError("Fog integrity checks failed: " + ", ".join(failed))

    unreal.EditorAssetLibrary.save_directory(
        fog.FOG_ROOT, only_if_is_dirty=False, recursive=True
    )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach map after Fog-only repair")

    report = {
        "status": "repaired_and_verified",
        "map_path": MAP_PATH,
        "scope": "FogSheet assets/assignments/component policy and preview global fog only",
        "checks": checks,
        "map_backup": {
            "path": BACKUP_MAP_FILE,
            "sha256": sha256_file(BACKUP_MAP_FILE),
        },
        "actor_count_before": len(actors_before),
        "actor_count_after": len(actors_after),
        "actor_transform_signature_before": signature_before,
        "actor_transform_signature_after": signature_after,
        "fog_sheet": fog_audit,
        "material_graph": graph_audit,
        "material_instances": {
            "count": len(instances),
            "updated_count": sum(bool(item["updated"]) for item in instances.values()),
            "assignment_mismatches": assignment_mismatches,
        },
        "global_fog": global_audit,
        "global_fog_change": global_fog_change,
        "tombstones": {
            "registered_count": len(exclusions.exclusion_labels()),
            "present_before": excluded_present_before,
            "present_after": excluded_present_after,
        },
        "source_evidence": {
            "fog_sheet_records": fog.GAP_REPORT_PATH,
            "fog_sheet_blueprint": (
                "C:/Users/user/Desktop/카잔/Exports/BBQ/Content/_Kazan_/Art/"
                "Terrain/Terrain_VFX/WBP_FogSheet.json"
            ),
            "global_profiles": [
                "C:/Users/user/Desktop/카잔/Exports/BBQ/Content/Art/"
                "ArtRendering/AR_Data/Fog/FOG_Deep.json",
                "C:/Users/user/Desktop/카잔/Exports/BBQ/Content/Art/"
                "ArtRendering/AR_Data/Fog/FOG_Outdoor.json",
            ],
            "global_policy": (
                "The source switches FOG_Deep and FOG_Dark per WEP region. The "
                "single UE preview actor remains deliberately low-density; this repair "
                "only removes the hard cutoff and corrects the reversed cool albedo."
            ),
        },
        "excluded_content": [
            "all user/optimization tombstones",
            "all non-fog actor creation or transform edits",
            "all lights, post process, tutorial and gameplay/source code",
            "all HeinMach_Cine_* Fog actors",
        ],
    }
    write_json(REPORT_PATH, report)
    unreal.log(
        "KHAZAN_HEINMACH_FOG_INTEGRITY: RESULT passed=True actors={} fog={} "
        "material_v={} expressions={} report={}".format(
            len(actors_after),
            fog_audit["actual_count"],
            graph_audit["preview_version"],
            graph_audit["expression_count"],
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
        unreal.log_error("KHAZAN_HEINMACH_FOG_INTEGRITY: " + str(exception))
        raise
