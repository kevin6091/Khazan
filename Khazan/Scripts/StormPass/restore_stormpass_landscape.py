"""Build and place the reconstructed StormPass Landscape render terrain.

The exact FModel/CUE4Parse component geometry, full-landscape weight masks,
surface textures, material tiling values, packed channels, root transforms,
and collision are authoritative.  The original Base_Terrain5 graph and its
RVT covering branch are not exportable; only the Phase-2 upward-facing snow
cover uses a documented conservative slope approximation.  Fog is a hard
zero-count boundary throughout this pass.
"""

import importlib.util
import json
import math
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MESH_SCRIPT_PATH = os.path.join(
    SCRIPT_DIR, "import_stormpass_landscape_meshes.py"
)
COMPONENT_METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeComponents.json",
)
MATERIAL_SOURCE_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeMaterialSources.json",
)
TEXTURE_ASSET_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_LandscapeTextureAssets.json",
)
MATERIAL_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Landscape_MaterialBuild.json",
)
RESTORATION_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Landscape_Restoration.json",
)
RELOAD_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_Landscape_ReloadAudit.json",
)
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreLandscapeRestore"
)
MATERIAL_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Landscape/Materials"
)
MATERIAL_PATHS = {
    "Main": MATERIAL_ROOT + "/M_SP_Landscape_Main",
    "Boss": MATERIAL_ROOT + "/M_SP_Landscape_Boss",
}
MANAGED_LABEL_PREFIX = "SP_Landscape_"
MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/Landscape"
EXPECTED_COMPONENT_COUNT = 456
EXPECTED_COUNTS = {"Main": 440, "Boss": 16}
EXPECTED_FOG_COUNT = 0
TRANSFORM_TOLERANCE = 0.02
GRAPH_VERSION = 1


def log(message):
    unreal.log("KHAZAN_STORMPASS_LANDSCAPE_RESTORE: " + str(message))


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_mesh_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_landscape_meshes", MESH_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load StormPass Landscape mesh helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mesh_helpers = load_mesh_module()


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        if not unreal.EditorAssetLibrary.make_directory(path):
            raise RuntimeError("Unable to create asset directory: " + path)


def object_path(value):
    return value.get_path_name() if value else None


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value))
    return re.sub(r"_+", "_", value).strip("_") or "Unnamed"


def expression(material, expression_class, x, y):
    node = unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, int(x), int(y)
    )
    if not node:
        raise RuntimeError("Failed to create material expression")
    return node


def pin(node, output=""):
    return node, output


def connect(source, destination, input_name):
    node, output_name = source
    if not unreal.MaterialEditingLibrary.connect_material_expressions(
        node, output_name, destination, input_name
    ):
        raise RuntimeError(
            "Failed to connect {} -> {}:{}".format(
                node.get_class().get_name(),
                destination.get_class().get_name(),
                input_name,
            )
        )


def constant(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(value))
    return pin(node)


def constant2(material, x_value, y_value, x, y):
    node = expression(material, unreal.MaterialExpressionConstant2Vector, x, y)
    node.set_editor_property("r", float(x_value))
    node.set_editor_property("g", float(y_value))
    return pin(node)


def scalar_parameter(material, name, value, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property("default_value", float(value))
    return pin(node)


def vector_parameter(material, name, value, x, y):
    node = expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property(
        "default_value",
        unreal.LinearColor(
            float(value["r"]),
            float(value["g"]),
            float(value["b"]),
            float(value["a"]),
        ),
    )
    return node


def binary(material, expression_class, a, b, x, y):
    node = expression(material, expression_class, x, y)
    connect(a, node, "A")
    connect(b, node, "B")
    return pin(node)


def add(material, a, b, x, y):
    return binary(material, unreal.MaterialExpressionAdd, a, b, x, y)


def subtract(material, a, b, x, y):
    return binary(material, unreal.MaterialExpressionSubtract, a, b, x, y)


def multiply(material, a, b, x, y):
    return binary(material, unreal.MaterialExpressionMultiply, a, b, x, y)


def divide(material, a, b, x, y):
    return binary(material, unreal.MaterialExpressionDivide, a, b, x, y)


def lerp(material, a, b, alpha, x, y):
    node = expression(material, unreal.MaterialExpressionLinearInterpolate, x, y)
    connect(a, node, "A")
    connect(b, node, "B")
    connect(alpha, node, "Alpha")
    return pin(node)


def saturate(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionSaturate, x, y)
    connect(value, node, "None")
    return pin(node)


def normalize(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionNormalize, x, y)
    connect(value, node, "VectorInput")
    return pin(node)


def one_minus(material, value, x, y):
    node = expression(material, unreal.MaterialExpressionOneMinus, x, y)
    connect(value, node, "None")
    return pin(node)


def component_mask(material, value, channel, x, y):
    node = expression(material, unreal.MaterialExpressionComponentMask, x, y)
    for name in ("r", "g", "b", "a"):
        node.set_editor_property(name, name == channel.lower())
    connect(value, node, "None")
    return pin(node)


def texture_parameter(
    material,
    name,
    texture,
    sampler_type,
    sampler_source,
    uv,
    x,
    y,
):
    node = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, x, y
    )
    node.set_editor_property("parameter_name", str(name))
    node.set_editor_property("texture", texture)
    node.set_editor_property("sampler_type", sampler_type)
    node.set_editor_property("sampler_source", sampler_source)
    connect(uv, node, "UVs")
    return node


