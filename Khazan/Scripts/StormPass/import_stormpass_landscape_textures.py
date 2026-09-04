"""Import and configure exact StormPass Landscape source textures.

UE 5.8 Interchange can re-enter TaskGraph during Python-driven multi-file
imports, so every task explicitly uses the legacy TextureFactory.
"""

from __future__ import annotations

import json
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SOURCE_METADATA = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeMaterialSources.json",
)
ASSET_METADATA = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeTextureAssets.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Landscape_TextureImport.json",
)
DESTINATION_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Landscape/Textures"
)
SURFACE_ROOT = DESTINATION_ROOT + "/Surface"
WEIGHT_ROOT = DESTINATION_ROOT + "/Weightmaps"
EXPECTED_SURFACE_COUNT = 37
EXPECTED_WEIGHT_COUNT = 14
EXPECTED_NORMAL_COUNT = 2


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def log(message):
    unreal.log("KHAZAN_STORMPASS_LANDSCAPE_TEXTURE: " + str(message))


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value))
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "Unnamed"


def does_asset_exist(path):
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def asset_path(root, name):
    return root + "/" + name


def texture_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset or asset.get_class().get_name() != "Texture2D":
        return None
    return asset


def source_rows(metadata):
    rows = []
    for source in metadata["decoded_surface_textures"]:
        name = "T_SP_Surface_" + safe_name(source["source_object_name"])
        semantics = set()
        for binding in source.get("parameter_bindings", []):
            parameter = str(binding["parameter_name"])
            if "Tex_N" in parameter or parameter.endswith("Tex_N"):
                semantics.add("normal")
            elif "Tex_S" in parameter or parameter.endswith("Tex_S"):
                semantics.add("surface")
            elif "Tex_D" in parameter or parameter.endswith("Tex_D"):
                semantics.add("diffuse")
        rows.append(
            {
                "kind": "surface",
                "source_name": source["source_object_name"],
                "source_path": source["path"],
                "destination_root": SURFACE_ROOT,
                "asset_name": name,
                "asset_path": asset_path(SURFACE_ROOT, name),
                "semantics": sorted(semantics),
                "source_width": int(source["width"]),
                "source_height": int(source["height"]),
            }
        )

    short_names = {
        "StormPass_Landscape": "Main",
        "StormPass_Boss_Phase_2": "Boss",
    }
    for landscape in metadata["landscapes"]:
        short = short_names[landscape["source_level"]]
        normal = landscape["normal_map"]
        normal_name = "T_SP_{}_LandscapeNormal".format(short)
        rows.append(
            {
                "kind": "landscape_normal",
                "source_name": "NormalMap_DX",
                "source_path": normal["path"],
                "destination_root": WEIGHT_ROOT + "/" + short,
                "asset_name": normal_name,
                "asset_path": asset_path(WEIGHT_ROOT + "/" + short, normal_name),
                "semantics": ["normal"],
                "source_width": int(normal["width"]),
                "source_height": int(normal["height"]),
            }
        )
        for layer in landscape["weight_layers"]:
            material_layer = layer["material_layer_name"]
            name = "T_SP_{}_Weight_{}".format(short, safe_name(material_layer))
            rows.append(
                {
                    "kind": "weight",
                    "source_name": layer["exported_layer_name"],
                    "material_layer_name": material_layer,
                    "source_path": layer["path"],
                    "destination_root": WEIGHT_ROOT + "/" + short,
                    "asset_name": name,
                    "asset_path": asset_path(WEIGHT_ROOT + "/" + short, name),
                    "semantics": ["weight"],
                    "source_width": int(layer["width"]),
                    "source_height": int(layer["height"]),
                    "statistics": layer.get("statistics"),
                }
            )
    return rows


