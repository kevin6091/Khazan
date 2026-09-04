"""Import the environment-only HeinMach USD stage into Unreal Engine 5.

Run this script with UnrealEditor-Cmd. It composes only geometry-related level
layers, imports their meshes/materials/textures, and saves a reconstructed map.
Cinematic, character, spawn, audio, BGM, position, spline, and precache layers
are deliberately not included.
"""

import json
import os
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_LEVEL_ROOT = os.path.join(
    FMODEL_ROOT,
    "BBQ",
    "Content",
    "_Kazan_",
    "Level",
    "HeinMach",
)
STAGE_NAME = "HeinMach_EnvironmentOnly"
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
DESTINATION_ROOT = "/Game/_Art/Kazan/Environment/HeinMach/Imported"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportReports", "HeinMach_Environment_Import.json"
)

# Keep the order from HeinMach_All.usda. Earlier entries are stronger USD layers.
ENVIRONMENT_LAYERS = (
    "HeinMach_Light",
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
)

# These are intentionally absent from the generated stage. In particular, every
# HeinMach_Cine_* layer is excluded so the barehanded/staggering movement scene
# cannot enter the reconstructed level through a cinematic sublayer.
EXCLUDED_LAYERS = (
    "HeinMach_BGM",
    "HeinMach_Cine_BossEnd",
    "HeinMach_Cine_BossStart",
    "HeinMach_Cine_LevelEvent",
    "HeinMach_Cine_LevelEvent02",
    "HeinMach_Cine_Opening01",
    "HeinMach_Cine_Opening02",
    "HeinMach_Cine_RevivePlayer",
    "HeinMach_MoveCustomSpline",
    "HeinMach_POS",
    "HeinMach_Sound",
    "HeinMach_Spawn_Main01",
    "Precache_HeinMach",
)


def log(message):
    unreal.log("KHAZAN_HEINMACH_IMPORT: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_IMPORT: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def source_path(layer_name):
    return os.path.join(SOURCE_LEVEL_ROOT, layer_name + ".usda")


def write_filtered_stage():
    if not os.path.isdir(SOURCE_LEVEL_ROOT):
        raise RuntimeError("HeinMach USD directory does not exist: " + SOURCE_LEVEL_ROOT)

    missing = [source_path(name) for name in ENVIRONMENT_LAYERS if not os.path.isfile(source_path(name))]
    if missing:
        raise RuntimeError("Missing required HeinMach USD layers: " + ", ".join(missing))

    sublayers = []
    for name in ENVIRONMENT_LAYERS:
        normalized = source_path(name).replace("\\", "/")
        sublayers.append("        @{}@".format(normalized))

    stage_text = "\n".join(
        [
            "#usda 1.0",
            "(",
            '    defaultPrim = "{}"'.format(STAGE_NAME),
            "    metersPerUnit = 0.01",
            '    upAxis = "Z"',
            "    subLayers = [",
            ",\n".join(sublayers),
            "    ]",
            ")",
            "",
            'def Scope "{}"'.format(STAGE_NAME),
            "{",
            "}",
            "",
        ]
    )

    lowered = stage_text.casefold()
    forbidden = [name for name in EXCLUDED_LAYERS if name.casefold() in lowered]
    if forbidden:
        raise RuntimeError("Generated stage contains excluded layers: " + ", ".join(forbidden))

    os.makedirs(os.path.dirname(GENERATED_STAGE_PATH), exist_ok=True)
    with open(GENERATED_STAGE_PATH, "w", encoding="utf-8", newline="\n") as stage_file:
        stage_file.write(stage_text)
    return [source_path(name) for name in ENVIRONMENT_LAYERS]


def load_or_create_map():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        if not subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load reconstruction map: " + MAP_PATH)
        return subsystem, False

    if not subsystem.new_level(MAP_PATH, False):
        raise RuntimeError("Failed to create reconstruction map: " + MAP_PATH)
    return subsystem, True


def scene_root_actors():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return [
        actor
        for actor in subsystem.get_all_level_actors()
        if actor and actor.get_actor_label() == STAGE_NAME
    ]


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def collect_stats():
    asset_paths = []
    if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION_ROOT):
        asset_paths = list(
            unreal.EditorAssetLibrary.list_assets(
                DESTINATION_ROOT, recursive=True, include_folder=False
            )
        )

    class_counts = {}
    static_mesh_paths = []
    for asset_path in asset_paths:
        class_name = asset_class_name(asset_path)
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
        if class_name == "StaticMesh":
            static_mesh_paths.append(asset_path)

    meshes_with_materials = 0
    assigned_material_slots = 0
    for asset_path in static_mesh_paths:
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not mesh:
            continue
        assigned = 0
        for static_material in mesh.get_editor_property("static_materials"):
            if static_material.get_editor_property("material_interface"):
                assigned += 1
        if assigned:
            meshes_with_materials += 1
            assigned_material_slots += assigned

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors())
    components = list(actor_subsystem.get_all_level_actors_components())
    static_mesh_components = [
        component for component in components if isinstance(component, unreal.StaticMeshComponent)
    ]
    populated_static_mesh_components = [
        component
        for component in static_mesh_components
        if component.get_editor_property("static_mesh")
    ]

    material_count = sum(
        count
        for name, count in class_counts.items()
        if name in ("Material", "MaterialInstanceConstant")
    )
    texture_count = sum(
        count for name, count in class_counts.items() if name.startswith("Texture")
    )
    return {
        "asset_count": len(asset_paths),
        "asset_class_counts": dict(sorted(class_counts.items())),
        "static_mesh_count": len(static_mesh_paths),
        "material_count": material_count,
        "texture_count": texture_count,
        "meshes_with_materials": meshes_with_materials,
        "assigned_material_slots": assigned_material_slots,
        "actor_count": len(actors),
        "stage_root_actor_count": len(scene_root_actors()),
        "static_mesh_component_count": len(static_mesh_components),
        "populated_static_mesh_component_count": len(populated_static_mesh_components),
    }


