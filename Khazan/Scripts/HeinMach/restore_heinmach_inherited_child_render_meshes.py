"""Restore visible HeinMach child meshes inherited from Blueprint templates.

The first child-render repair only covered 15 StaticMesh values serialized
directly in level component objects.  The template-aware audit found another
12 visible child components.  Eight of those have non-identity local transforms,
so this script composes Local * Parent through UE's Transform implementation.

Fog actors and Fog materials are a hard boundary.  Their count and transform
signature are checked before and after the operation and they are never edited.
"""

import hashlib
import json
import math
import os
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreInheritedChildFix"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed"
DESTINATION_ROOT = RECONSTRUCTED_ROOT + "/InheritedChildRenderAssets"
SEARCH_ROOTS = (
    RECONSTRUCTED_ROOT + "/CorrectedSourceAssets",
    RECONSTRUCTED_ROOT + "/ChildRenderAssets",
    DESTINATION_ROOT,
)
STAGE_NAME = "HeinMach_InheritedChildRenderLibrary"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
AUDIT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_ChildTemplateCoverage_Audit.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_InheritedChild_Render_Restore.json",
)

MANAGED_LABEL_PREFIX = "HM_InheritedChild_"
MANAGED_FOLDER_ROOT = "HeinMach/Reconstructed/InheritedChildProps"
FOG_LABEL_PREFIX = "HM_FogSheet_"
EXPECTED_COMPONENT_COUNT = 12
EXPECTED_PACKAGE_COUNT = 4
EXPECTED_FOG_COUNT = 50
EXPECTED_FOG_SHA256 = "3d49d1082a3c21e1ec51712f9124619d24cc9e0bb9e0df7c7b4951514df00c48"
LOCATION_TOLERANCE_CM = 0.02
ROTATION_TOLERANCE_DEGREES = 0.02
SCALE_TOLERANCE = 0.0002


def log(message):
    unreal.log("KHAZAN_HEINMACH_INHERITED_CHILD: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required template-child audit does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def source_usd_path(package):
    return os.path.join(FMODEL_ROOT, *str(package).split("/")) + ".usda"


def normalized_asset_names(asset):
    names = {asset.get_name()}
    for prefix in ("SM_", "MI_", "M_", "T_"):
        if asset.get_name().startswith(prefix):
            names.add(asset.get_name()[len(prefix) :])
    return names


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def static_mesh_index():
    result = {}
    for root in SEARCH_ROOTS:
        if not unreal.EditorAssetLibrary.does_directory_exist(root):
            continue
        for asset_path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        ):
            if asset_class_name(asset_path) != "StaticMesh":
                continue
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not asset:
                continue
            for name in normalized_asset_names(asset):
                result.setdefault(name, asset)
    return result


def accepted_records(payload):
    records = [
        record
        for record in payload.get("resolved_child_mesh_components", [])
        if not bool(
            record.get("resolution", {}).get("already_in_old_direct_gap_report")
        )
    ]
    packages = sorted({str(record.get("static_mesh_package", "")) for record in records})
    packages = [package for package in packages if package]
    if len(records) != EXPECTED_COMPONENT_COUNT or len(packages) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError(
            "Unexpected inherited-child inventory: records={} packages={}".format(
                len(records), len(packages)
            )
        )
    if any(record.get("visible") is False for record in records):
        raise RuntimeError("Hidden component entered inherited-child inventory")
    if any(
        record.get("attach_parent_object_index")
        != record.get("root_component_object_index")
        for record in records
    ):
        raise RuntimeError("Nested child hierarchy requires an additional transform chain")
    if any(record.get("override_material_packages") for record in records):
        raise RuntimeError("Unexpected inherited-child override material inventory")
    searchable = " ".join(
        "{} {} {} {}".format(
            record.get("actor_type", ""),
            record.get("actor_name", ""),
            record.get("component_name", ""),
            record.get("static_mesh_package", ""),
        )
        for record in records
    ).lower()
    if any(token in searchable for token in ("fog", "mist", "volumetric")):
        raise RuntimeError("Fog content entered inherited-child inventory")
    labels = [managed_label(record) for record in records]
    if len(set(labels)) != len(labels):
        raise RuntimeError("Inherited-child inventory creates duplicate labels")
    missing_source = [package for package in packages if not os.path.isfile(source_usd_path(package))]
    if missing_source:
        raise RuntimeError("Missing inherited-child USD source: " + missing_source[0])
    return records, packages, set(labels)


