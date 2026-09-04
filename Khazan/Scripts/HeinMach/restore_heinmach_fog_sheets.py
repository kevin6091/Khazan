"""Restore non-cinematic HeinMach fog sheets with a safe preview material.

FModel preserves the 50 actor transforms and dynamic parameter values, but its
USD preview materials collapse the original custom fog shader to an opaque
white material.  This script imports the authored fog plane and smoke-noise
texture, creates a translucent noise/edge-fade preview shader, makes one MIC per
source actor, and places the actors at their exact source transforms.
"""

import json
import math
import os
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeFogSheetRestore"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed"
FOG_ROOT = RECONSTRUCTED_ROOT + "/FogSheets"
FOG_MESH_ROOT = FOG_ROOT + "/Meshes"
FOG_TEXTURE_ROOT = FOG_ROOT + "/Textures"
FOG_MATERIAL_ROOT = FOG_ROOT + "/Materials"
BASE_MATERIAL_PATH = FOG_MATERIAL_ROOT + "/M_HeinMach_FogSheet_Preview"
NOISE_TEXTURE_PATH = FOG_TEXTURE_ROOT + "/T_FTW_Smoke_Noise_001"
PLANE_STAGE_NAME = "HeinMach_FogSheetPlane"
PLANE_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", PLANE_STAGE_NAME + ".usda"
)
PLANE_SOURCE_PATH = os.path.join(
    FMODEL_ROOT,
    "BBQ",
    "Content",
    "_Kazan_",
    "Art",
    "VFX",
    "VFX_Mesh",
    "FS_FogSheet_Plane.usda",
)
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
GAP_REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Render_Gap_Analysis.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_FogSheet_Restore.json",
)

MANAGED_LABEL_PREFIX = "HM_FogSheet_"
MANAGED_FOLDER_ROOT = "HeinMach/Reconstructed/FogSheets"
EXPECTED_FOG_COUNT = 50
GLOBAL_OPACITY_SCALE = 0.18
EMISSIVE_SCALE = 0.10
PREVIEW_MATERIAL_VERSION = 3


def log(message):
    unreal.log("KHAZAN_HEINMACH_FOG: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required render-gap report does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def list_class_assets(root, class_name):
    if not unreal.EditorAssetLibrary.does_directory_exist(root):
        return []
    return [
        path
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        )
        if asset_class_name(path) == class_name
    ]


def normalized_asset_names(asset):
    names = {asset.get_name()}
    for prefix in ("SM_", "T_", "MI_", "M_"):
        if asset.get_name().startswith(prefix):
            names.add(asset.get_name()[len(prefix) :])
    return names