def is_valid_import(stats):
    return (
        stats["stage_root_actor_count"] == 1
        and stats["static_mesh_count"] > 0
        and stats["material_count"] > 0
        and stats["texture_count"] > 0
        and stats["meshes_with_materials"] > 0
        and stats["populated_static_mesh_component_count"] > 0
    )


def import_stage():
    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", True)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_only_used_materials", True)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", ["/"])
    options.set_editor_property("share_assets_for_identical_prims", True)
    options.set_editor_property("prim_path_folder_structure", False)
    options.set_editor_property("merge_identical_material_slots", True)
    options.set_editor_property("interpret_lods", True)
    options.set_editor_property("existing_actor_policy", unreal.ReplaceActorPolicy.APPEND)
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", GENERATED_STAGE_PATH)
    task.set_editor_property("destination_path", DESTINATION_ROOT)
    task.set_editor_property("destination_name", STAGE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths"))


def main():
    included_sources = write_filtered_stage()
    level_subsystem, map_created = load_or_create_map()
    before = collect_stats()

    report = {
        "destination_root": DESTINATION_ROOT,
        "excluded_layers": list(EXCLUDED_LAYERS),
        "generated_stage": GENERATED_STAGE_PATH,
        "included_layers": list(ENVIRONMENT_LAYERS),
        "included_sources": included_sources,
        "map_created": map_created,
        "map_path": MAP_PATH,
        "source_level_root": SOURCE_LEVEL_ROOT,
        "stats_before": before,
    }

    if is_valid_import(before):
        report["status"] = "skipped_existing_valid"
        report["stats_after"] = before
        report["imported_object_paths"] = []
        write_json(REPORT_PATH, report)
        log("RESULT skipped existing valid import report={}".format(REPORT_PATH))
        return

    if before["stage_root_actor_count"]:
        raise RuntimeError(
            "A partial HeinMach stage root already exists. Refusing to append a duplicate actor tree."
        )

    imported_paths = import_stage()
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save reconstruction map: " + MAP_PATH)
    unreal.EditorAssetLibrary.save_directory(
        DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
    )

    after = collect_stats()
    report["status"] = "imported" if is_valid_import(after) else "validation_failed"
    report["stats_after"] = after
    report["imported_object_paths"] = imported_paths
    write_json(REPORT_PATH, report)

    log(
        "RESULT status={} assets={} meshes={} materials={} textures={} actors={} "
        "mesh_components={} mapped_meshes={} report={}".format(
            report["status"],
            after["asset_count"],
            after["static_mesh_count"],
            after["material_count"],
            after["texture_count"],
            after["actor_count"],
            after["populated_static_mesh_component_count"],
            after["meshes_with_materials"],
            REPORT_PATH,
        )
    )
    if report["status"] != "imported":
        raise RuntimeError("HeinMach import validation failed; see " + REPORT_PATH)


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