def load_canonical_sources():
    material_source = load_json(MATERIAL_SOURCE_PATH)
    texture_source = load_json(TEXTURE_ASSET_PATH)
    if material_source.get("status") != "passed":
        raise RuntimeError("Landscape material source audit is not passed")
    if texture_source.get("status") != "passed":
        raise RuntimeError("Landscape texture asset audit is not passed")
    if int(material_source.get("decoded_surface_texture_count", -1)) != 37:
        raise RuntimeError("Landscape surface texture inventory changed")
    if int(texture_source.get("texture_count", -1)) != 53:
        raise RuntimeError("Landscape imported texture inventory changed")

    plans = {
        row["material_name"]: row for row in material_source["surface_plans"]
    }
    landscapes = {
        row["source_level"]: row for row in material_source["landscapes"]
    }
    if set(plans) != {"WLM_Stormpass", "WLM_Stormpass_Phase2"}:
        raise RuntimeError("Landscape surface plan inventory changed")
    if set(landscapes) != {"StormPass_Landscape", "StormPass_Boss_Phase_2"}:
        raise RuntimeError("Landscape source inventory changed")

    surface_assets = {}
    weight_assets = {}
    normal_assets = {}
    for row in texture_source["textures"]:
        asset = unreal.EditorAssetLibrary.load_asset(row["asset_path"])
        if not asset or asset.get_class().get_name() != "Texture2D":
            raise RuntimeError("Landscape Texture2D is missing: " + row["asset_path"])
        if row["kind"] == "surface":
            key = row["source_name"]
            if key in surface_assets:
                raise RuntimeError("Duplicate Landscape surface texture: " + key)
            surface_assets[key] = asset
        elif row["kind"] == "weight":
            group = "Main" if "/Weightmaps/Main/" in row["asset_path"] else "Boss"
            key = (group, row["material_layer_name"])
            if key in weight_assets:
                raise RuntimeError("Duplicate Landscape weight texture: " + str(key))
            weight_assets[key] = asset
        elif row["kind"] == "landscape_normal":
            group = "Main" if "/Weightmaps/Main/" in row["asset_path"] else "Boss"
            normal_assets[group] = asset
    if (len(surface_assets), len(weight_assets), len(normal_assets)) != (37, 14, 2):
        raise RuntimeError("Landscape Texture2D classification changed")
    return material_source, plans, landscapes, surface_assets, weight_assets, normal_assets


def records_by_group():
    _metadata, _landscapes, records = mesh_helpers.load_inventory()
    grouped = {"Main": [], "Boss": []}
    for record in records:
        grouped[record["destination_group"]].append(record)
        if not mesh_helpers.component_mesh_path(record):
            raise RuntimeError(
                "Landscape component mesh is missing: " + record["component_name"]
            )
    if {key: len(value) for key, value in grouped.items()} != EXPECTED_COUNTS:
        raise RuntimeError("Landscape component group inventory changed")
    return grouped


def landscape_coordinates(material, landscape, records):
    root = records[0]["root_transform"]
    for record in records[1:]:
        if record["root_transform"] != root:
            raise RuntimeError("Landscape component root transform is inconsistent")
    minimum_x = min(
        int(row["section_base"]["x"]) + int(row["cached_local_box"]["min"]["x"])
        for row in records
    )
    minimum_y = min(
        int(row["section_base"]["y"]) + int(row["cached_local_box"]["min"]["y"])
        for row in records
    )
    maximum_x = max(
        int(row["section_base"]["x"]) + int(row["cached_local_box"]["max"]["x"])
        for row in records
    )
    maximum_y = max(
        int(row["section_base"]["y"]) + int(row["cached_local_box"]["max"]["y"])
        for row in records
    )
    width = int(landscape["dimensions"]["width"])
    height = int(landscape["dimensions"]["height"])
    if (maximum_x - minimum_x + 1, maximum_y - minimum_y + 1) != (width, height):
        raise RuntimeError("Landscape dimensions do not match component extents")

    world_position = expression(
        material, unreal.MaterialExpressionWorldPosition, -2500, -850
    )
    world_xy = pin(world_position, "XY")
    root_location = root["location_cm"]
    root_scale = root["scale"]
    local_xy = divide(
        material,
        subtract(
            material,
            world_xy,
            constant2(
                material,
                root_location["x"],
                root_location["y"],
                -2500,
                -700,
            ),
            -2250,
            -820,
        ),
        constant2(
            material, root_scale["x"], root_scale["y"], -2250, -670
        ),
        -2000,
        -820,
    )
    extent_xy = subtract(
        material,
        local_xy,
        constant2(material, minimum_x, minimum_y, -2000, -680),
        -1750,
        -820,
    )
    pixel_center = add(
        material,
        extent_xy,
        constant2(material, 0.5, 0.5, -1750, -680),
        -1500,
        -820,
    )
    global_uv = divide(
        material,
        pixel_center,
        constant2(material, width, height, -1500, -680),
        -1250,
        -820,
    )
    return world_xy, global_uv, {
        "root_transform": root,
        "minimum_section_coordinate": {"x": minimum_x, "y": minimum_y},
        "maximum_section_coordinate": {"x": maximum_x, "y": maximum_y},
        "dimensions": {"width": width, "height": height},
        "weight_uv_formula": (
            "((AbsoluteWorldXY - RootLocationXY) / RootScaleXY "
            "- MinSectionXY + 0.5) / DimensionsXY"
        ),
    }


