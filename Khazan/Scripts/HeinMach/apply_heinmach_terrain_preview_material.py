"""Apply a reversible snow preview material to the two extracted terrains.

FModel exported the 57 landscape components and their UVs, but not the source
landscape layer/weightmap material data.  The imported aggregate terrain meshes
therefore use MI_DisplayColor placeholders.  This pass preserves mesh assets
and transforms, backs up the map once, and applies an explicitly approximate
snow material using an extracted HeinMach snow diffuse texture.
"""

import json
import os
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeTerrainPreviewMaterial"
)
TERRAIN_LABELS = ("HM_Terrain_Landscape1", "HM_Terrain_Landscape2")
MATERIAL_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/TerrainPreview"
)
BASE_MATERIAL_PATH = MATERIAL_ROOT + "/M_HeinMach_Terrain_Snow_Preview"
INSTANCE_PATH = MATERIAL_ROOT + "/MI_HeinMach_Terrain_Snow_Preview"
SNOW_TEXTURE_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials/"
    "Textures/T_WLT_Snow_004A_D.T_WLT_Snow_004A_D"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Terrain_Preview_Material.json",
)

PREVIEW_VERSION = 1
UV_TILING_SCALE = 0.125
SNOW_TINT = unreal.LinearColor(0.58, 0.65, 0.72, 1.0)
ROUGHNESS = 0.84
SPECULAR = 0.16


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def object_path(value):
    return value.get_path_name() if value else None


def expression(material, expression_class, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default))
    return node


def build_base_material(snow_texture):
    ensure_directory(MATERIAL_ROOT)
    material = unreal.EditorAssetLibrary.load_asset(BASE_MATERIAL_PATH)
    created = material is None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_HeinMach_Terrain_Snow_Preview",
            MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create terrain preview base material")

    material.modify()
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("two_sided", False)

    library = unreal.MaterialEditingLibrary
    texcoord = expression(
        material, unreal.MaterialExpressionTextureCoordinate, -900, -160
    )
    tiling = scalar_parameter(material, "UVTilingScale", UV_TILING_SCALE, -900, 20)
    scaled_uv = expression(material, unreal.MaterialExpressionMultiply, -680, -120)
    texture = expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, -430, -120
    )
    texture.set_editor_property("parameter_name", "SnowDiffuse")
    texture.set_editor_property("texture", snow_texture)
    tint = expression(material, unreal.MaterialExpressionVectorParameter, -400, 100)
    tint.set_editor_property("parameter_name", "SnowTint")
    tint.set_editor_property("default_value", SNOW_TINT)
    tinted_color = expression(material, unreal.MaterialExpressionMultiply, -120, -50)
    roughness = scalar_parameter(material, "Roughness", ROUGHNESS, -120, 130)
    specular = scalar_parameter(material, "Specular", SPECULAR, -120, 250)

    library.connect_material_expressions(texcoord, "", scaled_uv, "A")
    library.connect_material_expressions(tiling, "", scaled_uv, "B")
    library.connect_material_expressions(scaled_uv, "", texture, "Coordinates")
    library.connect_material_expressions(texture, "RGB", tinted_color, "A")
    library.connect_material_expressions(tint, "RGB", tinted_color, "B")
    library.connect_material_property(
        tinted_color, "", unreal.MaterialProperty.MP_BASE_COLOR
    )
    library.connect_material_property(
        roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
    )
    library.connect_material_property(specular, "", unreal.MaterialProperty.MP_SPECULAR)
    library.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, created


