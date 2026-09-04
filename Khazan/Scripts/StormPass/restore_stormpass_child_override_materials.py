"""Rebuild StormPass child-only override materials from FModel Properties JSON."""

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
CHILD_RESTORE_PATH = os.path.join(
    SCRIPT_DIR, "restore_stormpass_child_render_meshes.py"
)
SOURCE_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildOverrideSource_Audit.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildOverrideMaterial_Restoration.json",
)
OVERRIDE_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials"
)
MATERIAL_ROOT = OVERRIDE_ROOT + "/ChildOverrides/Materials"
TEXTURE_ROOT = OVERRIDE_ROOT + "/Textures"
EXPECTED_MATERIAL_COUNT = 3
EXPECTED_TEXTURE_COUNT = 11


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass material helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load_module("khazan_stormpass_child_override_helpers", SHARED_PATH)
child = load_module("khazan_stormpass_child_restore_material_context", CHILD_RESTORE_PATH)


def log(message):
    unreal.log("KHAZAN_STORMPASS_CHILD_OVERRIDE_MATERIALS: " + str(message))


def configure():
    child.configure_shared()
    shared.CORRECTED_ROOT = child.SOURCE_ROOT
    shared.OVERRIDE_ROOT = OVERRIDE_ROOT
    shared.MATERIAL_ROOT = MATERIAL_ROOT
    shared.TEXTURE_ROOT = TEXTURE_ROOT
    shared.UPDATE_MATERIAL_INSTANCES = False
    shared.USE_LEGACY_TEXTURE_FACTORY = True
    shared.repair.CORRECTED_ROOT = child.SOURCE_ROOT
    shared.repair.FMODEL_ROOT = shared.FMODEL_ROOT
    shared.log = log


def append_child_material_index(index):
    root = child.DESTINATION_ROOT
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return
    for path in unreal.EditorAssetLibrary.list_assets(
        root, recursive=True, include_folder=False
    ):
        if child.asset_class_name(path) not in {"Material", "MaterialInstanceConstant"}:
            continue
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            continue
        for name in shared.normalized_material_names(asset):
            index[name].append(path)


def source_inventory():
    audit = shared.load_json(SOURCE_AUDIT_PATH)
    if (
        audit.get("status") != "audited"
        or audit.get("material_package_count") != EXPECTED_MATERIAL_COUNT
        or audit.get("parsed_material_count") != EXPECTED_MATERIAL_COUNT
        or audit.get("missing_json_count")
        or audit.get("parse_error_count")
        or audit.get("unique_texture_package_count") != EXPECTED_TEXTURE_COUNT
        or audit.get("missing_texture_image_count")
    ):
        raise RuntimeError("StormPass child override source audit is incomplete")
    packages = sorted(item["package"] for item in audit.get("records", []))
    return audit, packages


def live_template_inventory(records):
    child_payload = child.shared.load_json(child.AUDIT_PATH)
    placements = child_payload.get("resolved_child_mesh_components", [])
    mesh_packages = sorted({item["static_mesh_package"] for item in placements})
    mesh_index = child.shared.static_mesh_index()
    slot_maps = {}
    mapping_records = []
    for package in mesh_packages:
        mesh = mesh_index[child.shared.package_basename(package)]
        mapping, record = child.build_slot_mapping(package, mesh)
        slot_maps[package] = mapping
        mapping_records.append(record)

    requested = {record["package"] for record in records}
    live_templates = collections.defaultdict(list)
    for placement in placements:
        mesh = mesh_index[child.shared.package_basename(placement["static_mesh_package"])]
        static_materials = list(mesh.get_editor_property("static_materials"))
        mapping = slot_maps[placement["static_mesh_package"]]
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if package not in requested:
                continue
            ue_slot = mapping.get(source_slot)
            if ue_slot is None or ue_slot >= len(static_materials):
                continue
            material = static_materials[ue_slot].get_editor_property(
                "material_interface"
            )
            if material:
                live_templates[package].append(material.get_path_name())
    return live_templates, mapping_records


def main():
    configure()
    source_audit, packages = source_inventory()
    records = [shared.raw_material_record(package) for package in packages]
    required_texture_names = {
        item["texture_name"] for record in records for item in record["textures"]
    }
    if len(required_texture_names) != EXPECTED_TEXTURE_COUNT:
        raise RuntimeError(
            "Unexpected StormPass child texture inventory: {}".format(
                len(required_texture_names)
            )
        )
    previous_import_count = 0
    if os.path.isfile(REPORT_PATH):
        previous_report = shared.load_json(REPORT_PATH)
        if previous_report.get("status") == "restored":
            previous_import_count = int(
                previous_report.get("texture_import_task_count", 0)
            )
    texture_index, texture_import_count, configured_textures = shared.import_textures(
        records
    )
    live_templates, mapping_records = live_template_inventory(records)

    material_index, _ = shared.material_asset_index()
    append_child_material_index(material_index)
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
                "parameter_result": parameter_result,
            }
        )
    unreal.EditorAssetLibrary.save_directory(
        MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )

    missing_assets = [
        item["material_path"]
        for item in materials
        if not unreal.EditorAssetLibrary.does_asset_exist(
            item["material_path"].split(".", 1)[0]
        )
    ]
    if len(materials) != EXPECTED_MATERIAL_COUNT or missing_assets:
        raise RuntimeError("StormPass child material asset verification failed")
    report = {
        "status": "restored",
        "source_audit_path": SOURCE_AUDIT_PATH,
        "material_root": MATERIAL_ROOT,
        "texture_root": TEXTURE_ROOT,
        "material_count": len(materials),
        "required_texture_count": len(required_texture_names),
        "texture_root_inventory_count": len(texture_index),
        "texture_import_task_count": max(
            previous_import_count, texture_import_count
        ),
        "texture_import_task_count_this_run": texture_import_count,
        "configured_texture_count": len(configured_textures),
        "parameter_application_totals": dict(parameter_totals),
        "material_results": materials,
        "child_mesh_slot_mappings": mapping_records,
        "missing_asset_count": len(missing_assets),
        "source_audit_counts": {
            "missing_json_count": source_audit.get("missing_json_count"),
            "missing_texture_image_count": source_audit.get(
                "missing_texture_image_count"
            ),
        },
        "excluded_content": [
            "All StormPass Fog/Mist actors and materials",
            "Foliage HISM components",
            "Gameplay, character, enemy, spawn, quest, cinema and audio content",
        ],
    }
    shared.write_json(REPORT_PATH, report)
    log(
        "RESULT status={} materials={} textures={} imported={} report={}".format(
            report["status"],
            report["material_count"],
            report["required_texture_count"],
            report["texture_import_task_count"],
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
        unreal.log_error(
            "KHAZAN_STORMPASS_CHILD_OVERRIDE_MATERIALS: " + str(exception)
        )
        raise
