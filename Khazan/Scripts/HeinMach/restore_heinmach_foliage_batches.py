"""Transfer the audited corrected HISM foliage batches into the HeinMach map."""

import collections
import hashlib
import json
import math
import os
import re
import struct
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
SANDBOX_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_FoliageImportSandbox"
)
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeFoliageRestore"
)
CORRECTED_SOURCE_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/"
    "CorrectedSourceAssets"
)
FOLIAGE_FOLDER_ROOT = "HeinMach/Reconstructed/FoliageBatches"
LABEL_PREFIX = "HM_FoliageBatch_"
EXPECTED_BATCH_COUNT = 113
EXPECTED_INSTANCE_COUNT = 12495
EXPECTED_PROTOTYPE_COUNT = 19
EXPECTED_CORRECTED_SOURCE_CROSSCHECKS = 3
EXPECTED_MAIN_ACTOR_COUNT_BEFORE = 2760
# Historical main-map inventory after the first child/fog restoration pass.
# Later root-template, Landscape and preview-light restoration legitimately add
# actors, so the foliage-specific audit must not treat this global count as an
# invariant.  Exact live composition is owned by the dedicated integrity audits.
LEGACY_MAIN_ACTOR_COUNT_AFTER = 2938

IMPORT_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Batch_Import.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Batch_Restore.json",
)
BASELINE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Transform_Baseline.json",
)


