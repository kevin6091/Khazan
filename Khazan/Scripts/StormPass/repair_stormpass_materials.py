"""Apply verified FModel LOD0 material semantics to StormPass root props."""

from __future__ import annotations

import importlib.util
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SHARED_SCRIPT = os.path.join(
    PROJECT_ROOT, "Scripts", "HeinMach", "repair_heinmach_materials.py"
)
SCOPE_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Metadata",
    "StormPass_SourceScope.json",
)
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/StormPass/Maps/"
    "L_StormPass_Environment_PreMaterialRebuild"
)


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_material_repair", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared material repair")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create StormPass pre-material backup")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def main():
    shared = load_shared()
    scope = load_json(SCOPE_PATH)
    backup_created = backup_map_once()
    shared.APPLY_CHANGES = True
    shared.UPDATE_MATERIAL_INSTANCES = False
    shared.MAP_PATH = MAP_PATH
    shared.CORRECTED_ROOT = (
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/SourceAssets"
    )
    shared.PLACEMENT_PATH = os.path.join(
        PROJECT_ROOT,
        "Content",
        "_Art",
        "Kazan",
        "Environment",
        "StormPass",
        "Metadata",
        "StormPass_ResolvedRootPlacements.json",
    )
    shared.REPORT_PATH = os.path.join(
        PROJECT_ROOT,
        "Saved",
        "ImportReports",
        "StormPass_Material_Surface_Repair.json",
    )
    shared.MANAGED_LABEL_PREFIX = "SP_Prop_"
    shared.ENVIRONMENT_LEVELS = set(scope.get("visual_levels", []))
    shared.EXPECTED_PLACEMENT_COUNT = 13050
    shared.EXPECTED_MESH_COUNT = 271
    shared.log = lambda message: unreal.log(
        "KHAZAN_STORMPASS_MATERIAL_REPAIR: " + str(message)
    )
    shared.main()
    report = shared.load_json(shared.REPORT_PATH)
    report["backup_map_path"] = BACKUP_MAP_PATH
    report["backup_created"] = backup_created
    shared.write_json(shared.REPORT_PATH, report)
    return report


if __name__ == "__main__":
    main()
