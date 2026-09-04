"""Repair the currently imported HeinMach environment preview map.

The FModel world USD keeps the two landscape meshes, but it does not recreate
Khazan's custom light actors and the exported landscape material is missing.
This script makes a one-time map backup, builds a practical terrain preview
material from the extracted soil textures, assigns it to both landscape mesh
components, and reconstructs the non-cinematic HeinMach_Light actors from the
preserved FModel property metadata.
"""

import json
import os
import traceback

import unreal


MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_BeforeReconstruction"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed"
MATERIAL_FOLDER = RECONSTRUCTED_ROOT + "/Materials"
TERRAIN_MATERIAL_PATH = MATERIAL_FOLDER + "/M_HeinMach_Terrain_Preview"
IMPORTED_TEXTURE_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Imported/"
    "HeinMach_EnvironmentOnly/Textures"
)
TERRAIN_BASE_COLOR_PATH = IMPORTED_TEXTURE_ROOT + "/T_WT_VFS_Soil_Tile_001_D"
TERRAIN_NORMAL_PATH = IMPORTED_TEXTURE_ROOT + "/T_WT_VFS_Soil_Tile_001_N"
LEVEL_DATA_PATH = os.path.join(
    unreal.Paths.project_content_dir(),
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_LevelData.json",
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Environment_Reconstruction.json",
)

SOURCE_LIGHT_LEVEL = "HeinMach_Light"
SOURCE_LIGHT_LABEL_PREFIX = "HM_SourceLight_"
SOURCE_LIGHT_FOLDER = "HeinMach/Reconstructed/SourceLights"
PREVIEW_LIGHT_FOLDER = "HeinMach/Reconstructed/PreviewLighting"
LANDSCAPE_MESH_NAMES = {"SM_RootComponent", "SM_RootComponent0"}
SOURCE_INTENSITY_TO_LUMENS = 750.0


def log(message):
    unreal.log("KHAZAN_HEINMACH_RECONSTRUCT: " + str(message))


def warning(message):
    unreal.log_warning("KHAZAN_HEINMACH_RECONSTRUCT: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_RECONSTRUCT: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def safe_set(obj, property_name, value, failures=None):
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception as exception:
        if failures is not None:
            failures.append(
                {
                    "object": obj.get_name() if hasattr(obj, "get_name") else str(obj),
                    "property": property_name,
                    "error": str(exception),
                }
            )
        return False


def load_json(path):
    if not os.path.isfile(path):
        raise RuntimeError("Required metadata does not exist: " + path)
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def backup_map_once():
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError("HeinMach map does not exist: " + MAP_PATH)
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH)
    if not duplicated:
        raise RuntimeError("Failed to create map backup: " + BACKUP_MAP_PATH)
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def load_map():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load map: " + MAP_PATH)
    return level_subsystem


def load_required_asset(asset_path):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        raise RuntimeError("Required Unreal asset does not exist: " + asset_path)
    return asset