def surface_uv(material, world_xy, layer_name, tiling_meters, y):
    tiling = scalar_parameter(
        material,
        "TilingMeters_{}".format(safe_name(layer_name)),
        tiling_meters,
        -2250,
        y,
    )
    centimeters = multiply(
        material,
        tiling,
        constant(material, 100.0, -2250, y + 100),
        -2000,
        y,
    )
    return divide(material, world_xy, centimeters, -1750, y)


def create_weight_samples(material, group, landscape, global_uv, weight_assets):
    samples = {}
    used = set()
    for index, layer in enumerate(landscape["weight_layers"]):
        layer_name = layer["material_layer_name"]
        texture = weight_assets.get((group, layer_name))
        if not texture:
            raise RuntimeError(
                "Missing {} Landscape weight asset: {}".format(group, layer_name)
            )
        node = texture_parameter(
            material,
            "Weight_{}".format(safe_name(layer_name)),
            texture,
            unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            unreal.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS,
            global_uv,
            -1000,
            -900 + index * 180,
        )
        samples[layer_name] = pin(node, "R")
        used.add(texture.get_path_name())
    return samples, used


def create_surface_layer(
    material,
    world_xy,
    layer,
    weight,
    surface_assets,
    index,
    name_prefix=None,
):
    layer_name = name_prefix or layer["layer_name"]
    y = -300 + index * 520
    uv = surface_uv(
        material, world_xy, layer_name, float(layer["tiling_meters"]), y
    )
    semantics = {
        "diffuse": (
            unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
            "RGB",
            unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
        ),
        "normal": (
            unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
            "RGB",
            unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
        ),
        "surface": (
            unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            "RGB",
            unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
        ),
    }
    nodes = {}
    used = set()
    for semantic_index, semantic in enumerate(("diffuse", "normal", "surface")):
        texture_name = layer["textures"][semantic]["object_name"]
        texture = surface_assets.get(texture_name)
        if not texture:
            raise RuntimeError("Missing Landscape surface texture: " + texture_name)
        sampler_type, _output, sampler_source = semantics[semantic]
        nodes[semantic] = texture_parameter(
            material,
            "{}_{}".format(safe_name(layer_name), semantic.capitalize()),
            texture,
            sampler_type,
            sampler_source,
            uv,
            -1450 + semantic_index * 260,
            y,
        )
        used.add(texture.get_path_name())

    weighted = {
        "base_color": multiply(
            material, pin(nodes["diffuse"], "RGB"), weight, -600, y
        ),
        "normal": multiply(
            material, pin(nodes["normal"], "RGB"), weight, -600, y + 90
        ),
        "ambient_occlusion": multiply(
            material, pin(nodes["surface"], "R"), weight, -600, y + 180
        ),
        "roughness": multiply(
            material, pin(nodes["surface"], "G"), weight, -600, y + 270
        ),
        "metallic": multiply(
            material, pin(nodes["surface"], "B"), weight, -600, y + 360
        ),
    }
    return weighted, used


def accumulate(material, current, value, x, y):
    return value if current is None else add(material, current, value, x, y)


