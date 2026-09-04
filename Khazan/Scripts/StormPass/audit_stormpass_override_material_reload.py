"""Reload StormPass and verify every reconstructed root material binding."""

from __future__ import annotations

import collections
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
DEV_MAP_PATH = "/Game/Maps/DevMap"
PLACEMENT_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_ResolvedRootPlacements.json",
)
RESTORATION_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_OverrideMaterial_Restoration.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_OverrideMaterial_ReloadAudit.json",
)
OVERRIDE_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials"
)
TEXTURE_ROOT = OVERRIDE_ROOT + "/Textures"
MATERIAL_ROOT = OVERRIDE_ROOT + "/ActorOverrides/Materials"
ENGINE_BASIC_SHAPE = "Engine/Content/BasicShapes/BasicShapeMaterial"
ENGINE_BASIC_SHAPE_PATH = (
    "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"
)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def managed_label(placement):
    return (
        "SP_Prop_{}_{}_{}".format(
            placement.get("source_level", "Unknown"),
            placement.get("source_object_index", 0),
            placement.get("actor_name", "Actor"),
        )
    )[:220]


def listed_assets(root, class_names):
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    result = []
    for path in unreal.EditorAssetLibrary.list_assets(
        root, recursive=True, include_folder=False
    ):
        data = unreal.EditorAssetLibrary.find_asset_data(path)
        if data and data.is_valid() and str(data.asset_class_path.asset_name) in class_names:
            result.append(path)
    return sorted(result)


def main():
    placements = load_json(PLACEMENT_PATH).get("placements", [])
    restoration = load_json(RESTORATION_PATH)
    if restoration.get("status") != "restored":
        raise RuntimeError("StormPass override restoration report is incomplete")
    if len(placements) != 13050:
        raise RuntimeError("Unexpected StormPass placement count: {}".format(len(placements)))

    slot_maps = {}
    expected_meshes = {}
    source_material_paths = collections.defaultdict(list)
    for mesh_record in restoration.get("mesh_mappings", []):
        mesh_package = mesh_record["mesh_package"]
        expected_meshes[mesh_package] = mesh_record["mesh_path"]
        slot_maps[mesh_package] = {
            int(item["source_slot"]): int(item["ue_slot"])
            for item in mesh_record.get("assignments", [])
        }
        for item in mesh_record.get("assignments", []):
            package = item.get("source_package")
            actual_path = item.get("actual_material_path")
            if package and actual_path:
                source_material_paths[package].append(actual_path)

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

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(DEV_MAP_PATH):
        raise RuntimeError("Failed to load neutral map before reload audit")
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to reload StormPass environment map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in all_actors
        if actor.get_actor_label().startswith("SP_Prop_")
    }
    expected_labels = {managed_label(placement) for placement in placements}

    missing_actors = []
    missing_components = []
    mesh_mismatches = []
    material_mismatches = []
    unresolved_expected_materials = collections.Counter()
    total_override_references = 0
    render_slot_references = 0
    matched_references = 0
    non_render_references = 0

    for placement in placements:
        label = managed_label(placement)
        actor = actors_by_label.get(label)
        if not actor:
            missing_actors.append(label)
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            missing_components.append(label)
            continue
        mesh_package = placement["static_mesh_package"]
        mesh = component.get_editor_property("static_mesh")
        actual_mesh_path = mesh.get_path_name() if mesh else None
        expected_mesh_path = expected_meshes.get(mesh_package)
        if actual_mesh_path != expected_mesh_path:
            mesh_mismatches.append(
                {
                    "label": label,
                    "expected": expected_mesh_path,
                    "actual": actual_mesh_path,
                }
            )
        slot_map = slot_maps.get(mesh_package, {})
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if not package:
                continue
            total_override_references += 1
            ue_slot = slot_map.get(source_slot)
            if ue_slot is None:
                non_render_references += 1
                continue
            render_slot_references += 1
            expected_material_path = rebuilt_materials.get(package)
            if not expected_material_path:
                expected_material_path = resolved_existing.get(package)
            if not expected_material_path:
                unresolved_expected_materials[package] += 1
                continue
            actual_material = component.get_material(ue_slot)
            actual_material_path = (
                actual_material.get_path_name() if actual_material else None
            )
            if actual_material_path == expected_material_path:
                matched_references += 1
            else:
                material_mismatches.append(
                    {
                        "label": label,
                        "source_slot": source_slot,
                        "ue_slot": ue_slot,
                        "package": package,
                        "expected": expected_material_path,
                        "actual": actual_material_path,
                    }
                )

    fog_actors = []
    for actor in all_actors:
        label = actor.get_actor_label()
        class_name = actor.get_class().get_name()
        if label.startswith("SP_Fog_") or "Fog" in class_name:
            fog_actors.append({"label": label, "class": class_name})

    texture_assets = listed_assets(TEXTURE_ROOT, {"Texture2D", "TextureCube"})
    material_assets = listed_assets(MATERIAL_ROOT, {"MaterialInstanceConstant"})
    unexpected_managed = sorted(set(actors_by_label) - expected_labels)
    report = {
        "status": "verified",
        "map_path": MAP_PATH,
        "reload_cycle": [DEV_MAP_PATH, MAP_PATH],
        "placement_count": len(placements),
        "managed_actor_count": len(actors_by_label),
        "missing_actor_count": len(missing_actors),
        "missing_component_count": len(missing_components),
        "unexpected_managed_actor_count": len(unexpected_managed),
        "mesh_mismatch_count": len(mesh_mismatches),
        "material_binding": {
            "total_source_override_reference_count": total_override_references,
            "render_slot_reference_count": render_slot_references,
            "matched_reference_count": matched_references,
            "non_render_lod_or_unused_reference_count": non_render_references,
            "mismatch_count": len(material_mismatches),
            "unresolved_expected_reference_count": sum(
                unresolved_expected_materials.values()
            ),
        },
        "asset_inventory": {
            "texture_count": len(texture_assets),
            "material_instance_count": len(material_assets),
        },
        "deferred_fog_actor_count": len(fog_actors),
        "missing_actors": missing_actors,
        "missing_components": missing_components,
        "unexpected_managed_actors": unexpected_managed,
        "mesh_mismatches": mesh_mismatches,
        "material_mismatches": material_mismatches,
        "unresolved_expected_materials": [
            {"package": package, "reference_count": count}
            for package, count in sorted(unresolved_expected_materials.items())
        ],
        "fog_actors": fog_actors,
    }
    failures = [
        len(actors_by_label) != 13050,
        bool(missing_actors),
        bool(missing_components),
        bool(unexpected_managed),
        bool(mesh_mismatches),
        total_override_references != 10489,
        render_slot_references != 7717,
        matched_references != 7717,
        non_render_references != 2772,
        bool(material_mismatches),
        bool(unresolved_expected_materials),
        len(texture_assets) != 87,
        len(material_assets) != 93,
        bool(fog_actors),
    ]
    if any(failures):
        report["status"] = "failed"
    write_json(REPORT_PATH, report)
    if report["status"] != "verified":
        raise RuntimeError("StormPass material reload audit failed: " + REPORT_PATH)
    unreal.log(
        "KHAZAN_STORMPASS_OVERRIDE_RELOAD_AUDIT: RESULT actors={} meshes={} "
        "bindings={}/{} textures={} materials={} fog={} report={}".format(
            len(actors_by_label),
            len(mesh_mismatches),
            matched_references,
            render_slot_references,
            len(texture_assets),
            len(material_assets),
            len(fog_actors),
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    main()
