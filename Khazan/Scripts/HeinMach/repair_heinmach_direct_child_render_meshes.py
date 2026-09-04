"""Correct transforms and LOD0 material overrides on the original 15 child props.

The historical child repair copied the owning actor transform and treated the
override array index as a UE material slot.  The current template-aware audit
shows one bridge child with a +500 cm local Z offset, while the carrier meshes
also contain one override index that is not bound by the exported LOD0 mesh.
This repair composes Local * Parent and maps only USDA LOD0 source bindings to
UE slots by texture fingerprint.
"""

import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "restore_heinmach_child_render_meshes.py")
NEW_SCRIPT_PATH = os.path.join(
    SCRIPT_DIR, "restore_heinmach_inherited_child_render_meshes.py"
)
MATERIAL_HELPER_PATH = os.path.join(SCRIPT_DIR, "repair_heinmach_materials.py")
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_DirectChild_TransformMaterial_Repair.json",
)
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreDirectChildTransformMaterialFix"
)
EXPECTED_COMPONENT_COUNT = 15
EXPECTED_MESH_COUNT = 3
EXPECTED_RENDER_OVERRIDE_REFERENCE_COUNT = 29
EXPECTED_NON_RENDER_REFERENCE_COUNT = 5
MATERIAL_SEARCH_ROOTS = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials/Inherited/Materials",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials/Materials",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/ChildRenderAssets",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/SourceAssets",
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load repair helper: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load_module("khazan_direct_child_old_helpers", OLD_SCRIPT_PATH)
new = load_module("khazan_direct_child_transform_helpers", NEW_SCRIPT_PATH)
material_helper = load_module("khazan_direct_child_material_helpers", MATERIAL_HELPER_PATH)


def log(message):
    unreal.log("KHAZAN_HEINMACH_DIRECT_CHILD_REPAIR: " + str(message))


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        return "Invalid"


def material_index():
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
            for name in new.normalized_asset_names(asset):
                result.setdefault(name, asset)
    return result


def actual_material_records(mesh):
    records = []
    for ue_slot, static_material in enumerate(mesh.get_editor_property("static_materials")):
        material = static_material.get_editor_property("material_interface")
        records.append(
            {
                "ue_slot": ue_slot,
                "material": material,
                "path": material.get_path_name() if material else None,
                "name": material.get_name() if material else None,
                "textures": material_helper.actual_material_textures(material),
            }
        )
    return records


def build_slot_mapping(mesh_package, mesh):
    parsed = material_helper.parse_mesh_materials(mesh_package)
    source_records = []
    for source_slot, source_name in sorted(parsed["slots"].items()):
        source_records.append(
            {
                "source_slot": source_slot,
                "source": material_helper.source_material_info(
                    source_name,
                    reference_usd=parsed["references"].get(source_name),
                ),
            }
        )
    assignments, tie_count = material_helper.best_slot_assignment(
        source_records, actual_material_records(mesh)
    )
    if tie_count != 1:
        raise RuntimeError(
            "Ambiguous child material slot mapping for {}: {} ties".format(
                mesh_package, tie_count
            )
        )
    mapping = {
        int(assignment["source_slot"]): int(assignment["ue_slot"])
        for assignment in assignments
    }
    return mapping, {
        "mesh_package": mesh_package,
        "mesh_asset": mesh.get_path_name(),
        "source_lod0_binding_count": len(source_records),
        "ue_material_slot_count": len(mesh.get_editor_property("static_materials")),
        "assignment_tie_count": tie_count,
        "assignments": [
            {
                "source_slot": int(assignment["source_slot"]),
                "ue_slot": int(assignment["ue_slot"]),
                "source_material": assignment["source"].get("name"),
                "actual_default_material": assignment["actual_material_path"],
                "matched_textures": list(assignment.get("matched_textures", [])),
                "score": int(assignment.get("score", 0)),
            }
            for assignment in assignments
        ],
    }


