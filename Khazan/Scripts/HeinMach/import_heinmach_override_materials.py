"""Rebuild and apply HeinMach actor-only override materials.

FModel does not emit standalone material instances as USD geometry. The 12
override-only materials are therefore reconstructed from their exported JSON
properties and texture images, then assigned through the source-to-UE slot map
created by repair_heinmach_materials.py.
"""

import collections
import json
import os
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
OVERRIDE_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials"
OVERRIDE_MATERIAL_ROOT = OVERRIDE_ROOT + "/Materials"
OVERRIDE_TEXTURE_ROOT = OVERRIDE_ROOT + "/Textures"
USD_PREVIEW_PARENT = (
    "/USDCore/Materials/UsdPreviewSurfaceTranslucent.UsdPreviewSurfaceTranslucent"
)
PLACEMENT_PATH = os.path.join(
    unreal.Paths.project_content_dir(),
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_RenderableStaticMeshPlacements.json",
)
MATERIAL_REPAIR_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Material_Surface_Repair.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Override_Material_Reconstruction.json",
)

MANAGED_LABEL_PREFIX = "HM_Prop_"
ENVIRONMENT_LEVELS = {
    "HeinMach_Chrcollision",
    "HeinMach_Landscape2",
    "HeinMach_Landscape1",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_Blizzard_2",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV07_BG",
    "HeinMach_SubLV05_Escape_1",
}