def build_weight_blend(
    material,
    group,
    plan,
    world_xy,
    weight_samples,
    surface_assets,
):
    layer_names = {row["layer_name"] for row in plan["layers"]}
    expected_weight_names = set(layer_names)
    if group == "Boss":
        expected_weight_names.update(("Layer8", "Puddle"))
    if set(weight_samples) != expected_weight_names:
        raise RuntimeError(
            "{} Landscape weight/plan mismatch: {} != {}".format(
                group, sorted(weight_samples), sorted(expected_weight_names)
            )
        )

    effective_weights = dict(weight_samples)
    if group == "Boss":
        effective_weights["Layer1"] = add(
            material,
            weight_samples["Layer1"],
            weight_samples["Layer8"],
            -750,
            -1150,
        )

    accumulators = {
        "base_color": None,
        "normal": None,
        "ambient_occlusion": None,
        "roughness": None,
        "metallic": None,
    }
    total_weight = None
    used = set()
    for index, layer in enumerate(plan["layers"]):
        layer_name = layer["layer_name"]
        weight = effective_weights[layer_name]
        weighted, layer_used = create_surface_layer(
            material,
            world_xy,
            layer,
            weight,
            surface_assets,
            index,
        )
        used.update(layer_used)
        total_weight = accumulate(
            material, total_weight, weight, 0, -500 + index * 80
        )
        for property_index, property_name in enumerate(accumulators):
            accumulators[property_name] = accumulate(
                material,
                accumulators[property_name],
                weighted[property_name],
                50 + index * 180,
                -200 + property_index * 120,
            )

    safe_weight = add(
        material,
        total_weight,
        constant(material, 0.00001, 700, -550),
        900,
        -500,
    )
    outputs = {}
    for property_index, property_name in enumerate(accumulators):
        outputs[property_name] = divide(
            material,
            accumulators[property_name],
            safe_weight,
            1100,
            -200 + property_index * 130,
        )
    outputs["normal"] = normalize(material, outputs["normal"], 1300, -70)
    for property_index, property_name in enumerate(
        ("ambient_occlusion", "roughness", "metallic")
    ):
        outputs[property_name] = saturate(
            material,
            outputs[property_name],
            1300,
            80 + property_index * 130,
        )
    return outputs, used


def apply_covering(material, outputs, plan, world_xy, surface_assets):
    cover = plan.get("covering")
    if not cover:
        return outputs, set(), None
    y = 3900
    uv = surface_uv(
        material,
        world_xy,
        "Covering",
        float(cover["tiling_meters"]),
        y,
    )
    nodes = {}
    used = set()
    sampler_types = {
        "diffuse": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        "surface": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
    }
    for index, semantic in enumerate(("diffuse", "normal", "surface")):
        source_name = cover["textures"][semantic]["object_name"]
        texture = surface_assets.get(source_name)
        if not texture:
            raise RuntimeError("Missing covering texture: " + source_name)
        nodes[semantic] = texture_parameter(
            material,
            "Covering_{}".format(semantic.capitalize()),
            texture,
            sampler_types[semantic],
            unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
            uv,
            -1450 + index * 260,
            y,
        )
        used.add(texture.get_path_name())

    vertex_normal = expression(
        material, unreal.MaterialExpressionVertexNormalWS, -1150, y + 500
    )
    normal_z = component_mask(material, pin(vertex_normal), "b", -950, y + 500)
    snow_height = scalar_parameter(
        material, "SnowHeight_Source", cover["snow_height"], -1450, y + 620
    )
    normalized_height = multiply(
        material,
        snow_height,
        constant(material, 0.01, -1450, y + 740),
        -1200,
        y + 650,
    )
    slope_threshold = one_minus(material, normalized_height, -950, y + 650)
    slope_delta = subtract(material, normal_z, slope_threshold, -700, y + 560)
    height_intensity = scalar_parameter(
        material,
        "HeightIntensity_DeepSnow_Source",
        cover["height_intensity"],
        -700,
        y + 700,
    )
    cover_alpha = saturate(
        material,
        multiply(
            material,
            multiply(
                material, slope_delta, height_intensity, -450, y + 580
            ),
            constant(material, 4.0, -450, y + 720),
            -200,
            y + 580,
        ),
        50,
        y + 580,
    )

    covered = {
        "base_color": lerp(
            material,
            outputs["base_color"],
            pin(nodes["diffuse"], "RGB"),
            cover_alpha,
            1700,
            0,
        ),
        "normal": normalize(
            material,
            lerp(
                material,
                outputs["normal"],
                pin(nodes["normal"], "RGB"),
                cover_alpha,
                1700,
                140,
            ),
            1900,
            140,
        ),
        "ambient_occlusion": lerp(
            material,
            outputs["ambient_occlusion"],
            pin(nodes["surface"], "R"),
            cover_alpha,
            1700,
            280,
        ),
        "roughness": lerp(
            material,
            outputs["roughness"],
            pin(nodes["surface"], "G"),
            cover_alpha,
            1700,
            420,
        ),
        "metallic": lerp(
            material,
            outputs["metallic"],
            pin(nodes["surface"], "B"),
            cover_alpha,
            1700,
            560,
        ),
    }
    return covered, used, {
        "mode": "conservative_upward_slope_approximation",
        "source_snow_height": float(cover["snow_height"]),
        "source_height_intensity": float(cover["height_intensity"]),
        "source_tiling_meters": float(cover["tiling_meters"]),
        "formula": "saturate((VertexNormalWS.Z - (1-SnowHeight/100)) * HeightIntensity * 4)",
        "reason": "The source Base_Terrain5/RVT material graph was not exportable.",
    }