def create_terrain_material():
    existing = unreal.EditorAssetLibrary.load_asset(TERRAIN_MATERIAL_PATH)
    if existing:
        return existing, False

    if not unreal.EditorAssetLibrary.does_directory_exist(MATERIAL_FOLDER):
        unreal.EditorAssetLibrary.make_directory(MATERIAL_FOLDER)

    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_HeinMach_Terrain_Preview",
        MATERIAL_FOLDER,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        raise RuntimeError("Failed to create terrain preview material")

    base_color = load_required_asset(TERRAIN_BASE_COLOR_PATH)
    normal = load_required_asset(TERRAIN_NORMAL_PATH)
    material_library = unreal.MaterialEditingLibrary

    texcoord = material_library.create_material_expression(
        material, unreal.MaterialExpressionTextureCoordinate, -700, 0
    )
    texcoord.set_editor_property("u_tiling", 8.0)
    texcoord.set_editor_property("v_tiling", 8.0)

    base_sample = material_library.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, -430, -160
    )
    base_sample.set_editor_property("texture", base_color)
    normal_sample = material_library.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, -430, 80
    )
    normal_sample.set_editor_property("texture", normal)
    normal_sample.set_editor_property(
        "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    )
    roughness = material_library.create_material_expression(
        material, unreal.MaterialExpressionConstant, -200, 260
    )
    roughness.set_editor_property("r", 0.82)

    material_library.connect_material_expressions(texcoord, "", base_sample, "Coordinates")
    material_library.connect_material_expressions(texcoord, "", normal_sample, "Coordinates")
    material_library.connect_material_property(
        base_sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    )
    material_library.connect_material_property(
        normal_sample, "RGB", unreal.MaterialProperty.MP_NORMAL
    )
    material_library.connect_material_property(
        roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
    )
    material_library.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material, True


def assign_terrain_material(material):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    components = actor_subsystem.get_all_level_actors_components()
    assignments = []
    for component in components:
        if not isinstance(component, unreal.StaticMeshComponent):
            continue
        mesh = component.get_editor_property("static_mesh")
        if not mesh or mesh.get_name() not in LANDSCAPE_MESH_NAMES:
            continue
        slot_count = max(1, len(mesh.get_editor_property("static_materials")))
        for slot_index in range(slot_count):
            component.set_material(slot_index, material)
        assignments.append(
            {
                "component": component.get_path_name(),
                "mesh": mesh.get_path_name(),
                "slot_count": slot_count,
            }
        )
    if len(assignments) != 2:
        raise RuntimeError(
            "Expected two landscape mesh components but assigned {}".format(len(assignments))
        )
    return assignments


def actor_by_label(actors, label):
    for actor in actors:
        if actor and actor.get_actor_label() == label:
            return actor
    return None


def set_actor_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        safe_set(actor, "folder_path", folder)


def spawn_or_reuse(actor_class, label, location, rotation, actors):
    actor = actor_by_label(actors, label)
    created = False
    if not actor:
        actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
            actor_class, location, rotation
        )
        if not actor:
            raise RuntimeError("Failed to spawn actor: " + label)
        actor.set_actor_label(label, mark_dirty=True)
        actors.append(actor)
        created = True
    actor.set_actor_location(location, False, False)
    actor.set_actor_rotation(rotation, False)
    return actor, created


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


def source_light_component_data(record):
    for component in record.get("components", []):
        if "LightComponent" in str(component.get("type", "")):
            properties = component.get("properties", {})
            return properties if isinstance(properties, dict) else {}
    return {}


def apply_source_light(component, source, property_failures):
    source_intensity = float(source.get("Intensity", 2.0))
    lumens = max(500.0, min(50000.0, source_intensity * SOURCE_INTENSITY_TO_LUMENS))
    safe_set(component, "mobility", unreal.ComponentMobility.MOVABLE, property_failures)
    safe_set(component, "intensity", lumens, property_failures)
    safe_set(
        component,
        "attenuation_radius",
        float(source.get("AttenuationRadius", 2000.0)),
        property_failures,
    )
    safe_set(
        component,
        "volumetric_scattering_intensity",
        float(source.get("VolumetricScatteringIntensity", 1.0)),
        property_failures,
    )
    safe_set(component, "specular_scale", float(source.get("SpecularScale", 0.0)), property_failures)
    safe_set(component, "cast_shadows", bool(source.get("CastShadows", False)), property_failures)
    use_inverse_squared = bool(source.get("bUseInverseSquaredFalloff", True))
    safe_set(
        component,
        "use_inverse_squared_falloff",
        use_inverse_squared,
        property_failures,
    )
    if "LightFalloffExponent" in source:
        safe_set(
            component,
            "light_falloff_exponent",
            float(source["LightFalloffExponent"]),
            property_failures,
        )
    for source_name, property_name in (
        ("MaxDrawDistance", "max_draw_distance"),
        ("MaxDistanceFadeRange", "max_distance_fade_range"),
        ("IndirectLightingIntensity", "indirect_lighting_intensity"),
    ):
        if source_name in source:
            safe_set(
                component,
                property_name,
                float(source[source_name]),
                property_failures,
            )

    color = source.get("LightColor", {})
    source_color = unreal.Color(
        r=int(color.get("R", 255)),
        g=int(color.get("G", 255)),
        b=int(color.get("B", 255)),
        a=int(color.get("A", 255)),
    )
    try:
        # FModel serializes ULightComponent::LightColor as an sRGB FColor.
        # Writing normalized channels through SetLightColor(..., True) applies
        # a second transfer curve (for example 216 became 237).  Preserve the
        # source byte values directly so the engine performs one conversion at
        # render time, exactly as it does for the original property.
        component.set_editor_property("light_color", source_color)
    except Exception as exception:
        property_failures.append(
            {"object": component.get_name(), "property": "light_color", "error": str(exception)}
        )

    if isinstance(component, unreal.SpotLightComponent):
        safe_set(
            component,
            "outer_cone_angle",
            float(source.get("OuterConeAngle", 44.0)),
            property_failures,
        )

    return lumens


