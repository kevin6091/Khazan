"""Dry-run StormPass LOD0 material-slot correlation without changing assets."""

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


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_material_binding_audit", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared material mapping helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def main():
    shared = load_shared()
    scope = load_json(SCOPE_PATH)
    shared.APPLY_CHANGES = False
    shared.MAP_PATH = (
        "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
    )
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
        "StormPass_MaterialBinding_Audit.json",
    )
    shared.MANAGED_LABEL_PREFIX = "SP_Prop_"
    shared.ENVIRONMENT_LEVELS = set(scope.get("visual_levels", []))
    shared.EXPECTED_PLACEMENT_COUNT = 13050
    shared.EXPECTED_MESH_COUNT = 271
    shared.log = lambda message: unreal.log(
        "KHAZAN_STORMPASS_MATERIAL_AUDIT: " + str(message)
    )
    shared.main()


if __name__ == "__main__":
    main()