def apply_puddle(material, outputs, plan, weight_samples):
    puddle = plan.get("puddle")
    if not puddle:
        return outputs, None
    weight = weight_samples[puddle["weight_layer"]]
    color_node = vector_parameter(
        material, "Puddle1Color_Source", puddle["color"], 1550, 900
    )
    wet_darkness = scalar_parameter(
        material,
        "WetSurfaceDarkness_Source",
        puddle["wet_surface_darkness"],
        1550,
        1040,
    )
    wet_target = multiply(
        material, outputs["base_color"], pin(color_node, "RGB"), 1800, 900
    )
    color_alpha = saturate(
        material,
        multiply(
            material,
            multiply(
                material, weight, wet_darkness, 1800, 1040
            ),
            pin(color_node, "A"),
            2000,
            1040,
        ),
        2200,
        1040,
    )
    puddle_weight = saturate(material, weight, 1800, 1180)
    result = dict(outputs)
    result["base_color"] = lerp(
        material,
        outputs["base_color"],
        wet_target,
        color_alpha,
        2400,
        900,
    )
    result["roughness"] = lerp(
        material,
        outputs["roughness"],
        scalar_parameter(
            material,
            "Puddle1Roughness_Source",
            puddle["roughness"],
            2000,
            1200,
        ),
        puddle_weight,
        2400,
        1180,
    )
    result["metallic"] = lerp(
        material,
        outputs["metallic"],
        scalar_parameter(
            material,
            "Puddle1Metallic_Source",
            puddle["metallic"],
            2000,
            1340,
        ),
        puddle_weight,
        2400,
        1340,
    )
    return result, {
        "weight_layer": puddle["weight_layer"],
        "color": puddle["color"],
        "wet_surface_darkness": float(puddle["wet_surface_darkness"]),
        "roughness": float(puddle["roughness"]),
        "metallic": float(puddle["metallic"]),
    }


def connect_outputs(material, outputs):
    library = unreal.MaterialEditingLibrary
    properties = {
        "base_color": unreal.MaterialProperty.MP_BASE_COLOR,
        "normal": unreal.MaterialProperty.MP_NORMAL,
        "ambient_occlusion": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,
        "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
        "metallic": unreal.MaterialProperty.MP_METALLIC,
    }
    for name, material_property in properties.items():
        node, output_name = outputs[name]
        if not library.connect_material_property(node, output_name, material_property):
            raise RuntimeError("Failed to connect Landscape material output: " + name)


def create_or_load_material(group):
    path = MATERIAL_PATHS[group]
    material = unreal.EditorAssetLibrary.load_asset(path)
    created = material is None
    if not material:
        ensure_directory(MATERIAL_ROOT)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            os.path.basename(path),
            MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material or material.get_class().get_name() != "Material":
        raise RuntimeError("Unable to create Landscape Material: " + path)
    return material, created


def build_one_material(
    group,
    plan,
    landscape,
    records,
    surface_assets,
    weight_assets,
):
    material, created = create_or_load_material(group)
    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("two_sided", False)
    try:
        material.set_editor_property("tangent_space_normal", True)
    except Exception:
        pass

    world_xy, global_uv, coordinate_metadata = landscape_coordinates(
        material, landscape, records
    )
    weight_samples, weight_used = create_weight_samples(
        material, group, landscape, global_uv, weight_assets
    )
    outputs, surface_used = build_weight_blend(
        material,
        group,
        plan,
        world_xy,
        weight_samples,
        surface_assets,
    )
    outputs, cover_used, covering_metadata = apply_covering(
        material, outputs, plan, world_xy, surface_assets
    )
    outputs, puddle_metadata = apply_puddle(
        material, outputs, plan, weight_samples
    )
    connect_outputs(material, outputs)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)

    expected_textures = weight_used | surface_used | cover_used
    actual_textures = {
        texture.get_path_name()
        for texture in unreal.MaterialEditingLibrary.get_material_used_textures(
            material
        )
        if texture
    }
    missing_textures = sorted(expected_textures - actual_textures)
    unexpected_textures = sorted(actual_textures - expected_textures)
    if missing_textures or unexpected_textures:
        raise RuntimeError(
            "{} Landscape material texture binding mismatch: missing={} unexpected={}".format(
                group, missing_textures[:3], unexpected_textures[:3]
            )
        )
    return material, {
        "group": group,
        "asset_path": material.get_path_name(),
        "created": created,
        "graph_version": GRAPH_VERSION,
        "expression_count": int(
            unreal.MaterialEditingLibrary.get_num_material_expressions(material)
        ),
        "weight_layer_count": len(weight_samples),
        "surface_layer_count": len(plan["layers"]),
        "used_texture_count": len(actual_textures),
        "used_textures": sorted(actual_textures),
        "missing_texture_count": 0,
        "unexpected_texture_count": 0,
        "coordinate_mapping": coordinate_metadata,
        "packed_surface_channels": {
            "ambient_occlusion": "R",
            "roughness": "G",
            "metallic": "B",
        },
        "layer8_policy": plan.get("layer8_policy"),
        "puddle": puddle_metadata,
        "covering": covering_metadata,
        "geometry_displacement_policy": (
            "Not applied: exact exported component geometry already contains "
            "the authoritative Landscape height surface."
        ),
    }