def log(message):
    unreal.log("KHAZAN_HEINMACH_OVERRIDE_MATERIALS: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def package_json_path(package):
    relative = os.path.join(*str(package).split("/")) + ".json"
    direct = os.path.join(FMODEL_ROOT, relative)
    exported = os.path.join(FMODEL_ROOT, "Exports", relative)
    return direct if os.path.isfile(direct) else exported


def package_from_object_path(object_path):
    return str(object_path).rsplit(".", 1)[0]


def texture_basename(object_path):
    return package_basename(package_from_object_path(object_path))


def accepted_placements(payload):
    return [
        placement
        for placement in payload.get("placements", [])
        if placement.get("source_level") in ENVIRONMENT_LEVELS
        and placement.get("visible") is not False
        and placement.get("static_mesh_package")
    ]


def managed_label(placement):
    return (
        "{}{}_{}_{}".format(
            MANAGED_LABEL_PREFIX,
            placement.get("source_level", "Unknown"),
            placement.get("source_object_index", 0),
            placement.get("actor_name", "Actor"),
        )
    )[:220]


def raw_material_record(package):
    path = package_json_path(package)
    payload = load_json(path)
    if not isinstance(payload, list):
        raise RuntimeError("Expected raw FModel material JSON list: " + path)
    record = next(
        (
            item
            for item in payload
            if isinstance(item, dict)
            and item.get("Type") in {"Material", "MaterialInstanceConstant"}
        ),
        None,
    )
    if not record:
        raise RuntimeError("Material record is missing from: " + path)
    properties = record.get("Properties", {})
    texture_parameters = {}
    texture_packages = {}
    for item in properties.get("TextureParameterValues", []):
        if not isinstance(item, dict):
            continue
        parameter_name = item.get("ParameterInfo", {}).get("Name")
        object_path = item.get("ParameterValue", {}).get("ObjectPath")
        if not parameter_name or not object_path:
            continue
        texture_parameters[parameter_name] = texture_basename(object_path)
        texture_packages[texture_basename(object_path)] = package_from_object_path(
            object_path
        )
    return {
        "package": package,
        "name": package_basename(package),
        "json_path": path,
        "parent": properties.get("Parent", {}).get("ObjectPath"),
        "texture_parameters": texture_parameters,
        "texture_packages": texture_packages,
        "base_property_overrides": properties.get("BasePropertyOverrides", {}),
    }


def source_image_path(texture_package):
    relative = os.path.join(*str(texture_package).split("/"))
    candidates = []
    for root in (FMODEL_ROOT, os.path.join(FMODEL_ROOT, "Exports")):
        for extension in (".png", ".hdr", ".exr", ".tga"):
            candidates.append(os.path.join(root, relative) + extension)
    return next((path for path in candidates if os.path.isfile(path)), None)


def existing_texture_index():
    result = {}
    if not unreal.EditorAssetLibrary.does_directory_exist(OVERRIDE_TEXTURE_ROOT):
        return result
    for asset_path in unreal.EditorAssetLibrary.list_assets(
        OVERRIDE_TEXTURE_ROOT, recursive=True, include_folder=False
    ):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset or asset.get_class().get_name() != "Texture2D":
            continue
        name = asset.get_name()
        if name.startswith("T_"):
            name = name[2:]
        result[name] = asset
    return result


def import_textures(records):
    required = {}
    for record in records:
        required.update(record["texture_packages"])
    texture_index = existing_texture_index()
    missing_source_images = []
    tasks = []
    for texture_name, texture_package in sorted(required.items()):
        if texture_name in texture_index:
            continue
        image_path = source_image_path(texture_package)
        if not image_path:
            missing_source_images.append(
                {"texture": texture_name, "package": texture_package}
            )
            continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", image_path)
        task.set_editor_property("destination_path", OVERRIDE_TEXTURE_ROOT)
        task.set_editor_property("destination_name", "T_" + texture_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        tasks.append(task)

    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    texture_index = existing_texture_index()

    configured = []
    for texture_name, texture in sorted(texture_index.items()):
        if texture_name not in required:
            continue
        try:
            texture.modify()
            upper_name = texture_name.upper()
            if upper_name.endswith("_N"):
                texture.set_editor_property(
                    "compression_settings",
                    unreal.TextureCompressionSettings.TC_NORMALMAP,
                )
                texture.set_editor_property("srgb", False)
            elif upper_name.endswith("_S") or "HEIGHT" in upper_name:
                texture.set_editor_property(
                    "compression_settings",
                    unreal.TextureCompressionSettings.TC_MASKS,
                )
                texture.set_editor_property("srgb", False)
            configured.append(texture.get_path_name())
        except Exception:
            pass
    if unreal.EditorAssetLibrary.does_directory_exist(OVERRIDE_TEXTURE_ROOT):
        unreal.EditorAssetLibrary.save_directory(
            OVERRIDE_TEXTURE_ROOT, only_if_is_dirty=False, recursive=True
        )
    return texture_index, tasks, missing_source_images, configured


def source_material_templates(repair_report):
    result = collections.defaultdict(list)
    for mesh_record in repair_report.get("mesh_mappings", []):
        for assignment in mesh_record.get("assignments", []):
            source_name = assignment.get("source", {}).get("name")
            actual_path = assignment.get("actual_material_path")
            if source_name and actual_path:
                result[source_name].append(actual_path)
    return result


def create_or_load_material(record, template_index):
    asset_name = "MI_" + record["name"]
    asset_path = OVERRIDE_MATERIAL_ROOT + "/" + asset_name
    material = unreal.EditorAssetLibrary.load_asset(asset_path)
    if material:
        return material, False, None

    base_name = record["name"].removesuffix("_Portal")
    template_paths = template_index.get(base_name, [])
    if template_paths:
        source_path = collections.Counter(template_paths).most_common(1)[0][0]
        duplicated = unreal.EditorAssetLibrary.duplicate_asset(
            source_path.split(".", 1)[0], asset_path
        )
        material = unreal.EditorAssetLibrary.load_asset(asset_path)
        if duplicated and material:
            return material, True, source_path

    factory = unreal.MaterialInstanceConstantFactoryNew()
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name,
        OVERRIDE_MATERIAL_ROOT,
        unreal.MaterialInstanceConstant,
        factory,
    )
    if not material:
        raise RuntimeError("Failed to create material instance: " + asset_path)
    parent = unreal.EditorAssetLibrary.load_asset(USD_PREVIEW_PARENT)
    if not parent:
        raise RuntimeError("USD PreviewSurface parent is unavailable")
    unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
    return material, True, None


def blend_mode_value(value):
    mapping = {
        "BLEND_Opaque": unreal.BlendMode.BLEND_OPAQUE,
        "BLEND_Masked": unreal.BlendMode.BLEND_MASKED,
        "BLEND_Translucent": unreal.BlendMode.BLEND_TRANSLUCENT,
        "BLEND_Additive": unreal.BlendMode.BLEND_ADDITIVE,
        "BLEND_Modulate": unreal.BlendMode.BLEND_MODULATE,
        "BLEND_AlphaComposite": unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
        "BLEND_AlphaHoldout": unreal.BlendMode.BLEND_ALPHA_HOLDOUT,
    }
    return mapping.get(str(value))


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def set_texture(material, parameter_name, texture):
    return unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
        material, parameter_name, texture
    )


def set_scalar(material, parameter_name, value):
    return unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, parameter_name, float(value)
    )


