"""Repair the remaining bright-white VFS tree trunk LOD slots in HeinMach.

``WM_VFS_Tree_Dry_001_LOD1`` is not a null export, but it contains only a
bright wood detail map and relies on the unavailable proprietary master
material's vertex/detail composition.  The reconstructed preview parent treats
that detail map as BaseColor, making meshes 004-010 render plain white.  A
dedicated recovered material uses the authored full-resolution diffuse,
normal, and specular textures from the exact VFS Tree Dry 001 family.
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
    "HeinMach_RemainingWhiteTreeMaterial_Repair.json",
)
USER_EXCLUSION_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_UserExclusions.json",
)
SOURCE_MATERIAL_ROOT = os.path.join(
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
)
SOURCE_LOD_JSON = os.path.join(SOURCE_MATERIAL_ROOT, "WM_VFS_Tree_Dry_001_LOD1.json")
SOURCE_TEXTURED_JSON = os.path.join(SOURCE_MATERIAL_ROOT, "WM_VFS_Tree_Dry_001.json")

MATERIAL_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/"
    "HeinMach_StaticMeshLibrary_Corrected/Materials"
)
TEXTURED_SIBLING_PATH = MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001"
RECOVERED_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/RecoveredMaterials/Trees"
)
RECOVERED_PATH = RECOVERED_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD1_Recovered"
SUSPICIOUS_MATERIAL_PATHS = {
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD_0",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD_1",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD_2",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD_3",
    MATERIAL_ROOT + "/MI_WM_VFS_Tree_Dry_001_LOD1",
}
TREE_MESH_NAMES = {
    "SM_WP_VFS_Tree_Dry_004",
    "SM_WP_VFS_Tree_Dry_005",
    "SM_WP_VFS_Tree_Dry_006",
    "SM_WP_VFS_Tree_Dry_007",
    "SM_WP_VFS_Tree_Dry_008",
    "SM_WP_VFS_Tree_Dry_009",
    "SM_WP_VFS_Tree_Dry_010",
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


def material_evidence(material):
    parent = None
    try:
        parent = object_path(material.get_editor_property("parent")) if material else None
    except Exception:
        pass
    return {
        "path": object_path(material),
        "parent": parent,
        "base_color_texture": texture_value(material, "BaseColorTexture") if material else None,
        "normal_texture": texture_value(material, "NormalTexture") if material else None,
        "roughness_texture": texture_value(material, "RoughnessTexture") if material else None,
        "opacity_texture": texture_value(material, "OpacityTexture") if material else None,
        "use_base_color_texture": scalar_value(material, "UseBaseColorTexture") if material else None,
        "use_normal_texture": scalar_value(material, "UseNormalTexture") if material else None,
        "use_opacity_texture": scalar_value(material, "UseOpacityTexture") if material else None,
    }


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
            for slot_index in range(component.get_num_materials()):
                material = component.get_material(slot_index)
                material_path = normalized_asset_path(object_path(material))
                if material_path not in SUSPICIOUS_MATERIAL_PATHS:
                    continue
                tree_actor_labels.add(actor.get_actor_label())
                instance_count = None
                if isinstance(component, unreal.InstancedStaticMeshComponent):
                    try:
                        instance_count = component.get_instance_count()
                    except Exception:
                        pass
                slots.append(
                    {
                        "actor": actor,
                        "component": component,
                        "slot_index": slot_index,
                        "material": material,
                        "record": {
                            "actor_label": actor.get_actor_label(),
                            "component_path": component.get_path_name(),
                            "component_class": component.get_class().get_name(),
                            "instance_count": instance_count,
                            "mesh": mesh.get_path_name(),
                            "slot_index": slot_index,
                            "material_before": object_path(material),
                        },
                    }
                )
    return slots, tree_actor_labels


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
            raise RuntimeError("Textured VFS Tree Dry sibling material is missing")
        if not unreal.EditorAssetLibrary.duplicate_asset(TEXTURED_SIBLING_PATH, RECOVERED_PATH):
            raise RuntimeError("Failed to create recovered VFS trunk material")
        material = unreal.EditorAssetLibrary.load_asset(RECOVERED_PATH)
        created = True
    if not material:
        raise RuntimeError("Recovered VFS trunk material did not load")
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanSourceMaterial", "WM_VFS_Tree_Dry_001_LOD1"
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material,
        "KhazanRecoveryReason",
        "LOD detail-only material requires unavailable proprietary vertex/detail composition",
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanTextureFallback", "WM_VFS_Tree_Dry_001"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    evidence = material_evidence(material)
    if (
        not evidence["base_color_texture"]
        or "WT_VFS_Tree_Dry_001_D" not in evidence["base_color_texture"]
        or float(evidence["use_base_color_texture"] or 0.0) < 0.5
    ):
        raise RuntimeError("Recovered VFS trunk material lacks the authored trunk diffuse")
    return material, created, evidence


def exclusion_evidence(actor_subsystem):
    payload = load_json(USER_EXCLUSION_PATH)
    labels = {
        actor.get_actor_label()
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }
    expected_absent = sorted(
        {
            record["label"]
            for record in payload.get("exclusions", [])
            if record.get("do_not_restore") and record.get("label")
        }
    )
    unexpectedly_present = sorted(set(expected_absent) & labels)
    return {
        "expected_absent_count": len(expected_absent),
        "unexpectedly_present_count": len(unexpectedly_present),
        "unexpectedly_present": unexpectedly_present,
    }


def main(apply_changes=False):
    lod_source = load_json(SOURCE_LOD_JSON)
    textured_source = load_json(SOURCE_TEXTURED_JSON)
    lod_textures = lod_source.get("Textures", {})
    textured_textures = textured_source.get("Textures", {})
    source_evidence = {
        "lod_json": SOURCE_LOD_JSON,
        "lod_is_null": bool(lod_source.get("Parameters", {}).get("IsNull")),
        "lod_textures": lod_textures,
        "lod_has_full_diffuse": "Tex_D" in lod_textures,
        "lod_pm_diffuse": lod_textures.get("PM_Diffuse"),
        "textured_sibling_json": SOURCE_TEXTURED_JSON,
        "textured_sibling_tex_d": textured_textures.get("Tex_D"),
        "textured_sibling_tex_n": textured_textures.get("Tex_N"),
        "textured_sibling_tex_s": textured_textures.get("Tex_S"),
    }
    if (
        source_evidence["lod_is_null"]
        or source_evidence["lod_has_full_diffuse"]
        or "WT_DetailMap_Wood_01_D" not in str(source_evidence["lod_pm_diffuse"])
        or "WT_VFS_Tree_Dry_001_D" not in str(source_evidence["textured_sibling_tex_d"])
    ):
        raise RuntimeError("Remaining white-tree source evidence changed")

    level_subsystem = load_level_if_needed()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor_count_before = len(actor_subsystem.get_all_level_actors())
    exclusions_before = exclusion_evidence(actor_subsystem)
    if exclusions_before["unexpectedly_present_count"]:
        raise RuntimeError("A user-deleted HeinMach actor is unexpectedly present")

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
            raise RuntimeError("Failed to save remaining white-tree material repair")
        unreal.EditorAssetLibrary.save_directory(
            RECOVERED_ROOT, only_if_is_dirty=False, recursive=True
        )

    slots_after, _ = affected_slots(actor_subsystem)
    transform_after = transform_signature(affected_actors)
    actor_count_after = len(actor_subsystem.get_all_level_actors())
    exclusions_after = exclusion_evidence(actor_subsystem)
    if apply_changes and transform_after != transform_before:
        raise RuntimeError("VFS tree actor transforms changed during material repair")
    if apply_changes and slots_after:
        raise RuntimeError("Bright detail-only VFS trunk slots remain after repair")
    if actor_count_after != actor_count_before:
        raise RuntimeError("Actor count changed during material-only repair")
    if exclusions_after["unexpectedly_present_count"]:
        raise RuntimeError("A user-deleted HeinMach actor was restored")

    affected_instance_count = sum(
        max(1, int(slot["record"].get("instance_count") or 1)) for slot in slots_before
    )
    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "source_evidence": source_evidence,
        "decision": (
            "The remaining white VFS trunks are not authored white paint. The source LOD1 "
            "material supplies only a bright detail texture and depends on an unavailable "
            "proprietary vertex/detail composition. Use the full diffuse/normal/specular "
            "textures from the exact VFS Tree Dry 001 family for the reconstructed preview."
        ),
        "tree_scope": {
            "mesh_names": sorted(TREE_MESH_NAMES),
            "tree_actor_count_in_scope": len(tree_actor_labels),
            "suspicious_material_paths": sorted(SUSPICIOUS_MATERIAL_PATHS),
        },
        "counts": {
            "actor_count_before": actor_count_before,
            "actor_count_after": actor_count_after,
            "affected_component_slot_before": len(slots_before),
            "affected_actor_before": len(affected_actors),
            "affected_render_instance_before": affected_instance_count,
            "repaired_component_slot": len(repaired),
            "affected_component_slot_after": len(slots_after),
        },
        "user_exclusions_before": exclusions_before,
        "user_exclusions_after": exclusions_after,
        "affected_slots_before": [slot["record"] for slot in slots_before],
        "detail_only_material_evidence": list(before_materials.values()),
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