def world_snapshot():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    actors = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()
    fog = []
    for actor in actors:
        if not actor:
            continue
        label = actor.get_actor_label()
        class_name = actor.get_class().get_name()
        if label.startswith("SP_Fog_") or "Fog" in class_name:
            fog.append({"label": label, "class": class_name})
    fog.sort(key=lambda row: (row["label"], row["class"]))
    return {
        "world_path": world.get_path_name() if world else None,
        "actor_count": len(actors),
        "fog_actor_count": len(fog),
        "fog_actors": fog,
    }


def assert_fog_zero(snapshot, context):
    if int(snapshot.get("fog_actor_count", -1)) != EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog boundary changed {}".format(context))


def build_materials():
    (
        _material_source,
        plans,
        landscapes,
        surface_assets,
        weight_assets,
        _normal_assets,
    ) = load_canonical_sources()
    grouped = records_by_group()
    plan_names = {
        "Main": "WLM_Stormpass",
        "Boss": "WLM_Stormpass_Phase2",
    }
    source_levels = {
        "Main": "StormPass_Landscape",
        "Boss": "StormPass_Boss_Phase_2",
    }
    before = world_snapshot()
    assert_fog_zero(before, "before material build")
    materials = {}
    details = []
    for group in ("Main", "Boss"):
        material, detail = build_one_material(
            group,
            plans[plan_names[group]],
            landscapes[source_levels[group]],
            grouped[group],
            surface_assets,
            weight_assets,
        )
        materials[group] = material
        details.append(detail)
    unreal.EditorAssetLibrary.save_directory(
        MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )
    after = world_snapshot()
    assert_fog_zero(after, "after material build")
    if after != before:
        raise RuntimeError("Editor world changed during asset-only material build")
    report = {
        "status": "passed",
        "operation": "asset_only_landscape_material_build",
        "map_modified": False,
        "graph_version": GRAPH_VERSION,
        "canonical_material_source": MATERIAL_SOURCE_PATH,
        "canonical_texture_assets": TEXTURE_ASSET_PATH,
        "material_count": len(details),
        "materials": details,
        "exact_source_scope": [
            "456 FModel Landscape component meshes",
            "14 decoded full-Landscape weightmaps",
            "37 decoded WLM surface textures",
            "12 active source surface groups and source tiling values",
            "packed AO=R, Roughness=G, Metallic=B channels",
            "Phase-2 Puddle weight, color, darkness, roughness and metallic",
        ],
        "documented_approximation": (
            "Only the Phase-2 Base_Terrain5/RVT covering mask is approximated "
            "from upward slope; its source Snow 004 textures and scalar values "
            "remain exact."
        ),
        "fog_policy": "deferred_until_final_pass",
        "world_before": before,
        "world_after": after,
    }
    write_json(MATERIAL_REPORT_PATH, report)
    log(
        "MATERIALS status=passed main_expr={} boss_expr={} fog=0 report={}".format(
            details[0]["expression_count"],
            details[1]["expression_count"],
            MATERIAL_REPORT_PATH,
        )
    )
    return materials, report


def load_verified_materials():
    report = load_json(MATERIAL_REPORT_PATH)
    if report.get("status") != "passed" or int(report.get("graph_version", -1)) != GRAPH_VERSION:
        raise RuntimeError("Verified StormPass Landscape material report is unavailable")
    details = {row["group"]: row for row in report.get("materials", [])}
    if set(details) != set(MATERIAL_PATHS):
        raise RuntimeError("StormPass Landscape material report inventory changed")
    materials = {}
    for group, path in MATERIAL_PATHS.items():
        material = unreal.EditorAssetLibrary.load_asset(path)
        if not material or material.get_class().get_name() != "Material":
            raise RuntimeError("StormPass Landscape material is missing: " + path)
        if int(unreal.MaterialEditingLibrary.get_num_material_expressions(material)) != int(
            details[group]["expression_count"]
        ):
            raise RuntimeError("StormPass Landscape material graph changed: " + group)
        actual_textures = {
            texture.get_path_name()
            for texture in unreal.MaterialEditingLibrary.get_material_used_textures(
                material
            )
            if texture
        }
        if actual_textures != set(details[group]["used_textures"]):
            raise RuntimeError("StormPass Landscape material textures changed: " + group)
        materials[group] = material
    return materials, report


def managed_label(record):
    return "{}{}_{}".format(
        MANAGED_LABEL_PREFIX,
        record["destination_group"],
        record["component_name"],
    )


