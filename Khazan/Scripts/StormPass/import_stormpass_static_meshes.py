"""Import the verified StormPass mesh library and place non-Fog root props."""

from __future__ import annotations

import importlib.util
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SHARED_SCRIPT = os.path.join(
    PROJECT_ROOT, "Scripts", "HeinMach", "import_heinmach_static_meshes.py"
)
METADATA_ROOT = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
)
ROOT_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_RootTemplateCoverage_Audit.json",
)
SOURCE_SCOPE_PATH = os.path.join(METADATA_ROOT, "StormPass_SourceScope.json")
PLACEMENT_PATH = os.path.join(METADATA_ROOT, "StormPass_ResolvedRootPlacements.json")
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_StaticMesh_Reconstruction.json",
)

MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreRootPropRebuild"
)
RECONSTRUCTED_ROOT = "/Game/_Art/Kazan/Environment/StormPass/Reconstructed"
DESTINATION_ROOT = RECONSTRUCTED_ROOT + "/SourceAssets"
STAGE_NAME = "StormPass_StaticMeshLibrary"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
EXPECTED_PLACEMENT_COUNT = 13050
EXPECTED_MESH_COUNT = 271


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_static_mesh_helpers", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared static-mesh reconstruction helpers")
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


def main():
    audit = load_json(ROOT_AUDIT_PATH)
    scope = load_json(SOURCE_SCOPE_PATH)
    summary = audit.get("summary", {})
    if (
        int(summary.get("resolved_visible_root_placement_count", -1))
        != EXPECTED_PLACEMENT_COUNT
        or int(summary.get("resolved_unique_static_mesh_count", -1))
        != EXPECTED_MESH_COUNT
        or int(summary.get("missing_usd_static_mesh_count", -1)) != 0
        or int(summary.get("fog_excluded_root_mesh_count", -1)) != 53
    ):
        raise RuntimeError("StormPass root-template audit is not ready for import")

    shared = load_shared()
    shared.MAP_PATH = MAP_PATH
    shared.BACKUP_MAP_PATH = BACKUP_MAP_PATH
    shared.RECONSTRUCTED_ROOT = RECONSTRUCTED_ROOT
    shared.DESTINATION_ROOT = DESTINATION_ROOT
    shared.STAGE_NAME = STAGE_NAME
    shared.GENERATED_STAGE_PATH = GENERATED_STAGE_PATH
    shared.PLACEMENT_PATH = PLACEMENT_PATH
    shared.REPORT_PATH = REPORT_PATH
    shared.MANAGED_LABEL_PREFIX = "SP_Prop_"
    shared.MANAGED_FOLDER_ROOT = "StormPass/Reconstructed/Props"
    shared.ENVIRONMENT_LEVELS = set(scope.get("visual_levels", []))
    shared.EXPECTED_PLACEMENT_COUNT = EXPECTED_PLACEMENT_COUNT
    shared.EXPECTED_MESH_COUNT = EXPECTED_MESH_COUNT
    shared.TRANSFORM_OVERRIDES = {}
    shared.filter_excluded_placements = lambda placements: list(placements)
    shared.restoration_exclusion_labels = lambda category="root_prop": set()
    shared.log = lambda message: unreal.log(
        "KHAZAN_STORMPASS_PROPS: " + str(message)
    )
    shared.error = lambda message: unreal.log_error(
        "KHAZAN_STORMPASS_PROPS: " + str(message)
    )

    def backup_map_once():
        if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            return False
        if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
            return False
        if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
            raise RuntimeError("Failed to create StormPass root-prop backup map")
        unreal.EditorAssetLibrary.save_asset(
            BACKUP_MAP_PATH, only_if_is_dirty=False
        )
        return True

    def load_or_create_map():
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            if not subsystem.load_level(MAP_PATH):
                raise RuntimeError("Failed to load StormPass environment map")
        elif not subsystem.new_level(MAP_PATH, False):
            raise RuntimeError("Failed to create StormPass environment map")
        return subsystem

    shared.backup_map_once = backup_map_once
    shared.load_map = load_or_create_map
    shared.main()

    report = load_json(REPORT_PATH)
    report["level"] = "StormPass"
    report["source_root_audit"] = ROOT_AUDIT_PATH
    report["source_scope"] = SOURCE_SCOPE_PATH
    report["fog_state"] = "deferred_until_final_pass"
    report["excluded_content"] = [
        "All Fog/Mist actors and Fog materials (deferred)",
        "Cinema, character, spawn, quest, navigation, sound, BGM, and POS layers",
        "Gameplay logic and source code",
    ]
    write_json(REPORT_PATH, report)
    unreal.log(
        "KHAZAN_STORMPASS_PROPS: VERIFIED meshes={} placements={} map={} report={}".format(
            EXPECTED_MESH_COUNT, EXPECTED_PLACEMENT_COUNT, MAP_PATH, REPORT_PATH
        )
    )
    return report


if __name__ == "__main__":
    main()
