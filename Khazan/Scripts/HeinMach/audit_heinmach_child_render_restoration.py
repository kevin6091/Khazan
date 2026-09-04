"""Audit all 27 restored non-root HeinMach render mesh components.

This consumes the cached template-aware inventory instead of rescanning FModel.
It validates the original 15 direct child meshes and the 12 newly discovered
template-inherited child meshes against the persisted editor level.
"""

import hashlib
import importlib.util
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_RESTORE_PATH = os.path.join(SCRIPT_DIR, "restore_heinmach_child_render_meshes.py")
NEW_RESTORE_PATH = os.path.join(
    SCRIPT_DIR, "restore_heinmach_inherited_child_render_meshes.py"
)
DIRECT_REPAIR_PATH = os.path.join(
    SCRIPT_DIR, "repair_heinmach_direct_child_render_meshes.py"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_ChildRender_Integrity_Audit.json",
)
EXPECTED_DIRECT_COUNT = 15
EXPECTED_INHERITED_COUNT = 12
EXPECTED_TOTAL_COUNT = 27
EXPECTED_UNIQUE_MESH_COUNT = 7
MAX_MISMATCH_SAMPLES = 100


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load audit helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load_module("khazan_heinmach_direct_child_helpers", OLD_RESTORE_PATH)
new = load_module("khazan_heinmach_inherited_child_helpers", NEW_RESTORE_PATH)
direct_repair = load_module("khazan_heinmach_direct_child_repair_helpers", DIRECT_REPAIR_PATH)


def canonical_sha256(records):
    encoded = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_direct(record):
    return bool(record.get("resolution", {}).get("already_in_old_direct_gap_report"))


def expected_label(record):
    return old.managed_label(record) if is_direct(record) else new.managed_label(record)


def expected_prefix(record):
    return old.MANAGED_LABEL_PREFIX if is_direct(record) else new.MANAGED_LABEL_PREFIX


def canonical_quaternion(rotation):
    quat = rotation if isinstance(rotation, unreal.Quat) else rotation.quaternion()
    values = [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]
    for value in values:
        if abs(value) > 1.0e-7:
            if value < 0.0:
                values = [-item for item in values]
            break
    return values


def vector_mismatch(actual, expected, tolerance):
    return any(abs(float(a) - float(b)) > tolerance for a, b in zip(actual, expected))


def rotation_mismatch(actual, expected):
    a = canonical_quaternion(actual)
    b = canonical_quaternion(expected)
    dot = min(1.0, abs(sum(left * right for left, right in zip(a, b))))
    return math.degrees(2.0 * math.acos(dot)) > new.ROTATION_TOLERANCE_DEGREES


def material_matches(material, source_package):
    if not material:
        return False
    return new.package_basename(source_package) in new.normalized_asset_names(material)


