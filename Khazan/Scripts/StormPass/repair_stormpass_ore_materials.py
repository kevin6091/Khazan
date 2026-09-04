"""Restore the four StormPass white-ore materials from FModel hierarchy data.

The generic USD preview parent displays the yellow ``Tex_E`` RGB directly.
Source metadata instead routes the ore family through ``WM_BBQProp_Ore`` and a
blue-grey ``GlowColor`` inherited from ``WM_COM_Ore_White_002``.  This pass
keeps every extracted texture and binding, restores the source masked surface
channels, and applies the inherited glow controls to a dedicated UE5 parent.
"""

from __future__ import annotations

import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT, "Saved", "ImportReports", "StormPass_OreMaterial_Repair.json"
)
TREE_HELPER_PATH = os.path.join(
    SCRIPT_DIR, "repair_stormpass_tree_foliage_materials.py"
)
SOURCE_ROOT = os.path.join(
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
INSTANCE_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials/"
    "ActorOverrides/Materials"
)
REPAIR_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Ore"
)
PARENT_PATH = REPAIR_ROOT + "/M_SP_SourceOre_V2"
BACKUP_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Backups/"
    "PreOreMaterialRepair_20260904/Materials"
)
MATERIAL_COUNTS = {
    "WM_COM_Ore_White_001": 218,
    "WM_COM_Ore_White_002": 218,
    "WM_COM_Ore_White_003": 261,
    "WM_COM_Ore_White_003_IceLOD": 163,
}
EXPECTED_SLOT_TOTAL = sum(MATERIAL_COUNTS.values())
EXPECTED_ACTOR_TOTAL = 14408


def load_tree_helper():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_ore_tree_helpers", TREE_HELPER_PATH
    )
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load material helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def material_path(name):
    return INSTANCE_ROOT + "/MI_" + name


def source_export(name):
    candidates = [
        os.path.join(SOURCE_ROOT, name + ".json"),
        os.path.join(SOURCE_ROOT, "Base", name + ".json"),
    ]
    path = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
    if not path:
        raise RuntimeError("Missing FModel material JSON: " + name)
    exports = load_json(path)
    material = next(
        (
            row
            for row in exports
            if row.get("Type") == "MaterialInstanceConstant"
            and row.get("Name") == name
        ),
        None,
    )
    if not material:
        raise RuntimeError("Missing FModel MIC export: " + name)
    return path, material


def source_parent_name(material):
    path = ((material.get("Properties") or {}).get("Parent") or {}).get("ObjectPath")
    return str(path).rsplit("/", 1)[-1].split(".", 1)[0] if path else None


def source_parameters(name, seen=None):
    seen = set() if seen is None else set(seen)
    if name in seen:
        raise RuntimeError("Source material hierarchy cycle: " + name)
    seen.add(name)
    path, material = source_export(name)
    parent_name = source_parent_name(material)
    if name == "WM_BBQProp_Ore":
        inherited = {"scalars": {}, "vectors": {}, "chain": [], "json": []}
    elif parent_name and (
        parent_name.startswith("WM_COM_Ore_White_")
        or parent_name == "WM_BBQProp_Ore"
    ):
        inherited = source_parameters(parent_name, seen)
    else:
        raise RuntimeError(name + " does not resolve to WM_BBQProp_Ore")

    properties = material.get("Properties") or {}
    scalars = dict(inherited["scalars"])
    vectors = dict(inherited["vectors"])
    for row in properties.get("ScalarParameterValues", []):
        parameter = (row.get("ParameterInfo") or {}).get("Name")
        if parameter:
            scalars[parameter] = float(row.get("ParameterValue", 0.0))
    for row in properties.get("VectorParameterValues", []):
        parameter = (row.get("ParameterInfo") or {}).get("Name")
        value = row.get("ParameterValue") or {}
        if parameter:
            vectors[parameter] = [
                float(value.get("R", 0.0)),
                float(value.get("G", 0.0)),
                float(value.get("B", 0.0)),
                float(value.get("A", 1.0)),
            ]
    return {
        "scalars": scalars,
        "vectors": vectors,
        "chain": inherited["chain"] + [name],
        "json": inherited["json"] + [path],
    }