def write_mesh_stage(packages):
    source_files = [source_usd_path(package) for package in packages]
    stage_text = "\n".join(
        [
            "#usda 1.0",
            "(",
            "    metersPerUnit = 0.01",
            '    upAxis = "Z"',
            "    subLayers = [",
            ",\n".join(
                "        @{}@".format(path.replace("\\", "/"))
                for path in source_files
            ),
            "    ]",
            ")",
            "",
        ]
    )
    os.makedirs(os.path.dirname(GENERATED_STAGE_PATH), exist_ok=True)
    with open(GENERATED_STAGE_PATH, "w", encoding="utf-8", newline="\n") as output:
        output.write(stage_text)
    return source_files


def import_mesh_library():
    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", False)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_only_used_materials", True)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", ["/"])
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("prim_path_folder_structure", False)
    options.set_editor_property("merge_identical_material_slots", False)
    options.set_editor_property("interpret_lods", True)
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", GENERATED_STAGE_PATH)
    task.set_editor_property("destination_path", DESTINATION_ROOT)
    task.set_editor_property("destination_name", STAGE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths"))


def ensure_meshes(packages):
    index = static_mesh_index()
    missing = [package for package in packages if package_basename(package) not in index]
    imported_paths = []
    imported_source_files = []
    if missing:
        imported_source_files = write_mesh_stage(missing)
        imported_paths = import_mesh_library()
        index = static_mesh_index()
        missing = [package for package in packages if package_basename(package) not in index]
    if missing:
        raise RuntimeError("USD import left inherited-child mesh unresolved: " + missing[0])
    return index, imported_paths, imported_source_files


def vector_from(transform, field, defaults):
    value = transform.get(field, {})
    return unreal.Vector(
        x=float(value.get("x", defaults[0])),
        y=float(value.get("y", defaults[1])),
        z=float(value.get("z", defaults[2])),
    )


def rotator_from(transform):
    value = transform.get("rotation_degrees", {})
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def unreal_transform(transform):
    return unreal.Transform(
        location=vector_from(transform, "location_cm", (0.0, 0.0, 0.0)),
        rotation=rotator_from(transform),
        scale=vector_from(transform, "scale", (1.0, 1.0, 1.0)),
    )


def expected_world_transform(record):
    local = unreal_transform(record.get("local_transform", {}))
    parent = unreal_transform(record.get("actor_world_transform", {}))
    # UE ComposeTransforms(A, B) applies A first, then B.  Child local space
    # therefore composes as Local * Parent.
    return unreal.MathLibrary.compose_transforms(local, parent)


def managed_label(record):
    return "{}{}_{:05d}_{:05d}".format(
        MANAGED_LABEL_PREFIX,
        record.get("source_level", "Unknown"),
        int(record.get("actor_object_index", -1)),
        int(record.get("component_object_index", -1)),
    )[:220]


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
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create inherited-child backup map")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def spawn_static_mesh_actor(actor_subsystem, mesh, transform):
    try:
        actor = actor_subsystem.spawn_actor_from_object(
            mesh, transform.translation, transform.rotation.rotator()
        )
    except Exception:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor, transform.translation, transform.rotation.rotator()
        )
    if not actor:
        raise RuntimeError("Failed to spawn inherited-child mesh: " + mesh.get_name())
    return actor


