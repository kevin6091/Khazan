"""Polish HeinMach fog rendering and cave lighting without touching source layout.

The source game uses custom fog-sheet and volumetric-mist shaders that are not
present in the FModel export.  This script therefore keeps every recovered
transform and source light unchanged, rebuilds the fog-sheet preview shader
from the extracted dynamic parameters, and adds clearly-labelled/reversible
UE5 preview fog and route-fill actors.

Run inside Unreal Editor.  The operation is idempotent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreFogLightingPolish"
)
FOG_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "restore_heinmach_fog_sheets.py")
LIGHT_SCRIPT_PATH = os.path.join(
    SCRIPT_DIR, "calibrate_heinmach_preview_lighting.py"
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_FogLighting_Polish.json",
)

FOG_LABEL_PREFIX = "HM_FogSheet_"
SOURCE_LIGHT_LABEL_PREFIX = "HM_SourceLight_"
ROUTE_FILL_LABEL_PREFIX = "HM_PreviewRouteFill_"
ROUTE_FILL_FOLDER = "HeinMach/Reconstructed/PreviewLighting/RouteFill"
VOLUMETRIC_FOG_LABEL = "HM_PreviewVolumetricFog"
VOLUMETRIC_FOG_FOLDER = "HeinMach/Reconstructed/PreviewFog"
EXPECTED_FOG_COUNT = 50
EXPECTED_SOURCE_LIGHT_COUNT = 89
PREVIEW_MATERIAL_VERSION = 5
FOG_BASE_MATERIAL_NAME = "M_HeinMach_FogSheet_Preview_V5"
LUMEN_SURFACE_CACHE_ATLAS_SIZE = 8192

# The source values reach 100.  Converting them through an exponential density
# curve preserves their ordering without allowing raw values above one to turn
# the complete sheet into a hard rectangle.
FOG_DENSITY_CURVE_SCALE = 0.18
FOG_EMISSIVE_SCALE = 0.04

ROUTE_FILL_SPECS = (
    {
        "tag": "Tomb_01",
        "location": (12175.4369937, 16251.5777747, 983.55811),
        "intensity_lumens": 9000.0,
        "attenuation_radius_cm": 3500.0,
        "color_linear": (0.72, 0.78, 0.88),
    },
    {
        "tag": "Tomb_02",
        "location": (28098.0115482, 8071.4278110, -488.84407),
        "intensity_lumens": 11000.0,
        "attenuation_radius_cm": 4000.0,
        "color_linear": (0.52, 0.63, 0.88),
    },
    {
        "tag": "Tomb_03",
        "location": (22895.1630317, -2689.8031882, 97.37791),
        "intensity_lumens": 16000.0,
        "attenuation_radius_cm": 4500.0,
        "color_linear": (0.82, 0.70, 0.64),
    },
    {
        "tag": "Tomb_04",
        "location": (1987.2006424, -6305.4802295, -3675.26289),
        "intensity_lumens": 10000.0,
        "attenuation_radius_cm": 4000.0,
        "color_linear": (0.72, 0.76, 0.82),
    },
    {
        "tag": "Mission01_Boss_Start",
        "location": (-128.38306, -9446.851, -3383.18),
        "intensity_lumens": 7500.0,
        "attenuation_radius_cm": 4500.0,
        "color_linear": (0.58, 0.68, 0.82),
    },
)


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load helper module: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def actor_transform_signature(actors, prefix):
    records = []
    for actor in actors:
        if not actor.get_actor_label().startswith(prefix):
            continue
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
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "count": len(records),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def expression(material, expression_class, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default))
    return node


def constant(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(value))
    return node


def vector_parameter(material, name, value, x, y):
    node = expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", unreal.LinearColor(*value))
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


def create_fog_material(fog, noise_texture):
    material_path = fog.FOG_MATERIAL_ROOT + "/" + FOG_BASE_MATERIAL_NAME
    material = unreal.EditorAssetLibrary.load_asset(material_path)
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            FOG_BASE_MATERIAL_NAME,
            fog.FOG_MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create Fog V5 base material: " + material_path)

    expression_classes = {
        node.get_class().get_name()
        for node in unreal.MaterialEditingLibrary.get_material_expressions(material)
        if node
    }
    graph_is_current = (
        unreal.EditorAssetLibrary.get_metadata_tag(
            material, "KhazanFogPreviewVersion"
        )
        == str(PREVIEW_MATERIAL_VERSION)
        and "MaterialExpressionPixelDepth" not in expression_classes
        and {
            "MaterialExpressionWorldPosition",
            "MaterialExpressionCameraPositionWS",
            "MaterialExpressionDistance",
            "MaterialExpressionDepthFade",
            "MaterialExpressionPixelNormalWS",
            "MaterialExpressionCameraVectorWS",
            "MaterialExpressionDotProduct",
        }.issubset(expression_classes)
        and not bool(material.get_editor_property("disable_depth_test"))
    )
    if graph_is_current:
        return material

    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("two_sided", False)
    material.set_editor_property("disable_depth_test", False)
    try:
        material.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_UNLIT
        )
    except Exception:
        pass

    # Animated two-octave noise.  Pan vectors are per instance so the extracted
    # PanningSpeed and Rotator values retain their source meaning.
    texcoord = expression(material, unreal.MaterialExpressionTextureCoordinate, -1800, 0)
    noise_tiling = scalar_parameter(material, "NoiseTiling", 1.0, -1800, -160)
    tiled_uv = expression(material, unreal.MaterialExpressionMultiply, -1580, -40)
    pan_vector = vector_parameter(
        material, "PanVector", (0.015, 0.005, 0.0, 0.0), -1580, -300
    )
    panner_primary = expression(material, unreal.MaterialExpressionPanner, -1350, -100)
    noise_primary = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, -1120, -100
    )
    noise_primary.set_editor_property("parameter_name", "NoiseTexture")
    noise_primary.set_editor_property("texture", noise_texture)

    secondary_tiling = scalar_parameter(
        material, "SecondaryTiling", 1.73, -1580, 170
    )
    secondary_uv = expression(material, unreal.MaterialExpressionMultiply, -1350, 170)
    secondary_pan_vector = vector_parameter(
        material, "SecondaryPanVector", (-0.006, -0.002, 0.0, 0.0), -1350, 340
    )
    panner_secondary = expression(material, unreal.MaterialExpressionPanner, -1120, 180)
    noise_secondary = expression(material, unreal.MaterialExpressionTextureSample, -900, 180)
    noise_secondary.set_editor_property("texture", noise_texture)

    primary_weight = constant(material, 0.65, -880, -190)
    secondary_weight = constant(material, 0.35, -660, 250)
    primary_scaled = expression(material, unreal.MaterialExpressionMultiply, -660, -100)
    secondary_scaled = expression(material, unreal.MaterialExpressionMultiply, -440, 180)
    noise_blend = expression(material, unreal.MaterialExpressionAdd, -220, 20)
    cloud_low = scalar_parameter(material, "CloudLow", 0.22, -220, -160)
    cloud_subtract = expression(material, unreal.MaterialExpressionSubtract, 0, 0)
    cloud_range = scalar_parameter(material, "CloudRange", 0.60, 0, 150)
    cloud_divide = expression(material, unreal.MaterialExpressionDivide, 220, 0)
    cloud = expression(material, unreal.MaterialExpressionSaturate, 430, 0)

    # Soft rectangular edge mask, shaped by the source RoundSize value.
    center = constant(material, 0.5, -900, 520)
    uv_centered = expression(material, unreal.MaterialExpressionSubtract, -680, 500)
    uv_absolute = expression(material, unreal.MaterialExpressionAbs, -460, 500)
    two = constant(material, 2.0, -460, 660)
    uv_scaled = expression(material, unreal.MaterialExpressionMultiply, -240, 500)
    mask_u = expression(material, unreal.MaterialExpressionComponentMask, -20, 430)
    mask_u.set_editor_property("r", True)
    mask_u.set_editor_property("g", False)
    mask_u.set_editor_property("b", False)
    mask_u.set_editor_property("a", False)
    mask_v = expression(material, unreal.MaterialExpressionComponentMask, -20, 570)
    mask_v.set_editor_property("r", False)
    mask_v.set_editor_property("g", True)
    mask_v.set_editor_property("b", False)
    mask_v.set_editor_property("a", False)
    edge_u = expression(material, unreal.MaterialExpressionOneMinus, 190, 430)
    edge_v = expression(material, unreal.MaterialExpressionOneMinus, 190, 570)
    edge_product = expression(material, unreal.MaterialExpressionMultiply, 400, 500)
    edge_saturate = expression(material, unreal.MaterialExpressionSaturate, 610, 500)
    edge_power_value = scalar_parameter(material, "EdgePower", 1.5, 610, 650)
    edge = expression(material, unreal.MaterialExpressionPower, 830, 500)

    # Raw source opacity becomes a bounded optical density.
    max_opacity = scalar_parameter(material, "MaxOpacity", 0.8, 430, 210)
    density_scale = constant(material, -FOG_DENSITY_CURVE_SCALE, 430, 350)
    negative_density = expression(material, unreal.MaterialExpressionMultiply, 650, 250)
    density_exp = expression(material, unreal.MaterialExpressionExponential2, 860, 250)
    density = expression(material, unreal.MaterialExpressionOneMinus, 1070, 250)

    cloud_edge = expression(material, unreal.MaterialExpressionMultiply, 1070, 20)
    opacity_density = expression(material, unreal.MaterialExpressionMultiply, 1280, 80)
    fade_distance = scalar_parameter(material, "FadeDistance", 1000.0, 1070, 710)
    depth_fade = expression(material, unreal.MaterialExpressionDepthFade, 1500, 140)

    world_position = expression(
        material, unreal.MaterialExpressionWorldPosition, 1070, 920
    )
    camera_position = expression(
        material, unreal.MaterialExpressionCameraPositionWS, 1070, 1080
    )
    camera_distance = expression(
        material, unreal.MaterialExpressionDistance, 1280, 960
    )
    near_fade_distance = scalar_parameter(material, "NearFade", 50.0, 1070, 1050)
    near_fade_multiplier = scalar_parameter(
        material, "PreviewNearFadeMultiplier", 4.0, 1070, 1210
    )
    near_fade_range = expression(
        material, unreal.MaterialExpressionMultiply, 1280, 1140
    )
    near_divide = expression(material, unreal.MaterialExpressionDivide, 1490, 960)
    near_fade = expression(material, unreal.MaterialExpressionSaturate, 1700, 960)

    fading_start = scalar_parameter(material, "FadingStart", 100000.0, 1070, 1380)
    far_subtract = expression(material, unreal.MaterialExpressionSubtract, 1490, 1380)
    fading_reduction = scalar_parameter(
        material, "FadingReduction", 5000.0, 1280, 1530
    )
    far_divide = expression(material, unreal.MaterialExpressionDivide, 1700, 1380)
    far_saturate = expression(material, unreal.MaterialExpressionSaturate, 1910, 1380)
    far_fade = expression(material, unreal.MaterialExpressionOneMinus, 2120, 1380)

    pixel_normal = expression(
        material, unreal.MaterialExpressionPixelNormalWS, 1490, 1670
    )
    camera_vector = expression(
        material, unreal.MaterialExpressionCameraVectorWS, 1490, 1830
    )
    facing_dot = expression(material, unreal.MaterialExpressionDotProduct, 1700, 1740)
    facing_abs = expression(material, unreal.MaterialExpressionAbs, 1910, 1740)
    facing_saturate = expression(
        material, unreal.MaterialExpressionSaturate, 2120, 1740
    )
    angle_fade_power = scalar_parameter(
        material, "PreviewAngleFadePower", 1.5, 1910, 1910
    )
    facing_fade = expression(material, unreal.MaterialExpressionPower, 2330, 1740)

    depth_near = expression(material, unreal.MaterialExpressionMultiply, 1720, 200)
    opacity_far = expression(material, unreal.MaterialExpressionMultiply, 1940, 250)
    opacity_facing = expression(material, unreal.MaterialExpressionMultiply, 2160, 250)
    opacity_final = expression(material, unreal.MaterialExpressionSaturate, 2380, 250)

    tint = vector_parameter(
        material, "FogTint", (0.56, 0.66, 0.72, 1.0), 1070, -300
    )
    emissive_strength = scalar_parameter(
        material, "EmissiveStrength", 1.0, 1070, -160
    )
    emissive_scale = constant(material, FOG_EMISSIVE_SCALE, 1280, -160)
    emissive_amount = expression(material, unreal.MaterialExpressionMultiply, 1490, -160)
    emissive_color = expression(material, unreal.MaterialExpressionMultiply, 1700, -260)
    emissive_cloud = expression(material, unreal.MaterialExpressionMultiply, 1910, -160)
    emissive_final = expression(material, unreal.MaterialExpressionMultiply, 2120, -100)

    connect(texcoord, "", tiled_uv, "A")
    connect(noise_tiling, "", tiled_uv, "B")
    connect(tiled_uv, "", panner_primary, "Coordinate")
    connect(pan_vector, "RGB", panner_primary, "Speed")
    connect(panner_primary, "", noise_primary, "UVs")
    connect(tiled_uv, "", secondary_uv, "A")
    connect(secondary_tiling, "", secondary_uv, "B")
    connect(secondary_uv, "", panner_secondary, "Coordinate")
    connect(secondary_pan_vector, "RGB", panner_secondary, "Speed")
    connect(panner_secondary, "", noise_secondary, "UVs")
    connect(noise_primary, "R", primary_scaled, "A")
    connect(primary_weight, "", primary_scaled, "B")
    connect(noise_secondary, "R", secondary_scaled, "A")
    connect(secondary_weight, "", secondary_scaled, "B")
    connect(primary_scaled, "", noise_blend, "A")
    connect(secondary_scaled, "", noise_blend, "B")
    connect(noise_blend, "", cloud_subtract, "A")
    connect(cloud_low, "", cloud_subtract, "B")
    connect(cloud_subtract, "", cloud_divide, "A")
    connect(cloud_range, "", cloud_divide, "B")
    connect(cloud_divide, "", cloud, "None")

    connect(texcoord, "", uv_centered, "A")
    connect(center, "", uv_centered, "B")
    connect(uv_centered, "", uv_absolute, "None")
    connect(uv_absolute, "", uv_scaled, "A")
    connect(two, "", uv_scaled, "B")
    connect(uv_scaled, "", mask_u, "None")
    connect(uv_scaled, "", mask_v, "None")
    connect(mask_u, "", edge_u, "None")
    connect(mask_v, "", edge_v, "None")
    connect(edge_u, "", edge_product, "A")
    connect(edge_v, "", edge_product, "B")
    connect(edge_product, "", edge_saturate, "None")
    connect(edge_saturate, "", edge, "Base")
    connect(edge_power_value, "", edge, "Exp")

    connect(max_opacity, "", negative_density, "A")
    connect(density_scale, "", negative_density, "B")
    connect(negative_density, "", density_exp, "None")
    connect(density_exp, "", density, "None")
    connect(cloud, "", cloud_edge, "A")
    connect(edge, "", cloud_edge, "B")
    connect(cloud_edge, "", opacity_density, "A")
    connect(density, "", opacity_density, "B")
    connect(opacity_density, "", depth_fade, "Opacity")
    connect(fade_distance, "", depth_fade, "FadeDistance")

    connect(world_position, "", camera_distance, "A")
    connect(camera_position, "", camera_distance, "B")
    connect(near_fade_distance, "", near_fade_range, "A")
    connect(near_fade_multiplier, "", near_fade_range, "B")
    connect(camera_distance, "", near_divide, "A")
    connect(near_fade_range, "", near_divide, "B")
    connect(near_divide, "", near_fade, "None")
    connect(camera_distance, "", far_subtract, "A")
    connect(fading_start, "", far_subtract, "B")
    connect(far_subtract, "", far_divide, "A")
    connect(fading_reduction, "", far_divide, "B")
    connect(far_divide, "", far_saturate, "None")
    connect(far_saturate, "", far_fade, "None")
    connect(depth_fade, "", depth_near, "A")
    connect(near_fade, "", depth_near, "B")
    connect(depth_near, "", opacity_far, "A")
    connect(far_fade, "", opacity_far, "B")
    connect(pixel_normal, "", facing_dot, "A")
    connect(camera_vector, "", facing_dot, "B")
    connect(facing_dot, "", facing_abs, "None")
    connect(facing_abs, "", facing_saturate, "None")
    connect(facing_saturate, "", facing_fade, "Base")
    connect(angle_fade_power, "", facing_fade, "Exp")
    connect(opacity_far, "", opacity_facing, "A")
    connect(facing_fade, "", opacity_facing, "B")
    connect(opacity_facing, "", opacity_final, "None")

    connect(emissive_strength, "", emissive_amount, "A")
    connect(emissive_scale, "", emissive_amount, "B")
    connect(tint, "RGB", emissive_color, "A")
    connect(emissive_amount, "", emissive_color, "B")
    connect(emissive_color, "", emissive_cloud, "A")
    connect(cloud, "", emissive_cloud, "B")
    connect(emissive_cloud, "", emissive_final, "A")
    connect(edge, "", emissive_final, "B")

    if not unreal.MaterialEditingLibrary.connect_material_property(
        opacity_final, "", unreal.MaterialProperty.MP_OPACITY
    ):
        raise RuntimeError("Failed to connect fog opacity")
    if not unreal.MaterialEditingLibrary.connect_material_property(
        emissive_final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    ):
        raise RuntimeError("Failed to connect fog emissive color")

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanFogPreviewVersion", str(PREVIEW_MATERIAL_VERSION)
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanFogDistanceModel", "EuclideanWorldSpace"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material


def source_scalar(record, name, fallback):
    value = record.get("dynamic_scalar_parameters", {}).get(name, fallback)
    return float(value) if isinstance(value, (int, float)) else float(fallback)


def scalar_nearly_equal(left, right, tolerance=0.0001):
    return abs(float(left) - float(right)) <= tolerance


def color_nearly_equal(left, right, tolerance=0.0001):
    return all(
        scalar_nearly_equal(getattr(left, channel), getattr(right, channel), tolerance)
        for channel in ("r", "g", "b", "a")
    )


def update_fog_material_instances(fog, records, material, noise_texture):
    results = {}
    for record in records:
        name = fog.instance_asset_name(record)
        path = fog.FOG_MATERIAL_ROOT + "/" + name
        instance = unreal.EditorAssetLibrary.load_asset(path)
        if not instance:
            raise RuntimeError("Fog material instance is missing: " + path)
        source_opacity = max(0.0, min(100.0, source_scalar(record, "MaxOpacity", 0.8)))
        source_emissive = max(
            0.0, min(10.0, source_scalar(record, "emmisivestrength", 1.0))
        )
        source_angle = source_scalar(record, "Rotator", 0.0)
        source_speed = source_scalar(record, "PanningSpeed", 0.05)
        radians = math.radians(source_angle)
        pan_x = math.cos(radians) * source_speed
        pan_y = math.sin(radians) * source_speed
        round_size = max(0.25, min(1.0, source_scalar(record, "RoundSize", 0.5)))
        noise_size = max(1.0, source_scalar(record, "NoiseSize", 2048.0))
        parent_name = str(record.get("dynamic_material_parent_package", ""))
        tint = (
            unreal.LinearColor(0.64, 0.69, 0.76, 1.0)
            if parent_name.endswith("FMI_FogSheet_01")
            else unreal.LinearColor(0.50, 0.60, 0.68, 1.0)
        )

        scalars = {
            "MaxOpacity": source_opacity,
            "EmissiveStrength": source_emissive,
            "FadeDistance": max(1.0, source_scalar(record, "fadedistance", 1000.0)),
            "NearFade": max(1.0, source_scalar(record, "NearFade", 50.0)),
            "FadingStart": max(0.0, source_scalar(record, "FadingStart", 100000.0)),
            "FadingReduction": max(
                1.0, source_scalar(record, "FadingReduction", 5000.0)
            ),
            "NoiseTiling": max(0.25, min(4.0, 2048.0 / noise_size)),
            "SecondaryTiling": 1.73,
            "EdgePower": 1.0 + (1.0 - round_size) * 2.0,
            "CloudLow": 0.22,
            "CloudRange": 0.60,
            "PreviewNearFadeMultiplier": 4.0,
            "PreviewAngleFadePower": 1.5,
        }
        vectors = {
            "PanVector": unreal.LinearColor(pan_x, pan_y, 0.0, 0.0),
            "SecondaryPanVector": unreal.LinearColor(
                -pan_x * 0.37, -pan_y * 0.37, 0.0, 0.0
            ),
            "FogTint": tint,
        }
        current_parent = instance.get_editor_property("parent")
        needs_update = current_parent != material
        if not needs_update:
            for parameter_name, value in scalars.items():
                current = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                    instance, parameter_name
                )
                if not scalar_nearly_equal(current, value):
                    needs_update = True
                    break
        if not needs_update:
            for parameter_name, value in vectors.items():
                current = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
                    instance, parameter_name
                )
                if not color_nearly_equal(current, value):
                    needs_update = True
                    break
        if not needs_update:
            current_texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
                instance, "NoiseTexture"
            )
            needs_update = current_texture != noise_texture

        if needs_update:
            unreal.MaterialEditingLibrary.set_material_instance_parent(instance, material)
            for parameter_name, value in scalars.items():
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                    instance, parameter_name, value
                )
            for parameter_name, value in vectors.items():
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                    instance, parameter_name, value
                )
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, "NoiseTexture", noise_texture
            )
            unreal.EditorAssetLibrary.save_loaded_asset(
                instance, only_if_is_dirty=False
            )
        results[fog.managed_label(record)] = {
            "material": instance.get_path_name(),
            "updated": needs_update,
            "source_max_opacity": source_opacity,
            "source_emissive": source_emissive,
            "source_rotator_degrees": source_angle,
            "source_panning_speed": source_speed,
            "pan_vector": [pan_x, pan_y],
            "near_fade_cm": scalars["NearFade"],
            "depth_fade_cm": scalars["FadeDistance"],
            "far_fade_start_cm": scalars["FadingStart"],
            "far_fade_reduction_cm": scalars["FadingReduction"],
            "preview_near_fade_multiplier": scalars[
                "PreviewNearFadeMultiplier"
            ],
            "preview_angle_fade_power": scalars["PreviewAngleFadePower"],
            "edge_power": scalars["EdgePower"],
        }
    return results


def ensure_fog_assignments(fog, actors, records, instances):
    by_label = {actor.get_actor_label(): actor for actor in actors}
    mismatches = []
    for record in records:
        label = fog.managed_label(record)
        actor = by_label.get(label)
        if not actor:
            mismatches.append({"label": label, "reason": "actor_missing"})
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            mismatches.append({"label": label, "reason": "component_missing"})
            continue
        instance = unreal.EditorAssetLibrary.load_asset(instances[label]["material"])
        component.set_material(0, instance)
        component.set_editor_property("cast_shadow", False)
        if component.get_material(0) != instance:
            mismatches.append({"label": label, "reason": "material_assignment"})
    return mismatches


def ensure_volumetric_fog(actor_subsystem, actors):
    actor = next(
        (item for item in actors if item.get_actor_label() == VOLUMETRIC_FOG_LABEL),
        None,
    )
    created = actor is None
    if not actor:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.ExponentialHeightFog,
            unreal.Vector(0.0, 0.0, -4500.0),
            unreal.Rotator(),
        )
        if not actor:
            raise RuntimeError("Failed to create preview volumetric fog")
        actor.set_actor_label(VOLUMETRIC_FOG_LABEL, mark_dirty=True)
    actor.set_actor_location(unreal.Vector(0.0, 0.0, -4500.0), False, False)
    set_actor_folder(actor, VOLUMETRIC_FOG_FOLDER)
    component = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if not component:
        raise RuntimeError("Preview volumetric fog component is missing")

    settings = {
        "fog_density": 0.0045,
        "fog_height_falloff": 0.12,
        "fog_max_opacity": 0.55,
        "start_distance": 100.0,
        # A finite cutoff produces a world-space wall when distant background
        # geometry crosses it. Zero keeps the height fog continuous.
        "fog_cutoff_distance": 0.0,
        "enable_volumetric_fog": True,
        "volumetric_fog_scattering_distribution": 0.15,
        # Keyword construction is intentional. Positional Color construction in
        # Unreal Python follows struct field order (B,G,R,A) and previously
        # reversed this intended cool tint into a warm one.
        "volumetric_fog_albedo": unreal.Color(r=158, g=177, b=196, a=255),
        "volumetric_fog_emissive": unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
        "volumetric_fog_extinction_scale": 0.35,
        "volumetric_fog_distance": 30000.0,
        "volumetric_fog_start_distance": 100.0,
        "volumetric_fog_near_fade_in_distance": 400.0,
    }
    failures = []
    for property_name, value in settings.items():
        try:
            component.set_editor_property(property_name, value)
        except Exception as exception:
            failures.append({"property": property_name, "error": str(exception)})
    if failures:
        raise RuntimeError(
            "Preview volumetric fog property failures: {} {}".format(
                len(failures), json.dumps(failures, ensure_ascii=False)
            )
        )
    return {
        "label": VOLUMETRIC_FOG_LABEL,
        "created": created,
        "folder": VOLUMETRIC_FOG_FOLDER,
        "location": [0.0, 0.0, -4500.0],
        "settings": {
            key: str(value) if not isinstance(value, (int, float, bool)) else value
            for key, value in settings.items()
        },
        "policy": (
            "Preview approximation only: the extracted game references a custom "
            "xxVolumetricMist shader, but its implementation was not exported."
        ),
    }


def create_route_fill_lights(actor_subsystem, actors):
    existing = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(ROUTE_FILL_LABEL_PREFIX)
    }
    expected = {ROUTE_FILL_LABEL_PREFIX + spec["tag"] for spec in ROUTE_FILL_SPECS}
    unexpected = sorted(set(existing) - expected)
    if unexpected:
        raise RuntimeError("Unexpected managed route-fill actor: " + unexpected[0])

    results = []
    for spec in ROUTE_FILL_SPECS:
        label = ROUTE_FILL_LABEL_PREFIX + spec["tag"]
        actor = existing.get(label)
        created = actor is None
        if not actor:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.PointLight, unreal.Vector(*spec["location"]), unreal.Rotator()
            )
            if not actor:
                raise RuntimeError("Failed to create route-fill light: " + label)
            actor.set_actor_label(label, mark_dirty=True)
        actor.set_actor_location(unreal.Vector(*spec["location"]), False, False)
        set_actor_folder(actor, ROUTE_FILL_FOLDER)
        component = actor.get_component_by_class(unreal.PointLightComponent)
        component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        component.set_editor_property("intensity", spec["intensity_lumens"])
        component.set_editor_property(
            "attenuation_radius", spec["attenuation_radius_cm"]
        )
        component.set_editor_property("cast_shadows", False)
        component.set_editor_property("use_inverse_squared_falloff", True)
        component.set_editor_property("volumetric_scattering_intensity", 0.35)
        color = spec["color_linear"]
        component.set_light_color(
            unreal.LinearColor(color[0], color[1], color[2], 1.0), True
        )
        results.append({"label": label, "created": created, **spec})
    return results


def set_post_property(settings, name, value, failures, required=False):
    try:
        settings.set_editor_property(name, value)
        return True
    except Exception as exception:
        failures.append(
            {"property": name, "required": required, "error": str(exception)}
        )
        if required:
            raise
        return False


def configure_post_process(post):
    try:
        post.set_editor_property("unbound", True)
    except Exception:
        pass
    settings = post.get_editor_property("settings")
    failures = []
    values = (
        ("override_auto_exposure_method", True, True),
        ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM, True),
        ("override_auto_exposure_min_brightness", True, True),
        ("auto_exposure_min_brightness", 0.0, True),
        ("override_auto_exposure_max_brightness", True, True),
        ("auto_exposure_max_brightness", 14.0, True),
        ("override_auto_exposure_bias", True, True),
        ("auto_exposure_bias", -0.25, True),
        ("override_auto_exposure_speed_up", True, False),
        ("auto_exposure_speed_up", 3.0, False),
        ("override_auto_exposure_speed_down", True, False),
        ("auto_exposure_speed_down", 1.5, False),
        ("override_dynamic_global_illumination_method", True, False),
        (
            "dynamic_global_illumination_method",
            unreal.DynamicGlobalIlluminationMethod.LUMEN,
            False,
        ),
        ("override_indirect_lighting_intensity", True, False),
        ("indirect_lighting_intensity", 1.20, False),
        ("override_lumen_scene_lighting_quality", True, False),
        ("lumen_scene_lighting_quality", 2.0, False),
        ("override_lumen_scene_detail", True, False),
        ("lumen_scene_detail", 1.5, False),
        ("override_lumen_scene_view_distance", True, False),
        ("lumen_scene_view_distance", 40000.0, False),
        ("override_lumen_final_gather_quality", True, False),
        ("lumen_final_gather_quality", 2.0, False),
        ("override_lumen_max_trace_distance", True, False),
        ("lumen_max_trace_distance", 40000.0, False),
        ("override_lumen_skylight_leaking", True, False),
        ("lumen_skylight_leaking", 0.08, False),
    )
    applied = []
    for name, value, required in values:
        if set_post_property(settings, name, value, failures, required):
            applied.append(name)
    post.set_editor_property("settings", settings)
    return {
        "exposure": {
            "method": "Histogram",
            "min_ev100": 0.0,
            "max_ev100": 14.0,
            "bias": -0.25,
            "speed_up": 3.0,
            "speed_down": 1.5,
        },
        "lumen": {
            "dynamic_gi": "Lumen",
            "indirect_lighting_intensity": 1.20,
            "scene_lighting_quality": 2.0,
            "scene_detail": 1.5,
            "scene_view_distance_cm": 40000.0,
            "final_gather_quality": 2.0,
            "max_trace_distance_cm": 40000.0,
            "skylight_leaking": 0.08,
            "surface_cache_atlas_size": LUMEN_SURFACE_CACHE_ATLAS_SIZE,
        },
        "applied_properties": applied,
        "optional_property_failures": failures,
    }


def main():
    fog = load_module("khazan_heinmach_fog_helpers_v4", FOG_SCRIPT_PATH)
    lighting = load_module("khazan_heinmach_light_helpers_v4", LIGHT_SCRIPT_PATH)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
        world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()

    if not unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        raise RuntimeError(
            "Safety backup is missing; create it before running polish: "
            + BACKUP_MAP_PATH
        )

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = list(actor_subsystem.get_all_level_actors())
    fog_signature_before = actor_transform_signature(actors_before, FOG_LABEL_PREFIX)
    source_light_signature_before = actor_transform_signature(
        actors_before, SOURCE_LIGHT_LABEL_PREFIX
    )
    if fog_signature_before["count"] != EXPECTED_FOG_COUNT:
        raise RuntimeError("Expected 50 source fog-sheet actors")
    if source_light_signature_before["count"] != EXPECTED_SOURCE_LIGHT_COUNT:
        raise RuntimeError("Expected 89 source-light actors")

    gap_report = fog.load_json(fog.GAP_REPORT_PATH)
    records = list(gap_report.get("fog_sheet_actors", []))
    if len(records) != EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog metadata inventory changed")
    if any(record.get("source_level", "").startswith("HeinMach_Cine_") for record in records):
        raise RuntimeError("Cinematic fog entered the environment inventory")

    noise_texture = unreal.EditorAssetLibrary.load_asset(fog.NOISE_TEXTURE_PATH)
    if not noise_texture:
        raise RuntimeError("Fog noise texture is missing")
    material = create_fog_material(fog, noise_texture)
    instances = update_fog_material_instances(
        fog, records, material, noise_texture
    )
    assignment_mismatches = ensure_fog_assignments(
        fog, actors_before, records, instances
    )
    if assignment_mismatches:
        raise RuntimeError("Fog assignment validation failed")

    volumetric_fog = ensure_volumetric_fog(
        actor_subsystem, list(actor_subsystem.get_all_level_actors())
    )

    # Reset first: no exploratory edit may leak into an authoritative source light.
    source_light_reset = lighting.reset_source_lights(
        list(actor_subsystem.get_all_level_actors())
    )
    route_fill_lights = create_route_fill_lights(
        actor_subsystem, list(actor_subsystem.get_all_level_actors())
    )

    actors_current = list(actor_subsystem.get_all_level_actors())
    by_label = {actor.get_actor_label(): actor for actor in actors_current}
    sun = by_label.get("HM_PreviewSun")
    sky = by_label.get("HM_PreviewSkyLight")
    post = by_label.get("HM_PreviewPostProcess")
    if not sun or not sky or not post:
        raise RuntimeError("Preview environment actors are missing")
    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sun_component.set_editor_property("intensity", 20000.0)
    sky_component.set_editor_property("intensity", 1.0)
    sky_component.set_editor_property("real_time_capture", True)
    post_result = configure_post_process(post)

    unreal.SystemLibrary.execute_console_command(
        world,
        "r.LumenScene.SurfaceCache.AtlasSize {}".format(
            LUMEN_SURFACE_CACHE_ATLAS_SIZE
        ),
    )

    actors_after = list(actor_subsystem.get_all_level_actors())
    fog_signature_after = actor_transform_signature(actors_after, FOG_LABEL_PREFIX)
    source_light_signature_after = actor_transform_signature(
        actors_after, SOURCE_LIGHT_LABEL_PREFIX
    )
    if fog_signature_after != fog_signature_before:
        raise RuntimeError("Fog-sheet source transforms changed during polish")
    if source_light_signature_after != source_light_signature_before:
        raise RuntimeError("Source-light transforms changed during polish")
    if len(source_light_reset) != EXPECTED_SOURCE_LIGHT_COUNT:
        raise RuntimeError("Source-light metadata reset count changed")
    if len(route_fill_lights) != len(ROUTE_FILL_SPECS):
        raise RuntimeError("Route-fill light validation failed")

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach map after fog/light polish")
    unreal.EditorAssetLibrary.save_directory(
        fog.FOG_ROOT, only_if_is_dirty=False, recursive=True
    )

    payload = {
        "status": "polished",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "preview_material_version": PREVIEW_MATERIAL_VERSION,
        "fog_sheet": {
            "source_actor_count": len(records),
            "base_material": material.get_path_name(),
            "material_instance_count": len(instances),
            "source_transform_signature_before": fog_signature_before,
            "source_transform_signature_after": fog_signature_after,
            "assignment_mismatches": assignment_mismatches,
            "features": [
                "two-octave animated source noise",
                "per-source Rotator/PanningSpeed pan vectors",
                "bounded raw MaxOpacity density curve",
                "soft sheet-edge fade",
                "DepthFade intersection softening",
                "source NearFade and far-distance fade",
                "Euclidean WorldPosition-to-CameraPosition distance fade",
                "grazing-angle fade without PixelDepth screen bands",
                "depth test explicitly enabled",
                "subtle source emissive response",
            ],
            "source_parameter_samples": list(instances.values())[:5],
            "policy": (
                "Transforms, sort priorities and one-sided source policy are exact; "
                "shader graph is a documented UE5 preview reconstruction because "
                "the custom parent shader was not exported."
            ),
        },
        "volumetric_fog": volumetric_fog,
        "source_lights": {
            "count": len(source_light_reset),
            "transform_signature_before": source_light_signature_before,
            "transform_signature_after": source_light_signature_after,
            "policy": (
                "All 89 source positions, colors, attenuation radii and reconstructed "
                "intensities were reset from cached FModel metadata before polishing."
            ),
        },
        "route_fill_lights": {
            "count": len(route_fill_lights),
            "folder": ROUTE_FILL_FOLDER,
            "lights": route_fill_lights,
            "policy": (
                "Five reversible, movable, shadowless checkpoint fills compensate for "
                "missing proprietary GI/environment controllers; source lights are untouched."
            ),
        },
        "post_process": post_result,
        "actor_total": len(actors_after),
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "WBP_FogSheet_Local_C cinematic-only actor",
            "Barehanded staggering/basic-movement protagonist scenes",
        ],
    }
    write_json(REPORT_PATH, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "report": REPORT_PATH,
                "fog": len(records),
                "source_lights": len(source_light_reset),
                "route_fills": len(route_fill_lights),
                "actors": len(actors_after),
            }
        )
    )
    return payload


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
        unreal.log_error("KHAZAN_HEINMACH_POLISH: " + str(exception))
        raise