def resolved_source_record(name):
    resolved = source_parameters(name)
    if not resolved["chain"] or resolved["chain"][0] != "WM_BBQProp_Ore":
        raise RuntimeError(name + " source chain does not start at WM_BBQProp_Ore")
    required_scalars = {
        "MasterOpacity": 1.0,
        "TexBrightness": 1.25,
        "BaseEmissiveAmount": 2.5,
    }
    effective_scalars = {
        parameter: float(resolved["scalars"].get(parameter, default))
        for parameter, default in required_scalars.items()
    }
    glow = resolved["vectors"].get("GlowColor")
    if not glow:
        raise RuntimeError(name + " lacks inherited GlowColor")
    return {
        "chain": resolved["chain"],
        "source_json_chain": resolved["json"],
        "effective_scalars": effective_scalars,
        "glow_color": glow,
        "ore_main_noise_uv": resolved["scalars"].get("Ore_MainNoise_UV"),
        "ore_sub_noise_uv": resolved["scalars"].get("Ore_SubNoise_UV"),
    }


def slot_inventory(actor_subsystem, helper):
    expected = {material_path(name): name for name in MATERIAL_COUNTS}
    counts = {name: 0 for name in MATERIAL_COUNTS}
    actors = {name: set() for name in MATERIAL_COUNTS}
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(int(component.get_num_materials())):
                current = helper.normalized_asset_path(
                    helper.object_path(component.get_material(slot))
                )
                name = expected.get(current)
                if name:
                    counts[name] += 1
                    actors[name].add(actor.get_actor_label())
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "actor_counts": {name: len(values) for name, values in actors.items()},
    }


