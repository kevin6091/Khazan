"""Audit reconstructed HeinMach placements and material surface settings.

The script is read-only. It compares every managed prop actor against the
FModel-derived placement manifest and correlates the material used by each UE
slot with the source material JSON referenced by the mesh USDA.
"""

import collections
import json
import math
import os
import re
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
PLACEMENT_PATH = os.path.join(
    unreal.Paths.project_content_dir(),
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_RenderableStaticMeshPlacements.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Placement_Surface_Audit.json",
)
MATERIAL_REPAIR_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Material_Surface_Repair.json",
)
OVERRIDE_MATERIAL_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Override_Material_Reconstruction.json",
)

MANAGED_LABEL_PREFIX = "HM_Prop_"
ENVIRONMENT_LEVELS = {
    "HeinMach_Chrcollision",
    "HeinMach_Landscape2",
    "HeinMach_Landscape1",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_Blizzard_2",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV07_BG",
    "HeinMach_SubLV05_Escape_1",
}

INDEX_RE = re.compile(r"unrealMaterialIndex\s*=\s*(-?\d+)")
BINDING_RE = re.compile(r"rel\s+material:binding\s*=\s*<.*?/Materials/([^>]+)>")
MATERIAL_DEF_RE = re.compile(r'\bdef\s+Material\s+"([^"]+)"')
REFERENCE_RE = re.compile(r"references\s*=\s*@([^@]+)@")
NUMERIC_DUPLICATE_SUFFIX_RE = re.compile(r"_\d+$")


def log(message):
    unreal.log("KHAZAN_HEINMACH_AUDIT: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def source_usd_path(package):
    return os.path.join(FMODEL_ROOT, *str(package).split("/")) + ".usda"


def accepted_placements(payload):
    return [
        placement
        for placement in payload.get("placements", [])
        if placement.get("source_level") in ENVIRONMENT_LEVELS
        and placement.get("visible") is not False
        and placement.get("static_mesh_package")
    ]


def managed_label(placement):
    return (
        "{}{}_{}_{}".format(
            MANAGED_LABEL_PREFIX,
            placement.get("source_level", "Unknown"),
            placement.get("source_object_index", 0),
            placement.get("actor_name", "Actor"),
        )
    )[:220]


def vector_values(value):
    return float(value.x), float(value.y), float(value.z)


def expected_location(placement):
    value = placement.get("transform", {}).get("location_cm", {})
    return float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("z", 0.0))


def expected_scale(placement):
    value = placement.get("transform", {}).get("scale", {})
    return float(value.get("x", 1.0)), float(value.get("y", 1.0)), float(value.get("z", 1.0))


def expected_rotation(placement):
    value = placement.get("transform", {}).get("rotation_degrees", {})
    return (
        float(value.get("pitch", 0.0)),
        float(value.get("yaw", 0.0)),
        float(value.get("roll", 0.0)),
    )


def rotation_values(value):
    return float(value.pitch), float(value.yaw), float(value.roll)


def vector_distance(a, b):
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def angular_error(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def rotation_error(a, b):
    return max(angular_error(left, right) for left, right in zip(a, b))


def unit_vector_angle_degrees(a, b):
    left = vector_values(a)
    right = vector_values(b)
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if left_length <= 1.0e-8 or right_length <= 1.0e-8:
        return 180.0
    cosine = sum(x * y for x, y in zip(left, right)) / (left_length * right_length)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def orientation_error(actor, placement):
    pitch, yaw, roll = expected_rotation(placement)
    expected = unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll)
    expected_forward = unreal.MathLibrary.get_forward_vector(expected)
    expected_up = unreal.MathLibrary.get_up_vector(expected)
    return max(
        unit_vector_angle_degrees(actor.get_actor_forward_vector(), expected_forward),
        unit_vector_angle_degrees(actor.get_actor_up_vector(), expected_up),
    )


def normalized_mesh_name(name):
    return name[3:] if name.startswith("SM_") else name