def log(message):
    unreal.log("KHAZAN_HEINMACH_FOLIAGE_RESTORE: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_FOLIAGE_RESTORE: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required JSON does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def read_text(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required source file does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return source.read()


def object_path(obj):
    return obj.get_path_name() if obj else None


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def normalized_asset_names(asset):
    name = asset.get_name()
    result = {name}
    for prefix in ("SM_", "MI_", "M_"):
        if name.startswith(prefix):
            result.add(name[len(prefix) :])
    return result


def corrected_source_mesh_index():
    result = {}
    for path in unreal.EditorAssetLibrary.list_assets(
        CORRECTED_SOURCE_ROOT, recursive=True, include_folder=False
    ):
        if asset_class_name(path) != "StaticMesh":
            continue
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not mesh:
            continue
        for name in normalized_asset_names(mesh):
            result.setdefault(name, mesh)
    return result


def vector(record, default=0.0):
    return unreal.Vector(
        x=float(record.get("x", default)),
        y=float(record.get("y", default)),
        z=float(record.get("z", default)),
    )


def rotator(record):
    return unreal.Rotator(
        pitch=float(record.get("pitch", 0.0)),
        yaw=float(record.get("yaw", 0.0)),
        roll=float(record.get("roll", 0.0)),
    )


def label_for(source):
    return "{}{}_{}".format(
        LABEL_PREFIX, source["layer"], source["point_instancer"]
    )


def folder_for(source):
    return "{}/{}".format(FOLIAGE_FOLDER_ROOT, source["layer"])


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicate = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicate:
        raise RuntimeError("Failed to create foliage restore backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def source_for_batch(mesh_path, source_by_key):
    segments = mesh_path.split("/")
    candidates = []
    for key, source in source_by_key.items():
        layer, point_name = key
        if layer in segments and point_name in segments:
            candidates.append(source)
    if len(candidates) != 1:
        raise RuntimeError(
            "Could not uniquely map foliage mesh path to source: {} matches={}".format(
                mesh_path, len(candidates)
            )
        )
    return candidates[0]


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


def parse_prototype_material_requirement(source_level_root, source):
    prototype_path = os.path.normpath(
        os.path.join(source_level_root, source["prototype_reference"])
    )
    prototype_text = read_text(prototype_path)
    bindings = re.findall(
        r"rel\s+material:binding(?:\:[^=\s]+)?\s*=\s*"
        r"<[^>]+/Materials/([^>/]+)>",
        prototype_text,
    )
    material_names = list(dict.fromkeys(bindings))
    if len(material_names) != 1:
        raise RuntimeError(
            "Expected one foliage material binding for {} but found {}".format(
                source["prototype_basename"], len(material_names)
            )
        )
    material_name = material_names[0]
    reference_match = re.search(
        r'def\s+Material\s+"{}"\s*\(\s*prepend\s+references\s*=\s*'
        r"@([^@]+)@".format(re.escape(material_name)),
        prototype_text,
        re.DOTALL,
    )
    if not reference_match:
        raise RuntimeError(
            "Could not resolve foliage material reference for "
            + source["prototype_basename"]
        )
    material_usda_path = os.path.normpath(
        os.path.join(os.path.dirname(prototype_path), reference_match.group(1))
    )
    material_json_path = os.path.splitext(material_usda_path)[0] + ".json"
    material_json = load_json(material_json_path)
    parameters = material_json.get("Parameters", {})
    properties = parameters.get("Properties", {})
    overrides = properties.get("BasePropertyOverrides", {})

    two_sided = None
    if overrides.get("bOverride_TwoSided") or "TwoSided" in overrides:
        two_sided = bool(overrides.get("TwoSided", False))
    blend_source = overrides.get("BlendMode", parameters.get("BlendMode"))
    blend_mode = blend_mode_value(blend_source)
    if blend_mode is None:
        raise RuntimeError("Unsupported foliage blend mode: " + str(blend_source))
    opacity_clip = overrides.get("OpacityMaskClipValue")
    if opacity_clip is None and blend_mode == unreal.BlendMode.BLEND_MASKED:
        material_text = read_text(material_usda_path)
        threshold_match = re.search(
            r"inputs:opacityThreshold\s*=\s*([-+0-9.eE]+)", material_text
        )
        if threshold_match:
            opacity_clip = float(threshold_match.group(1))

    return {
        "prototype_path": prototype_path,
        "material_name": material_name,
        "material_usda_path": material_usda_path,
        "material_json_path": material_json_path,
        "two_sided": two_sided,
        "blend_mode": blend_mode,
        "blend_mode_source": blend_source,
        "opacity_mask_clip_value": float(opacity_clip)
        if opacity_clip is not None
        else None,
    }


def static_mesh_materials(mesh):
    return [
        item.get_editor_property("material_interface")
        for item in mesh.get_editor_property("static_materials")
    ]


def build_mappings(import_report, source_meshes):
    source_rows = import_report.get("source_batches", [])
    batch_rows = import_report.get("batch_records", [])
    if len(source_rows) != EXPECTED_BATCH_COUNT or len(batch_rows) != EXPECTED_BATCH_COUNT:
        raise RuntimeError(
            "Foliage import report is incomplete: sources={} batches={}".format(
                len(source_rows), len(batch_rows)
            )
        )
    if sum(int(row.get("instance_count", 0)) for row in source_rows) != EXPECTED_INSTANCE_COUNT:
        raise RuntimeError("Foliage source instance total is not 12495")

    source_level_root = import_report.get("source_level_root")
    if not source_level_root or not os.path.isdir(source_level_root):
        raise RuntimeError("FModel HeinMach source level root is unavailable")
    source_by_key = {
        (row["layer"], row["point_instancer"]): row for row in source_rows
    }
    requirement_by_prototype = {}
    mappings = []
    seen_keys = set()
    for batch in batch_rows:
        source = source_for_batch(batch["mesh_path"], source_by_key)
        key = (source["layer"], source["point_instancer"])
        if key in seen_keys:
            raise RuntimeError("Duplicate imported foliage batch mapping: {}".format(key))
        seen_keys.add(key)

        batch_mesh = unreal.EditorAssetLibrary.load_asset(batch["mesh_path"])
        if not batch_mesh:
            raise RuntimeError("Missing imported foliage batch mesh: " + batch["mesh_path"])
        batch_vertices = int(
            unreal.EditorStaticMeshLibrary.get_number_verts(batch_mesh, 0)
        )
        if batch_vertices <= 0:
            raise RuntimeError("Foliage batch mesh has no LOD0 vertices: " + batch["mesh_path"])
        prototype_name = source["prototype_basename"]
        if prototype_name not in requirement_by_prototype:
            requirement_by_prototype[prototype_name] = (
                parse_prototype_material_requirement(source_level_root, source)
            )
        source_mesh = source_meshes.get(prototype_name)
        source_vertices = None
        corrected_source_matches = None
        if source_mesh:
            source_vertices = int(
                unreal.EditorStaticMeshLibrary.get_number_verts(source_mesh, 0)
            )
            corrected_source_matches = source_vertices == batch_vertices

        imported_materials = static_mesh_materials(batch_mesh)
        if len(imported_materials) != 1 or not imported_materials[0]:
            raise RuntimeError(
                "Expected one valid foliage batch material: " + batch["mesh_path"]
            )
        assigned_materials = (
            static_mesh_materials(source_mesh) if source_mesh else imported_materials
        )
        if len(assigned_materials) != 1 or not assigned_materials[0]:
            raise RuntimeError("Expected one valid assigned foliage material")

        mappings.append(
            {
                "key": key,
                "source": source,
                "batch": batch,
                "source_mesh": source_mesh,
                "batch_mesh": batch_mesh,
                "source_vertex_count": source_vertices,
                "batch_vertex_count": batch_vertices,
                "corrected_source_vertex_matches": corrected_source_matches,
                "material_requirement": requirement_by_prototype[prototype_name],
                "assigned_materials": assigned_materials,
            }
        )

    if len(mappings) != EXPECTED_BATCH_COUNT or len(seen_keys) != EXPECTED_BATCH_COUNT:
        raise RuntimeError("Foliage mapping is not one-to-one")
    if len(requirement_by_prototype) != EXPECTED_PROTOTYPE_COUNT:
        raise RuntimeError("Unexpected foliage prototype inventory")

    prototype_vertex_counts = collections.defaultdict(set)
    for mapping in mappings:
        prototype_vertex_counts[mapping["source"]["prototype_basename"]].add(
            mapping["batch_vertex_count"]
        )
    inconsistent = {
        name: sorted(values)
        for name, values in prototype_vertex_counts.items()
        if len(values) != 1
    }
    if inconsistent:
        raise RuntimeError(
            "Foliage prototype vertex counts vary between batches: "
            + json.dumps(inconsistent, sort_keys=True)
        )
    corrected_crosschecks = {
        mapping["source"]["prototype_basename"]
        for mapping in mappings
        if mapping["source_mesh"]
    }
    if len(corrected_crosschecks) != EXPECTED_CORRECTED_SOURCE_CROSSCHECKS:
        raise RuntimeError(
            "Expected 3 corrected foliage prototype cross-checks but found {}".format(
                len(corrected_crosschecks)
            )
        )
    crosscheck_mismatches = [
        mapping
        for mapping in mappings
        if mapping["corrected_source_vertex_matches"] is False
    ]
    if crosscheck_mismatches:
        first = crosscheck_mismatches[0]
        raise RuntimeError(
            "Corrected foliage prototype vertex mismatch for {}: source={} batch={}".format(
                first["source"]["prototype_basename"],
                first["source_vertex_count"],
                first["batch_vertex_count"],
            )
        )
    return mappings, prototype_vertex_counts, requirement_by_prototype


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def requirement_key(requirement):
    return (
        requirement.get("two_sided"),
        str(requirement.get("blend_mode")),
        requirement.get("opacity_mask_clip_value"),
    )


def repair_assigned_materials(mappings):
    requirements_by_material = collections.defaultdict(list)
    material_objects = {}
    for mapping in mappings:
        for material in mapping["assigned_materials"]:
            path = object_path(material)
            requirements_by_material[path].append(mapping["material_requirement"])
            material_objects[path] = material

    results = []
    for material_path, requirements in sorted(requirements_by_material.items()):
        keys = {requirement_key(item) for item in requirements}
        if len(keys) != 1:
            raise RuntimeError(
                "Conflicting source surface requirements for material: " + material_path
            )
        requirement = requirements[0]
        material = material_objects[material_path]
        material.modify()
        overrides = material.get_editor_property("base_property_overrides")
        if requirement["two_sided"] is not None:
            if not set_struct_property(overrides, "override_two_sided", True):
                raise RuntimeError("Could not override TwoSided for " + material_path)
            if not set_struct_property(
                overrides, "two_sided", requirement["two_sided"]
            ):
                raise RuntimeError("Could not set TwoSided for " + material_path)
        if not set_struct_property(overrides, "override_blend_mode", True):
            raise RuntimeError("Could not override BlendMode for " + material_path)
        if not set_struct_property(
            overrides, "blend_mode", requirement["blend_mode"]
        ):
            raise RuntimeError("Could not set BlendMode for " + material_path)
        if requirement["opacity_mask_clip_value"] is not None:
            if not set_struct_property(
                overrides, "override_opacity_mask_clip_value", True
            ):
                raise RuntimeError("Could not override OpacityMaskClip for " + material_path)
            if not set_struct_property(
                overrides,
                "opacity_mask_clip_value",
                requirement["opacity_mask_clip_value"],
            ):
                raise RuntimeError("Could not set OpacityMaskClip for " + material_path)
        material.set_editor_property("base_property_overrides", overrides)
        try:
            unreal.MaterialEditingLibrary.update_material_instance(material)
        except Exception:
            pass
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            material, only_if_is_dirty=False
        ):
            raise RuntimeError("Could not save repaired foliage material: " + material_path)

        actual = material.get_editor_property("base_property_overrides")
        actual_two_sided = actual.get_editor_property("two_sided")
        actual_blend = actual.get_editor_property("blend_mode")
        actual_clip = actual.get_editor_property("opacity_mask_clip_value")
        matches = actual_blend == requirement["blend_mode"]
        if requirement["two_sided"] is not None:
            matches = matches and actual_two_sided == requirement["two_sided"]
        if requirement["opacity_mask_clip_value"] is not None:
            matches = matches and abs(
                float(actual_clip) - requirement["opacity_mask_clip_value"]
            ) <= 0.00001
        results.append(
            {
                "material": material_path,
                "source_jsons": sorted(
                    {item["material_json_path"] for item in requirements}
                ),
                "two_sided": requirement["two_sided"],
                "blend_mode": str(requirement["blend_mode"]),
                "opacity_mask_clip_value": requirement[
                    "opacity_mask_clip_value"
                ],
                "actual_two_sided": actual_two_sided,
                "actual_blend_mode": str(actual_blend),
                "actual_opacity_mask_clip_value": float(actual_clip),
                "matches": matches,
            }
        )
    mismatches = [row for row in results if not row["matches"]]
    if mismatches:
        raise RuntimeError("Foliage material surface validation failed")
    return results


def foliage_component(actor):
    matches = []
    for component in actor.get_components_by_class(unreal.ActorComponent):
        if not component:
            continue
        if component.get_class().get_name() in (
            "FoliageInstancedStaticMeshComponent",
            "HierarchicalInstancedStaticMeshComponent",
            "InstancedStaticMeshComponent",
        ):
            matches.append(component)
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one HISM component on {} but found {}".format(
                actor.get_actor_label(), len(matches)
            )
        )
    return matches[0]


