"""Prepare the exact StormPass fog meshes/texture and UE5 preview materials.

FModel preserves the authored meshes, noise texture and every per-instance
parameter, but cooked custom material graphs are not exported.  This pass is
therefore intentionally asset-only: it imports the source geometry/texture and
builds three translucent, unlit preview parents matching the source parent and
two-sided variants.  It never creates or changes map actors.
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_FogMaterials.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Fog_AssetPreparation.json",
)
FOG_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/FogAssets"
MESH_ROOT = FOG_ROOT + "/Meshes"
TEXTURE_ROOT = FOG_ROOT + "/Textures"
MATERIAL_ROOT = FOG_ROOT + "/Materials"
NOISE_TEXTURE_PATH = TEXTURE_ROOT + "/T_FTW_Smoke_Noise_001"
NOISE_SOURCE_PATH = os.path.join(
    FMODEL_ROOT,
    "BBQ",
    "Content",
    "_Kazan_",
    "Art",
    "VFX",
    "VFX_Texture",
    "BBQ_Texture",
    "World",
    "FTW_Smoke_Noise_001.png",
)
MESH_SPECS = {
    "standard": {
        "source": os.path.join(
            FMODEL_ROOT,
            "BBQ",
            "Content",
            "_Kazan_",
            "Art",
            "VFX",
            "VFX_Mesh",
            "FS_FogSheet_Plane.usda",
        ),
        "source_name": "FS_FogSheet_Plane",
        "stage_name": "StormPass_FogSheet_Standard",
        "destination": MESH_ROOT + "/Standard",
    },
    "local": {
        "source": os.path.join(
            FMODEL_ROOT,
            "BBQ",
            "Content",
            "_Kazan_",
            "Art",
            "VFX",
            "VFX_Mesh",
            "BBQ_Mesh",
            "FS_W_FogSheet_Plane.usda",
        ),
        "source_name": "FS_W_FogSheet_Plane",
        "stage_name": "StormPass_FogSheet_Local",
        "destination": MESH_ROOT + "/Local",
    },
}
MATERIAL_SPECS = {
    "standard_one_sided": {
        "name": "M_SP_FogSheet_FMI_02_OneSided_V2",
        "kind": "standard",
        "two_sided": False,
        "source_parent": (
            "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/"
            "FMI_FogSheet_02"
        ),
    },
    "standard_two_sided": {
        "name": "M_SP_FogSheet_FMI_01_TwoSided_V2",
        "kind": "standard",
        "two_sided": True,
        "source_parent": (
            "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/"
            "FMI_FogSheet_01"
        ),
    },
    "local_two_sided": {
        "name": "M_SP_FogSheet_Local_TwoSided_V2",
        "kind": "local",
        "two_sided": True,
        "source_parent": (
            "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/BBQ_Material/World/"
            "FM_FogSheet_Local"
        ),
    },
}
KNOWN_SAFE_MAP_BOUNDARIES = {
    (14328, 0),  # base restoration before environment/Fog
    (14355, 0),  # environment complete, Fog deliberately deferred
    (14408, 53),  # complete reconstructed level; asset-only rerun
}
EXPECTED_SOURCE_FOG_COUNT = 53
PREVIEW_MATERIAL_VERSION = 2
FOG_DENSITY_CURVE_SCALE = 0.18
FOG_EMISSIVE_SCALE = 0.04
STANDARD_SCALARS = {
    "MaxOpacity": 0.8,
    "FadingStart": 100000.0,
    "TilingMaskProjectionDistance": 2048.0,
    "NoiseSize": 2048.0,
    "PanningSpeed": 0.05,
    "FadingReduction": 5000.0,
    "Rotator": 0.0,
    "NearFade": 50.0,
    "emmisivestrength": 1.0,
    "fresnelsize": 0.0,
    "RoundSize": 0.5,
    "fadedistance": 1000.0,
    "PreviewNearFadeMultiplier": 4.0,
    "PreviewAngleFadePower": 1.5,
}
LOCAL_SCALARS = {
    "MaxOpacity": 0.5,
    "FadingStart": 1000.0,
    "TexSize": 2.0,
    "Noise_Speed": 0.03,
    "FadingReduction": 1000000.0,
    "NearFade": 200.0,
    "emmisivestrength": 1.3,
    "fresnelsize": 0.0,
    "fadedistance": 500.0,
    "Noise_Density": 3.0,
    "Noise_Strength": 2.0,
    "PreviewNearFadeMultiplier": 2.0,
    "PreviewAngleFadePower": 1.5,
}


def log(message):
    unreal.log("KHAZAN_STORMPASS_FOG_ASSETS: " + str(message))


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


def asset_class_name(path):
    data = unreal.EditorAssetLibrary.find_asset_data(path)
    if not data or not data.is_valid():
        return "Invalid"
    return str(data.asset_class_path.asset_name)


def normalized_names(asset):
    names = {asset.get_name()}
    for prefix in ("SM_", "SK_", "T_", "M_", "MI_"):
        if asset.get_name().startswith(prefix):
            names.add(asset.get_name()[len(prefix) :])
    return names


def load_stormpass_and_snapshot():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
        world = editor_subsystem.get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    fog = [
        actor
        for actor in actors
        if actor.get_actor_label().startswith("SP_Fog_")
    ]
    unmanaged_native_fog = [
        actor.get_actor_label()
        for actor in actors
        if "Fog" in actor.get_class().get_name()
        and not actor.get_actor_label().startswith("SP_Fog_")
        and actor.get_actor_label() != "SP_Environment_HeightFog"
    ]
    result = {
        "world": world.get_path_name() if world else None,
        "actor_count": len(actors),
        "fog_actor_count": len(fog),
        "fog_labels": sorted(actor.get_actor_label() for actor in fog),
    }
    if (result["actor_count"], result["fog_actor_count"]) not in KNOWN_SAFE_MAP_BOUNDARIES:
        raise RuntimeError(
            "StormPass map boundary is not a known reconstruction state: {} / {}".format(
                result["actor_count"], result["fog_actor_count"]
            )
        )
    if unmanaged_native_fog:
        raise RuntimeError("StormPass contains unmanaged native Fog content")
    return result


def imported_static_meshes(root):
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    result = []
    for path in unreal.EditorAssetLibrary.list_assets(
        root, recursive=True, include_folder=False
    ):
        if asset_class_name(path) == "StaticMesh":
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if asset:
                result.append(asset)
    return result


def find_mesh(spec):
    matches = [
        mesh
        for mesh in imported_static_meshes(spec["destination"])
        if spec["source_name"] in normalized_names(mesh)
    ]
    if len(matches) > 1:
        raise RuntimeError("Multiple Fog mesh candidates: " + spec["source_name"])
    return matches[0] if matches else None


def import_mesh(key, spec):
    if not os.path.isfile(spec["source"]):
        raise RuntimeError("Fog mesh source is missing: " + spec["source"])
    ensure_directory(spec["destination"])
    existing = find_mesh(spec)
    if existing:
        return existing, False, []

    stage_path = os.path.join(
        unreal.Paths.project_saved_dir(),
        "ImportSources",
        spec["stage_name"] + ".usda",
    )
    os.makedirs(os.path.dirname(stage_path), exist_ok=True)
    with open(stage_path, "w", encoding="utf-8", newline="\n") as output:
        output.write(
            '#usda 1.0\n(\n    metersPerUnit = 0.01\n    upAxis = "Z"\n'
            "    subLayers = [\n        @{}@\n    ]\n)\n".format(
                spec["source"].replace("\\", "/")
            )
        )

    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", False)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", ["/"])
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("merge_identical_material_slots", False)
    options.set_editor_property("prim_path_folder_structure", False)
    options.set_editor_property(
        "existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE
    )

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", stage_path)
    task.set_editor_property("destination_path", spec["destination"])
    task.set_editor_property("destination_name", spec["stage_name"])
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = find_mesh(spec)
    if not mesh:
        raise RuntimeError("Fog mesh import failed: " + key)
    return mesh, True, list(task.get_editor_property("imported_object_paths"))


def import_noise_texture():
    texture = unreal.EditorAssetLibrary.load_asset(NOISE_TEXTURE_PATH)
    imported = False
    imported_paths = []
    if not texture:
        if not os.path.isfile(NOISE_SOURCE_PATH):
            raise RuntimeError("Fog noise source is missing: " + NOISE_SOURCE_PATH)
        ensure_directory(TEXTURE_ROOT)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", NOISE_SOURCE_PATH)
        task.set_editor_property("destination_path", TEXTURE_ROOT)
        task.set_editor_property("destination_name", "T_FTW_Smoke_Noise_001")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.TextureFactory())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported_paths = list(task.get_editor_property("imported_object_paths"))
        texture = unreal.EditorAssetLibrary.load_asset(NOISE_TEXTURE_PATH)
        imported = True
    if not texture:
        raise RuntimeError("Fog noise texture import failed")
    texture.modify()
    texture.set_editor_property("srgb", False)
    texture.set_editor_property(
        "compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE
    )
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
    return texture, imported, imported_paths


def expression(material, expression_class, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default))
    return node


def vector_parameter(material, name, value, x, y):
    node = expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", unreal.LinearColor(*value))
    return node


def constant(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(value))
    return node


def connect(source, source_output, target, target_input):
    if not unreal.MaterialEditingLibrary.connect_material_expressions(
        source, source_output, target, target_input
    ):
        raise RuntimeError(
            "Material connection failed: {}.{} -> {}.{}".format(
                source.get_class().get_name(),
                source_output,
                target.get_class().get_name(),
                target_input,
            )
        )


def component_mask(material, x, y, red=False, green=False):
    node = expression(material, unreal.MaterialExpressionComponentMask, x, y)
    node.set_editor_property("r", red)
    node.set_editor_property("g", green)
    node.set_editor_property("b", False)
    node.set_editor_property("a", False)
    return node


def build_edge_mask(material, texcoord, exponent, x, y):
    center = constant(material, 0.5, x, y + 160)
    centered = expression(material, unreal.MaterialExpressionSubtract, x + 200, y)
    absolute = expression(material, unreal.MaterialExpressionAbs, x + 400, y)
    two = constant(material, 2.0, x + 400, y + 170)
    scaled = expression(material, unreal.MaterialExpressionMultiply, x + 600, y)
    mask_u = component_mask(material, x + 800, y - 70, red=True)
    mask_v = component_mask(material, x + 800, y + 80, green=True)
    one_u = expression(material, unreal.MaterialExpressionOneMinus, x + 1000, y - 70)
    one_v = expression(material, unreal.MaterialExpressionOneMinus, x + 1000, y + 80)
    product = expression(material, unreal.MaterialExpressionMultiply, x + 1200, y)
    saturated = expression(material, unreal.MaterialExpressionSaturate, x + 1400, y)
    shaped = expression(material, unreal.MaterialExpressionPower, x + 1600, y)
    connect(texcoord, "", centered, "A")
    connect(center, "", centered, "B")
    connect(centered, "", absolute, "None")
    connect(absolute, "", scaled, "A")
    connect(two, "", scaled, "B")
    connect(scaled, "", mask_u, "None")
    connect(scaled, "", mask_v, "None")
    connect(mask_u, "", one_u, "None")
    connect(mask_v, "", one_v, "None")
    connect(one_u, "", product, "A")
    connect(one_v, "", product, "B")
    connect(product, "", saturated, "None")
    connect(saturated, "", shaped, "Base")
    connect(exponent, "", shaped, "Exp")
    return shaped


def build_distance_fades(material, opacity, params, x, y):
    depth_fade = expression(material, unreal.MaterialExpressionDepthFade, x, y)
    world_position = expression(material, unreal.MaterialExpressionWorldPosition, x, y + 230)
    camera_position = expression(material, unreal.MaterialExpressionCameraPositionWS, x, y + 390)
    camera_distance = expression(material, unreal.MaterialExpressionDistance, x + 220, y + 300)
    near_distance = expression(material, unreal.MaterialExpressionMultiply, x + 220, y + 500)
    near_divide = expression(material, unreal.MaterialExpressionDivide, x + 440, y + 300)
    near = expression(material, unreal.MaterialExpressionSaturate, x + 660, y + 300)
    far_subtract = expression(material, unreal.MaterialExpressionSubtract, x + 440, y + 530)
    far_divide = expression(material, unreal.MaterialExpressionDivide, x + 660, y + 530)
    far_saturate = expression(material, unreal.MaterialExpressionSaturate, x + 880, y + 530)
    far = expression(material, unreal.MaterialExpressionOneMinus, x + 1100, y + 530)

    normal = expression(material, unreal.MaterialExpressionPixelNormalWS, x + 440, y + 760)
    view = expression(material, unreal.MaterialExpressionCameraVectorWS, x + 440, y + 920)
    facing_dot = expression(material, unreal.MaterialExpressionDotProduct, x + 660, y + 830)
    facing_abs = expression(material, unreal.MaterialExpressionAbs, x + 880, y + 830)
    facing_saturate = expression(material, unreal.MaterialExpressionSaturate, x + 1100, y + 830)
    facing = expression(material, unreal.MaterialExpressionPower, x + 1320, y + 830)

    depth_near = expression(material, unreal.MaterialExpressionMultiply, x + 880, y + 100)
    distance_faded = expression(material, unreal.MaterialExpressionMultiply, x + 1320, y + 180)
    angle_faded = expression(material, unreal.MaterialExpressionMultiply, x + 1540, y + 250)
    saturated = expression(material, unreal.MaterialExpressionSaturate, x + 1760, y + 250)
    connect(opacity, "", depth_fade, "Opacity")
    connect(params["fadedistance"], "", depth_fade, "FadeDistance")
    connect(world_position, "", camera_distance, "A")
    connect(camera_position, "", camera_distance, "B")
    connect(params["NearFade"], "", near_distance, "A")
    connect(params["PreviewNearFadeMultiplier"], "", near_distance, "B")
    connect(camera_distance, "", near_divide, "A")
    connect(near_distance, "", near_divide, "B")
    connect(near_divide, "", near, "None")
    connect(camera_distance, "", far_subtract, "A")
    connect(params["FadingStart"], "", far_subtract, "B")
    connect(far_subtract, "", far_divide, "A")
    connect(params["FadingReduction"], "", far_divide, "B")
    connect(far_divide, "", far_saturate, "None")
    connect(far_saturate, "", far, "None")
    connect(depth_fade, "", depth_near, "A")
    connect(near, "", depth_near, "B")
    connect(depth_near, "", distance_faded, "A")
    connect(far, "", distance_faded, "B")
    connect(normal, "", facing_dot, "A")
    connect(view, "", facing_dot, "B")
    connect(facing_dot, "", facing_abs, "None")
    connect(facing_abs, "", facing_saturate, "None")
    connect(facing_saturate, "", facing, "Base")
    connect(params["PreviewAngleFadePower"], "", facing, "Exp")
    connect(distance_faded, "", angle_faded, "A")
    connect(facing, "", angle_faded, "B")
    connect(angle_faded, "", saturated, "None")
    return saturated


def create_material(spec, noise_texture):
    ensure_directory(MATERIAL_ROOT)
    path = MATERIAL_ROOT + "/" + spec["name"]
    material = unreal.EditorAssetLibrary.load_asset(path)
    created = material is None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            spec["name"],
            MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create Fog material: " + spec["name"])
    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("two_sided", bool(spec["two_sided"]))
    material.set_editor_property("disable_depth_test", False)
    try:
        material.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_UNLIT
        )
    except Exception:
        pass

    kind = spec["kind"]
    defaults = STANDARD_SCALARS if kind == "standard" else LOCAL_SCALARS
    params = {}
    y_cursor = -900
    for name, default in defaults.items():
        params[name] = scalar_parameter(material, name, default, -2200, y_cursor)
        y_cursor += 135
    pan = vector_parameter(
        material, "PreviewPanVector", (0.015, 0.005, 0.0, 0.0), -1900, -900
    )
    tint_name = "Uvcontrol" if kind == "standard" else "Color"
    tint = vector_parameter(material, tint_name, (1.0, 1.0, 1.0, 1.0), -200, -550)
    noise = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, -900, -480
    )
    noise.set_editor_property("parameter_name", "NoiseTexture")
    noise.set_editor_property("texture", noise_texture)
    texcoord = expression(material, unreal.MaterialExpressionTextureCoordinate, -1900, -450)

    if kind == "standard":
        reference_size = constant(material, 2048.0, -1900, -300)
        uv_scale = expression(material, unreal.MaterialExpressionDivide, -1680, -390)
        connect(reference_size, "", uv_scale, "A")
        connect(params["NoiseSize"], "", uv_scale, "B")
        edge_exponent = params["RoundSize"]
    else:
        uv_scale = expression(material, unreal.MaterialExpressionMultiply, -1680, -390)
        connect(params["TexSize"], "", uv_scale, "A")
        connect(params["Noise_Density"], "", uv_scale, "B")
        edge_exponent = constant(material, 0.7, -1680, 650)

    scaled_uv = expression(material, unreal.MaterialExpressionMultiply, -1460, -420)
    panner = expression(material, unreal.MaterialExpressionPanner, -1190, -450)
    connect(texcoord, "", scaled_uv, "A")
    connect(uv_scale, "", scaled_uv, "B")
    connect(scaled_uv, "", panner, "Coordinate")
    connect(pan, "RGB", panner, "Speed")
    connect(panner, "", noise, "UVs")
    noise_r = component_mask(material, -680, -480, red=True)
    connect(noise, "R", noise_r, "None")
    cloud = noise_r
    if kind == "local":
        noise_power = expression(material, unreal.MaterialExpressionPower, -450, -450)
        connect(noise_r, "", noise_power, "Base")
        connect(params["Noise_Strength"], "", noise_power, "Exp")
        cloud = noise_power

    edge = build_edge_mask(material, texcoord, edge_exponent, -1800, 600)
    cloud_edge = expression(material, unreal.MaterialExpressionMultiply, 100, -200)
    connect(cloud, "", cloud_edge, "A")
    connect(edge, "", cloud_edge, "B")

    negative_scale = constant(material, -FOG_DENSITY_CURVE_SCALE, 100, 20)
    negative_density = expression(material, unreal.MaterialExpressionMultiply, 330, 0)
    density_exp = expression(material, unreal.MaterialExpressionExponential2, 550, 0)
    density = expression(material, unreal.MaterialExpressionOneMinus, 770, 0)
    opacity = expression(material, unreal.MaterialExpressionMultiply, 990, -120)
    connect(params["MaxOpacity"], "", negative_density, "A")
    connect(negative_scale, "", negative_density, "B")
    connect(negative_density, "", density_exp, "None")
    connect(density_exp, "", density, "None")
    connect(cloud_edge, "", opacity, "A")
    connect(density, "", opacity, "B")
    opacity_final = build_distance_fades(material, opacity, params, 1220, -120)

    emissive_scale = constant(material, FOG_EMISSIVE_SCALE, 100, -700)
    emissive_amount = expression(material, unreal.MaterialExpressionMultiply, 330, -650)
    tinted = expression(material, unreal.MaterialExpressionMultiply, 550, -600)
    cloudy = expression(material, unreal.MaterialExpressionMultiply, 770, -550)
    emissive = expression(material, unreal.MaterialExpressionMultiply, 990, -500)
    connect(params["emmisivestrength"], "", emissive_amount, "A")
    connect(emissive_scale, "", emissive_amount, "B")
    connect(tint, "RGB", tinted, "A")
    connect(emissive_amount, "", tinted, "B")
    connect(tinted, "", cloudy, "A")
    connect(cloud, "", cloudy, "B")
    connect(cloudy, "", emissive, "A")
    connect(edge, "", emissive, "B")

    if not unreal.MaterialEditingLibrary.connect_material_property(
        opacity_final, "", unreal.MaterialProperty.MP_OPACITY
    ):
        raise RuntimeError("Failed to connect Fog opacity")
    if not unreal.MaterialEditingLibrary.connect_material_property(
        emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    ):
        raise RuntimeError("Failed to connect Fog emissive color")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanStormPassFogPreviewVersion", str(PREVIEW_MATERIAL_VERSION)
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanSourceParent", spec["source_parent"]
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, created


def material_audit(material, spec):
    library = unreal.MaterialEditingLibrary
    scalars = sorted(str(name) for name in library.get_scalar_parameter_names(material))
    vectors = sorted(str(name) for name in library.get_vector_parameter_names(material))
    textures = sorted(str(name) for name in library.get_texture_parameter_names(material))
    required_scalars = set(
        STANDARD_SCALARS if spec["kind"] == "standard" else LOCAL_SCALARS
    )
    required_vectors = {"Uvcontrol" if spec["kind"] == "standard" else "Color"}
    missing = sorted(
        required_scalars.difference(scalars)
        | required_vectors.difference(vectors)
        | ({"NoiseTexture"} - set(textures))
    )
    return {
        "asset": material.get_path_name(),
        "source_parent": spec["source_parent"],
        "kind": spec["kind"],
        "two_sided_expected": bool(spec["two_sided"]),
        "two_sided_actual": bool(material.get_editor_property("two_sided")),
        "blend_mode": str(material.get_editor_property("blend_mode")),
        "expression_count": int(library.get_num_material_expressions(material)),
        "scalar_parameters": scalars,
        "vector_parameters": vectors,
        "texture_parameters": textures,
        "missing_required_parameters": missing,
        "preview_version": unreal.EditorAssetLibrary.get_metadata_tag(
            material, "KhazanStormPassFogPreviewVersion"
        ),
        "disable_depth_test": bool(material.get_editor_property("disable_depth_test")),
    }


def texture_audit(texture):
    return {
        "asset": texture.get_path_name(),
        "size_x": int(texture.blueprint_get_size_x()),
        "size_y": int(texture.blueprint_get_size_y()),
        "srgb": bool(texture.get_editor_property("srgb")),
        "compression_settings": str(texture.get_editor_property("compression_settings")),
    }


def mesh_audit(mesh, key, spec):
    bounds = mesh.get_bounding_box()
    minimum = bounds.min
    maximum = bounds.max
    return {
        "kind": key,
        "asset": mesh.get_path_name(),
        "source": spec["source"],
        "source_sha256": sha256_file(spec["source"]),
        "source_size": os.path.getsize(spec["source"]),
        "lod_count": int(unreal.EditorStaticMeshLibrary.get_lod_count(mesh)),
        "bounds_min": [minimum.x, minimum.y, minimum.z],
        "bounds_max": [maximum.x, maximum.y, maximum.z],
    }


def main():
    metadata = load_json(METADATA_PATH)
    if (
        metadata.get("status") != "passed"
        or int(metadata.get("summary", {}).get("fog_actor_count", -1))
        != EXPECTED_SOURCE_FOG_COUNT
    ):
        raise RuntimeError("StormPass Fog material metadata is incomplete")

    before = load_stormpass_and_snapshot()
    meshes = {}
    mesh_imports = {}
    imported_paths = []
    for key, spec in MESH_SPECS.items():
        mesh, imported, paths = import_mesh(key, spec)
        meshes[key] = mesh
        mesh_imports[key] = imported
        imported_paths.extend(paths)
    texture, texture_imported, texture_paths = import_noise_texture()
    imported_paths.extend(texture_paths)

    materials = {}
    material_created = {}
    material_reports = {}
    for key, spec in MATERIAL_SPECS.items():
        material, created = create_material(spec, texture)
        materials[key] = material
        material_created[key] = created
        material_reports[key] = material_audit(material, spec)
    failures = [
        {"material": key, "missing": report["missing_required_parameters"]}
        for key, report in material_reports.items()
        if report["missing_required_parameters"]
        or report["two_sided_actual"] != report["two_sided_expected"]
    ]
    if failures:
        raise RuntimeError("StormPass Fog base-material audit failed: " + str(failures[0]))

    unreal.EditorAssetLibrary.save_directory(
        FOG_ROOT, only_if_is_dirty=False, recursive=True
    )
    after = load_stormpass_and_snapshot()
    if after != before:
        raise RuntimeError("Fog asset preparation changed the StormPass map boundary")

    report = {
        "status": "prepared",
        "map_modified": False,
        "map_boundary_before": before,
        "map_boundary_after": after,
        "source_metadata": METADATA_PATH,
        "source_fog_actor_count": EXPECTED_SOURCE_FOG_COUNT,
        "source_noise_texture": {
            "path": NOISE_SOURCE_PATH,
            "sha256": sha256_file(NOISE_SOURCE_PATH),
            "size": os.path.getsize(NOISE_SOURCE_PATH),
        },
        "mesh_imported": mesh_imports,
        "texture_imported": texture_imported,
        "material_created": material_created,
        "imported_object_paths": imported_paths,
        "mesh_assets": [
            mesh_audit(meshes[key], key, MESH_SPECS[key])
            for key in sorted(meshes)
        ],
        "texture_asset": texture_audit(texture),
        "material_assets": material_reports,
        "material_audit_failure_count": len(failures),
        "preview_material_policy": {
            "source_custom_material_graph_available": False,
            "exact_source_parameter_names_preserved": True,
            "exact_source_parameter_values_deferred_to_instances": True,
            "density_curve_scale": FOG_DENSITY_CURVE_SCALE,
            "emissive_scale": FOG_EMISSIVE_SCALE,
            "note": (
                "FModel's cooked USD material is an opaque PreviewSurface stub. "
                "The replacement graph recreates animated noise, shaped sheet edges, "
                "depth intersection, radial camera-distance fading, grazing-angle "
                "suppression and source tint controls without screen-axis cutoffs."
            ),
        },
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} meshes={} materials={} actors={} fog={} report={}".format(
            report["status"],
            len(meshes),
            len(materials),
            after["actor_count"],
            after["fog_actor_count"],
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
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_FOG_ASSETS: " + str(exception))
        raise
