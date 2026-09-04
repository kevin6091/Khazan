"""Audit the persisted template-complete HeinMach environment reconstruction.

The source coverage report remains the authoritative per-actor inventory.  To
avoid repeating a full FModel survey, this audit records aggregate counts,
canonical SHA-256 signatures, and only mismatch samples.
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
RESTORE_SCRIPT = os.path.join(
    SCRIPT_DIR, "restore_heinmach_inherited_override_materials.py"
)


def load_restore_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_restored_level_audit_helpers", RESTORE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load inherited material restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_restore_module()
REPORT_PATH = os.path.join(
    restore.PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RestoredLevel_Integrity_Audit.json",
)
REMAINING_WHITE_TREE_REPORT_PATH = os.path.join(
    restore.PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RemainingWhiteTreeMaterial_Repair.json",
)
EXPECTED_FOG_SHA256 = "3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48"
TRANSFORM_TOLERANCE_CM = 0.02
ROTATION_TOLERANCE_DEGREES = 0.02
SCALE_TOLERANCE = 0.0002
MAX_MISMATCH_SAMPLES = 100


def canonical_sha256(records):
    encoded = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def vector_values(value):
    return [float(value.x), float(value.y), float(value.z)]


def rotator_values(value):
    return [float(value.pitch), float(value.yaw), float(value.roll)]


def source_location(placement):
    value = placement.get("transform", {}).get("location_cm", {})
    return [float(value.get(axis, 0.0)) for axis in ("x", "y", "z")]


def source_rotation(placement):
    value = placement.get("transform", {}).get("rotation_degrees", {})
    return [
        float(value.get("pitch", 0.0)),
        float(value.get("yaw", 0.0)),
        float(value.get("roll", 0.0)),
    ]


def source_scale(placement):
    value = placement.get("transform", {}).get("scale", {})
    return [float(value.get(axis, 1.0)) for axis in ("x", "y", "z")]


def vector_mismatch(actual, expected, tolerance):
    return any(abs(float(a) - float(b)) > tolerance for a, b in zip(actual, expected))


def canonical_quaternion(rotation):
    quat = unreal.Rotator(
        pitch=float(rotation[0]),
        yaw=float(rotation[1]),
        roll=float(rotation[2]),
    ).quaternion()
    values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
    # q and -q encode the same rotation.  Canonicalize the sign using the
    # first stable component so 180-degree rotations hash identically.
    for value in values:
        if abs(value) > 1.0e-7:
            if value < 0.0:
                values = [-item for item in values]
            break
    return values


def rotation_mismatch(actual, expected):
    actual_quat = canonical_quaternion(actual)
    expected_quat = canonical_quaternion(expected)
    dot = min(
        1.0,
        abs(sum(a * b for a, b in zip(actual_quat, expected_quat))),
    )
    angular_error_degrees = math.degrees(2.0 * math.acos(dot))
    return angular_error_degrees > ROTATION_TOLERANCE_DEGREES


def stripped_mesh_name(mesh):
    if not mesh:
        return None
    name = mesh.get_name()
    return name[3:] if name.startswith("SM_") else name


def mismatch_sample(samples, payload):
    if len(samples) < MAX_MISMATCH_SAMPLES:
        samples.append(payload)


def material_path(material):
    return material.get_path_name() if material else None


def object_path_mesh_name(value):
    name = str(value).rsplit(".", 1)[-1]
    return name[3:] if name.startswith("SM_") else name


def primary_texture_expectations(record, texture_index):
    mapping = {
        "Tex_D": ("BaseColorTexture", "OpacityTexture"),
        "Tex_S": ("MetallicTexture", "RoughnessTexture"),
        "Tex_N": ("NormalTexture",),
        "Tex_E": ("EmissiveColorTexture",),
    }
    result = {}
    for item in record["textures"]:
        if item["name"] not in mapping:
            continue
        texture = texture_index.get(item["texture_name"])
        if not texture:
            continue
        for parameter in mapping[item["name"]]:
            result[parameter] = texture.get_path_name()
    return result


def main():
    root_audit = restore.load_json(restore.ROOT_AUDIT_PATH)
    restoration = restore.load_json(restore.ROOT_RESTORATION_PATH)
    material_report = restore.load_json(restore.REPORT_PATH)
    remaining_white_tree_report = restore.load_json(
        REMAINING_WHITE_TREE_REPORT_PATH
    )
    allowed_recovered_tree_slots = {
        (
            str(record["actor_label"]),
            object_path_mesh_name(record["mesh"]),
            int(record["slot_index"]),
        ): str(record["material_after"])
        for record in remaining_white_tree_report.get("repaired_slots", [])
    }
    if (
        remaining_white_tree_report.get("status") != "repaired"
        or len(allowed_recovered_tree_slots) != 86
        or int(
            (remaining_white_tree_report.get("counts") or {}).get(
                "affected_component_slot_after", 1
            )
        )
        != 0
    ):
        raise RuntimeError("Remaining white-tree recovery evidence is incomplete")
    source_placements = list(root_audit.get("resolved_root_placements", []))
    mesh_packages = sorted(
        {str(item["static_mesh_package"]) for item in source_placements}
    )
    if (
        len(source_placements) != restore.EXPECTED_PLACEMENT_COUNT
        or len(mesh_packages) != restore.EXPECTED_MESH_COUNT
    ):
        raise RuntimeError("Source placement inventory changed")
    placements = restore.filter_excluded_placements(source_placements)
    if material_report.get("status") != "restored":
        raise RuntimeError("Inherited material restoration is not complete")

    rebuild_packages = sorted(
        item["package"]
        for item in restoration.get("placement_result", {}).get(
            "unresolved_override_materials", []
        )
    )
    raw_records = {
        package: restore.raw_material_record(package) for package in rebuild_packages
    }
    (
        mesh_mappings,
        source_package_to_actual,
        _,
        mesh_mapping_records,
    ) = restore.build_mesh_mappings(mesh_packages)
    material_name_index, _ = restore.material_asset_index()
    texture_index = restore.existing_texture_index()

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(restore.MAP_PATH):
        raise RuntimeError("Failed to load restored HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = [
        actor for actor in actor_subsystem.get_all_level_actors() if actor
    ]
    managed_actors = [
        actor
        for actor in all_actors
        if actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
    ]
    label_counts = collections.Counter(
        actor.get_actor_label() for actor in managed_actors
    )
    duplicate_labels = sorted(
        label for label, count in label_counts.items() if count != 1
    )
    actors_by_label = {actor.get_actor_label(): actor for actor in managed_actors}

    existing_material_cache = {}
    mismatch_samples = []
    counts = collections.Counter()
    per_level = collections.defaultdict(collections.Counter)
    current_records = []
    expected_records = []
    expected_labels = set()
    validated_recovered_tree_slots = set()
    min_location = [float("inf")] * 3
    max_location = [float("-inf")] * 3

    for placement in placements:
        level_name = placement["source_level"]
        level_counts = per_level[level_name]
        level_counts["expected_placements"] += 1
        label = restore.managed_label(placement)
        expected_labels.add(label)
        actor = actors_by_label.get(label)
        if not actor:
            counts["missing_actor_count"] += 1
            level_counts["missing_actors"] += 1
            mismatch_sample(
                mismatch_samples, {"type": "missing_actor", "label": label}
            )
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            counts["missing_component_count"] += 1
            level_counts["missing_components"] += 1
            mismatch_sample(
                mismatch_samples, {"type": "missing_component", "label": label}
            )
            continue

        actual_location = vector_values(actor.get_actor_location())
        actual_rotation = rotator_values(actor.get_actor_rotation())
        actual_scale = vector_values(actor.get_actor_scale3d())
        expected_placement = dict(placement)
        expected_placement["transform"] = restore.expected_transform(placement)
        expected_location = source_location(expected_placement)
        expected_rotation = source_rotation(expected_placement)
        expected_scale = source_scale(expected_placement)
        for axis in range(3):
            min_location[axis] = min(min_location[axis], actual_location[axis])
            max_location[axis] = max(max_location[axis], actual_location[axis])

        transform_bad = (
            vector_mismatch(
                actual_location, expected_location, TRANSFORM_TOLERANCE_CM
            )
            or rotation_mismatch(actual_rotation, expected_rotation)
            or vector_mismatch(actual_scale, expected_scale, SCALE_TOLERANCE)
        )
        if transform_bad:
            counts["transform_mismatch_count"] += 1
            level_counts["transform_mismatches"] += 1
            mismatch_sample(
                mismatch_samples,
                {
                    "type": "transform_mismatch",
                    "label": label,
                    "actual": {
                        "location": actual_location,
                        "rotation": actual_rotation,
                        "scale": actual_scale,
                    },
                    "expected": {
                        "location": expected_location,
                        "rotation": expected_rotation,
                        "scale": expected_scale,
                    },
                },
            )

        expected_mesh_name = restore.package_basename(
            placement["static_mesh_package"]
        )
        actual_mesh = component.get_editor_property("static_mesh")
        actual_mesh_name = stripped_mesh_name(actual_mesh)
        if actual_mesh_name != expected_mesh_name:
            counts["mesh_mismatch_count"] += 1
            level_counts["mesh_mismatches"] += 1
            mismatch_sample(
                mismatch_samples,
                {
                    "type": "mesh_mismatch",
                    "label": label,
                    "actual": actual_mesh_name,
                    "expected": expected_mesh_name,
                },
            )

        try:
            reverse_culling = bool(component.get_editor_property("reverse_culling"))
        except Exception:
            reverse_culling = False
        if reverse_culling:
            counts["reverse_culling_true_count"] += 1
        if actual_scale[0] * actual_scale[1] * actual_scale[2] < 0.0:
            counts["negative_determinant_count"] += 1

        slot_map = mesh_mappings[str(placement["static_mesh_package"])]
        expected_materials = {}
        current_materials = {}
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if not package:
                continue
            counts["source_override_reference_count"] += 1
            ue_slot = slot_map.get(source_slot)
            if ue_slot is None:
                counts["non_render_lod_or_unused_reference_count"] += 1
                continue
            counts["render_slot_override_reference_count"] += 1
            if package in raw_records:
                expected_material = unreal.EditorAssetLibrary.load_asset(
                    restore.MATERIAL_ROOT + "/MI_" + restore.package_basename(package)
                )
            else:
                if package not in existing_material_cache:
                    existing_material_cache[package] = (
                        restore.existing_material_for_package(
                            package,
                            source_package_to_actual,
                            material_name_index,
                        )
                    )
                expected_material = existing_material_cache[package]
            actual_material = component.get_material(ue_slot)
            authored_expected_path = material_path(expected_material)
            actual_path = material_path(actual_material)
            recovery_key = (label, expected_mesh_name, int(ue_slot))
            expected_path = allowed_recovered_tree_slots.get(
                recovery_key, authored_expected_path
            )
            expected_materials[str(ue_slot)] = expected_path
            current_materials[str(ue_slot)] = actual_path
            if not expected_path or actual_path != expected_path:
                counts["material_mismatch_count"] += 1
                level_counts["material_mismatches"] += 1
                mismatch_sample(
                    mismatch_samples,
                    {
                        "type": "material_mismatch",
                        "label": label,
                        "source_slot": source_slot,
                        "ue_slot": ue_slot,
                        "package": package,
                        "actual": actual_path,
                        "expected": expected_path,
                        "authored_expected": authored_expected_path,
                    },
                )
            elif recovery_key in allowed_recovered_tree_slots:
                validated_recovered_tree_slots.add(recovery_key)
                counts["validated_recovered_white_tree_override_count"] += 1

        static_material_count = len(
            list(actual_mesh.get_editor_property("static_materials"))
        ) if actual_mesh else 0
        override_materials = list(
            component.get_editor_property("override_materials")
        )
        stale = [
            material_path(material)
            for slot, material in enumerate(override_materials)
            if slot >= static_material_count and material
        ]
        if stale:
            counts["stale_out_of_range_override_actor_count"] += 1
            mismatch_sample(
                mismatch_samples,
                {
                    "type": "stale_out_of_range_override",
                    "label": label,
                    "materials": stale,
                },
            )

        current_record = {
            "label": label,
            "mesh": actual_mesh_name,
            "location": [round(value, 5) for value in actual_location],
            "rotation_quaternion": [
                round(value, 6) for value in canonical_quaternion(actual_rotation)
            ],
            "scale": [round(value, 7) for value in actual_scale],
            "render_override_materials": current_materials,
        }
        expected_record = {
            "label": label,
            "mesh": expected_mesh_name,
            "location": [round(value, 5) for value in expected_location],
            "rotation_quaternion": [
                round(value, 6) for value in canonical_quaternion(expected_rotation)
            ],
            "scale": [round(value, 7) for value in expected_scale],
            "render_override_materials": expected_materials,
        }
        current_records.append(current_record)
        expected_records.append(expected_record)
        level_counts["validated_placements"] += 1

    unexpected_labels = sorted(set(actors_by_label) - expected_labels)
    missing_labels = sorted(expected_labels - set(actors_by_label))
    counts["reported_recovered_white_tree_override_count"] = len(
        allowed_recovered_tree_slots
    )
    counts["managed_actor_count"] = len(managed_actors)
    counts["duplicate_managed_label_count"] = len(duplicate_labels)
    counts["unexpected_managed_actor_count"] = len(unexpected_labels)

    material_asset_issues = []
    primary_texture_mismatches = []
    library = unreal.MaterialEditingLibrary
    for package, record in raw_records.items():
        path = restore.MATERIAL_ROOT + "/MI_" + restore.package_basename(package)
        material = unreal.EditorAssetLibrary.load_asset(path)
        if not material:
            material_asset_issues.append({"package": package, "issue": "missing"})
            continue
        if material.get_class().get_name() != "MaterialInstanceConstant":
            material_asset_issues.append(
                {"package": package, "issue": "wrong_class", "class": material.get_class().get_name()}
            )
            continue
        for parameter, expected_path in primary_texture_expectations(
            record, texture_index
        ).items():
            try:
                actual_texture = library.get_material_instance_texture_parameter_value(
                    material, parameter
                )
            except Exception:
                actual_texture = None
            actual_path = material_path(actual_texture)
            if actual_path != expected_path:
                mismatch_sample(
                    primary_texture_mismatches,
                    {
                        "package": package,
                        "parameter": parameter,
                        "actual": actual_path,
                        "expected": expected_path,
                    },
                )
    counts["rebuilt_material_asset_issue_count"] = len(material_asset_issues)
    counts["primary_texture_parameter_mismatch_count"] = len(
        primary_texture_mismatches
    )

    fog = restore.fog_signature(actor_subsystem)
    failures = {
        key: value
        for key, value in counts.items()
        if key.endswith("mismatch_count")
        or key.endswith("issue_count")
        or key in {
            "missing_actor_count",
            "missing_component_count",
            "duplicate_managed_label_count",
            "unexpected_managed_actor_count",
            "stale_out_of_range_override_actor_count",
            "reverse_culling_true_count",
        }
        if value
    }
    if len(managed_actors) != len(placements):
        failures["managed_actor_count"] = len(managed_actors)
    if fog != {"count": restore.EXPECTED_FOG_COUNT, "sha256": EXPECTED_FOG_SHA256}:
        failures["fog_boundary"] = fog

    current_records.sort(key=lambda item: item["label"])
    expected_records.sort(key=lambda item: item["label"])
    report = {
        "status": "passed" if not failures else "failed",
        "map_path": restore.MAP_PATH,
        "source_inventory_report": restore.ROOT_AUDIT_PATH,
        "material_restoration_report": restore.REPORT_PATH,
        "checks": {
            "source_placement_count": restore.EXPECTED_PLACEMENT_COUNT,
            "active_placement_count": len(placements),
            "excluded_placement_count": len(source_placements) - len(placements),
            "unique_mesh_count": restore.EXPECTED_MESH_COUNT,
            "transform_tolerance_cm": TRANSFORM_TOLERANCE_CM,
            "rotation_tolerance_degrees": ROTATION_TOLERANCE_DEGREES,
            "scale_tolerance": SCALE_TOLERANCE,
        },
        "counts": dict(sorted(counts.items())),
        "world_bounds_cm": {"min": min_location, "max": max_location},
        "per_source_level": [
            {"source_level": level_name, **dict(sorted(level_counts.items()))}
            for level_name, level_counts in sorted(per_level.items())
        ],
        "canonical_signatures": {
            "expected_semantic_placement_sha256": canonical_sha256(expected_records),
            "current_semantic_placement_sha256": canonical_sha256(current_records),
            "record_count": len(current_records),
            "note": (
                "The authoritative full actor metadata remains in the source inventory "
                "report; hashes avoid duplicating and rescanning 9,104 records."
            ),
        },
        "fog_boundary": {
            "status": "unchanged" if fog["sha256"] == EXPECTED_FOG_SHA256 else "changed",
            "current": fog,
            "expected": {
                "count": restore.EXPECTED_FOG_COUNT,
                "sha256": EXPECTED_FOG_SHA256,
            },
        },
        "mesh_mapping_summary": {
            "mesh_count": len(mesh_mapping_records),
            "max_source_binding_slot_count": max(
                item["source_binding_slot_count"] for item in mesh_mapping_records
            ),
            "max_ue_slot_count": max(
                item["ue_slot_count"] for item in mesh_mapping_records
            ),
        },
        "duplicate_managed_labels": duplicate_labels,
        "missing_managed_labels": missing_labels[:MAX_MISMATCH_SAMPLES],
        "unexpected_managed_labels": unexpected_labels[:MAX_MISMATCH_SAMPLES],
        "placement_mismatch_samples": mismatch_samples,
        "material_asset_issues": material_asset_issues[:MAX_MISMATCH_SAMPLES],
        "primary_texture_parameter_mismatches": primary_texture_mismatches,
        "failures": failures,
        "excluded_content": [
            "Managed FogSheet modifications (read-only hash only)",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    restore.write_json(REPORT_PATH, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "counts": report["counts"],
                "fog_boundary": report["fog_boundary"],
                "failures": failures,
                "report": REPORT_PATH,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if failures:
        raise RuntimeError("Restored level integrity audit failed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        if not os.path.isfile(REPORT_PATH):
            restore.write_json(
                REPORT_PATH,
                {
                    "status": "failed",
                    "error": str(exception),
                    "traceback": traceback.format_exc(),
                },
            )
        unreal.log_error(str(exception))
        raise
