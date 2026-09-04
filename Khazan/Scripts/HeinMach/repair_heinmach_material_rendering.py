"""Repair FModel USD packed-channel and accidental translucency errors.

Input is the exact live-use inventory produced by
``audit_heinmach_material_rendering.py``.  The operation does not load or save
the level and never touches Fog assets.  Before changing each uasset it copies
the original binary into Saved/ArtBackups so the repair is reversible.
"""

from __future__ import annotations

import collections
import json
import os
import shutil
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_MaterialRendering_Audit.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_MaterialRendering_Repair.json",
)
BACKUP_ROOT = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ArtBackups",
    "HeinMach_MaterialRendering_PreFix",
)
USD_OPAQUE_PARENT = "/USDCore/Materials/UsdPreviewSurface.UsdPreviewSurface"
FOG_ASSET_TOKEN = "/FogSheets/"
PROJECT_ASSET_PREFIX = "/Game/_Art/Kazan/Environment/HeinMach/"


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def package_path(object_path):
    return str(object_path).split(".", 1)[0]


def filesystem_io_path(path):
    """Return a Windows extended-length path for long reconstructed asset names."""
    normalized = os.path.abspath(os.path.normpath(path))
    if os.name == "nt" and not normalized.startswith("\\\\?\\"):
        return "\\\\?\\" + normalized
    return normalized


def backup_asset(object_path):
    package = package_path(object_path)
    if not package.startswith("/Game/"):
        raise RuntimeError("Refusing to back up a non-project asset: " + package)
    relative = package[len("/Game/") :].replace("/", os.sep) + ".uasset"
    source = os.path.join(unreal.Paths.project_content_dir(), relative)
    destination = os.path.join(BACKUP_ROOT, "Game", relative)
    source = os.path.normpath(unreal.Paths.convert_relative_path_to_full(source))
    destination = os.path.normpath(destination)
    source_io = filesystem_io_path(source)
    destination_io = filesystem_io_path(destination)
    if not os.path.isfile(source_io):
        raise RuntimeError("Material uasset is missing: " + source)
    os.makedirs(os.path.dirname(destination_io), exist_ok=True)
    if not os.path.isfile(destination_io):
        shutil.copy2(source_io, destination_io)
        return destination, True
    return destination, False


def texture_from_record(record, key):
    item = (record.get("textures") or {}).get(key) or {}
    path = item.get("path")
    return unreal.load_asset(path) if path else None


def parameter_names(material, kind):
    library = unreal.MaterialEditingLibrary
    getter = {
        "scalar": library.get_scalar_parameter_names,
        "vector": library.get_vector_parameter_names,
        "texture": library.get_texture_parameter_names,
    }[kind]
    return {str(name) for name in getter(material)}


def set_scalar(material, names, name, value):
    if name not in names:
        return False
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, name, float(value)
    )
    return True


def set_vector(material, names, name, values):
    if name not in names:
        return False
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        material,
        name,
        unreal.LinearColor(values[0], values[1], values[2], values[3]),
    )
    return True


def set_texture(material, names, name, texture):
    if name not in names or not texture:
        return False
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
        material, name, texture
    )
    return True


def current_parent(material):
    try:
        parent = material.get_editor_property("parent")
        return parent.get_path_name() if parent else None
    except Exception:
        return None


