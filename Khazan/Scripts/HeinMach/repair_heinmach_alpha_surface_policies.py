"""Restore Masked/TwoSided policy for live alpha materials from FModel JSON.

The USD preview importer used a Translucent parent whenever BaseColor exposed an
alpha channel.  For Khazan props that alpha is normally a cutout mask.  This
targeted pass considers only live, alpha-preserving materials that are still
effectively Translucent, resolves their exact source packages through the
existing inherited material mapping report, and applies the authoritative
FModel BasePropertyOverrides.  Fog actors/assets are never modified.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import shutil
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_MaterialRendering_Audit.json",
)
MAPPING_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_InheritedOverrideMaterial_Restoration.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_AlphaSurfacePolicy_Repair.json",
)
BACKUP_ROOT = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ArtBackups",
    "HeinMach_AlphaSurface_PreFix",
)
FOG_LABEL_PREFIX = "HM_FogSheet_"
FOG_ASSET_TOKEN = "/FogSheets/"


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(asset):
    return asset.get_path_name() if asset else None


def package_path(value):
    return str(value).split(".", 1)[0]


def filesystem_io_path(path):
    normalized = os.path.abspath(os.path.normpath(path))
    if os.name == "nt" and not normalized.startswith("\\\\?\\"):
        return "\\\\?\\" + normalized
    return normalized


def backup_asset(value):
    package = package_path(value)
    if not package.startswith("/Game/"):
        raise RuntimeError("Refusing to back up non-project asset: " + package)
    relative = package[len("/Game/") :].replace("/", os.sep) + ".uasset"
    source = os.path.normpath(
        unreal.Paths.convert_relative_path_to_full(
            os.path.join(unreal.Paths.project_content_dir(), relative)
        )
    )
    destination = os.path.normpath(os.path.join(BACKUP_ROOT, "Game", relative))
    source_io = filesystem_io_path(source)
    destination_io = filesystem_io_path(destination)
    if not os.path.isfile(source_io):
        raise RuntimeError("Material uasset is missing: " + source)
    os.makedirs(os.path.dirname(destination_io), exist_ok=True)
    if not os.path.isfile(destination_io):
        shutil.copy2(source_io, destination_io)
        return destination, True
    return destination, False


def safe_property(target, name, default=None):
    try:
        return target.get_editor_property(name)
    except Exception:
        return default


def material_surface_state(material):
    overrides = safe_property(material, "base_property_overrides")
    override_blend = bool(
        safe_property(overrides, "override_blend_mode", False)
    )
    instance_blend = str(safe_property(overrides, "blend_mode"))
    override_two_sided = bool(
        safe_property(overrides, "override_two_sided", False)
    )
    instance_two_sided = bool(safe_property(overrides, "two_sided", False))
    override_clip = bool(
        safe_property(overrides, "override_opacity_mask_clip_value", False)
    )
    clip = safe_property(overrides, "opacity_mask_clip_value")

    visited = set()
    current = material
    base = None
    effective_blend = None
    effective_two_sided = None
    blend_source_path = None
    two_sided_source_path = None
    while current:
        path = object_path(current)
        if path in visited:
            break
        visited.add(path)
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
                blend_source_path = path
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
                two_sided_source_path = path
            current = safe_property(current, "parent")
            continue
        base = current
        break
    base_blend = str(safe_property(base, "blend_mode")) if base else None
    base_two_sided = bool(safe_property(base, "two_sided", False)) if base else None
    if effective_blend is None:
        effective_blend = base_blend
        blend_source_path = object_path(base)
    if effective_two_sided is None:
        effective_two_sided = base_two_sided
        two_sided_source_path = object_path(base)
    return {
        "base_material": object_path(base),
        "base_blend_mode": base_blend,
        "override_blend_mode": override_blend,
        "instance_blend_mode": instance_blend,
        "effective_blend_mode": effective_blend,
        "blend_source_path": blend_source_path,
        "base_two_sided": base_two_sided,
        "override_two_sided": override_two_sided,
        "instance_two_sided": instance_two_sided,
        "effective_two_sided": effective_two_sided,
        "two_sided_source_path": two_sided_source_path,
        "override_opacity_mask_clip_value": override_clip,
        "opacity_mask_clip_value": float(clip) if clip is not None else None,
    }


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


def package_json_path(package):
    relative = os.path.join(*str(package).split("/")) + ".json"
    direct = os.path.normcase(os.path.abspath(os.path.join(FMODEL_ROOT, relative)))
    exported = os.path.normcase(
        os.path.abspath(os.path.join(FMODEL_ROOT, "Exports", relative))
    )
    return direct if os.path.isfile(direct) else exported


def source_material_policy(package):
    path = package_json_path(package)
    result = {
        "package": package,
        "json_path": path,
        "json_exists": os.path.isfile(path),
        "blend_mode": None,
        "two_sided": None,
        "opacity_mask_clip_value": None,
    }
    if not result["json_exists"]:
        return result
    payload = load_json(path)
    if isinstance(payload, list):
        record = next(
            (
                item
                for item in payload
                if isinstance(item, dict)
                and item.get("Type") in {"Material", "MaterialInstanceConstant"}
            ),
            {},
        )
        parameters = {}
        properties = record.get("Properties", {})
    else:
        parameters = payload.get("Parameters", {})
        properties = parameters.get("Properties", {})
    overrides = properties.get("BasePropertyOverrides", {})
    result["blend_mode"] = overrides.get(
        "BlendMode", parameters.get("BlendMode")
    )
    if "TwoSided" in overrides:
        result["two_sided"] = bool(overrides.get("TwoSided"))
    clip = overrides.get("OpacityMaskClipValue")
    if isinstance(clip, (int, float)):
        result["opacity_mask_clip_value"] = float(clip)
    return result


def is_masked(value):
    return str(value) in {"1", "BLEND_Masked"} or "BLEND_MASKED" in str(value).upper()


def mapping_by_material(payload):
    result = collections.defaultdict(set)
    for mesh in payload.get("mesh_mappings") or []:
        for assignment in mesh.get("assignments") or []:
            material = assignment.get("actual_material_path")
            package = assignment.get("source_package")
            if material and package:
                result[material].add(package)
    return result


def set_scalar_if_present(material, name, value):
    names = {
        str(item)
        for item in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)
    }
    if name not in names:
        return False
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, name, float(value)
    )
    return True


def repair_material(record, packages):
    path = record["path"]
    if FOG_ASSET_TOKEN in path:
        raise RuntimeError("Fog material entered alpha repair: " + path)
    material = unreal.load_asset(path)
    if not material or not isinstance(material, unreal.MaterialInstance):
        raise RuntimeError("Material instance is unavailable: " + path)
    before = material_surface_state(material)
    policies = [source_material_policy(package) for package in sorted(packages)]
    missing = [item["package"] for item in policies if not item["json_exists"]]
    blends = {str(item["blend_mode"]) for item in policies if item["blend_mode"] is not None}
    if missing:
        return {"path": path, "status": "unresolved", "reason": "missing_source_json", "source_policies": policies}
    if not blends or not all(is_masked(value) for value in blends):
        return {"path": path, "status": "unresolved", "reason": "source_blend_not_uniformly_masked", "source_policies": policies}

    backup_path, backup_created = backup_asset(path)
    material.modify()
    overrides = material.get_editor_property("base_property_overrides")
    overrides.set_editor_property("override_blend_mode", True)
    overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)

    two_sided_values = [
        item["two_sided"] for item in policies if item["two_sided"] is not None
    ]
    if two_sided_values:
        overrides.set_editor_property("override_two_sided", True)
        overrides.set_editor_property("two_sided", any(two_sided_values))

    clips = [
        item["opacity_mask_clip_value"]
        for item in policies
        if item["opacity_mask_clip_value"] is not None
    ]
    if clips:
        clip = collections.Counter(clips).most_common(1)[0][0]
        overrides.set_editor_property("override_opacity_mask_clip_value", True)
        overrides.set_editor_property("opacity_mask_clip_value", float(clip))
    material.set_editor_property("base_property_overrides", overrides)
    opacity_enabled = set_scalar_if_present(material, "UseOpacityTexture", 1.0)
    unreal.MaterialEditingLibrary.update_material_instance(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("Failed to save material: " + path)
    after = material_surface_state(material)
    if "BLEND_MASKED" not in str(after["effective_blend_mode"]).upper():
        raise RuntimeError("Material did not become effectively Masked: " + path)
    return {
        "path": path,
        "status": "repaired",
        "backup_path": backup_path,
        "backup_created": backup_created,
        "source_policies": policies,
        "before": before,
        "after": after,
        "opacity_texture_enabled": opacity_enabled,
    }


def main():
    audit = load_json(AUDIT_PATH)
    mapping = load_json(MAPPING_PATH)
    source_fog = ((audit.get("fog_boundary") or {}).get("signature") or {})
    if source_fog.get("count") != 50:
        raise RuntimeError("Fog boundary is invalid in source audit")

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        raise RuntimeError("Open the live HeinMach map before alpha surface repair")
    actors = list(
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    )
    fog_before = fog_signature(actors)
    if fog_before != source_fog:
        raise RuntimeError("Fog signature changed before alpha surface repair")

    sources = mapping_by_material(mapping)
    candidates = []
    skipped = []
    for record in audit.get("materials") or []:
        if (record.get("classification") or {}).get("render_policy") != "alpha_preserving":
            continue
        material = unreal.load_asset(record.get("path"))
        if not material:
            skipped.append({"path": record.get("path"), "reason": "load_failed"})
            continue
        state = material_surface_state(material)
        if "TRANSLUCENT" not in str(state["effective_blend_mode"]).upper():
            continue
        packages = sources.get(record["path"], set())
        if not packages:
            skipped.append({"path": record["path"], "reason": "no_source_mapping"})
            continue
        candidates.append((record, packages))

    results = []
    failures = []
    for index, (record, packages) in enumerate(candidates, start=1):
        try:
            results.append(repair_material(record, packages))
        except Exception as error:
            failures.append(
                {
                    "path": record.get("path"),
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
        if index % 10 == 0:
            unreal.log(
                "KHAZAN_HEINMACH_ALPHA_SURFACE: {}/{} failures={}".format(
                    index, len(candidates), len(failures)
                )
            )

    fog_after = fog_signature(
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    )
    repaired = [item for item in results if item.get("status") == "repaired"]
    unresolved = [item for item in results if item.get("status") == "unresolved"]
    status = "repaired" if not failures and not unresolved else "failed"
    payload = {
        "status": status,
        "map_path": MAP_PATH,
        "source_audit": AUDIT_PATH,
        "source_mapping_report": MAPPING_PATH,
        "backup_root": BACKUP_ROOT,
        "scope": "Only live alpha-preserving materials still effectively Translucent",
        "candidate_count": len(candidates),
        "repaired_count": len(repaired),
        "unresolved_count": len(unresolved),
        "skipped_count": len(skipped),
        "fog_boundary": {
            "policy": "Fog actors and assets were excluded",
            "before": fog_before,
            "after": fog_after,
            "unchanged": fog_before == fog_after == source_fog,
        },
        "results": results,
        "skipped": skipped,
        "failures": failures,
    }
    write_json(REPORT_PATH, payload)
    print(
        json.dumps(
            {
                "report": REPORT_PATH,
                "status": status,
                "candidate_count": len(candidates),
                "repaired_count": len(repaired),
                "unresolved_count": len(unresolved),
                "skipped_count": len(skipped),
                "fog_unchanged": payload["fog_boundary"]["unchanged"],
            }
        )
    )
    if status != "repaired":
        raise RuntimeError("Alpha surface policy repair did not fully resolve")
    return payload


if __name__ == "__main__":
    main()