def transform_values(transform):
    translation = transform.translation
    rotation = transform.rotation
    scale = transform.scale3d
    return (
        float(translation.x),
        float(translation.y),
        float(translation.z),
        float(rotation.x),
        float(rotation.y),
        float(rotation.z),
        float(rotation.w),
        float(scale.x),
        float(scale.y),
        float(scale.z),
    )


def component_transform_snapshot(component):
    return [
        transform_values(
            component.get_instance_transform(instance_index, world_space=True)
        )
        for instance_index in range(int(component.get_instance_count()))
    ]


def transform_digest(snapshot):
    digest = hashlib.sha256()
    for values in snapshot:
        digest.update(struct.pack("<10d", *values))
    return digest.hexdigest()


def compare_component_transforms(component, expected_snapshot):
    actual_count = int(component.get_instance_count())
    if actual_count != len(expected_snapshot):
        return {
            "matches": False,
            "expected_count": len(expected_snapshot),
            "actual_count": actual_count,
            "max_translation_error": None,
            "max_rotation_error_degrees": None,
            "max_scale_error": None,
        }
    max_translation = 0.0
    max_rotation = 0.0
    max_scale = 0.0
    actual_snapshot = []
    for instance_index, expected in enumerate(expected_snapshot):
        actual = transform_values(
            component.get_instance_transform(instance_index, world_space=True)
        )
        actual_snapshot.append(actual)
        translation_error = math.sqrt(
            sum((actual[index] - expected[index]) ** 2 for index in range(3))
        )
        scale_error = math.sqrt(
            sum((actual[index] - expected[index]) ** 2 for index in range(7, 10))
        )
        left_norm = math.sqrt(sum(expected[index] ** 2 for index in range(3, 7)))
        right_norm = math.sqrt(sum(actual[index] ** 2 for index in range(3, 7)))
        dot = abs(
            sum(expected[index] * actual[index] for index in range(3, 7))
        )
        if left_norm > 0.0 and right_norm > 0.0:
            dot = max(0.0, min(1.0, dot / (left_norm * right_norm)))
            rotation_error = math.degrees(2.0 * math.acos(dot))
        else:
            rotation_error = 180.0
        max_translation = max(max_translation, translation_error)
        max_rotation = max(max_rotation, rotation_error)
        max_scale = max(max_scale, scale_error)
    return {
        "matches": (
            max_translation <= 0.01
            and max_rotation <= 0.001
            and max_scale <= 0.00001
        ),
        "expected_count": len(expected_snapshot),
        "actual_count": actual_count,
        "max_translation_error": max_translation,
        "max_rotation_error_degrees": max_rotation,
        "max_scale_error": max_scale,
        "actual_digest": transform_digest(actual_snapshot),
    }


