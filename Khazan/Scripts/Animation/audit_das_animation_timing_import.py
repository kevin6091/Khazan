"""Fresh-process audit for the complete DAS animation timing restoration."""

from __future__ import annotations

import json
import pathlib
import runpy
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_CompositeExact60PipelineFinalAudit_20260917.json"
PLAYBACK_ROOT = "/Game/_Art/Player/Animation/Playback/DualAxeSword"
PLAYER_ANIM_BLUEPRINT = "/Game/_Art/Player/Character/Bluprints/ABP_Player"
ROWS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
INVENTORY = json.loads(
    (
        PROJECT
        / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"
    ).read_text(encoding="utf-8")
)
BACKUP = json.loads(
    (
        PROJECT / "Saved/ImportReports/Khazan_DAS_AnimationBackup_20260916.json"
    ).read_text(encoding="utf-8")
)
H = runpy.run_path(
    str(PROJECT / "Scripts/Animation/import_das_animation_timing.py"),
    run_name="das_animation_import_helpers",
)
def write(value) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def dependency_closure(registry, root: str, options) -> set[str]:
    pending = [root]
    visited = set()
    while pending:
        package = pending.pop()
        if package in visited:
            continue
        visited.add(package)
        for dependency in registry.get_dependencies(package, options):
            value = str(dependency)
            if value.startswith("/Game/") and value not in visited:
                pending.append(value)
    return visited


def verify_protected_hashes() -> int:
    count = 0
    for package in BACKUP["protected_locomotion_packages"]:
        for file in package["files"]:
            path = PROJECT / file["path"]
            if not path.is_file() or H["sha256"](path) != file["sha256"]:
                raise RuntimeError("Protected locomotion changed: " + file["path"])
            count += 1
    return count


def verify_backup_copies() -> int:
    count = 0
    for package in BACKUP["mutated_packages"]:
        for file in package["files"]:
            backup = pathlib.Path(file["backup_path"])
            if not backup.is_file() or H["sha256"](backup) != file["sha256"]:
                raise RuntimeError("Mutation backup changed: " + str(backup))
            count += 1
    return count


def verify_non_bone_preservation(row: dict, sequence) -> None:
    if row["operation"] != "replace_existing":
        return
    original = H["expected_non_bone_contract"](row["destination"])
    current = H["current_non_bone_contract"](sequence)
    skeleton_changed = original["skeleton"] != row["skeleton_destination"]
    if skeleton_changed:
        # The four auxiliary weapon clips were incorrectly assigned to the
        # character skeleton. Their old assets contained no authored events,
        # curves, markers, referencers, or metadata; their package paths remain.
        inventory = H["INVENTORY_BY_ASSET"][row["destination"]]
        if (
            inventory.get("referencers")
            or original["notify_events"]
            or original["float_curve_count"]
            or original["transform_curve_count"]
            or any(original["sync_markers"].values())
            or original["metadata"]
        ):
            raise RuntimeError("Unexpected non-bone data on skeleton-corrected asset")
        return
    for key in (
        "skeleton",
        "notify_tracks",
        "notify_events",
        "float_curve_count",
        "transform_curve_count",
        "import_filenames",
    ):
        if current[key] != original[key]:
            raise RuntimeError(f"Final non-bone preservation failed for {key}: {row['destination']}")
    expected_markers = H["expected_sync_markers_after"](row, original)
    if not H["sync_markers_equal"](current["sync_markers"], expected_markers):
        raise RuntimeError(
            "Final sync-marker preservation/remap failed: " + row["destination"]
        )
    for key, value in original["metadata"].items():
        if current["metadata"].get(key) != value:
            raise RuntimeError(
                f"Final metadata preservation failed for {key}: {row['destination']}"
            )