def vector(value):
    return unreal.Vector(
        float(value["x"]), float(value["y"]), float(value["z"])
    )


def rotator(value):
    return unreal.Rotator(
        roll=float(value["roll"]),
        pitch=float(value["pitch"]),
        yaw=float(value["yaw"]),
    )


def set_actor_folder(actor, path):
    try:
        actor.set_folder_path(path)
    except Exception:
        actor.set_editor_property("folder_path", path)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create pre-Landscape StormPass map backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def close_enough(actual, expected):
    return abs(float(actual) - float(expected)) <= TRANSFORM_TOLERANCE


def actor_transform_matches(actor, transform):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    expected_location = transform["location_cm"]
    expected_rotation = transform["rotation_degrees"]
    expected_scale = transform["scale"]
    return (
        all(
            close_enough(actual, expected)
            for actual, expected in zip(
                (location.x, location.y, location.z),
                (
                    expected_location["x"],
                    expected_location["y"],
                    expected_location["z"],
                ),
            )
        )
        and all(
            close_enough(actual, expected)
            for actual, expected in zip(
                (rotation.pitch, rotation.yaw, rotation.roll),
                (
                    expected_rotation["pitch"],
                    expected_rotation["yaw"],
                    expected_rotation["roll"],
                ),
            )
        )
        and all(
            close_enough(actual, expected)
            for actual, expected in zip(
                (scale.x, scale.y, scale.z),
                (expected_scale["x"], expected_scale["y"], expected_scale["z"]),
            )
        )
    )


