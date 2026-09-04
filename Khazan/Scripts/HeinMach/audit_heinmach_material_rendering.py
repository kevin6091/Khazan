"""Audit only the materials that are actually rendered by HeinMach actors.

The FModel USD preview exporter connected the packed ``*_S`` texture as
roughness=B and metallic=G.  Khazan's environment textures follow the usual
ORM-style channel layout (AO=R, roughness=G, metallic=B), so that import makes
stone and wood look like glossy metal.  USD also selected a translucent parent
whenever the diffuse texture exposed an alpha channel, including materials whose
source alpha is constantly one.

This script is read-only.  It records the exact live material inventory, source
alpha ranges, packed-mask eligibility, and the effective blend/TwoSided state
after Material Instance base-property overrides.  Fog actors and Fog materials
are explicitly excluded.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_MaterialRendering_Audit.json",
)
MANAGED_PREFIXES = ("HM_Prop_", "HM_ChildProp_", "HM_FoliageBatch_")
FOG_LABEL_PREFIX = "HM_FogSheet_"
PROJECT_ASSET_PREFIX = "/Game/_Art/Kazan/Environment/HeinMach/"
FOG_ASSET_TOKEN = "/FogSheets/"
OPAQUE_NAME_RE = re.compile(r"_opaque(?:_\d+)?$", re.IGNORECASE)
USD_TRANSLUCENT_PARENT = (
    "/USDCore/Materials/UsdPreviewSurfaceTranslucent."
    "UsdPreviewSurfaceTranslucent"
)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(asset):
    return asset.get_path_name() if asset else None


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


def fog_signature(actors):
    records = sorted(
        (
            actor_transform_record(actor)
            for actor in actors
            if actor.get_actor_label().startswith(FOG_LABEL_PREFIX)
        ),
        key=lambda item: item["label"],
    )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def scalar_value(material, name):
    try:
        return float(
            unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                material, name
            )
        )
    except Exception:
        return None


def vector_value(material, name):
    try:
        value = (
            unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
                material, name
            )
        )
        return [float(value.r), float(value.g), float(value.b), float(value.a)]
    except Exception:
        return None


def texture_value(material, name):
    try:
        return unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            material, name
        )
    except Exception:
        return None


def texture_record(texture, include_alpha=False):
    if not texture:
        return None
    record = {
        "path": texture.get_path_name(),
        "class": texture.get_class().get_name(),
    }
    if include_alpha and isinstance(texture, unreal.Texture2D):
        try:
            minimum, maximum = texture.compute_texture_source_channel_min_max()
            record["source_channel_min"] = [
                float(minimum.r),
                float(minimum.g),
                float(minimum.b),
                float(minimum.a),
            ]
            record["source_channel_max"] = [
                float(maximum.r),
                float(maximum.g),
                float(maximum.b),
                float(maximum.a),
            ]
        except Exception as error:
            record["source_channel_error"] = str(error)
    return record


def component_matches(value, expected, tolerance=0.001):
    return bool(
        value
        and len(value) == len(expected)
        and all(abs(float(actual) - float(target)) <= tolerance for actual, target in zip(value, expected))
    )


def safe_property(target, name, default=None):
    try:
        return target.get_editor_property(name)
    except Exception:
        return default


def material_surface_state(material):
    """Return inherited and effective surface properties for one material."""
    state = {
        "parent": None,
        "base_material": None,
        "base_blend_mode": None,
        "base_two_sided": None,
        "override_blend_mode": False,
        "instance_blend_mode": None,
        "effective_blend_mode": None,
        "override_two_sided": False,
        "instance_two_sided": False,
        "effective_two_sided": False,
        "override_opacity_mask_clip_value": False,
        "opacity_mask_clip_value": None,
        "blend_source_path": None,
        "two_sided_source_path": None,
    }
    state["parent"] = object_path(safe_property(material, "parent"))
    overrides = safe_property(material, "base_property_overrides")
    if overrides is not None:
        state["override_blend_mode"] = bool(
            safe_property(overrides, "override_blend_mode", False)
        )
        state["instance_blend_mode"] = str(
            safe_property(overrides, "blend_mode")
        )
        state["override_two_sided"] = bool(
            safe_property(overrides, "override_two_sided", False)
        )
        state["instance_two_sided"] = bool(
            safe_property(overrides, "two_sided", False)
        )
        state["override_opacity_mask_clip_value"] = bool(
            safe_property(
                overrides, "override_opacity_mask_clip_value", False
            )
        )
        clip = safe_property(overrides, "opacity_mask_clip_value")
        state["opacity_mask_clip_value"] = (
            float(clip) if clip is not None else None
        )

    # Parent USD preview assets are themselves Material Instances.  Resolve the
    # first override in the complete inheritance chain instead of jumping to
    # the ultimate Material and losing the Translucent parent override.
    visited = set()
    current = material
    effective_blend = None
    effective_two_sided = None
    base = None
    while current:
        current_path = object_path(current)
        if current_path in visited:
            break
        visited.add(current_path)
        if "MaterialInstance" in current.get_class().get_name():
            current_overrides = safe_property(current, "base_property_overrides")
            if (
                effective_blend is None
                and bool(
                    safe_property(
                        current_overrides, "override_blend_mode", False
                    )
                )
            ):
                effective_blend = str(
                    safe_property(current_overrides, "blend_mode")
                )
                state["blend_source_path"] = current_path
            if (
                effective_two_sided is None
                and bool(
                    safe_property(
                        current_overrides, "override_two_sided", False
                    )
                )
            ):
                effective_two_sided = bool(
                    safe_property(current_overrides, "two_sided", False)
                )
                state["two_sided_source_path"] = current_path
            current = safe_property(current, "parent")
            continue
        base = current
        break

    if base:
        state["base_material"] = object_path(base)
        state["base_blend_mode"] = str(safe_property(base, "blend_mode"))
        state["base_two_sided"] = bool(
            safe_property(base, "two_sided", False)
        )
        if effective_blend is None:
            effective_blend = state["base_blend_mode"]
            state["blend_source_path"] = state["base_material"]
        if effective_two_sided is None:
            effective_two_sided = state["base_two_sided"]
            state["two_sided_source_path"] = state["base_material"]

    state["effective_blend_mode"] = effective_blend
    state["effective_two_sided"] = effective_two_sided
    return state


def material_record(path, material, usage_count, sample_labels):
    parent = None
    try:
        parent = material.get_editor_property("parent")
    except Exception:
        pass

    base_color = texture_value(material, "BaseColorTexture")
    roughness = texture_value(material, "RoughnessTexture")
    metallic = texture_value(material, "MetallicTexture")
    base_record = texture_record(base_color, include_alpha=True)
    alpha_min = None
    alpha_max = None
    if base_record and base_record.get("source_channel_min"):
        alpha_min = float(base_record["source_channel_min"][3])
        alpha_max = float(base_record["source_channel_max"][3])

    name_for_policy = material.get_name()
    source_forces_opaque = bool(OPAQUE_NAME_RE.search(name_for_policy))
    constant_opaque_alpha = (
        alpha_min is not None
        and alpha_max is not None
        and alpha_min >= 0.999
        and alpha_max >= 0.999
    )
    solid_opaque = source_forces_opaque or constant_opaque_alpha
    roughness_path = object_path(roughness)
    metallic_path = object_path(metallic)
    ambient_occlusion = texture_value(material, "AmbientOcclusionTexture")
    ambient_occlusion_path = object_path(ambient_occlusion)
    # Engine's 127grey is the USD parent's disabled placeholder, not a source
    # packed mask.  Project-local same-texture inputs include the real *_S maps
    # and the flat-yellow visual fallback used by some foliage exports.
    packed_mask = bool(
        roughness_path
        and roughness_path == metallic_path
        and roughness_path.startswith(PROJECT_ASSET_PREFIX)
    )
    use_roughness = scalar_value(material, "UseRoughnessTexture")
    use_metallic = scalar_value(material, "UseMetallicTexture")
    use_ambient_occlusion = scalar_value(material, "UseAmbientOcclusionTexture")
    roughness_component = vector_value(material, "RoughnessTextureComponent")
    metallic_component = vector_value(material, "MetallicTextureComponent")
    ambient_occlusion_component = vector_value(
        material, "AmbientOcclusionTextureComponent"
    )
    packed_channel_mapping_correct = bool(
        packed_mask
        and ambient_occlusion_path == roughness_path
        and component_matches(roughness_component, (0, 1, 0, 0))
        and component_matches(metallic_component, (0, 0, 1, 0))
        and component_matches(ambient_occlusion_component, (1, 0, 0, 0))
        and use_roughness is not None
        and use_roughness >= 0.999
        and use_metallic is not None
        and use_metallic >= 0.999
        and use_ambient_occlusion is not None
        and use_ambient_occlusion >= 0.999
    )

    surface = material_surface_state(material)
    return {
        "path": path,
        "name": material.get_name(),
        "class": material.get_class().get_name(),
        "parent_path": object_path(parent),
        "usage_count": int(usage_count),
        "sample_actor_labels": list(sample_labels),
        "textures": {
            "base_color": base_record,
            "normal": texture_record(texture_value(material, "NormalTexture")),
            "roughness": texture_record(roughness),
            "metallic": texture_record(metallic),
            "ambient_occlusion": texture_record(ambient_occlusion),
        },
        "parameters": {
            "UseBaseColorTexture": scalar_value(material, "UseBaseColorTexture"),
            "UseNormalTexture": scalar_value(material, "UseNormalTexture"),
            "UseRoughnessTexture": use_roughness,
            "UseMetallicTexture": use_metallic,
            "UseOpacityTexture": scalar_value(material, "UseOpacityTexture"),
            "UseAmbientOcclusionTexture": use_ambient_occlusion,
            "RoughnessTextureComponent": roughness_component,
            "MetallicTextureComponent": metallic_component,
            "AmbientOcclusionTextureComponent": ambient_occlusion_component,
        },
        "surface": surface,
        "classification": {
            "base_color_alpha_min": alpha_min,
            "base_color_alpha_max": alpha_max,
            "source_name_forces_opaque": source_forces_opaque,
            "constant_opaque_alpha": constant_opaque_alpha,
            "render_policy": "solid_opaque" if solid_opaque else "alpha_preserving",
            "packed_mask_texture": packed_mask,
            "packed_channel_mapping_correct": packed_channel_mapping_correct,
            "needs_channel_repair": bool(
                packed_mask and not packed_channel_mapping_correct
            ),
            "needs_opaque_parent_repair": bool(
                solid_opaque and object_path(parent) == USD_TRANSLUCENT_PARENT
            ),
        },
    }


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors())
    usage = collections.Counter()
    samples = collections.defaultdict(list)
    materials = {}
    skipped_non_project = collections.Counter()

    for actor in actors:
        label = actor.get_actor_label()
        if label.startswith(FOG_LABEL_PREFIX) or not label.startswith(MANAGED_PREFIXES):
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(component.get_num_materials()):
                material = component.get_material(slot)
                if not material or not isinstance(material, unreal.MaterialInstance):
                    continue
                path = material.get_path_name()
                if FOG_ASSET_TOKEN in path:
                    continue
                if not path.startswith(PROJECT_ASSET_PREFIX):
                    skipped_non_project[path] += 1
                    continue
                usage[path] += 1
                materials[path] = material
                if len(samples[path]) < 4:
                    samples[path].append(label)

    records = []
    for index, path in enumerate(sorted(materials), start=1):
        records.append(
            material_record(path, materials[path], usage[path], samples[path])
        )
        if index % 100 == 0:
            unreal.log(
                "KHAZAN_HEINMACH_MATERIAL_AUDIT: {}/{}".format(
                    index, len(materials)
                )
            )

    counts = collections.Counter(
        {
            "effective_blend_opaque": 0,
            "effective_blend_masked": 0,
            "effective_blend_translucent": 0,
            "effective_two_sided": 0,
            "alpha_preserving_effective_opaque": 0,
            "alpha_preserving_effective_masked": 0,
            "alpha_preserving_effective_translucent": 0,
        }
    )
    for record in records:
        policy = record["classification"]
        surface = record["surface"]
        counts[policy["render_policy"]] += 1
        blend_text = str(surface.get("effective_blend_mode") or "").upper()
        blend_key = None
        if "MASKED" in blend_text:
            blend_key = "masked"
        elif "TRANSLUCENT" in blend_text:
            blend_key = "translucent"
        elif "OPAQUE" in blend_text:
            blend_key = "opaque"
        if blend_key:
            counts["effective_blend_" + blend_key] += 1
            if policy["render_policy"] == "alpha_preserving":
                counts["alpha_preserving_effective_" + blend_key] += 1
        if surface.get("effective_two_sided"):
            counts["effective_two_sided"] += 1
        if policy["needs_channel_repair"]:
            counts["needs_channel_repair"] += 1
        if policy["packed_mask_texture"]:
            counts["packed_mask_texture"] += 1
        if policy["packed_channel_mapping_correct"]:
            counts["packed_channel_mapping_correct"] += 1
        if policy["needs_opaque_parent_repair"]:
            counts["needs_opaque_parent_repair"] += 1

    payload = {
        "status": "audited",
        "map_path": MAP_PATH,
        "actor_count": len(actors),
        "managed_material_slot_count": int(sum(usage.values())),
        "unique_material_count": len(records),
        "counts": dict(sorted(counts.items())),
        "fog_boundary": {
            "policy": "Fog actors and Fog material assets are excluded",
            "signature": fog_signature(actors),
        },
        "classification_policy": {
            "solid_opaque": "source name ends in _opaque or BaseColor alpha is constantly 1",
            "alpha_preserving": "BaseColor alpha varies; effective Masked/Translucent is reported separately and source JSON remains authoritative",
            "effective_surface": "Material Instance base-property overrides are resolved against the ultimate base Material",
            "packed_mask": "RoughnessTexture and MetallicTexture resolve to the same project-local texture; engine 127grey placeholders are excluded",
            "packed_channels": {"ambient_occlusion": "R", "roughness": "G", "metallic": "B"},
        },
        "skipped_non_project_materials": dict(skipped_non_project),
        "materials": records,
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({"report": REPORT_PATH, **payload["counts"], "unique": len(records)}))
    return payload


if __name__ == "__main__":
    main()