def object_path(asset):
    return asset.get_path_name() if asset else None


def safe_property(target, name, default=None):
    try:
        return target.get_editor_property(name)
    except Exception:
        return default


def enum_text(value):
    return str(value) if value is not None else None


def material_state(material):
    state = {
        "asset": object_path(material),
        "class": material.get_class().get_name() if material else None,
        "parent": None,
        "base_material": None,
        "base_two_sided": None,
        "effective_two_sided": None,
        "override_two_sided": None,
        "instance_two_sided": None,
        "base_blend_mode": None,
        "override_blend_mode": None,
        "instance_blend_mode": None,
        "effective_blend_mode": None,
    }
    if not material:
        return state

    class_name = state["class"] or ""
    parent = safe_property(material, "parent") if "MaterialInstance" in class_name else None
    state["parent"] = object_path(parent)

    overrides = safe_property(material, "base_property_overrides")
    if overrides is not None:
        state["override_two_sided"] = bool(
            safe_property(overrides, "override_two_sided", False)
        )
        state["instance_two_sided"] = bool(safe_property(overrides, "two_sided", False))
        state["override_blend_mode"] = bool(
            safe_property(overrides, "override_blend_mode", False)
        )
        state["instance_blend_mode"] = enum_text(
            safe_property(overrides, "blend_mode")
        )

    visited = set()
    base = material
    while base and "MaterialInstance" in base.get_class().get_name():
        path = object_path(base)
        if path in visited:
            base = None
            break
        visited.add(path)
        base = safe_property(base, "parent")

    if base:
        state["base_material"] = object_path(base)
        state["base_two_sided"] = bool(safe_property(base, "two_sided", False))
        state["base_blend_mode"] = enum_text(safe_property(base, "blend_mode"))

    if state["override_two_sided"]:
        state["effective_two_sided"] = state["instance_two_sided"]
    else:
        state["effective_two_sided"] = state["base_two_sided"]
    if state["override_blend_mode"]:
        state["effective_blend_mode"] = state["instance_blend_mode"]
    else:
        state["effective_blend_mode"] = state["base_blend_mode"]
    return state


def validated_material_repairs():
    if not os.path.isfile(MATERIAL_REPAIR_REPORT_PATH):
        return {"status": "repair report missing"}, {}, {}
    repair_report = load_json(MATERIAL_REPAIR_REPORT_PATH)
    actual_states = {}
    two_sided_expected_count = 0
    two_sided_mismatch_count = 0
    masked_expected_count = 0
    masked_mismatch_count = 0
    assignment_count = 0
    slot_maps = {}

    for mesh_record in repair_report.get("mesh_mappings", []):
        slot_maps[mesh_record["mesh_package"]] = {
            int(item["source_slot"]): int(item["ue_slot"])
            for item in mesh_record.get("assignments", [])
        }
        for assignment in mesh_record.get("assignments", []):
            assignment_count += 1
            path = assignment.get("actual_material_path")
            if path not in actual_states:
                actual_states[path] = material_state(
                    unreal.EditorAssetLibrary.load_asset(path)
                )
            state = actual_states[path]
            source = assignment.get("source", {})
            if source.get("two_sided") is True:
                two_sided_expected_count += 1
                if state.get("effective_two_sided") is not True:
                    two_sided_mismatch_count += 1
            if str(source.get("blend_mode")) in {"BLEND_Masked", "1"}:
                masked_expected_count += 1
                if "BLEND_MASKED" not in str(state.get("effective_blend_mode")):
                    masked_mismatch_count += 1

    return (
        {
            "status": "validated",
            "assignment_count": assignment_count,
            "unique_material_count": len(actual_states),
            "two_sided_expected_assignment_count": two_sided_expected_count,
            "two_sided_mismatch_count": two_sided_mismatch_count,
            "masked_expected_assignment_count": masked_expected_count,
            "masked_mismatch_count": masked_mismatch_count,
        },
        slot_maps,
        actual_states,
    )


