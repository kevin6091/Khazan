"""Restore FModel material semantics on the corrected HeinMach USD import.

USD preserves each geometry subset binding, but UE is free to reorder the
resulting static-mesh slots and FModel's PreviewSurface export does not carry
MaterialInstance base-property overrides. This script correlates source and UE
materials by their texture fingerprints, restores TwoSided/blend/clip settings,
and remaps sparse actor overrides from original slot indices to UE slot indices.
"""

import collections
import itertools
import json
import os
import re
import traceback

import unreal


APPLY_CHANGES = True
UPDATE_MATERIAL_INSTANCES = True

FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
CORRECTED_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets"
)
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
    "HeinMach_Material_Surface_Repair.json",
)

MANAGED_LABEL_PREFIX = "HM_Prop_"
EXPECTED_PLACEMENT_COUNT = 2665
EXPECTED_MESH_COUNT = 183
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
TRAILING_IMPORT_SUFFIX_RE = re.compile(r"_\d+$")


def log(message):
    unreal.log("KHAZAN_HEINMACH_MATERIAL_REPAIR: " + str(message))


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


def canonical_path(path):
    return os.path.normcase(os.path.abspath(path)) if path else None


def package_json_path(package):
    relative = os.path.join(*str(package).split("/")) + ".json"
    direct = canonical_path(os.path.join(FMODEL_ROOT, relative))
    exported = canonical_path(os.path.join(FMODEL_ROOT, "Exports", relative))
    return direct if os.path.isfile(direct) else exported


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


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    return str(data.asset_class_path.asset_name)


def corrected_mesh_index():
    result = {}
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        CORRECTED_ROOT, recursive=True, include_folder=False
    ):
        if asset_class_name(asset_path) != "StaticMesh":
            continue
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not mesh:
            continue
        name = mesh.get_name()
        if name.startswith("SM_"):
            name = name[3:]
        result[name] = mesh
    return result


def parse_mesh_materials(mesh_package):
    path = source_usd_path(mesh_package)
    slots = {}
    references = {}
    pending_index = None
    pending_material = None
    with open(path, "r", encoding="utf-8-sig", errors="replace") as source:
        for line in source:
            match = INDEX_RE.search(line)
            if match:
                pending_index = int(match.group(1))
                continue
            match = BINDING_RE.search(line)
            if match and pending_index is not None:
                slots.setdefault(pending_index, match.group(1))
                pending_index = None
                continue
            match = MATERIAL_DEF_RE.search(line)
            if match:
                pending_material = match.group(1)
                continue
            match = REFERENCE_RE.search(line)
            if match and pending_material:
                reference = match.group(1).replace("/", os.sep)
                references[pending_material] = os.path.normpath(
                    os.path.join(os.path.dirname(path), reference)
                )
                pending_material = None
    return {"slots": slots, "references": references, "path": path}


def referenced_texture_basename(value):
    text = str(value).replace("\\", "/")
    leaf = text.rsplit("/", 1)[-1]
    return leaf.split(".", 1)[0]


def source_material_info(name, reference_usd=None, package=None):
    if package:
        json_path = package_json_path(package)
    else:
        json_path = canonical_path(os.path.splitext(reference_usd or "")[0] + ".json")
    result = {
        "name": name or package_basename(package or ""),
        "package": package,
        "json_path": json_path,
        "json_exists": bool(json_path and os.path.isfile(json_path)),
        "textures": [],
        "two_sided": None,
        "override_two_sided": None,
        "blend_mode": None,
        "opacity_mask_clip_value": None,
    }
    if not result["json_exists"]:
        return result

    payload = load_json(json_path)
    if isinstance(payload, list):
        record = next(
            (
                item
                for item in payload
                if isinstance(item, dict)
                and item.get("Type") in {"Material", "MaterialInstanceConstant"}
            ),
            {},
        )
        raw_properties = record.get("Properties", {})
        texture_values = raw_properties.get("TextureParameterValues", [])
        result["textures"] = sorted(
            {
                referenced_texture_basename(
                    item.get("ParameterValue", {}).get("ObjectPath", "")
                )
                for item in texture_values
                if isinstance(item, dict) and item.get("ParameterValue")
            }
        )
        parameters = {}
        properties = raw_properties
    else:
        result["textures"] = sorted(
            {
                referenced_texture_basename(value)
                for value in payload.get("Textures", {}).values()
                if value
            }
        )
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
    return result