def reconstruct_source_lights(level_data, actors):
    source_lights = [
        record
        for record in level_data.get("lights", [])
        if record.get("source_level") == SOURCE_LIGHT_LEVEL
        and record.get("actor_type") in ("xxPointLight", "xxSpotLight")
    ]
    if len(source_lights) != 89:
        raise RuntimeError(
            "Expected 89 non-cinematic HeinMach source lights but found {}".format(
                len(source_lights)
            )
        )

    created_count = 0
    reused_count = 0
    point_count = 0
    spot_count = 0
    property_failures = []
    for record in source_lights:
        is_spot = record.get("actor_type") == "xxSpotLight"
        actor_class = unreal.SpotLight if is_spot else unreal.PointLight
        transform = record.get("transform", {})
        label = SOURCE_LIGHT_LABEL_PREFIX + str(record.get("actor_name", "Unknown"))
        actor, created = spawn_or_reuse(
            actor_class,
            label,
            vector_from_transform(transform),
            rotator_from_transform(transform),
            actors,
        )
        set_actor_folder(actor, SOURCE_LIGHT_FOLDER)
        component_class = unreal.SpotLightComponent if is_spot else unreal.PointLightComponent
        component = actor.get_component_by_class(component_class)
        if not component:
            raise RuntimeError("Spawned light has no component: " + label)
        apply_source_light(component, source_light_component_data(record), property_failures)
        if created:
            created_count += 1
        else:
            reused_count += 1
        if is_spot:
            spot_count += 1
        else:
            point_count += 1

    return {
        "source_count": len(source_lights),
        "point_count": point_count,
        "spot_count": spot_count,
        "created_count": created_count,
        "reused_count": reused_count,
        "property_failures": property_failures,
    }


