"""Read-only Unreal preflight for the DAS timing restoration manifest.

This loads every prepared pose and its target skeleton, exercises the topology
adapter used by the mutation worker, and rejects protected or inconsistent
destinations.  It does not create, dirty, or save any Unreal asset.
"""

from __future__ import annotations

import json
import math
import pathlib
import runpy
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_CompositeExact60PipelinePreflight_20260917.json"
HELPERS = runpy.run_path(
    str(PROJECT / "Scripts/Animation/import_das_animation_timing.py"),
    run_name="das_animation_import_preflight_helpers",
)
ROWS = HELPERS["ROWS"]
INVENTORY = HELPERS["INVENTORY"]
EAL = unreal.EditorAssetLibrary


def write(value: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_properties(row: dict) -> None:
    if not math.isfinite(float(row["rate_scale"])) or float(row["rate_scale"]) <= 0.0:
        raise RuntimeError("Invalid RateScale: " + row["destination"])
    properties = row["properties"]
    root_lock = {
        "RefPose": unreal.RootMotionRootLock.REF_POSE,
        "AnimFirstFrame": unreal.RootMotionRootLock.ANIM_FIRST_FRAME,
        "Zero": unreal.RootMotionRootLock.ZERO,
    }
    additive = {
        "AAT_None": unreal.AdditiveAnimationType.AAT_NONE,
        "AAT_LocalSpaceBase": unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE,
        "AAT_RotationOffsetMeshSpace": unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE,
    }
    base_pose = {
        "ABPT_None": unreal.AdditiveBasePoseType.ABPT_NONE,
        "ABPT_RefPose": unreal.AdditiveBasePoseType.ABPT_REF_POSE,
        "ABPT_AnimScaled": unreal.AdditiveBasePoseType.ABPT_ANIM_SCALED,
        "ABPT_AnimFrame": unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME,
        "ABPT_LocalAnimFrame": unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME,
    }
    contracts = (
        ("RootMotionRootLock", root_lock),
        ("AdditiveAnimType", additive),
        ("RefPoseType", base_pose),
    )
    for property_name, values in contracts:
        if property_name not in properties:
            continue
        key = HELPERS["enum_tail"](properties[property_name])
        if key not in values:
            raise RuntimeError(
                f"Unsupported {property_name} {key}: {row['destination']}"
            )


def main() -> None:
    result = {
        "schema": 1,
        "status": "running",
        "read_only": True,
        "version": HELPERS["VERSION"],
        "manifest_sha256": HELPERS["sha256"](HELPERS["MANIFEST_PATH"]),
        "inventory_sha256": HELPERS["sha256"](HELPERS["INVENTORY_PATH"]),
        "assets": [],
        "failures": [],
    }
    try:
        if INVENTORY.get("status") != "passed" or not INVENTORY.get("read_only"):
            raise RuntimeError("The source project inventory is not a passed read-only audit")
        if len(ROWS) != 981:
            raise RuntimeError(f"Unexpected manifest size: {len(ROWS)}")
        destinations = [row["destination"] for row in ROWS]
        if len(set(destinations)) != len(destinations):
            raise RuntimeError("The import manifest contains duplicate destinations")
        protected = set(INVENTORY["protected_locomotion_sequences"])
        overlap = protected.intersection(destinations)
        if overlap:
            raise RuntimeError("Manifest overlaps protected locomotion: " + repr(sorted(overlap)))
        for row in ROWS:
            if (
                row["kind"] == "CompositePlayback"
                and pathlib.PurePosixPath(row["destination"]).name != row["source_name"]
            ):
                raise RuntimeError(
                    "Composite playback basename differs from the original: "
                    + row["destination"]
                )

        skeleton_cache = {}
        mesh_cache = {}
        maxima = [0.0, 0.0, 0.0]
        existing_replacements = 0
        existing_created_assets = 0
        absent_creations = 0
        existing_generated = 0
        existing_previous_version = 0
        existing_generated_previous_version = 0
        player_root_motion_normalized_assets = 0
        player_composite_root_bakes = 0
        corrected_root_intervals = 0
        maximum_root_bake_error = [0.0, 0.0]
        player_inserted_root_reference_scales = set()
        for index, row in enumerate(ROWS):
            samples = int(row["samples"])
            numerator, denominator = (int(value) for value in row["fps"])
            if samples < 2 or numerator <= 0 or denominator <= 0:
                raise RuntimeError("Invalid timeline: " + row["destination"])
            calculated_duration = (samples - 1) * denominator / numerator
            # Cooked metadata serializes duration as float; the rational frame
            # grid is authoritative and may differ in the seventh decimal.
            if abs(calculated_duration - float(row["duration"])) >= 1.0e-6:
                raise RuntimeError(
                    f"Timeline duration is inconsistent: {row['destination']}"
                )
            unreal.FrameRate(numerator, denominator)
            validate_properties(row)

            exists = EAL.does_asset_exist(row["destination"])
            operation = row["operation"]
            expected_version = HELPERS["target_version"](row)
            if operation == "replace_existing":
                if not exists or row["destination"] not in HELPERS["INVENTORY_BY_ASSET"]:
                    raise RuntimeError("Replacement source is missing: " + row["destination"])
                asset = HELPERS["load"](row["destination"])
                version = EAL.get_metadata_tag(asset, "DASTimingVersion")
                if version != expected_version and not HELPERS["is_pipeline_upgrade"](
                    row, version
                ):
                    raise RuntimeError(
                        f"Replacement has unexpected timing version {version!r}: "
                        + row["destination"]
                    )
                if version != expected_version:
                    existing_previous_version += 1
                existing_replacements += 1
            elif operation == "create_missing":
                if exists:
                    asset = HELPERS["load"](row["destination"])
                    version = EAL.get_metadata_tag(asset, "DASTimingVersion")
                    if version != expected_version and not HELPERS[
                        "is_pipeline_upgrade"
                    ](row, version):
                        raise RuntimeError(
                            f"Recovered destination has unexpected timing version {version!r}: "
                            + row["destination"]
                        )
                    if version != expected_version:
                        existing_previous_version += 1
                    existing_created_assets += 1
                else:
                    absent_creations += 1
            elif operation == "create_or_replace_generated":
                if exists:
                    asset = HELPERS["load"](row["destination"])
                    version = EAL.get_metadata_tag(asset, "DASTimingVersion")
                    if (
                        version != expected_version
                        and not HELPERS["is_pipeline_upgrade"](row, version)
                    ):
                        raise RuntimeError(
                            "Unrecognized asset occupies generated destination: "
                            + row["destination"]
                        )
                    if version != expected_version:
                        existing_generated_previous_version += 1
                    existing_generated += 1
                else:
                    absent_creations += 1
            else:
                raise RuntimeError("Unsupported operation: " + str(operation))

            is_player_root_motion = (
                row["skeleton_destination"].endswith("/SK_Khazan")
                and bool(row["properties"].get("bEnableRootMotion", False))
            )
            if is_player_root_motion:
                if row["skeleton_destination"] not in skeleton_cache:
                    skeleton_cache[row["skeleton_destination"]] = HELPERS["load"](
                        row["skeleton_destination"]
                    )
                skeleton = skeleton_cache[row["skeleton_destination"]]
                adapter = row["topology_adapter"]
                inserted_ref = skeleton.get_reference_pose().get_bone_pose(
                    adapter["inserted_root_bone"]
                )
                reference_scale = [
                    float(value)
                    for value in HELPERS["transform_values"](inserted_ref)[7:10]
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
                    adapter.get(
                        "root_motion_translation_scale", 1.0
                    )
                )
                expected_translation_scale = 1.0 / inserted_root_scale
                if abs(translation_scale - expected_translation_scale) >= 1.0e-12:
                    raise RuntimeError(
                        "Player Root Motion compensation is not the reciprocal of the "
                        "inserted root reference scale: "
                        + row["destination"]
                    )
                required_root_version = (
                    HELPERS["COMPOSITE_VERSION"]
                    if row["kind"] == "CompositePlayback"
                    else HELPERS["ROOT_MOTION_VERSION"]
                )
                if expected_version != required_root_version:
                    raise RuntimeError(
                        "Normalized player Root Motion has wrong target version: "
                        + row["destination"]
                    )
                player_root_motion_normalized_assets += 1
                player_inserted_root_reference_scales.add(inserted_root_scale)

            if row["kind"] == "CompositePlayback":
                root_bake = row.get("root_motion_bake")
                is_player = row["skeleton_destination"].endswith("/SK_Khazan")
                if is_player:
                    if not root_bake:
                        raise RuntimeError(
                            "Player Composite has no continuous root-motion bake: "
                            + row["destination"]
                        )
                    if any(
                        abs(float(value)) >= 1.0e-7
                        for value in root_bake["initial_baked_root_translation"]
                    ):
                        raise RuntimeError(
                            "Player Composite root was not rebased: " + row["destination"]
                        )
                    errors = root_bake["maximum_baked_interval_contract_error"]
                    if float(errors[0]) >= 0.0001 or float(errors[1]) >= 1.0e-10:
                        raise RuntimeError(
                            "Player Composite root-motion contract error: "
                            + row["destination"]
                        )
                    maximum_root_bake_error = [
                        max(maximum_root_bake_error[axis], float(errors[axis]))
                        for axis in range(2)
                    ]
                    player_composite_root_bakes += 1
                    corrected_root_intervals += int(root_bake["corrected_interval_count"])
                elif root_bake is not None:
                    raise RuntimeError(
                        "Auxiliary weapon Composite unexpectedly has player root bake: "
                        + row["destination"]
                    )

            if row["skeleton_destination"] not in skeleton_cache:
                skeleton_cache[row["skeleton_destination"]] = HELPERS["load"](
                    row["skeleton_destination"]
                )
            if row["mesh_destination"] not in mesh_cache:
                mesh_cache[row["mesh_destination"]] = HELPERS["load"](
                    row["mesh_destination"]
                )
            skeleton = skeleton_cache[row["skeleton_destination"]]
            mesh = mesh_cache[row["mesh_destination"]]
            output_bones, prepared_pose, topology_error = HELPERS["adapted_pose"](
                row, skeleton, mesh
            )
            if len(output_bones) != len(row["bones"]) + 1:
                raise RuntimeError("Topology adapter output count mismatch")
            if prepared_pose.shape != (samples, len(output_bones), 10):
                raise RuntimeError("Topology adapter output shape mismatch")
            maxima = [max(maxima[i], float(topology_error[i])) for i in range(3)]
            result["assets"].append(
                {
                    "asset": row["destination"],
                    "kind": row["kind"],
                    "operation": operation,
                    "samples": samples,
                    "source_tracks": len(row["bones"]),
                    "output_tracks": len(output_bones),
                    "skeleton": row["skeleton_destination"],
                    "root_motion": bool(row["properties"].get("bEnableRootMotion", False)),
                    "dilation_applied": bool(row.get("dilation_applied", False)),
                    "topology_component_pose_invariant_max_error": topology_error,
                }
            )
            del prepared_pose
            if (index + 1) % 50 == 0:
                print("DAS_PREFLIGHT", index + 1, "/", len(ROWS), flush=True)

        result.update(
            {
                "status": "passed",
                "asset_count": len(result["assets"]),
                "existing_replacements": existing_replacements,
                "existing_created_assets": existing_created_assets,
                "absent_creations": absent_creations,
                "existing_generated": existing_generated,
                "existing_previous_version": existing_previous_version,
                "existing_generated_previous_version": existing_generated_previous_version,
                "source_timeline_assets": sum(
                    row["kind"] == "SourceTimelineReplacement" for row in ROWS
                ),
                "unused_locomotion_assets": sum(
                    row["kind"] == "UnusedLocomotionReplacement" for row in ROWS
                ),
                "composite_playback_assets": sum(
                    row["kind"] == "CompositePlayback" for row in ROWS
                ),
                "dilation_bakes": sum(
                    bool(row.get("dilation_applied", False)) for row in ROWS
                ),
                "root_motion_assets": sum(
                    bool(row["properties"].get("bEnableRootMotion", False)) for row in ROWS
                ),
                "player_root_motion_normalized_assets": player_root_motion_normalized_assets,
                "player_inserted_root_reference_uniform_scales": sorted(
                    player_inserted_root_reference_scales
                ),
                "player_root_motion_translation_scale": (
                    1.0 / next(iter(player_inserted_root_reference_scales))
                ),
                "temporary_player_mesh_component_scale_used_as_asset_input": False,
                "player_composite_root_motion_bakes": player_composite_root_bakes,
                "corrected_root_intervals": corrected_root_intervals,
                "maximum_root_bake_interval_contract_error": {
                    "translation": maximum_root_bake_error[0],
                    "quaternion_dot_distance": maximum_root_bake_error[1],
                },
                "maximum_topology_invariant_errors": {
                    "position_cm": maxima[0],
                    "quaternion_component": maxima[1],
                    "scale": maxima[2],
                },
            }
        )
    except Exception:
        result["status"] = "failed"
        result["failures"].append(traceback.format_exc())
        raise
    finally:
        write(result)

    print(json.dumps({key: value for key, value in result.items() if key != "assets"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