def actual_material_textures(material):
    result = []
    if not material:
        return result
    library = unreal.MaterialEditingLibrary
    try:
        names = list(library.get_texture_parameter_names(material))
    except Exception:
        names = []
    for name in names:
        try:
            texture = library.get_material_instance_texture_parameter_value(material, name)
        except Exception:
            texture = None
        if texture:
            result.append(texture.get_name())
    return sorted(set(result))


def texture_name_matches(expected, actual):
    candidates = {actual}
    if actual.startswith("T_"):
        candidates.add(actual[2:])
    for candidate in candidates:
        if candidate == expected:
            return True
        if candidate.startswith(expected + "_") and candidate[len(expected) + 1 :].isdigit():
            return True
    return False


def common_prefix_length(left, right):
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def association_score(source_info, actual_record):
    expected = source_info.get("textures", [])
    actual = actual_record.get("textures", [])
    matched = [
        expected_name
        for expected_name in expected
        if any(texture_name_matches(expected_name, actual_name) for actual_name in actual)
    ]
    actual_name = actual_record.get("name") or ""
    if actual_name.startswith("MI_"):
        actual_name = actual_name[3:]
    name_prefix = common_prefix_length(source_info.get("name") or "", actual_name)
    score = len(matched) * 10000 + name_prefix
    if actual_name == source_info.get("name"):
        score += 1000
    return score, matched


def best_slot_assignment(source_records, actual_records):
    if not source_records:
        return [], 0
    if len(actual_records) < len(source_records):
        raise RuntimeError(
            "UE mesh has fewer material slots than FModel source: {} < {}".format(
                len(actual_records), len(source_records)
            )
        )

    score_table = {}
    for source_index, source_record in enumerate(source_records):
        for actual_index, actual_record in enumerate(actual_records):
            score_table[(source_index, actual_index)] = association_score(
                source_record["source"], actual_record
            )

    best_permutation = None
    best_score = None
    tie_count = 0
    for permutation in itertools.permutations(
        range(len(actual_records)), len(source_records)
    ):
        score = sum(
            score_table[(source_index, actual_index)][0]
            for source_index, actual_index in enumerate(permutation)
        )
        if best_score is None or score > best_score:
            best_score = score
            best_permutation = permutation
            tie_count = 1
        elif score == best_score:
            tie_count += 1

    assignments = []
    for source_index, actual_index in enumerate(best_permutation or []):
        score, matched = score_table[(source_index, actual_index)]
        assignments.append(
            {
                "source_slot": source_records[source_index]["source_slot"],
                "ue_slot": actual_records[actual_index]["ue_slot"],
                "source": source_records[source_index]["source"],
                "actual_material": actual_records[actual_index]["material"],
                "actual_material_path": actual_records[actual_index]["path"],
                "actual_textures": actual_records[actual_index]["textures"],
                "score": score,
                "matched_textures": matched,
            }
        )
    return assignments, tie_count