def build_instance(base_material, snow_texture):
    instance = unreal.EditorAssetLibrary.load_asset(INSTANCE_PATH)
    created = instance is None
    if not instance:
        instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_HeinMach_Terrain_Snow_Preview",
            MATERIAL_ROOT,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
    if not instance:
        raise RuntimeError("Failed to create terrain preview material instance")
    library = unreal.MaterialEditingLibrary
    library.set_material_instance_parent(instance, base_material)
    library.set_material_instance_texture_parameter_value(
        instance, "SnowDiffuse", snow_texture
    )
    library.set_material_instance_scalar_parameter_value(
        instance, "UVTilingScale", UV_TILING_SCALE
    )
    library.set_material_instance_scalar_parameter_value(
        instance, "Roughness", ROUGHNESS
    )
    library.set_material_instance_scalar_parameter_value(instance, "Specular", SPECULAR)
    library.set_material_instance_vector_parameter_value(
        instance, "SnowTint", SNOW_TINT
    )
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    return instance, created


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create terrain-preview map backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def main():
    snow_texture = unreal.EditorAssetLibrary.load_asset(SNOW_TEXTURE_PATH)
    if not snow_texture:
        raise RuntimeError("Missing extracted snow texture: " + SNOW_TEXTURE_PATH)
    base_material, base_created = build_base_material(snow_texture)
    instance, instance_created = build_instance(base_material, snow_texture)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_path = current_world.get_path_name() if current_world else ""
    if not current_path.startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")
    backup_created = backup_map_once()

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    terrain_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label() in TERRAIN_LABELS
    }
    if set(terrain_by_label) != set(TERRAIN_LABELS):
        raise RuntimeError(
            "Terrain actor inventory mismatch: " + str(sorted(terrain_by_label))
        )

    actor_results = []
    material_mismatches = []
    for label in TERRAIN_LABELS:
        actor = terrain_by_label[label]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Terrain actor has no StaticMeshComponent: " + label)
        mesh = component.get_editor_property("static_mesh")
        slot_count = max(1, int(component.get_num_materials()))
        before = [object_path(component.get_material(slot)) for slot in range(slot_count)]
        for slot in range(slot_count):
            component.set_material(slot, instance)
        after = [object_path(component.get_material(slot)) for slot in range(slot_count)]
        expected = object_path(instance)
        if any(path != expected for path in after):
            material_mismatches.append(label)
        actor_results.append(
            {
                "label": label,
                "mesh": object_path(mesh),
                "material_slot_count": slot_count,
                "materials_before_this_run": before,
                "materials_after": after,
                "location_cm": {
                    "x": float(actor.get_actor_location().x),
                    "y": float(actor.get_actor_location().y),
                    "z": float(actor.get_actor_location().z),
                },
                "scale": {
                    "x": float(actor.get_actor_scale3d().x),
                    "y": float(actor.get_actor_scale3d().y),
                    "z": float(actor.get_actor_scale3d().z),
                },
            }
        )

    if material_mismatches:
        raise RuntimeError("Terrain preview material assignment failed")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save terrain-preview HeinMach map")
    unreal.EditorAssetLibrary.save_directory(
        MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "applied_preview",
        "preview_version": PREVIEW_VERSION,
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "base_material": object_path(base_material),
        "base_material_created": base_created,
        "material_instance": object_path(instance),
        "material_instance_created": instance_created,
        "snow_texture": object_path(snow_texture),
        "uv_tiling_scale": UV_TILING_SCALE,
        "snow_tint": {
            "r": float(SNOW_TINT.r),
            "g": float(SNOW_TINT.g),
            "b": float(SNOW_TINT.b),
            "a": float(SNOW_TINT.a),
        },
        "roughness": ROUGHNESS,
        "specular": SPECULAR,
        "terrain_actor_count": len(actor_results),
        "material_mismatch_count": len(material_mismatches),
        "actors": actor_results,
        "source_limitations": {
            "landscape_component_count": 57,
            "original_weightmaps_found": False,
            "original_landscape_material_graph_found": False,
            "note": (
                "This is a reversible visual preview. Geometry, source transforms, "
                "and UVs are preserved; original layer blending cannot be recovered "
                "without the missing WLM/weightmap exports."
            ),
        },
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "Barehanded staggering/basic-movement protagonist scenes",
        ],
    }
    write_json(REPORT_PATH, report)
    unreal.log(
        "KHAZAN_HEINMACH_TERRAIN_PREVIEW: RESULT status={} terrain={} "
        "mismatches={} report={}".format(
            report["status"],
            report["terrain_actor_count"],
            report["material_mismatch_count"],
            REPORT_PATH,
        )
    )


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
        unreal.log_error("KHAZAN_HEINMACH_TERRAIN_PREVIEW: " + str(exception))
        raise
