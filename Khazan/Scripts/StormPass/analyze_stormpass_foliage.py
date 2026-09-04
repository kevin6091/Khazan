"""Extract canonical StormPass Foliage/HISM instances from FModel USDA.

FModel's Properties JSON keeps component settings but omits bulk per-instance
transforms.  Its world USDA exports the same components as PointInstancers,
including every position, orientation, scale, and prototype mesh reference.
This read-only audit joins both sources and converts USD's reflected Y axis to
Unreal coordinates.  No Unreal asset or map is modified.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pxr import Gf, Sdf, Usd, UsdGeom


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
PROPERTIES_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
WORLD_ROOT = (
    FMODEL_ROOT
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
SCOPE_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_SourceScope.json"
)
METADATA_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_FoliageInstances.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_Foliage_SourceAudit.json"
)
ROOT_HELPER_PATH = (
    PROJECT_ROOT / "Scripts" / "HeinMach" / "audit_heinmach_root_template_coverage.py"
)
LEVEL_PACKAGE_ROOT = "BBQ/Content/_Kazan_/Level/StormPass"
EXPECTED_VISUAL_LEVEL_COUNT = 38
EXPECTED_COMPONENT_COUNT = 218
EXPECTED_INSTANCE_COUNT = 21259
MATRIX_TOLERANCE = 1.0e-7
BOUND_TOLERANCE_CM = 5.0


def load_root_helpers():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_foliage_root_helpers", ROOT_HELPER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass package resolver helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


root = load_root_helpers()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=False)
        output.write("\n")


def inherited_value(resolver, component, package, objects, name):
    return resolver.inherited_property(component, package, objects, name)[0]


def usd_reference_asset_path(prim) -> str | None:
    references = prim.GetMetadata("references")
    if references is None:
        return None
    items = list(references.GetAddedOrExplicitItems())
    if len(items) != 1:
        return None
    return str(items[0].assetPath)


def package_from_usd_reference(stage_path: Path, asset_path: str) -> str:
    source = (stage_path.parent / asset_path).resolve()
    relative = source.relative_to(FMODEL_ROOT.resolve())
    if source.suffix.lower() != ".usda":
        raise RuntimeError("PointInstancer prototype is not USDA: " + str(source))
    return relative.with_suffix("").as_posix()


def matrix_parent_translation(matrix: Gf.Matrix4d) -> tuple[float, float, float]:
    for row in range(3):
        for column in range(3):
            expected = 1.0 if row == column else 0.0
            if abs(float(matrix[row][column]) - expected) > MATRIX_TOLERANCE:
                raise RuntimeError(
                    "PointInstancer parent contains unsupported rotation/scale"
                )
    if any(abs(float(matrix[row][3])) > MATRIX_TOLERANCE for row in range(3)):
        raise RuntimeError("PointInstancer parent matrix contains perspective")
    if abs(float(matrix[3][3]) - 1.0) > MATRIX_TOLERANCE:
        raise RuntimeError("PointInstancer parent matrix W changed")
    translation = matrix.ExtractTranslation()
    return float(translation[0]), float(translation[1]), float(translation[2])


def ue_quaternion(orientation) -> dict[str, float]:
    real = float(orientation.GetReal())
    imaginary = orientation.GetImaginary()
    # USD and UE are both Z-up here, but FModel's USD is right-handed.  The
    # Y reflection uses R_ue = S * R_usd * S, S=diag(1,-1,1), yielding this
    # quaternion mapping.
    values = (
        -float(imaginary[0]),
        float(imaginary[1]),
        -float(imaginary[2]),
        real,
    )
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude <= 1.0e-12:
        raise RuntimeError("PointInstancer orientation quaternion is zero")
    x, y, z, w = (value / magnitude for value in values)
    return {"x": x, "y": y, "z": z, "w": w}


def ue_instance_transform(position, orientation, scale, parent_translation):
    stage_x = float(position[0]) + parent_translation[0]
    stage_y = float(position[1]) + parent_translation[1]
    stage_z = float(position[2]) + parent_translation[2]
    return {
        "location_cm": {"x": stage_x, "y": -stage_y, "z": stage_z},
        "rotation_quaternion": ue_quaternion(orientation),
        "scale": {
            "x": float(scale[0]),
            "y": float(scale[1]),
            "z": float(scale[2]),
        },
    }


def quaternion_matrix(value):
    x = float(value["x"])
    y = float(value["y"])
    z = float(value["z"])
    w = float(value["w"])
    return (
        (
            1.0 - 2.0 * (y * y + z * z),
            2.0 * (x * y - z * w),
            2.0 * (x * z + y * w),
        ),
        (
            2.0 * (x * y + z * w),
            1.0 - 2.0 * (x * x + z * z),
            2.0 * (y * z - x * w),
        ),
        (
            2.0 * (x * z - y * w),
            2.0 * (y * z + x * w),
            1.0 - 2.0 * (x * x + y * y),
        ),
    )


def transformed_bounds(transforms, mesh_bounds):
    origin = mesh_bounds.get("Origin") or {}
    extent = mesh_bounds.get("BoxExtent") or {}
    local_origin = (
        float(origin.get("X", 0.0)),
        float(origin.get("Y", 0.0)),
        float(origin.get("Z", 0.0)),
    )
    local_extent = (
        float(extent.get("X", 0.0)),
        float(extent.get("Y", 0.0)),
        float(extent.get("Z", 0.0)),
    )
    result_min = [float("inf")] * 3
    result_max = [float("-inf")] * 3
    for transform in transforms:
        location = transform["location_cm"]
        scale = transform["scale"]
        scaled_origin = (
            local_origin[0] * float(scale["x"]),
            local_origin[1] * float(scale["y"]),
            local_origin[2] * float(scale["z"]),
        )
        scaled_extent = (
            local_extent[0] * abs(float(scale["x"])),
            local_extent[1] * abs(float(scale["y"])),
            local_extent[2] * abs(float(scale["z"])),
        )
        rotation = quaternion_matrix(transform["rotation_quaternion"])
        center = [
            float(location[("x", "y", "z")[axis]])
            + sum(rotation[axis][column] * scaled_origin[column] for column in range(3))
            for axis in range(3)
        ]
        world_extent = [
            sum(abs(rotation[axis][column]) * scaled_extent[column] for column in range(3))
            for axis in range(3)
        ]
        for axis in range(3):
            result_min[axis] = min(result_min[axis], center[axis] - world_extent[axis])
            result_max[axis] = max(result_max[axis], center[axis] + world_extent[axis])
    return {"min": result_min, "max": result_max}


def component_settings(resolver, component, package, objects):
    override = inherited_value(
        resolver, component, package, objects, "OverrideMaterials"
    )
    if override is None:
        override = inherited_value(
            resolver, component, package, objects, "SavedOverrideMaterials"
        )
    body = inherited_value(resolver, component, package, objects, "BodyInstance")
    body = body if isinstance(body, dict) else {}
    result = {
        "cast_shadow": inherited_value(
            resolver, component, package, objects, "CastShadow"
        ),
        "affect_dynamic_indirect_lighting": inherited_value(
            resolver,
            component,
            package,
            objects,
            "bAffectDynamicIndirectLighting",
        ),
        "affect_distance_field_lighting": inherited_value(
            resolver,
            component,
            package,
            objects,
            "bAffectDistanceFieldLighting",
        ),
        "receives_decals": inherited_value(
            resolver, component, package, objects, "bReceivesDecals"
        ),
        "enable_density_scaling": inherited_value(
            resolver, component, package, objects, "bEnableDensityScaling"
        ),
        "instance_start_cull_distance": inherited_value(
            resolver,
            component,
            package,
            objects,
            "InstanceStartCullDistance",
        ),
        "instance_end_cull_distance": inherited_value(
            resolver,
            component,
            package,
            objects,
            "InstanceEndCullDistance",
        ),
        "cached_max_draw_distance": inherited_value(
            resolver, component, package, objects, "CachedMaxDrawDistance"
        ),
        "override_material_packages": root.referenced_package_slots(override),
        "collision_profile_name": body.get("CollisionProfileName"),
        "collision_enabled": body.get("CollisionEnabled"),
        "collision_object_type": body.get("ObjectType"),
        "instancing_random_seed": inherited_value(
            resolver, component, package, objects, "InstancingRandomSeed"
        ),
    }
    return result


def component_map(objects, package):
    actors_by_name = defaultdict(list)
    components_by_key = defaultdict(list)
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            continue
        if root.is_actor(obj):
            actors_by_name[str(obj.get("Name"))].append((index, obj))
        outer = obj.get("Outer")
        outer_path = outer.get("ObjectPath") if isinstance(outer, dict) else None
        actor_index = root.object_index(outer)
        if (
            isinstance(outer_path, str)
            and outer_path.startswith(package + ".")
            and actor_index is not None
        ):
            components_by_key[(actor_index, str(obj.get("Name")))].append((index, obj))
    return actors_by_name, components_by_key


def point_instancer_record(
    resolver,
    stage,
    stage_path,
    level_name,
    package,
    objects,
    actors_by_name,
    components_by_key,
    prim,
):
    path_parts = [part for part in str(prim.GetPath()).split("/") if part]
    if len(path_parts) < 4 or path_parts[0] != level_name:
        raise RuntimeError("Unexpected PointInstancer prim path: " + str(prim.GetPath()))
    actor_name = path_parts[1]
    actor_candidates = actors_by_name.get(actor_name, [])
    if len(actor_candidates) != 1:
        raise RuntimeError(
            "PointInstancer actor mapping is ambiguous: {} {}".format(
                level_name, actor_name
            )
        )
    actor_index, actor = actor_candidates[0]

    instancer = UsdGeom.PointInstancer(prim)
    prototype_targets = list(instancer.GetPrototypesRel().GetTargets())
    if len(prototype_targets) != 1:
        raise RuntimeError("PointInstancer must have exactly one prototype")
    prototype_path = prototype_targets[0]
    component_name = str(prototype_path).split("/")[-1]
    component_candidates = components_by_key.get((actor_index, component_name), [])
    if len(component_candidates) != 1:
        raise RuntimeError(
            "PointInstancer component mapping is ambiguous: {} {} {}".format(
                level_name, actor_name, component_name
            )
        )
    component_index, component = component_candidates[0]
    component_type = str(component.get("Type"))
    if not (
        "FoliageInstancedStaticMesh" in component_type
        or "HierarchicalInstancedStaticMesh" in component_type
    ):
        raise RuntimeError("PointInstancer mapped to a non-HISM component")

    prototype = stage.GetPrimAtPath(prototype_path)
    reference_path = usd_reference_asset_path(prototype)
    if not reference_path:
        raise RuntimeError("PointInstancer prototype reference is unavailable")
    usd_mesh_package = package_from_usd_reference(stage_path, reference_path)
    mesh_value = inherited_value(
        resolver, component, package, objects, "StaticMesh"
    )
    json_mesh_package = root.referenced_package(mesh_value)
    if not json_mesh_package or json_mesh_package != usd_mesh_package:
        raise RuntimeError(
            "PointInstancer mesh source mismatch: {} != {}".format(
                json_mesh_package, usd_mesh_package
            )
        )

    positions = list(instancer.GetPositionsAttr().Get() or [])
    orientations = list(instancer.GetOrientationsAttr().Get() or [])
    scales = list(instancer.GetScalesAttr().Get() or [])
    proto_indices = list(instancer.GetProtoIndicesAttr().Get() or [])
    invisible_ids = list(instancer.GetInvisibleIdsAttr().Get() or [])
    count = len(positions)
    if not orientations:
        orientations = [Gf.Quath(1.0)] * count
    if not scales:
        scales = [Gf.Vec3f(1.0)] * count
    if not (
        len(orientations) == count
        and len(scales) == count
        and len(proto_indices) == count
    ):
        raise RuntimeError("PointInstancer transform array lengths differ")
    if any(int(index) != 0 for index in proto_indices):
        raise RuntimeError("PointInstancer uses an unexpected prototype index")
    if invisible_ids:
        raise RuntimeError("PointInstancer contains deferred invisible instances")

    parent_matrix = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
    parent_translation = matrix_parent_translation(parent_matrix)
    local_transforms = [
        ue_instance_transform(position, orientation, scale, (0.0, 0.0, 0.0))
        for position, orientation, scale in zip(positions, orientations, scales)
    ]
    transforms = [
        ue_instance_transform(position, orientation, scale, parent_translation)
        for position, orientation, scale in zip(positions, orientations, scales)
    ]
    properties = component.get("Properties") or {}
    expected_counts = [
        int(value)
        for value in (
            properties.get("NumBuiltInstances"),
            properties.get("InstanceCountToRender"),
        )
        if value is not None and int(value) >= 0
    ]
    if expected_counts and any(value != count for value in expected_counts):
        raise RuntimeError("PointInstancer count differs from Properties JSON")

    built_bounds = properties.get("BuiltInstanceBounds")
    mesh_extended_bounds = inherited_value(
        resolver, component, package, objects, "CacheMeshExtendedBounds"
    )
    bound_validation = None
    if (
        isinstance(built_bounds, dict)
        and isinstance(mesh_extended_bounds, dict)
        and transforms
    ):
        calculated = transformed_bounds(local_transforms, mesh_extended_bounds)
        source_minimum = built_bounds.get("Min") or {}
        source_maximum = built_bounds.get("Max") or {}
        expected_min = [
            float(source_minimum[axis]) for axis in ("X", "Y", "Z")
        ]
        expected_max = [
            float(source_maximum[axis]) for axis in ("X", "Y", "Z")
        ]
        deltas = [
            abs(actual - expected)
            for actual, expected in zip(
                calculated["min"] + calculated["max"],
                expected_min + expected_max,
            )
        ]
        maximum_delta = max(deltas)
        bound_validation = {
            "calculated_min": calculated["min"],
            "calculated_max": calculated["max"],
            "source_min": expected_min,
            "source_max": expected_max,
            "maximum_delta_cm": maximum_delta,
            "tolerance_cm": BOUND_TOLERANCE_CM,
        }
        if maximum_delta > BOUND_TOLERANCE_CM:
            raise RuntimeError(
                "PointInstancer transformed bounds mismatch: level={} actor={} "
                "component={} max_delta={} parent={}".format(
                    level_name,
                    actor_name,
                    component_name,
                    maximum_delta,
                    parent_translation,
                )
            )

    settings = component_settings(
        resolver, component, package, objects
    )
    return {
        "source_level": level_name,
        "source_package": package,
        "source_world_usd": str(stage_path),
        "point_instancer_prim": str(prim.GetPath()),
        "prototype_prim": str(prototype_path),
        "prototype_reference": reference_path,
        "actor_object_index": actor_index,
        "actor_type": actor.get("Type"),
        "actor_name": actor_name,
        "component_object_index": component_index,
        "component_type": component_type,
        "component_name": component_name,
        "static_mesh_package": json_mesh_package,
        "instance_count": count,
        "parent_stage_translation": {
            "x": parent_translation[0],
            "y": parent_translation[1],
            "z": parent_translation[2],
        },
        "built_instance_bounds": built_bounds,
        "mesh_extended_bounds": mesh_extended_bounds,
        "bound_validation": bound_validation,
        "built_bounds_coordinate_space": "point_instancer_local_before_parent_transform",
        "settings": settings,
        "instances": transforms,
    }


def main():
    scope = load_json(SCOPE_PATH)
    visual_levels = sorted(scope.get("visual_levels", []))
    if len(visual_levels) != EXPECTED_VISUAL_LEVEL_COUNT:
        raise RuntimeError("StormPass visual-level inventory changed")
    resolver = root.PackageResolver(FMODEL_ROOT)
    components = []
    level_counts = []
    source_usd_total_bytes = 0

    for level_name in visual_levels:
        properties_path = PROPERTIES_ROOT / f"{level_name}.json"
        stage_path = WORLD_ROOT / f"{level_name}.usda"
        if not properties_path.is_file() or not stage_path.is_file():
            raise RuntimeError("StormPass Foliage source file is missing: " + level_name)
        objects = load_json(properties_path)
        if not isinstance(objects, list):
            raise RuntimeError("StormPass Properties JSON is invalid: " + level_name)
        package = f"{LEVEL_PACKAGE_ROOT}/{level_name}"
        actors_by_name, components_by_key = component_map(objects, package)
        stage = Usd.Stage.Open(str(stage_path))
        if not stage:
            raise RuntimeError("Unable to open StormPass world USDA: " + str(stage_path))
        level_records = []
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.PointInstancer):
                level_records.append(
                    point_instancer_record(
                        resolver,
                        stage,
                        stage_path,
                        level_name,
                        package,
                        objects,
                        actors_by_name,
                        components_by_key,
                        prim,
                    )
                )
        components.extend(level_records)
        source_usd_total_bytes += stage_path.stat().st_size
        level_counts.append(
            {
                "source_level": level_name,
                "component_count": len(level_records),
                "instance_count": sum(row["instance_count"] for row in level_records),
                "source_world_usd": str(stage_path),
            }
        )

    instance_count = sum(row["instance_count"] for row in components)
    if len(components) != EXPECTED_COMPONENT_COUNT:
        raise RuntimeError(
            "StormPass Foliage component count changed: {} != {}".format(
                len(components), EXPECTED_COMPONENT_COUNT
            )
        )
    if instance_count != EXPECTED_INSTANCE_COUNT:
        raise RuntimeError(
            "StormPass Foliage instance count changed: {} != {}".format(
                instance_count, EXPECTED_INSTANCE_COUNT
            )
        )
    keys = [
        (row["source_level"], row["actor_object_index"], row["component_object_index"])
        for row in components
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("StormPass Foliage component keys are not unique")

    mesh_usage = Counter()
    material_usage = Counter()
    component_type_counts = Counter()
    collision_counts = Counter()
    shadow_counts = Counter()
    for row in components:
        mesh_usage[row["static_mesh_package"]] += row["instance_count"]
        component_type_counts[row["component_type"]] += 1
        collision_counts[
            str(row["settings"].get("collision_profile_name") or "<inherited/default>")
        ] += 1
        shadow_counts[str(row["settings"].get("cast_shadow"))] += 1
        for material in row["settings"].get("override_material_packages", []):
            if material:
                material_usage[material] += 1

    missing_mesh_usd = []
    for package in sorted(mesh_usage):
        candidates = resolver.source_candidates(package, ".usda")
        if not any(path.is_file() for path in candidates):
            missing_mesh_usd.append(
                {"package": package, "candidates": [str(path) for path in candidates]}
            )
    if missing_mesh_usd:
        raise RuntimeError("A StormPass Foliage mesh USDA is missing")

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "passed",
        "scope": {
            "visual_levels": visual_levels,
            "cinematic_levels_excluded": True,
            "fog_excluded": True,
            "light_excluded": True,
            "landscape_excluded": True,
        },
        "source": {
            "properties_root": str(PROPERTIES_ROOT),
            "world_root": str(WORLD_ROOT),
            "transform_source": "FModel world USDA PointInstancer arrays",
            "component_settings_source": "FModel Properties JSON",
            "coordinate_conversion": {
                "position": "UE=(USD.X,-USD.Y,USD.Z) after parent translation",
                "quaternion": "UE=(-USD.X,USD.Y,-USD.Z,USD.W)",
                "scale": "unchanged",
            },
        },
        "summary": {
            "visual_level_count": len(visual_levels),
            "point_instancer_component_count": len(components),
            "instance_count": instance_count,
            "unique_static_mesh_count": len(mesh_usage),
            "override_material_package_count": len(material_usage),
            "missing_mesh_usd_count": len(missing_mesh_usd),
            "source_world_usd_total_bytes": source_usd_total_bytes,
            "non_identity_parent_translation_component_count": sum(
                any(abs(float(value)) > MATRIX_TOLERANCE for value in row["parent_stage_translation"].values())
                for row in components
            ),
        },
        "component_type_counts": dict(sorted(component_type_counts.items())),
        "collision_profile_component_counts": dict(sorted(collision_counts.items())),
        "cast_shadow_component_counts": dict(sorted(shadow_counts.items())),
        "counts_by_level": level_counts,
        "mesh_usage": [
            {
                "package": package,
                "component_count": sum(
                    row["static_mesh_package"] == package for row in components
                ),
                "instance_count": count,
            }
            for package, count in sorted(mesh_usage.items())
        ],
        "override_material_usage": [
            {"package": package, "component_count": count}
            for package, count in sorted(material_usage.items())
        ],
        "missing_mesh_usd": missing_mesh_usd,
        "components": components,
    }
    write_json(METADATA_PATH, payload)
    report = {
        "status": "passed",
        "canonical_metadata": str(METADATA_PATH),
        **payload["summary"],
        "component_type_counts": payload["component_type_counts"],
        "collision_profile_component_counts": payload[
            "collision_profile_component_counts"
        ],
        "cast_shadow_component_counts": payload["cast_shadow_component_counts"],
        "fog_actor_count": 0,
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
