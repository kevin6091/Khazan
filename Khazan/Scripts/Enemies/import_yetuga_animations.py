"""Create bounded batches of source-timed Yetuga runtime AnimSequences."""

from __future__ import annotations

import json
import pathlib
import sys
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
sys.path.insert(0, str(PROJECT / "Saved/ArtTools/EnemyPython"))
import numpy as np


MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
ROWS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
VERSION = "20260911_Yetuga_SourceCompositePlaybackV2_RootLockPropagation"
UPGRADABLE_VERSIONS = {"20260911_Yetuga_SourceCompositePlaybackV1", VERSION}
MESH_PATH = MANIFEST["body"]["destination"]
SKELETON_PATH = MANIFEST["body"]["skeleton_destination"]
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load(path: str):
    asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError("Missing UE asset " + path)
    return asset


def save(asset) -> None:
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Save failed " + asset.get_path_name())


def set_sequence_properties(sequence, row: dict) -> None:
    sequence.set_editor_property("rate_scale", row["rate_scale"])
    properties = row["properties"]
    sequence.set_editor_property("enable_root_motion", bool(properties.get("bEnableRootMotion", False)))
    sequence.set_editor_property("force_root_lock", bool(properties.get("bForceRootLock", False)))
    if "RootMotionRootLock" in properties:
        values = {
            "RefPose": unreal.RootMotionRootLock.REF_POSE,
            "AnimFirstFrame": unreal.RootMotionRootLock.ANIM_FIRST_FRAME,
            "Zero": unreal.RootMotionRootLock.ZERO,
        }
        key = properties["RootMotionRootLock"].split("::")[-1]
        if key not in values:
            raise RuntimeError("Unsupported root-motion lock " + key)
        sequence.set_editor_property("root_motion_root_lock", values[key])
    if "AdditiveAnimType" in properties:
        values = {
            "AAT_None": unreal.AdditiveAnimationType.AAT_NONE,
            "AAT_LocalSpaceBase": unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE,
            "AAT_RotationOffsetMeshSpace": unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE,
        }
        key = properties["AdditiveAnimType"].split("::")[-1]
        if key not in values:
            raise RuntimeError("Unsupported additive type " + key)
        sequence.set_editor_property("additive_anim_type", values[key])
    if "RefPoseType" in properties:
        values = {
            "ABPT_None": unreal.AdditiveBasePoseType.ABPT_NONE,
            "ABPT_RefPose": unreal.AdditiveBasePoseType.ABPT_REF_POSE,
            "ABPT_AnimScaled": unreal.AdditiveBasePoseType.ABPT_ANIM_SCALED,
            "ABPT_AnimFrame": unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME,
            "ABPT_LocalAnimFrame": unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME,
        }
        key = properties["RefPoseType"].split("::")[-1]
        if key not in values:
            raise RuntimeError("Unsupported additive base-pose type " + key)
        sequence.set_editor_property("ref_pose_type", values[key])
    if "RefFrameIndex" in properties:
        sequence.set_editor_property("ref_frame_index", properties["RefFrameIndex"])


def apply_sequence_contract(sequence, row: dict) -> None:
    set_sequence_properties(sequence, row)
    EAL.set_metadata_tag(sequence, "OriginalPackage", row["source_package"])
    EAL.set_metadata_tag(sequence, "EnemyArtRole", "PlaybackSequence")
    EAL.set_metadata_tag(sequence, "PlaybackDerivation", row["playback_derivation"])
    EAL.set_metadata_tag(sequence, "EnemySourceLevels", json.dumps(MANIFEST["source_levels"]))
    EAL.set_metadata_tag(sequence, "YetugaLibraryVersion", MANIFEST["library_version"])
    EAL.set_metadata_tag(sequence, "EnemyTimingVersion", VERSION)
    EAL.set_metadata_tag(
        sequence,
        "TimingContract",
        json.dumps(
            {key: value for key, value in row.items() if key not in {"bones", "data_file", "properties"}},
            ensure_ascii=False,
        ),
    )
    if row["playback_derivation"] == "CompositeBake":
        usage = "Source AnimComposite trims, segment rates and dilation are baked; play at Rate Scale 1.0."
    else:
        usage = "Source AnimSequence timeline retained directly for original profile/BlendSpace consumption."
    EAL.set_metadata_tag(sequence, "PlaybackUsage", usage)


def create_sequence(row: dict):
    path = row["destination"]
    if EAL.does_asset_exist(path):
        sequence = load(path)
        if EAL.get_metadata_tag(sequence, "EnemyTimingVersion") not in UPGRADABLE_VERSIONS:
            raise RuntimeError("Unrecognized existing Yetuga animation " + path)
        apply_sequence_contract(sequence, row)
        save(sequence)
        return sequence, False

    skeleton = load(row["skeleton_destination"])
    mesh = load(row["mesh_destination"])
    factory = unreal.AnimSequenceFactory()
    factory.set_editor_property("target_skeleton", skeleton)
    factory.set_editor_property("preview_skeletal_mesh", mesh)
    folder, name = path.rsplit("/", 1)
    settings = unreal.get_default_object(unreal.AnimationSettings)
    previous = settings.get_editor_property("default_frame_rate")
    settings.set_editor_property(
        "default_frame_rate",
        unreal.FrameRate(*row["fps"]),
        notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER,
    )
    try:
        sequence = TOOLS.create_asset(name, folder, unreal.AnimSequence, factory)
    finally:
        settings.set_editor_property(
            "default_frame_rate", previous, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER
        )
    if not sequence:
        raise RuntimeError("Animation creation failed " + path)

    data = np.load(row["data_file"])
    expected_shape = (row["samples"], len(row["bones"]), 10)
    if data.shape != expected_shape or not np.isfinite(data).all():
        raise RuntimeError(f"Invalid animation sample data {data.shape} != {expected_shape}")
    controller = sequence.controller
    controller.open_bracket("Import source-timed Yetuga playback", False)
    controller.set_frame_rate(unreal.FrameRate(*row["fps"]), False)
    controller.set_number_of_frames(unreal.FrameNumber(row["samples"] - 1), False)
    for bone_index, bone_name in enumerate(row["bones"]):
        values = data[:, bone_index, :].tolist()
        positions = [unreal.Vector(*value[:3]) for value in values]
        rotations = [unreal.Quat(*value[3:7]) for value in values]
        scales = [unreal.Vector(*value[7:]) for value in values]
        controller.add_bone_curve(bone_name, False)
        if not controller.set_bone_track_keys(bone_name, positions, rotations, scales, False):
            raise RuntimeError("Unable to write bone track " + bone_name)
    controller.close_bracket(False)
    apply_sequence_contract(sequence, row)
    save(sequence)
    return sequence, True


