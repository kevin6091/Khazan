"""Import and repair the 19 StormPass Foliage/HISM source meshes."""

from __future__ import annotations

import collections
import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
CHILD_RESTORE_PATH = os.path.join(
    SCRIPT_DIR, "restore_stormpass_child_render_meshes.py"
)
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_FoliageInstances.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Foliage_AssetPreparation.json",
)
FOLIAGE_ASSET_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/FoliageAssets"
)
STAGE_NAME = "StormPass_FoliageLibrary"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
EXPECTED_COMPONENT_COUNT = 218
EXPECTED_INSTANCE_COUNT = 21259
EXPECTED_MESH_COUNT = 19
LOD10_SOURCE_PACKAGE = (
    "BBQ/Content/Art/World/World_Model/Prop/Plant/"
    "WP_COM_Plants_Base_001_10"
)
LOD10_IMPORTED_PATH = (
    FOLIAGE_ASSET_ROOT
    + "/"
    + STAGE_NAME
    + "/StaticMeshes/SM_WP_COM_Plants_Base_001"
)
LOD10_TARGET_PATH = LOD10_IMPORTED_PATH + "_10"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Foliage helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


child = load_module("khazan_stormpass_foliage_child_helpers", CHILD_RESTORE_PATH)


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOLIAGE_ASSETS: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def configure():
    child.configure_shared()
    child.shared.DESTINATION_ROOT = FOLIAGE_ASSET_ROOT
    child.shared.SEARCH_ROOTS = (
        child.SOURCE_ROOT,
        child.DESTINATION_ROOT,
        FOLIAGE_ASSET_ROOT,
    )
    child.shared.STAGE_NAME = STAGE_NAME
    child.shared.GENERATED_STAGE_PATH = GENERATED_STAGE_PATH
    child.shared.log = log
    child.material_helper.FMODEL_ROOT = child.shared.FMODEL_ROOT
    child.material_helper.CORRECTED_ROOT = FOLIAGE_ASSET_ROOT
    child.material_helper.APPLY_CHANGES = True
    child.material_helper.UPDATE_MATERIAL_INSTANCES = False


def source_inventory():
    payload = load_json(METADATA_PATH)
    summary = payload.get("summary", {})
    if (
        payload.get("status") != "passed"
        or int(summary.get("point_instancer_component_count", -1))
        != EXPECTED_COMPONENT_COUNT
        or int(summary.get("instance_count", -1)) != EXPECTED_INSTANCE_COUNT
        or int(summary.get("unique_static_mesh_count", -1)) != EXPECTED_MESH_COUNT
        or int(summary.get("missing_mesh_usd_count", -1)) != 0
    ):
        raise RuntimeError("StormPass Foliage source metadata is incomplete")
    packages = sorted(item["package"] for item in payload.get("mesh_usage", []))
    if len(packages) != EXPECTED_MESH_COUNT:
        raise RuntimeError("StormPass Foliage mesh package inventory changed")
    return payload, packages


def world_snapshot():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    actors = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()
    fog = sorted(
        (actor.get_actor_label(), actor.get_class().get_name())
        for actor in actors
        if actor
        and (
            actor.get_actor_label().startswith("SP_Fog_")
            or "Fog" in actor.get_class().get_name()
        )
    )
    return {
        "world_path": world.get_path_name() if world else None,
        "actor_count": len(actors),
        "fog_actor_count": len(fog),
        "fog_actors": fog,
    }


