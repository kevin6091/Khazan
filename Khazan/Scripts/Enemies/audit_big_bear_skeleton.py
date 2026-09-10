"""Verify the canonical BigBear mesh skeleton in a fresh Unreal process.

This small preflight catches stale interrupted-import packages before the
animation batches are allowed to write runtime assets.
"""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = PROJECT / "Saved/ImportReports/BigBear_SkeletonPreflight_20260910.json"
ROOT = "/Game/_Art/Enemies/Shared/Beasts/BigBear"
MESH_PATH = ROOT + "/Meshes/SK_EN_BigBear"
SKELETON_PATH = ROOT + "/Skeletons/SKEL_EN_BigBear"
TEMP_ROOTS = [ROOT + "/_ImportStaging", ROOT + "/_ImportStaging79V1", ROOT + "/_UpgradeBackup"]
EXPECTED_HELPERS = {
    "Muscle_L_Eyeball2",
    "Muscle_R_Eyeball2",
    "B_Hair_01_01_Head2",
    "B_Eyelid_02_01_Head2",
    "B_Eyelid_01_01_Head2",
    "B_Ear_02_01_Head2",
    "B_Ear_01_01_Head2",
    "B_Hair_03_01_Neck2",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    report = {"status": "running"}
    try:
        mesh = unreal.load_asset(MESH_PATH)
        skeleton = unreal.load_asset(SKELETON_PATH)
        check(mesh is not None, "Missing canonical BigBear mesh")
        check(skeleton is not None, "Missing canonical BigBear skeleton")
        check(mesh.get_editor_property("skeleton") == skeleton, "Mesh uses a different skeleton")

        component = unreal.new_object(unreal.SkeletalMeshComponent)
        component.set_skinned_asset_and_update(mesh)
        bone_names = [str(component.get_bone_name(index)) for index in range(component.get_num_bones())]
        missing_helpers = sorted(EXPECTED_HELPERS.difference(bone_names))
        check(len(bone_names) == 79, f"Expected 79 reference bones, found {len(bone_names)}")
        check(not missing_helpers, "Missing animation helper bones: " + ", ".join(missing_helpers))

        registered_temp_assets = {
            path: [str(asset) for asset in unreal.EditorAssetLibrary.list_assets(path, recursive=True, include_folder=False)]
            for path in TEMP_ROOTS
        }
        check(
            not any(registered_temp_assets.values()),
            "Temporary assets remain registered: " + json.dumps(registered_temp_assets),
        )
        report.update(
            {
                "status": "passed",
                "mesh": MESH_PATH,
                "skeleton": SKELETON_PATH,
                "reference_bone_count": len(bone_names),
                "animation_helper_bones": sorted(EXPECTED_HELPERS),
                "temporary_asset_registry": registered_temp_assets,
            }
        )
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("BIG_BEAR_SKELETON_PREFLIGHT_PASSED", flush=True)


if __name__ == "__main__":
    main()