def build_ore_parent(helper):
    unreal.EditorAssetLibrary.make_directory(REPAIR_ROOT)
    material = unreal.EditorAssetLibrary.load_asset(PARENT_PATH)
    created = material is None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_SP_SourceOre_V2",
            REPAIR_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create StormPass ore parent")
    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT
    )
    material.set_editor_property("two_sided", False)
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
        "Textures/T_WT_COM_Ore_Base_001_S"
    )
    if not white or not default_normal or not default_surface:
        raise RuntimeError("Required engine textures are unavailable")

    base = helper.texture_parameter(
        material,
        "BaseColorTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -1250,
        -600,
    )
    brightness = helper.scalar_parameter(material, "TexBrightness", 1.25, -1250, -390)
    base_scaled = helper.expression(material, unreal.MaterialExpressionMultiply, -930, -540)
    helper.connect(base, "RGB", base_scaled, "A")
    helper.connect(brightness, "", base_scaled, "B")
    helper.connect_property(base_scaled, "", unreal.MaterialProperty.MP_BASE_COLOR)

    opacity_texture = helper.texture_parameter(
        material,
        "OpacityTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -1250,
        -830,
    )
    master_opacity = helper.scalar_parameter(material, "MasterOpacity", 1.0, -930, -830)
    opacity = helper.expression(material, unreal.MaterialExpressionMultiply, -650, -790)
    helper.connect(opacity_texture, "A", opacity, "A")
    helper.connect(master_opacity, "", opacity, "B")
    helper.connect_property(opacity, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    normal = helper.texture_parameter(
        material,
        "NormalTexture",
        default_normal,
        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        -930,
        -190,
    )
    helper.connect_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)

    roughness_texture = helper.texture_parameter(
        material,
        "RoughnessTexture",
        default_surface,
        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
        -650,
        120,
    )
    roughness_scale = helper.scalar_parameter(
        material, "RoughnessMultiplier", 1.0, -650, 330
    )
    roughness = helper.expression(material, unreal.MaterialExpressionMultiply, -350, 150)
    helper.connect(roughness_texture, "G", roughness, "A")
    helper.connect(roughness_scale, "", roughness, "B")
    helper.connect_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    helper.connect_property(
        roughness_texture, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION
    )

    metallic_texture = helper.texture_parameter(
        material,
        "MetallicTexture",
        default_surface,
        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
        -650,
        520,
    )
    metallic_scale = helper.scalar_parameter(
        material, "MetallicMultiplier", 1.0, -650, 720
    )
    metallic = helper.expression(material, unreal.MaterialExpressionMultiply, -350, 550)
    helper.connect(metallic_texture, "B", metallic, "A")
    helper.connect(metallic_scale, "", metallic, "B")
    helper.connect_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
    specular = helper.scalar_parameter(material, "Specular", 0.5, -350, 760)
    helper.connect_property(specular, "", unreal.MaterialProperty.MP_SPECULAR)

    emissive_texture = helper.texture_parameter(
        material,
        "EmissiveColorTexture",
        white,
        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
        -650,
        -520,
    )
    glow_color = helper.vector_parameter(
        material,
        "GlowColor",
        (0.12066, 0.162065, 0.166667, 1.0),
        -650,
        -330,
    )
    tinted_glow = helper.expression(material, unreal.MaterialExpressionMultiply, -350, -430)
    helper.connect(emissive_texture, "R", tinted_glow, "A")
    helper.connect(glow_color, "RGB", tinted_glow, "B")
    emissive_amount = helper.scalar_parameter(
        material, "BaseEmissiveAmount", 2.5, -350, -250
    )
    emissive = helper.expression(material, unreal.MaterialExpressionMultiply, -50, -390)
    helper.connect(tinted_glow, "", emissive, "A")
    helper.connect(emissive_amount, "", emissive, "B")
    helper.connect_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material,
        "KhazanSourcePolicy",
        "WM_BBQProp_Ore Masked; AO=R Roughness=G Metallic=B",
    )
    unreal.EditorAssetLibrary.set_metadata_tag(
        material,
        "KhazanTexEPolicy",
        "Tex_E.R masks inherited GlowColor and BaseEmissiveAmount",
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    if not unreal.MaterialEditingLibrary.get_material_property_input_node(
        material, unreal.MaterialProperty.MP_EMISSIVE_COLOR
    ):
        raise RuntimeError("Ore parent emissive input is missing")
    return material, created


def backup_materials(materials, helper):
    unreal.EditorAssetLibrary.make_directory(BACKUP_ROOT)
    rows = []
    for name, material in materials.items():
        backup_path = BACKUP_ROOT + "/MI_" + name + "_PreOreMaterialRepair"
        created = False
        if not unreal.EditorAssetLibrary.does_asset_exist(backup_path):
            if not unreal.EditorAssetLibrary.duplicate_asset(material_path(name), backup_path):
                raise RuntimeError("Failed to back up " + name)
            created = True
        backup = unreal.EditorAssetLibrary.load_asset(backup_path)
        unreal.EditorAssetLibrary.save_loaded_asset(backup, only_if_is_dirty=False)
        rows.append(
            {
                "source": material.get_path_name(),
                "backup": helper.object_path(backup),
                "created": created,
            }
        )
    return rows


def apply_ore_instance(material, parent, capture, source, helper):
    material.modify()
    unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
    unreal.MaterialEditingLibrary.update_material_instance(material)
    for parameter in (
        "BaseColorTexture",
        "OpacityTexture",
        "NormalTexture",
        "RoughnessTexture",
        "MetallicTexture",
        "EmissiveColorTexture",
    ):
        helper.set_texture(material, parameter, capture["texture_objects"][parameter])
    helper.set_scalar(
        material, "MasterOpacity", source["effective_scalars"]["MasterOpacity"]
    )
    helper.set_scalar(
        material, "TexBrightness", source["effective_scalars"]["TexBrightness"]
    )
    helper.set_scalar(
        material,
        "BaseEmissiveAmount",
        source["effective_scalars"]["BaseEmissiveAmount"],
    )
    helper.set_scalar(material, "RoughnessMultiplier", 1.0)
    helper.set_scalar(material, "MetallicMultiplier", 1.0)
    helper.set_scalar(material, "Specular", 0.5)
    helper.set_vector(material, "GlowColor", source["glow_color"])

    overrides = material.get_editor_property("base_property_overrides")
    required = (
        ("override_two_sided", True),
        ("two_sided", False),
        ("override_blend_mode", True),
        ("blend_mode", unreal.BlendMode.BLEND_MASKED),
        ("override_opacity_mask_clip_value", True),
        ("opacity_mask_clip_value", 0.3333),
        ("override_dithered_lod_transition", True),
        ("dithered_lod_transition", True),
        ("override_shading_model", True),
        ("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT),
    )
    failed = [
        name
        for name, value in required
        if not helper.set_struct_property(overrides, name, value)
    ]
    if failed:
        raise RuntimeError(material.get_name() + " failed overrides: " + ",".join(failed))
    material.set_editor_property("base_property_overrides", overrides)
    unreal.MaterialEditingLibrary.update_material_instance(material)
    unreal.EditorAssetLibrary.set_metadata_tag(
        material,
        "KhazanOreMaterialRepair",
        "FModel WM_BBQProp_Ore hierarchy; yellow raw Tex_E removed",
    )
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)


def validation_record(material, helper):
    parent = material.get_editor_property("parent")
    textures = {
        parameter: helper.object_path(helper.texture_value(material, parameter))
        for parameter in (
            "BaseColorTexture",
            "OpacityTexture",
            "NormalTexture",
            "RoughnessTexture",
            "MetallicTexture",
            "EmissiveColorTexture",
        )
    }
    glow = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
        material, "GlowColor"
    )
    overrides = material.get_editor_property("base_property_overrides")
    return {
        "asset": material.get_path_name(),
        "parent": helper.object_path(parent),
        "textures": textures,
        "glow_color": [float(glow.r), float(glow.g), float(glow.b), float(glow.a)],
        "base_emissive_amount": helper.scalar_value(material, "BaseEmissiveAmount"),
        "tex_brightness": helper.scalar_value(material, "TexBrightness"),
        "blend_mode_override": str(overrides.get_editor_property("blend_mode")),
        "shading_model_override": str(overrides.get_editor_property("shading_model")),
        "opacity_clip_override": float(
            overrides.get_editor_property("opacity_mask_clip_value")
        ),
    }


