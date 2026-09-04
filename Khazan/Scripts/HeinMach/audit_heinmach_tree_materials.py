"""Read-only material audit for every tree-like mesh in the HeinMach art map.

The earlier white-tree repair intentionally covered one known VFS branch LOD
family.  This audit broadens discovery to all live static-mesh and foliage
components whose mesh name looks tree-related, and records effective material
textures before any further material is changed.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
MAP_FILE = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Maps",
    "L_HeinMach_Environment.umap",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_TreeMaterial_FullAudit.json",
)

TREE_TOKENS = (
    "tree",
    "branch",
    "trunk",
    "stump",
    "thorn",
    "sapling",
)
DEFAULT_TEXTURE_TOKENS = (
    "whitesquaretexture",
    "blacktexture",
    "defaultnormal",
    "defaultdiffuse",
    "defaulttexture",
    "/engine/engine",
)
DEFAULT_MATERIAL_TOKENS = (
    "worldgridmaterial",
    "defaultmaterial",
)
BASE_COLOR_PARAMETER_TOKENS = (
    "basecolor",
    "base_color",
    "diffuse",
    "tex_d",
    "pm_diffuse",
    "albedo",
)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(value):
    return value.get_path_name() if value else None


def normalized_asset_path(value):
    return str(value).rsplit(".", 1)[0] if value else None


def safe_material_textures(material):
    if not material:
        return [], {}, []
    library = unreal.MaterialEditingLibrary
    try:
        used = sorted(
            {
                object_path(texture)
                for texture in library.get_material_used_textures(material)
                if texture
            }
        )
    except Exception:
        used = []
    parameter_values = {}
    parameter_errors = []
    try:
        names = list(library.get_texture_parameter_names(material))
    except Exception as exception:
        names = []
        parameter_errors.append("texture_parameter_names: " + str(exception))
    for name in names:
        key = str(name)
        try:
            value = library.get_material_instance_texture_parameter_value(material, name)
            parameter_values[key] = object_path(value)
        except Exception as exception:
            parameter_values[key] = None
            parameter_errors.append(key + ": " + str(exception))
    return used, parameter_values, parameter_errors


def safe_scalar_parameters(material):
    if not material:
        return {}
    library = unreal.MaterialEditingLibrary
    values = {}
    try:
        names = list(library.get_scalar_parameter_names(material))
    except Exception:
        return values
    for name in names:
        key = str(name)
        lowered = key.lower()
        if not any(token in lowered for token in ("use", "base", "diff", "opacity")):
            continue
        try:
            values[key] = library.get_material_instance_scalar_parameter_value(material, name)
        except Exception:
            values[key] = None
    return values


def is_default_texture(path):
    lowered = str(path or "").lower()
    return not path or any(token in lowered for token in DEFAULT_TEXTURE_TOKENS)


def material_record(material):
    path = object_path(material)
    normalized_path = normalized_asset_path(path)
    parent = None
    if material:
        try:
            parent = object_path(material.get_editor_property("parent"))
        except Exception:
            pass
    used, texture_parameters, parameter_errors = safe_material_textures(material)
    scalars = safe_scalar_parameters(material)
    real_used = [path for path in used if not is_default_texture(path)]
    base_parameters = {
        name: value
        for name, value in texture_parameters.items()
        if any(token in name.lower() for token in BASE_COLOR_PARAMETER_TOKENS)
    }
    real_base_parameters = {
        name: value
        for name, value in base_parameters.items()
        if value and not is_default_texture(value)
    }
    disabled_base_switches = {
        name: value
        for name, value in scalars.items()
        if (
            any(token in name.lower() for token in ("usebase", "use_base", "usediff", "use_diff"))
            and value is not None
            and float(value) < 0.5
        )
    }
    flags = []
    if not material:
        flags.append("missing_material")
    if any(token in str(path or "").lower() for token in DEFAULT_MATERIAL_TOKENS):
        flags.append("default_material")
    if material and not used:
        flags.append("no_used_textures")
    if used and not real_used:
        flags.append("only_default_textures")
    if base_parameters and not real_base_parameters:
        flags.append("no_real_base_color_parameter")
    if disabled_base_switches:
        flags.append("base_color_texture_switch_disabled")
    # Imported tree materials without any texture parameter or used texture are
    # strong white-fallback candidates even if the parent material compiles.
    if material and not texture_parameters and not real_used:
        flags.append("untextured_tree_material")
    return {
        "path": path,
        "normalized_path": normalized_path,
        "class": material.get_class().get_name() if material else None,
        "parent": parent,
        "used_textures": used,
        "real_used_textures": real_used,
        "texture_parameters": texture_parameters,
        "base_color_parameters": base_parameters,
        "real_base_color_parameters": real_base_parameters,
        "relevant_scalar_parameters": scalars,
        "disabled_base_color_switches": disabled_base_switches,
        "parameter_errors": parameter_errors,
        "flags": sorted(set(flags)),
    }


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    material_cache = {}
    usage = collections.defaultdict(
        lambda: {
            "component_count": 0,
            "slot_usage_count": 0,
            "actor_labels": set(),
            "component_classes": set(),
            "mesh_paths": set(),
            "slot_indices": set(),
        }
    )
    tree_components = 0
    tree_actors = set()
    slot_records = []

    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            mesh_path = object_path(mesh)
            mesh_name = mesh.get_name() if mesh else ""
            candidate = (mesh_name + " " + str(mesh_path or "")).lower()
            if not mesh or not any(token in candidate for token in TREE_TOKENS):
                continue
            tree_components += 1
            actor_label = actor.get_actor_label()
            tree_actors.add(actor_label)
            component_path = component.get_path_name()
            component_class = component.get_class().get_name()
            instance_count = None
            if isinstance(component, unreal.InstancedStaticMeshComponent):
                try:
                    instance_count = component.get_instance_count()
                except Exception:
                    pass
            for slot_index in range(component.get_num_materials()):
                material = component.get_material(slot_index)
                key = object_path(material) or "<None>"
                if key not in material_cache:
                    material_cache[key] = material_record(material)
                evidence = material_cache[key]
                usage_record = usage[key]
                usage_record["component_count"] += 1
                usage_record["slot_usage_count"] += max(1, int(instance_count or 1))
                usage_record["actor_labels"].add(actor_label)
                usage_record["component_classes"].add(component_class)
                usage_record["mesh_paths"].add(mesh_path)
                usage_record["slot_indices"].add(slot_index)
                slot_records.append(
                    {
                        "actor_label": actor_label,
                        "component_path": component_path,
                        "component_class": component_class,
                        "instance_count": instance_count,
                        "mesh": mesh_path,
                        "slot_index": slot_index,
                        "material": key,
                        "flags": evidence["flags"],
                    }
                )

    material_groups = []
    for key in sorted(usage):
        record = usage[key]
        evidence = material_cache[key]
        material_groups.append(
            {
                "material": evidence,
                "usage": {
                    "component_count": record["component_count"],
                    "slot_or_instance_usage_count": record["slot_usage_count"],
                    "actor_count": len(record["actor_labels"]),
                    "actor_labels": sorted(record["actor_labels"]),
                    "component_classes": sorted(record["component_classes"]),
                    "mesh_paths": sorted(record["mesh_paths"]),
                    "slot_indices": sorted(record["slot_indices"]),
                },
            }
        )

    suspicious_groups = [group for group in material_groups if group["material"]["flags"]]
    suspicious_slots = [record for record in slot_records if record["flags"]]
    map_hash = None
    if os.path.isfile(MAP_FILE):
        with open(MAP_FILE, "rb") as source:
            map_hash = hashlib.sha256(source.read()).hexdigest().upper()
    report = {
        "status": "audited",
        "map_path": MAP_PATH,
        "map_sha256": map_hash,
        "discovery_policy": {
            "tree_tokens": list(TREE_TOKENS),
            "default_texture_tokens": list(DEFAULT_TEXTURE_TOKENS),
            "note": "Flags identify evidence candidates; source-family JSON decides whether a material is repaired.",
        },
        "counts": {
            "tree_actor_count": len(tree_actors),
            "tree_component_count": tree_components,
            "tree_material_slot_count": len(slot_records),
            "unique_tree_material_count": len(material_groups),
            "suspicious_material_group_count": len(suspicious_groups),
            "suspicious_component_slot_count": len(suspicious_slots),
        },
        "suspicious_material_groups": suspicious_groups,
        "all_material_groups": material_groups,
        "suspicious_slots": suspicious_slots,
    }
    write_json(REPORT_PATH, report)
    summary = {
        "status": report["status"],
        "counts": report["counts"],
        "suspicious": [
            {
                "material": group["material"]["path"],
                "flags": group["material"]["flags"],
                "actor_count": group["usage"]["actor_count"],
                "meshes": [os.path.basename(path or "") for path in group["usage"]["mesh_paths"]],
            }
            for group in suspicious_groups
        ],
        "report": REPORT_PATH,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
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
            },
        )
        raise
