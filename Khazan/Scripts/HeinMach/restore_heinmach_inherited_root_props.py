"""Restore HeinMach root meshes inherited from Blueprint component templates.

The first reconstruction only saw StaticMesh values serialized directly on a
level actor's local root component.  Most prop actors inherit that value from
their Blueprint component template, so 6,439 visible placements were omitted.

This script consumes HeinMach_RootTemplateCoverage_Audit.json, imports the
newly extracted mesh library, revalidates the existing managed placements, and
adds only the missing actors.  It never edits the managed FogSheet actors.
"""

import hashlib
import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "import_heinmach_static_meshes.py")
ROOT_AUDIT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_RootTemplateCoverage_Audit.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_InheritedRootProp_Restoration.json",
)
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreTemplateCoverageFix"
)

EXPECTED_PLACEMENT_COUNT = 9104
EXPECTED_EXISTING_COUNT = 2665
EXPECTED_INHERITED_COUNT = 6439
EXPECTED_STATIC_MESH_COUNT = 313
EXPECTED_FOG_ACTOR_COUNT = 50
FOG_LABEL_PREFIX = "HM_FogSheet_"


def load_base_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_static_mesh_base", BASE_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load base reconstruction script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_module()
base.BACKUP_MAP_PATH = BACKUP_MAP_PATH
base.REPORT_PATH = REPORT_PATH


def log(message):
    unreal.log("KHAZAN_HEINMACH_TEMPLATE_ROOTS: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_TEMPLATE_ROOTS: " + str(message))


def actor_transform_record(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "label": actor.get_actor_label(),
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": [scale.x, scale.y, scale.z],
    }


def fog_signature(actor_subsystem):
    records = sorted(
        (
            actor_transform_record(actor)
            for actor in actor_subsystem.get_all_level_actors()
            if actor and actor.get_actor_label().startswith(FOG_LABEL_PREFIX)
        ),
        key=lambda item: item["label"],
    )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "count": len(records),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def validated_inventory(payload):
    if payload.get("status") != "audited":
        raise RuntimeError("Root-template coverage report is not audited")

    source_placements = list(payload.get("resolved_root_placements", []))
    packages = sorted(
        {str(item.get("static_mesh_package", "")) for item in source_placements}
    )
    packages = [package for package in packages if package]
    inherited_count = sum(
        not bool(item.get("resolution", {}).get("already_in_compact_manifest"))
        for item in source_placements
    )
    existing_count = len(source_placements) - inherited_count

    counts = {
        "placement_count": len(source_placements),
        "existing_count": existing_count,
        "inherited_count": inherited_count,
        "static_mesh_count": len(packages),
    }
    expected = {
        "placement_count": EXPECTED_PLACEMENT_COUNT,
        "existing_count": EXPECTED_EXISTING_COUNT,
        "inherited_count": EXPECTED_INHERITED_COUNT,
        "static_mesh_count": EXPECTED_STATIC_MESH_COUNT,
    }
    if counts != expected:
        raise RuntimeError(
            "Unexpected root-template inventory: actual={} expected={}".format(
                counts, expected
            )
        )

    fog_tokens = []
    for item in source_placements:
        searchable = " ".join(
            str(item.get(key, ""))
            for key in ("actor_name", "actor_type", "static_mesh_package")
        ).lower()
        if "fog" in searchable:
            fog_tokens.append(item.get("actor_name"))
    if fog_tokens:
        raise RuntimeError(
            "Fog content entered the prop placement inventory: " + str(fog_tokens[:5])
        )

    labels = [base.managed_label(item) for item in source_placements]
    if len(set(labels)) != len(labels):
        raise RuntimeError("Root-template inventory contains duplicate managed labels")
    placements = base.filter_excluded_placements(source_placements)
    active_packages = sorted(
        {str(item.get("static_mesh_package", "")) for item in placements}
    )
    active_packages = [package for package in active_packages if package]
    counts["active_placement_count"] = len(placements)
    counts["excluded_placement_count"] = len(source_placements) - len(placements)
    active_labels = {base.managed_label(item) for item in placements}
    return placements, active_packages, counts, active_labels


