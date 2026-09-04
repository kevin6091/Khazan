"""Rebuild StormPass Foliage/HISM override materials from FModel metadata.

This is an asset-only pass.  It imports the exact texture sources required by
the five serialized Foliage overrides, selects a live default material from
the corresponding restored mesh as the parameter-compatible template, and
creates dedicated material instances for the later HISM placement pass.
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
    "restore_heinmach_inherited_override_materials.py",
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
SOURCE_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_FoliageOverrideSource_Audit.json",
)
ASSET_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Foliage_AssetPreparation.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_FoliageOverrideMaterial_Restoration.json",
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed"
SOURCE_ROOT = RECONSTRUCTED_ROOT + "/SourceAssets"
FOLIAGE_ASSET_ROOT = RECONSTRUCTED_ROOT + "/FoliageAssets"
OVERRIDE_ROOT = RECONSTRUCTED_ROOT + "/OverrideMaterials"
MATERIAL_ROOT = OVERRIDE_ROOT + "/FoliageOverrides/Materials"
TEXTURE_ROOT = OVERRIDE_ROOT + "/Textures"
EXPECTED_COMPONENT_COUNT = 218
EXPECTED_INSTANCE_COUNT = 21259
EXPECTED_MESH_COUNT = 19
EXPECTED_OVERRIDE_MATERIAL_COUNT = 5
EXPECTED_OVERRIDE_REFERENCE_COUNT = 50
EXPECTED_TEXTURE_COUNT = 19


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Foliage material helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load_module("khazan_stormpass_foliage_override_helpers", SHARED_PATH)


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOLIAGE_OVERRIDE_MATERIALS: " + str(message))


def configure():
    shared.CORRECTED_ROOT = SOURCE_ROOT
    shared.OVERRIDE_ROOT = OVERRIDE_ROOT
    shared.MATERIAL_ROOT = MATERIAL_ROOT
    shared.TEXTURE_ROOT = TEXTURE_ROOT
    shared.UPDATE_MATERIAL_INSTANCES = False
    shared.USE_LEGACY_TEXTURE_FACTORY = True
    shared.repair.CORRECTED_ROOT = SOURCE_ROOT
    shared.repair.FMODEL_ROOT = shared.FMODEL_ROOT
    shared.log = log


def world_snapshot():
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    actors = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()
    fog = [
        actor
        for actor in actors
        if actor
        and (
            actor.get_actor_label().startswith("SP_Fog_")
            or "Fog" in actor.get_class().get_name()
        )
    ]
    return {
        "world_path": world.get_path_name() if world else None,
        "actor_count": len(actors),
        "fog_actor_count": len(fog),
    }


def source_inventory():
    metadata = shared.load_json(METADATA_PATH)
    summary = metadata.get("summary", {})
    if (
        metadata.get("status") != "passed"
        or int(summary.get("point_instancer_component_count", -1))
        != EXPECTED_COMPONENT_COUNT
        or int(summary.get("instance_count", -1)) != EXPECTED_INSTANCE_COUNT
        or int(summary.get("unique_static_mesh_count", -1)) != EXPECTED_MESH_COUNT
        or int(summary.get("override_material_package_count", -1))
        != EXPECTED_OVERRIDE_MATERIAL_COUNT
    ):
        raise RuntimeError("StormPass Foliage metadata inventory changed")

    audit = shared.load_json(SOURCE_AUDIT_PATH)
    if (
        audit.get("status") != "audited"
        or int(audit.get("material_package_count", -1))
        != EXPECTED_OVERRIDE_MATERIAL_COUNT
        or int(audit.get("parsed_material_count", -1))
        != EXPECTED_OVERRIDE_MATERIAL_COUNT
        or int(audit.get("unique_texture_package_count", -1))
        != EXPECTED_TEXTURE_COUNT
        or audit.get("missing_json_count")
        or audit.get("missing_texture_image_count")
        or audit.get("parse_error_count")
    ):
        raise RuntimeError("StormPass Foliage override source audit is incomplete")

    asset_report = shared.load_json(ASSET_REPORT_PATH)
    if (
        asset_report.get("status") != "passed"
        or int(asset_report.get("resolved_static_mesh_count", -1))
        != EXPECTED_MESH_COUNT
        or int(
            asset_report.get("material_repair_summary", {}).get(
                "material_error_count", -1
            )
        )
        != 0
    ):
        raise RuntimeError("StormPass Foliage asset preparation is incomplete")

    packages = sorted(item["package"] for item in audit.get("records", []))
    reference_count = sum(
        1
        for component in metadata.get("components", [])
        for package in component.get("settings", {}).get(
            "override_material_packages", []
        )
        if package
    )
    if reference_count != EXPECTED_OVERRIDE_REFERENCE_COUNT:
        raise RuntimeError(
            "StormPass Foliage override reference inventory changed: {}".format(
                reference_count
            )
        )
    return metadata, audit, asset_report, packages


def append_material_index(index):
    for root in (FOLIAGE_ASSET_ROOT,):
        if not unreal.EditorAssetLibrary.does_directory_exist(root):
            continue
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        ):
            if shared.asset_class_name(path) not in {
                "Material",
                "MaterialInstanceConstant",
            }:
                continue
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if not asset:
                continue
            for name in shared.normalized_material_names(asset):
                index[name].append(path)


def live_template_inventory(metadata, asset_report, records):
    requested = {record["package"] for record in records}
    mesh_assets = {
        package: unreal.EditorAssetLibrary.load_asset(path)
        for package, path in asset_report.get("mesh_assets", {}).items()
    }
    slot_maps = {}
    for item in asset_report.get("mesh_slot_mappings", []):
        slot_maps[item["mesh_package"]] = {
            int(assignment["source_slot"]): int(assignment["ue_slot"])
            for assignment in item.get("assignments", [])
        }

    live_templates = collections.defaultdict(list)
    resolved_references = 0
    non_render_references = 0
    for component in metadata.get("components", []):
        mesh_package = component["static_mesh_package"]
        mesh = mesh_assets.get(mesh_package)
        if not mesh:
            raise RuntimeError("Missing prepared Foliage mesh: " + mesh_package)
        materials = list(mesh.get_editor_property("static_materials"))
        mapping = slot_maps.get(mesh_package, {})
        for source_slot, package in enumerate(
            component.get("settings", {}).get("override_material_packages", [])
        ):
            if not package or package not in requested:
                continue
            ue_slot = mapping.get(source_slot)
            if ue_slot is None or ue_slot >= len(materials):
                non_render_references += 1
                continue
            material = materials[ue_slot].get_editor_property("material_interface")
            if material:
                live_templates[package].append(material.get_path_name())
                resolved_references += 1
    if resolved_references + non_render_references != EXPECTED_OVERRIDE_REFERENCE_COUNT:
        raise RuntimeError("Foliage live template reference resolution changed")
    if non_render_references:
        raise RuntimeError("Foliage override points outside restored LOD0 render slots")
    return live_templates, resolved_references


def main():
    configure()
    before = world_snapshot()
    if before["fog_actor_count"] != 0:
        raise RuntimeError("Fog boundary differs before Foliage material rebuild")

    metadata, source_audit, asset_report, packages = source_inventory()
    records = [shared.raw_material_record(package) for package in packages]
    required_texture_names = {
        item["texture_name"] for record in records for item in record["textures"]
    }
    if len(required_texture_names) != EXPECTED_TEXTURE_COUNT:
        raise RuntimeError("Unexpected Foliage override texture inventory")

    previous_import_count = 0
    if os.path.isfile(REPORT_PATH):
        previous = shared.load_json(REPORT_PATH)
        if previous.get("status") == "restored":
            previous_import_count = int(previous.get("texture_import_task_count", 0))
    texture_index, import_count, configured_textures = shared.import_textures(records)
    live_templates, live_reference_count = live_template_inventory(
        metadata, asset_report, records
    )

    material_index, _ = shared.material_asset_index()
    append_material_index(material_index)
    rebuilt_by_name = {}
    materials = []
    parameter_totals = collections.Counter()
    for record in records:
        template_path, template_reason = shared.choose_template(
            record,
            live_templates,
            collections.defaultdict(list),
            collections.defaultdict(list),
            material_index,
            rebuilt_by_name,
        )
        material, created = shared.create_or_load_material(record, template_path)
        parameter_result = shared.configure_material(material, record, texture_index)
        parameter_totals.update(parameter_result)
        rebuilt_by_name[record["name"]] = material
        materials.append(
            {
                "package": record["package"],
                "material_path": material.get_path_name(),
                "created": created,
                "template_path": template_path,
                "template_reason": template_reason,
                "source_texture_count": len(record["textures"]),
                "source_scalar_count": len(record["scalars"]),
                "source_vector_count": len(record["vectors"]),
                "source_static_switch_count": len(record["switches"]),
                "source_base_property_overrides": record["base_property_overrides"],
                "parameter_result": parameter_result,
            }
        )
    unreal.EditorAssetLibrary.save_directory(
        MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )
    missing = [
        item["material_path"]
        for item in materials
        if not unreal.EditorAssetLibrary.does_asset_exist(
            item["material_path"].split(".", 1)[0]
        )
    ]
    if len(materials) != EXPECTED_OVERRIDE_MATERIAL_COUNT or missing:
        raise RuntimeError("StormPass Foliage material asset verification failed")

    after = world_snapshot()
    if after != before:
        raise RuntimeError("Editor world changed during Foliage material asset pass")
    report = {
        "status": "restored",
        "operation": "asset_only_foliage_override_material_rebuild",
        "map_modified": False,
        "source_audit_path": SOURCE_AUDIT_PATH,
        "source_metadata_path": METADATA_PATH,
        "source_asset_report_path": ASSET_REPORT_PATH,
        "material_root": MATERIAL_ROOT,
        "texture_root": TEXTURE_ROOT,
        "material_count": len(materials),
        "required_texture_count": len(required_texture_names),
        "texture_root_inventory_count": len(texture_index),
        "texture_import_task_count": max(previous_import_count, import_count),
        "texture_import_task_count_this_run": import_count,
        "configured_texture_count": len(configured_textures),
        "live_template_reference_count": live_reference_count,
        "parameter_application_totals": dict(parameter_totals),
        "material_results": materials,
        "missing_asset_count": len(missing),
        "fog_policy": "deferred_until_final_pass",
        "world_before": before,
        "world_after": after,
    }
    shared.write_json(REPORT_PATH, report)
    log(
        "RESULT materials={} textures={} imported={} templates={} fog=0 report={}".format(
            report["material_count"],
            report["required_texture_count"],
            report["texture_import_task_count"],
            report["live_template_reference_count"],
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
                "fog_policy": "deferred_until_final_pass",
            },
        )
        unreal.log_error(
            "KHAZAN_STORMPASS_FOLIAGE_OVERRIDE_MATERIALS: " + str(exception)
        )
        raise