def import_fog_plane():
    if not os.path.isfile(PLANE_SOURCE_PATH):
        raise RuntimeError("Fog plane source is missing: " + PLANE_SOURCE_PATH)
    ensure_directory(FOG_MESH_ROOT)
    existing = []
    for path in list_class_assets(FOG_MESH_ROOT, "StaticMesh"):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset and "FS_FogSheet_Plane" in normalized_asset_names(asset):
            existing.append(asset)
    if len(existing) == 1:
        return existing[0], False, []
    if len(existing) > 1:
        raise RuntimeError("Multiple imported fog plane meshes were found")

    os.makedirs(os.path.dirname(PLANE_STAGE_PATH), exist_ok=True)
    with open(PLANE_STAGE_PATH, "w", encoding="utf-8", newline="\n") as output:
        output.write(
            "#usda 1.0\n(\n    metersPerUnit = 0.01\n    upAxis = \"Z\"\n"
            "    subLayers = [\n        @{}@\n    ]\n)\n".format(
                PLANE_SOURCE_PATH.replace("\\", "/")
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
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", PLANE_STAGE_PATH)
    task.set_editor_property("destination_path", FOG_MESH_ROOT)
    task.set_editor_property("destination_name", PLANE_STAGE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))

    candidates = []
    for path in list_class_assets(FOG_MESH_ROOT, "StaticMesh"):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset and "FS_FogSheet_Plane" in normalized_asset_names(asset):
            candidates.append(asset)
    if len(candidates) != 1:
        raise RuntimeError(
            "Fog plane import validation failed: candidates={}".format(len(candidates))
        )
    return candidates[0], True, imported_paths


def import_noise_texture():
    existing = unreal.EditorAssetLibrary.load_asset(NOISE_TEXTURE_PATH)
    if existing:
        return existing, False, []
    if not os.path.isfile(NOISE_SOURCE_PATH):
        raise RuntimeError("Fog noise source is missing: " + NOISE_SOURCE_PATH)
    ensure_directory(FOG_TEXTURE_ROOT)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", NOISE_SOURCE_PATH)
    task.set_editor_property("destination_path", FOG_TEXTURE_ROOT)
    task.set_editor_property("destination_name", "T_FTW_Smoke_Noise_001")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = unreal.EditorAssetLibrary.load_asset(NOISE_TEXTURE_PATH)
    if not texture:
        raise RuntimeError("Fog noise texture import did not create expected asset")
    texture.modify()
    texture.set_editor_property("srgb", False)
    try:
        texture.set_editor_property(
            "compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE
        )
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
    return texture, True, list(task.get_editor_property("imported_object_paths"))


def expression(material, expression_class, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )


def scalar_parameter(material, name, default, x, y):
    node = expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", float(default))
    return node


def create_base_material(noise_texture):
    existing = unreal.EditorAssetLibrary.load_asset(BASE_MATERIAL_PATH)
    ensure_directory(FOG_MATERIAL_ROOT)
    created = existing is None
    material = existing
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_HeinMach_FogSheet_Preview",
            FOG_MATERIAL_ROOT,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
    if not material:
        raise RuntimeError("Failed to create fog preview base material")
    material.modify()
    # Rebuild the graph on every run so a partially-created or outdated preview
    # material cannot leave all fog sheets on WorldGridMaterial.  The UE Python
    # pin name for single-input expressions is "None" (not the UI label
    # "Input").
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("two_sided", False)
    try:
        material.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_UNLIT
        )
    except Exception:
        pass

    library = unreal.MaterialEditingLibrary
    texcoord = expression(material, unreal.MaterialExpressionTextureCoordinate, -1200, -80)
    panner = expression(material, unreal.MaterialExpressionPanner, -1000, -220)
    panner.set_editor_property("speed_x", 0.015)
    panner.set_editor_property("speed_y", 0.005)
    noise = expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -780, -220)
    noise.set_editor_property("parameter_name", "NoiseTexture")
    noise.set_editor_property("texture", noise_texture)

    center = expression(material, unreal.MaterialExpressionConstant, -1000, 80)
    center.set_editor_property("r", 0.5)
    subtract = expression(material, unreal.MaterialExpressionSubtract, -820, 80)
    absolute = expression(material, unreal.MaterialExpressionAbs, -650, 80)
    two = expression(material, unreal.MaterialExpressionConstant, -650, 230)
    two.set_editor_property("r", 2.0)
    scaled_abs = expression(material, unreal.MaterialExpressionMultiply, -470, 80)
    mask_u = expression(material, unreal.MaterialExpressionComponentMask, -290, 30)
    mask_u.set_editor_property("r", True)
    mask_u.set_editor_property("g", False)
    mask_u.set_editor_property("b", False)
    mask_u.set_editor_property("a", False)
    mask_v = expression(material, unreal.MaterialExpressionComponentMask, -290, 150)
    mask_v.set_editor_property("r", False)
    mask_v.set_editor_property("g", True)
    mask_v.set_editor_property("b", False)
    mask_v.set_editor_property("a", False)
    fade_u = expression(material, unreal.MaterialExpressionOneMinus, -100, 30)
    fade_v = expression(material, unreal.MaterialExpressionOneMinus, -100, 150)
    edge_fade = expression(material, unreal.MaterialExpressionMultiply, 80, 90)
    noise_r = expression(material, unreal.MaterialExpressionComponentMask, 80, -150)
    noise_r.set_editor_property("r", True)
    noise_r.set_editor_property("g", False)
    noise_r.set_editor_property("b", False)
    noise_r.set_editor_property("a", False)
    noise_edge = expression(material, unreal.MaterialExpressionMultiply, 260, -80)

    max_opacity = scalar_parameter(material, "MaxOpacity", 0.8, 260, 120)
    opacity_source = expression(material, unreal.MaterialExpressionMultiply, 450, -20)
    opacity_scale = expression(material, unreal.MaterialExpressionConstant, 450, 150)
    opacity_scale.set_editor_property("r", GLOBAL_OPACITY_SCALE)
    opacity_final = expression(material, unreal.MaterialExpressionMultiply, 650, 20)

    tint = expression(material, unreal.MaterialExpressionVectorParameter, 260, -330)
    tint.set_editor_property("parameter_name", "FogTint")
    tint.set_editor_property(
        "default_value", unreal.LinearColor(0.62, 0.70, 0.76, 1.0)
    )
    emissive_strength = scalar_parameter(material, "EmissiveStrength", 1.0, 260, -230)
    emissive_scale = expression(material, unreal.MaterialExpressionConstant, 450, -230)
    emissive_scale.set_editor_property("r", EMISSIVE_SCALE)
    scaled_emissive = expression(material, unreal.MaterialExpressionMultiply, 630, -250)
    tinted_emissive = expression(material, unreal.MaterialExpressionMultiply, 820, -260)
    emissive_final = expression(material, unreal.MaterialExpressionMultiply, 1000, -170)

    library.connect_material_expressions(texcoord, "", panner, "Coordinate")
    library.connect_material_expressions(panner, "", noise, "Coordinates")
    library.connect_material_expressions(texcoord, "", subtract, "A")
    library.connect_material_expressions(center, "", subtract, "B")
    library.connect_material_expressions(subtract, "", absolute, "None")
    library.connect_material_expressions(absolute, "", scaled_abs, "A")
    library.connect_material_expressions(two, "", scaled_abs, "B")
    library.connect_material_expressions(scaled_abs, "", mask_u, "None")
    library.connect_material_expressions(scaled_abs, "", mask_v, "None")
    library.connect_material_expressions(mask_u, "", fade_u, "None")
    library.connect_material_expressions(mask_v, "", fade_v, "None")
    library.connect_material_expressions(fade_u, "", edge_fade, "A")
    library.connect_material_expressions(fade_v, "", edge_fade, "B")
    library.connect_material_expressions(noise, "", noise_r, "None")
    library.connect_material_expressions(noise_r, "", noise_edge, "A")
    library.connect_material_expressions(edge_fade, "", noise_edge, "B")
    library.connect_material_expressions(noise_edge, "", opacity_source, "A")
    library.connect_material_expressions(max_opacity, "", opacity_source, "B")
    library.connect_material_expressions(opacity_source, "", opacity_final, "A")
    library.connect_material_expressions(opacity_scale, "", opacity_final, "B")
    library.connect_material_expressions(emissive_strength, "", scaled_emissive, "A")
    library.connect_material_expressions(emissive_scale, "", scaled_emissive, "B")
    library.connect_material_expressions(tint, "RGB", tinted_emissive, "A")
    library.connect_material_expressions(scaled_emissive, "", tinted_emissive, "B")
    library.connect_material_expressions(tinted_emissive, "", emissive_final, "A")
    library.connect_material_expressions(noise_edge, "", emissive_final, "B")
    library.connect_material_property(
        opacity_final, "", unreal.MaterialProperty.MP_OPACITY
    )
    library.connect_material_property(
        emissive_final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    library.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, created


def managed_label(record):
    return (
        "{}{}_{:05d}_{}".format(
            MANAGED_LABEL_PREFIX,
            record.get("source_level", "Unknown"),
            int(record.get("source_object_index", 0)),
            record.get("actor_name", "Fog"),
        )
    )[:220]


def instance_asset_name(record):
    return (
        "MI_HM_Fog_{}_{:05d}_{}".format(
            record.get("source_level", "Unknown"),
            int(record.get("source_object_index", 0)),
            record.get("actor_name", "Fog"),
        )
    )[:180]


def source_scalar(record, name, fallback):
    value = record.get("dynamic_scalar_parameters", {}).get(name, fallback)
    return float(value) if isinstance(value, (int, float)) else float(fallback)


def create_material_instances(records, base_material, noise_texture):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    result = {}
    created_count = 0
    updated_count = 0
    for record in records:
        name = instance_asset_name(record)
        path = FOG_MATERIAL_ROOT + "/" + name
        material = unreal.EditorAssetLibrary.load_asset(path)
        if not material:
            material = asset_tools.create_asset(
                name,
                FOG_MATERIAL_ROOT,
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
            if not material:
                raise RuntimeError("Failed to create fog material instance: " + name)
            created_count += 1
        else:
            updated_count += 1
        unreal.MaterialEditingLibrary.set_material_instance_parent(
            material, base_material
        )
        max_opacity = max(0.0, min(1.0, source_scalar(record, "MaxOpacity", 0.8)))
        emissive = max(
            0.0, min(10.0, source_scalar(record, "emmisivestrength", 1.0))
        )
        parent_name = str(record.get("dynamic_material_parent_package", ""))
        tint = (
            unreal.LinearColor(0.68, 0.72, 0.78, 1.0)
            if parent_name.endswith("FMI_FogSheet_01")
            else unreal.LinearColor(0.56, 0.66, 0.72, 1.0)
        )
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            material, "MaxOpacity", max_opacity
        )
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            material, "EmissiveStrength", emissive
        )
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
            material, "FogTint", tint
        )
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
            material, "NoiseTexture", noise_texture
        )
        unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
        result[managed_label(record)] = material
    return result, created_count, updated_count