def collect_sandbox_batches(actor_subsystem, mappings):
    expected_by_mesh = {
        object_path(mapping["batch_mesh"]): mapping for mapping in mappings
    }
    result = {}
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        try:
            component = foliage_component(actor)
        except RuntimeError:
            continue
        mesh_path = object_path(component.get_editor_property("static_mesh"))
        mapping = expected_by_mesh.get(mesh_path)
        if not mapping:
            continue
        if mesh_path in result:
            raise RuntimeError("Duplicate sandbox foliage mesh actor: " + mesh_path)
        instance_count = int(component.get_instance_count())
        expected_instances = int(mapping["source"]["instance_count"])
        if instance_count != expected_instances:
            raise RuntimeError(
                "Sandbox foliage instance mismatch for {}: expected={} actual={}".format(
                    mapping["key"], expected_instances, instance_count
                )
            )
        snapshot = component_transform_snapshot(component)
        result[mesh_path] = {
            "actor": actor,
            "component": component,
            "instance_count": instance_count,
            "instance_world_transforms": snapshot,
            "instance_transform_digest": transform_digest(snapshot),
        }
    if len(result) != EXPECTED_BATCH_COUNT:
        raise RuntimeError(
            "Corrected foliage sandbox has {} mapped HISM actors".format(len(result))
        )
    if sum(item["instance_count"] for item in result.values()) != EXPECTED_INSTANCE_COUNT:
        raise RuntimeError("Corrected foliage sandbox instance total mismatch")
    return result