def validate_existing_managed_actors(actor_subsystem, expected_labels):
    labels = {
        actor.get_actor_label()
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(base.MANAGED_LABEL_PREFIX)
    }
    unexpected = sorted(labels - expected_labels)
    if unexpected:
        raise RuntimeError(
            "Unexpected managed prop actors exist; first: " + unexpected[0]
        )
    return len(labels)


def negative_determinant_count(placements):
    count = 0
    for item in placements:
        scale = item.get("transform", {}).get("scale", {})
        determinant = (
            float(scale.get("x", 1.0))
            * float(scale.get("y", 1.0))
            * float(scale.get("z", 1.0))
        )
        if determinant < 0.0:
            count += 1
    return count


def main():
    payload = base.load_json(ROOT_AUDIT_PATH)
    placements, packages, inventory, expected_labels = validated_inventory(payload)

    source_files = base.write_mesh_stage(packages)
    class_assets_before = base.imported_assets_by_class()
    _, missing_before = base.expected_meshes_present(packages, class_assets_before)
    imported_object_paths = []
    if missing_before:
        log("Importing {} newly extracted source meshes".format(len(missing_before)))
        imported_object_paths = base.import_mesh_library()

    class_assets_after = base.imported_assets_by_class()
    static_mesh_index, missing_after = base.expected_meshes_present(
        packages, class_assets_after
    )
    if missing_after:
        raise RuntimeError(
            "USD import left {} source meshes unresolved; first: {}".format(
                len(missing_after), missing_after[0]
            )
        )

    material_paths = []
    for class_name in ("Material", "MaterialInstanceConstant"):
        material_paths.extend(class_assets_after.get(class_name, []))
    material_index = base.loaded_asset_index(material_paths)

    backup_created = base.backup_map_once()
    level_subsystem = base.load_map()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing_managed_count = validate_existing_managed_actors(
        actor_subsystem, expected_labels
    )
    fog_before = fog_signature(actor_subsystem)
    if fog_before["count"] != EXPECTED_FOG_ACTOR_COUNT:
        raise RuntimeError(
            "Fog boundary guard expected {} actors, found {}".format(
                EXPECTED_FOG_ACTOR_COUNT, fog_before["count"]
            )
        )

    placement_result = base.place_meshes(
        placements, static_mesh_index, material_index
    )
    active_expected_count = len(placements)
    if placement_result["final_managed_actor_count"] != active_expected_count:
        raise RuntimeError(
            "Managed prop validation failed: expected {} got {}".format(
                active_expected_count,
                placement_result["final_managed_actor_count"],
            )
        )

    fog_after = fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError(
            "Fog boundary guard failed: before={} after={}".format(
                fog_before, fog_after
            )
        )

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save the root-template-complete HeinMach map")
    unreal.EditorAssetLibrary.save_directory(
        base.DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored",
        "map_path": base.MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "root_template_audit_path": ROOT_AUDIT_PATH,
        "inventory": inventory,
        "source_usd_count": len(source_files),
        "missing_mesh_count_before_import": len(missing_before),
        "missing_mesh_count_after_import": len(missing_after),
        "imported_object_path_count": len(imported_object_paths),
        "imported_asset_class_counts": {
            class_name: len(paths)
            for class_name, paths in sorted(class_assets_after.items())
        },
        "existing_managed_actor_count": existing_managed_count,
        "placement_result": placement_result,
        "negative_determinant_placement_count": negative_determinant_count(
            placements
        ),
        "reverse_culling_policy": (
            "Leave component reverse_culling disabled. Unreal automatically reverses "
            "winding for negative local-to-world determinants."
        ),
        "fog_boundary": {
            "status": "unchanged",
            "before": fog_before,
            "after": fog_after,
        },
        "excluded_content": [
            "Managed FogSheet actors and Fog materials",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    base.write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} placements={} created={} reused={} fog={} report={}".format(
            report["status"],
            inventory["static_mesh_count"],
            inventory["placement_count"],
            placement_result["created_count"],
            placement_result["reused_count"],
            fog_after["count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "error": str(exception),
            "status": "failed",
            "traceback": traceback.format_exc(),
        }
        base.write_json(REPORT_PATH, failure)
        error(str(exception))
        error(failure["traceback"])
        raise
