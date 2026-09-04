"""Restore all visible StormPass child meshes with exact hierarchy/material data.

Fog and foliage HISM components remain outside this pass.  Child transforms are
composed through the complete FModel AttachParent chain before being flattened
into managed StaticMeshActors in the reconstructed environment map.
"""

from __future__ import annotations

import collections
import importlib.util
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SHARED_PATH = os.path.join(
    PROJECT_ROOT,
    "Scripts",
    "HeinMach",
    "restore_heinmach_inherited_child_render_meshes.py",
)
MATERIAL_HELPER_PATH = os.path.join(
    PROJECT_ROOT, "Scripts", "HeinMach", "repair_heinmach_materials.py"
)
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreChildRenderRestore"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed"
SOURCE_ROOT = RECONSTRUCTED_ROOT + "/SourceAssets"
DESTINATION_ROOT = RECONSTRUCTED_ROOT + "/ChildRenderAssets"
OVERRIDE_MATERIAL_ROOT = (
    RECONSTRUCTED_ROOT + "/OverrideMaterials/ActorOverrides/Materials"
)
CHILD_OVERRIDE_MATERIAL_ROOT = (
    RECONSTRUCTED_ROOT + "/OverrideMaterials/ChildOverrides/Materials"
)
AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildTemplateCoverage_Audit.json",
)
ROOT_MATERIAL_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_OverrideMaterial_Restoration.json",
)
CHILD_MATERIAL_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildOverrideMaterial_Restoration.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildRender_Restoration.json",
)
STAGE_NAME = "StormPass_ChildRenderLibrary"
MANAGED_LABEL_PREFIX = "SP_ChildProp_"
MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/ChildProps"
EXPECTED_COMPONENT_COUNT = 551
EXPECTED_PACKAGE_COUNT = 44
EXPECTED_OVERRIDE_REFERENCE_COUNT = 123
EXPECTED_FOG_SIGNATURE = {
    "count": 0,
    "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}
MATERIAL_SEARCH_ROOTS = (
    CHILD_OVERRIDE_MATERIAL_ROOT,
    OVERRIDE_MATERIAL_ROOT,
    DESTINATION_ROOT,
    SOURCE_ROOT,
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load_module("khazan_stormpass_child_restore_helpers", SHARED_PATH)
material_helper = load_module(
    "khazan_stormpass_child_material_helpers", MATERIAL_HELPER_PATH
)


def log(message):
    unreal.log("KHAZAN_STORMPASS_CHILD_RESTORE: " + str(message))


def configure_shared():
    shared.MAP_PATH = MAP_PATH
    shared.BACKUP_MAP_PATH = BACKUP_MAP_PATH
    shared.RECONSTRUCTED_ROOT = RECONSTRUCTED_ROOT
    shared.DESTINATION_ROOT = DESTINATION_ROOT
    shared.SEARCH_ROOTS = (SOURCE_ROOT, DESTINATION_ROOT)
    shared.STAGE_NAME = STAGE_NAME
    shared.GENERATED_STAGE_PATH = os.path.join(
        unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
    )
    shared.AUDIT_PATH = AUDIT_PATH
    shared.REPORT_PATH = REPORT_PATH
    shared.MANAGED_LABEL_PREFIX = MANAGED_LABEL_PREFIX
    shared.MANAGED_FOLDER_ROOT = MANAGED_FOLDER_ROOT
    shared.FOG_LABEL_PREFIX = "SP_Fog_"
    shared.EXPECTED_COMPONENT_COUNT = EXPECTED_COMPONENT_COUNT
    shared.EXPECTED_PACKAGE_COUNT = EXPECTED_PACKAGE_COUNT
    shared.EXPECTED_FOG_COUNT = 0
    shared.EXPECTED_FOG_SHA256 = EXPECTED_FOG_SIGNATURE["sha256"]
    shared.log = log
    material_helper.FMODEL_ROOT = shared.FMODEL_ROOT
    material_helper.CORRECTED_ROOT = SOURCE_ROOT


def accepted_records(payload):
    records = list(payload.get("resolved_child_mesh_components", []))
    packages = sorted(
        {
            str(record.get("static_mesh_package", ""))
            for record in records
            if record.get("static_mesh_package")
        }
    )
    if len(records) != EXPECTED_COMPONENT_COUNT or len(packages) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError(
            "Unexpected StormPass child inventory: records={} packages={}".format(
                len(records), len(packages)
            )
        )
    if payload.get("summary", {}).get("unresolved_component_count") != 0:
        raise RuntimeError("StormPass child source audit contains unresolved records")
    if payload.get("summary", {}).get("missing_usd_static_mesh_count") != 0:
        raise RuntimeError("StormPass child source audit has missing USD meshes")
    if any(record.get("visible") is False for record in records):
        raise RuntimeError("Hidden component entered StormPass child inventory")
    if any(record.get("has_absolute_attachment_policy") for record in records):
        raise RuntimeError("Absolute child transforms require a separate composition policy")
    if any(record.get("has_socket_attachment") for record in records):
        raise RuntimeError("Socket-attached child transforms require socket evaluation")
    labels = [shared.managed_label(record) for record in records]
    if len(set(labels)) != len(labels):
        raise RuntimeError("StormPass child inventory creates duplicate labels")
    missing = [
        package for package in packages if not os.path.isfile(shared.source_usd_path(package))
    ]
    if missing:
        raise RuntimeError("Missing StormPass child USD source: " + missing[0])
    return records, packages, set(labels)


def expected_world_transform(record):
    result = shared.unreal_transform(record.get("local_transform", {}))
    for parent in record.get("attachment_parent_chain", []):
        result = unreal.MathLibrary.compose_transforms(
            result, shared.unreal_transform(parent.get("local_transform", {}))
        )
    return unreal.MathLibrary.compose_transforms(
        result, shared.unreal_transform(record.get("actor_world_transform", {}))
    )


def asset_class_name(path):
    data = unreal.EditorAssetLibrary.find_asset_data(path)
    if not data or not data.is_valid():
        return "Invalid"
    return str(data.asset_class_path.asset_name)


def material_name_index():
    result = {}
    for root in MATERIAL_SEARCH_ROOTS:
        if not unreal.EditorAssetLibrary.does_directory_exist(root):
            continue
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        ):
            if asset_class_name(path) not in {"Material", "MaterialInstanceConstant"}:
                continue
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if not asset:
                continue
            for name in shared.normalized_asset_names(asset):
                result.setdefault(name, asset)
    return result


def actual_material_records(mesh):
    result = []
    for ue_slot, static_material in enumerate(
        mesh.get_editor_property("static_materials")
    ):
        material = static_material.get_editor_property("material_interface")
        result.append(
            {
                "ue_slot": ue_slot,
                "material": material,
                "path": material.get_path_name() if material else None,
                "name": material.get_name() if material else None,
                "textures": material_helper.actual_material_textures(material),
            }
        )
    return result


def build_slot_mapping(mesh_package, mesh):
    parsed = material_helper.parse_mesh_materials(mesh_package)
    source_records = []
    for source_slot, source_name in sorted(parsed["slots"].items()):
        source_records.append(
            {
                "source_slot": source_slot,
                "source": material_helper.source_material_info(
                    source_name, reference_usd=parsed["references"].get(source_name)
                ),
            }
        )
    assignments, tie_count = material_helper.best_slot_assignment(
        source_records, actual_material_records(mesh)
    )
    mapping = {
        int(assignment["source_slot"]): int(assignment["ue_slot"])
        for assignment in assignments
    }
    if len(mapping) != len(source_records):
        raise RuntimeError("Incomplete child slot mapping: " + mesh_package)
    return mapping, {
        "mesh_package": mesh_package,
        "mesh_asset": mesh.get_path_name(),
        "source_lod0_binding_count": len(source_records),
        "ue_material_slot_count": len(mesh.get_editor_property("static_materials")),
        "assignment_tie_count": tie_count,
        "assignments": [
            {
                "source_slot": int(item["source_slot"]),
                "ue_slot": int(item["ue_slot"]),
                "source_material": item["source"].get("name"),
                "actual_default_material": item.get("actual_material_path"),
                "matched_textures": list(item.get("matched_textures", [])),
                "score": int(item.get("score", 0)),
            }
            for item in assignments
        ],
    }


def required_materials(records):
    required = sorted(
        {
            str(package)
            for record in records
            for package in record.get("override_material_packages", [])
            if package
        }
    )
    rebuilt_paths = {}
    for report_path in (ROOT_MATERIAL_REPORT_PATH, CHILD_MATERIAL_REPORT_PATH):
        rebuilt_report = shared.load_json(report_path)
        rebuilt_paths.update(
            {
                item["package"]: item["material_path"]
                for item in rebuilt_report.get("material_results", [])
            }
        )
    names = material_name_index()
    result = {}
    resolution = []
    for package in required:
        material = None
        reason = None
        path = rebuilt_paths.get(package)
        if path:
            material = unreal.EditorAssetLibrary.load_asset(path)
            reason = "verified_override_rebuild"
        if not material:
            material = names.get(shared.package_basename(package))
            reason = "imported_material_name"
        if not material:
            raise RuntimeError("Missing StormPass child override material: " + package)
        result[package] = material
        resolution.append(
            {
                "package": package,
                "material_path": material.get_path_name(),
                "reason": reason,
            }
        )
    return result, resolution


def apply_material_overrides(records, actors, mesh_index):
    packages = sorted({record["static_mesh_package"] for record in records})
    slot_maps = {}
    mapping_records = []
    for index, package in enumerate(packages, start=1):
        mesh = mesh_index[shared.package_basename(package)]
        mapping, mapping_record = build_slot_mapping(package, mesh)
        slot_maps[package] = mapping
        mapping_records.append(mapping_record)
        if index % 20 == 0:
            log("Mapped {}/{} child mesh material layouts".format(index, len(packages)))

    materials, material_resolution = required_materials(records)
    total_references = 0
    render_references = 0
    non_render_references = 0
    applied_references = 0
    verified_references = 0
    for record in records:
        actor = actors[shared.managed_label(record)]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            component.empty_override_materials()
        mapping = slot_maps[record["static_mesh_package"]]
        for source_slot, package in enumerate(
            record.get("override_material_packages", [])
        ):
            if not package:
                continue
            total_references += 1
            ue_slot = mapping.get(source_slot)
            if ue_slot is None:
                non_render_references += 1
                continue
            render_references += 1
            material = materials.get(package)
            if not material:
                raise RuntimeError("Unresolved child material package: " + package)
            component.set_material(ue_slot, material)
            applied_references += 1
            actual = component.get_material(ue_slot)
            if actual and actual.get_path_name() == material.get_path_name():
                verified_references += 1
    if total_references != EXPECTED_OVERRIDE_REFERENCE_COUNT:
        raise RuntimeError(
            "Unexpected child override inventory: {}".format(total_references)
        )
    if applied_references != render_references or verified_references != render_references:
        raise RuntimeError(
            "Child material verification failed: applied={} verified={} render={}".format(
                applied_references, verified_references, render_references
            )
        )
    return {
        "total_source_override_reference_count": total_references,
        "render_slot_reference_count": render_references,
        "applied_reference_count": applied_references,
        "verified_reference_count": verified_references,
        "non_render_lod_or_unused_reference_count": non_render_references,
        "material_resolution": material_resolution,
        "mesh_slot_mappings": mapping_records,
    }


def main():
    configure_shared()
    shared.expected_world_transform = expected_world_transform
    payload = shared.load_json(AUDIT_PATH)
    if payload.get("status") != "audited":
        raise RuntimeError("StormPass child coverage report is not audited")
    records, packages, expected_labels = accepted_records(payload)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fog_before = shared.fog_signature(actor_subsystem)
    if fog_before != EXPECTED_FOG_SIGNATURE:
        raise RuntimeError("Fog boundary differs before StormPass child restoration")

    backup_created = shared.backup_map_once()
    mesh_index, imported_paths, imported_source_files = shared.ensure_meshes(packages)
    actor_subsystem, actors, placement = shared.place_records(
        records, mesh_index, expected_labels
    )
    placement_failures = shared.validate_placements(records, actors)
    if placement_failures:
        raise RuntimeError(
            "StormPass child placement validation failed: "
            + str(placement_failures[0])
        )
    material_summary = shared.mesh_material_summary(packages, mesh_index)
    null_slots = sum(item["null_material_slot_count"] for item in material_summary)
    if null_slots:
        raise RuntimeError("StormPass child mesh import contains null material slots")
    material_result = apply_material_overrides(records, actors, mesh_index)

    fog_after = shared.fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError("Fog boundary changed during StormPass child restoration")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass child restoration")
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_audit_path": AUDIT_PATH,
        "source_component_count": len(records),
        "required_static_mesh_count": len(packages),
        "imported_source_files": imported_source_files,
        "imported_object_path_count": len(imported_paths),
        "placement_result": placement,
        "placement_validation_failure_count": len(placement_failures),
        "mesh_material_summary": material_summary,
        "material_restoration": material_result,
        "fog_boundary": {
            "status": "unchanged",
            "before": fog_before,
            "after": fog_after,
        },
        "transform_policy": "UE ComposeTransforms(Child, ParentChain..., ActorRoot)",
        "excluded_content": [
            "All StormPass Fog/Mist actors and materials",
            "All foliage HISM components",
            "Cinema, character, enemy, spawn, quest, audio, navigation and gameplay logic",
        ],
    }
    shared.write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} actors={} created={} reused={} overrides={}/{} "
        "lod_only={} fog={} report={}".format(
            report["status"],
            len(packages),
            len(records),
            placement["created_count"],
            placement["reused_count"],
            material_result["applied_reference_count"],
            material_result["render_slot_reference_count"],
            material_result["non_render_lod_or_unused_reference_count"],
            fog_after["count"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        shared.write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_CHILD_RESTORE: " + str(exception))
        raise