def blend_mode_value(value):
    numeric = {
        0: unreal.BlendMode.BLEND_OPAQUE,
        1: unreal.BlendMode.BLEND_MASKED,
        2: unreal.BlendMode.BLEND_TRANSLUCENT,
        3: unreal.BlendMode.BLEND_ADDITIVE,
        4: unreal.BlendMode.BLEND_MODULATE,
        5: unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
        6: unreal.BlendMode.BLEND_ALPHA_HOLDOUT,
    }
    names = {
        "BLEND_Opaque": unreal.BlendMode.BLEND_OPAQUE,
        "BLEND_Masked": unreal.BlendMode.BLEND_MASKED,
        "BLEND_Translucent": unreal.BlendMode.BLEND_TRANSLUCENT,
        "BLEND_Additive": unreal.BlendMode.BLEND_ADDITIVE,
        "BLEND_Modulate": unreal.BlendMode.BLEND_MODULATE,
        "BLEND_AlphaComposite": unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
        "BLEND_AlphaHoldout": unreal.BlendMode.BLEND_ALPHA_HOLDOUT,
    }
    if isinstance(value, int):
        return numeric.get(value)
    return names.get(str(value))


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def apply_material_requirements(material, infos):
    two_sided_values = [
        info["two_sided"] for info in infos if info.get("two_sided") is not None
    ]
    blend_values = [
        blend_mode_value(info.get("blend_mode"))
        for info in infos
        if blend_mode_value(info.get("blend_mode")) is not None
    ]
    clip_values = [
        float(info["opacity_mask_clip_value"])
        for info in infos
        if isinstance(info.get("opacity_mask_clip_value"), (int, float))
    ]
    result = {
        "material": material.get_path_name(),
        "source_jsons": sorted(
            {info.get("json_path") for info in infos if info.get("json_path")}
        ),
        "two_sided": any(two_sided_values) if two_sided_values else None,
        "blend_mode": str(collections.Counter(blend_values).most_common(1)[0][0])
        if blend_values
        else None,
        "opacity_mask_clip_value": collections.Counter(clip_values).most_common(1)[0][0]
        if clip_values
        else None,
        "conflicting_two_sided": len(set(two_sided_values)) > 1,
        "conflicting_blend_modes": len(set(blend_values)) > 1,
        "changed": False,
        "errors": [],
    }
    if not APPLY_CHANGES:
        return result

    try:
        material.modify()
        overrides = material.get_editor_property("base_property_overrides")
        if two_sided_values:
            set_struct_property(overrides, "override_two_sided", True)
            set_struct_property(overrides, "two_sided", any(two_sided_values))
        if blend_values:
            set_struct_property(overrides, "override_blend_mode", True)
            set_struct_property(
                overrides,
                "blend_mode",
                collections.Counter(blend_values).most_common(1)[0][0],
            )
        if clip_values:
            set_struct_property(overrides, "override_opacity_mask_clip_value", True)
            set_struct_property(
                overrides,
                "opacity_mask_clip_value",
                collections.Counter(clip_values).most_common(1)[0][0],
            )
        material.set_editor_property("base_property_overrides", overrides)
        if UPDATE_MATERIAL_INSTANCES:
            try:
                unreal.MaterialEditingLibrary.update_material_instance(material)
            except Exception:
                pass
        result["changed"] = True
    except Exception as exception:
        result["errors"].append(str(exception))
    return result