def verify_root_bake_contract(row: dict) -> tuple[int, list[float]]:
    if row["kind"] != "CompositePlayback":
        return 0, [0.0, 0.0]
    root_bake = row.get("root_motion_bake")
    is_player = row["skeleton_destination"].endswith("/SK_Player")
    if not is_player:
        if root_bake is not None:
            raise RuntimeError(
                "Auxiliary weapon Composite unexpectedly has player root bake: "
                + row["destination"]
            )
        return 0, [0.0, 0.0]
    if not root_bake:
        raise RuntimeError(
            "Player Composite has no continuous root-motion bake: " + row["destination"]
        )
    if any(
        abs(float(value)) >= 1.0e-7
        for value in root_bake["initial_baked_root_translation"]
    ):
        raise RuntimeError("Player Composite root was not rebased: " + row["destination"])
    errors = [
        float(value) for value in root_bake["maximum_baked_interval_contract_error"]
    ]
    if errors[0] >= 0.0001 or errors[1] >= 1.0e-10:
        raise RuntimeError(
            "Player Composite root-motion contract error: " + row["destination"]
        )
    return int(root_bake["corrected_interval_count"]), errors


def verify_root_translation_scale_contract(row: dict, skeleton):
    is_player_root_motion = (
        row["skeleton_destination"].endswith("/SK_Player")
        and bool(row["properties"].get("bEnableRootMotion", False))
    )
    if not is_player_root_motion:
        return None
    adapter = row["topology_adapter"]
    inserted_ref = skeleton.get_reference_pose().get_bone_pose(
        adapter["inserted_root_bone"]
    )
    reference_scale = [
        float(value) for value in H["transform_values"](inserted_ref)[7:10]
    ]
    if (
        min(reference_scale) <= 0.0
        or max(reference_scale) - min(reference_scale) >= 1.0e-9
    ):
        raise RuntimeError(
            "Player inserted root reference scale is not positive and uniform: "
            + row["destination"]
        )
    inserted_root_scale = reference_scale[0]
    translation_scale = float(
        adapter.get("root_motion_translation_scale", 1.0)
    )
    if abs(translation_scale - 1.0 / inserted_root_scale) >= 1.0e-12:
        raise RuntimeError(
            "Player Root Motion compensation is not the reciprocal of the inserted "
            "root reference scale: "
            + row["destination"]
        )
    required_root_version = (
        H["COMPOSITE_VERSION"]
        if row["kind"] == "CompositePlayback"
        else H["ROOT_MOTION_VERSION"]
    )
    if H["target_version"](row) != required_root_version:
        raise RuntimeError(
            "Normalized player Root Motion has wrong target version: "
            + row["destination"]
        )
    return inserted_root_scale


