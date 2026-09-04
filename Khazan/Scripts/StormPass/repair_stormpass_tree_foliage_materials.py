"""Repair StormPass tree foliage materials reconstructed with false emissive.

The generic USD preview fallback maps every source ``Tex_E`` parameter to the
emissive input.  The affected StormPass tree instances are source-authored as
masked, two-sided foliage and their inherited source metadata explicitly says
``HasTopEmissive=false``.  This script keeps the restored source textures, but
reparents only those instances to a stock-UE Two Sided Foliage material where
``Tex_E.R`` is used as a subsurface mask instead of emissive color.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT, "Saved", "ImportReports", "StormPass_TreeFoliageMaterial_Repair.json"
)
RAW_SOURCE_ROOT = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "Exports",
    "BBQ",
    "Content",
    "Art",
    "World",
    "World_Material",
    "Prop",
    "Material",
)
RESOLVED_SOURCE_ROOT = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "BBQ",
    "Content",
    "Art",
    "World",
    "World_Material",
    "Prop",
    "Material",
)
INSTANCE_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials/"
    "ActorOverrides/Materials"
)
REPAIR_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Trees"
)
PARENT_PATH = REPAIR_ROOT + "/M_SP_SourceTreeFoliage_V2"
BACKUP_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Backups/"
    "PreTreeFoliageRepair_20260903/Materials"
)

MATERIAL_NAMES = (
    "WM_COM_SmallTree_Base_001_02",
    "WM_COM_SmallTree_Base_002_02",
    "WM_COM_SmallTree_Base_003_02",
    "WM_COM_SmallTree_Base_004_02",
    "WM_COM_SmallTree_Base_005_03",
    "WM_COM_ThickTree_Dry_002",
    "WM_COM_ThinTree_Dry_002",
    "WM_COM_ThinTree_Dry_003",
    "WM_COM_ThinTree_Dry_004",
)
EXPECTED_SLOT_COUNTS = {
    "WM_COM_SmallTree_Base_001_02": 139,
    "WM_COM_SmallTree_Base_002_02": 115,
    "WM_COM_SmallTree_Base_003_02": 172,
    "WM_COM_SmallTree_Base_004_02": 75,
    "WM_COM_SmallTree_Base_005_03": 63,
    "WM_COM_ThickTree_Dry_002": 29,
    "WM_COM_ThinTree_Dry_002": 71,
    "WM_COM_ThinTree_Dry_003": 17,
    "WM_COM_ThinTree_Dry_004": 52,
}
EXPECTED_SLOT_TOTAL = 733
EXPECTED_ACTOR_TOTAL = 14408

TEXTURE_PARAMETERS = (
    "BaseColorTexture",
    "OpacityTexture",
    "NormalTexture",
    "RoughnessTexture",
    "MetallicTexture",
    # The legacy parameter name is retained so the exact imported Tex_E
    # override survives reparenting.  The new parent uses only its R channel
    # as a subsurface mask and has no emissive connection.
    "EmissiveColorTexture",
)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(value):
    return value.get_path_name() if value else None


def normalized_asset_path(value):
    return str(value).rsplit(".", 1)[0] if value else None


def source_object_name(value):
    if not isinstance(value, dict):
        return None
    raw = str(value.get("ObjectName") or "")
    match = re.search(r"'([^']+)'", raw)
    return match.group(1) if match else None


def parameter_map(items, value_key="ParameterValue"):
    result = {}
    for item in items or []:
        info = item.get("ParameterInfo") or {}
        name = info.get("Name")
        if name:
            result[str(name)] = item.get(value_key)
    return result


def color_tuple(value):
    if not isinstance(value, dict):
        return None
    return tuple(float(value.get(key, fallback)) for key, fallback in zip("RGBA", (1, 1, 1, 1)))


def material_source_record(name):
    raw_path = os.path.join(RAW_SOURCE_ROOT, name + ".json")
    raw_exports = load_json(raw_path)
    source = next(
        (
            item
            for item in raw_exports
            if item.get("Type") == "MaterialInstanceConstant" and item.get("Name") == name
        ),
        None,
    )
    if not source:
        raise RuntimeError("Missing source material export: " + name)
    properties = source.get("Properties") or {}
    textures = parameter_map(properties.get("TextureParameterValues"))
    scalars = parameter_map(properties.get("ScalarParameterValues"))
    vectors = parameter_map(properties.get("VectorParameterValues"))
    switches = {
        str((item.get("ParameterInfo") or {}).get("Name")): bool(item.get("Value"))
        for item in ((properties.get("StaticParameters") or {}).get("StaticSwitchParameters") or [])
        if (item.get("ParameterInfo") or {}).get("Name")
    }
    parent_name = source_object_name(properties.get("Parent"))
    resolved_path = (
        os.path.join(RESOLVED_SOURCE_ROOT, parent_name + ".json") if parent_name else None
    )
    resolved = load_json(resolved_path) if resolved_path and os.path.isfile(resolved_path) else {}
    resolved_parameters = resolved.get("Parameters") or {}
    resolved_scalars = resolved_parameters.get("Scalars") or {}
    resolved_colors = resolved_parameters.get("Colors") or {}
    resolved_switches = resolved_parameters.get("Switches") or {}
    overrides = properties.get("BasePropertyOverrides") or {}

    diffuse_intensity = scalars.get("Diffuse_Intensity")
    if diffuse_intensity is None:
        diffuse_intensity = resolved_scalars.get("Diffuse_Intensity", 1.0)
    sss_intensity = scalars.get("SSS_Mask_Intensity")
    if sss_intensity is None:
        sss_intensity = resolved_scalars.get("SSS_Mask_Intensity", 1.0)
    sss_color = color_tuple(vectors.get("SSS_DiffuseColor"))
    if sss_color is None:
        sss_color = color_tuple(resolved_colors.get("SSS_DiffuseColor"))
    if sss_color is None:
        sss_color = (1.0, 1.0, 1.0, 1.0)

    texture_names = {}
    for parameter in ("Tex_D", "Tex_S", "Tex_N", "Tex_E"):
        texture_names[parameter] = source_object_name(textures.get(parameter))
    required_texture_failures = [key for key, value in texture_names.items() if not value]
    evidence_failures = []
    if required_texture_failures:
        evidence_failures.append("missing source textures: " + ",".join(required_texture_failures))
    if overrides.get("BlendMode") != "BLEND_Masked":
        evidence_failures.append("source blend is not Masked")
    if overrides.get("TwoSided") is not True:
        evidence_failures.append("source TwoSided is not true")
    if abs(float(overrides.get("OpacityMaskClipValue", -1.0)) - 0.3333) > 0.0001:
        evidence_failures.append("source opacity clip differs from 0.3333")
    if resolved_parameters.get("HasTopEmissive") is not False:
        evidence_failures.append("parent HasTopEmissive is not explicitly false")
    if evidence_failures:
        raise RuntimeError(name + " source evidence failed: " + "; ".join(evidence_failures))

    return {
        "name": name,
        "raw_json": raw_path,
        "parent_name": parent_name,
        "resolved_parent_json": resolved_path,
        "source_textures": texture_names,
        "source_overrides": overrides,
        "source_shading_model": overrides.get("ShadingModel"),
        "source_has_top_emissive": resolved_parameters.get("HasTopEmissive"),
        "source_use_tree_leaf": switches.get(
            "UseTreeLeaf", resolved_switches.get("UseTreeLeaf")
        ),
        "source_use_sss": switches.get("UseSSS", resolved_switches.get("UseSSS")),
        "effective_parameters": {
            "Diffuse_Intensity": float(diffuse_intensity),
            "SSS_Mask_Intensity": float(sss_intensity),
            "SSS_DiffuseColor": list(sss_color),
        },
    }


def transform_signature(actors):
    records = []
    for actor in actors:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        records.append(
            (
                actor.get_path_name(),
                actor.get_actor_label(),
                actor.get_class().get_name(),
                round(location.x, 6),
                round(location.y, 6),
                round(location.z, 6),
                round(rotation.pitch, 6),
                round(rotation.yaw, 6),
                round(rotation.roll, 6),
                round(scale.x, 6),
                round(scale.y, 6),
                round(scale.z, 6),
            )
        )
    records.sort()
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def load_level():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load StormPass environment map")
    return level_subsystem


def material_path(name):
    return INSTANCE_ROOT + "/MI_" + name


def texture_value(material, parameter):
    try:
        value = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            material, parameter
        )
        return value
    except Exception:
        return None


def scalar_value(material, parameter):
    try:
        return float(
            unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                material, parameter
            )
        )
    except Exception:
        return None


def capture_material(material):
    parent = None
    try:
        parent = material.get_editor_property("parent")
    except Exception:
        pass
    textures = {name: texture_value(material, name) for name in TEXTURE_PARAMETERS}
    return {
        "asset": normalized_asset_path(object_path(material)),
        "parent": object_path(parent),
        "use_emissive": scalar_value(material, "UseEmissiveColorTexture"),
        "textures": {key: object_path(value) for key, value in textures.items()},
        "texture_objects": textures,
    }


def slot_inventory(actor_subsystem):
    expected_paths = {material_path(name): name for name in MATERIAL_NAMES}
    counts = {name: 0 for name in MATERIAL_NAMES}
    actors = {name: set() for name in MATERIAL_NAMES}
    meshes = {name: set() for name in MATERIAL_NAMES}
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            for slot_index in range(component.get_num_materials()):
                current = normalized_asset_path(object_path(component.get_material(slot_index)))
                name = expected_paths.get(current)
                if not name:
                    continue
                counts[name] += 1
                actors[name].add(actor.get_actor_label())
                if mesh:
                    meshes[name].add(mesh.get_name())
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "actor_counts": {name: len(values) for name, values in actors.items()},
        "meshes": {name: sorted(values) for name, values in meshes.items()},
    }


def expression(material, expression_class, x, y):
    value = unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )
    if not value:
        raise RuntimeError("Failed to create " + expression_class.__name__)
    return value


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


def connect_property(source, output_name, material_property):
    if not unreal.MaterialEditingLibrary.connect_material_property(
        source, output_name, material_property
    ):
        raise RuntimeError(
            "Material property connection failed: {} -> {}".format(
                source.get_class().get_name(), material_property
            )
        )


def texture_parameter(material, name, texture, sampler_type, x, y):
    node = expression(material, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("texture", texture)
    node.set_editor_property("sampler_type", sampler_type)
    return node


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default))
    return node


def vector_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", unreal.LinearColor(*default))
    return node


def build_foliage_parent():
    unreal.EditorAssetLibrary.make_directory(REPAIR_ROOT)
    material = unreal.EditorAssetLibrary.load_asset(PARENT_PATH)
    created = material is None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_SP_SourceTreeFoliage_V2",
            REPAIR_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create StormPass foliage repair parent")

    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE
    )
    material.set_editor_property("two_sided", True)
    material.set_editor_property("dithered_lod_transition", True)
    material.set_editor_property("opacity_mask_clip_value", 0.3333)

    white = unreal.EditorAssetLibrary.load_asset(
        "/Engine/EditorLandscapeResources/WhiteSquareTexture"
    )
    default_normal = unreal.EditorAssetLibrary.load_asset(
        "/Engine/EngineMaterials/DefaultNormal"
    )
    default_surface = unreal.EditorAssetLibrary.load_asset(
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials/"
        "Textures/T_WT_COM_ThinTree_Base_001_02_S"
    )
    if not white or not default_normal or not default_surface:
        raise RuntimeError("Required engine fallback textures are unavailable")

    base = texture_parameter(
        material,
        "BaseColorTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -1250,
        -600,
    )
    diffuse_intensity = scalar_parameter(
        material, "Diffuse_Intensity", 1.0, -1250, -390
    )
    base_scaled = expression(material, unreal.MaterialExpressionMultiply, -930, -540)
    connect(base, "RGB", base_scaled, "A")
    connect(diffuse_intensity, "", base_scaled, "B")
    connect_property(base_scaled, "", unreal.MaterialProperty.MP_BASE_COLOR)

    opacity = texture_parameter(
        material,
        "OpacityTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -920,
        -830,
    )
    connect_property(opacity, "A", unreal.MaterialProperty.MP_OPACITY_MASK)

    normal = texture_parameter(
        material,
        "NormalTexture",
        default_normal,
        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        -920,
        -110,
    )
    connect_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)

    surface = texture_parameter(
        material,
        "RoughnessTexture",
        default_surface,
        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
        -620,
        130,
    )
    roughness_scale = scalar_parameter(
        material, "RoughnessMultiplier", 1.0, -620, 350
    )
    roughness = expression(material, unreal.MaterialExpressionMultiply, -330, 170)
    # Khazan's packed *_S convention is AO=R, Roughness=G, Metallic=B.
    # Foliage is non-metallic, so B is intentionally not applied here.
    connect(surface, "G", roughness, "A")
    connect(roughness_scale, "", roughness, "B")
    connect_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    connect_property(surface, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

    metallic = scalar_parameter(material, "Metallic", 0.0, -330, 430)
    specular = scalar_parameter(material, "Specular", 0.25, -330, 550)
    connect_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
    connect_property(specular, "", unreal.MaterialProperty.MP_SPECULAR)

    # FModel's generic USD translation treated Tex_E as RGB emissive.  The
    # source material says there is no top emissive and exposes foliage SSS
    # controls, so only the R channel is consumed as a transmission mask.
    source_sss_mask = texture_parameter(
        material,
        "EmissiveColorTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -620,
        -380,
    )
    sss_intensity = scalar_parameter(
        material, "SSS_Mask_Intensity", 1.0, -620, -170
    )
    mask_scaled = expression(material, unreal.MaterialExpressionMultiply, -330, -330)
    connect(source_sss_mask, "R", mask_scaled, "A")
    connect(sss_intensity, "", mask_scaled, "B")
    sss_color = vector_parameter(
        material, "SSS_DiffuseColor", (1.0, 1.0, 1.0, 1.0), -330, -110
    )
    tinted_base = expression(material, unreal.MaterialExpressionMultiply, -40, -410)
    connect(base_scaled, "", tinted_base, "A")
    connect(sss_color, "RGB", tinted_base, "B")
    subsurface = expression(material, unreal.MaterialExpressionMultiply, 220, -330)
    connect(tinted_base, "", subsurface, "A")
    connect(mask_scaled, "", subsurface, "B")
    connect_property(subsurface, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanSourcePolicy", "Masked TwoSided foliage; opacity clip 0.3333"
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanTexEPolicy", "Tex_E.R feeds subsurface mask; emissive disconnected"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    emissive_node = unreal.MaterialEditingLibrary.get_material_property_input_node(
        material, unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    if emissive_node:
        raise RuntimeError("Foliage repair parent unexpectedly has an emissive input")
    return material, created


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def set_texture(material, name, value):
    if not value:
        raise RuntimeError(material.get_name() + " lacks " + name)
    for _ in range(2):
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
            material, name, value
        )
        current = texture_value(material, name)
        if object_path(current) == object_path(value):
            return
        unreal.MaterialEditingLibrary.update_material_instance(material)
    raise RuntimeError(material.get_name() + " failed texture parameter " + name)


def set_scalar(material, name, value):
    expected = float(value)
    for _ in range(2):
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            material, name, expected
        )
        current = scalar_value(material, name)
        if current is not None and abs(current - expected) <= 0.00001:
            return
        unreal.MaterialEditingLibrary.update_material_instance(material)
    raise RuntimeError(material.get_name() + " failed scalar parameter " + name)


def set_vector(material, name, value):
    expected = unreal.LinearColor(*value)
    for _ in range(2):
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
            material, name, expected
        )
        try:
            current = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
                material, name
            )
        except Exception:
            current = None
        if current and all(
            abs(float(left) - float(right)) <= 0.00001
            for left, right in zip(
                (current.r, current.g, current.b, current.a),
                (expected.r, expected.g, expected.b, expected.a),
            )
        ):
            return
        unreal.MaterialEditingLibrary.update_material_instance(material)
    raise RuntimeError(material.get_name() + " failed vector parameter " + name)


def backup_materials(materials):
    unreal.EditorAssetLibrary.make_directory(BACKUP_ROOT)
    results = []
    for name, material in materials.items():
        source_path = material_path(name)
        backup_path = BACKUP_ROOT + "/MI_" + name + "_PreTreeFoliageRepair"
        created = False
        if not unreal.EditorAssetLibrary.does_asset_exist(backup_path):
            if not unreal.EditorAssetLibrary.duplicate_asset(source_path, backup_path):
                raise RuntimeError("Failed to back up material " + source_path)
            created = True
        backup = unreal.EditorAssetLibrary.load_asset(backup_path)
        if not backup:
            raise RuntimeError("Material backup did not load: " + backup_path)
        unreal.EditorAssetLibrary.save_loaded_asset(backup, only_if_is_dirty=False)
        results.append(
            {"source": source_path, "backup": object_path(backup), "created": created}
        )
    return results


def apply_material_policy(material, parent, capture, source_record):
    material.modify()
    unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
    # A newly compiled parent may not expose its parameter cache to an MI until
    # the instance has been refreshed once.  Refresh before applying overrides
    # and validate every write by readback below.
    unreal.MaterialEditingLibrary.update_material_instance(material)
    for parameter, texture in capture["texture_objects"].items():
        # MetallicTexture is intentionally not sampled by the repaired parent;
        # it is retained in the instance for provenance and reversibility.
        if parameter in set(TEXTURE_PARAMETERS) - {"MetallicTexture"}:
            set_texture(material, parameter, texture)
    effective = source_record["effective_parameters"]
    set_scalar(material, "Diffuse_Intensity", effective["Diffuse_Intensity"])
    set_scalar(material, "SSS_Mask_Intensity", effective["SSS_Mask_Intensity"])
    set_scalar(material, "RoughnessMultiplier", 1.0)
    set_scalar(material, "Metallic", 0.0)
    set_scalar(material, "Specular", 0.25)
    set_vector(material, "SSS_DiffuseColor", effective["SSS_DiffuseColor"])

    overrides = material.get_editor_property("base_property_overrides")
    required = (
        ("override_two_sided", True),
        ("two_sided", True),
        ("override_blend_mode", True),
        ("blend_mode", unreal.BlendMode.BLEND_MASKED),
        ("override_opacity_mask_clip_value", True),
        ("opacity_mask_clip_value", 0.3333),
        ("override_dithered_lod_transition", True),
        ("dithered_lod_transition", True),
        ("override_shading_model", True),
        ("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE),
    )
    failed = [name for name, value in required if not set_struct_property(overrides, name, value)]
    if failed:
        raise RuntimeError(material.get_name() + " failed base overrides: " + ",".join(failed))
    material.set_editor_property("base_property_overrides", overrides)
    unreal.MaterialEditingLibrary.update_material_instance(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material, "KhazanTreeFoliageRepair", "Source HasTopEmissive=false; Tex_E.R used for SSS"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)


def validation_record(material):
    parent = material.get_editor_property("parent")
    parameter_names = {
        str(value) for value in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)
    }
    textures = {
        name: object_path(texture_value(material, name)) for name in TEXTURE_PARAMETERS
    }
    overrides = material.get_editor_property("base_property_overrides")
    return {
        "asset": object_path(material),
        "parent": object_path(parent),
        "has_use_emissive_parameter": "UseEmissiveColorTexture" in parameter_names,
        "textures": textures,
        "diffuse_intensity": scalar_value(material, "Diffuse_Intensity"),
        "sss_mask_intensity": scalar_value(material, "SSS_Mask_Intensity"),
        "two_sided_override": bool(overrides.get_editor_property("two_sided")),
        "blend_mode_override": str(overrides.get_editor_property("blend_mode")),
        "shading_model_override": str(overrides.get_editor_property("shading_model")),
        "opacity_clip_override": float(
            overrides.get_editor_property("opacity_mask_clip_value")
        ),
    }


def main(apply_changes=False):
    level_subsystem = load_level()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    transform_before = transform_signature(actors_before)
    if transform_before["count"] != EXPECTED_ACTOR_TOTAL:
        raise RuntimeError(
            "Unexpected StormPass actor count: {} != {}".format(
                transform_before["count"], EXPECTED_ACTOR_TOTAL
            )
        )

    source_records = {name: material_source_record(name) for name in MATERIAL_NAMES}
    materials = {}
    captures = {}
    for name in MATERIAL_NAMES:
        material = unreal.EditorAssetLibrary.load_asset(material_path(name))
        if not material or material.get_class().get_name() != "MaterialInstanceConstant":
            raise RuntimeError("Missing reconstructed material instance: " + name)
        materials[name] = material
        captures[name] = capture_material(material)

    slots_before = slot_inventory(actor_subsystem)
    if slots_before["total"] != EXPECTED_SLOT_TOTAL:
        raise RuntimeError(
            "Unexpected affected slot total: {} != {}".format(
                slots_before["total"], EXPECTED_SLOT_TOTAL
            )
        )
    if slots_before["counts"] != EXPECTED_SLOT_COUNTS:
        raise RuntimeError("Affected material slot distribution changed")

    backups = []
    parent = unreal.EditorAssetLibrary.load_asset(PARENT_PATH)
    parent_created = False
    if apply_changes:
        backups = backup_materials(materials)
        parent, parent_created = build_foliage_parent()
        for name in MATERIAL_NAMES:
            apply_material_policy(materials[name], parent, captures[name], source_records[name])
        unreal.EditorAssetLibrary.save_directory(
            REPAIR_ROOT, only_if_is_dirty=False, recursive=True
        )
        unreal.EditorAssetLibrary.save_directory(
            INSTANCE_ROOT, only_if_is_dirty=False, recursive=True
        )
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save StormPass after foliage material repair")

    slots_after = slot_inventory(actor_subsystem)
    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    transform_after = transform_signature(actors_after)
    if transform_after != transform_before:
        raise RuntimeError("Actor transforms changed during foliage material repair")
    if slots_after != slots_before:
        raise RuntimeError("Tree material slot bindings changed during in-place repair")

    validation = {name: validation_record(materials[name]) for name in MATERIAL_NAMES}
    validation_failures = []
    if apply_changes:
        for name, item in validation.items():
            if normalized_asset_path(item["parent"]) != PARENT_PATH:
                validation_failures.append(name + ": wrong parent")
            if item["has_use_emissive_parameter"]:
                validation_failures.append(name + ": generic emissive switch remains")
            if any(not value for key, value in item["textures"].items() if key != "MetallicTexture"):
                validation_failures.append(name + ": missing texture override")
        emissive_node = unreal.MaterialEditingLibrary.get_material_property_input_node(
            parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR
        )
        if emissive_node:
            validation_failures.append("parent emissive input is connected")
    if validation_failures:
        raise RuntimeError("; ".join(validation_failures))

    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "decision": (
            "Nine StormPass tree leaf materials are source Masked/TwoSided and inherit "
            "HasTopEmissive=false.  Their Tex_E.R channel is restored as a foliage "
            "subsurface mask; no material emissive input is connected."
        ),
        "source_records": source_records,
        "counts": {
            "material": len(MATERIAL_NAMES),
            "affected_slot": slots_before["total"],
            "actor": transform_before["count"],
        },
        "slot_inventory": slots_before,
        "material_before": {
            name: {key: value for key, value in capture.items() if key != "texture_objects"}
            for name, capture in captures.items()
        },
        "backups": backups,
        "repair_parent": {
            "asset": object_path(parent),
            "created": parent_created,
            "blend": "BLEND_Masked",
            "shading_model": "MSM_TwoSidedFoliage",
            "two_sided": True,
            "opacity_mask_clip": 0.3333,
            "emissive_connected": False,
            "tex_e_usage": "R channel multiplied into source-tinted subsurface color",
            "tex_s_usage": "R=ambient occlusion, G=roughness, foliage metallic=0",
        },
        "material_after": validation,
        "transform_before": transform_before,
        "transform_after": transform_after,
        "validation_failures": validation_failures,
    }
    write_json(REPORT_PATH, report)
    print(
        "KHAZAN_STORMPASS_TREE_FOLIAGE: status={} materials={} slots={} actors={} transform_sha={}".format(
            report["status"],
            report["counts"]["material"],
            report["counts"]["affected_slot"],
            report["counts"]["actor"],
            transform_after["sha256"],
        )
    )
    return report


if __name__ == "__main__":
    try:
        main(False)
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