def validated_override_materials(placements, label_groups, slot_maps):
    if not os.path.isfile(OVERRIDE_MATERIAL_REPORT_PATH):
        return {"status": "override material report missing"}
    override_report = load_json(OVERRIDE_MATERIAL_REPORT_PATH)
    expected_materials = {
        item["package"]: item["material"]
        for item in override_report.get("material_results", [])
    }
    target_count = 0
    mismatch_count = 0
    fallback_count = 0
    mismatch_examples = []
    for placement in placements:
        actors = label_groups.get(managed_label(placement), [])
        if len(actors) != 1:
            continue
        component = actors[0].get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            continue
        slot_map = slot_maps.get(str(placement["static_mesh_package"]), {})
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            expected_path = expected_materials.get(package)
            if not expected_path:
                continue
            target_count += 1
            ue_slot = slot_map.get(source_slot)
            if ue_slot is None and len(slot_map) == 1:
                ue_slot = next(iter(slot_map.values()))
                fallback_count += 1
            actual = component.get_material(ue_slot) if ue_slot is not None else None
            actual_path = object_path(actual)
            if actual_path != expected_path:
                mismatch_count += 1
                if len(mismatch_examples) < 50:
                    mismatch_examples.append(
                        {
                            "label": managed_label(placement),
                            "source_slot": source_slot,
                            "ue_slot": ue_slot,
                            "package": package,
                            "expected_material": expected_path,
                            "actual_material": actual_path,
                        }
                    )
    return {
        "status": "validated",
        "target_assignment_count": target_count,
        "single_slot_fallback_count": fallback_count,
        "mismatch_count": mismatch_count,
        "mismatch_examples": mismatch_examples,
    }


def parse_mesh_materials(mesh_package):
    """Return source material data keyed by the Unreal material slot index."""
    path = source_usd_path(mesh_package)
    result = {
        "mesh_usd": path,
        "exists": os.path.isfile(path),
        "slots": {},
        "references": {},
        "parse_errors": [],
    }
    if not result["exists"]:
        return result

    pending_index = None
    pending_material = None
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as source:
            for line in source:
                match = INDEX_RE.search(line)
                if match:
                    pending_index = int(match.group(1))
                    continue
                match = BINDING_RE.search(line)
                if match and pending_index is not None:
                    result["slots"].setdefault(str(pending_index), match.group(1))
                    pending_index = None
                    continue
                match = MATERIAL_DEF_RE.search(line)
                if match:
                    pending_material = match.group(1)
                    continue
                match = REFERENCE_RE.search(line)
                if match and pending_material:
                    reference = match.group(1).replace("/", os.sep)
                    result["references"][pending_material] = os.path.normpath(
                        os.path.join(os.path.dirname(path), reference)
                    )
                    pending_material = None
    except Exception as exception:
        result["parse_errors"].append(str(exception))
    return result


def source_material_info(package=None, name=None, reference_usd=None):
    if package:
        material_name = package_basename(package)
        json_path = os.path.join(FMODEL_ROOT, *str(package).split("/")) + ".json"
    else:
        material_name = name
        json_path = os.path.splitext(reference_usd or "")[0] + ".json"

    result = {
        "name": material_name,
        "package": package,
        "json_path": json_path or None,
        "json_exists": bool(json_path and os.path.isfile(json_path)),
        "two_sided": None,
        "override_two_sided": None,
        "blend_mode": None,
        "opacity_mask_clip_value": None,
        "error": None,
    }
    if not result["json_exists"]:
        return result

    try:
        payload = load_json(json_path)
        parameters = payload.get("Parameters", {})
        properties = parameters.get("Properties", {})
        overrides = properties.get("BasePropertyOverrides", {})
        result["override_two_sided"] = bool(
            overrides.get("bOverride_TwoSided", False)
        )
        if "TwoSided" in overrides:
            result["two_sided"] = bool(overrides.get("TwoSided"))
        result["blend_mode"] = overrides.get("BlendMode", parameters.get("BlendMode"))
        result["opacity_mask_clip_value"] = overrides.get("OpacityMaskClipValue")
    except Exception as exception:
        result["error"] = str(exception)
    return result


