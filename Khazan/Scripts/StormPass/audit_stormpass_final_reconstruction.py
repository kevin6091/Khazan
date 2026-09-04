"""Read-only, saved-map final audit for the complete StormPass reconstruction.

The audit reloads the map and validates every managed stage in its final state:
root props, inherited child props, landscape components, foliage HISMs, source
lights, the deliberately-last Fog sheets, and the restored environment profile.
It does not repair or save assets.
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
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
DEV_MAP_PATH = "/Game/Maps/DevMap"
MAP_DISK_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Maps",
    "L_StormPass_Environment.umap",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Final_Reconstruction_Audit.json",
)
ROOT_PLACEMENT_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_ResolvedRootPlacements.json",
)
ROOT_MATERIAL_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_OverrideMaterial_Restoration.json",
)
MODULE_PATHS = {
    "child": os.path.join(SCRIPT_DIR, "restore_stormpass_child_render_meshes.py"),
    "landscape": os.path.join(SCRIPT_DIR, "restore_stormpass_landscape.py"),
    "foliage": os.path.join(SCRIPT_DIR, "restore_stormpass_foliage.py"),
    "light": os.path.join(SCRIPT_DIR, "restore_stormpass_lights.py"),
    "fog": os.path.join(SCRIPT_DIR, "restore_stormpass_fog.py"),
    "water": os.path.join(
        SCRIPT_DIR, "restore_stormpass_native_water_materials.py"
    ),
    "environment": os.path.join(
        SCRIPT_DIR, "restore_stormpass_environment_profile.py"
    ),
    "tree_material": os.path.join(
        SCRIPT_DIR, "repair_stormpass_tree_foliage_materials.py"
    ),
    "false_emissive": os.path.join(
        SCRIPT_DIR, "repair_stormpass_false_emissive_worldprops.py"
    ),
    "ore_material": os.path.join(
        SCRIPT_DIR, "repair_stormpass_ore_materials.py"
    ),
}
EXPECTED_PREFIX_COUNTS = {
    "SP_Prop_": 13050,
    "SP_ChildProp_": 551,
    "SP_Landscape_": 456,
    "SP_Foliage_": 218,
    "SP_SourceLight_": 53,
    "SP_Fog_": 53,
    "SP_Environment_": 27,
}
EXPECTED_TOTAL_ACTOR_COUNT = sum(EXPECTED_PREFIX_COUNTS.values())
ROOT_LOCATION_TOLERANCE_CM = 0.002
ROOT_ROTATION_TOLERANCE_DEGREES = 0.003
ROOT_SCALE_TOLERANCE = 0.000002
ENGINE_BASIC_SHAPE = "Engine/Content/BasicShapes/BasicShapeMaterial"
ENGINE_BASIC_SHAPE_PATH = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"


def log(message):
    unreal.log("KHAZAN_STORMPASS_FINAL_AUDIT: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


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
    return digest.hexdigest().upper()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_final_" + name, path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load final-audit helper: " + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_quaternion(rotation):
    quat = rotation if isinstance(rotation, unreal.Quat) else rotation.quaternion()
    values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
    length = math.sqrt(sum(value * value for value in values))
    if length <= 1.0e-12:
        raise RuntimeError("Encountered a zero quaternion during final audit")
    return [value / length for value in values]


def rotation_delta_degrees(left, right):
    left_values = canonical_quaternion(left)
    right_values = canonical_quaternion(right)
    dot = min(1.0, abs(sum(a * b for a, b in zip(left_values, right_values))))
    return math.degrees(2.0 * math.acos(dot))


def source_vector(value, default=0.0):
    return unreal.Vector(
        float(value.get("x", default)),
        float(value.get("y", default)),
        float(value.get("z", default)),
    )


def source_rotator(value):
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def vector_delta(left, right):
    return max(
        abs(float(left.x) - float(right.x)),
        abs(float(left.y) - float(right.y)),
        abs(float(left.z) - float(right.z)),
    )


def root_label(placement):
    return (
        "SP_Prop_{}_{}_{}".format(
            placement.get("source_level", "Unknown"),
            placement.get("source_object_index", 0),
            placement.get("actor_name", "Actor"),
        )
    )[:220]


def audit_inventory(actors):
    counts = {
        prefix: sum(actor.get_actor_label().startswith(prefix) for actor in actors)
        for prefix in EXPECTED_PREFIX_COUNTS
    }
    recognized = sum(counts.values())
    labels = [actor.get_actor_label() for actor in actors]
    duplicate_labels = sorted(
        label
        for label, count in collections.Counter(labels).items()
        if count > 1
    )
    unrecognized = sorted(
        {
            actor.get_actor_label()
            for actor in actors
            if not any(
                actor.get_actor_label().startswith(prefix)
                for prefix in EXPECTED_PREFIX_COUNTS
            )
        }
    )
    failures = []
    if len(actors) != EXPECTED_TOTAL_ACTOR_COUNT:
        failures.append("total_actor_count")
    if counts != EXPECTED_PREFIX_COUNTS:
        failures.append("prefix_counts")
    if recognized != len(actors):
        failures.append("unrecognized_actors")
    if duplicate_labels:
        failures.append("duplicate_labels")
    return {
        "total_actor_count": len(actors),
        "expected_total_actor_count": EXPECTED_TOTAL_ACTOR_COUNT,
        "prefix_counts": counts,
        "expected_prefix_counts": EXPECTED_PREFIX_COUNTS,
        "recognized_actor_count": recognized,
        "unrecognized_actor_count": len(unrecognized),
        "unrecognized_actors": unrecognized,
        "duplicate_label_count": len(duplicate_labels),
        "duplicate_labels": duplicate_labels,
        "failure_count": len(failures),
        "failures": failures,
    }


def audit_root_props(actors):
    placements = list(load_json(ROOT_PLACEMENT_PATH).get("placements", []))
    restoration = load_json(ROOT_MATERIAL_REPORT_PATH)
    if len(placements) != EXPECTED_PREFIX_COUNTS["SP_Prop_"]:
        raise RuntimeError("Final root source placement inventory changed")
    if restoration.get("status") != "restored":
        raise RuntimeError("Final root material restoration report is incomplete")

    expected_meshes = {}
    slot_maps = {}
    source_material_paths = collections.defaultdict(list)
    for mesh_record in restoration.get("mesh_mappings", []):
        package = mesh_record["mesh_package"]
        expected_meshes[package] = mesh_record["mesh_path"]
        slot_maps[package] = {
            int(item["source_slot"]): int(item["ue_slot"])
            for item in mesh_record.get("assignments", [])
        }
        for item in mesh_record.get("assignments", []):
            source_package = item.get("source_package")
            actual_path = item.get("actual_material_path")
            if source_package and actual_path:
                source_material_paths[source_package].append(actual_path)
    rebuilt_materials = {
        item["package"]: item["material_path"]
        for item in restoration.get("material_results", [])
    }
    resolved_existing = {
        package: collections.Counter(paths).most_common(1)[0][0]
        for package, paths in source_material_paths.items()
        if paths
    }
    resolved_existing[ENGINE_BASIC_SHAPE] = ENGINE_BASIC_SHAPE_PATH

    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith("SP_Prop_")
    }
    expected_labels = {root_label(placement) for placement in placements}
    failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    material_counts = collections.Counter()
    for placement in placements:
        label = root_label(placement)
        actor = managed.get(label)
        issues = []
        if not actor:
            failures.append({"label": label, "issues": ["missing_actor"]})
            continue
        if not isinstance(actor, unreal.StaticMeshActor):
            issues.append("actor_class")
        transform = placement["transform"]
        expected_location = source_vector(transform["location_cm"])
        expected_rotation = source_rotator(transform["rotation_degrees"])
        expected_scale = source_vector(transform["scale"], default=1.0)
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
        if deltas["location_delta_cm"] > ROOT_LOCATION_TOLERANCE_CM:
            issues.append("transform_location")
        if deltas["rotation_delta_degrees"] > ROOT_ROTATION_TOLERANCE_DEGREES:
            issues.append("transform_rotation")
        if deltas["scale_delta"] > ROOT_SCALE_TOLERANCE:
            issues.append("transform_scale")
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            issues.append("component_missing")
        else:
            mesh = component.get_editor_property("static_mesh")
            mesh_path = mesh.get_path_name() if mesh else None
            mesh_package = placement["static_mesh_package"]
            if mesh_path != expected_meshes.get(mesh_package):
                issues.append("mesh")
            if component.get_editor_property("mobility") != unreal.ComponentMobility.STATIC:
                issues.append("mobility")
            if bool(component.get_editor_property("cast_shadow")) != bool(
                placement.get("cast_shadow", True)
            ):
                issues.append("cast_shadow")
            slot_map = slot_maps.get(mesh_package, {})
            for source_slot, package in enumerate(
                placement.get("override_material_packages", [])
            ):
                if not package:
                    continue
                material_counts["source"] += 1
                ue_slot = slot_map.get(source_slot)
                if ue_slot is None:
                    material_counts["non_render"] += 1
                    continue
                material_counts["render"] += 1
                expected_material = rebuilt_materials.get(package) or resolved_existing.get(
                    package
                )
                actual_material = component.get_material(ue_slot)
                actual_path = actual_material.get_path_name() if actual_material else None
                if not expected_material:
                    material_counts["unresolved"] += 1
                    issues.append("material_unresolved")
                elif actual_path == expected_material:
                    material_counts["matched"] += 1
                else:
                    material_counts["mismatch"] += 1
                    issues.append("material:{}".format(source_slot))
        if issues:
            failures.append({"label": label, "issues": sorted(set(issues))})
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    if (
        material_counts["source"] != 10489
        or material_counts["render"] != 7717
        or material_counts["matched"] != 7717
        or material_counts["non_render"] != 2772
        or material_counts["unresolved"]
        or material_counts["mismatch"]
    ):
        failures.append({"label": "<material-counts>", "issues": [dict(material_counts)]})
    return {
        "source_placement_count": len(placements),
        "managed_actor_count": len(managed),
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "failure_count": len(failures),
        "failures": failures[:20],
        "maximum_transform_deltas": maxima,
        "material_binding_counts": dict(material_counts),
    }


def audit_child_props(actors, child):
    child.configure_shared()
    child.shared.expected_world_transform = child.expected_world_transform
    source = child.shared.load_json(child.AUDIT_PATH)
    records, packages, expected_labels = child.accepted_records(source)
    restoration = child.shared.load_json(child.REPORT_PATH)
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(child.MANAGED_LABEL_PREFIX)
    }
    placement_failures = child.shared.validate_placements(records, managed)
    material_result = restoration.get("material_restoration", {})
    slot_maps = {
        item["mesh_package"]: {
            int(assignment["source_slot"]): int(assignment["ue_slot"])
            for assignment in item.get("assignments", [])
        }
        for item in material_result.get("mesh_slot_mappings", [])
    }
    material_paths = {
        item["package"]: item["material_path"]
        for item in material_result.get("material_resolution", [])
    }
    checks = 0
    mismatches = []
    non_render = 0
    for record in records:
        label = child.shared.managed_label(record)
        actor = managed.get(label)
        if not actor:
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mapping = slot_maps.get(record["static_mesh_package"], {})
        for source_slot, package in enumerate(
            record.get("override_material_packages", [])
        ):
            if not package:
                continue
            ue_slot = mapping.get(source_slot)
            if ue_slot is None:
                non_render += 1
                continue
            checks += 1
            actual_material = component.get_material(ue_slot) if component else None
            actual = actual_material.get_path_name() if actual_material else None
            expected = material_paths.get(package)
            if actual != expected:
                mismatches.append(
                    {"label": label, "source_slot": source_slot, "actual": actual, "expected": expected}
                )
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    failure_count = (
        len(placement_failures)
        + len(mismatches)
        + len(missing)
        + len(extra)
        + int(checks != child.EXPECTED_OVERRIDE_REFERENCE_COUNT)
        + int(non_render != 0)
    )
    return {
        "source_component_count": len(records),
        "source_mesh_count": len(packages),
        "managed_actor_count": len(managed),
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "placement_mismatch_count": len(placement_failures),
        "material_override_check_count": checks,
        "material_mismatch_count": len(mismatches),
        "non_render_reference_count": non_render,
        "failure_count": failure_count,
        "placement_failures": placement_failures[:20],
        "material_mismatches": mismatches[:20],
    }


def audit_landscape(actors, landscape):
    grouped = landscape.records_by_group()
    materials, material_report = landscape.load_verified_materials()
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(landscape.MANAGED_LABEL_PREFIX)
    }
    failures, group_counts = landscape.validate_components(
        grouped, materials, managed
    )
    expected_labels = {
        landscape.managed_label(record)
        for record in grouped["Main"] + grouped["Boss"]
    }
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    return {
        "source_component_count": landscape.EXPECTED_COMPONENT_COUNT,
        "managed_actor_count": len(managed),
        "group_counts": group_counts,
        "material_build_status": material_report.get("status"),
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "component_failure_count": len(failures),
        "failure_count": len(failures) + len(missing) + len(extra),
        "failures": failures[:20],
    }


def audit_foliage(actors, foliage):
    metadata, records, expected_labels = foliage.source_inventory()
    asset_report, meshes, slot_maps = foliage.prepared_assets(records)
    material_report, materials = foliage.prepared_materials(records)
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(foliage.MANAGED_LABEL_PREFIX)
    }
    failures = []
    component_count = 0
    instance_count = 0
    override_count = 0
    transform_failure_count = 0
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
    }
    for record in records:
        label = foliage.managed_label(record)
        actor = managed.get(label)
        if not actor:
            failures.append({"label": label, "issues": ["missing_actor"]})
            continue
        components = list(
            actor.get_components_by_class(unreal.FoliageInstancedStaticMeshComponent)
        )
        component_count += len(components)
        if len(components) != 1:
            failures.append({"label": label, "issues": ["component_count"]})
            continue
        component = components[0]
        issues, component_maxima, overrides, transform_failures = foliage.validate_component(
            component,
            record,
            meshes[record["static_mesh_package"]],
            slot_maps[record["static_mesh_package"]],
            materials,
        )
        instance_count += component.get_instance_count()
        override_count += overrides
        transform_failure_count += transform_failures
        for name, value in component_maxima.items():
            maxima[name] = max(maxima[name], value)
        if issues:
            failures.append({"label": label, "issues": issues})
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    aggregate_failures = sum(
        (
            component_count != foliage.EXPECTED_COMPONENT_COUNT,
            instance_count != foliage.EXPECTED_INSTANCE_COUNT,
            override_count != foliage.EXPECTED_OVERRIDE_REFERENCE_COUNT,
            transform_failure_count != 0,
        )
    )
    return {
        "managed_actor_count": len(managed),
        "component_count": component_count,
        "instance_count": instance_count,
        "override_reference_count": override_count,
        "instance_transform_failure_count": transform_failure_count,
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "component_failure_count": len(failures),
        "failure_count": len(failures) + len(missing) + len(extra) + aggregate_failures,
        "maximum_transform_deltas": maxima,
        "failures": failures[:20],
    }


def audit_lights(actors, light):
    metadata, records, expected_labels = light.source_inventory()
    profile_report, profile = light.prepared_profile()
    managed = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(light.MANAGED_LABEL_PREFIX)
    }
    failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
        "maximum_property_float_delta": 0.0,
    }
    point_count = 0
    spot_count = 0
    ies_count = 0
    for record in records:
        label = light.managed_label(record)
        actor = managed.get(label)
        if not actor:
            failures.append({"label": label, "issues": ["missing_actor"]})
            continue
        issues, deltas = light.validate_actor(actor, record, profile)
        for name, value in deltas.items():
            maxima[name] = max(maxima[name], value)
        if issues:
            failures.append({"label": label, "issues": issues})
        is_spot = record["actor_type"] == "xxSpotLight"
        point_count += int(not is_spot)
        spot_count += int(is_spot)
        component = light.get_light_component(actor, is_spot)
        ies_count += int(component.get_editor_property("ies_texture") == profile)
    missing = sorted(expected_labels - set(managed))
    extra = sorted(set(managed) - expected_labels)
    aggregate_failures = sum(
        (
            point_count != light.EXPECTED_POINT_LIGHT_COUNT,
            spot_count != light.EXPECTED_SPOT_LIGHT_COUNT,
            ies_count != light.EXPECTED_IES_REFERENCE_COUNT,
        )
    )
    return {
        "managed_actor_count": len(managed),
        "point_light_count": point_count,
        "spot_light_count": spot_count,
        "ies_binding_count": ies_count,
        "missing_label_count": len(missing),
        "extra_label_count": len(extra),
        "actor_failure_count": len(failures),
        "failure_count": len(failures) + len(missing) + len(extra) + aggregate_failures,
        "maximum_deltas": maxima,
        "failures": failures[:20],
    }


def audit_fog(actors, fog):
    metadata, records, expected_labels = fog.source_inventory()
    asset_report, meshes, parents, texture = fog.prepared_assets()
    materials = {}
    missing_materials = []
    for record in records:
        label = fog.managed_label(record)
        path = fog.MATERIAL_INSTANCE_ROOT + "/" + fog.instance_asset_name(record)
        instance = unreal.EditorAssetLibrary.load_asset(path)
        if instance:
            materials[label] = instance
        else:
            missing_materials.append(path)
    if missing_materials:
        return {
            "managed_actor_count": sum(
                actor.get_actor_label().startswith(fog.MANAGED_LABEL_PREFIX)
                for actor in actors
            ),
            "missing_material_instance_count": len(missing_materials),
            "failure_count": len(missing_materials),
            "failures": missing_materials[:20],
        }
    validation = fog.validate_all(
        records,
        expected_labels,
        meshes,
        materials,
        parents,
        texture,
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem),
    )
    validation["missing_material_instance_count"] = 0
    return validation


def audit_native_water(actors, water):
    metadata = water.load_json(water.METADATA_PATH)
    restoration = water.load_json(water.REPORT_PATH)
    actor_records = metadata.get("water_actors", [])
    _, _, actor_instances = water.load_prepared_assets(actor_records)
    validation = water.validate_map_bindings(
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem),
        actor_records,
        actor_instances,
    )
    report_failures = []
    if metadata.get("status") != "analyzed":
        report_failures.append("source_metadata")
    if restoration.get("status") != "restored":
        report_failures.append("restoration_report")
    if len(actor_records) != water.EXPECTED_WATER_ACTOR_COUNT:
        report_failures.append("source_actor_count")
    validation["source_metadata_status"] = metadata.get("status")
    validation["restoration_report_status"] = restoration.get("status")
    validation["report_failure_count"] = len(report_failures)
    validation["report_failures"] = report_failures
    validation["failure_count"] += len(report_failures)
    return validation


def audit_environment_profile(actors, environment):
    metadata = environment.load_json(environment.METADATA_PATH)
    restoration = environment.load_json(environment.REPORT_PATH)
    expected_labels = environment.expected_labels(metadata)
    validation = environment.validate_environment(metadata, actors, expected_labels)
    by_label = {actor.get_actor_label(): actor for actor in actors}
    failures = []
    report_failures = []
    maxima = {
        "location_delta_cm": 0.0,
        "rotation_delta_degrees": 0.0,
        "scale_delta": 0.0,
        "property_float_delta": 0.0,
    }

    def add_failure(label, issue):
        failures.append({"label": label, "issue": issue})

    def check_transform(label, location, rotation, scale):
        actor = by_label.get(label)
        if not actor:
            add_failure(label, "missing_actor")
            return None
        deltas = {
            "location_delta_cm": vector_delta(actor.get_actor_location(), location),
            "rotation_delta_degrees": rotation_delta_degrees(
                actor.get_actor_rotation(), rotation
            ),
            "scale_delta": vector_delta(actor.get_actor_scale3d(), scale),
        }
        for name, value in deltas.items():
            maxima[name] = max(maxima[name], value)
        if deltas["location_delta_cm"] > 0.002:
            add_failure(label, "actor_location")
        if deltas["rotation_delta_degrees"] > 0.003:
            add_failure(label, "actor_rotation")
        if deltas["scale_delta"] > 0.000002:
            add_failure(label, "actor_scale")
        return actor

    def check_float(label, current, expected, issue, tolerance=0.0001):
        delta = abs(float(current) - float(expected))
        maxima["property_float_delta"] = max(
            maxima["property_float_delta"], delta
        )
        if delta > tolerance:
            add_failure(label, issue)

    if metadata.get("status") != "passed":
        report_failures.append("environment_metadata_status")
    if metadata.get("failures"):
        report_failures.append("environment_metadata_failures")
    if restoration.get("status") != "restored":
        report_failures.append("environment_restoration_status")
    if restoration.get("validation", {}).get("failures"):
        report_failures.append("environment_restoration_validation")
    if restoration.get("validation", {}).get("class_counts") != validation.get(
        "class_counts"
    ):
        report_failures.append("environment_class_counts")

    report_property_failures = []

    def collect_property_failures(value, path="report"):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = path + "." + str(key)
                if key in {"property_failures", "actor_property_failures"}:
                    if child:
                        report_property_failures.append(child_path)
                else:
                    collect_property_failures(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                collect_property_failures(child, path + "[{}]".format(index))

    collect_property_failures(restoration)
    if report_property_failures:
        report_failures.append("environment_property_failures")

    core_signature = environment.core_signature(actors)
    if core_signature != restoration.get("protected_core_after"):
        report_failures.append("protected_core_signature")

    proxy_components = metadata["environment_proxy"]["components"]
    clouds = [
        row
        for row in proxy_components
        if row["source_object_type"] == "xxEnvCloudComponent"
    ]
    skies = [
        row
        for row in proxy_components
        if row["source_object_type"] == "xxSkyMeshComponent"
    ]
    winds = [
        row
        for row in proxy_components
        if row["source_object_type"] == "xxWindDSComponent"
    ]
    proxy_rows = [("SP_Environment_SkyMesh", skies[0])]
    proxy_rows.extend(
        ("SP_Environment_Cloud_{}".format(index), row)
        for index, row in enumerate(clouds)
    )
    for label, row in proxy_rows:
        transform = row["transform"]
        actor = check_transform(
            label,
            environment.source_vector(transform["location_cm"]),
            environment.source_rotator(transform["rotation_degrees"]),
            environment.source_vector(transform["scale"], 1.0),
        )
        if actor:
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if not component or not component.get_editor_property("static_mesh"):
                add_failure(label, "static_mesh")
            elif not component.get_material(0):
                add_failure(label, "material")

    wind_transform = winds[0]["transform"]
    wind = check_transform(
        "SP_Environment_Wind",
        environment.source_vector(wind_transform["location_cm"]),
        environment.source_rotator(wind_transform["rotation_degrees"]),
        environment.source_vector(wind_transform["scale"], 1.0),
    )
    if wind:
        component = wind.get_component_by_class(unreal.WindDirectionalSourceComponent)
        if not component:
            add_failure("SP_Environment_Wind", "component")
        else:
            check_float(
                "SP_Environment_Wind",
                component.get_editor_property("speed"),
                winds[0]["properties"].get("Speed", 0.5),
                "speed",
            )

    center = unreal.Vector(18278.31, 51594.58, 21658.588)
    profile = metadata["profiles"][metadata["default_profile_key"]]
    wdl = profile["components"]["directional_light"]["properties"]
    rotation = wdl.get("RelativeRotation") or {}
    sun = check_transform(
        "SP_Environment_DirectionalLight",
        center,
        unreal.Rotator(
            pitch=float(rotation.get("Pitch", -90.0)),
            yaw=float(rotation.get("Yaw", 0.0)),
            roll=float(rotation.get("Roll", 0.0)),
        ),
        unreal.Vector(1.0, 1.0, 1.0),
    )
    if sun:
        component = sun.get_component_by_class(unreal.DirectionalLightComponent)
        if not component:
            add_failure("SP_Environment_DirectionalLight", "component")
        else:
            check_float(
                "SP_Environment_DirectionalLight",
                component.get_editor_property("intensity"),
                10.0,
                "intensity",
            )
            if component.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE:
                add_failure("SP_Environment_DirectionalLight", "mobility")
            if not component.get_editor_property("cast_shadows"):
                add_failure("SP_Environment_DirectionalLight", "cast_shadows")

    sky_light = check_transform(
        "SP_Environment_SkyLight",
        center,
        unreal.Rotator(),
        unreal.Vector(1.0, 1.0, 1.0),
    )
    if sky_light:
        component = sky_light.get_component_by_class(unreal.SkyLightComponent)
        wsl = profile["components"]["sky_light"]["properties"]
        if not component:
            add_failure("SP_Environment_SkyLight", "component")
        else:
            check_float(
                "SP_Environment_SkyLight",
                component.get_editor_property("intensity"),
                wsl.get("Intensity", 1.0),
                "intensity",
            )
            if component.get_editor_property("source_type") != unreal.SkyLightSourceType.SLS_CAPTURED_SCENE:
                add_failure("SP_Environment_SkyLight", "source_type")
            if not component.get_editor_property("real_time_capture"):
                add_failure("SP_Environment_SkyLight", "real_time_capture")

    for index, source in enumerate(metadata["reflection_captures"]):
        label = "SP_Environment_Reflection_{:02d}".format(index)
        transform = source["transform"]
        actor = check_transform(
            label,
            environment.source_vector(transform["location_cm"]),
            environment.source_rotator(transform["rotation_degrees"]),
            environment.source_vector(transform["scale"], 1.0),
        )
        if not actor:
            continue
        component = actor.get_component_by_class(
            unreal.SphereReflectionCaptureComponent
        )
        if not component:
            add_failure(label, "component")
            continue
        check_float(
            label,
            component.get_editor_property("influence_radius"),
            source["influence_radius_cm"],
            "influence_radius",
        )
        check_float(
            label,
            component.get_editor_property("brightness"),
            source["brightness"],
            "brightness",
        )
        if not component.get_editor_property("cubemap"):
            add_failure(label, "cubemap")

    for source in metadata["post_process_volumes"]:
        label = "SP_Environment_PP_{}_{:03d}".format(
            source["source_level"], int(source["source_actor_index"])
        )
        location, rotation, scale = environment.volume_proxy_transform(source)
        actor = check_transform(label, location, rotation, scale)
        if not actor:
            continue
        for property_name, expected in (
            ("unbound", bool(source["unbound"])),
            ("priority", float(source["priority"])),
            ("blend_radius", float(source["blend_radius"])),
            ("blend_weight", float(source["blend_weight"])),
            ("enabled", bool(source["enabled"])),
        ):
            current = actor.get_editor_property(property_name)
            if isinstance(expected, bool):
                if bool(current) != expected:
                    add_failure(label, property_name)
            else:
                check_float(label, current, expected, property_name)

    fallback = check_transform(
        "SP_Environment_PostProcessFallback",
        center,
        unreal.Rotator(),
        unreal.Vector(1.0, 1.0, 1.0),
    )
    if fallback:
        if not fallback.get_editor_property("unbound"):
            add_failure("SP_Environment_PostProcessFallback", "unbound")
        check_float(
            "SP_Environment_PostProcessFallback",
            fallback.get_editor_property("priority"),
            -100.0,
            "priority",
        )

    fog_source = profile["components"]["fog"]["properties"]
    outside = [
        row
        for row in metadata["post_process_volumes"]
        if row["profile_key"] == metadata["default_profile_key"]
        and row["source_actor_name"] == "WEP_StormPass_Outside_2"
    ][0]
    base_location = environment.source_vector(outside["transform"]["location_cm"])
    offset = fog_source.get("CameraFollowOffset") or {}
    fog_location = unreal.Vector(
        base_location.x + float(offset.get("X", 0.0)),
        base_location.y + float(offset.get("Y", 0.0)),
        base_location.z + float(offset.get("Z", 0.0)),
    )
    height_fog = check_transform(
        "SP_Environment_HeightFog",
        fog_location,
        unreal.Rotator(),
        unreal.Vector(1.0, 1.0, 1.0),
    )
    if height_fog:
        component = height_fog.get_component_by_class(
            unreal.ExponentialHeightFogComponent
        )
        if not component:
            add_failure("SP_Environment_HeightFog", "component")
        else:
            check_float(
                "SP_Environment_HeightFog",
                component.get_editor_property("fog_density"),
                float(fog_source.get("FogDensity", 0.5))
                * environment.FOG_DENSITY_SCALE,
                "fog_density",
            )
            check_float(
                "SP_Environment_HeightFog",
                component.get_editor_property("fog_height_falloff"),
                float(fog_source.get("FogHeightFalloff", 1.0))
                * environment.FOG_HEIGHT_FALLOFF_SCALE,
                "fog_height_falloff",
            )
            if not component.get_editor_property("enable_volumetric_fog"):
                add_failure("SP_Environment_HeightFog", "enable_volumetric_fog")

    total_failure_count = (
        int(validation.get("failures") != [])
        + len(report_failures)
        + len(failures)
    )
    return {
        "managed_actor_count": validation["present_count"],
        "expected_actor_count": validation["expected_count"],
        "class_counts": validation["class_counts"],
        "protected_core_signature": core_signature,
        "maximum_deltas": maxima,
        "source_metadata_status": metadata.get("status"),
        "restoration_report_status": restoration.get("status"),
        "report_property_failure_count": len(report_property_failures),
        "report_property_failures": report_property_failures,
        "report_failure_count": len(report_failures),
        "report_failures": report_failures,
        "actor_or_property_failure_count": len(failures),
        "failures": failures[:50],
        "failure_count": total_failure_count,
    }


def audit_visual_material_integrity(actors):
    """Guard the sky/cloud/Fog fixes that remove screen-space clipping."""
    library = unreal.EditorAssetLibrary
    material_library = unreal.MaterialEditingLibrary
    environment_root = (
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/"
        "EnvironmentAssets"
    )
    fog_root = (
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/FogAssets"
    )
    specifications = {
        "sky": {
            "path": environment_root + "/Materials/M_SP_SourceSky_V2",
            "version_tag": "KhazanStormPassVisualMaterialVersion",
            "required_version": "2",
            "required_classes": {
                "MaterialExpressionActorPositionWS",
                "MaterialExpressionNormalize",
                "MaterialExpressionWorldPosition",
            },
        },
        "cloud": {
            "path": environment_root + "/Materials/M_SP_SourceCloud_V2",
            "version_tag": "KhazanStormPassVisualMaterialVersion",
            "required_version": "2",
            "required_classes": {
                "MaterialExpressionActorPositionWS",
                "MaterialExpressionDivide",
                "MaterialExpressionWorldPosition",
            },
        },
        "fog_standard_one_sided": {
            "path": fog_root
            + "/Materials/M_SP_FogSheet_FMI_02_OneSided_V2",
            "version_tag": "KhazanStormPassFogPreviewVersion",
            "required_version": "2",
            "required_classes": {
                "MaterialExpressionCameraPositionWS",
                "MaterialExpressionCameraVectorWS",
                "MaterialExpressionDepthFade",
                "MaterialExpressionDistance",
                "MaterialExpressionDotProduct",
                "MaterialExpressionPixelNormalWS",
                "MaterialExpressionWorldPosition",
            },
        },
        "fog_standard_two_sided": {
            "path": fog_root
            + "/Materials/M_SP_FogSheet_FMI_01_TwoSided_V2",
            "version_tag": "KhazanStormPassFogPreviewVersion",
            "required_version": "2",
            "required_classes": {
                "MaterialExpressionCameraPositionWS",
                "MaterialExpressionCameraVectorWS",
                "MaterialExpressionDepthFade",
                "MaterialExpressionDistance",
                "MaterialExpressionDotProduct",
                "MaterialExpressionPixelNormalWS",
                "MaterialExpressionWorldPosition",
            },
        },
        "fog_local_two_sided": {
            "path": fog_root + "/Materials/M_SP_FogSheet_Local_TwoSided_V2",
            "version_tag": "KhazanStormPassFogPreviewVersion",
            "required_version": "2",
            "required_classes": {
                "MaterialExpressionCameraPositionWS",
                "MaterialExpressionCameraVectorWS",
                "MaterialExpressionDepthFade",
                "MaterialExpressionDistance",
                "MaterialExpressionDotProduct",
                "MaterialExpressionPixelNormalWS",
                "MaterialExpressionWorldPosition",
            },
        },
    }
    failures = []
    material_rows = {}
    loaded_materials = {}
    for key, specification in specifications.items():
        material = library.load_asset(specification["path"])
        if not material:
            failures.append({"asset": key, "issue": "missing_material"})
            continue
        loaded_materials[key] = material
        expression_classes = {
            expression.get_class().get_name()
            for expression in material_library.get_material_expressions(material)
        }
        missing_classes = sorted(
            specification["required_classes"].difference(expression_classes)
        )
        version = library.get_metadata_tag(
            material, specification["version_tag"]
        )
        disable_depth_test = bool(
            material.get_editor_property("disable_depth_test")
        )
        if missing_classes:
            failures.append(
                {
                    "asset": key,
                    "issue": "missing_expression_classes",
                    "classes": missing_classes,
                }
            )
        if "MaterialExpressionPixelDepth" in expression_classes:
            failures.append({"asset": key, "issue": "pixel_depth_reintroduced"})
        if disable_depth_test:
            failures.append({"asset": key, "issue": "depth_test_disabled"})
        if version != specification["required_version"]:
            failures.append(
                {
                    "asset": key,
                    "issue": "material_version",
                    "actual": version,
                }
            )
        material_rows[key] = {
            "path": material.get_path_name(),
            "expression_count": int(
                material_library.get_num_material_expressions(material)
            ),
            "expression_classes": sorted(expression_classes),
            "missing_required_expression_classes": missing_classes,
            "pixel_depth_present": (
                "MaterialExpressionPixelDepth" in expression_classes
            ),
            "disable_depth_test": disable_depth_test,
            "version": version,
        }

    instance_specs = {
        "sky": (
            environment_root
            + "/MaterialInstances/MI_SP_Sky_GloomyDay_V2",
            "sky",
        ),
        "cloud_0": (
            environment_root
            + "/MaterialInstances/MI_SP_Cloud_White_Layer1_V2",
            "cloud",
        ),
        "cloud_1": (
            environment_root
            + "/MaterialInstances/MI_SP_Cloud_GloomyDawn_Layer2_V2",
            "cloud",
        ),
    }
    instances = {}
    instance_rows = {}
    for key, (path, parent_key) in instance_specs.items():
        instance = library.load_asset(path)
        instances[key] = instance
        parent = instance.get_editor_property("parent") if instance else None
        expected_parent = loaded_materials.get(parent_key)
        parent_matches = bool(
            parent
            and expected_parent
            and parent.get_path_name() == expected_parent.get_path_name()
        )
        if not instance:
            failures.append({"asset": key, "issue": "missing_instance"})
        elif not parent_matches:
            failures.append({"asset": key, "issue": "instance_parent"})
        instance_rows[key] = {
            "path": instance.get_path_name() if instance else None,
            "parent": parent.get_path_name() if parent else None,
            "parent_matches": parent_matches,
        }

    by_label = {actor.get_actor_label(): actor for actor in actors}
    actor_instance_keys = {
        "SP_Environment_SkyMesh": "sky",
        "SP_Environment_Cloud_0": "cloud_0",
        "SP_Environment_Cloud_1": "cloud_1",
    }
    actor_rows = {}
    for label, instance_key in actor_instance_keys.items():
        actor = by_label.get(label)
        component = (
            actor.get_component_by_class(unreal.StaticMeshComponent)
            if actor
            else None
        )
        assigned = component.get_material(0) if component else None
        expected = instances.get(instance_key)
        matches = bool(
            assigned
            and expected
            and assigned.get_path_name() == expected.get_path_name()
        )
        if not matches:
            failures.append({"actor": label, "issue": "material_assignment"})
        actor_rows[label] = {
            "material": assigned.get_path_name() if assigned else None,
            "matches": matches,
        }

    fog_parent_counts = collections.Counter()
    fog_actor_count = 0
    for actor in actors:
        if not actor.get_actor_label().startswith("SP_Fog_"):
            continue
        fog_actor_count += 1
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        instance = component.get_material(0) if component else None
        parent = instance.get_editor_property("parent") if instance else None
        fog_parent_counts[parent.get_path_name() if parent else "<missing>"] += 1
    expected_fog_parent_counts = {
        loaded_materials[key].get_path_name(): count
        for key, count in (
            ("fog_standard_one_sided", 45),
            ("fog_standard_two_sided", 6),
            ("fog_local_two_sided", 2),
        )
        if key in loaded_materials
    }
    if fog_actor_count != 53:
        failures.append({"issue": "fog_actor_count", "actual": fog_actor_count})
    if dict(fog_parent_counts) != expected_fog_parent_counts:
        failures.append(
            {
                "issue": "fog_parent_distribution",
                "actual": dict(fog_parent_counts),
                "expected": expected_fog_parent_counts,
            }
        )

    temporary_hidden = sorted(
        actor.get_actor_label()
        for actor in actors
        if actor.is_temporarily_hidden_in_editor()
    )
    if temporary_hidden:
        failures.append(
            {"issue": "temporarily_hidden_actors", "actors": temporary_hidden[:20]}
        )
    return {
        "material_count": len(material_rows),
        "materials": material_rows,
        "instances": instance_rows,
        "environment_actor_materials": actor_rows,
        "fog_actor_count": fog_actor_count,
        "fog_parent_counts": dict(fog_parent_counts),
        "expected_fog_parent_counts": expected_fog_parent_counts,
        "temporary_hidden_actor_count": len(temporary_hidden),
        "temporary_hidden_actors": temporary_hidden[:20],
        "failure_count": len(failures),
        "failures": failures,
    }


def audit_tree_material_repair(actors, tree):
    report = tree.load_json(tree.REPORT_PATH)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    slots = tree.slot_inventory(actor_subsystem)
    signature = tree.transform_signature(actors)
    parent = unreal.EditorAssetLibrary.load_asset(tree.PARENT_PATH)
    failures = []
    sampler_failures = []
    parent_texture_expression_count = 0
    if report.get("status") != "repaired":
        failures.append("repair_report_status")
    if report.get("validation_failures"):
        failures.append("repair_report_validation")
    if report.get("repair_parent", {}).get("tex_s_usage") != (
        "R=ambient occlusion, G=roughness, foliage metallic=0"
    ):
        failures.append("packed_texture_policy")
    if slots["total"] != tree.EXPECTED_SLOT_TOTAL:
        failures.append("slot_total")
    if slots["counts"] != tree.EXPECTED_SLOT_COUNTS:
        failures.append("slot_distribution")
    if signature != report.get("transform_after"):
        failures.append("actor_transform_signature")
    if not parent:
        failures.append("repair_parent_missing")
    else:
        if unreal.MaterialEditingLibrary.get_material_property_input_node(
            parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR
        ):
            failures.append("repair_parent_emissive_connected")
        texture_expressions = [
            expression
            for expression in unreal.MaterialEditingLibrary.get_material_expressions(parent)
            if isinstance(expression, unreal.MaterialExpressionTextureSampleParameter2D)
        ]
        parent_texture_expression_count = len(texture_expressions)
        if parent_texture_expression_count != 5:
            failures.append("repair_parent_texture_expression_count")
        for expression in texture_expressions:
            texture = expression.get_editor_property("texture")
            sampler = expression.get_editor_property("sampler_type")
            if (
                sampler == unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
                and (
                    not texture
                    or texture.get_editor_property("compression_settings")
                    != unreal.TextureCompressionSettings.TC_MASKS
                )
            ):
                sampler_failures.append(str(expression.get_editor_property("parameter_name")))
        if sampler_failures:
            failures.append("repair_parent_sampler_compatibility")

    material_failures = []
    for name in tree.MATERIAL_NAMES:
        material = unreal.EditorAssetLibrary.load_asset(tree.material_path(name))
        if not material:
            material_failures.append({"material": name, "issues": ["missing"]})
            continue
        record = tree.validation_record(material)
        issues = []
        if tree.normalized_asset_path(record["parent"]) != tree.PARENT_PATH:
            issues.append("parent")
        if record["has_use_emissive_parameter"]:
            issues.append("emissive_parameter")
        for parameter in (
            "BaseColorTexture",
            "OpacityTexture",
            "NormalTexture",
            "RoughnessTexture",
            "EmissiveColorTexture",
        ):
            if not record["textures"].get(parameter):
                issues.append(parameter)
        if not record["two_sided_override"]:
            issues.append("two_sided")
        if issues:
            material_failures.append({"material": name, "issues": issues})
    return {
        "material_count": len(tree.MATERIAL_NAMES),
        "affected_slot_count": slots["total"],
        "slot_inventory": slots,
        "actor_transform_signature": signature,
        "repair_report_status": report.get("status"),
        "parent_texture_expression_count": parent_texture_expression_count,
        "sampler_failure_count": len(sampler_failures),
        "sampler_failures": sampler_failures,
        "material_failure_count": len(material_failures),
        "material_failures": material_failures,
        "aggregate_failures": failures,
        "failure_count": len(failures) + len(material_failures),
    }


def audit_false_emissive_repair(actors, repair):
    report = repair.load_json(repair.REPORT_PATH)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    slots = repair.slot_inventory(actor_subsystem)
    signature = repair.transform_signature(actors)
    failures = []
    material_states = {}
    if report.get("status") != "repaired":
        failures.append("repair_report_status")
    if report.get("validation_failures"):
        failures.append("repair_report_validation")
    if report.get("master_emissive_defaults", {}).get("EmissiveOn") != 0.0:
        failures.append("source_emissive_default")
    if slots["counts"] != repair.MATERIAL_COUNTS:
        failures.append("slot_distribution")
    if slots["total"] != repair.EXPECTED_SLOT_TOTAL:
        failures.append("slot_total")
    if signature != report.get("transform_after"):
        failures.append("actor_transform_signature")
    for name in repair.MATERIAL_COUNTS:
        material = unreal.EditorAssetLibrary.load_asset(repair.material_path(name))
        if not material:
            material_states[name] = {"missing": True}
            failures.append(name + ":missing")
            continue
        state = repair.emissive_override(material)
        material_states[name] = state
        if state["direct"] != 0.0 or state["effective"] != 0.0:
            failures.append(name + ":false_emissive")
    return {
        "material_count": len(repair.MATERIAL_COUNTS),
        "affected_slot_count": slots["total"],
        "slot_inventory": slots,
        "actor_transform_signature": signature,
        "repair_report_status": report.get("status"),
        "material_states": material_states,
        "failures": failures,
        "failure_count": len(failures),
    }


def audit_ore_material_repair(actors, ore):
    report = ore.load_json(ore.REPORT_PATH)
    helper = ore.load_tree_helper()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    slots = ore.slot_inventory(actor_subsystem, helper)
    signature = helper.transform_signature(actors)
    parent = unreal.EditorAssetLibrary.load_asset(ore.PARENT_PATH)
    failures = []
    material_states = {}
    sampler_failures = []
    parent_texture_expression_count = 0
    if report.get("status") != "repaired":
        failures.append("repair_report_status")
    if report.get("validation_failures"):
        failures.append("repair_report_validation")
    if slots["counts"] != ore.MATERIAL_COUNTS:
        failures.append("slot_distribution")
    if slots["total"] != ore.EXPECTED_SLOT_TOTAL:
        failures.append("slot_total")
    if signature != report.get("transform_after"):
        failures.append("actor_transform_signature")
    if not parent:
        failures.append("repair_parent_missing")
    else:
        if not unreal.MaterialEditingLibrary.get_material_property_input_node(
            parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR
        ):
            failures.append("repair_parent_emissive_missing")
        texture_expressions = [
            expression
            for expression in unreal.MaterialEditingLibrary.get_material_expressions(parent)
            if isinstance(expression, unreal.MaterialExpressionTextureSampleParameter2D)
        ]
        parent_texture_expression_count = len(texture_expressions)
        if parent_texture_expression_count != 6:
            failures.append("repair_parent_texture_expression_count")
        for expression in texture_expressions:
            texture = expression.get_editor_property("texture")
            sampler = expression.get_editor_property("sampler_type")
            if (
                sampler == unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
                and (
                    not texture
                    or texture.get_editor_property("compression_settings")
                    != unreal.TextureCompressionSettings.TC_MASKS
                )
            ):
                sampler_failures.append(str(expression.get_editor_property("parameter_name")))
        if sampler_failures:
            failures.append("repair_parent_sampler_compatibility")

    for name in ore.MATERIAL_COUNTS:
        material = unreal.EditorAssetLibrary.load_asset(ore.material_path(name))
        if not material:
            material_states[name] = {"missing": True}
            failures.append(name + ":missing")
            continue
        state = ore.validation_record(material, helper)
        source = ore.resolved_source_record(name)
        material_states[name] = state
        if helper.normalized_asset_path(state["parent"]) != ore.PARENT_PATH:
            failures.append(name + ":parent")
        if any(not value for value in state["textures"].values()):
            failures.append(name + ":texture")
        if abs(
            state["base_emissive_amount"]
            - source["effective_scalars"]["BaseEmissiveAmount"]
        ) > 0.00001:
            failures.append(name + ":base_emissive_amount")
        if abs(
            state["tex_brightness"]
            - source["effective_scalars"]["TexBrightness"]
        ) > 0.00001:
            failures.append(name + ":tex_brightness")
        if max(
            abs(left - right)
            for left, right in zip(state["glow_color"], source["glow_color"])
        ) > 0.00001:
            failures.append(name + ":glow_color")
    return {
        "material_count": len(ore.MATERIAL_COUNTS),
        "affected_slot_count": slots["total"],
        "slot_inventory": slots,
        "actor_transform_signature": signature,
        "repair_report_status": report.get("status"),
        "parent_texture_expression_count": parent_texture_expression_count,
        "sampler_failure_count": len(sampler_failures),
        "sampler_failures": sampler_failures,
        "material_states": material_states,
        "failures": failures,
        "failure_count": len(failures),
    }


def audit_material_surface(actors):
    null_slots = []
    world_grid_slots = []
    checked_components = 0
    checked_slots = 0
    for actor in actors:
        components = list(actor.get_components_by_class(unreal.StaticMeshComponent))
        components.extend(
            actor.get_components_by_class(unreal.FoliageInstancedStaticMeshComponent)
        )
        unique = []
        seen = set()
        for component in components:
            path = component.get_path_name()
            if path not in seen:
                seen.add(path)
                unique.append(component)
        for component in unique:
            checked_components += 1
            for slot in range(int(component.get_num_materials())):
                checked_slots += 1
                material = component.get_material(slot)
                if not material:
                    null_slots.append(
                        {"actor": actor.get_actor_label(), "component": component.get_name(), "slot": slot}
                    )
                    continue
                path = material.get_path_name()
                if "WorldGridMaterial" in path or path.endswith("DefaultMaterial.DefaultMaterial"):
                    world_grid_slots.append(
                        {"actor": actor.get_actor_label(), "component": component.get_name(), "slot": slot, "material": path}
                    )
    return {
        "checked_component_count": checked_components,
        "checked_material_slot_count": checked_slots,
        "null_material_slot_count": len(null_slots),
        "world_grid_or_default_material_slot_count": len(world_grid_slots),
        "failure_count": len(null_slots) + len(world_grid_slots),
        "null_material_slots": null_slots[:20],
        "world_grid_or_default_material_slots": world_grid_slots[:20],
    }


def main():
    modules = {
        name: load_module(name, path) for name, path in MODULE_PATHS.items()
    }
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(DEV_MAP_PATH):
        raise RuntimeError("Failed to leave StormPass for final saved-map audit")
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to reload StormPass for final audit")
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    actors = [
        actor
        for actor in unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).get_all_level_actors()
        if actor
    ]

    stages = {
        "inventory": audit_inventory(actors),
        "root_props": audit_root_props(actors),
        "child_props": audit_child_props(actors, modules["child"]),
        "landscape": audit_landscape(actors, modules["landscape"]),
        "foliage": audit_foliage(actors, modules["foliage"]),
        "lights": audit_lights(actors, modules["light"]),
        "fog": audit_fog(actors, modules["fog"]),
        "native_water": audit_native_water(actors, modules["water"]),
        "environment_profile": audit_environment_profile(
            actors, modules["environment"]
        ),
        "visual_material_integrity": audit_visual_material_integrity(actors),
        "tree_material_repair": audit_tree_material_repair(
            actors, modules["tree_material"]
        ),
        "false_emissive_repair": audit_false_emissive_repair(
            actors, modules["false_emissive"]
        ),
        "ore_material_repair": audit_ore_material_repair(
            actors, modules["ore_material"]
        ),
        "material_surface": audit_material_surface(actors),
    }
    failed_stages = [
        name for name, result in stages.items() if int(result.get("failure_count", 0))
    ]
    report = {
        "status": "passed" if not failed_stages else "failed",
        "operation": "final_saved_map_full_reconstruction_audit",
        "map_path": MAP_PATH,
        "world_path": world.get_path_name() if world else None,
        "reload_cycle": [DEV_MAP_PATH, MAP_PATH],
        "map_modified": False,
        "map_disk_path": MAP_DISK_PATH,
        "map_size_bytes": os.path.getsize(MAP_DISK_PATH),
        "map_sha256": sha256_file(MAP_DISK_PATH),
        "failed_stage_count": len(failed_stages),
        "failed_stages": failed_stages,
        "stages": stages,
        "content_boundary": {
            "visual_level_content_only": True,
            "all_actors_use_reconstruction_prefix": True,
            "gameplay_or_source_code_audited_or_modified": False,
        },
    }
    write_json(REPORT_PATH, report)
    if failed_stages:
        raise RuntimeError(
            "StormPass final reconstruction audit failed: " + ", ".join(failed_stages)
        )
    log(
        "RESULT status=passed actors={} roots={} child={} landscape={} foliage={}/{} "
        "lights={} fog={} environment={} visual_materials={} tree_materials={} false_emissive={} "
        "ore_materials={} water={} "
        "material_slots={} sha256={} report={}".format(
            stages["inventory"]["total_actor_count"],
            stages["root_props"]["managed_actor_count"],
            stages["child_props"]["managed_actor_count"],
            stages["landscape"]["managed_actor_count"],
            stages["foliage"]["component_count"],
            stages["foliage"]["instance_count"],
            stages["lights"]["managed_actor_count"],
            stages["fog"]["managed_fog_actor_count"],
            stages["environment_profile"]["managed_actor_count"],
            stages["visual_material_integrity"]["material_count"],
            stages["tree_material_repair"]["material_count"],
            stages["false_emissive_repair"]["material_count"],
            stages["ore_material_repair"]["material_count"],
            stages["native_water"]["checked_water_actor_count"],
            stages["material_surface"]["checked_material_slot_count"],
            report["map_sha256"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        if not os.path.isfile(REPORT_PATH):
            write_json(
                REPORT_PATH,
                {
                    "status": "failed",
                    "error": str(exception),
                    "traceback": traceback.format_exc(),
                    "map_modified": False,
                },
            )
        unreal.log_error("KHAZAN_STORMPASS_FINAL_AUDIT: " + str(exception))
        raise