def main():
    payload = load_json(PLACEMENT_PATH)
    placements = accepted_placements(payload)
    mesh_packages = sorted({str(item["static_mesh_package"]) for item in placements})
    mesh_index = corrected_mesh_index()
    if (
        len(mesh_packages) != EXPECTED_MESH_COUNT
        or len(placements) != EXPECTED_PLACEMENT_COUNT
    ):
        raise RuntimeError("Unexpected HeinMach manifest inventory")

    mesh_mappings = {}
    source_to_actual_paths = collections.defaultdict(list)
    material_requirements = collections.defaultdict(list)
    material_objects = {}
    mapping_records = []
    zero_texture_match_count = 0
    assignment_count = 0

    for item_index, mesh_package in enumerate(mesh_packages, start=1):
        mesh_name = package_basename(mesh_package)
        mesh = mesh_index.get(mesh_name)
        if not mesh:
            raise RuntimeError("Corrected static mesh is missing: " + mesh_package)
        parsed = parse_mesh_materials(mesh_package)
        source_records = []
        for source_slot, source_name in sorted(parsed["slots"].items()):
            source_records.append(
                {
                    "source_slot": source_slot,
                    "source": source_material_info(
                        source_name,
                        reference_usd=parsed["references"].get(source_name),
                    ),
                }
            )

        actual_records = []
        for ue_slot, static_material in enumerate(
            list(mesh.get_editor_property("static_materials"))
        ):
            material = static_material.get_editor_property("material_interface")
            actual_records.append(
                {
                    "ue_slot": ue_slot,
                    "material": material,
                    "path": material.get_path_name() if material else None,
                    "name": material.get_name() if material else None,
                    "textures": actual_material_textures(material),
                }
            )

        assignments, tie_count = best_slot_assignment(source_records, actual_records)
        source_slot_to_ue_slot = {}
        for assignment in assignments:
            assignment_count += 1
            if assignment["source"].get("textures") and not assignment["matched_textures"]:
                zero_texture_match_count += 1
            source_slot_to_ue_slot[assignment["source_slot"]] = assignment["ue_slot"]
            actual_path = assignment["actual_material_path"]
            source_json = assignment["source"].get("json_path")
            if actual_path:
                material_objects[actual_path] = assignment["actual_material"]
                material_requirements[actual_path].append(assignment["source"])
                if source_json:
                    source_to_actual_paths[source_json].append(actual_path)

        mesh_mappings[mesh_package] = source_slot_to_ue_slot
        mapping_records.append(
            {
                "mesh_package": mesh_package,
                "mesh": mesh.get_path_name(),
                "source_slot_count": len(source_records),
                "ue_slot_count": len(actual_records),
                "optimal_assignment_tie_count": tie_count,
                "assignments": [
                    {
                        key: value
                        for key, value in assignment.items()
                        if key != "actual_material"
                    }
                    for assignment in assignments
                ],
            }
        )
        if item_index % 30 == 0:
            log("Mapped {}/{} mesh material layouts".format(item_index, len(mesh_packages)))

    material_results = []
    for material_path, infos in sorted(material_requirements.items()):
        material_results.append(
            apply_material_requirements(material_objects[material_path], infos)
        )

    if APPLY_CHANGES:
        unreal.EditorAssetLibrary.save_directory(
            CORRECTED_ROOT, only_if_is_dirty=False, recursive=True
        )

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }

    override_slot_count = 0
    override_applied_count = 0
    unresolved_overrides = collections.Counter()
    missing_actors = []
    for placement in placements:
        actor = actors_by_label.get(managed_label(placement))
        if not actor:
            missing_actors.append(managed_label(placement))
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            continue
        if APPLY_CHANGES:
            try:
                component.set_editor_property("override_materials", [])
            except Exception:
                component.empty_override_materials()

        slot_mapping = mesh_mappings[str(placement["static_mesh_package"])]
        for source_slot, override_package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if not override_package:
                continue
            override_slot_count += 1
            json_path = package_json_path(override_package)
            candidates = source_to_actual_paths.get(json_path, [])
            ue_slot = slot_mapping.get(source_slot)
            if not candidates or ue_slot is None:
                unresolved_overrides[override_package] += 1
                continue
            material_path = collections.Counter(candidates).most_common(1)[0][0]
            material = material_objects.get(material_path)
            if not material:
                unresolved_overrides[override_package] += 1
                continue
            if APPLY_CHANGES:
                component.set_material(ue_slot, material)
            override_applied_count += 1

    if APPLY_CHANGES:
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save repaired HeinMach map")

    report = {
        "status": "repaired" if APPLY_CHANGES else "dry_run",
        "apply_changes": APPLY_CHANGES,
        "map_path": MAP_PATH,
        "corrected_asset_root": CORRECTED_ROOT,
        "placement_count": len(placements),
        "mesh_mapping_count": len(mesh_mappings),
        "material_assignment_count": assignment_count,
        "zero_texture_match_assignment_count": zero_texture_match_count,
        "unique_material_requirement_count": len(material_requirements),
        "two_sided_material_target_count": sum(
            result.get("two_sided") is True for result in material_results
        ),
        "masked_material_target_count": sum(
            "BLEND_MASKED" in str(result.get("blend_mode"))
            for result in material_results
        ),
        "material_change_error_count": sum(
            bool(result.get("errors")) for result in material_results
        ),
        "material_conflict_count": sum(
            result.get("conflicting_two_sided") or result.get("conflicting_blend_modes")
            for result in material_results
        ),
        "override_slot_count": override_slot_count,
        "override_applied_count": override_applied_count,
        "unresolved_override_slot_count": sum(unresolved_overrides.values()),
        "unresolved_override_materials": [
            {"package": package, "slot_count": count}
            for package, count in sorted(unresolved_overrides.items())
        ],
        "missing_actor_count": len(missing_actors),
        "material_results": material_results,
        "mesh_mappings": mapping_records,
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} materials={} two_sided={} masked={} "
        "zero_texture_matches={} overrides={}/{} unresolved={} report={}".format(
            report["status"],
            report["mesh_mapping_count"],
            report["unique_material_requirement_count"],
            report["two_sided_material_target_count"],
            report["masked_material_target_count"],
            report["zero_texture_match_assignment_count"],
            report["override_applied_count"],
            report["override_slot_count"],
            report["unresolved_override_slot_count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "apply_changes": APPLY_CHANGES,
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        unreal.log_error("KHAZAN_HEINMACH_MATERIAL_REPAIR: " + str(exception))
        unreal.log_error(failure["traceback"])
        raise
