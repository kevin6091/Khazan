"""Repair white VFS tree branch cards caused by a null FModel LOD export.

FModel exported ``WM_VFS_Tree_Branch_001_LOD2`` as ``IsNull: true`` with no
textures, while retaining the source Masked/TwoSided surface policy.  USD then
created opaque white placeholder materials for the branch-card slot.  The
non-LOD material from the exact same source family contains the authoritative
branch diffuse/normal/specular textures, so a dedicated recovered copy is used
for only the affected slots.
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_WhiteTreeMaterial_Repair.json",
)
SOURCE_NULL_JSON = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "BBQ",
    "Content",
    "Art",
    "World",
    "World_Material",
    "Prop",
    "Material",
    "WM_VFS_Tree_Branch_001_LOD2.json",
)
SOURCE_TEXTURED_JSON = os.path.join(
    os.path.dirname(SOURCE_NULL_JSON), "WM_VFS_Tree_Branch_001_02.json"
)
MATERIAL_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/"
    "HeinMach_StaticMeshLibrary_Corrected/Materials"
)
TEXTURED_SIBLING_PATH = MATERIAL_ROOT + "/MI_WM_VFS_Tree_Branch_001_02"
RECOVERED_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/RecoveredMaterials/Trees"
)
RECOVERED_PATH = RECOVERED_ROOT + "/MI_WM_VFS_Tree_Branch_001_LOD2_Recovered"
SUSPICIOUS_MATERIAL_PATHS = {
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Branch_001_LOD",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Branch_001_LOD_0",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Branch_001_LOD2",
}
TREE_MESH_NAMES = {
    "SM_WP_VFS_Tree_Dry_004",
    "SM_WP_VFS_Tree_Dry_005",
    "SM_WP_VFS_Tree_Dry_006",
}


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(value):
    return value.get_path_name() if value else None


def normalized_asset_path(value):
    return str(value).rsplit(".", 1)[0] if value else None


def texture_value(material, parameter):
    try:
        value = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            material, parameter
        )
        return object_path(value)
    except Exception:
        return None


def scalar_value(material, parameter):
    try:
        return unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            material, parameter
        )
    except Exception:
        return None


def transform_signature(actors):
    records = []
    for actor in actors:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        records.append(
            {
                "label": actor.get_actor_label(),
                "location": [location.x, location.y, location.z],
                "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
                "scale": [scale.x, scale.y, scale.z],
            }
        )
    records.sort(key=lambda item: item["label"])
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def affected_slots(actor_subsystem):
    slots = []
    tree_actor_labels = set()
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            if not mesh or mesh.get_name() not in TREE_MESH_NAMES:
                continue
            tree_actor_labels.add(actor.get_actor_label())
            for slot_index in range(component.get_num_materials()):
                material = component.get_material(slot_index)
                material_path = normalized_asset_path(object_path(material))
                if material_path in SUSPICIOUS_MATERIAL_PATHS:
                    slots.append(
                        {
                            "actor": actor,
                            "component": component,
                            "slot_index": slot_index,
                            "material": material,
                            "record": {
                                "actor_label": actor.get_actor_label(),
                                "component_path": component.get_path_name(),
                                "mesh": mesh.get_path_name(),
                                "slot_index": slot_index,
                                "material_before": object_path(material),
                            },
                        }
                    )
    return slots, tree_actor_labels


def material_evidence(material):
    parent = None
    try:
        value = material.get_editor_property("parent") if material else None
        parent = object_path(value)
    except Exception:
        pass
    return {
        "path": object_path(material),
        "parent": parent,
        "base_color_texture": texture_value(material, "BaseColorTexture") if material else None,
        "opacity_texture": texture_value(material, "OpacityTexture") if material else None,
        "normal_texture": texture_value(material, "NormalTexture") if material else None,
        "roughness_texture": texture_value(material, "RoughnessTexture") if material else None,
        "use_base_color_texture": scalar_value(material, "UseBaseColorTexture") if material else None,
        "use_opacity_texture": scalar_value(material, "UseOpacityTexture") if material else None,
    }


def load_level_if_needed():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    return level_subsystem


def ensure_recovered_material():
    material = unreal.EditorAssetLibrary.load_asset(RECOVERED_PATH)
    created = False
    if not material:
        if not unreal.EditorAssetLibrary.does_asset_exist(TEXTURED_SIBLING_PATH):
            raise RuntimeError("Textured branch sibling material is missing")
        if not unreal.EditorAssetLibrary.duplicate_asset(
            TEXTURED_SIBLING_PATH, RECOVERED_PATH
        ):
            raise RuntimeError("Failed to create recovered tree branch material")
        material = unreal.EditorAssetLibrary.load_asset(RECOVERED_PATH)
        created = True
    if not material:
        raise RuntimeError("Recovered tree branch material did not load")
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanSourceMaterial", "WM_VFS_Tree_Branch_001_LOD2"
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material,
        "KhazanRecoveryReason",
        "FModel USD exported inherited LOD material as IsNull with no textures",
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanTextureFallback", "WM_VFS_Tree_Branch_001_02"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    evidence = material_evidence(material)
    if (
        not evidence["base_color_texture"]
        or "WhiteSquareTexture" in evidence["base_color_texture"]
        or float(evidence["use_base_color_texture"] or 0.0) < 0.5
    ):
        raise RuntimeError("Recovered material still lacks a real base-color texture")
    return material, created, evidence


def main(apply_changes=False):
    null_source = load_json(SOURCE_NULL_JSON)
    textured_source = load_json(SOURCE_TEXTURED_JSON)
    null_parameters = null_source.get("Parameters", {})
    textured_textures = textured_source.get("Textures", {})
    source_evidence = {
        "null_lod_json": SOURCE_NULL_JSON,
        "null_lod_is_null": bool(null_parameters.get("IsNull")),
        "null_lod_texture_count": len(null_source.get("Textures", {})),
        "null_lod_base_property_overrides": (
            null_parameters.get("Properties", {}).get("BasePropertyOverrides", {})
        ),
        "textured_sibling_json": SOURCE_TEXTURED_JSON,
        "textured_sibling_texture_count": len(textured_textures),
        "textured_sibling_textures": textured_textures,
    }
    if (
        not source_evidence["null_lod_is_null"]
        or source_evidence["null_lod_texture_count"] != 0
        or "Tex_D" not in textured_textures
    ):
        raise RuntimeError("Tree material source evidence changed")

    level_subsystem = load_level_if_needed()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    slots_before, tree_actor_labels = affected_slots(actor_subsystem)
    affected_actors = sorted(
        {slot["actor"] for slot in slots_before}, key=lambda actor: actor.get_actor_label()
    )
    transform_before = transform_signature(affected_actors)
    before_materials = {}
    for slot in slots_before:
        path = object_path(slot["material"])
        if path not in before_materials:
            before_materials[path] = material_evidence(slot["material"])

    repaired = []
    recovered_created = False
    recovered_evidence = None
    if apply_changes and slots_before:
        recovered, recovered_created, recovered_evidence = ensure_recovered_material()
        for slot in slots_before:
            slot["component"].set_material(slot["slot_index"], recovered)
            record = dict(slot["record"])
            record["material_after"] = recovered.get_path_name()
            repaired.append(record)
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save white-tree material repair")
        unreal.EditorAssetLibrary.save_directory(
            RECOVERED_ROOT, only_if_is_dirty=False, recursive=True
        )

    slots_after, _ = affected_slots(actor_subsystem)
    affected_after = sorted(
        {slot["actor"] for slot in slots_before}, key=lambda actor: actor.get_actor_label()
    )
    transform_after = transform_signature(affected_after)
    if apply_changes and transform_after != transform_before:
        raise RuntimeError("Tree actor transforms changed during material repair")
    if apply_changes and slots_after:
        raise RuntimeError("White placeholder tree materials remain after repair")

    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "source_evidence": source_evidence,
        "decision": (
            "The white result is not source-authored snow coloration. It is the USD fallback "
            "for a null/inherited LOD material; use the textured sibling from the same family."
        ),
        "tree_scope": {
            "mesh_names": sorted(TREE_MESH_NAMES),
            "tree_actor_count_in_scope": len(tree_actor_labels),
            "suspicious_material_paths": sorted(SUSPICIOUS_MATERIAL_PATHS),
        },
        "counts": {
            "affected_slot_before": len(slots_before),
            "affected_actor_before": len(affected_actors),
            "repaired_slot": len(repaired),
            "affected_slot_after": len(slots_after),
        },
        "affected_slots_before": [slot["record"] for slot in slots_before],
        "placeholder_material_evidence": list(before_materials.values()),
        "recovered_material": recovered_evidence,
        "recovered_material_created": recovered_created,
        "repaired_slots": repaired,
        "affected_transform_before": transform_before,
        "affected_transform_after": transform_after,
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    try:
        main(False)
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        raise