def repair_material(record, opaque_parent):
    path = record["path"]
    if FOG_ASSET_TOKEN in path:
        raise RuntimeError("Fog material entered the repair inventory: " + path)
    material = unreal.load_asset(path)
    if not material or not isinstance(material, unreal.MaterialInstance):
        raise RuntimeError("Material instance is unavailable: " + path)

    backup_path, backup_created = backup_asset(path)
    scalar_names = parameter_names(material, "scalar")
    vector_names = parameter_names(material, "vector")
    texture_names = parameter_names(material, "texture")
    policy = record["classification"]
    changes = []

    if policy.get("render_policy") == "solid_opaque":
        if current_parent(material) != USD_OPAQUE_PARENT:
            unreal.MaterialEditingLibrary.set_material_instance_parent(
                material, opaque_parent
            )
            changes.append("opaque_parent")
        if set_scalar(material, scalar_names, "UseOpacityTexture", 0.0):
            changes.append("disable_opacity_texture")
        set_scalar(material, scalar_names, "Opacity", 1.0)

    mask_record = (record.get("textures") or {}).get("roughness") or {}
    mask_path = mask_record.get("path") or ""
    packed_mask = bool(
        policy.get("packed_mask_texture")
        and mask_path.startswith(PROJECT_ASSET_PREFIX)
    )
    if packed_mask:
        mask_texture = texture_from_record(record, "roughness")
        if set_vector(
            material, vector_names, "RoughnessTextureComponent", (0, 1, 0, 0)
        ):
            changes.append("roughness_G")
        if set_vector(
            material, vector_names, "MetallicTextureComponent", (0, 0, 1, 0)
        ):
            changes.append("metallic_B")
        set_scalar(material, scalar_names, "UseRoughnessTexture", 1.0)
        set_scalar(material, scalar_names, "UseMetallicTexture", 1.0)
        if set_texture(
            material, texture_names, "AmbientOcclusionTexture", mask_texture
        ):
            set_vector(
                material,
                vector_names,
                "AmbientOcclusionTextureComponent",
                (1, 0, 0, 0),
            )
            set_scalar(material, scalar_names, "UseAmbientOcclusionTexture", 1.0)
            changes.append("ambient_occlusion_R")
    elif policy.get("packed_mask_texture"):
        # The original audit treated the USD parent's engine 127grey defaults as
        # packed maps.  Restore their disabled pre-fix values exactly instead of
        # leaving those materials half metallic.
        original_parameters = record.get("parameters") or {}
        for name in (
            "UseRoughnessTexture",
            "UseMetallicTexture",
            "UseAmbientOcclusionTexture",
        ):
            value = original_parameters.get(name)
            if value is not None:
                set_scalar(material, scalar_names, name, value)
        for name in (
            "RoughnessTextureComponent",
            "MetallicTextureComponent",
            "AmbientOcclusionTextureComponent",
        ):
            value = original_parameters.get(name)
            if value:
                set_vector(material, vector_names, name, value)
        original_ao = texture_from_record(record, "ambient_occlusion")
        set_texture(
            material,
            texture_names,
            "AmbientOcclusionTexture",
            original_ao,
        )
        changes.append("restore_non_mask_placeholder")

    saved = unreal.EditorAssetLibrary.save_loaded_asset(
        material, only_if_is_dirty=False
    )
    if not saved:
        raise RuntimeError("Failed to save material: " + path)
    return {
        "path": path,
        "backup_path": backup_path,
        "backup_created": backup_created,
        "render_policy": policy.get("render_policy"),
        "changes": changes,
        "parent_after": current_parent(material),
    }


def main():
    audit = load_json(AUDIT_PATH)
    if audit.get("status") != "audited":
        raise RuntimeError("Material audit is not complete")
    fog_signature = ((audit.get("fog_boundary") or {}).get("signature") or {})
    if fog_signature.get("count") != 50:
        raise RuntimeError("Fog boundary changed before material repair")
    records = list(audit.get("materials") or [])
    if not records:
        raise RuntimeError("Material audit inventory is empty")

    opaque_parent = unreal.load_asset(USD_OPAQUE_PARENT)
    if not opaque_parent:
        raise RuntimeError("USD opaque preview material is unavailable")

    results = []
    failures = []
    for index, record in enumerate(records, start=1):
        try:
            results.append(repair_material(record, opaque_parent))
        except Exception as error:
            failures.append(
                {
                    "path": record.get("path"),
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
        if index % 25 == 0:
            unreal.log(
                "KHAZAN_HEINMACH_MATERIAL_REPAIR: {}/{} failures={}".format(
                    index, len(records), len(failures)
                )
            )

    totals = collections.Counter()
    for result in results:
        totals["material_saved"] += 1
        totals["backup_created"] += int(result["backup_created"])
        for change in result["changes"]:
            totals[change] += 1
    for record in records:
        policy = record.get("classification") or {}
        mask_path = (((record.get("textures") or {}).get("roughness") or {}).get("path") or "")
        totals["solid_opaque_material"] += int(
            policy.get("render_policy") == "solid_opaque"
        )
        totals["project_packed_mask_material"] += int(
            policy.get("packed_mask_texture")
            and mask_path.startswith(PROJECT_ASSET_PREFIX)
        )
    payload = {
        "status": "repaired" if not failures else "failed",
        "source_audit": AUDIT_PATH,
        "backup_root": BACKUP_ROOT,
        "fog_boundary": {
            "policy": "No level or Fog asset was loaded or saved",
            "source_signature": fog_signature,
        },
        "packed_channel_policy": {
            "ambient_occlusion": "R",
            "roughness": "G",
            "metallic": "B",
        },
        "totals": dict(sorted(totals.items())),
        "results": results,
        "failures": failures,
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({"report": REPORT_PATH, "status": payload["status"], **payload["totals"]}))
    if failures:
        raise RuntimeError("Material repair failures: {}".format(len(failures)))
    return payload


if __name__ == "__main__":
    main()