def main(apply_changes=False):
    helper = load_tree_helper()
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load StormPass")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    signature_before = helper.transform_signature(actors_before)
    if signature_before["count"] != EXPECTED_ACTOR_TOTAL:
        raise RuntimeError("Unexpected StormPass actor count")

    sources = {name: resolved_source_record(name) for name in MATERIAL_COUNTS}
    materials = {}
    captures = {}
    for name in MATERIAL_COUNTS:
        material = unreal.EditorAssetLibrary.load_asset(material_path(name))
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError("Missing reconstructed ore material: " + name)
        materials[name] = material
        captures[name] = helper.capture_material(material)
    slots_before = slot_inventory(actor_subsystem, helper)
    if slots_before["counts"] != MATERIAL_COUNTS or slots_before["total"] != EXPECTED_SLOT_TOTAL:
        raise RuntimeError("Ore slot inventory changed")

    backups = []
    parent = unreal.EditorAssetLibrary.load_asset(PARENT_PATH)
    parent_created = False
    if apply_changes:
        backups = backup_materials(materials, helper)
        parent, parent_created = build_ore_parent(helper)
        for name in MATERIAL_COUNTS:
            apply_ore_instance(
                materials[name], parent, captures[name], sources[name], helper
            )
        unreal.EditorAssetLibrary.save_directory(
            REPAIR_ROOT, only_if_is_dirty=False, recursive=True
        )
        unreal.EditorAssetLibrary.save_directory(
            INSTANCE_ROOT, only_if_is_dirty=False, recursive=True
        )

    after = {
        name: validation_record(material, helper)
        for name, material in materials.items()
    }
    failures = []
    if apply_changes:
        for name, record in after.items():
            if helper.normalized_asset_path(record["parent"]) != PARENT_PATH:
                failures.append(name + ":parent")
            if any(not value for value in record["textures"].values()):
                failures.append(name + ":texture")
            expected = sources[name]
            if abs(record["base_emissive_amount"] - expected["effective_scalars"]["BaseEmissiveAmount"]) > 0.00001:
                failures.append(name + ":emissive_amount")
            if max(
                abs(left - right)
                for left, right in zip(record["glow_color"], expected["glow_color"])
            ) > 0.00001:
                failures.append(name + ":glow_color")
    slots_after = slot_inventory(actor_subsystem, helper)
    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    signature_after = helper.transform_signature(actors_after)
    if slots_after != slots_before:
        raise RuntimeError("Ore bindings changed during repair")
    if signature_after != signature_before:
        raise RuntimeError("Actor transforms changed during ore repair")
    if failures:
        raise RuntimeError("; ".join(failures))

    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "decision": (
            "The source hierarchy enables the ore path and inherits blue-grey GlowColor. "
            "The dedicated masked parent restores extracted textures, AO=R/Roughness=G/"
            "Metallic=B, and Tex_E.R-masked source glow instead of raw yellow Tex_E RGB."
        ),
        "source_records": sources,
        "counts": {
            "material": len(MATERIAL_COUNTS),
            "affected_slot": slots_before["total"],
            "actor": signature_before["count"],
        },
        "slot_inventory": slots_before,
        "backups": backups,
        "repair_parent": {
            "asset": helper.object_path(parent),
            "created": parent_created,
            "blend": "BLEND_Masked",
            "shading_model": "MSM_DefaultLit preview for source MSM_BBQHalfCartoon",
            "opacity_mask_clip": 0.3333,
            "tex_s_usage": "R=ambient occlusion, G=roughness, B=metallic",
            "tex_e_usage": "R mask multiplied by inherited GlowColor and BaseEmissiveAmount",
        },
        "material_after": after,
        "transform_before": signature_before,
        "transform_after": signature_after,
        "validation_failures": failures,
        "source_fidelity_note": (
            "Cooked custom material graph expressions are unavailable; the exact extracted "
            "textures and effective FModel parameters are reproduced in a native UE5 preview graph."
        ),
    }
    write_json(REPORT_PATH, report)
    print(
        "KHAZAN_STORMPASS_ORE: status={} materials={} slots={} actors={} transform_sha={}".format(
            report["status"],
            report["counts"]["material"],
            report["counts"]["affected_slot"],
            report["counts"]["actor"],
            signature_after["sha256"],
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