def validate_rows(rows):
    surface_count = sum(row["kind"] == "surface" for row in rows)
    weight_count = sum(row["kind"] == "weight" for row in rows)
    normal_count = sum(row["kind"] == "landscape_normal" for row in rows)
    if (surface_count, weight_count, normal_count) != (
        EXPECTED_SURFACE_COUNT,
        EXPECTED_WEIGHT_COUNT,
        EXPECTED_NORMAL_COUNT,
    ):
        raise RuntimeError(
            "Texture source inventory changed: {}".format(
                (surface_count, weight_count, normal_count)
            )
        )
    names = [row["asset_path"] for row in rows]
    if len(names) != len(set(names)):
        raise RuntimeError("Landscape texture destination names are not unique")
    missing = [row["source_path"] for row in rows if not os.path.isfile(row["source_path"])]
    if missing:
        raise RuntimeError("Landscape texture source is missing: " + missing[0])


def import_missing(rows):
    tasks = []
    for row in rows:
        if texture_asset(row["asset_path"]):
            continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", row["source_path"])
        task.set_editor_property("destination_path", row["destination_root"])
        task.set_editor_property("destination_name", row["asset_name"])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.TextureFactory())
        tasks.append(task)
    if tasks:
        log("Importing {} textures through legacy TextureFactory".format(len(tasks)))
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    unresolved = [row["asset_path"] for row in rows if not texture_asset(row["asset_path"])]
    if unresolved:
        raise RuntimeError("Texture import left an asset unresolved: " + unresolved[0])
    return len(tasks)


def configure(rows):
    configured = []
    failures = []
    for row in rows:
        texture = texture_asset(row["asset_path"])
        if not texture:
            failures.append({"asset_path": row["asset_path"], "issue": "missing"})
            continue
        semantics = set(row["semantics"])
        texture.modify()
        if "normal" in semantics:
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
            )
            texture.set_editor_property("srgb", False)
        elif semantics & {"surface", "weight"}:
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
            )
            texture.set_editor_property("srgb", False)
        else:
            texture.set_editor_property("srgb", True)
        actual_srgb = bool(texture.get_editor_property("srgb"))
        expected_srgb = not bool(semantics & {"normal", "surface", "weight"})
        if actual_srgb != expected_srgb:
            failures.append({"asset_path": row["asset_path"], "issue": "srgb"})
        configured.append(
            {
                **row,
                "loaded_path": texture.get_path_name(),
                "srgb": actual_srgb,
                "compression_settings": str(
                    texture.get_editor_property("compression_settings")
                ),
            }
        )
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )
    if failures:
        raise RuntimeError("Landscape texture configuration failed: " + str(failures[0]))
    return configured


def main():
    metadata = load_json(SOURCE_METADATA)
    if metadata.get("status") != "passed":
        raise RuntimeError("Landscape material source metadata is not passed")
    rows = source_rows(metadata)
    validate_rows(rows)
    imported = import_missing(rows)
    configured = configure(rows)
    payload = {
        "schema_version": 1,
        "status": "passed",
        "destination_root": DESTINATION_ROOT,
        "texture_count": len(configured),
        "surface_texture_count": sum(row["kind"] == "surface" for row in configured),
        "weight_texture_count": sum(row["kind"] == "weight" for row in configured),
        "landscape_normal_texture_count": sum(
            row["kind"] == "landscape_normal" for row in configured
        ),
        "textures": configured,
        "import_policy": "Explicit legacy TextureFactory; no Interchange multi-import.",
        "fog_policy": "deferred_until_final_pass",
    }
    write_json(ASSET_METADATA, payload)
    report = {
        "status": "passed",
        "canonical_metadata": ASSET_METADATA,
        "imported_this_run": imported,
        "texture_count": len(configured),
        "surface_texture_count": payload["surface_texture_count"],
        "weight_texture_count": payload["weight_texture_count"],
        "landscape_normal_texture_count": payload[
            "landscape_normal_texture_count"
        ],
        "fog_actor_count": 0,
    }
    write_json(REPORT_PATH, report)
    log("RESULT " + json.dumps(report, ensure_ascii=False, sort_keys=True))
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
        unreal.log_error("KHAZAN_STORMPASS_LANDSCAPE_TEXTURE: " + str(exception))
        raise