def main():
    payload = new.load_json(new.AUDIT_PATH)
    if payload.get("status") != "audited":
        raise RuntimeError("Template-child coverage report is not audited")
    records = list(payload.get("resolved_child_mesh_components", []))
    direct_count = sum(is_direct(record) for record in records)
    inherited_count = len(records) - direct_count
    unique_mesh_count = len(
        {str(record.get("static_mesh_package", "")) for record in records}
    )
    source_counts = {
        "direct_component_count": direct_count,
        "inherited_component_count": inherited_count,
        "total_component_count": len(records),
        "unique_mesh_count": unique_mesh_count,
    }
    expected_counts = {
        "direct_component_count": EXPECTED_DIRECT_COUNT,
        "inherited_component_count": EXPECTED_INHERITED_COUNT,
        "total_component_count": EXPECTED_TOTAL_COUNT,
        "unique_mesh_count": EXPECTED_UNIQUE_MESH_COUNT,
    }
    if source_counts != expected_counts:
        raise RuntimeError(
            "Child source inventory changed: actual={} expected={}".format(
                source_counts, expected_counts
            )
        )

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(new.MAP_PATH + "."):
        if not level_subsystem.load_level(new.MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = list(actor_subsystem.get_all_level_actors())

    managed_actors = [
        actor
        for actor in all_actors
        if actor
        and actor.get_actor_label().startswith(
            (old.MANAGED_LABEL_PREFIX, new.MANAGED_LABEL_PREFIX)
        )
    ]
    actors_by_label = {}
    duplicate_labels = []
    for actor in managed_actors:
        label = actor.get_actor_label()
        if label in actors_by_label:
            duplicate_labels.append(label)
        actors_by_label[label] = actor

    expected_labels = {expected_label(record) for record in records}
    missing_labels = sorted(expected_labels - set(actors_by_label))
    unexpected_labels = sorted(set(actors_by_label) - expected_labels)
    mismatch_samples = []
    expected_signature_records = []
    current_signature_records = []
    material_override_checks = 0
    non_render_override_references = 0
    direct_slot_mappings = {}
    for record in records:
        if not is_direct(record):
            continue
        mesh_package = record["static_mesh_package"]
        if mesh_package in direct_slot_mappings:
            continue
        actor = actors_by_label.get(expected_label(record))
        component = actor.get_component_by_class(unreal.StaticMeshComponent) if actor else None
        mesh = component.get_editor_property("static_mesh") if component else None
        if mesh:
            direct_slot_mappings[mesh_package] = direct_repair.build_slot_mapping(
                mesh_package, mesh
            )[0]

    for record in records:
        label = expected_label(record)
        actor = actors_by_label.get(label)
        expected = new.expected_world_transform(record)
        expected_signature_records.append(
            {
                "label": label,
                "mesh": new.package_basename(record["static_mesh_package"]),
                "location": [
                    round(expected.translation.x, 5),
                    round(expected.translation.y, 5),
                    round(expected.translation.z, 5),
                ],
                "rotation_quaternion": [
                    round(value, 6) for value in canonical_quaternion(expected.rotation)
                ],
                "scale": [
                    round(expected.scale3d.x, 7),
                    round(expected.scale3d.y, 7),
                    round(expected.scale3d.z, 7),
                ],
            }
        )
        if not actor:
            continue

        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        mesh = component.get_editor_property("static_mesh") if component else None
        actual_mesh = None
        if mesh:
            actual_mesh = mesh.get_name()[3:] if mesh.get_name().startswith("SM_") else mesh.get_name()
        current_signature_records.append(
            {
                "label": label,
                "mesh": actual_mesh,
                "location": [round(location.x, 5), round(location.y, 5), round(location.z, 5)],
                "rotation_quaternion": [
                    round(value, 6) for value in canonical_quaternion(rotation)
                ],
                "scale": [round(scale.x, 7), round(scale.y, 7), round(scale.z, 7)],
            }
        )

        issues = []
        if not component:
            issues.append("missing_static_mesh_component")
        elif new.package_basename(record["static_mesh_package"]) not in new.normalized_asset_names(mesh):
            issues.append("mesh")
        if vector_mismatch(
            (location.x, location.y, location.z),
            (expected.translation.x, expected.translation.y, expected.translation.z),
            new.LOCATION_TOLERANCE_CM,
        ):
            issues.append("location")
        if rotation_mismatch(rotation, expected.rotation):
            issues.append("rotation")
        if vector_mismatch(
            (scale.x, scale.y, scale.z),
            (expected.scale3d.x, expected.scale3d.y, expected.scale3d.z),
            new.SCALE_TOLERANCE,
        ):
            issues.append("scale")
        if component and component.get_editor_property("reverse_culling"):
            issues.append("reverse_culling")
        if component and bool(component.get_editor_property("cast_shadow")) != bool(
            record.get("cast_shadow", True)
        ):
            issues.append("cast_shadow")

        if component:
            for source_slot, material_package in enumerate(
                record.get("override_material_packages", [])
            ):
                if not material_package:
                    continue
                slot_mapping = direct_slot_mappings.get(
                    record["static_mesh_package"], {}
                )
                if source_slot not in slot_mapping:
                    non_render_override_references += 1
                    continue
                material_override_checks += 1
                try:
                    ue_slot = slot_mapping[source_slot]
                    actual_material = component.get_material(ue_slot)
                except Exception:
                    actual_material = None
                if not material_matches(actual_material, material_package):
                    issues.append("override_material_slot_{}".format(source_slot))

        if issues and len(mismatch_samples) < MAX_MISMATCH_SAMPLES:
            mismatch_samples.append({"label": label, "issues": sorted(set(issues))})

    fog = new.fog_signature(actor_subsystem)
    expected_fog = {"count": new.EXPECTED_FOG_COUNT, "sha256": new.EXPECTED_FOG_SHA256}
    failures = {}
    if len(managed_actors) != EXPECTED_TOTAL_COUNT:
        failures["managed_actor_count"] = len(managed_actors)
    if duplicate_labels:
        failures["duplicate_label_count"] = len(duplicate_labels)
    if missing_labels:
        failures["missing_actor_count"] = len(missing_labels)
    if unexpected_labels:
        failures["unexpected_actor_count"] = len(unexpected_labels)
    if mismatch_samples:
        failures["placement_or_material_mismatch_count"] = len(mismatch_samples)
    if non_render_override_references != direct_repair.EXPECTED_NON_RENDER_REFERENCE_COUNT:
        failures["non_render_override_reference_count"] = non_render_override_references
    if fog != expected_fog:
        failures["fog_boundary"] = fog

    expected_signature_records.sort(key=lambda item: item["label"])
    current_signature_records.sort(key=lambda item: item["label"])
    report = {
        "status": "passed" if not failures else "failed",
        "map_path": new.MAP_PATH,
        "source_inventory_report": new.AUDIT_PATH,
        "source_counts": source_counts,
        "current_managed_actor_count": len(managed_actors),
        "material_override_check_count": material_override_checks,
        "non_render_lod_or_unused_override_reference_count": non_render_override_references,
        "canonical_signatures": {
            "expected_sha256": canonical_sha256(expected_signature_records),
            "current_sha256": canonical_sha256(current_signature_records),
            "record_count": len(current_signature_records),
        },
        "fog_boundary": {
            "status": "unchanged" if fog == expected_fog else "changed",
            "current": fog,
            "expected": expected_fog,
        },
        "duplicate_labels": duplicate_labels[:MAX_MISMATCH_SAMPLES],
        "missing_labels": missing_labels[:MAX_MISMATCH_SAMPLES],
        "unexpected_labels": unexpected_labels[:MAX_MISMATCH_SAMPLES],
        "mismatch_samples": mismatch_samples,
        "failures": failures,
        "excluded_content": [
            "Managed FogSheet modifications (read-only hash only)",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    new.write_json(REPORT_PATH, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "source_counts": source_counts,
                "managed_actor_count": len(managed_actors),
                "material_override_check_count": material_override_checks,
                "fog_boundary": report["fog_boundary"],
                "failures": failures,
                "report": REPORT_PATH,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if failures:
        raise RuntimeError("Child-render integrity audit failed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        if not os.path.isfile(REPORT_PATH):
            new.write_json(
                REPORT_PATH,
                {"status": "failed", "error": str(exception), "traceback": traceback.format_exc()},
            )
        unreal.log_error("KHAZAN_HEINMACH_CHILD_AUDIT: " + str(exception))
        raise