def pose_errors(row: dict, sequence) -> dict:
    data = np.load(row["data_file"])
    maximum = np.zeros(3)
    worst = None
    modes = [unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED]
    options = [
        unreal.AnimPoseEvaluationOptions(
            evaluation_type=mode,
            should_retarget=False,
            extract_root_motion=False,
            incorporate_root_motion_into_pose=True,
        )
        for mode in modes
    ]
    for mode, option in zip(modes, options):
        for frame in sorted({0, (row["samples"] - 1) // 2, row["samples"] - 1}):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(sequence, frame, option)
            if not pose.is_valid():
                raise RuntimeError("Invalid animation pose " + row["destination"])
            for bone_index, bone_name in enumerate(row["bones"]):
                transform = pose.get_bone_pose(bone_name, unreal.AnimPoseSpaces.LOCAL)
                expected = data[frame, bone_index]
                position = [transform.translation.x, transform.translation.y, transform.translation.z]
                rotation = [transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w]
                scale = [transform.scale3d.x, transform.scale3d.y, transform.scale3d.z]
                error = [
                    max(abs(left - right) for left, right in zip(position, expected[:3])),
                    min(
                        max(abs(left - right) for left, right in zip(rotation, expected[3:7])),
                        max(abs(left + right) for left, right in zip(rotation, expected[3:7])),
                    ),
                    max(abs(left - right) for left, right in zip(scale, expected[7:])),
                ]
                if error[1] > maximum[1]:
                    worst = {
                        "bone": bone_name,
                        "frame": frame,
                        "mode": str(mode),
                        "quaternion_component_error": float(error[1]),
                    }
                maximum = np.maximum(maximum, error)
    # Numerical import/compression tolerances; these are validation limits, not gameplay values.
    if not (maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001):
        raise RuntimeError(f"Pose mismatch {row['destination']}: {maximum.tolist()} {worst}")
    return {
        "max_position_error_cm": float(maximum[0]),
        "max_quaternion_component_error": float(maximum[1]),
        "max_scale_error": float(maximum[2]),
        "worst_rotation": worst,
    }


def verify(row: dict, sequence) -> dict:
    duration = sequence.get_play_length()
    duration_error = abs(duration - row["duration"])
    if duration_error >= 1e-5:
        raise RuntimeError(f"Duration mismatch {row['destination']}: {duration} != {row['duration']}")
    if abs(sequence.get_editor_property("rate_scale") - row["rate_scale"]) >= 1e-6:
        raise RuntimeError("Rate Scale mismatch " + row["destination"])
    # UE 5.8 exposes the immutable data-model interface through the sequence's
    # controller; AnimSequence.get_data_model() is not part of its Python API.
    model = sequence.controller.get_model_interface()
    frame_rate = model.get_frame_rate()
    if [frame_rate.numerator, frame_rate.denominator] != row["fps"]:
        raise RuntimeError("Frame rate mismatch " + row["destination"])
    if model.get_number_of_keys() != row["samples"] or model.get_number_of_frames() != row["samples"] - 1:
        raise RuntimeError("Frame/sample count mismatch " + row["destination"])
    result = {
        "asset": row["destination"],
        "source": row["source_package"],
        "derivation": row["playback_derivation"],
        "samples": row["samples"],
        "fps": row["fps"],
        "duration": duration,
        "target_duration": row["duration"],
        "duration_error_seconds": duration_error,
        "dilation_applied": row.get("dilation_applied", False),
        "root_motion": bool(row["properties"].get("bEnableRootMotion", False)),
        "force_root_lock": bool(row["properties"].get("bForceRootLock", False)),
        "additive_type": row["properties"].get("AdditiveAnimType"),
    }
    result.update(pose_errors(row, sequence))
    return result


def command_range() -> tuple[int, int]:
    start = 0
    count = len(ROWS)
    for part in unreal.SystemLibrary.get_command_line().split():
        if part.startswith("-YetugaStart="):
            start = int(part.split("=", 1)[1])
        elif part.startswith("-YetugaCount="):
            count = int(part.split("=", 1)[1])
    return start, count


def main() -> None:
    start, count = command_range()
    target = PROJECT / "Saved/ImportReports/YetugaAnimationBatches" / f"{start:04d}.json"
    report = {"status": "running", "version": VERSION, "start": start, "count": count, "assets": []}
    try:
        for index, row in enumerate(ROWS[start : start + count], start):
            sequence, created = create_sequence(row)
            entry = verify(row, sequence)
            entry["created"] = created
            report["assets"].append(entry)
            write(target, report)
            print("YETUGA_ANIMATION", index + 1, "/", len(ROWS), row["destination"], flush=True)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        write(target, report)


if __name__ == "__main__":
    main()