def vector_from_transform(transform):
    value = transform.get("location_cm", {})
    return unreal.Vector(
        x=float(value.get("x", 0.0)),
        y=float(value.get("y", 0.0)),
        z=float(value.get("z", 0.0)),
    )


def rotator_from_transform(transform):
    value = transform.get("rotation_degrees", {})
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def scale_from_transform(transform):
    value = transform.get("scale", {})
    return unreal.Vector(
        x=float(value.get("x", 1.0)),
        y=float(value.get("y", 1.0)),
        z=float(value.get("z", 1.0)),
    )


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def spawn_static_mesh_actor(actor_subsystem, mesh, location, rotation):
    try:
        actor = actor_subsystem.spawn_actor_from_object(mesh, location, rotation)
    except Exception:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor, location, rotation
        )
        if actor:
            actor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh)
    if not actor:
        raise RuntimeError("Failed to spawn fog sheet actor")
    return actor


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create fog restore map backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def vector_distance(a, b):
    return math.sqrt(
        (float(a.x) - float(b.x)) ** 2
        + (float(a.y) - float(b.y)) ** 2
        + (float(a.z) - float(b.z)) ** 2
    )


def place_fog(records, plane_mesh, materials):
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_subsystem.get_editor_world()
    current_path = current_world.get_path_name() if current_world else ""
    if not current_path.startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    managed = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    created_count = 0
    reused_count = 0
    material_assignment_count = 0
    max_location_error = 0.0
    max_scale_error = 0.0
    mesh_mismatches = []
    material_mismatches = []

    for record in records:
        label = managed_label(record)
        transform = record.get("transform", {})
        expected_location = vector_from_transform(transform)
        expected_rotation = rotator_from_transform(transform)
        expected_scale = scale_from_transform(transform)
        actor = managed.get(label)
        if actor:
            reused_count += 1
            actor.set_actor_location(expected_location, False, False)
            actor.set_actor_rotation(expected_rotation, False)
        else:
            actor = spawn_static_mesh_actor(
                actor_subsystem, plane_mesh, expected_location, expected_rotation
            )
            actor.set_actor_label(label, mark_dirty=True)
            managed[label] = actor
            created_count += 1
        actor.set_actor_scale3d(expected_scale)
        set_actor_folder(
            actor,
            "{}/{}".format(MANAGED_FOLDER_ROOT, record.get("source_level", "Unknown")),
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component.get_editor_property("static_mesh") != plane_mesh:
            component.set_static_mesh(plane_mesh)
        component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        component.set_editor_property("cast_shadow", False)
        try:
            component.set_editor_property(
                "translucency_sort_priority",
                int(record.get("translucency_sort_priority", 0)),
            )
        except Exception:
            pass
        try:
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        material = materials[label]
        slot_count = max(1, int(component.get_num_materials()))
        for slot in range(slot_count):
            component.set_material(slot, material)
            material_assignment_count += 1

        max_location_error = max(
            max_location_error,
            vector_distance(actor.get_actor_location(), expected_location),
        )
        max_scale_error = max(
            max_scale_error,
            vector_distance(actor.get_actor_scale3d(), expected_scale),
        )
        if component.get_editor_property("static_mesh") != plane_mesh:
            mesh_mismatches.append(label)
        if component.get_material(0) != material:
            material_mismatches.append(label)

    final_actors = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    ]
    return level_subsystem, {
        "created_count": created_count,
        "reused_count": reused_count,
        "final_managed_actor_count": len(final_actors),
        "final_total_actor_count": len(actor_subsystem.get_all_level_actors()),
        "material_assignment_count": material_assignment_count,
        "max_location_error_cm": max_location_error,
        "max_scale_error": max_scale_error,
        "mesh_mismatch_count": len(mesh_mismatches),
        "material_mismatch_count": len(material_mismatches),
        "mesh_mismatches": mesh_mismatches,
        "material_mismatches": material_mismatches,
    }