def configure_material(material, record, texture_index):
    material.modify()
    parameters = record["texture_parameters"]
    applied_textures = {}
    missing_textures = []

    channel_mapping = {
        "Tex_D": (("BaseColorTexture", "OpacityTexture"), ("UseBaseColorTexture", "UseOpacityTexture")),
        "Tex_S": (("MetallicTexture", "RoughnessTexture"), ("UseMetallicTexture", "UseRoughnessTexture")),
        "Tex_N": (("NormalTexture",), ("UseNormalTexture",)),
        "Tex_E": (("EmissiveColorTexture",), ("UseEmissiveColorTexture",)),
    }
    for source_parameter, (target_parameters, toggles) in channel_mapping.items():
        texture_name = parameters.get(source_parameter)
        if not texture_name:
            continue
        texture = texture_index.get(texture_name)
        if not texture:
            missing_textures.append(texture_name)
            continue
        for target_parameter in target_parameters:
            set_texture(material, target_parameter, texture)
        for toggle in toggles:
            set_scalar(material, toggle, 1.0)
        applied_textures[source_parameter] = texture.get_path_name()

    set_scalar(material, "Opacity", 1.0)
    overrides = material.get_editor_property("base_property_overrides")
    source_overrides = record["base_property_overrides"]
    if "TwoSided" in source_overrides:
        set_struct_property(overrides, "override_two_sided", True)
        set_struct_property(overrides, "two_sided", bool(source_overrides["TwoSided"]))
    blend_mode = blend_mode_value(source_overrides.get("BlendMode"))
    if blend_mode is not None:
        set_struct_property(overrides, "override_blend_mode", True)
        set_struct_property(overrides, "blend_mode", blend_mode)
    clip_value = source_overrides.get("OpacityMaskClipValue")
    if isinstance(clip_value, (int, float)):
        set_struct_property(overrides, "override_opacity_mask_clip_value", True)
        set_struct_property(overrides, "opacity_mask_clip_value", float(clip_value))
    material.set_editor_property("base_property_overrides", overrides)
    try:
        unreal.MaterialEditingLibrary.update_material_instance(material)
    except Exception:
        pass
    return applied_textures, missing_textures


def main():
    placement_payload = load_json(PLACEMENT_PATH)
    placements = accepted_placements(placement_payload)
    repair_report = load_json(MATERIAL_REPAIR_REPORT_PATH)
    unresolved_packages = [
        item["package"]
        for item in repair_report.get("unresolved_override_materials", [])
    ]
    if len(unresolved_packages) != 12:
        raise RuntimeError(
            "Expected 12 override-only material packages, got {}".format(
                len(unresolved_packages)
            )
        )

    records = [raw_material_record(package) for package in unresolved_packages]
    texture_index, import_tasks, missing_images, configured_textures = import_textures(
        records
    )
    template_index = source_material_templates(repair_report)

    materials_by_package = {}
    material_results = []
    for record in records:
        material, created, template = create_or_load_material(record, template_index)
        applied_textures, missing_textures = configure_material(
            material, record, texture_index
        )
        materials_by_package[record["package"]] = material
        material_results.append(
            {
                "package": record["package"],
                "material": material.get_path_name(),
                "created": created,
                "template": template,
                "applied_textures": applied_textures,
                "missing_textures": missing_textures,
            }
        )

    unreal.EditorAssetLibrary.save_directory(
        OVERRIDE_MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )

    slot_maps = {}
    for mesh_record in repair_report.get("mesh_mappings", []):
        slot_maps[mesh_record["mesh_package"]] = {
            int(assignment["source_slot"]): int(assignment["ue_slot"])
            for assignment in mesh_record.get("assignments", [])
        }

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }

    target_slot_count = 0
    applied_slot_count = 0
    single_slot_fallback_count = 0
    unresolved = collections.Counter()
    for placement in placements:
        actor = actors_by_label.get(managed_label(placement))
        if not actor:
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            continue
        slot_map = slot_maps.get(str(placement["static_mesh_package"]), {})
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if package not in materials_by_package:
                continue
            target_slot_count += 1
            ue_slot = slot_map.get(source_slot)
            # Two original variant actors store a sparse override at index 1
            # even though FModel's mesh export contains one render slot. In
            # that unambiguous case the variant belongs on the only UE slot.
            if ue_slot is None and len(slot_map) == 1:
                ue_slot = next(iter(slot_map.values()))
                single_slot_fallback_count += 1
            material = materials_by_package.get(package)
            if ue_slot is None or not material:
                unresolved[package] += 1
                continue
            component.set_material(ue_slot, material)
            applied_slot_count += 1

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach override-material assignments")

    report = {
        "status": "reconstructed",
        "map_path": MAP_PATH,
        "material_package_count": len(records),
        "created_or_updated_material_count": len(material_results),
        "requested_texture_count": len(
            {name for record in records for name in record["texture_packages"]}
        ),
        "texture_import_task_count": len(import_tasks),
        "configured_texture_count": len(configured_textures),
        "missing_source_images": missing_images,
        "material_results": material_results,
        "target_override_slot_count": target_slot_count,
        "applied_override_slot_count": applied_slot_count,
        "single_slot_fallback_count": single_slot_fallback_count,
        "unresolved_override_slot_count": sum(unresolved.values()),
        "unresolved_override_materials": [
            {"package": package, "slot_count": count}
            for package, count in sorted(unresolved.items())
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT materials={} textures={} applied_overrides={}/{} unresolved={} report={}".format(
            report["created_or_updated_material_count"],
            report["configured_texture_count"],
            report["applied_override_slot_count"],
            report["target_override_slot_count"],
            report["unresolved_override_slot_count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        unreal.log_error("KHAZAN_HEINMACH_OVERRIDE_MATERIALS: " + str(exception))
        unreal.log_error(failure["traceback"])
        raise
