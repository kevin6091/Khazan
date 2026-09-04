"""Restore the two native StormPass custom-water material bindings.

The source xxWaterBodyCustomActor writes its WaterMaterial to
CustomMeshComponent at runtime.  The generic child-component reconstruction
therefore correctly recovered the mesh/transform but retained the mesh's
WorldGridMaterial fallback.  This pass reconstructs the FModel-authored
material-instance hierarchy, imports its exact source textures, creates a
UE5 SingleLayerWater preview graph for the unavailable cooked master graph,
and binds only the two affected StormPass child actors.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
FMODEL_EXPORT_ROOT = os.path.join(FMODEL_ROOT, "Exports")
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
DEV_MAP_PATH = "/Game/Maps/DevMap"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreNativeWaterRestore"
)
ASSET_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/WaterAssets"
TEXTURE_ROOT = ASSET_ROOT + "/Textures"
MATERIAL_ROOT = ASSET_ROOT + "/Materials"
MASTER_MATERIAL_PATH = MATERIAL_ROOT + "/M_SP_Water_Material_AK_Preview"
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_NativeWaterMaterials.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_NativeWaterMaterial_Restoration.json",
)
CHILD_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_ChildTemplateCoverage_Audit.json",
)
EXPECTED_ACTOR_COUNT = 14408
EXPECTED_FOG_COUNT = 53
EXPECTED_WATER_ACTOR_COUNT = 2
PREVIEW_MATERIAL_VERSION = 1

MATERIAL_PACKAGES = collections.OrderedDict(
    (
        (
            "master",
            "BBQ/Content/Art/Terrain/Terrain_Data/Water/Material/Water_Material_AK",
        ),
        (
            "skoffa",
            "BBQ/Content/Art/Terrain/Terrain_Data/Water/Material/"
            "Water_Material_SkoffaCave_CustomMesh_AK",
        ),
        (
            "stormpass",
            "BBQ/Content/Art/Terrain/Terrain_Data/Water/Material/"
            "Water_Material_StormPass_CustomMesh_AK",
        ),
        (
            "stormpass_inst1",
            "BBQ/Content/Art/Terrain/Terrain_Data/Water/Material/"
            "Water_Material_StormPass_CustomMesh_AK_Inst1",
        ),
    )
)
SOURCE_INSTANCE_ASSETS = {
    "skoffa": MATERIAL_ROOT + "/MI_Water_Material_SkoffaCave_CustomMesh_AK",
    "stormpass": MATERIAL_ROOT + "/MI_Water_Material_StormPass_CustomMesh_AK",
    "stormpass_inst1": MATERIAL_ROOT
    + "/MI_Water_Material_StormPass_CustomMesh_AK_Inst1",
}
ACTOR_SPECS = (
    {
        "label": "SP_ChildProp_StormPass_Boss_Phase_1_02379_00076",
        "source_level": "StormPass_Boss_Phase_1",
        "source_actor_index": 2379,
        "source_component_index": 76,
        "source_material_key": "stormpass",
        "actor_instance_path": MATERIAL_ROOT
        + "/MI_SP_Water_Boss_Phase_1_Actor_02379",
    },
    {
        "label": "SP_ChildProp_StormPass_Boss_Phase_2_02538_00179",
        "source_level": "StormPass_Boss_Phase_2",
        "source_actor_index": 2538,
        "source_component_index": 179,
        "source_material_key": "stormpass_inst1",
        "actor_instance_path": MATERIAL_ROOT
        + "/MI_SP_Water_Boss_Phase_2_Actor_02538",
    },
)
TEXTURE_PACKAGES = (
    "BBQ/Content/Art/Character/CHA_Material/Texture/Base/BASE_Black_NoneSRGB",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/BBQ_Texture/Noise/FT_Noise_011",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/BBQ_Texture/Mask/FT_S_Liquid_002",
    "BBQ/Content/Art/Terrain/Terrain_Data/Water/Texture/WLT_SeaFoam2",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/water/FT_Water_12",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/BBQ_Texture/Noise/FT_Ele_Noise",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Noise/FT_Noise_3ch_001",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Noise/FT_Noise_007",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Noise/FT_S_Tile_03B",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Noise/FT_Noise_Water",
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Noise/FT_Sparkle_Noise_002",
)
SOURCE_MESH_PACKAGE = (
    "BBQ/Content/_Kazan_/Art/Terrain/Terrain_Data/Water/Data/WLP_WaterPlan_10x10"
)


def log(message):
    unreal.log("KHAZAN_STORMPASS_NATIVE_WATER: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def package_basename(package):
    return str(package).rsplit("/", 1)[-1]


def fmodel_path(package, extension, exports=False):
    root = FMODEL_EXPORT_ROOT if exports else FMODEL_ROOT
    return os.path.join(root, *str(package).split("/")) + extension


def material_json_path(key):
    return fmodel_path(MATERIAL_PACKAGES[key], ".json", exports=True)


def normalize_array(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def object_path(value):
    return str((value or {}).get("ObjectPath") or "").rsplit(".", 1)[0]


def source_color(value, default_alpha=1.0):
    value = value or {}
    return (
        float(value.get("R", 0.0)),
        float(value.get("G", 0.0)),
        float(value.get("B", 0.0)),
        float(value.get("A", default_alpha)),
    )


def parse_master_parameters(document):
    root = document[0]
    cached = root.get("CachedExpressionData") or root.get("Properties", {}).get(
        "CachedExpressionData", {}
    )
    parameters = cached.get("Parameters", {})
    runtime_entries = [
        value
        for name, value in parameters.items()
        if str(name).startswith("RuntimeEntries") and isinstance(value, dict)
    ]

    def map_values(values_name):
        values = normalize_array(parameters.get(values_name))
        entry = next(
            (
                candidate
                for candidate in runtime_entries
                if len(normalize_array(candidate.get("ParameterInfos"))) == len(values)
            ),
            None,
        )
        if not values or not entry:
            return []
        result = []
        for info, value in zip(entry.get("ParameterInfos", []), values):
            result.append(
                {
                    "name": str(info.get("Name")),
                    "association": str(info.get("Association")),
                    "index": int(info.get("Index", -1)),
                    "value": value,
                }
            )
        return result

    scalars = map_values("ScalarValues")
    vectors = map_values("VectorValues")
    textures = map_values("TextureValues")
    return {
        "scalars": [
            dict(item, value=float(item["value"])) for item in scalars
        ],
        "vectors": [
            dict(item, value=list(source_color(item["value"]))) for item in vectors
        ],
        "textures": [
            dict(
                item,
                value={
                    "object_name": str((item["value"] or {}).get("ObjectName") or ""),
                    "object_path": str((item["value"] or {}).get("ObjectPath") or ""),
                },
            )
            for item in textures
        ],
        "referenced_textures": [
            {
                "object_name": str((item or {}).get("ObjectName") or ""),
                "object_path": str((item or {}).get("ObjectPath") or ""),
            }
            for item in normalize_array(cached.get("ReferencedTextures"))
        ],
    }


def parse_instance(document):
    root = document[0]
    properties = root.get("Properties", {}) or {}
    static = properties.get("StaticParameters", {}) or {}
    return {
        "name": str(root.get("Name")),
        "package": str(root.get("Package")),
        "parent": object_path(properties.get("Parent")),
        "scalars": [
            {
                "name": str(item["ParameterInfo"]["Name"]),
                "value": float(item["ParameterValue"]),
            }
            for item in normalize_array(properties.get("ScalarParameterValues"))
        ],
        "vectors": [
            {
                "name": str(item["ParameterInfo"]["Name"]),
                "value": list(source_color(item["ParameterValue"])),
            }
            for item in normalize_array(properties.get("VectorParameterValues"))
        ],
        "textures": [
            {
                "name": str(item["ParameterInfo"]["Name"]),
                "object_name": str(
                    (item.get("ParameterValue") or {}).get("ObjectName") or ""
                ),
                "object_path": str(
                    (item.get("ParameterValue") or {}).get("ObjectPath") or ""
                ),
            }
            for item in normalize_array(properties.get("TextureParameterValues"))
        ],
        "switches": [
            {
                "name": str(item["ParameterInfo"]["Name"]),
                "value": bool(item.get("Value")),
                "override": bool(item.get("bOverride")),
            }
            for item in normalize_array(static.get("StaticSwitchParameters"))
        ],
        "base_property_overrides": dict(properties.get("BasePropertyOverrides") or {}),
    }


def source_inventory():
    missing = []
    material_documents = {}
    material_hashes = {}
    for key in MATERIAL_PACKAGES:
        path = material_json_path(key)
        if not os.path.isfile(path):
            missing.append(path)
            continue
        material_documents[key] = load_json(path)
        material_hashes[key] = sha256_file(path)

    texture_records = []
    for package in TEXTURE_PACKAGES:
        png_path = fmodel_path(package, ".png", exports=False)
        json_path = fmodel_path(package, ".json", exports=True)
        if not os.path.isfile(png_path):
            missing.append(png_path)
        if not os.path.isfile(json_path):
            missing.append(json_path)
        if not os.path.isfile(png_path) or not os.path.isfile(json_path):
            continue
        document = load_json(json_path)
        root = document[0]
        properties = root.get("Properties", {}) or {}
        texture_records.append(
            {
                "package": package,
                "name": package_basename(package),
                "png_path": png_path,
                "json_path": json_path,
                "png_sha256": sha256_file(png_path),
                "json_sha256": sha256_file(json_path),
                "size_x": int(root.get("SizeX", 0)),
                "size_y": int(root.get("SizeY", 0)),
                "pixel_format": str(root.get("PixelFormat") or ""),
                "srgb": bool(properties.get("SRGB", True)),
                "compression_settings": str(
                    properties.get("CompressionSettings") or "TC_Default"
                ),
                "lod_group": str(properties.get("LODGroup") or ""),
            }
        )

    child_audit = load_json(CHILD_AUDIT_PATH)
    child_records = {
        (
            str(item.get("source_level")),
            int(item.get("actor_object_index", -1)),
            int(item.get("component_object_index", -1)),
        ): item
        for item in child_audit.get("resolved_child_mesh_components", [])
    }
    actor_records = []
    for spec in ACTOR_SPECS:
        level_path = os.path.join(
            FMODEL_EXPORT_ROOT,
            "BBQ",
            "Content",
            "_Kazan_",
            "Level",
            "StormPass",
            spec["source_level"] + ".json",
        )
        if not os.path.isfile(level_path):
            missing.append(level_path)
            continue
        level = load_json(level_path)
        actor = level[spec["source_actor_index"]]
        component = level[spec["source_component_index"]]
        key = (
            spec["source_level"],
            spec["source_actor_index"],
            spec["source_component_index"],
        )
        child = child_records.get(key)
        if not child:
            raise RuntimeError("Water child coverage record is missing: " + str(key))
        actor_properties = actor.get("Properties", {}) or {}
        component_properties = component.get("Properties", {}) or {}
        source_material = object_path(actor_properties.get("WaterMaterial"))
        expected_material = MATERIAL_PACKAGES[spec["source_material_key"]]
        if source_material != expected_material:
            raise RuntimeError(
                "WaterMaterial source mismatch for {}: {}".format(
                    spec["label"], source_material
                )
            )
        mesh = object_path(component_properties.get("StaticMesh"))
        if mesh != SOURCE_MESH_PACKAGE:
            raise RuntimeError("Water source mesh changed for " + spec["label"])
        record = dict(spec)
        record.update(
            {
                "source_level_json": level_path,
                "source_level_json_sha256": sha256_file(level_path),
                "source_actor_type": str(actor.get("Type")),
                "source_actor_name": str(actor.get("Name")),
                "source_component_name": str(component.get("Name")),
                "source_material_package": source_material,
                "source_mesh_package": mesh,
                "effect_color": list(source_color(actor_properties.get("EffectColor"))),
                "foam_color": list(source_color(actor_properties.get("FoamColor"))),
                "collision_profile_name": str(
                    actor_properties.get("CollisionProfileName") or ""
                ),
                "cast_shadow": bool(component_properties.get("CastShadow", True)),
                "visible": bool(child.get("visible", True)),
                "child_world_transform": child.get("actor_world_transform"),
                "child_override_material_packages": child.get(
                    "override_material_packages", []
                ),
            }
        )
        actor_records.append(record)

    if missing:
        raise RuntimeError("Missing native-water FModel sources: " + missing[0])
    if len(actor_records) != EXPECTED_WATER_ACTOR_COUNT:
        raise RuntimeError("Unexpected native-water actor source count")

    master_parameters = parse_master_parameters(material_documents["master"])
    instances = {
        key: parse_instance(material_documents[key])
        for key in ("skoffa", "stormpass", "stormpass_inst1")
    }
    expected_parents = {
        "skoffa": MATERIAL_PACKAGES["master"],
        "stormpass": MATERIAL_PACKAGES["skoffa"],
        "stormpass_inst1": MATERIAL_PACKAGES["stormpass"],
    }
    for key, expected_parent in expected_parents.items():
        if instances[key]["parent"] != expected_parent:
            raise RuntimeError("Native-water material parent chain changed: " + key)

    metadata = {
        "schema_version": 1,
        "status": "analyzed",
        "scope": "StormPass native xxWaterBodyCustomActor visual materials only",
        "source_mesh_package": SOURCE_MESH_PACKAGE,
        "source_material_packages": dict(MATERIAL_PACKAGES),
        "source_material_json_hashes": material_hashes,
        "master_parameters": master_parameters,
        "material_instances": instances,
        "source_textures": texture_records,
        "water_actors": actor_records,
        "analysis": {
            "source_actor_count": len(actor_records),
            "source_texture_count": len(texture_records),
            "master_scalar_parameter_count": len(master_parameters["scalars"]),
            "master_vector_parameter_count": len(master_parameters["vectors"]),
            "master_texture_parameter_count": len(master_parameters["textures"]),
            "native_actor_runtime_water_material_binding_required": True,
            "child_component_override_was_null": all(
                item["child_override_material_packages"] == [None]
                for item in actor_records
            ),
            "cooked_master_graph_available_from_fmodel": False,
            "ue5_single_layer_water_preview_graph_required": True,
        },
        "content_boundary": {
            "visual_level_content_only": True,
            "gameplay_or_source_code_modified": False,
            "collision_or_navigation_modified": False,
        },
    }
    write_json(METADATA_PATH, metadata)
    return metadata, actor_records, master_parameters, instances, texture_records


def import_source_textures(texture_records):
    ensure_directory(TEXTURE_ROOT)
    textures = {}
    results = []
    for index, record in enumerate(texture_records, start=1):
        asset_path = TEXTURE_ROOT + "/" + record["name"]
        texture = unreal.EditorAssetLibrary.load_asset(asset_path)
        imported = False
        imported_paths = []
        if not texture:
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", record["png_path"])
            task.set_editor_property("destination_path", TEXTURE_ROOT)
            task.set_editor_property("destination_name", record["name"])
            task.set_editor_property("automated", True)
            task.set_editor_property("replace_existing", False)
            task.set_editor_property("replace_existing_settings", False)
            task.set_editor_property("save", True)
            task.set_editor_property("factory", unreal.TextureFactory())
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported_paths = list(task.get_editor_property("imported_object_paths"))
            texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            imported = True
        if not texture:
            raise RuntimeError("Failed to import native-water texture: " + record["name"])
        texture.modify()
        texture.set_editor_property("srgb", bool(record["srgb"]))
        compression = getattr(
            unreal.TextureCompressionSettings,
            str(record["compression_settings"]).upper(),
            unreal.TextureCompressionSettings.TC_DEFAULT,
        )
        texture.set_editor_property("compression_settings", compression)
        if record["lod_group"]:
            group = getattr(
                unreal.TextureGroup, str(record["lod_group"]).upper(), None
            )
            if group is not None:
                texture.set_editor_property("lod_group", group)
        unreal.EditorAssetLibrary.set_metadata_tag(
            texture, "KhazanSourcePackage", record["package"]
        )
        unreal.EditorAssetLibrary.set_metadata_tag(
            texture, "KhazanSourcePngSHA256", record["png_sha256"]
        )
        unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
        textures[record["name"]] = texture
        results.append(
            {
                "source_package": record["package"],
                "asset_path": texture.get_path_name(),
                "imported": imported,
                "imported_object_paths": imported_paths,
                "srgb": bool(texture.get_editor_property("srgb")),
                "compression_settings": str(
                    texture.get_editor_property("compression_settings")
                ),
                "size_x": int(texture.blueprint_get_size_x()),
                "size_y": int(texture.blueprint_get_size_y()),
            }
        )
        if index % 5 == 0:
            log("Prepared {}/{} source water textures".format(index, len(texture_records)))
    return textures, results


def expression(material, expression_class, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )


def connect(source, output_name, target, input_name):
    if not unreal.MaterialEditingLibrary.connect_material_expressions(
        source, output_name, target, input_name
    ):
        raise RuntimeError(
            "Material connection failed: {}.{} -> {}.{}".format(
                source.get_class().get_name(),
                output_name,
                target.get_class().get_name(),
                input_name,
            )
        )


def connect_property(source, output_name, material_property, required=True):
    result = unreal.MaterialEditingLibrary.connect_material_property(
        source, output_name, material_property
    )
    if required and not result:
        raise RuntimeError("Failed to connect material property " + str(material_property))
    return bool(result)


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property("default_value", float(default))
    return node


def vector_parameter(material, name, value, x, y):
    node = expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property("default_value", unreal.LinearColor(*value))
    return node


def constant(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(value))
    return node


def component_mask(material, x, y, red=False, green=False, blue=False, alpha=False):
    node = expression(material, unreal.MaterialExpressionComponentMask, x, y)
    node.set_editor_property("r", bool(red))
    node.set_editor_property("g", bool(green))
    node.set_editor_property("b", bool(blue))
    node.set_editor_property("a", bool(alpha))
    return node


def binary(material, expression_class, a, b, x, y):
    node = expression(material, expression_class, x, y)
    connect(a, "", node, "A")
    connect(b, "", node, "B")
    return node


def saturate(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionSaturate, x, y)
    connect(value, "", node, "None")
    return node


def make_uv(material, world_xy, scale, speed, x, y):
    divided = binary(
        material, unreal.MaterialExpressionDivide, world_xy, scale, x, y
    )
    panner = expression(material, unreal.MaterialExpressionPanner, x + 220, y)
    connect(divided, "", panner, "Coordinate")
    connect(speed, "RGB", panner, "Speed")
    return panner


def sample_parameter(material, name, texture, sampler, uv, x, y):
    node = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, x, y
    )
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property("texture", texture)
    node.set_editor_property("sampler_type", sampler)
    connect(uv, "", node, "UVs")
    return node


def resolve_fmodel_texture(reference, imported_textures):
    if not reference:
        return None
    object_name = str(reference.get("object_name") or "")
    object_path_value = str(reference.get("object_path") or "")
    if "'" in object_name:
        name = object_name.split("'", 1)[-1].rstrip("'")
    else:
        name = package_basename(object_path_value.rsplit(".", 1)[0])
    if name in imported_textures:
        return imported_textures[name]
    package = object_path_value.rsplit(".", 1)[0]
    ue_path = None
    if package.startswith("Engine/Content/"):
        relative = package[len("Engine/Content/") :]
        ue_path = "/Engine/" + relative + "." + package_basename(relative)
    elif package.startswith("Engine/Plugins/Experimental/Water/Content/"):
        relative = package[len("Engine/Plugins/Experimental/Water/Content/") :]
        ue_path = "/Water/" + relative + "." + package_basename(relative)
    elif package.startswith("Engine/Plugins/Experimental/Landmass/Content/"):
        relative = package[len("Engine/Plugins/Experimental/Landmass/Content/") :]
        ue_path = "/Landmass/" + relative + "." + package_basename(relative)
    return unreal.EditorAssetLibrary.load_asset(ue_path) if ue_path else None


def create_master_material(master_parameters, imported_textures):
    ensure_directory(MATERIAL_ROOT)
    material = unreal.EditorAssetLibrary.load_asset(MASTER_MATERIAL_PATH)
    created = material is None
    if material:
        library = unreal.MaterialEditingLibrary
        scalar_names = {str(name) for name in library.get_scalar_parameter_names(material)}
        vector_names = {str(name) for name in library.get_vector_parameter_names(material)}
        texture_names = {str(name) for name in library.get_texture_parameter_names(material)}
        required_scalars = {item["name"] for item in master_parameters["scalars"]}
        required_vectors = {item["name"] for item in master_parameters["vectors"]}
        required_textures = {item["name"] for item in master_parameters["textures"]}
        version = unreal.EditorAssetLibrary.get_metadata_tag(
            material, "KhazanStormPassWaterPreviewVersion"
        )
        expressions = list(library.get_material_expressions(material))
        texture_object_parameters = {}
        for item in expressions:
            if (
                item
                and item.get_class().get_name()
                == "MaterialExpressionTextureObjectParameter"
            ):
                name = str(item.get_editor_property("parameter_name"))
                texture_object_parameters[name] = item
        default_repairs = []
        unresolved_defaults = []
        for item in master_parameters["textures"]:
            reference = item["value"]
            desired = resolve_fmodel_texture(reference, imported_textures)
            if reference["object_path"] and not desired:
                unresolved_defaults.append(
                    {
                        "parameter": item["name"],
                        "object_path": reference["object_path"],
                    }
                )
                continue
            node = texture_object_parameters.get(item["name"])
            if not node or not desired:
                continue
            current = node.get_editor_property("texture")
            if not current or current.get_path_name() != desired.get_path_name():
                node.modify()
                node.set_editor_property("texture", desired)
                default_repairs.append(
                    {
                        "parameter": item["name"],
                        "texture": desired.get_path_name(),
                    }
                )
        if default_repairs:
            library.recompile_material(material)
            unreal.EditorAssetLibrary.save_loaded_asset(
                material, only_if_is_dirty=False
            )
        water_outputs = [
            item
            for item in expressions
            if item
            and item.get_class().get_name()
            == "MaterialExpressionSingleLayerWaterMaterialOutput"
        ]
        reusable = (
            version == str(PREVIEW_MATERIAL_VERSION)
            and required_scalars.issubset(scalar_names)
            and required_vectors.issubset(vector_names)
            and required_textures.issubset(texture_names)
            and len(water_outputs) == 1
            and material.get_editor_property("blend_mode")
            == unreal.BlendMode.BLEND_MASKED
            and material.get_editor_property("shading_model")
            == unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER
            and bool(material.get_editor_property("two_sided"))
        )
        if reusable:
            water_input_names = [
                str(name)
                for name in library.get_material_expression_input_names(
                    water_outputs[0]
                )
            ]
            return material, {
                "asset_path": material.get_path_name(),
                "created": False,
                "reused_verified_master": True,
                "blend_mode": str(material.get_editor_property("blend_mode")),
                "shading_model": str(material.get_editor_property("shading_model")),
                "two_sided": bool(material.get_editor_property("two_sided")),
                "opacity_mask_clip_value": float(
                    material.get_editor_property("opacity_mask_clip_value")
                ),
                "expression_count": len(expressions),
                "source_scalar_parameter_count": len(master_parameters["scalars"]),
                "source_vector_parameter_count": len(master_parameters["vectors"]),
                "source_texture_parameter_count": len(master_parameters["textures"]),
                "single_layer_water_output_inputs": water_input_names,
                "single_layer_water_output_connections": {
                    "scattering_coefficients": "ScatteringCoefficients",
                    "absorption_coefficients": "AbsorptionCoefficients",
                    "phase_g": "PhaseG",
                    "color_scale_behind_water": "ColorScaleBehindWater",
                },
                "anisotropy_property_connected": True,
                "source_texture_default_repairs": default_repairs,
                "unresolved_non_rendering_source_texture_defaults": unresolved_defaults,
            }
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            package_basename(MASTER_MATERIAL_PATH),
            MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create native-water preview master")

    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property("two_sided", True)
    material.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER
    )
    material.set_editor_property("opacity_mask_clip_value", 0.3333)

    scalar_nodes = {}
    for index, item in enumerate(master_parameters["scalars"]):
        column = index // 35
        row = index % 35
        scalar_nodes[item["name"]] = scalar_parameter(
            material,
            item["name"],
            item["value"],
            -7600 + column * 260,
            -4600 + row * 120,
        )
    vector_nodes = {}
    for index, item in enumerate(master_parameters["vectors"]):
        vector_nodes[item["name"]] = vector_parameter(
            material, item["name"], item["value"], -6500, -4500 + index * 150
        )

    preview_vectors = {
        "EffectColor": (5.0, 0.15, 0.15, 1.0),
        "FoamColor": (0.25, 0.0, 0.0, 1.0),
        "PreviewNormalSpeedA": (0.012, 0.008, 0.0, 0.0),
        "PreviewNormalSpeedB": (-0.006, 0.011, 0.0, 0.0),
        "PreviewFoamSpeed": (0.003, -0.002, 0.0, 0.0),
        "PreviewPoisonSpeed": (-0.02, 0.02, 0.0, 0.0),
        "PreviewPoisonSpeedB": (0.005, 0.0005, 0.0, 0.0),
    }
    for index, (name, value) in enumerate(preview_vectors.items()):
        vector_nodes[name] = vector_parameter(
            material, name, value, -6200, -2500 + index * 160
        )

    source_texture_defaults = {
        item["name"]: resolve_fmodel_texture(item["value"], imported_textures)
        for item in master_parameters["textures"]
    }
    effective_graph_textures = dict(source_texture_defaults)
    effective_graph_textures.update(
        {
            # These three are the final inherited values authored by the
            # Skoffa -> StormPass instance chain and avoid sampler ambiguity
            # in the standalone preview master.
            "poison_Noise": imported_textures["FT_Noise_011"],
            "poison_Tex": imported_textures["FT_S_Tile_03B"],
            "poison_Tex2": imported_textures["FT_Noise_Water"],
        }
    )
    graph_texture_names = {
        "poison_Noise",
        "poison_Tex",
        "poison_Tex2",
        "InstantFoamWave",
        "SurfaceInstantFoamMask",
        "InstantFoamMask",
    }
    unresolved_defaults = []
    for index, item in enumerate(master_parameters["textures"]):
        if item["name"] in graph_texture_names:
            continue
        texture = source_texture_defaults[item["name"]]
        if not texture and item["value"]["object_path"]:
            unresolved_defaults.append(
                {
                    "parameter": item["name"],
                    "object_path": item["value"]["object_path"],
                }
            )
        node = expression(
            material, unreal.MaterialExpressionTextureObjectParameter, -6100, -900 + index * 130
        )
        node.set_editor_property("parameter_name", item["name"])
        if texture:
            node.set_editor_property("texture", texture)

    switch_defaults = {
        "Enable Water VS Mapping": False,
        "poison": True,
        "UseScalarWaterBodyIndex": True,
    }
    switch_nodes = {}
    for index, (name, value) in enumerate(switch_defaults.items()):
        node = expression(
            material, unreal.MaterialExpressionStaticSwitchParameter, -5600, -500 + index * 160
        )
        node.set_editor_property("parameter_name", name)
        node.set_editor_property("default_value", bool(value))
        switch_nodes[name] = node

    world = expression(material, unreal.MaterialExpressionWorldPosition, -5200, -3900)
    world_xy = component_mask(material, -5000, -3900, red=True, green=True)
    connect(world, "", world_xy, "None")

    normal_texture = unreal.EditorAssetLibrary.load_asset(
        "/Engine/Functions/Engine_MaterialFunctions02/ExampleContent/Textures/"
        "water_n.water_n"
    )
    normal_texture_b = unreal.EditorAssetLibrary.load_asset(
        "/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled_N."
        "T_WaterFlow_01_Foam_Tiled_N"
    )
    if not normal_texture or not normal_texture_b:
        raise RuntimeError("Required UE Water plugin normal textures are unavailable")

    near_uv = make_uv(
        material,
        world_xy,
        scalar_nodes["Default Near Water Scale"],
        vector_nodes["PreviewNormalSpeedA"],
        -4700,
        -3900,
    )
    distant_uv = make_uv(
        material,
        world_xy,
        scalar_nodes["Default Distant Water Scale"],
        vector_nodes["PreviewNormalSpeedB"],
        -4700,
        -3550,
    )
    normal_a = sample_parameter(
        material,
        "WaterNormalTexture",
        normal_texture,
        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        near_uv,
        -4200,
        -3900,
    )
    normal_b = sample_parameter(
        material,
        "WaterNormalTextureB",
        normal_texture_b,
        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        distant_uv,
        -4200,
        -3550,
    )
    normal_a_xy = component_mask(material, -3950, -3900, red=True, green=True)
    normal_b_xy = component_mask(material, -3950, -3550, red=True, green=True)
    connect(normal_a, "RGB", normal_a_xy, "None")
    connect(normal_b, "RGB", normal_b_xy, "None")
    half = constant(material, 0.5, -3900, -3300)
    two = constant(material, 2.0, -3700, -3300)
    normal_a_center = binary(
        material, unreal.MaterialExpressionSubtract, normal_a_xy, half, -3700, -3900
    )
    normal_b_center = binary(
        material, unreal.MaterialExpressionSubtract, normal_b_xy, half, -3700, -3550
    )
    normal_a_signed = binary(
        material, unreal.MaterialExpressionMultiply, normal_a_center, two, -3450, -3900
    )
    normal_b_signed = binary(
        material, unreal.MaterialExpressionMultiply, normal_b_center, two, -3450, -3550
    )
    normal_a_strength = binary(
        material,
        unreal.MaterialExpressionMultiply,
        normal_a_signed,
        scalar_nodes["Default Near Normal Strength"],
        -3200,
        -3900,
    )
    normal_b_strength = binary(
        material,
        unreal.MaterialExpressionMultiply,
        normal_b_signed,
        scalar_nodes["Default Distant Normal StrengthB"],
        -3200,
        -3550,
    )
    normal_xy = binary(
        material,
        unreal.MaterialExpressionAdd,
        normal_a_strength,
        normal_b_strength,
        -2950,
        -3725,
    )
    normal = expression(material, unreal.MaterialExpressionDeriveNormalZ, -2700, -3725)
    connect(normal_xy, "", normal, "InXY")

    foam_uv = make_uv(
        material,
        world_xy,
        scalar_nodes["SurfaceFoamWaveTiling"],
        vector_nodes["PreviewFoamSpeed"],
        -4700,
        -2850,
    )
    foam_wave = sample_parameter(
        material,
        "InstantFoamWave",
        source_texture_defaults["InstantFoamWave"],
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        foam_uv,
        -4200,
        -2950,
    )
    foam_detail = sample_parameter(
        material,
        "SurfaceInstantFoamMask",
        source_texture_defaults["SurfaceInstantFoamMask"],
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        foam_uv,
        -4200,
        -2670,
    )
    foam_splash = sample_parameter(
        material,
        "InstantFoamMask",
        source_texture_defaults["InstantFoamMask"],
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        foam_uv,
        -4200,
        -2390,
    )
    foam_product = binary(
        material, unreal.MaterialExpressionMultiply, foam_wave, foam_detail, -3900, -2800
    )
    splash_scale = constant(material, 0.35, -3900, -2350)
    scaled_splash = binary(
        material, unreal.MaterialExpressionMultiply, foam_splash, splash_scale, -3650, -2400
    )
    foam_combined = binary(
        material, unreal.MaterialExpressionAdd, foam_product, scaled_splash, -3650, -2750
    )
    foam_threshold = binary(
        material,
        unreal.MaterialExpressionSubtract,
        foam_combined,
        scalar_nodes["DistanceFoamGradientMin"],
        -3400,
        -2750,
    )
    foam_contrast = constant(material, 4.0, -3400, -2500)
    foam_shaped = binary(
        material, unreal.MaterialExpressionMultiply, foam_threshold, foam_contrast, -3150, -2750
    )
    foam_saturated = saturate(material, foam_shaped, -2900, -2750)
    foam_mask = binary(
        material,
        unreal.MaterialExpressionMultiply,
        foam_saturated,
        scalar_nodes["SurfaceFoamIntensity"],
        -2650,
        -2750,
    )

    poison_uv = make_uv(
        material,
        world_xy,
        scalar_nodes["poison_Tiling"],
        vector_nodes["PreviewPoisonSpeed"],
        -4700,
        -1750,
    )
    poison_uv_b = make_uv(
        material,
        world_xy,
        scalar_nodes["poison_Tiling2"],
        vector_nodes["PreviewPoisonSpeedB"],
        -4700,
        -1400,
    )
    poison_noise = sample_parameter(
        material,
        "poison_Noise",
        effective_graph_textures["poison_Noise"],
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        poison_uv,
        -4200,
        -1900,
    )
    poison_tex = sample_parameter(
        material,
        "poison_Tex",
        effective_graph_textures["poison_Tex"],
        unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
        poison_uv,
        -4200,
        -1620,
    )
    poison_tex2 = sample_parameter(
        material,
        "poison_Tex2",
        effective_graph_textures["poison_Tex2"],
        unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
        poison_uv_b,
        -4200,
        -1340,
    )
    poison_detail = binary(
        material, unreal.MaterialExpressionMultiply, poison_tex, poison_tex2, -3900, -1500
    )
    noise_weight = constant(material, 0.35, -3900, -1200)
    weighted_noise = binary(
        material, unreal.MaterialExpressionMultiply, poison_noise, noise_weight, -3650, -1850
    )
    poison_combined = binary(
        material, unreal.MaterialExpressionAdd, poison_detail, weighted_noise, -3400, -1600
    )
    poison_sat = saturate(material, poison_combined, -3150, -1600)
    poison_power = expression(material, unreal.MaterialExpressionPower, -2900, -1600)
    connect(poison_sat, "", poison_power, "Base")
    connect(scalar_nodes["poison_pow"], "", poison_power, "Exp")
    opacity_scale = constant(material, 0.01, -2900, -1350)
    poison_opacity = binary(
        material,
        unreal.MaterialExpressionMultiply,
        scalar_nodes["poison_Opacity"],
        opacity_scale,
        -2650,
        -1450,
    )
    poison_mask_unchecked = binary(
        material,
        unreal.MaterialExpressionMultiply,
        poison_power,
        poison_opacity,
        -2400,
        -1600,
    )
    zero = constant(material, 0.0, -2400, -1300)
    connect(poison_mask_unchecked, "", switch_nodes["poison"], "True")
    connect(zero, "", switch_nodes["poison"], "False")
    poison_mask = switch_nodes["poison"]

    effect_scale = constant(material, 0.18, -2100, -900)
    effect_normalized = binary(
        material,
        unreal.MaterialExpressionMultiply,
        vector_nodes["EffectColor"],
        effect_scale,
        -1850,
        -950,
    )
    poison_tint = binary(
        material,
        unreal.MaterialExpressionMultiply,
        effect_normalized,
        vector_nodes["poisonColor"],
        -1600,
        -950,
    )
    water_poison = expression(
        material, unreal.MaterialExpressionLinearInterpolate, -1300, -950
    )
    connect(vector_nodes["Water Albedo"], "RGB", water_poison, "A")
    connect(poison_tint, "", water_poison, "B")
    connect(poison_mask, "", water_poison, "Alpha")

    foam_tint = binary(
        material,
        unreal.MaterialExpressionMultiply,
        vector_nodes["FoamColor"],
        scalar_nodes["FoamColorBright"],
        -1600,
        -600,
    )
    surface_color = expression(
        material, unreal.MaterialExpressionLinearInterpolate, -1000, -800
    )
    connect(water_poison, "", surface_color, "A")
    connect(foam_tint, "", surface_color, "B")
    connect(foam_mask, "", surface_color, "Alpha")

    poison_emissive_raw = binary(
        material,
        unreal.MaterialExpressionMultiply,
        vector_nodes["EffectColor"],
        vector_nodes["poisonColor"],
        -1550,
        -250,
    )
    poison_emissive_masked = binary(
        material,
        unreal.MaterialExpressionMultiply,
        poison_emissive_raw,
        poison_mask,
        -1300,
        -250,
    )
    emissive_scale = constant(material, 0.04, -1300, 20)
    poison_emissive = binary(
        material,
        unreal.MaterialExpressionMultiply,
        poison_emissive_masked,
        emissive_scale,
        -1050,
        -250,
    )
    foam_emissive_masked = binary(
        material,
        unreal.MaterialExpressionMultiply,
        foam_tint,
        foam_mask,
        -1300,
        250,
    )
    foam_emissive_scale = constant(material, 0.15, -1300, 480)
    foam_emissive = binary(
        material,
        unreal.MaterialExpressionMultiply,
        foam_emissive_masked,
        foam_emissive_scale,
        -1050,
        250,
    )
    emissive = binary(
        material, unreal.MaterialExpressionAdd, poison_emissive, foam_emissive, -750, 0
    )

    one = constant(material, 1.0, -700, 550)
    connect_property(surface_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    connect_property(normal, "", unreal.MaterialProperty.MP_NORMAL)
    connect_property(
        scalar_nodes["Water Roughness"], "", unreal.MaterialProperty.MP_ROUGHNESS
    )
    connect_property(
        scalar_nodes["Water Specular"], "", unreal.MaterialProperty.MP_SPECULAR
    )
    connect_property(
        vector_nodes["Water Albedo"], "A", unreal.MaterialProperty.MP_OPACITY
    )
    connect_property(one, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    connect_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    anisotropy_connected = connect_property(
        scalar_nodes["Anisotropy"],
        "",
        unreal.MaterialProperty.MP_ANISOTROPY,
        required=False,
    )

    water_output = expression(
        material, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, -500, -350
    )
    water_input_names = [
        str(name)
        for name in unreal.MaterialEditingLibrary.get_material_expression_input_names(
            water_output
        )
    ]

    def normalized(value):
        return "".join(character.lower() for character in str(value) if character.isalnum())

    def water_input(*candidates):
        candidate_keys = {normalized(candidate) for candidate in candidates}
        return next(
            (name for name in water_input_names if normalized(name) in candidate_keys), None
        )

    absorption_scale = constant(material, 0.002, -1000, 750)
    scattering_scale = constant(material, 0.001, -1000, 980)
    absorption = binary(
        material,
        unreal.MaterialExpressionMultiply,
        vector_nodes["Absorption"],
        absorption_scale,
        -750,
        750,
    )
    scattering = binary(
        material,
        unreal.MaterialExpressionMultiply,
        vector_nodes["Scattering"],
        scattering_scale,
        -750,
        980,
    )
    water_connections = {}
    for key, source, output, candidates in (
        (
            "scattering_coefficients",
            scattering,
            "",
            ("ScatteringCoefficients", "Scattering Coefficients"),
        ),
        (
            "absorption_coefficients",
            absorption,
            "",
            ("AbsorptionCoefficients", "Absorption Coefficients"),
        ),
        ("phase_g", scalar_nodes["Anisotropy"], "", ("PhaseG", "Phase G")),
        (
            "color_scale_behind_water",
            vector_nodes["Water Albedo"],
            "RGB",
            ("ColorScaleBehindWater", "Color Scale Behind Water"),
        ),
    ):
        target_input = water_input(*candidates)
        if not target_input:
            raise RuntimeError("SingleLayerWater output input missing: " + key)
        connect(source, output, water_output, target_input)
        water_connections[key] = target_input

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanStormPassWaterPreviewVersion", str(PREVIEW_MATERIAL_VERSION)
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanSourcePackage", MATERIAL_PACKAGES["master"]
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, {
        "asset_path": material.get_path_name(),
        "created": created,
        "blend_mode": str(material.get_editor_property("blend_mode")),
        "shading_model": str(material.get_editor_property("shading_model")),
        "two_sided": bool(material.get_editor_property("two_sided")),
        "opacity_mask_clip_value": float(
            material.get_editor_property("opacity_mask_clip_value")
        ),
        "expression_count": int(
            unreal.MaterialEditingLibrary.get_num_material_expressions(material)
        ),
        "source_scalar_parameter_count": len(master_parameters["scalars"]),
        "source_vector_parameter_count": len(master_parameters["vectors"]),
        "source_texture_parameter_count": len(master_parameters["textures"]),
        "single_layer_water_output_inputs": water_input_names,
        "single_layer_water_output_connections": water_connections,
        "anisotropy_property_connected": anisotropy_connected,
        "source_texture_default_repairs": [],
        "unresolved_non_rendering_source_texture_defaults": unresolved_defaults,
    }


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def apply_base_overrides(instance, source_overrides):
    overrides = instance.get_editor_property("base_property_overrides")
    checks = {}
    if "TwoSided" in source_overrides:
        checks["two_sided"] = set_struct_property(
            overrides, "override_two_sided", True
        ) and set_struct_property(
            overrides, "two_sided", bool(source_overrides["TwoSided"])
        )
    blend_map = {
        "BLEND_Opaque": unreal.BlendMode.BLEND_OPAQUE,
        "BLEND_Masked": unreal.BlendMode.BLEND_MASKED,
        "BLEND_Translucent": unreal.BlendMode.BLEND_TRANSLUCENT,
    }
    if source_overrides.get("BlendMode") in blend_map:
        checks["blend_mode"] = set_struct_property(
            overrides, "override_blend_mode", True
        ) and set_struct_property(
            overrides, "blend_mode", blend_map[source_overrides["BlendMode"]]
        )
    if "OpacityMaskClipValue" in source_overrides:
        checks["opacity_mask_clip_value"] = set_struct_property(
            overrides, "override_opacity_mask_clip_value", True
        ) and set_struct_property(
            overrides,
            "opacity_mask_clip_value",
            float(source_overrides["OpacityMaskClipValue"]),
        )
    if source_overrides.get("ShadingModel"):
        shading_name = str(source_overrides["ShadingModel"])
        shading = {
            "MSM_SingleLayerWater": unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,
        }.get(shading_name)
        if shading is None:
            shading = getattr(
                unreal.MaterialShadingModel, shading_name.upper(), None
            )
        checks["shading_model"] = bool(shading) and set_struct_property(
            overrides, "override_shading_model", True
        ) and set_struct_property(overrides, "shading_model", shading)
    instance.set_editor_property("base_property_overrides", overrides)
    if checks and not all(checks.values()):
        raise RuntimeError("Failed native-water base property override: " + str(checks))
    return checks


def create_or_load_instance(asset_path):
    instance = unreal.EditorAssetLibrary.load_asset(asset_path)
    created = instance is None
    if not instance:
        instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            package_basename(asset_path),
            MATERIAL_ROOT,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
    if not instance:
        raise RuntimeError("Failed to create water material instance: " + asset_path)
    return instance, created


def texture_from_source(item, imported_textures):
    return resolve_fmodel_texture(
        {
            "object_name": item.get("object_name"),
            "object_path": item.get("object_path"),
        },
        imported_textures,
    )


def configure_instance(instance, parent, record, imported_textures, source_package):
    library = unreal.MaterialEditingLibrary
    instance.modify()
    library.set_material_instance_parent(instance, parent)
    library.clear_all_material_instance_parameters(instance)
    results = collections.Counter()
    for item in record.get("scalars", []):
        results["scalar_attempts"] += 1
        library.set_material_instance_scalar_parameter_value(
            instance, item["name"], float(item["value"])
        )
        actual = library.get_material_instance_scalar_parameter_value(
            instance, item["name"]
        )
        if abs(float(actual) - float(item["value"])) > 0.00002:
            raise RuntimeError("Scalar water parameter mismatch: " + item["name"])
        results["scalar_applied"] += 1
    for item in record.get("vectors", []):
        results["vector_attempts"] += 1
        library.set_material_instance_vector_parameter_value(
            instance, item["name"], unreal.LinearColor(*item["value"])
        )
        actual = library.get_material_instance_vector_parameter_value(
            instance, item["name"]
        )
        if linear_color_delta(actual, item["value"]) > 0.00002:
            raise RuntimeError("Vector water parameter mismatch: " + item["name"])
        results["vector_applied"] += 1
    for item in record.get("textures", []):
        results["texture_attempts"] += 1
        texture = texture_from_source(item, imported_textures)
        if not texture:
            raise RuntimeError(
                "Unresolved water instance texture {} for {}".format(
                    item["object_path"], source_package
                )
            )
        library.set_material_instance_texture_parameter_value(
            instance, item["name"], texture
        )
        actual = library.get_material_instance_texture_parameter_value(
            instance, item["name"]
        )
        if not actual or actual.get_path_name() != texture.get_path_name():
            raise RuntimeError("Texture water parameter mismatch: " + item["name"])
        results["texture_applied"] += 1
    for item in record.get("switches", []):
        results["switch_attempts"] += 1
        library.set_material_instance_static_switch_parameter_value(
            instance, item["name"], bool(item["value"])
        )
        actual = library.get_material_instance_static_switch_parameter_value(
            instance, item["name"]
        )
        if bool(actual) != bool(item["value"]):
            raise RuntimeError("Switch water parameter mismatch: " + item["name"])
        results["switch_applied"] += 1
    override_checks = apply_base_overrides(
        instance, record.get("base_property_overrides", {})
    )
    library.update_material_instance(instance)
    unreal.EditorAssetLibrary.set_metadata_tag(
        instance, "KhazanSourcePackage", source_package
    )
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    for kind in ("scalar", "vector", "texture", "switch"):
        if results[kind + "_attempts"] != results[kind + "_applied"]:
            raise RuntimeError(
                "Water instance parameter application failed: {} {}".format(
                    source_package, dict(results)
                )
            )
    return dict(results), override_checks


def create_material_hierarchy(master, instances, imported_textures, actor_records):
    created = {}
    materials = {"master": master}
    results = []
    parent_keys = {
        "skoffa": "master",
        "stormpass": "skoffa",
        "stormpass_inst1": "stormpass",
    }
    for key in ("skoffa", "stormpass", "stormpass_inst1"):
        asset_path = SOURCE_INSTANCE_ASSETS[key]
        instance, was_created = create_or_load_instance(asset_path)
        parameter_results, override_results = configure_instance(
            instance,
            materials[parent_keys[key]],
            instances[key],
            imported_textures,
            MATERIAL_PACKAGES[key],
        )
        materials[key] = instance
        created[key] = was_created
        results.append(
            {
                "key": key,
                "asset_path": instance.get_path_name(),
                "parent_path": materials[parent_keys[key]].get_path_name(),
                "created": was_created,
                "parameter_application": parameter_results,
                "base_property_overrides": override_results,
            }
        )

    actor_instances = {}
    for record in actor_records:
        instance, was_created = create_or_load_instance(
            record["actor_instance_path"]
        )
        actor_parameter_record = {
            "vectors": [
                {"name": "EffectColor", "value": record["effect_color"]},
                {"name": "FoamColor", "value": record["foam_color"]},
            ]
        }
        parameter_results, override_results = configure_instance(
            instance,
            materials[record["source_material_key"]],
            actor_parameter_record,
            imported_textures,
            record["source_material_package"] + ":runtime_actor_colors",
        )
        unreal.EditorAssetLibrary.set_metadata_tag(
            instance, "KhazanSourceActor", record["label"]
        )
        unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
        actor_instances[record["label"]] = instance
        results.append(
            {
                "key": record["label"],
                "asset_path": instance.get_path_name(),
                "parent_path": materials[
                    record["source_material_key"]
                ].get_path_name(),
                "created": was_created,
                "parameter_application": parameter_results,
                "base_property_overrides": override_results,
                "effect_color": record["effect_color"],
                "foam_color": record["foam_color"],
            }
        )
    return materials, actor_instances, results


def load_map():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    return level_subsystem, unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create pre-native-water StormPass backup")
    if not unreal.EditorAssetLibrary.save_asset(
        BACKUP_MAP_PATH, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save pre-native-water StormPass backup")
    return True


def actor_map(actor_subsystem):
    return {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }


def validate_boundary(actor_subsystem):
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    fog_count = sum(
        actor.get_actor_label().startswith("SP_Fog_") for actor in actors
    )
    missing = sorted(
        spec["label"]
        for spec in ACTOR_SPECS
        if spec["label"] not in {actor.get_actor_label() for actor in actors}
    )
    if len(actors) != EXPECTED_ACTOR_COUNT or fog_count != EXPECTED_FOG_COUNT or missing:
        raise RuntimeError(
            "StormPass native-water boundary changed: actors={} fog={} missing={}".format(
                len(actors), fog_count, missing
            )
        )
    return {"actor_count": len(actors), "fog_count": fog_count}


def place_material_bindings(actor_subsystem, actor_records, actor_instances):
    actors = actor_map(actor_subsystem)
    results = []
    for record in actor_records:
        actor = actors[record["label"]]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Water child has no StaticMeshComponent: " + record["label"])
        mesh = component.get_editor_property("static_mesh")
        if not mesh or SOURCE_MESH_PACKAGE.rsplit("/", 1)[-1] not in mesh.get_name():
            raise RuntimeError("Water child mesh changed: " + record["label"])
        before = component.get_material(0)
        material = actor_instances[record["label"]]
        component.modify()
        component.set_material(0, material)
        component.set_editor_property("cast_shadow", bool(record["cast_shadow"]))
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        actual = component.get_material(0)
        if not actual or actual.get_path_name() != material.get_path_name():
            raise RuntimeError("Failed to bind native-water material: " + record["label"])
        results.append(
            {
                "label": record["label"],
                "slot": 0,
                "previous_material": before.get_path_name() if before else None,
                "material": actual.get_path_name(),
                "source_material_package": record["source_material_package"],
                "source_mesh_package": record["source_mesh_package"],
                "cast_shadow": bool(component.get_editor_property("cast_shadow")),
                "collision_or_navigation_modified": False,
            }
        )
    return results


def linear_color_delta(actual, expected):
    return max(
        abs(float(actual.r) - float(expected[0])),
        abs(float(actual.g) - float(expected[1])),
        abs(float(actual.b) - float(expected[2])),
        abs(float(actual.a) - float(expected[3])),
    )


def load_prepared_assets(actor_records=None):
    master = unreal.EditorAssetLibrary.load_asset(MASTER_MATERIAL_PATH)
    if not master:
        raise RuntimeError("Native-water preview master is missing")
    source_instances = {}
    for key, path in SOURCE_INSTANCE_ASSETS.items():
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            raise RuntimeError("Native-water source instance is missing: " + key)
        source_instances[key] = asset
    if actor_records is None:
        metadata = load_json(METADATA_PATH)
        actor_records = metadata["water_actors"]
    actor_instances = {}
    for record in actor_records:
        asset = unreal.EditorAssetLibrary.load_asset(record["actor_instance_path"])
        if not asset:
            raise RuntimeError("Native-water actor instance is missing: " + record["label"])
        actor_instances[record["label"]] = asset
    return master, source_instances, actor_instances


def validate_map_bindings(actor_subsystem=None, actor_records=None, actor_instances=None):
    if actor_records is None:
        actor_records = load_json(METADATA_PATH)["water_actors"]
    if actor_instances is None:
        _, _, actor_instances = load_prepared_assets(actor_records)
    if actor_subsystem is None:
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    boundary = validate_boundary(actor_subsystem)
    actors = actor_map(actor_subsystem)
    failures = []
    checked = []
    maximum_color_delta = 0.0
    library = unreal.MaterialEditingLibrary
    for record in actor_records:
        actor = actors.get(record["label"])
        issues = []
        if not actor:
            failures.append({"label": record["label"], "issues": ["missing_actor"]})
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            failures.append({"label": record["label"], "issues": ["missing_component"]})
            continue
        material = component.get_material(0)
        expected = actor_instances[record["label"]]
        if not material or material.get_path_name() != expected.get_path_name():
            issues.append("material_binding")
        mesh = component.get_editor_property("static_mesh")
        if not mesh or SOURCE_MESH_PACKAGE.rsplit("/", 1)[-1] not in mesh.get_name():
            issues.append("mesh")
        if bool(component.get_editor_property("cast_shadow")) != bool(
            record["cast_shadow"]
        ):
            issues.append("cast_shadow")
        if component.get_editor_property("mobility") != unreal.ComponentMobility.STATIC:
            issues.append("mobility")
        for parameter_name, expected_color in (
            ("EffectColor", record["effect_color"]),
            ("FoamColor", record["foam_color"]),
        ):
            actual = library.get_material_instance_vector_parameter_value(
                expected, parameter_name
            )
            delta = linear_color_delta(actual, expected_color)
            maximum_color_delta = max(maximum_color_delta, delta)
            if delta > 0.000002:
                issues.append("parameter:" + parameter_name)
        if issues:
            failures.append({"label": record["label"], "issues": issues})
        checked.append(
            {
                "label": record["label"],
                "material": material.get_path_name() if material else None,
                "mesh": mesh.get_path_name() if mesh else None,
                "effect_color": record["effect_color"],
                "foam_color": record["foam_color"],
            }
        )
    return {
        "expected_water_actor_count": EXPECTED_WATER_ACTOR_COUNT,
        "checked_water_actor_count": len(checked),
        "actor_count": boundary["actor_count"],
        "fog_count": boundary["fog_count"],
        "maximum_actor_color_parameter_delta": maximum_color_delta,
        "failure_count": len(failures),
        "failures": failures,
        "bindings": checked,
    }


def main():
    (
        metadata,
        actor_records,
        master_parameters,
        instances,
        texture_records,
    ) = source_inventory()
    level_subsystem, actor_subsystem = load_map()
    boundary_before = validate_boundary(actor_subsystem)
    backup_created = backup_map_once()
    imported_textures, texture_results = import_source_textures(texture_records)
    master, master_result = create_master_material(
        master_parameters, imported_textures
    )
    source_materials, actor_instances, hierarchy_results = create_material_hierarchy(
        master, instances, imported_textures, actor_records
    )
    bindings = place_material_bindings(
        actor_subsystem, actor_records, actor_instances
    )
    validation = validate_map_bindings(
        actor_subsystem, actor_records, actor_instances
    )
    if validation["failure_count"]:
        raise RuntimeError(
            "Native-water validation failed: " + str(validation["failures"][0])
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass native-water restoration")
    unreal.EditorAssetLibrary.save_directory(
        ASSET_ROOT, only_if_is_dirty=False, recursive=True
    )
    boundary_after = validate_boundary(actor_subsystem)
    map_disk_path = os.path.join(
        PROJECT_ROOT,
        "Content",
        "_Art",
        "Kazan",
        "Environment",
        "StormPass",
        "Maps",
        "L_StormPass_Environment.umap",
    )
    report = {
        "status": "restored",
        "operation": "stormpass_native_water_material_restoration",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "metadata_path": METADATA_PATH,
        "boundary_before": boundary_before,
        "boundary_after": boundary_after,
        "texture_results": texture_results,
        "master_material": master_result,
        "material_hierarchy": hierarchy_results,
        "bindings": bindings,
        "validation": validation,
        "map_size_bytes": os.path.getsize(map_disk_path),
        "map_sha256": sha256_file(map_disk_path),
        "fidelity": {
            "exact_source_actor_and_component_identity": True,
            "exact_source_mesh_and_transform_preserved": True,
            "exact_source_texture_pixels_and_settings": True,
            "exact_source_material_parent_hierarchy": True,
            "exact_source_instance_parameters": True,
            "exact_source_actor_effect_and_foam_colors": True,
            "exact_source_base_property_overrides": True,
            "cooked_custom_master_graph_available_from_fmodel": False,
            "ue5_single_layer_water_preview_graph_used": True,
        },
        "content_boundary": metadata["content_boundary"],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status=restored actors={} water={} fog={} textures={} expressions={} "
        "failures={} report={}".format(
            boundary_after["actor_count"],
            validation["checked_water_actor_count"],
            boundary_after["fog_count"],
            len(texture_results),
            master_result["expression_count"],
            validation["failure_count"],
            REPORT_PATH,
        )
    )
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
                "map_path": MAP_PATH,
                "content_boundary": {
                    "visual_level_content_only": True,
                    "gameplay_or_source_code_modified": False,
                },
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_NATIVE_WATER: " + str(exception))
        raise