def actor_index(actors):
    result = {}
    for actor in actors:
        label = actor.get_actor_label()
        if label.startswith(LABEL_PREFIX):
            if label in result:
                raise RuntimeError("Duplicate foliage actor label: " + label)
            result[label] = actor
    return result


def distance(left, right):
    return math.sqrt(
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def rotator_error(left, right):
    values = []
    for left_value, right_value in (
        (left.pitch, right.pitch),
        (left.yaw, right.yaw),
        (left.roll, right.roll),
    ):
        delta = (float(left_value) - float(right_value) + 180.0) % 360.0 - 180.0
        values.append(abs(delta))
    return max(values)


def configure_foliage_actor(actor, mapping):
    source = mapping["source"]
    actor.set_actor_label(label_for(source), mark_dirty=True)
    set_actor_folder(actor, folder_for(source))
    component = foliage_component(actor)
    for slot_index, material in enumerate(mapping["assigned_materials"]):
        component.set_material(slot_index, material)
    return component


def duplicate_sandbox_batches(actor_subsystem, mappings, sandbox_batches):
    target_world = unreal.EditorAssetLibrary.load_asset(MAP_PATH)
    if not target_world:
        raise RuntimeError("Could not load HeinMach target world for duplication")
    source_actors = [
        sandbox_batches[object_path(mapping["batch_mesh"])]["actor"]
        for mapping in sorted(mappings, key=lambda row: row["key"])
    ]
    duplicated = list(
        actor_subsystem.duplicate_actors(
            source_actors, to_world=target_world, offset=unreal.Vector(0.0, 0.0, 0.0)
        )
    )
    if len(duplicated) != EXPECTED_BATCH_COUNT:
        raise RuntimeError(
            "Cross-world foliage duplication returned {} actors".format(len(duplicated))
        )
    duplicated_by_mesh = {}
    for actor in duplicated:
        component = foliage_component(actor)
        mesh_path = object_path(component.get_editor_property("static_mesh"))
        if mesh_path in duplicated_by_mesh:
            raise RuntimeError("Duplicated foliage mesh is not unique: " + mesh_path)
        duplicated_by_mesh[mesh_path] = actor

    for mapping in mappings:
        mesh_path = object_path(mapping["batch_mesh"])
        actor = duplicated_by_mesh.get(mesh_path)
        if not actor:
            raise RuntimeError("Duplicated foliage actor missing mesh: " + mesh_path)
        component = configure_foliage_actor(actor, mapping)
        expected = sandbox_batches[mesh_path]
        if int(component.get_instance_count()) != expected["instance_count"]:
            raise RuntimeError("Duplicated HISM instance count changed: " + mesh_path)
        comparison = compare_component_transforms(
            component, expected["instance_world_transforms"]
        )
        expected["duplicate_transform_comparison"] = comparison
        if not comparison["matches"]:
            raise RuntimeError(
                "Duplicated HISM transforms changed: {} comparison={}".format(
                    mesh_path, json.dumps(comparison, sort_keys=True)
                )
            )

    if not unreal.EditorAssetLibrary.save_asset(MAP_PATH, only_if_is_dirty=False):
        raise RuntimeError("Failed to save foliage-restored target map asset")
    return duplicated


def validate_main_map(actor_subsystem, mappings, sandbox_batches):
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    index = actor_index(actors)
    mesh_mismatches = []
    instance_count_mismatches = []
    instance_transform_mismatches = []
    actor_transform_mismatches = []
    material_mismatches = []
    result_rows = []
    total_instances = 0
    for mapping in sorted(mappings, key=lambda row: row["key"]):
        source = mapping["source"]
        batch = mapping["batch"]
        label = label_for(source)
        actor = index.get(label)
        if not actor:
            mesh_mismatches.append({"label": label, "reason": "missing actor"})
            continue
        component = foliage_component(actor)
        mesh_path = object_path(component.get_editor_property("static_mesh"))
        expected_mesh_path = object_path(mapping["batch_mesh"])
        if mesh_path != expected_mesh_path:
            mesh_mismatches.append(
                {"label": label, "expected": expected_mesh_path, "actual": mesh_path}
            )
            continue
        actual_instances = int(component.get_instance_count())
        expected_instances = int(source["instance_count"])
        total_instances += actual_instances
        if actual_instances != expected_instances:
            instance_count_mismatches.append(
                {
                    "label": label,
                    "expected": expected_instances,
                    "actual": actual_instances,
                }
            )
        transform_comparison = compare_component_transforms(
            component,
            sandbox_batches[expected_mesh_path]["instance_world_transforms"],
        )
        actual_digest = transform_comparison.get("actual_digest")
        if not transform_comparison["matches"]:
            instance_transform_mismatches.append(
                {"label": label, "comparison": transform_comparison}
            )

        expected_location = vector(batch["location"])
        expected_rotation = rotator(batch["rotation"])
        expected_scale = vector(batch["scale"], default=1.0)
        if (
            distance(actor.get_actor_location(), expected_location) > 0.001
            or rotator_error(actor.get_actor_rotation(), expected_rotation) > 0.0001
            or distance(actor.get_actor_scale3d(), expected_scale) > 0.00001
        ):
            actor_transform_mismatches.append(label)

        expected_materials = [
            object_path(material) for material in mapping["assigned_materials"]
        ]
        actual_materials = [object_path(item) for item in component.get_materials()]
        if actual_materials[: len(expected_materials)] != expected_materials:
            material_mismatches.append(
                {
                    "label": label,
                    "expected": expected_materials,
                    "actual": actual_materials,
                }
            )
        result_rows.append(
            {
                "label": label,
                "source_layer": source["layer"],
                "point_instancer": source["point_instancer"],
                "prototype": source["prototype_basename"],
                "instance_count": actual_instances,
                "instance_transform_digest": actual_digest,
                "instance_transform_comparison": transform_comparison,
                "source_mesh": object_path(mapping["source_mesh"]),
                "batch_mesh": expected_mesh_path,
                "source_vertex_count": mapping["source_vertex_count"],
                "batch_vertex_count": mapping["batch_vertex_count"],
                "materials": actual_materials,
            }
        )
    return {
        "actors": actors,
        "index": index,
        "total_instance_count": total_instances,
        "mesh_mismatches": mesh_mismatches,
        "instance_count_mismatches": instance_count_mismatches,
        "instance_transform_mismatches": instance_transform_mismatches,
        "actor_transform_mismatches": actor_transform_mismatches,
        "material_mismatches": material_mismatches,
        "batches": result_rows,
    }


def main():
    import_report = load_json(IMPORT_REPORT_PATH)
    if import_report.get("status") not in ("imported", "skipped_existing_valid"):
        raise RuntimeError("Foliage batch import report is not valid")
    if import_report.get("sandbox_map_path") != SANDBOX_MAP_PATH:
        raise RuntimeError("Foliage import report points to an unexpected sandbox map")

    source_meshes = corrected_source_mesh_index()
    mappings, prototype_vertex_counts, requirements = build_mappings(
        import_report, source_meshes
    )
    material_results = repair_assigned_materials(mappings)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_path = current_world.get_path_name().split(".")[0] if current_world else None
    if current_path != SANDBOX_MAP_PATH:
        if not level_subsystem.load_level(SANDBOX_MAP_PATH):
            raise RuntimeError("Failed to load corrected foliage sandbox")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sandbox_batches = collect_sandbox_batches(actor_subsystem, mappings)
    backup_created = backup_map_once()
    duplicated = duplicate_sandbox_batches(actor_subsystem, mappings, sandbox_batches)
    created_count = len(duplicated)
    del duplicated

    baseline_rows = []
    for mapping in sorted(mappings, key=lambda row: row["key"]):
        mesh_path = object_path(mapping["batch_mesh"])
        sandbox = sandbox_batches[mesh_path]
        baseline_rows.append(
            {
                "label": label_for(mapping["source"]),
                "mesh_path": mesh_path,
                "instance_count": sandbox["instance_count"],
                "instance_transform_digest": sandbox[
                    "instance_transform_digest"
                ],
                "instance_world_transforms": sandbox[
                    "instance_world_transforms"
                ],
            }
        )
    write_json(
        BASELINE_PATH,
        {
            "status": "baseline_saved",
            "batch_count": len(baseline_rows),
            "instance_count": sum(
                row["instance_count"] for row in baseline_rows
            ),
            "batches": baseline_rows,
        },
    )

    prototype_rows = []
    for prototype_name in sorted(prototype_vertex_counts):
        mapping = next(
            row
            for row in mappings
            if row["source"]["prototype_basename"] == prototype_name
        )
        requirement = requirements[prototype_name]
        prototype_rows.append(
            {
                "prototype": prototype_name,
                "batch_count": sum(
                    row["source"]["prototype_basename"] == prototype_name
                    for row in mappings
                ),
                "instance_count": sum(
                    int(row["source"]["instance_count"])
                    for row in mappings
                    if row["source"]["prototype_basename"] == prototype_name
                ),
                "batch_vertex_count": next(
                    iter(prototype_vertex_counts[prototype_name])
                ),
                "corrected_source_mesh": object_path(mapping["source_mesh"]),
                "corrected_source_vertex_count": mapping["source_vertex_count"],
                "corrected_source_vertex_matches": mapping[
                    "corrected_source_vertex_matches"
                ],
                "material_name": requirement["material_name"],
                "material_json_path": requirement["material_json_path"],
                "two_sided": requirement["two_sided"],
                "blend_mode": str(requirement["blend_mode"]),
                "opacity_mask_clip_value": requirement[
                    "opacity_mask_clip_value"
                ],
            }
        )

    report = {
        "status": "transferred_pending_reload_validation",
        "map_path": MAP_PATH,
        "sandbox_map_path": SANDBOX_MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "transform_baseline_path": BASELINE_PATH,
        "source_batch_count": len(mappings),
        "source_instance_count": EXPECTED_INSTANCE_COUNT,
        "prototype_count": len(prototype_rows),
        "corrected_source_crosscheck_count": sum(
            row["corrected_source_mesh"] is not None for row in prototype_rows
        ),
        "prototype_vertex_consistency_mismatch_count": sum(
            len(values) != 1 for values in prototype_vertex_counts.values()
        ),
        "sandbox_batch_count": len(sandbox_batches),
        "sandbox_instance_count": sum(
            item["instance_count"] for item in sandbox_batches.values()
        ),
        "created_actor_count": created_count,
        "reused_actor_count": 0,
        "transferred_batch_actor_count": created_count,
        "transferred_instance_count": sum(
            item["instance_count"] for item in sandbox_batches.values()
        ),
        "material_surface_validation_count": len(material_results),
        "material_surface_mismatch_count": sum(
            not row["matches"] for row in material_results
        ),
        "cross_world_transform_comparisons": [
            {
                "mesh_path": mesh_path,
                "comparison": sandbox_batches[mesh_path].get(
                    "duplicate_transform_comparison"
                ),
            }
            for mesh_path in sorted(sandbox_batches)
        ],
        "prototype_validation": prototype_rows,
        "material_surface_validation": material_results,
    }
    write_json(REPORT_PATH, report)
    log(
        "TRANSFER status={} batches={} instances={} created={} report={}".format(
            report["status"],
            report["transferred_batch_actor_count"],
            report["transferred_instance_count"],
            created_count,
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
        error(str(exception))
        error(failure["traceback"])
        raise