def main():
    payload = load_json(GAP_REPORT_PATH)
    records = list(payload.get("fog_sheet_actors", []))
    if len(records) != EXPECTED_FOG_COUNT:
        raise RuntimeError(
            "Unexpected fog inventory: expected {} got {}".format(
                EXPECTED_FOG_COUNT, len(records)
            )
        )
    if any(record.get("actor_type") != "WBP_FogSheet_C" for record in records):
        raise RuntimeError("Unexpected local/cinematic fog actor entered environment restore")
    if any(record.get("two_sided") for record in records):
        raise RuntimeError("Fog source Two Side inventory changed; rebuild material variants")

    plane_mesh, plane_imported, plane_import_paths = import_fog_plane()
    noise_texture, texture_imported, texture_import_paths = import_noise_texture()
    base_material, base_material_created = create_base_material(noise_texture)
    material_instances, mic_created, mic_updated = create_material_instances(
        records, base_material, noise_texture
    )

    backup_created = backup_map_once()
    level_subsystem, placement_result = place_fog(
        records, plane_mesh, material_instances
    )
    if placement_result["final_managed_actor_count"] != EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog actor count validation failed")
    if placement_result["mesh_mismatch_count"]:
        raise RuntimeError("Fog mesh validation failed")
    if placement_result["material_mismatch_count"]:
        raise RuntimeError("Fog material validation failed")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach map after fog restore")
    unreal.EditorAssetLibrary.save_directory(
        FOG_ROOT, only_if_is_dirty=False, recursive=True
    )

    report = {
        "status": "restored_preview",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_fog_actor_count": len(records),
        "source_plane": PLANE_SOURCE_PATH,
        "source_noise_texture": NOISE_SOURCE_PATH,
        "plane_mesh": plane_mesh.get_path_name(),
        "noise_texture": noise_texture.get_path_name(),
        "base_material": base_material.get_path_name(),
        "plane_imported": plane_imported,
        "texture_imported": texture_imported,
        "base_material_created": base_material_created,
        "preview_material_version": PREVIEW_MATERIAL_VERSION,
        "material_instance_created_count": mic_created,
        "material_instance_updated_count": mic_updated,
        "imported_object_paths": plane_import_paths + texture_import_paths,
        "preview_material_limits": {
            "source_dynamic_usd_is_opaque_stub": True,
            "original_parent_shader_export_missing": True,
            "global_opacity_scale": GLOBAL_OPACITY_SCALE,
            "emissive_scale": EMISSIVE_SCALE,
            "note": (
                "Transforms and extracted scalar parameters are source-authored; "
                "the translucent noise/edge-fade graph is a UE5 preview approximation."
            ),
        },
        "placement_result": placement_result,
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "WBP_FogSheet_Local_C cinematic-only actor",
            "Barehanded staggering/basic-movement protagonist scenes",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} fog={} created={} reused={} total={} report={}".format(
            report["status"],
            report["source_fog_actor_count"],
            placement_result["created_count"],
            placement_result["reused_count"],
            placement_result["final_total_actor_count"],
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
        unreal.log_error("KHAZAN_HEINMACH_FOG: " + str(exception))
        raise