def source_key(info):
    return info.get("package") or info.get("json_path") or info.get("name") or "<unknown>"


def main():
    payload = load_json(PLACEMENT_PATH)
    placements = accepted_placements(payload)
    expected_by_label = {managed_label(placement): placement for placement in placements}

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach map: " + MAP_PATH)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    label_groups = collections.defaultdict(list)
    for actor in actor_subsystem.get_all_level_actors():
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX):
            label_groups[actor.get_actor_label()].append(actor)

    duplicate_labels = {
        label: len(actors) for label, actors in label_groups.items() if len(actors) != 1
    }
    missing_labels = sorted(set(expected_by_label) - set(label_groups))
    unexpected_labels = sorted(set(label_groups) - set(expected_by_label))

    mesh_material_cache = {}
    source_info_cache = {}
    actual_material_cache = {}
    material_usage = {}
    runtime_meshes = {}
    placement_mismatches = []
    location_errors = []
    rotation_errors = []
    scale_errors = []
    mesh_mismatch_count = 0
    negative_determinant_count = 0
    negative_determinant_reverse_culling_count = 0
    reverse_culling_count = 0
    slot_observation_count = 0
    source_two_sided_slot_count = 0
    source_two_sided_mismatch_count = 0
    source_two_sided_mismatches = []
    source_masked_slot_count = 0
    material_repair_validation, repair_slot_maps, repaired_material_states = (
        validated_material_repairs()
    )

    for index, placement in enumerate(placements, start=1):
        label = managed_label(placement)
        actors = label_groups.get(label, [])
        if len(actors) != 1:
            continue
        actor = actors[0]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            placement_mismatches.append({"label": label, "error": "missing StaticMeshComponent"})
            continue

        actual_location = vector_values(actor.get_actor_location())
        actual_scale = vector_values(actor.get_actor_scale3d())
        location_error = vector_distance(actual_location, expected_location(placement))
        rotation_delta = orientation_error(actor, placement)
        scale_error = vector_distance(actual_scale, expected_scale(placement))
        location_errors.append(location_error)
        rotation_errors.append(rotation_delta)
        scale_errors.append(scale_error)

        mesh = safe_property(component, "static_mesh")
        expected_mesh = package_basename(placement["static_mesh_package"])
        actual_mesh = normalized_mesh_name(mesh.get_name()) if mesh else None
        if mesh:
            runtime_meshes.setdefault(str(placement["static_mesh_package"]), mesh)
        mesh_matches = actual_mesh == expected_mesh
        if not mesh_matches:
            mesh_mismatch_count += 1

        reverse_culling = bool(safe_property(component, "reverse_culling", False))
        determinant_negative = actual_scale[0] * actual_scale[1] * actual_scale[2] < 0.0
        reverse_culling_count += int(reverse_culling)
        negative_determinant_count += int(determinant_negative)
        negative_determinant_reverse_culling_count += int(
            determinant_negative and reverse_culling
        )

        if (
            location_error > 0.1
            or rotation_delta > 0.01
            or scale_error > 0.0001
            or not mesh_matches
        ) and len(placement_mismatches) < 100:
            placement_mismatches.append(
                {
                    "label": label,
                    "location_error_cm": location_error,
                    "rotation_error_degrees": rotation_delta,
                    "scale_error": scale_error,
                    "expected_mesh": expected_mesh,
                    "actual_mesh": actual_mesh,
                }
            )

        mesh_package = str(placement["static_mesh_package"])
        if mesh_package not in mesh_material_cache:
            mesh_material_cache[mesh_package] = parse_mesh_materials(mesh_package)
        mesh_materials = mesh_material_cache[mesh_package]
        overrides = placement.get("override_material_packages", [])
        source_slots = mesh_materials.get("slots", {})
        source_slot_indices = [int(value) for value in source_slots.keys()]
        source_slot_count = max(
            len(overrides),
            (max(source_slot_indices) + 1) if source_slot_indices else 0,
        )
        source_to_ue_slots = repair_slot_maps.get(mesh_package, {})

        for source_slot_index in range(source_slot_count):
            ue_slot_index = source_to_ue_slots.get(
                source_slot_index, source_slot_index
            )
            override_package = (
                overrides[source_slot_index]
                if source_slot_index < len(overrides)
                else None
            )
            source_name = source_slots.get(str(source_slot_index))
            reference_usd = mesh_materials.get("references", {}).get(source_name)
            cache_key = override_package or reference_usd or source_name or "<unknown>"
            if cache_key not in source_info_cache:
                source_info_cache[cache_key] = source_material_info(
                    package=override_package,
                    name=source_name,
                    reference_usd=reference_usd,
                )
            source_info = source_info_cache[cache_key]

            actual_material = component.get_material(ue_slot_index)
            actual_path = object_path(actual_material) or "<none>"
            if actual_path not in actual_material_cache:
                actual_material_cache[actual_path] = material_state(actual_material)
            actual_state = actual_material_cache[actual_path]

            key = source_key(source_info)
            usage = material_usage.setdefault(
                key,
                {
                    "source": source_info,
                    "slot_usage_count": 0,
                    "actual_materials": collections.Counter(),
                    "effective_two_sided_values": collections.Counter(),
                },
            )
            usage["slot_usage_count"] += 1
            usage["actual_materials"][actual_path] += 1
            usage["effective_two_sided_values"][str(actual_state["effective_two_sided"])] += 1
            slot_observation_count += 1

            if source_info.get("two_sided") is True:
                source_two_sided_slot_count += 1
                if actual_state.get("effective_two_sided") is not True:
                    source_two_sided_mismatch_count += 1
                    source_two_sided_mismatches.append(
                        {
                            "label": label,
                            "mesh_package": mesh_package,
                            "source_slot_index": source_slot_index,
                            "ue_slot_index": ue_slot_index,
                            "source_material": source_info,
                            "actual_material": actual_path,
                            "actual_state": actual_state,
                        }
                    )
            if str(source_info.get("blend_mode")) in {"BLEND_Masked", "1"}:
                source_masked_slot_count += 1

        if index % 250 == 0:
            log("Audited {}/{} managed placements".format(index, len(placements)))

    serialized_material_usage = []
    for key, usage in sorted(material_usage.items()):
        serialized_material_usage.append(
            {
                "source_key": key,
                "source": usage["source"],
                "slot_usage_count": usage["slot_usage_count"],
                "actual_materials": dict(usage["actual_materials"].most_common()),
                "effective_two_sided_values": dict(
                    usage["effective_two_sided_values"].most_common()
                ),
            }
        )

    mesh_slot_records = []
    mesh_slot_mismatch_count = 0
    mesh_slot_count_mismatch_count = 0
    for mesh_package, mesh in sorted(runtime_meshes.items()):
        source_slots = mesh_material_cache[mesh_package].get("slots", {})
        source_slot_count = (
            max(int(slot) for slot in source_slots.keys()) + 1 if source_slots else 0
        )
        static_materials = list(safe_property(mesh, "static_materials", []) or [])
        ue_slots = []
        slot_mismatches = []
        for slot_index, static_material in enumerate(static_materials):
            interface = safe_property(static_material, "material_interface")
            actual_name = interface.get_name() if interface else None
            comparable_name = actual_name[3:] if actual_name and actual_name.startswith("MI_") else actual_name
            expected_name = source_slots.get(str(slot_index))
            matches = comparable_name == expected_name
            if not matches:
                slot_mismatches.append(
                    {
                        "slot_index": slot_index,
                        "expected_source_material": expected_name,
                        "actual_material": actual_name,
                    }
                )
            ue_slots.append(
                {
                    "slot_index": slot_index,
                    "material": object_path(interface),
                    "material_slot_name": str(
                        safe_property(static_material, "material_slot_name", "")
                    ),
                    "imported_material_slot_name": str(
                        safe_property(static_material, "imported_material_slot_name", "")
                    ),
                }
            )
        count_matches = source_slot_count == len(static_materials)
        if not count_matches:
            mesh_slot_count_mismatch_count += 1
        if slot_mismatches or not count_matches:
            mesh_slot_mismatch_count += 1
        mesh_slot_records.append(
            {
                "mesh_package": mesh_package,
                "ue_mesh": object_path(mesh),
                "source_slot_count": source_slot_count,
                "ue_slot_count": len(static_materials),
                "source_slots": source_slots,
                "ue_slots": ue_slots,
                "slot_mismatches": slot_mismatches,
            }
        )

    def error_summary(values):
        return {
            "count": len(values),
            "maximum": max(values) if values else None,
            "mean": sum(values) / len(values) if values else None,
        }

    override_material_validation = validated_override_materials(
        placements, label_groups, repair_slot_maps
    )

    report = {
        "status": "audited",
        "map_path": MAP_PATH,
        "manifest_path": PLACEMENT_PATH,
        "placement_validation": {
            "expected_count": len(placements),
            "managed_actor_count": sum(len(actors) for actors in label_groups.values()),
            "unique_managed_label_count": len(label_groups),
            "missing_label_count": len(missing_labels),
            "missing_labels": missing_labels[:100],
            "unexpected_label_count": len(unexpected_labels),
            "unexpected_labels": unexpected_labels[:100],
            "duplicate_labels": duplicate_labels,
            "mesh_mismatch_count": mesh_mismatch_count,
            "location_error_cm": error_summary(location_errors),
            "rotation_error_degrees": error_summary(rotation_errors),
            "scale_error": error_summary(scale_errors),
            "mismatch_examples": placement_mismatches,
        },
        "culling_validation": {
            "negative_determinant_actor_count": negative_determinant_count,
            "reverse_culling_actor_count": reverse_culling_count,
            "negative_determinant_and_reverse_culling_actor_count": (
                negative_determinant_reverse_culling_count
            ),
            "note": (
                "UE StaticMeshSceneProxy already XORs reverse_culling with the local-to-world "
                "negative determinant; negative scale alone does not require reverse_culling."
            ),
        },
        "material_validation": {
            "slot_observation_count": slot_observation_count,
            "unique_source_material_count": len(material_usage),
            "unique_actual_material_count": len(actual_material_cache),
            "source_two_sided_slot_count": source_two_sided_slot_count,
            "source_two_sided_mismatch_count": source_two_sided_mismatch_count,
            "source_two_sided_mismatches": source_two_sided_mismatches,
            "source_masked_slot_count": source_masked_slot_count,
            "mesh_slot_mismatch_count": mesh_slot_mismatch_count,
            "mesh_slot_count_mismatch_count": mesh_slot_count_mismatch_count,
        },
        "actual_material_states": actual_material_cache,
        "material_repair_validation": material_repair_validation,
        "override_material_validation": override_material_validation,
        "source_material_usage": serialized_material_usage,
        "mesh_slot_validation": mesh_slot_records,
        "source_mesh_parse_error_count": sum(
            bool(value.get("parse_errors")) for value in mesh_material_cache.values()
        ),
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT placements={} missing={} transform_mismatches={} mesh_mismatches={} "
        "two_sided_mismatches={} report={}".format(
            len(placements),
            len(missing_labels),
            len(placement_mismatches),
            mesh_mismatch_count,
            source_two_sided_mismatch_count,
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        unreal.log_error("KHAZAN_HEINMACH_AUDIT: " + str(exception))
        unreal.log_error(failure["traceback"])
        raise