def repair_lod_suffix_import_name():
    """Restore a source name that the USD importer mistakes for LOD 10.

    The source prim is literally ``WP_COM_Plants_Base_001_10``.  With
    ``interpret_lods`` enabled Unreal imports that one mesh as
    ``SM_WP_COM_Plants_Base_001`` even though the geometry is not a LOD child.
    This destination is dedicated to the StormPass Foliage library and the
    unsuffixed source package is not part of this batch, so the rename is
    deterministic and collision-free.
    """
    target_exists = unreal.EditorAssetLibrary.does_asset_exist(LOD10_TARGET_PATH)
    imported_exists = unreal.EditorAssetLibrary.does_asset_exist(LOD10_IMPORTED_PATH)
    result = {
        "source_package": LOD10_SOURCE_PACKAGE,
        "imported_path": LOD10_IMPORTED_PATH,
        "target_path": LOD10_TARGET_PATH,
        "renamed": False,
    }
    if target_exists:
        result["status"] = "already_correct"
        return result
    if not imported_exists:
        result["status"] = "not_present"
        return result
    if not unreal.EditorAssetLibrary.rename_asset(
        LOD10_IMPORTED_PATH, LOD10_TARGET_PATH
    ):
        raise RuntimeError("Failed to restore the Foliage _10 mesh asset name")
    if not unreal.EditorAssetLibrary.save_asset(
        LOD10_TARGET_PATH, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save the renamed Foliage _10 mesh asset")
    result["renamed"] = True
    result["status"] = "renamed_after_usd_lod_suffix_interpretation"
    return result


def ensure_foliage_meshes(packages):
    """Import missing meshes, correcting Unreal's one `_10` naming quirk."""
    name_repair = repair_lod_suffix_import_name()
    mesh_index = child.shared.static_mesh_index()
    missing = [
        package
        for package in packages
        if child.shared.package_basename(package) not in mesh_index
    ]
    imported_paths = []
    imported_source_files = []
    if missing:
        imported_source_files = child.shared.write_mesh_stage(missing)
        imported_paths = child.shared.import_mesh_library()
        post_import_repair = repair_lod_suffix_import_name()
        if post_import_repair.get("status") != "not_present":
            name_repair = post_import_repair
        mesh_index = child.shared.static_mesh_index()
        missing = [
            package
            for package in packages
            if child.shared.package_basename(package) not in mesh_index
        ]
    if missing:
        raise RuntimeError("StormPass Foliage mesh remains unresolved: " + missing[0])
    return mesh_index, imported_paths, imported_source_files, name_repair


def actual_material_records(mesh):
    records = []
    for ue_slot, static_material in enumerate(
        mesh.get_editor_property("static_materials")
    ):
        material = static_material.get_editor_property("material_interface")
        records.append(
            {
                "ue_slot": ue_slot,
                "material": material,
                "path": material.get_path_name() if material else None,
                "name": material.get_name() if material else None,
                "textures": child.material_helper.actual_material_textures(material),
            }
        )
    return records


def map_and_repair_materials(packages, mesh_index):
    material_objects = {}
    material_requirements = collections.defaultdict(list)
    mappings = {}
    mapping_records = []
    zero_texture_matches = 0
    assignment_count = 0
    for package in packages:
        mesh = mesh_index[child.shared.package_basename(package)]
        parsed = child.material_helper.parse_mesh_materials(package)
        source_records = [
            {
                "source_slot": source_slot,
                "source": child.material_helper.source_material_info(
                    source_name,
                    reference_usd=parsed["references"].get(source_name),
                ),
            }
            for source_slot, source_name in sorted(parsed["slots"].items())
        ]
        actual_records = actual_material_records(mesh)
        assignments, tie_count = child.material_helper.best_slot_assignment(
            source_records, actual_records
        )
        mapping = {
            int(item["source_slot"]): int(item["ue_slot"])
            for item in assignments
        }
        if len(mapping) != len(source_records):
            raise RuntimeError("Incomplete Foliage material slot mapping: " + package)
        mappings[package] = mapping
        for assignment in assignments:
            assignment_count += 1
            source = assignment["source"]
            if source.get("textures") and not assignment.get("matched_textures"):
                zero_texture_matches += 1
            material = assignment.get("actual_material")
            path = assignment.get("actual_material_path")
            if not material or not path:
                raise RuntimeError("Foliage mesh contains a null material slot: " + package)
            material_objects[path] = material
            material_requirements[path].append(source)
        mapping_records.append(
            {
                "mesh_package": package,
                "mesh_asset": mesh.get_path_name(),
                "source_lod0_binding_count": len(source_records),
                "ue_material_slot_count": len(actual_records),
                "assignment_tie_count": tie_count,
                "assignments": [
                    {
                        "source_slot": int(item["source_slot"]),
                        "ue_slot": int(item["ue_slot"]),
                        "source_material": item["source"].get("name"),
                        "source_json": item["source"].get("json_path"),
                        "actual_material_path": item.get("actual_material_path"),
                        "matched_textures": list(item.get("matched_textures", [])),
                        "score": int(item.get("score", 0)),
                    }
                    for item in assignments
                ],
            }
        )

    material_results = []
    for path, requirements in sorted(material_requirements.items()):
        material_results.append(
            child.material_helper.apply_material_requirements(
                material_objects[path], requirements
            )
        )
    for root in child.shared.SEARCH_ROOTS:
        if unreal.EditorAssetLibrary.does_directory_exist(root):
            unreal.EditorAssetLibrary.save_directory(
                root, only_if_is_dirty=False, recursive=True
            )
    return mappings, mapping_records, material_results, {
        "assignment_count": assignment_count,
        "zero_texture_match_count": zero_texture_matches,
        "material_asset_count": len(material_results),
        "material_error_count": sum(
            bool(item.get("errors")) for item in material_results
        ),
    }


def main():
    configure()
    payload, packages = source_inventory()
    before = world_snapshot()
    if before["fog_actor_count"] != 0:
        raise RuntimeError("Fog boundary differs before Foliage asset preparation")

    (
        mesh_index,
        imported_paths,
        imported_source_files,
        name_repair,
    ) = ensure_foliage_meshes(packages)
    missing = [
        package
        for package in packages
        if child.shared.package_basename(package) not in mesh_index
    ]
    if missing:
        raise RuntimeError("StormPass Foliage mesh remains unresolved: " + missing[0])
    mappings, mapping_records, material_results, material_summary = (
        map_and_repair_materials(packages, mesh_index)
    )
    if material_summary["material_error_count"]:
        raise RuntimeError("StormPass Foliage default material repair failed")
    mesh_material_summary = child.shared.mesh_material_summary(packages, mesh_index)
    if sum(item["null_material_slot_count"] for item in mesh_material_summary):
        raise RuntimeError("StormPass Foliage mesh library contains null material slots")

    after = world_snapshot()
    if after != before:
        raise RuntimeError("Editor world changed during Foliage asset-only preparation")
    report = {
        "status": "passed",
        "operation": "asset_only_foliage_mesh_import_and_material_repair",
        "map_modified": False,
        "source_metadata": METADATA_PATH,
        "foliage_asset_root": FOLIAGE_ASSET_ROOT,
        "source_component_count": EXPECTED_COMPONENT_COUNT,
        "source_instance_count": EXPECTED_INSTANCE_COUNT,
        "required_static_mesh_count": len(packages),
        "resolved_static_mesh_count": len(packages) - len(missing),
        "imported_source_files": imported_source_files,
        "imported_source_file_count": len(imported_source_files),
        "imported_object_paths": imported_paths,
        "imported_object_path_count": len(imported_paths),
        "usd_lod_suffix_name_repair": name_repair,
        "mesh_assets": {
            package: mesh_index[child.shared.package_basename(package)].get_path_name()
            for package in packages
        },
        "mesh_slot_mappings": mapping_records,
        "material_repair_summary": material_summary,
        "material_repair_results": material_results,
        "mesh_material_summary": mesh_material_summary,
        "fog_policy": "deferred_until_final_pass",
        "world_before": before,
        "world_after": after,
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT meshes={} imported_sources={} imported_assets={} slots={} "
        "materials={} fog=0 report={}".format(
            report["resolved_static_mesh_count"],
            report["imported_source_file_count"],
            report["imported_object_path_count"],
            material_summary["assignment_count"],
            material_summary["material_asset_count"],
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
        unreal.log_error("KHAZAN_STORMPASS_FOLIAGE_ASSETS: " + str(exception))
        raise
