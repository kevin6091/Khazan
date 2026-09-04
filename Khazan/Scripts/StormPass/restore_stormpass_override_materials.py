"""Rebuild and apply StormPass actor-only material overrides from FModel."""

from __future__ import annotations

import importlib.util
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SHARED_SCRIPT = os.path.join(
    PROJECT_ROOT,
    "Scripts",
    "HeinMach",
    "restore_heinmach_inherited_override_materials.py",
)
ENGINE_BASIC_SHAPE = "Engine/Content/BasicShapes/BasicShapeMaterial"


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_override_material_restoration", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared override-material restoration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    report_root = os.path.join(PROJECT_ROOT, "Saved", "ImportReports")
    shared.MAP_PATH = (
        "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
    )
    shared.BACKUP_MAP_PATH = (
        "/Game/_Art/Kazan/Environment/StormPass/Maps/"
        "L_StormPass_Environment_PreOverrideMaterialRebuild"
    )
    shared.CORRECTED_ROOT = (
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/SourceAssets"
    )
    shared.OVERRIDE_ROOT = (
        "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials"
    )
    shared.MATERIAL_ROOT = shared.OVERRIDE_ROOT + "/ActorOverrides/Materials"
    shared.TEXTURE_ROOT = shared.OVERRIDE_ROOT + "/Textures"
    shared.ROOT_AUDIT_PATH = os.path.join(
        report_root, "StormPass_RootTemplateCoverage_Audit.json"
    )
    shared.SOURCE_AUDIT_PATH = os.path.join(
        report_root, "StormPass_OverrideSource_Audit.json"
    )
    shared.ROOT_RESTORATION_PATH = os.path.join(
        report_root, "StormPass_StaticMesh_Reconstruction.json"
    )
    shared.REPORT_PATH = os.path.join(
        report_root, "StormPass_OverrideMaterial_Restoration.json"
    )
    shared.EXPECTED_PLACEMENT_COUNT = 13050
    shared.EXPECTED_MESH_COUNT = 271
    shared.EXPECTED_REBUILT_MATERIAL_COUNT = 93
    shared.EXPECTED_REBUILT_REFERENCE_COUNT = 10109
    shared.EXPECTED_FOG_COUNT = 0
    shared.MANAGED_LABEL_PREFIX = "SP_Prop_"
    shared.FOG_LABEL_PREFIX = "SP_Fog_"
    shared.SKIP_REBUILD_PACKAGES = {ENGINE_BASIC_SHAPE}
    shared.UPDATE_MATERIAL_INSTANCES = False
    shared.USE_LEGACY_TEXTURE_FACTORY = True
    shared.EXTERNAL_MATERIAL_PATHS = {
        ENGINE_BASIC_SHAPE: (
            "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"
        )
    }
    shared.TRANSFORM_OVERRIDES = {}
    shared.filter_excluded_placements = lambda placements: list(placements)
    shared.repair.CORRECTED_ROOT = shared.CORRECTED_ROOT
    shared.repair.FMODEL_ROOT = shared.FMODEL_ROOT
    shared.log = lambda message: unreal.log(
        "KHAZAN_STORMPASS_OVERRIDE_MATERIALS: " + str(message)
    )
    shared.main()


if __name__ == "__main__":
    main()