def configure_preview_lighting(actors):
    created_labels = []
    property_failures = []
    world_center = unreal.Vector(x=10000.0, y=2000.0, z=8000.0)

    sun = actor_by_label(actors, "HM_PreviewSun")
    if not sun:
        for actor in actors:
            if isinstance(actor, unreal.DirectionalLight):
                sun = actor
                sun.set_actor_label("HM_PreviewSun", mark_dirty=True)
                break
    if not sun:
        sun, created = spawn_or_reuse(
            unreal.DirectionalLight,
            "HM_PreviewSun",
            world_center,
            unreal.Rotator(pitch=-38.0, yaw=-32.0, roll=0.0),
            actors,
        )
        if created:
            created_labels.append("HM_PreviewSun")
    sun.set_actor_rotation(unreal.Rotator(pitch=-38.0, yaw=-32.0, roll=0.0), False)
    set_actor_folder(sun, PREVIEW_LIGHT_FOLDER)
    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    safe_set(sun_component, "mobility", unreal.ComponentMobility.MOVABLE, property_failures)
    safe_set(sun_component, "intensity", 4.0, property_failures)
    safe_set(sun_component, "atmosphere_sun_light", True, property_failures)
    safe_set(sun_component, "cast_shadows", True, property_failures)
    try:
        sun_component.set_light_color(unreal.LinearColor(0.82, 0.90, 1.0, 1.0), False)
    except Exception as exception:
        property_failures.append(
            {"object": sun_component.get_name(), "property": "light_color", "error": str(exception)}
        )

    sky, created = spawn_or_reuse(
        unreal.SkyLight,
        "HM_PreviewSkyLight",
        world_center,
        unreal.Rotator(),
        actors,
    )
    if created:
        created_labels.append("HM_PreviewSkyLight")
    set_actor_folder(sky, PREVIEW_LIGHT_FOLDER)
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    safe_set(sky_component, "mobility", unreal.ComponentMobility.MOVABLE, property_failures)
    safe_set(sky_component, "real_time_capture", True, property_failures)
    safe_set(sky_component, "intensity", 1.0, property_failures)

    atmosphere, created = spawn_or_reuse(
        unreal.SkyAtmosphere,
        "HM_PreviewSkyAtmosphere",
        world_center,
        unreal.Rotator(),
        actors,
    )
    if created:
        created_labels.append("HM_PreviewSkyAtmosphere")
    set_actor_folder(atmosphere, PREVIEW_LIGHT_FOLDER)

    post_process, created = spawn_or_reuse(
        unreal.PostProcessVolume,
        "HM_PreviewPostProcess",
        world_center,
        unreal.Rotator(),
        actors,
    )
    if created:
        created_labels.append("HM_PreviewPostProcess")
    set_actor_folder(post_process, PREVIEW_LIGHT_FOLDER)
    safe_set(post_process, "unbound", True, property_failures)
    settings = post_process.get_editor_property("settings")
    safe_set(settings, "override_auto_exposure_bias", True, property_failures)
    safe_set(settings, "auto_exposure_bias", 0.75, property_failures)
    safe_set(post_process, "settings", settings, property_failures)

    return {
        "created_labels": created_labels,
        "property_failures": property_failures,
    }


def main():
    level_data = load_json(LEVEL_DATA_PATH)
    backup_created = backup_map_once()
    level_subsystem = load_map()
    actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())

    terrain_material, material_created = create_terrain_material()
    terrain_assignments = assign_terrain_material(terrain_material)
    source_lights = reconstruct_source_lights(level_data, actors)
    preview_lighting = configure_preview_lighting(actors)

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save reconstructed map: " + MAP_PATH)
    unreal.EditorAssetLibrary.save_directory(
        RECONSTRUCTED_ROOT, only_if_is_dirty=False, recursive=True
    )

    all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    final_source_light_count = sum(
        actor.get_actor_label().startswith(SOURCE_LIGHT_LABEL_PREFIX) for actor in all_actors if actor
    )
    report = {
        "status": "reconstructed",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "terrain_material_path": TERRAIN_MATERIAL_PATH,
        "terrain_material_created": material_created,
        "terrain_assignments": terrain_assignments,
        "source_lights": source_lights,
        "preview_lighting": preview_lighting,
        "final_actor_count": len(all_actors),
        "final_source_light_count": final_source_light_count,
        "known_source_limitations": [
            "Original WLM_HeinMach/WLM_HeinMach2 materials and landscape layer weights were not present in the FModel export.",
            "The terrain material is a visible preview reconstruction using the extracted VFS soil textures.",
            "Source custom-light intensity values were converted to UE lumens for a usable UE5 preview.",
        ],
        "excluded_content": [
            "All HeinMach_Cine_* layers",
            "Character/spawn layers",
            "Barehanded staggering movement scene",
        ],
    }
    if final_source_light_count != 89:
        report["status"] = "validation_failed"
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} terrain_components={} source_lights={} actors={} report={}".format(
            report["status"],
            len(terrain_assignments),
            final_source_light_count,
            len(all_actors),
            REPORT_PATH,
        )
    )
    if report["status"] != "reconstructed":
        raise RuntimeError("HeinMach reconstruction validation failed; see " + REPORT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "error": str(exception),
            "status": "failed",
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        error(str(exception))
        error(failure["traceback"])
        raise