def accepted_records(payload):
    records = [
        record
        for record in payload.get("resolved_child_mesh_components", [])
        if bool(record.get("resolution", {}).get("already_in_old_direct_gap_report"))
    ]
    packages = sorted({str(record.get("static_mesh_package", "")) for record in records})
    if len(records) != EXPECTED_COMPONENT_COUNT or len(packages) != EXPECTED_MESH_COUNT:
        raise RuntimeError(
            "Unexpected direct-child inventory: records={} meshes={}".format(
                len(records), len(packages)
            )
        )
    if any(
        record.get("attach_parent_object_index")
        != record.get("root_component_object_index")
        for record in records
    ):
        raise RuntimeError("Nested direct-child transform hierarchy is unsupported")
    return records, packages


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(new.MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create direct-child correction backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def main():
    payload = new.load_json(new.AUDIT_PATH)
    if payload.get("status") != "audited":
        raise RuntimeError("Template-child coverage report is not audited")
    records, packages = accepted_records(payload)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(new.MAP_PATH + "."):
        if not level_subsystem.load_level(new.MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fog_before = new.fog_signature(actor_subsystem)
    expected_fog = {"count": new.EXPECTED_FOG_COUNT, "sha256": new.EXPECTED_FOG_SHA256}
    if fog_before != expected_fog:
        raise RuntimeError("Fog boundary differs before direct-child repair")
    backup_created = backup_map_once()

    actors = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(old.MANAGED_LABEL_PREFIX)
    }
    expected_labels = {old.managed_label(record) for record in records}
    if set(actors) != expected_labels:
        raise RuntimeError(
            "Direct-child actor set mismatch: actual={} expected={}".format(
                len(actors), len(expected_labels)
            )
        )

    mesh_by_package = {}
    for record in records:
        actor = actors[old.managed_label(record)]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = component.get_editor_property("static_mesh") if component else None
        if not mesh or new.package_basename(record["static_mesh_package"]) not in new.normalized_asset_names(mesh):
            raise RuntimeError("Direct-child mesh mismatch: " + old.managed_label(record))
        mesh_by_package.setdefault(record["static_mesh_package"], mesh)

    slot_mappings = {}
    mapping_records = []
    for mesh_package in packages:
        mapping, mapping_record = build_slot_mapping(
            mesh_package, mesh_by_package[mesh_package]
        )
        slot_mappings[mesh_package] = mapping
        mapping_records.append(mapping_record)

    materials = material_index()
    required_material_packages = sorted(
        {
            str(package)
            for record in records
            for package in record.get("override_material_packages", [])
            if package
        }
    )
    missing_materials = [
        package
        for package in required_material_packages
        if new.package_basename(package) not in materials
    ]
    if missing_materials:
        raise RuntimeError("Missing direct-child override material: " + missing_materials[0])

    transform_changed_count = 0
    render_override_references = 0
    non_render_references = 0
    applied_references = 0
    for record in records:
        actor = actors[old.managed_label(record)]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        expected = new.expected_world_transform(record)
        before = actor.get_actor_location()
        if new.vector_mismatch(
            (before.x, before.y, before.z),
            (expected.translation.x, expected.translation.y, expected.translation.z),
            new.LOCATION_TOLERANCE_CM,
        ):
            transform_changed_count += 1
        actor.set_actor_location(expected.translation, False, False)
        actor.set_actor_rotation(expected.rotation.rotator(), False)
        actor.set_actor_scale3d(expected.scale3d)
        component.set_editor_property("cast_shadow", bool(record.get("cast_shadow", True)))
        component.set_editor_property("reverse_culling", False)
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            component.empty_override_materials()

        mapping = slot_mappings[record["static_mesh_package"]]
        for source_slot, package in enumerate(record.get("override_material_packages", [])):
            if not package:
                continue
            ue_slot = mapping.get(source_slot)
            if ue_slot is None:
                non_render_references += 1
                continue
            render_override_references += 1
            material = materials[new.package_basename(package)]
            component.set_material(ue_slot, material)
            applied_references += 1

    if render_override_references != EXPECTED_RENDER_OVERRIDE_REFERENCE_COUNT:
        raise RuntimeError(
            "Unexpected direct-child LOD0 override count: " + str(render_override_references)
        )
    if non_render_references != EXPECTED_NON_RENDER_REFERENCE_COUNT:
        raise RuntimeError(
            "Unexpected direct-child non-render override count: " + str(non_render_references)
        )

    validation_failures = []
    for record in records:
        label = old.managed_label(record)
        actor = actors[label]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        expected = new.expected_world_transform(record)
        location = actor.get_actor_location()
        scale = actor.get_actor_scale3d()
        issues = []
        if new.vector_mismatch(
            (location.x, location.y, location.z),
            (expected.translation.x, expected.translation.y, expected.translation.z),
            new.LOCATION_TOLERANCE_CM,
        ):
            issues.append("location")
        if new.rotation_mismatch(actor.get_actor_rotation(), expected.rotation):
            issues.append("rotation")
        if new.vector_mismatch(
            (scale.x, scale.y, scale.z),
            (expected.scale3d.x, expected.scale3d.y, expected.scale3d.z),
            new.SCALE_TOLERANCE,
        ):
            issues.append("scale")
        mapping = slot_mappings[record["static_mesh_package"]]
        for source_slot, package in enumerate(record.get("override_material_packages", [])):
            if not package or source_slot not in mapping:
                continue
            actual_material = component.get_material(mapping[source_slot])
            if not actual_material or new.package_basename(package) not in new.normalized_asset_names(actual_material):
                issues.append("override_material_slot_{}".format(source_slot))
        if component.get_editor_property("reverse_culling"):
            issues.append("reverse_culling")
        if issues:
            validation_failures.append({"label": label, "issues": sorted(set(issues))})
    if validation_failures:
        raise RuntimeError("Direct-child validation failed: " + str(validation_failures[0]))

    fog_after = new.fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError("Fog boundary changed during direct-child repair")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save direct-child corrected HeinMach map")

    report = {
        "status": "repaired",
        "map_path": new.MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_inventory_report": new.AUDIT_PATH,
        "component_count": len(records),
        "mesh_count": len(packages),
        "transform_changed_actor_count": transform_changed_count,
        "render_override_reference_count": render_override_references,
        "applied_override_reference_count": applied_references,
        "non_render_lod_or_unused_reference_count": non_render_references,
        "material_slot_mappings": mapping_records,
        "validation_failure_count": len(validation_failures),
        "fog_boundary": {"status": "unchanged", "before": fog_before, "after": fog_after},
        "transform_policy": "UE ComposeTransforms(Local, Parent)",
        "material_policy": (
            "Map only USDA LOD0 material bindings to UE render slots; do not force "
            "LOD-only or unused override indices onto LOD0."
        ),
        "excluded_content": [
            "Managed FogSheet actors and Fog materials",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    new.write_json(REPORT_PATH, report)
    log(
        "RESULT status={} actors={} transform_fixes={} overrides={}/{} lod_only={} fog={} report={}".format(
            report["status"],
            len(records),
            transform_changed_count,
            applied_references,
            render_override_references,
            non_render_references,
            fog_after["count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        new.write_json(
            REPORT_PATH,
            {"status": "failed", "error": str(exception), "traceback": traceback.format_exc()},
        )
        unreal.log_error("KHAZAN_HEINMACH_DIRECT_CHILD_REPAIR: " + str(exception))
        raise