def place_components(grouped, materials):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_records = grouped["Main"] + grouped["Boss"]
    expected_labels = {managed_label(record) for record in all_records}
    existing = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    unexpected = sorted(set(existing) - expected_labels)
    if unexpected:
        raise RuntimeError("Unexpected managed Landscape actor: " + unexpected[0])

    created = 0
    reused = 0
    by_group = {
        "Main": {"created": 0, "reused": 0},
        "Boss": {"created": 0, "reused": 0},
    }
    for index, record in enumerate(all_records):
        group = record["destination_group"]
        mesh = mesh_helpers.component_mesh(record)
        if not mesh:
            raise RuntimeError("Landscape mesh is unresolved")
        material = materials[group]
        transform = record["root_transform"]
        label = managed_label(record)
        actor = existing.get(label)
        if actor:
            reused += 1
            by_group[group]["reused"] += 1
        else:
            actor = actor_subsystem.spawn_actor_from_object(
                mesh,
                vector(transform["location_cm"]),
                rotator(transform["rotation_degrees"]),
            )
            if not actor:
                raise RuntimeError("Failed to spawn Landscape component: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            existing[label] = actor
            created += 1
            by_group[group]["created"] += 1

        actor.set_actor_location(vector(transform["location_cm"]), False, False)
        actor.set_actor_rotation(rotator(transform["rotation_degrees"]), False)
        actor.set_actor_scale3d(vector(transform["scale"]))
        actor.set_actor_enable_collision(True)
        set_actor_folder(actor, "{}/{}".format(MANAGED_FOLDER_ROOT, group))
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Landscape actor lacks StaticMeshComponent: " + label)
        if component.get_editor_property("static_mesh") != mesh:
            component.set_static_mesh(mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        component.set_editor_property("cast_shadow", False)
        component.set_editor_property("reverse_culling", False)
        try:
            component.set_editor_property("visible", True)
            component.set_editor_property("hidden_in_game", False)
        except Exception:
            pass
        component.set_collision_profile_name("BlockAll")
        component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        component.set_material(0, material)
        if (index + 1) % 50 == 0:
            log("PLACED {}/{}".format(index + 1, len(all_records)))

    actors = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    if set(actors) != expected_labels:
        raise RuntimeError("Final StormPass Landscape actor inventory is incomplete")
    return actors, {
        "created_count": created,
        "reused_count": reused,
        "final_actor_count": len(actors),
        "by_group": by_group,
    }


def validate_components(grouped, materials, actors):
    failures = []
    group_counts = {"Main": 0, "Boss": 0}
    for record in grouped["Main"] + grouped["Boss"]:
        group = record["destination_group"]
        label = managed_label(record)
        actor = actors.get(label)
        issues = []
        if not actor:
            failures.append({"label": label, "issues": ["missing_actor"]})
            continue
        group_counts[group] += 1
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not actor_transform_matches(actor, record["root_transform"]):
            issues.append("transform")
        if not component:
            issues.append("missing_static_mesh_component")
        else:
            if component.get_editor_property("static_mesh") != mesh_helpers.component_mesh(
                record
            ):
                issues.append("mesh")
            if component.get_material(0) != materials[group]:
                issues.append("material")
            if component.get_editor_property("reverse_culling"):
                issues.append("reverse_culling")
            if component.get_editor_property("cast_shadow"):
                issues.append("cast_shadow")
            if (
                component.get_collision_enabled()
                != unreal.CollisionEnabled.QUERY_AND_PHYSICS
            ):
                issues.append("collision")
        if issues:
            failures.append({"label": label, "issues": issues})
    if group_counts != EXPECTED_COUNTS:
        failures.append(
            {"label": "group_inventory", "issues": [str(group_counts)]}
        )
    return failures, group_counts


def ensure_stormpass_map_loaded():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    current = world.get_path_name() if world else ""
    if current.startswith(MAP_PATH + "."):
        return False
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(
        MAP_PATH
    ):
        raise RuntimeError("Failed to load StormPass environment map")
    return True


def restore_map(rebuild_materials=True):
    if rebuild_materials:
        materials, material_report = build_materials()
    else:
        materials, material_report = load_verified_materials()
    grouped = records_by_group()
    map_loaded = ensure_stormpass_map_loaded()
    before = world_snapshot()
    assert_fog_zero(before, "before Landscape placement")
    backup_created = backup_map_once()
    actors, placement = place_components(grouped, materials)
    failures, group_counts = validate_components(grouped, materials, actors)
    if failures:
        raise RuntimeError(
            "StormPass Landscape placement validation failed: " + str(failures[0])
        )
    after = world_snapshot()
    assert_fog_zero(after, "after Landscape placement")
    if after["fog_actors"] != before["fog_actors"]:
        raise RuntimeError("Fog actor signature changed during Landscape placement")
    expected_actor_delta = placement["created_count"]
    if after["actor_count"] - before["actor_count"] != expected_actor_delta:
        raise RuntimeError("Unexpected actor-count delta during Landscape placement")
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save Landscape-restored StormPass map")
    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "map_loaded_by_script": map_loaded,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_component_count": EXPECTED_COMPONENT_COUNT,
        "source_component_metadata": COMPONENT_METADATA_PATH,
        "material_report": MATERIAL_REPORT_PATH,
        "material_assets": {
            group: material.get_path_name() for group, material in materials.items()
        },
        "placement": placement,
        "validated_actor_count": sum(group_counts.values()),
        "validated_by_group": group_counts,
        "validation_failure_count": 0,
        "collision": "BlockAll + QueryAndPhysics; meshes use ComplexAsSimple",
        "cast_shadow": False,
        "world_before": before,
        "world_after": after,
        "fog_policy": "deferred_until_final_pass",
        "fog_actor_count": after["fog_actor_count"],
        "material_build_status": material_report["status"],
    }
    write_json(RESTORATION_REPORT_PATH, report)
    log(
        "RESTORED actors={} created={} reused={} fog={} report={}".format(
            placement["final_actor_count"],
            placement["created_count"],
            placement["reused_count"],
            after["fog_actor_count"],
            RESTORATION_REPORT_PATH,
        )
    )
    return report


def audit_loaded_map():
    ensure_stormpass_map_loaded()
    (
        _material_source,
        _plans,
        _landscapes,
        _surface_assets,
        _weight_assets,
        _normal_assets,
    ) = load_canonical_sources()
    grouped = records_by_group()
    materials = {
        group: unreal.EditorAssetLibrary.load_asset(path)
        for group, path in MATERIAL_PATHS.items()
    }
    if not all(materials.values()):
        raise RuntimeError("StormPass Landscape material asset is missing")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    failures, group_counts = validate_components(grouped, materials, actors)
    snapshot = world_snapshot()
    assert_fog_zero(snapshot, "during Landscape reload audit")
    status = (
        "passed"
        if not failures
        and len(actors) == EXPECTED_COMPONENT_COUNT
        and group_counts == EXPECTED_COUNTS
        else "failed"
    )
    report = {
        "status": status,
        "operation": "landscape_map_reload_audit",
        "map_path": MAP_PATH,
        "managed_actor_count": len(actors),
        "validated_actor_count": sum(group_counts.values()),
        "validated_by_group": group_counts,
        "validation_failure_count": len(failures),
        "validation_failures": failures[:10],
        "material_assets": {
            group: material.get_path_name() for group, material in materials.items()
        },
        "world": snapshot,
        "fog_policy": "deferred_until_final_pass",
    }
    write_json(RELOAD_REPORT_PATH, report)
    if status != "passed":
        raise RuntimeError("StormPass Landscape reload audit failed")
    log(
        "RELOAD_AUDIT actors={} main={} boss={} fog={} status={}".format(
            len(actors),
            group_counts["Main"],
            group_counts["Boss"],
            snapshot["fog_actor_count"],
            status,
        )
    )
    return report


if __name__ == "__main__":
    try:
        restore_map()
    except Exception as exception:
        write_json(
            RESTORATION_REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
                "fog_policy": "deferred_until_final_pass",
            },
        )
        unreal.log_error(
            "KHAZAN_STORMPASS_LANDSCAPE_RESTORE: " + str(exception)
        )
        raise
