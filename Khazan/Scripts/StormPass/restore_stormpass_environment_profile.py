"""Restore StormPass sky, global lights, post process, reflections, and Fog.

The pass consumes only the audited FModel manifest.  Existing prop, landscape,
foliage, local-light, and Fog-sheet actors are protected by an exact transform
signature.  Fog is deliberately created after every other environment stage.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreEnvironmentProfileRestore"
)
METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_EnvironmentProfile.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_EnvironmentProfile_Restoration.json",
)
ASSET_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/EnvironmentAssets"
MESH_ROOT = ASSET_ROOT + "/Meshes"
TEXTURE_ROOT = ASSET_ROOT + "/Textures"
MATERIAL_ROOT = ASSET_ROOT + "/Materials"
INSTANCE_ROOT = ASSET_ROOT + "/MaterialInstances"
FOLDER_ROOT = "StormPass/Reconstructed/Environment"
MANAGED_PREFIX = "SP_Environment_"
CORE_PREFIX_COUNTS = {
    "SP_Prop_": 13050,
    "SP_ChildProp_": 551,
    "SP_Landscape_": 456,
    "SP_Foliage_": 218,
    "SP_SourceLight_": 53,
    "SP_Fog_": 53,
}
EXPECTED_CORE_ACTOR_COUNT = sum(CORE_PREFIX_COUNTS.values())
EXPECTED_ENVIRONMENT_ACTOR_COUNT = 27
EXPECTED_FINAL_ACTOR_COUNT = EXPECTED_CORE_ACTOR_COUNT + EXPECTED_ENVIRONMENT_ACTOR_COUNT
FOG_DENSITY_SCALE = 0.01
FOG_HEIGHT_FALLOFF_SCALE = 0.10
VISUAL_MATERIAL_VERSION = 2

TEXTURE_SPECS = {
    "cloud_distortion": {
        "asset": "T_SP_Sky_Cloud_Distortion",
        "source_index": 0,
        "srgb": False,
        "compression": unreal.TextureCompressionSettings.TC_MASKS,
    },
    "cloud_lookup": {
        "asset": "T_SP_Sky_Cloud_LookUp",
        "source_index": 1,
        "srgb": False,
        "compression": unreal.TextureCompressionSettings.TC_GRAYSCALE,
    },
    "cloud_normal": {
        "asset": "T_SP_Sky_Cloud_Normal",
        "source_index": 2,
        "srgb": False,
        "compression": unreal.TextureCompressionSettings.TC_NORMALMAP,
    },
    "nebula": {
        "asset": "T_SP_Sky_Nebula",
        "source_index": 3,
        "srgb": True,
        "compression": unreal.TextureCompressionSettings.TC_DEFAULT,
    },
    "stars": {
        "asset": "T_SP_Sky_Star_Mask",
        "source_index": 4,
        "srgb": False,
        "compression": unreal.TextureCompressionSettings.TC_MASKS,
    },
    "smoke_noise": {
        "asset": "T_SP_Sky_Smoke_Noise",
        "source_index": 5,
        "srgb": False,
        "compression": unreal.TextureCompressionSettings.TC_GRAYSCALE,
    },
}

POST_PROCESS_FIELDS = {
    "ColorSaturation": ("color_saturation", "vector4"),
    "ColorSaturationShadows": ("color_saturation_shadows", "vector4"),
    "ColorGainShadows": ("color_gain_shadows", "vector4"),
    "ColorSaturationMidtones": ("color_saturation_midtones", "vector4"),
    "ColorContrastMidtones": ("color_contrast_midtones", "vector4"),
    "ColorSaturationHighlights": ("color_saturation_highlights", "vector4"),
    "ColorContrastHighlights": ("color_contrast_highlights", "vector4"),
    "ColorGainHighlights": ("color_gain_highlights", "vector4"),
    "ColorCorrectionHighlightsMin": ("color_correction_highlights_min", "float"),
    "ColorCorrectionShadowsMax": ("color_correction_shadows_max", "float"),
    "FilmSlope": ("film_slope", "float"),
    "SceneColorTint": ("scene_color_tint", "linear_color"),
    "SceneFringeIntensity": ("scene_fringe_intensity", "float"),
    "ChromaticAberrationStartOffset": (
        "chromatic_aberration_start_offset",
        "float",
    ),
    "BloomIntensity": ("bloom_intensity", "float"),
    "BloomThreshold": ("bloom_threshold", "float"),
    "Bloom1Tint": ("bloom1_tint", "linear_color"),
    "BloomDirtMaskIntensity": ("bloom_dirt_mask_intensity", "float"),
    "LensFlareIntensity": ("lens_flare_intensity", "float"),
    "LensFlareBokehSize": ("lens_flare_bokeh_size", "float"),
    "LensFlareThreshold": ("lens_flare_threshold", "float"),
    "VignetteIntensity": ("vignette_intensity", "float"),
    "AmbientOcclusionIntensity": ("ambient_occlusion_intensity", "float"),
    "AmbientOcclusionStaticFraction": (
        "ambient_occlusion_static_fraction",
        "float",
    ),
    "AmbientOcclusionRadius": ("ambient_occlusion_radius", "float"),
    "AmbientOcclusionFadeDistance": (
        "ambient_occlusion_fade_distance",
        "float",
    ),
    "AmbientOcclusionFadeRadius": ("ambient_occlusion_fade_radius", "float"),
    "AmbientOcclusionRadiusInWS": ("ambient_occlusion_radius_in_ws", "bool"),
    "AmbientOcclusionPower": ("ambient_occlusion_power", "float"),
    "AmbientOcclusionBias": ("ambient_occlusion_bias", "float"),
    "AmbientOcclusionQuality": ("ambient_occlusion_quality", "float"),
    "AmbientOcclusionMipBlend": ("ambient_occlusion_mip_blend", "float"),
    "AmbientOcclusionMipScale": ("ambient_occlusion_mip_scale", "float"),
    "AmbientOcclusionMipThreshold": (
        "ambient_occlusion_mip_threshold",
        "float",
    ),
    "AmbientOcclusionTemporalBlendWeight": (
        "ambient_occlusion_temporal_blend_weight",
        "float",
    ),
    "IndirectLightingColor": ("indirect_lighting_color", "linear_color"),
    "IndirectLightingIntensity": ("indirect_lighting_intensity", "float"),
    "MotionBlurAmount": ("motion_blur_amount", "float"),
    "MotionBlurMax": ("motion_blur_max", "float"),
    "MotionBlurTargetFPS": ("motion_blur_target_fps", "int"),
    "MotionBlurPerObjectSize": ("motion_blur_per_object_size", "float"),
    "ScreenSpaceReflectionIntensity": (
        "screen_space_reflection_intensity",
        "float",
    ),
    "ScreenSpaceReflectionQuality": ("screen_space_reflection_quality", "float"),
    "ScreenSpaceReflectionMaxRoughness": (
        "screen_space_reflection_max_roughness",
        "float",
    ),
    "AutoExposureMinBrightness": ("auto_exposure_min_brightness", "float"),
    "AutoExposureMaxBrightness": ("auto_exposure_max_brightness", "float"),
    "AutoExposureBias": ("auto_exposure_bias", "float"),
    "DepthOfFieldNearBlurSize": ("depth_of_field_near_blur_size", "float"),
    "DepthOfFieldFarBlurSize": ("depth_of_field_far_blur_size", "float"),
    "RayTracingAOSamplesPerPixel": (
        "ray_tracing_ao_samples_per_pixel",
        "int",
    ),
}


def log(message):
    unreal.log("KHAZAN_STORMPASS_ENVIRONMENT: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def safe_set(obj, name, value, failures, required=False):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as exception:
        failures.append(
            {
                "object": obj.get_path_name() if obj else "None",
                "property": name,
                "value": str(value),
                "required": required,
                "error": str(exception),
            }
        )
        if required:
            raise
        return False


def source_vector(value, default=0.0):
    value = value or {}
    return unreal.Vector(
        float(value.get("x", default)),
        float(value.get("y", default)),
        float(value.get("z", default)),
    )


def source_rotator(value):
    value = value or {}
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def source_transform(value):
    value = value or {}
    return unreal.Transform(
        location=source_vector(value.get("location_cm"), 0.0),
        rotation=source_rotator(value.get("rotation_degrees")),
        scale=source_vector(value.get("scale"), 1.0),
    )


def fcolor(value, default=255):
    value = value or {}
    return unreal.Color(
        r=int(value.get("R", default)),
        g=int(value.get("G", default)),
        b=int(value.get("B", default)),
        a=int(value.get("A", 255)),
    )


def linear_color(value, default=0.0):
    value = value or {}
    return unreal.LinearColor(
        float(value.get("R", default)),
        float(value.get("G", default)),
        float(value.get("B", default)),
        float(value.get("A", 1.0)),
    )


def core_signature(actors):
    rows = []
    counts = {}
    for prefix, expected in CORE_PREFIX_COUNTS.items():
        matches = [actor for actor in actors if actor.get_actor_label().startswith(prefix)]
        counts[prefix] = len(matches)
        if len(matches) != expected:
            raise RuntimeError(
                "Protected StormPass actor inventory changed: {}={} expected {}".format(
                    prefix, len(matches), expected
                )
            )
        for actor in matches:
            location = actor.get_actor_location()
            rotation = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            rows.append(
                "{}|{:.6f},{:.6f},{:.6f}|{:.6f},{:.6f},{:.6f}|{:.7f},{:.7f},{:.7f}".format(
                    actor.get_actor_label(),
                    location.x,
                    location.y,
                    location.z,
                    rotation.pitch,
                    rotation.yaw,
                    rotation.roll,
                    scale.x,
                    scale.y,
                    scale.z,
                )
            )
    encoded = "\n".join(sorted(rows)).encode("utf-8")
    return {
        "actor_count": len(rows),
        "counts": counts,
        "transform_sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


def expected_labels(metadata):
    labels = {
        "SP_Environment_DirectionalLight",
        "SP_Environment_SkyLight",
        "SP_Environment_SkyMesh",
        "SP_Environment_Cloud_0",
        "SP_Environment_Cloud_1",
        "SP_Environment_Wind",
        "SP_Environment_PostProcessFallback",
        "SP_Environment_HeightFog",
    }
    labels.update(
        "SP_Environment_Reflection_{:02d}".format(index)
        for index in range(len(metadata["reflection_captures"]))
    )
    labels.update(
        "SP_Environment_PP_{}_{:03d}".format(
            row["source_level"], int(row["source_actor_index"])
        )
        for row in metadata["post_process_volumes"]
    )
    if len(labels) != EXPECTED_ENVIRONMENT_ACTOR_COUNT:
        raise RuntimeError("Environment label inventory changed")
    return labels


def load_map():
    if not unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        raise RuntimeError("Pre-environment backup map is missing")
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    return subsystem


def asset_by_name(path, name, asset_class=None):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    matches = []
    for data in registry.get_assets_by_path(path, recursive=True):
        if str(data.asset_name) != name:
            continue
        asset = data.get_asset()
        if asset_class and not isinstance(asset, asset_class):
            continue
        matches.append(asset)
    if len(matches) > 1:
        raise RuntimeError("Duplicate reconstructed asset: " + name)
    return matches[0] if matches else None


def import_texture(source, asset_name, compression, srgb):
    asset_path = TEXTURE_ROOT + "/" + asset_name
    texture = unreal.EditorAssetLibrary.load_asset(asset_path)
    imported = False
    imported_paths = []
    if not texture:
        if not os.path.isfile(source):
            raise RuntimeError("Texture source is missing: " + source)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source)
        task.set_editor_property("destination_path", TEXTURE_ROOT)
        task.set_editor_property("destination_name", asset_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.TextureFactory())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported_paths = [str(value) for value in task.get_editor_property("imported_object_paths")]
        texture = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not texture and imported_paths:
            texture = unreal.EditorAssetLibrary.load_asset(imported_paths[0])
        imported = True
    if not texture:
        raise RuntimeError("Texture import failed: " + asset_name)
    texture.modify()
    safe_failures = []
    safe_set(texture, "srgb", bool(srgb), safe_failures)
    safe_set(texture, "compression_settings", compression, safe_failures)
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
    return texture, {
        "asset": texture.get_path_name(),
        "source": source,
        "imported": imported,
        "imported_paths": imported_paths,
        "optional_property_failures": safe_failures,
    }


def import_cubemap(source):
    source = prepare_compatible_hdr(source)
    name = "T_SP_Base_Cube"
    path = TEXTURE_ROOT + "/" + name
    texture = unreal.EditorAssetLibrary.load_asset(path)
    imported = False
    imported_paths = []
    if not texture:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source)
        task.set_editor_property("destination_path", TEXTURE_ROOT)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.TextureFactory())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported_paths = [str(value) for value in task.get_editor_property("imported_object_paths")]
        texture = unreal.EditorAssetLibrary.load_asset(path)
        if not texture and imported_paths:
            texture = unreal.EditorAssetLibrary.load_asset(imported_paths[0])
        imported = True
    if not texture or texture.get_class().get_name() != "TextureCube":
        raise RuntimeError("Base_Cube HDR did not import as TextureCube")
    texture.modify()
    failures = []
    safe_set(texture, "srgb", False, failures)
    safe_set(
        texture,
        "compression_settings",
        unreal.TextureCompressionSettings.TC_HDR,
        failures,
    )
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
    return texture, {
        "asset": texture.get_path_name(),
        "source": source,
        "imported": imported,
        "imported_paths": imported_paths,
        "optional_property_failures": failures,
    }


def prepare_compatible_hdr(source):
    """Repack FModel's valid-but-sub-8px Radiance RLE into UE-compatible RLE.

    Radiance's modern scanline RLE is formally defined for widths of at least
    eight pixels.  CUE4Parse writes the six-pixel Base_Cube preview using that
    layout anyway, while Unreal's importer correctly rejects it.  Nearest
    expansion preserves every authored RGBE texel and changes only container
    compatibility.
    """
    destination = os.path.join(
        unreal.Paths.project_saved_dir(),
        "ImportSources",
        "StormPass_Base_Cube_UECompatible.hdr",
    )
    with open(source, "rb") as input_file:
        header_lines = []
        while True:
            line = input_file.readline()
            if not line:
                raise RuntimeError("Base_Cube HDR header is incomplete")
            header_lines.append(line)
            match = re.match(rb"-Y\s+(\d+)\s+\+X\s+(\d+)", line.strip())
            if match:
                height = int(match.group(1))
                width = int(match.group(2))
                break
        rows = []
        for _ in range(height):
            marker = input_file.read(4)
            if len(marker) != 4 or marker[0:2] != b"\x02\x02":
                raise RuntimeError("Base_Cube HDR scanline marker is invalid")
            encoded_width = (marker[2] << 8) | marker[3]
            if encoded_width != width:
                raise RuntimeError("Base_Cube HDR scanline width changed")
            channels = []
            for _channel in range(4):
                values = bytearray()
                while len(values) < width:
                    count_raw = input_file.read(1)
                    if not count_raw:
                        raise RuntimeError("Base_Cube HDR RLE ended early")
                    count = count_raw[0]
                    if count > 128:
                        run = count - 128
                        value = input_file.read(1)
                        if not value:
                            raise RuntimeError("Base_Cube HDR repeat ended early")
                        values.extend(value * run)
                    else:
                        literal = input_file.read(count)
                        if len(literal) != count:
                            raise RuntimeError("Base_Cube HDR literal ended early")
                        values.extend(literal)
                if len(values) != width:
                    raise RuntimeError("Base_Cube HDR RLE overrun")
                channels.append(values)
            rows.append(channels)
        if input_file.read(1):
            raise RuntimeError("Base_Cube HDR has unexpected trailing bytes")

    output_width = 64
    output_height = 32
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "wb") as output:
        output.write(
            b"#?RADIANCE\n# StormPass exact RGBE texels repacked for Unreal\n"
            b"FORMAT=32-bit_rle_rgbe\n\n"
        )
        output.write(
            "-Y {} +X {}\n".format(output_height, output_width).encode("ascii")
        )
        for output_y in range(output_height):
            source_y = min(height - 1, (output_y * height) // output_height)
            output.write(bytes((2, 2, output_width >> 8, output_width & 255)))
            for channel in range(4):
                expanded = bytes(
                    rows[source_y][channel][
                        min(width - 1, (output_x * width) // output_width)
                    ]
                    for output_x in range(output_width)
                )
                output.write(bytes((output_width,)))
                output.write(expanded)
    return destination


def import_mesh(source, name):
    destination = MESH_ROOT + "/" + name
    ensure_directory(destination)
    mesh = asset_by_name(destination, name, unreal.StaticMesh)
    if not mesh:
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        candidates = [
            data.get_asset()
            for data in registry.get_assets_by_path(destination, recursive=True)
            if name.lower() in str(data.asset_name).lower()
            and str(data.asset_class_path.asset_name) == "StaticMesh"
        ]
        if len(candidates) > 1:
            raise RuntimeError("Multiple environment mesh candidates: " + name)
        mesh = candidates[0] if candidates else None
    imported = False
    imported_paths = []
    if not mesh:
        stage_path = os.path.join(
            unreal.Paths.project_saved_dir(),
            "ImportSources",
            "StormPass_Environment_" + name + ".usda",
        )
        os.makedirs(os.path.dirname(stage_path), exist_ok=True)
        with open(stage_path, "w", encoding="utf-8", newline="\n") as output:
            output.write(
                '#usda 1.0\n(\n    metersPerUnit = 0.01\n    upAxis = "Z"\n'
                "    subLayers = [\n        @{}@\n    ]\n)\n".format(
                    source.replace("\\", "/")
                )
            )
        options = unreal.UsdStageImportOptions()
        for property_name, value in (
            ("import_actors", False),
            ("import_geometry", True),
            ("import_materials", False),
            ("import_skeletal_animations", False),
            ("import_level_sequences", False),
            ("import_groom_assets", False),
            ("import_sparse_volume_textures", False),
            ("import_sounds", False),
            ("prims_to_import", ["/"]),
            ("share_assets_for_identical_prims", False),
            ("merge_identical_material_slots", False),
            ("prim_path_folder_structure", False),
            ("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE),
        ):
            options.set_editor_property(property_name, value)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", stage_path)
        task.set_editor_property("destination_path", destination)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        task.set_editor_property("options", options)
        task.set_editor_property("factory", unreal.UsdStageImportFactory())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported_paths = [str(value) for value in task.get_editor_property("imported_object_paths")]
        mesh = asset_by_name(destination, name, unreal.StaticMesh)
        if not mesh:
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            candidates = [
                data.get_asset()
                for data in registry.get_assets_by_path(destination, recursive=True)
                if name.lower() in str(data.asset_name).lower()
                and str(data.asset_class_path.asset_name) == "StaticMesh"
            ]
            if len(candidates) > 1:
                raise RuntimeError("Multiple imported mesh candidates: " + name)
            mesh = candidates[0] if candidates else None
        imported = True
    if not mesh:
        raise RuntimeError("Environment mesh import failed: " + name)
    return mesh, {
        "asset": mesh.get_path_name(),
        "source": source,
        "imported": imported,
        "imported_paths": imported_paths,
    }


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


def texture_parameter(material, name, texture, x, y):
    node = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, x, y
    )
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("texture", texture)
    return node


def constant(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(value))
    return node


def component_mask(material, source, x, y, red=False, green=False, blue=False):
    node = expression(material, unreal.MaterialExpressionComponentMask, x, y)
    node.set_editor_properties(
        {"r": red, "g": green, "b": blue, "a": False}
    )
    connect(source, "", node, "None")
    return node


def make_material(name, blend_mode):
    ensure_directory(MATERIAL_ROOT)
    path = MATERIAL_ROOT + "/" + name
    material = unreal.EditorAssetLibrary.load_asset(path)
    created = material is None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew()
        )
    if not material:
        raise RuntimeError("Failed to create environment material: " + name)
    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", blend_mode)
    material.set_editor_property("two_sided", True)
    failures = []
    safe_set(
        material,
        "shading_model",
        unreal.MaterialShadingModel.MSM_UNLIT,
        failures,
    )
    return material, created, failures


def build_sky_material(textures):
    material, created, failures = make_material(
        "M_SP_SourceSky_V2", unreal.BlendMode.BLEND_OPAQUE
    )
    safe_set(material, "is_sky", True, failures)

    # The source USD sky mesh contains wrapped/negative texture V values.  They are
    # valid for its textures but cannot be used as a colour-gradient alpha.  The
    # previous preview parent did exactly that, producing seams and inverted wedges.
    # Reconstruct the vertical coordinate from object-relative world direction so
    # the result is independent of imported UV conventions.
    world_position = expression(material, unreal.MaterialExpressionWorldPosition, -2200, 150)
    object_position = expression(material, unreal.MaterialExpressionActorPositionWS, -2200, 330)
    relative = expression(material, unreal.MaterialExpressionSubtract, -1980, 220)
    direction = expression(material, unreal.MaterialExpressionNormalize, -1760, 220)
    direction_z = component_mask(material, direction, -1540, 220, blue=True)
    one = constant(material, 1.0, -1540, 400)
    plus_one = expression(material, unreal.MaterialExpressionAdd, -1320, 250)
    half = constant(material, 0.5, -1320, 430)
    remapped = expression(material, unreal.MaterialExpressionMultiply, -1100, 260)
    vertical = expression(material, unreal.MaterialExpressionSaturate, -880, 260)
    horizon_falloff = scalar_parameter(material, "Horizon Falloff", 1.25, -1100, 560)
    shaped_vertical = expression(material, unreal.MaterialExpressionPower, -650, 260)
    connect(world_position, "", relative, "A")
    connect(object_position, "", relative, "B")
    connect(relative, "", direction, "None")
    connect(direction_z, "", plus_one, "A")
    connect(one, "", plus_one, "B")
    connect(plus_one, "", remapped, "A")
    connect(half, "", remapped, "B")
    connect(remapped, "", vertical, "None")
    connect(vertical, "", shaped_vertical, "Base")
    connect(horizon_falloff, "", shaped_vertical, "Exp")

    bottom = vector_parameter(material, "Bottom color", (1.0, 1.0, 1.0, 1.0), -650, -20)
    sky = vector_parameter(material, "Sky Color", (0.5, 0.6, 0.7, 1.0), -650, 80)
    overall = vector_parameter(material, "Overall Color", (0.3, 0.36, 0.42, 1.0), -650, 500)
    gradient = expression(material, unreal.MaterialExpressionLinearInterpolate, -390, 100)
    connect(bottom, "RGB", gradient, "A")
    connect(sky, "RGB", gradient, "B")
    connect(shaped_vertical, "", gradient, "Alpha")
    tinted = expression(material, unreal.MaterialExpressionMultiply, -150, 100)
    connect(gradient, "", tinted, "A")
    connect(overall, "RGB", tinted, "B")
    sky_luminance = scalar_parameter(material, "PreviewSkyLuminance", 2.0, -150, 320)
    lifted_sky = expression(material, unreal.MaterialExpressionMultiply, 80, 100)
    connect(tinted, "", lifted_sky, "A")
    connect(sky_luminance, "", lifted_sky, "B")

    texcoord = expression(material, unreal.MaterialExpressionTextureCoordinate, -2200, -520)
    nebula_scale = scalar_parameter(material, "NebulaUVScale", 0.25, -2200, -700)
    nebula_uv = expression(material, unreal.MaterialExpressionMultiply, -1980, -520)
    connect(texcoord, "", nebula_uv, "A")
    connect(nebula_scale, "", nebula_uv, "B")
    nebula = texture_parameter(
        material, "SkyNebulaTexture", textures["nebula"], -1760, -520
    )
    connect(nebula_uv, "", nebula, "UVs")
    nebula_gray = component_mask(material, nebula, -1530, -500, red=True)
    nebula_intensity = scalar_parameter(material, "NebulaIntensity", 0.25, -1530, -700)
    nebula_influence = scalar_parameter(material, "PreviewNebulaInfluence", 0.05, -1300, -700)
    nebula_weight = expression(material, unreal.MaterialExpressionMultiply, -1080, -620)
    nebula_amount = expression(material, unreal.MaterialExpressionMultiply, -850, -500)
    connect(nebula_intensity, "", nebula_weight, "A")
    connect(nebula_influence, "", nebula_weight, "B")
    connect(nebula_gray, "", nebula_amount, "A")
    connect(nebula_weight, "", nebula_amount, "B")

    star_scale = scalar_parameter(material, "StarUVScale", 2.0, -2200, -1000)
    star_uv = expression(material, unreal.MaterialExpressionMultiply, -1980, -960)
    connect(texcoord, "", star_uv, "A")
    connect(star_scale, "", star_uv, "B")
    stars = texture_parameter(
        material, "SkyStarTexture", textures["stars"], -1760, -960
    )
    connect(star_uv, "", stars, "UVs")
    star_power = scalar_parameter(material, "StarPower", 4.0, -1530, -1120)
    powered = expression(material, unreal.MaterialExpressionPower, -1300, -950)
    connect(stars, "R", powered, "Base")
    connect(star_power, "", powered, "Exp")
    star_brightness = scalar_parameter(material, "StarBrightness", 1.0, -1080, -1120)
    star_visibility = scalar_parameter(material, "PreviewStarVisibility", 0.0, -1080, -820)
    star_level = expression(material, unreal.MaterialExpressionMultiply, -850, -1030)
    bright_stars = expression(material, unreal.MaterialExpressionMultiply, -620, -950)
    connect(star_brightness, "", star_level, "A")
    connect(star_visibility, "", star_level, "B")
    connect(powered, "", bright_stars, "A")
    connect(star_level, "", bright_stars, "B")
    star_color = vector_parameter(material, "StarBaseColor", (1, 1, 1, 1), -620, -760)
    colored_stars = expression(material, unreal.MaterialExpressionMultiply, -390, -900)
    connect(bright_stars, "", colored_stars, "A")
    connect(star_color, "RGB", colored_stars, "B")

    # Retain every authored parameter even where the original custom shader's
    # directional/blink implementation cannot be recovered from cooked data.
    scalar_parameter(material, "NebulaDesaturation", -1.0, -2200, -1260)
    scalar_parameter(material, "NebulaNoiseUVScale", 0.25, -2200, -1400)
    scalar_parameter(material, "StarBlinkWeight", 0.5, -1980, -1260)
    scalar_parameter(material, "StarBlinkSpeed", 2.0, -1980, -1400)
    scalar_parameter(material, "StarBlinkUVScale", 10.0, -1760, -1260)
    scalar_parameter(material, "StarColorWeight", 0.75, -1760, -1400)
    scalar_parameter(material, "StarHorizonHeightMin", 0.0, -1540, -1260)
    scalar_parameter(material, "StarHorizonHeightMax", 50000.0, -1540, -1400)
    scalar_parameter(material, "SunlightBackgroundIntensity", 1.25, -1320, -1260)
    scalar_parameter(material, "SunlightBackgroundRadius", 0.25, -1320, -1400)
    vector_parameter(material, "SunSideColor", (1.0, 0.76, 0.5, 1.0), -1100, -1360)

    add_nebula = expression(material, unreal.MaterialExpressionAdd, 320, 50)
    connect(lifted_sky, "", add_nebula, "A")
    connect(nebula_amount, "", add_nebula, "B")
    final = expression(material, unreal.MaterialExpressionAdd, 550, 0)
    connect(add_nebula, "", final, "A")
    connect(colored_stars, "", final, "B")
    if not unreal.MaterialEditingLibrary.connect_material_property(
        final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    ):
        raise RuntimeError("Failed to connect sky emissive color")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, "KhazanSourceMaterial", "SCM_SkyColor_GloomyDay")
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanStormPassVisualMaterialVersion", str(VISUAL_MATERIAL_VERSION)
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, {"asset": material.get_path_name(), "created": created, "optional_property_failures": failures}


def build_cloud_material(textures):
    material, created, failures = make_material(
        "M_SP_SourceCloud_V2", unreal.BlendMode.BLEND_TRANSLUCENT
    )
    # Sky clouds are a distant dome and must remain behind world geometry.  The V1
    # parent disabled depth testing and omitted the source horizon fade, causing the
    # dome's z=0 rim to appear as a straight screen-space cut.
    safe_set(material, "disable_depth_test", False, failures, required=True)
    texcoord = expression(material, unreal.MaterialExpressionTextureCoordinate, -2400, -400)
    scale_u = scalar_parameter(material, "DiffuseTexScaleU", 8.0, -2400, -690)
    scale_v = scalar_parameter(material, "DiffuseTexScaleV", 8.0, -2400, -840)
    uv_vector = expression(material, unreal.MaterialExpressionAppendVector, -2170, -750)
    connect(scale_u, "", uv_vector, "A")
    connect(scale_v, "", uv_vector, "B")
    scale_fix = scalar_parameter(material, "PreviewUVScaleFactor", 0.15, -2170, -560)
    scale_product = expression(material, unreal.MaterialExpressionMultiply, -1940, -650)
    connect(uv_vector, "", scale_product, "A")
    connect(scale_fix, "", scale_product, "B")
    scaled_uv = expression(material, unreal.MaterialExpressionMultiply, -1710, -450)
    connect(texcoord, "", scaled_uv, "A")
    connect(scale_product, "", scaled_uv, "B")

    uv_speed = scalar_parameter(material, "DiffuseTexUVSpeed", 1.0, -1940, -900)
    animation_scale = scalar_parameter(material, "PreviewAnimationScale", 0.01, -1940, -1050)
    speed = expression(material, unreal.MaterialExpressionMultiply, -1710, -960)
    speed_y_scale = constant(material, 0.37, -1710, -1110)
    speed_y = expression(material, unreal.MaterialExpressionMultiply, -1480, -1030)
    speed_vector = expression(material, unreal.MaterialExpressionAppendVector, -1250, -970)
    connect(uv_speed, "", speed, "A")
    connect(animation_scale, "", speed, "B")
    connect(speed, "", speed_y, "A")
    connect(speed_y_scale, "", speed_y, "B")
    connect(speed, "", speed_vector, "A")
    connect(speed_y, "", speed_vector, "B")
    panner = expression(material, unreal.MaterialExpressionPanner, -1020, -450)
    connect(scaled_uv, "", panner, "Coordinate")
    connect(speed_vector, "", panner, "Speed")

    distortion_scale = scalar_parameter(material, "WorldDistortionUVScale", 10.0, -2170, -1220)
    distortion_fix = scalar_parameter(material, "PreviewDistortionUVScale", 0.025, -1940, -1220)
    distortion_scale_product = expression(material, unreal.MaterialExpressionMultiply, -1710, -1220)
    distortion_uv = expression(material, unreal.MaterialExpressionMultiply, -1480, -1220)
    connect(distortion_scale, "", distortion_scale_product, "A")
    connect(distortion_fix, "", distortion_scale_product, "B")
    connect(texcoord, "", distortion_uv, "A")
    connect(distortion_scale_product, "", distortion_uv, "B")
    distortion = texture_parameter(
        material, "CloudDistortionTexture", textures["cloud_distortion"], -1250, -1270
    )
    connect(distortion_uv, "", distortion, "UVs")
    distortion_rg = component_mask(material, distortion, -1020, -1260, red=True, green=True)
    half = constant(material, 0.5, -1020, -1430)
    centered_distortion = expression(material, unreal.MaterialExpressionSubtract, -790, -1260)
    distortion_intensity = scalar_parameter(material, "WorldDistortionIntensity", 2.0, -790, -1450)
    distortion_strength = scalar_parameter(material, "PreviewDistortionStrength", 0.02, -560, -1450)
    strength_product = expression(material, unreal.MaterialExpressionMultiply, -330, -1370)
    distortion_offset = expression(material, unreal.MaterialExpressionMultiply, -100, -1260)
    distorted_uv = expression(material, unreal.MaterialExpressionAdd, 130, -520)
    connect(distortion_rg, "", centered_distortion, "A")
    connect(half, "", centered_distortion, "B")
    connect(distortion_intensity, "", strength_product, "A")
    connect(distortion_strength, "", strength_product, "B")
    connect(centered_distortion, "", distortion_offset, "A")
    connect(strength_product, "", distortion_offset, "B")
    connect(panner, "", distorted_uv, "A")
    connect(distortion_offset, "", distorted_uv, "B")

    density_texture = texture_parameter(
        material, "CloudDensityTexture", textures["smoke_noise"], 360, -550
    )
    connect(distorted_uv, "", density_texture, "UVs")
    density_r = component_mask(material, density_texture, 590, -520, red=True)
    lookup_x = constant(material, 0.5, 590, -720)
    lookup_uv = expression(material, unreal.MaterialExpressionAppendVector, 820, -570)
    connect(lookup_x, "", lookup_uv, "A")
    connect(density_r, "", lookup_uv, "B")
    lookup = texture_parameter(
        material, "CloudLookupTexture", textures["cloud_lookup"], 1050, -580
    )
    connect(lookup_uv, "", lookup, "UVs")
    lookup_r = component_mask(material, lookup, 1280, -520, red=True)

    amount = scalar_parameter(material, "CloudAmount", 1.0, 590, -900)
    amount_weight = constant(material, 0.20, 590, -1050)
    weighted_amount = expression(material, unreal.MaterialExpressionMultiply, 820, -950)
    threshold_base = constant(material, 0.50, 820, -1100)
    threshold = expression(material, unreal.MaterialExpressionSubtract, 1050, -980)
    centered_density = expression(material, unreal.MaterialExpressionSubtract, 1280, -760)
    sharpness = scalar_parameter(material, "CloudSharpness", 0.5, 1050, -1180)
    sharpness_scale = constant(material, 4.0, 1280, -1180)
    scaled_sharpness = expression(material, unreal.MaterialExpressionMultiply, 1510, -1100)
    contrast_base = constant(material, 2.0, 1510, -1250)
    contrast = expression(material, unreal.MaterialExpressionAdd, 1740, -1100)
    contrasted = expression(material, unreal.MaterialExpressionMultiply, 1510, -760)
    shaped = expression(material, unreal.MaterialExpressionSaturate, 1740, -760)
    connect(amount, "", weighted_amount, "A")
    connect(amount_weight, "", weighted_amount, "B")
    connect(threshold_base, "", threshold, "A")
    connect(weighted_amount, "", threshold, "B")
    connect(lookup_r, "", centered_density, "A")
    connect(threshold, "", centered_density, "B")
    connect(sharpness, "", scaled_sharpness, "A")
    connect(sharpness_scale, "", scaled_sharpness, "B")
    connect(contrast_base, "", contrast, "A")
    connect(scaled_sharpness, "", contrast, "B")
    connect(centered_density, "", contrasted, "A")
    connect(contrast, "", contrasted, "B")
    connect(contrasted, "", shaped, "None")

    # Exact source world-height horizon visibility.  The cloud mesh is an upper
    # hemisphere with a flat z=0 rim, so this is the critical anti-cutoff term.
    world_position = expression(material, unreal.MaterialExpressionWorldPosition, 360, 20)
    object_position = expression(material, unreal.MaterialExpressionActorPositionWS, 360, 190)
    relative_position = expression(material, unreal.MaterialExpressionSubtract, 590, 80)
    relative_height = component_mask(material, relative_position, 820, 80, blue=True)
    horizon_min = scalar_parameter(material, "HorizonVisibilityMin", 0.0, 590, 330)
    horizon_max = scalar_parameter(material, "HorizonVisibilityMax", 100000.0, 590, 480)
    height_from_min = expression(material, unreal.MaterialExpressionSubtract, 1050, 80)
    height_range = expression(material, unreal.MaterialExpressionSubtract, 820, 410)
    horizon_ratio = expression(material, unreal.MaterialExpressionDivide, 1280, 180)
    horizon_fade = expression(material, unreal.MaterialExpressionSaturate, 1510, 180)
    connect(world_position, "", relative_position, "A")
    connect(object_position, "", relative_position, "B")
    connect(relative_height, "", height_from_min, "A")
    connect(horizon_min, "", height_from_min, "B")
    connect(horizon_max, "", height_range, "A")
    connect(horizon_min, "", height_range, "B")
    connect(height_from_min, "", horizon_ratio, "A")
    connect(height_range, "", horizon_ratio, "B")
    connect(horizon_ratio, "", horizon_fade, "None")

    density_with_horizon = expression(material, unreal.MaterialExpressionMultiply, 1970, -420)
    connect(shaped, "", density_with_horizon, "A")
    connect(horizon_fade, "", density_with_horizon, "B")
    base_color = vector_parameter(material, "CloudBaseColor", (0.8, 0.75, 0.7, 1), 1740, 20)
    sun_color = vector_parameter(material, "CloudSunSideColor", (1, 0.8, 0.5, 1), 1740, 180)
    color_lerp = expression(material, unreal.MaterialExpressionLinearInterpolate, 1970, 80)
    connect(base_color, "RGB", color_lerp, "A")
    connect(sun_color, "RGB", color_lerp, "B")
    connect(shaped, "", color_lerp, "Alpha")
    intensity = scalar_parameter(material, "CloudIntensity", 0.9, 1970, 300)
    preview_luminance = scalar_parameter(material, "PreviewCloudLuminance", 1.25, 1970, 450)
    total_intensity = expression(material, unreal.MaterialExpressionMultiply, 2200, 360)
    lit_color = expression(material, unreal.MaterialExpressionMultiply, 2200, 80)
    connect(intensity, "", total_intensity, "A")
    connect(preview_luminance, "", total_intensity, "B")
    connect(color_lerp, "", lit_color, "A")
    connect(total_intensity, "", lit_color, "B")
    cloud_emissive = expression(material, unreal.MaterialExpressionMultiply, 2430, 20)
    connect(lit_color, "", cloud_emissive, "A")
    connect(density_with_horizon, "", cloud_emissive, "B")
    master_opacity = scalar_parameter(material, "MasterOpacity", 1.0, 1970, -610)
    opacity_scale = scalar_parameter(material, "PreviewOpacityScale", 0.16, 1970, -760)
    opacity_weight = expression(material, unreal.MaterialExpressionMultiply, 2200, -650)
    opacity = expression(material, unreal.MaterialExpressionMultiply, 2430, -470)
    connect(master_opacity, "", opacity_weight, "A")
    connect(opacity_scale, "", opacity_weight, "B")
    connect(density_with_horizon, "", opacity, "A")
    connect(opacity_weight, "", opacity, "B")

    # Keep the remaining authored inputs addressable in the instances/audit.
    scalar_parameter(material, "CloudPostPower", 1.0, 360, 650)
    scalar_parameter(material, "NormalLevel", 0.95, 590, 650)
    scalar_parameter(material, "BacklightCloudPostPower", 0.0, 820, 650)
    scalar_parameter(material, "BacklightRadius", 1.5, 1050, 650)
    scalar_parameter(material, "BacklightSharpness", 0.0, 1280, 650)
    scalar_parameter(material, "EdgeBrightness", 3.0, 1510, 650)
    scalar_parameter(material, "WorldDistortionSpeed", -0.1, 1740, 650)
    scalar_parameter(material, "HeightCutOffMin", 10000.0, 1970, 650)
    scalar_parameter(material, "HeightCutOffMax", 100000.0, 2200, 650)
    scalar_parameter(material, "HorizonCutOffHeightMin", 0.0, 2430, 650)
    scalar_parameter(material, "HorizonCutOffHeightMax", 0.0, 2660, 650)
    vector_parameter(material, "BacklightCloudColor", (0.58, 0.49, 0.36, 1.0), 2660, 400)
    normal_texture = texture_parameter(
        material, "CloudNormalTexture", textures["cloud_normal"], 2660, 100
    )
    connect(distorted_uv, "", normal_texture, "UVs")
    if not unreal.MaterialEditingLibrary.connect_material_property(
        cloud_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    ):
        raise RuntimeError("Failed to connect cloud emissive color")
    if not unreal.MaterialEditingLibrary.connect_material_property(
        opacity, "", unreal.MaterialProperty.MP_OPACITY
    ):
        raise RuntimeError("Failed to connect cloud opacity")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, "KhazanSourceMaterial", "StormPass WEP cloud layers")
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanStormPassVisualMaterialVersion", str(VISUAL_MATERIAL_VERSION)
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, {"asset": material.get_path_name(), "created": created, "optional_property_failures": failures}


def create_instance(name, parent, source_profile, textures, custom_scalars=None):
    ensure_directory(INSTANCE_ROOT)
    path = INSTANCE_ROOT + "/" + name
    instance = unreal.EditorAssetLibrary.load_asset(path)
    created = instance is None
    if not instance:
        instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name,
            INSTANCE_ROOT,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
    if not instance:
        raise RuntimeError("Failed to create material instance: " + name)
    unreal.MaterialEditingLibrary.set_material_instance_parent(instance, parent)
    scalar_names = {str(value) for value in unreal.MaterialEditingLibrary.get_scalar_parameter_names(parent)}
    vector_names = {str(value) for value in unreal.MaterialEditingLibrary.get_vector_parameter_names(parent)}
    texture_names = {str(value) for value in unreal.MaterialEditingLibrary.get_texture_parameter_names(parent)}
    applied = {"scalars": [], "vectors": [], "textures": []}
    for row in source_profile.get("scalar_parameters", []):
        parameter = str(row.get("name"))
        if parameter in scalar_names:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                instance, parameter, float(row.get("value", 0.0))
            )
            applied["scalars"].append(parameter)
    for parameter, value in (custom_scalars or {}).items():
        if parameter in scalar_names:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                instance, parameter, float(value)
            )
            applied["scalars"].append(parameter)
    for row in source_profile.get("vector_parameters", []):
        parameter = str(row.get("name"))
        if parameter in vector_names:
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                instance, parameter, linear_color(row.get("value"))
            )
            applied["vectors"].append(parameter)
    for parameter, texture in textures.items():
        if parameter in texture_names:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, parameter, texture
            )
            applied["textures"].append(parameter)
    unreal.EditorAssetLibrary.set_metadata_tag(
        instance, "KhazanSourceMaterial", str(source_profile.get("name"))
    )
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    return instance, {
        "asset": instance.get_path_name(),
        "created": created,
        "source_material": source_profile.get("name"),
        "source_parent": source_profile.get("parent_package"),
        "applied_parameters": {key: sorted(set(value)) for key, value in applied.items()},
    }


def prepare_assets(metadata):
    ensure_directory(ASSET_ROOT)
    ensure_directory(TEXTURE_ROOT)
    texture_sources = metadata["asset_sources"]["sky_textures"]
    textures = {}
    texture_report = {}
    for key, spec in TEXTURE_SPECS.items():
        texture, row = import_texture(
            texture_sources[spec["source_index"]],
            spec["asset"],
            spec["compression"],
            spec["srgb"],
        )
        textures[key] = texture
        texture_report[key] = row
    cubemap, cubemap_report = import_cubemap(
        metadata["asset_sources"]["reflection_cubemap_hdr"]
    )
    cloud_mesh, cloud_mesh_report = import_mesh(
        metadata["asset_sources"]["cloud_mesh_usda"], "WAS_CloudMesh"
    )
    sky_mesh, sky_mesh_report = import_mesh(
        metadata["asset_sources"]["sky_mesh_usda"], "WAS_SkyMesh"
    )
    sky_parent, sky_parent_report = build_sky_material(textures)
    cloud_parent, cloud_parent_report = build_cloud_material(textures)
    source_materials = metadata["source_material_profiles"]
    sky_instance, sky_instance_report = create_instance(
        "MI_SP_Sky_GloomyDay_V2",
        sky_parent,
        source_materials["sky_gloomy_day"],
        {"SkyNebulaTexture": textures["nebula"], "SkyStarTexture": textures["stars"]},
    )
    cloud_1, cloud_1_report = create_instance(
        "MI_SP_Cloud_White_Layer1_V2",
        cloud_parent,
        source_materials["cloud_layer_1"],
        {
            "CloudDensityTexture": textures["smoke_noise"],
            "CloudDistortionTexture": textures["cloud_distortion"],
            "CloudLookupTexture": textures["cloud_lookup"],
            "CloudNormalTexture": textures["cloud_normal"],
        },
        {"PreviewOpacityScale": 0.16, "PreviewUVScaleFactor": 0.15},
    )
    cloud_2, cloud_2_report = create_instance(
        "MI_SP_Cloud_GloomyDawn_Layer2_V2",
        cloud_parent,
        source_materials["cloud_layer_2"],
        {
            "CloudDensityTexture": textures["smoke_noise"],
            "CloudDistortionTexture": textures["cloud_distortion"],
            "CloudLookupTexture": textures["cloud_lookup"],
            "CloudNormalTexture": textures["cloud_normal"],
        },
        {"PreviewOpacityScale": 0.10, "PreviewUVScaleFactor": 0.13},
    )
    return {
        "objects": {
            "textures": textures,
            "cubemap": cubemap,
            "cloud_mesh": cloud_mesh,
            "sky_mesh": sky_mesh,
            "sky_material": sky_instance,
            "cloud_materials": [cloud_1, cloud_2],
        },
        "report": {
            "textures": texture_report,
            "cubemap": cubemap_report,
            "meshes": {"cloud": cloud_mesh_report, "sky": sky_mesh_report},
            "materials": {
                "sky_parent": sky_parent_report,
                "cloud_parent": cloud_parent_report,
                "sky_instance": sky_instance_report,
                "cloud_layer_1": cloud_1_report,
                "cloud_layer_2": cloud_2_report,
            },
        },
    }


def spawn_or_reuse(actor_subsystem, by_label, actor_class, label, location=None, rotation=None):
    actor = by_label.get(label)
    created = actor is None
    if actor and not isinstance(actor, actor_class):
        raise RuntimeError("Managed actor class mismatch: " + label)
    if not actor:
        actor = actor_subsystem.spawn_actor_from_class(
            actor_class, location or unreal.Vector(), rotation or unreal.Rotator()
        )
        if not actor:
            raise RuntimeError("Failed to spawn " + label)
        actor.set_actor_label(label, mark_dirty=True)
        by_label[label] = actor
    return actor, created


def configure_static_mesh_actor(actor, mesh, material, transform, folder):
    actor.set_actor_transform(source_transform(transform), False, False)
    set_actor_folder(actor, folder)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if not component:
        raise RuntimeError("Environment StaticMeshComponent is missing")
    component.set_static_mesh(mesh)
    component.set_material(0, material)
    failures = []
    safe_set(component, "cast_shadow", False, failures)
    safe_set(component, "receives_decals", False, failures)
    try:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception as exception:
        failures.append(
            {
                "object": component.get_path_name(),
                "property": "collision_enabled",
                "required": True,
                "value": str(unreal.CollisionEnabled.NO_COLLISION),
                "error": str(exception),
            }
        )
        raise
    safe_set(component, "visible_in_ray_tracing", False, failures)
    safe_set(component, "bounds_scale", 10.0, failures)
    return failures


def restore_sky_cloud_wind(metadata, assets, actor_subsystem, by_label):
    proxy = metadata["environment_proxy"]
    clouds = [row for row in proxy["components"] if row["source_object_type"] == "xxEnvCloudComponent"]
    skies = [row for row in proxy["components"] if row["source_object_type"] == "xxSkyMeshComponent"]
    winds = [row for row in proxy["components"] if row["source_object_type"] == "xxWindDSComponent"]
    if len(clouds) != 2 or len(skies) != 1 or len(winds) != 1:
        raise RuntimeError("Environment proxy component inventory changed")
    rows = []
    sky_actor, created = spawn_or_reuse(
        actor_subsystem,
        by_label,
        unreal.StaticMeshActor,
        "SP_Environment_SkyMesh",
    )
    failures = configure_static_mesh_actor(
        sky_actor,
        assets["sky_mesh"],
        assets["sky_material"],
        skies[0]["transform"],
        FOLDER_ROOT + "/Sky",
    )
    rows.append({"label": sky_actor.get_actor_label(), "created": created, "source_object_index": skies[0]["source_object_index"], "property_failures": failures})
    for index, source in enumerate(clouds):
        label = "SP_Environment_Cloud_{}".format(index)
        actor, created = spawn_or_reuse(
            actor_subsystem, by_label, unreal.StaticMeshActor, label
        )
        failures = configure_static_mesh_actor(
            actor,
            assets["cloud_mesh"],
            assets["cloud_materials"][index],
            source["transform"],
            FOLDER_ROOT + "/Sky",
        )
        rows.append({"label": label, "created": created, "source_object_index": source["source_object_index"], "property_failures": failures})
    wind_source = winds[0]
    wind, created = spawn_or_reuse(
        actor_subsystem,
        by_label,
        unreal.WindDirectionalSource,
        "SP_Environment_Wind",
    )
    wind.set_actor_transform(source_transform(wind_source["transform"]), False, False)
    set_actor_folder(wind, FOLDER_ROOT + "/Wind")
    component = wind.get_component_by_class(unreal.WindDirectionalSourceComponent)
    failures = []
    safe_set(component, "speed", float(wind_source["properties"].get("Speed", 0.5)), failures, True)
    rows.append({"label": wind.get_actor_label(), "created": created, "source_object_index": wind_source["source_object_index"], "property_failures": failures})
    return rows


def restore_global_lights(metadata, actor_subsystem, by_label, actors):
    profile = metadata["profiles"][metadata["default_profile_key"]]
    wdl = profile["components"]["directional_light"]["properties"]
    wsl = profile["components"]["sky_light"]["properties"]
    center = unreal.Vector(18278.31, 51594.58, 21658.588)
    label = "SP_Environment_DirectionalLight"
    sun = by_label.get(label)
    adopted = False
    created = False
    if not sun:
        candidates = [
            actor
            for actor in actors
            if isinstance(actor, unreal.DirectionalLight)
            and not actor.get_actor_label().startswith("SP_SourceLight_")
            and not actor.get_actor_label().startswith(MANAGED_PREFIX)
        ]
        if len(candidates) == 1:
            sun = candidates[0]
            sun.set_actor_label(label, mark_dirty=True)
            by_label[label] = sun
            adopted = True
        elif candidates:
            raise RuntimeError("Multiple unmanaged DirectionalLight actors found")
        else:
            sun, created = spawn_or_reuse(
                actor_subsystem, by_label, unreal.DirectionalLight, label, center
            )
    rotation = wdl.get("RelativeRotation") or {}
    sun.set_actor_location(center, False, False)
    sun.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    sun.set_actor_rotation(
        unreal.Rotator(
            pitch=float(rotation.get("Pitch", -90.0)),
            yaw=float(rotation.get("Yaw", 0.0)),
            roll=float(rotation.get("Roll", 0.0)),
        ),
        False,
    )
    set_actor_folder(sun, FOLDER_ROOT + "/Lighting")
    component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    failures = []
    for name, value, required in (
        ("mobility", unreal.ComponentMobility.MOVABLE, True),
        ("intensity", 10.0, True),
        ("cast_shadows", True, True),
        ("enable_light_shaft_occlusion", bool(wdl.get("bEnableLightShaftOcclusion", True)), False),
        ("occlusion_mask_darkness", float(wdl.get("OcclusionMaskDarkness", 0.9)), False),
        ("occlusion_depth_range", float(wdl.get("OcclusionDepthRange", 50000.0)), False),
        ("cascade_distribution_exponent", float(wdl.get("CascadeDistributionExponent", 2.5)), False),
        ("cascade_transition_fraction", float(wdl.get("CascadeTransitionFraction", 0.25)), False),
        ("distance_field_shadow_distance", float(wdl.get("DistanceFieldShadowDistance", 100000.0)), False),
        ("specular_scale", float(wdl.get("SpecularScale", 0.01)), False),
        ("enable_light_shaft_bloom", bool(wdl.get("bEnableLightShaftBloom", True)), False),
        ("bloom_scale", float(wdl.get("BloomScale", 0.05)), False),
        ("bloom_threshold", float(wdl.get("BloomThreshold", -2.0)), False),
        ("bloom_tint", fcolor(wdl.get("BloomTint")), False),
        ("light_color", fcolor(wdl.get("LightColor")), True),
    ):
        safe_set(component, name, value, failures, required)

    sky, sky_created = spawn_or_reuse(
        actor_subsystem, by_label, unreal.SkyLight, "SP_Environment_SkyLight", center
    )
    set_actor_folder(sky, FOLDER_ROOT + "/Lighting")
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_failures = []
    safe_set(sky_component, "mobility", unreal.ComponentMobility.MOVABLE, sky_failures, True)
    safe_set(sky_component, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, sky_failures, True)
    safe_set(sky_component, "real_time_capture", True, sky_failures, True)
    safe_set(sky_component, "intensity", float(wsl.get("Intensity", 1.0)), sky_failures, True)
    safe_set(sky_component, "light_color", fcolor(wsl.get("LightColor")), sky_failures, True)
    safe_set(sky_component, "lower_hemisphere_is_black", False, sky_failures)
    safe_set(sky_component, "lower_hemisphere_color", linear_color(wsl.get("LowerHemisphereColor")), sky_failures)
    # Real-time capture can retain the previous black/invalid sky for several
    # editor frames after a material-parent swap.  Force one deterministic capture
    # so distant mountains and foliage receive the restored ambient contribution.
    sky_component.recapture_sky()
    return {
        "directional_light": {
            "label": label,
            "created": created,
            "adopted_unmanaged_actor": adopted,
            "source_profile": metadata["default_profile_key"],
            "source_type": profile["components"]["directional_light"]["source_type"],
            "property_failures": failures,
        },
        "sky_light": {
            "label": sky.get_actor_label(),
            "created": sky_created,
            "source_profile": metadata["default_profile_key"],
            "source_type": profile["components"]["sky_light"]["source_type"],
            "recaptured_after_visual_material_restore": True,
            "property_failures": sky_failures,
        },
    }


def restore_reflections(metadata, cubemap, actor_subsystem, by_label):
    rows = []
    for index, source in enumerate(metadata["reflection_captures"]):
        label = "SP_Environment_Reflection_{:02d}".format(index)
        transform = source["transform"]
        actor, created = spawn_or_reuse(
            actor_subsystem,
            by_label,
            unreal.SphereReflectionCapture,
            label,
            source_vector(transform.get("location_cm")),
            source_rotator(transform.get("rotation_degrees")),
        )
        actor.set_actor_transform(source_transform(transform), False, False)
        set_actor_folder(actor, FOLDER_ROOT + "/Reflections")
        component = actor.get_component_by_class(unreal.SphereReflectionCaptureComponent)
        failures = []
        safe_set(component, "reflection_source_type", unreal.ReflectionSourceType.SPECIFIED_CUBEMAP, failures, True)
        safe_set(component, "cubemap", cubemap, failures, True)
        safe_set(component, "influence_radius", float(source["influence_radius_cm"]), failures, True)
        safe_set(component, "brightness", float(source["brightness"]), failures, True)
        rows.append({"label": label, "created": created, "source_actor_index": source["source_actor_index"], "source_actor_name": source["source_actor_name"], "property_failures": failures})
    return rows


def convert_post_value(value, kind):
    if kind == "float":
        return float(value)
    if kind == "int":
        return int(value)
    if kind == "bool":
        return bool(value)
    if kind == "linear_color":
        return linear_color(value)
    if kind == "vector4":
        return unreal.Vector4(
            float(value.get("X", 0.0)),
            float(value.get("Y", 0.0)),
            float(value.get("Z", 0.0)),
            float(value.get("W", 1.0)),
        )
    raise RuntimeError("Unknown post-process value kind: " + kind)


def apply_post_settings(actor, source_settings):
    settings = actor.get_editor_property("settings")
    failures = []
    applied = []
    unsupported = []
    for source_name, value in source_settings.items():
        if source_name.startswith("bOverride_"):
            continue
        mapping = POST_PROCESS_FIELDS.get(source_name)
        if mapping is None:
            if source_name not in {"WeightedBlendables", "LensFlareBokehShape", "AutoExposureBiasBackup", "FFXCACAOEnable", "FFXCACAORadius", "FFXCACAOShadowMultiplier", "FFXCACAOQuality"}:
                unsupported.append(source_name)
            continue
        property_name, kind = mapping
        converted = convert_post_value(value, kind)
        override_name = "override_" + property_name
        if safe_set(settings, override_name, True, failures):
            if safe_set(settings, property_name, converted, failures):
                applied.append(property_name)
    actor.set_editor_property("settings", settings)
    return {
        "applied_properties": sorted(applied),
        "unsupported_source_properties": sorted(unsupported),
        "property_failures": failures,
    }


def volume_proxy_transform(source):
    actor_transform = source_transform(source["transform"])
    origin = source_vector(source["model_origin_cm"])
    local_origin = unreal.Transform(location=origin)
    world_center_transform = unreal.MathLibrary.compose_transforms(local_origin, actor_transform)
    world_center = world_center_transform.translation
    source_scale = source_vector(source["transform"].get("scale"), 1.0)
    extent = source_vector(source["model_box_extent_cm"])
    proxy_scale = unreal.Vector(
        abs(source_scale.x * extent.x / 100.0),
        abs(source_scale.y * extent.y / 100.0),
        abs(source_scale.z * extent.z / 100.0),
    )
    return world_center, source_rotator(source["transform"].get("rotation_degrees")), proxy_scale


def configure_post_actor(actor, source, profile, is_fallback=False):
    failures = []
    if is_fallback:
        actor.set_actor_location(unreal.Vector(18278.31, 51594.58, 21658.588), False, False)
        actor.set_actor_rotation(unreal.Rotator(), False)
        actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
        safe_set(actor, "unbound", True, failures, True)
        safe_set(actor, "priority", -100.0, failures, True)
        safe_set(actor, "blend_radius", 0.0, failures)
        safe_set(actor, "blend_weight", 1.0, failures, True)
        safe_set(actor, "enabled", True, failures, True)
    else:
        center, rotation, scale = volume_proxy_transform(source)
        actor.set_actor_location(center, False, False)
        actor.set_actor_rotation(rotation, False)
        actor.set_actor_scale3d(scale)
        safe_set(actor, "unbound", bool(source["unbound"]), failures, True)
        safe_set(actor, "priority", float(source["priority"]), failures, True)
        safe_set(actor, "blend_radius", float(source["blend_radius"]), failures, True)
        safe_set(actor, "blend_weight", float(source["blend_weight"]), failures, True)
        safe_set(actor, "enabled", bool(source["enabled"]), failures, True)
    result = apply_post_settings(actor, profile["default_properties"].get("Settings") or {})
    result["actor_property_failures"] = failures
    return result


def restore_post_process(metadata, actor_subsystem, by_label):
    rows = []
    for source in metadata["post_process_volumes"]:
        label = "SP_Environment_PP_{}_{:03d}".format(source["source_level"], int(source["source_actor_index"]))
        actor, created = spawn_or_reuse(actor_subsystem, by_label, unreal.PostProcessVolume, label)
        set_actor_folder(actor, FOLDER_ROOT + "/PostProcess/" + source["profile_key"])
        result = configure_post_actor(actor, source, metadata["profiles"][source["profile_key"]])
        rows.append({
            "label": label,
            "created": created,
            "source_level": source["source_level"],
            "source_actor_index": source["source_actor_index"],
            "source_actor_name": source["source_actor_name"],
            "profile_key": source["profile_key"],
            "source_axis_aligned_box": source["axis_aligned_box_model"],
            "volume_geometry_policy": "exact_source_box" if source["axis_aligned_box_model"] else "source_bounds_proxy_with_exact_BSP_metadata_retained",
            **result,
        })
    fallback, created = spawn_or_reuse(
        actor_subsystem,
        by_label,
        unreal.PostProcessVolume,
        "SP_Environment_PostProcessFallback",
    )
    set_actor_folder(fallback, FOLDER_ROOT + "/PostProcess")
    result = configure_post_actor(
        fallback, None, metadata["profiles"][metadata["default_profile_key"]], True
    )
    rows.append({
        "label": fallback.get_actor_label(),
        "created": created,
        "profile_key": metadata["default_profile_key"],
        "volume_geometry_policy": "unbound_editor_fallback_for_original_environment_manager",
        **result,
    })
    return rows


def restore_fog_last(metadata, actor_subsystem, by_label):
    profile_key = metadata["default_profile_key"]
    fog_source = metadata["profiles"][profile_key]["components"]["fog"]["properties"]
    outside_volumes = [row for row in metadata["post_process_volumes"] if row["profile_key"] == profile_key and row["source_actor_name"] == "WEP_StormPass_Outside_2"]
    if len(outside_volumes) != 1:
        raise RuntimeError("Primary outside WEP volume is ambiguous")
    base_location = source_vector(outside_volumes[0]["transform"]["location_cm"])
    offset = fog_source.get("CameraFollowOffset") or {}
    location = unreal.Vector(
        base_location.x + float(offset.get("X", 0.0)),
        base_location.y + float(offset.get("Y", 0.0)),
        base_location.z + float(offset.get("Z", 0.0)),
    )
    actor, created = spawn_or_reuse(
        actor_subsystem,
        by_label,
        unreal.ExponentialHeightFog,
        "SP_Environment_HeightFog",
        location,
    )
    actor.set_actor_location(location, False, False)
    set_actor_folder(actor, FOLDER_ROOT + "/Fog")
    component = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    failures = []

    fog_density = float(fog_source.get("FogDensity", 0.5)) * FOG_DENSITY_SCALE
    fog_falloff = float(fog_source.get("FogHeightFalloff", 1.0)) * FOG_HEIGHT_FALLOFF_SCALE
    second = fog_source.get("SecondFogData") or {}
    settings = (
        ("fog_density", fog_density),
        ("fog_height_falloff", fog_falloff),
        ("fog_max_opacity", float(fog_source.get("FogMaxOpacity", 1.0))),
        ("directional_inscattering_exponent", float(fog_source.get("DirectionalInscatteringExponent", 2.5))),
        ("directional_inscattering_start_distance", float(fog_source.get("DirectionalInscatteringStartDistance", 0.0))),
        ("enable_volumetric_fog", True),
        ("volumetric_fog_scattering_distribution", float(fog_source.get("VolumetricFogScatteringDistribution", 0.25))),
        ("volumetric_fog_albedo", fcolor(fog_source.get("VolumetricFogAlbedo"), 255)),
        ("volumetric_fog_emissive", linear_color(fog_source.get("VolumetricFogEmissive"))),
        ("volumetric_fog_extinction_scale", float(fog_source.get("VolumetricFogExtinctionScale", 1.25))),
        ("volumetric_fog_distance", float(fog_source.get("VolumetricFogDistance", 10000.0))),
        ("volumetric_fog_static_lighting_scattering_intensity", float(fog_source.get("VolumetricFogStaticLightingScatteringIntensity", 0.0))),
    )
    for name, value in settings:
        safe_set(component, name, value, failures, True)
    safe_set(component, "fog_inscattering_luminance", linear_color(fog_source.get("FogInscatteringColor")), failures, True)
    if fog_source.get("DirectionalInscatteringColor"):
        safe_set(component, "directional_inscattering_luminance", linear_color(fog_source.get("DirectionalInscatteringColor")), failures)
    try:
        component.set_second_fog_density(float(second.get("FogDensity", 0.0)) * FOG_DENSITY_SCALE)
        component.set_second_fog_height_falloff(float(second.get("FogHeightFalloff", 0.0)) * FOG_HEIGHT_FALLOFF_SCALE)
        component.set_second_fog_height_offset(float(second.get("FogHeightOffset", 0.0)))
    except Exception as exception:
        failures.append({"object": component.get_path_name(), "property": "second_fog_data", "required": True, "error": str(exception)})
        raise
    return {
        "label": actor.get_actor_label(),
        "created": created,
        "source_profile": profile_key,
        "source_component_type": metadata["profiles"][profile_key]["components"]["fog"]["source_type"],
        "fog_stage_order": "last",
        "source_camera_follow": bool(fog_source.get("bCameraFollow", False)),
        "static_editor_location_cm": [location.x, location.y, location.z],
        "conversion": {
            "fog_density_scale": FOG_DENSITY_SCALE,
            "fog_height_falloff_scale": FOG_HEIGHT_FALLOFF_SCALE,
            "reason": "Source WEP profile uses normalized custom-renderer units; converted to native UE5 exponential-fog units.",
        },
        "applied_fog_density": fog_density,
        "applied_fog_height_falloff": fog_falloff,
        "property_failures": failures,
    }


def validate_environment(metadata, actors, labels):
    by_label = {actor.get_actor_label(): actor for actor in actors}
    present = {label for label in by_label if label.startswith(MANAGED_PREFIX)}
    missing = sorted(labels - present)
    unexpected = sorted(present - labels)
    class_counts = {}
    for label in sorted(labels):
        actor = by_label.get(label)
        if actor:
            name = actor.get_class().get_name()
            class_counts[name] = class_counts.get(name, 0) + 1
    failures = []
    if missing:
        failures.append("missing_managed_environment_actors")
    if unexpected:
        failures.append("unexpected_managed_environment_actors")
    if len(present) != EXPECTED_ENVIRONMENT_ACTOR_COUNT:
        failures.append("environment_actor_count")
    if len(actors) != EXPECTED_FINAL_ACTOR_COUNT:
        failures.append("total_actor_count")
    return {
        "expected_labels": sorted(labels),
        "present_count": len(present),
        "expected_count": EXPECTED_ENVIRONMENT_ACTOR_COUNT,
        "missing_labels": missing,
        "unexpected_labels": unexpected,
        "class_counts": class_counts,
        "total_actor_count": len(actors),
        "expected_total_actor_count": EXPECTED_FINAL_ACTOR_COUNT,
        "failures": failures,
    }


def main():
    metadata = load_json(METADATA_PATH)
    if metadata.get("status") != "passed" or metadata.get("level") != "StormPass":
        raise RuntimeError("StormPass environment source manifest is not audited")
    if metadata.get("fog_restore_order") != "last":
        raise RuntimeError("StormPass Fog ordering policy changed")
    level_subsystem = load_map()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = list(actor_subsystem.get_all_level_actors())
    protected_before = core_signature(actors_before)
    labels = expected_labels(metadata)
    existing_managed = {
        actor.get_actor_label()
        for actor in actors_before
        if actor.get_actor_label().startswith(MANAGED_PREFIX)
    }
    unexpected_managed = sorted(existing_managed - labels)
    if unexpected_managed:
        raise RuntimeError("Unexpected managed environment actor: " + unexpected_managed[0])
    unmanaged = [
        actor
        for actor in actors_before
        if not any(actor.get_actor_label().startswith(prefix) for prefix in CORE_PREFIX_COUNTS)
        and not actor.get_actor_label().startswith(MANAGED_PREFIX)
    ]
    if unmanaged and not (
        len(unmanaged) == 1 and isinstance(unmanaged[0], unreal.DirectionalLight)
    ):
        raise RuntimeError(
            "Unexpected unmanaged actor boundary: "
            + ", ".join(actor.get_actor_label() for actor in unmanaged[:10])
        )

    prepared = prepare_assets(metadata)
    actors_current = list(actor_subsystem.get_all_level_actors())
    by_label = {actor.get_actor_label(): actor for actor in actors_current}

    # Non-Fog environment content first.
    sky_cloud_wind = restore_sky_cloud_wind(
        metadata, prepared["objects"], actor_subsystem, by_label
    )
    global_lights = restore_global_lights(
        metadata,
        actor_subsystem,
        by_label,
        list(actor_subsystem.get_all_level_actors()),
    )
    reflections = restore_reflections(
        metadata, prepared["objects"]["cubemap"], actor_subsystem, by_label
    )
    post_process = restore_post_process(metadata, actor_subsystem, by_label)

    # Fog is intentionally and verifiably the last mutation stage.
    fog = restore_fog_last(metadata, actor_subsystem, by_label)

    actors_after = list(actor_subsystem.get_all_level_actors())
    protected_after = core_signature(actors_after)
    if protected_after != protected_before:
        raise RuntimeError("Protected StormPass actor transforms changed")
    validation = validate_environment(metadata, actors_after, labels)
    if validation["failures"]:
        raise RuntimeError(
            "Environment validation failed: " + ", ".join(validation["failures"])
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save StormPass environment map")
    unreal.EditorAssetLibrary.save_directory(
        ASSET_ROOT, only_if_is_dirty=False, recursive=True
    )
    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "metadata_path": METADATA_PATH,
        "protected_core_before": protected_before,
        "protected_core_after": protected_after,
        "assets": prepared["report"],
        "sky_cloud_wind": sky_cloud_wind,
        "global_lights": global_lights,
        "reflection_captures": reflections,
        "post_process_volumes": post_process,
        "fog": fog,
        "validation": validation,
        "source_fidelity_notes": [
            "All ten WEP actor transforms, priorities, profile values, BSP bounds, and exact BSP point/plane metadata are retained.",
            "Four box WEP brushes use exact native PostProcessVolume geometry; six irregular source BSP brushes use their exact transformed bounds because arbitrary cooked BSP mutation is not exposed to Unreal Python.",
            "The unbound Outside fallback emulates the original custom environment manager while editing the consolidated content-only map.",
            "The original custom FOG units are converted to native UE5 exponential-fog units using explicit recorded scales.",
        ],
        "excluded_content": [
            "Gameplay, character, animation, spawn, quest, navigation, cinema, sound, and source code",
            "HeinMach content and user-deleted HeinMach actors",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status=restored actors={} environment={} protected={} report={}".format(
            len(actors_after),
            validation["present_count"],
            protected_after["actor_count"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": "{}: {}".format(type(exception).__name__, exception),
            "traceback": traceback.format_exc(),
            "map_path": MAP_PATH,
            "backup_map_path": BACKUP_MAP_PATH,
        }
        write_json(REPORT_PATH, failure)
        unreal.log_error("KHAZAN_STORMPASS_ENVIRONMENT: " + failure["error"])
        raise