def place_records(records, mesh_index, expected_labels):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = list(actor_subsystem.get_all_level_actors())
    managed = {
        actor.get_actor_label(): actor
        for actor in all_actors
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    unexpected = sorted(set(managed) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected inherited-child actor exists: " + unexpected[0])

    created_count = 0
    reused_count = 0
    for record in records:
        mesh_package = str(record["static_mesh_package"])
        mesh = mesh_index[package_basename(mesh_package)]
        transform = expected_world_transform(record)
        label = managed_label(record)
        actor = managed.get(label)
        if actor:
            reused_count += 1
        else:
            actor = spawn_static_mesh_actor(actor_subsystem, mesh, transform)
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            created_count += 1

        actor.set_actor_location(transform.translation, False, False)
        actor.set_actor_rotation(transform.rotation.rotator(), False)
        actor.set_actor_scale3d(transform.scale3d)
        set_actor_folder(
            actor,
            "{}/{}".format(
                MANAGED_FOLDER_ROOT, record.get("source_level", "Unknown")
            ),
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Inherited-child actor has no StaticMeshComponent: " + label)
        if component.get_editor_property("static_mesh") != mesh:
            component.set_static_mesh(mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        component.set_editor_property("cast_shadow", bool(record.get("cast_shadow", True)))
        component.set_editor_property("reverse_culling", False)
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            component.empty_override_materials()
        max_distance = record.get("cached_max_draw_distance")
        if max_distance is not None:
            try:
                component.set_editor_property("ld_max_draw_distance", float(max_distance))
            except Exception:
                pass

    final = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    if set(final) != expected_labels:
        raise RuntimeError(
            "Inherited-child actor set mismatch: actual={} expected={}".format(
                len(final), len(expected_labels)
            )
        )
    return actor_subsystem, final, {
        "created_count": created_count,
        "reused_count": reused_count,
        "final_managed_actor_count": len(final),
        "final_total_actor_count": len(actor_subsystem.get_all_level_actors()),
    }


def quaternion_values(rotation):
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
    actual_values = quaternion_values(actual)
    expected_values = quaternion_values(expected)
    dot = min(1.0, abs(sum(a * b for a, b in zip(actual_values, expected_values))))
    return math.degrees(2.0 * math.acos(dot)) > ROTATION_TOLERANCE_DEGREES


def validate_placements(records, actors):
    failures = []
    records_by_label = {managed_label(record): record for record in records}
    for label, record in records_by_label.items():
        actor = actors[label]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        expected = expected_world_transform(record)
        actual_location = actor.get_actor_location()
        actual_rotation = actor.get_actor_rotation()
        actual_scale = actor.get_actor_scale3d()
        mesh = component.get_editor_property("static_mesh") if component else None
        issues = []
        if not mesh or package_basename(record["static_mesh_package"]) not in normalized_asset_names(mesh):
            issues.append("mesh")
        if vector_mismatch(
            (actual_location.x, actual_location.y, actual_location.z),
            (expected.translation.x, expected.translation.y, expected.translation.z),
            LOCATION_TOLERANCE_CM,
        ):
            issues.append("location")
        if rotation_mismatch(actual_rotation, expected.rotation):
            issues.append("rotation")
        if vector_mismatch(
            (actual_scale.x, actual_scale.y, actual_scale.z),
            (expected.scale3d.x, expected.scale3d.y, expected.scale3d.z),
            SCALE_TOLERANCE,
        ):
            issues.append("scale")
        if component and component.get_editor_property("reverse_culling"):
            issues.append("reverse_culling")
        if issues:
            failures.append({"label": label, "issues": issues})
    return failures


def mesh_material_summary(packages, mesh_index):
    result = []
    for package in packages:
        mesh = mesh_index[package_basename(package)]
        materials = mesh.get_editor_property("static_materials") or []
        result.append(
            {
                "source_package": package,
                "asset_path": mesh.get_path_name(),
                "static_material_slot_count": len(materials),
                "null_material_slot_count": sum(
                    not bool(item.get_editor_property("material_interface"))
                    for item in materials
                ),
            }
        )
    return result


def main():
    payload = load_json(AUDIT_PATH)
    if payload.get("status") != "audited":
        raise RuntimeError("Template-child coverage report is not audited")
    records, packages, expected_labels = accepted_records(payload)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fog_before = fog_signature(actor_subsystem)
    expected_fog = {"count": EXPECTED_FOG_COUNT, "sha256": EXPECTED_FOG_SHA256}
    if fog_before != expected_fog:
        raise RuntimeError("Fog boundary differs before child repair: " + str(fog_before))

    backup_created = backup_map_once()
    mesh_index, imported_paths, imported_source_files = ensure_meshes(packages)
    actor_subsystem, actors, placement = place_records(
        records, mesh_index, expected_labels
    )
    placement_failures = validate_placements(records, actors)
    if placement_failures:
        raise RuntimeError("Inherited-child placement validation failed: " + str(placement_failures[0]))

    material_summary = mesh_material_summary(packages, mesh_index)
    null_material_slots = sum(item["null_material_slot_count"] for item in material_summary)
    if null_material_slots:
        raise RuntimeError("Inherited-child mesh import contains null material slots")

    fog_after = fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError(
            "Fog boundary changed during child repair: before={} after={}".format(
                fog_before, fog_after
            )
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach map after inherited-child repair")
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
        "fog_boundary": {"status": "unchanged", "before": fog_before, "after": fog_after},
        "transform_policy": "UE ComposeTransforms(Local, Parent)",
        "excluded_content": [
            "Managed FogSheet actors and Fog materials",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} actors={} created={} reused={} fog={} report={}".format(
            report["status"],
            len(packages),
            len(records),
            placement["created_count"],
            placement["reused_count"],
            fog_after["count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {"status": "failed", "error": str(exception), "traceback": traceback.format_exc()},
        )
        unreal.log_error("KHAZAN_HEINMACH_INHERITED_CHILD: " + str(exception))
        raise