def main() -> None:
    result = {
        "schema": 1,
        "status": "running",
        "version": H["VERSION"],
        "assets": [],
        "failures": [],
    }
    try:
        if BACKUP.get("status") != "passed":
            raise RuntimeError("Backup contract is not passed")
        result["backup_files_verified"] = verify_backup_copies()
        result["protected_locomotion_files_verified"] = verify_protected_hashes()

        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.search_all_assets(True)
        options = unreal.AssetRegistryDependencyOptions(
            include_hard_package_references=True,
            include_soft_package_references=True,
            include_searchable_names=False,
            include_soft_management_references=True,
            include_hard_management_references=True,
        )
        closure = dependency_closure(registry, PLAYER_ANIM_BLUEPRINT, options)
        relevant_prefixes = (
            "/Game/_Art/Player/Animation/Weapons/DualAxeSword/",
            "/Game/_Art/Player/Animation/InGame/DAS/",
            "/Game/_Art/Player/Animation/Locomotion/Runtime/DualAxeSword/",
            PLAYBACK_ROOT + "/",
        )
        current_locomotion = []
        for package in sorted(closure):
            if not package.startswith(relevant_prefixes) or not unreal.EditorAssetLibrary.does_asset_exist(package):
                continue
            asset = unreal.load_asset(package)
            if isinstance(asset, unreal.AnimSequence):
                current_locomotion.append(package)
        if current_locomotion != INVENTORY["current_locomotion_dependencies"]:
            raise RuntimeError("The current locomotion dependency set changed")
        result["current_locomotion_dependencies"] = current_locomotion

        expected_playback = {
            row["destination"] for row in ROWS if row["kind"] == "CompositePlayback"
        }
        actual_playback = {
            str(data.package_name)
            for data in registry.get_assets_by_path(
                PLAYBACK_ROOT, recursive=True, include_only_on_disk_assets=True
            )
            if str(data.asset_class_path.asset_name) == "AnimSequence"
        }
        if actual_playback != expected_playback:
            raise RuntimeError(
                "Generated playback inventory differs: missing="
                + repr(sorted(expected_playback - actual_playback))
                + " extra="
                + repr(sorted(actual_playback - expected_playback))
            )

        maxima = [0.0, 0.0, 0.0]
        topology_maxima = [0.0, 0.0, 0.0]
        player_composite_root_bakes = 0
        corrected_root_intervals = 0
        maximum_root_bake_error = [0.0, 0.0]
        player_root_motion_normalized_assets = 0
        player_inserted_root_reference_scales = set()
        for index, row in enumerate(ROWS):
            sequence = H["load"](row["destination"])
            skeleton = H["load"](row["skeleton_destination"])
            mesh = H["load"](row["mesh_destination"])
            output_bones, expected, topology_error = H["adapted_pose"](
                row, skeleton, mesh
            )
            entry = H["verify"](
                row, sequence, expected, output_bones, topology_error
            )
            verify_non_bone_preservation(row, sequence)
            corrected, root_bake_error = verify_root_bake_contract(row)
            inserted_root_scale = verify_root_translation_scale_contract(row, skeleton)
            if inserted_root_scale is not None:
                player_root_motion_normalized_assets += 1
                player_inserted_root_reference_scales.add(inserted_root_scale)
            if row["kind"] == "CompositePlayback" and row.get("root_motion_bake"):
                player_composite_root_bakes += 1
            corrected_root_intervals += corrected
            maximum_root_bake_error = [
                max(maximum_root_bake_error[axis], root_bake_error[axis])
                for axis in range(2)
            ]
            result["assets"].append(entry)
            maxima = [
                max(maxima[0], entry["max_position_error_cm"]),
                max(maxima[1], entry["max_quaternion_component_error"]),
                max(maxima[2], entry["max_scale_error"]),
            ]
            topology_maxima = [
                max(topology_maxima[value], topology_error[value]) for value in range(3)
            ]
            if (index + 1) % 25 == 0:
                print("DAS_FINAL_AUDIT", index + 1, "/", len(ROWS), flush=True)

        result["asset_count"] = len(result["assets"])
        result["source_timeline_assets"] = sum(
            row["kind"] == "SourceTimelineReplacement" for row in ROWS
        )
        result["unused_locomotion_assets"] = sum(
            row["kind"] == "UnusedLocomotionReplacement" for row in ROWS
        )
        result["composite_playback_assets"] = len(expected_playback)
        result["dilation_bakes"] = sum(
            bool(row.get("dilation_applied", False)) for row in ROWS
        )
        result["player_composite_root_motion_bakes"] = player_composite_root_bakes
        result["corrected_root_intervals"] = corrected_root_intervals
        result[
            "player_root_motion_normalized_assets"
        ] = player_root_motion_normalized_assets
        result["player_inserted_root_reference_uniform_scales"] = sorted(
            player_inserted_root_reference_scales
        )
        result["player_root_motion_translation_scale"] = (
            1.0 / next(iter(player_inserted_root_reference_scales))
        )
        result["temporary_player_mesh_component_scale_used_as_asset_input"] = False
        result["maximum_root_bake_interval_contract_error"] = {
            "translation": maximum_root_bake_error[0],
            "quaternion_dot_distance": maximum_root_bake_error[1],
        }
        result["maximum_pose_errors"] = {
            "position_cm": maxima[0],
            "quaternion_component": maxima[1],
            "scale": maxima[2],
        }
        result["maximum_topology_invariant_errors"] = {
            "position_cm": topology_maxima[0],
            "quaternion_component": topology_maxima[1],
            "scale": topology_maxima[2],
        }
        result["status"] = "passed"
    except Exception:
        result["status"] = "failed"
        result["error"] = traceback.format_exc()
        raise
    finally:
        write(result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "asset_count": result.get("asset_count"),
                "protected_locomotion_files_verified": result.get(
                    "protected_locomotion_files_verified"
                ),
                "maximum_pose_errors": result.get("maximum_pose_errors"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
