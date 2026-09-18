"""Restore DAS source timing and create original Composite playback sequences.

The script runs in bounded Unreal commandlet batches. Existing non-locomotion
source assets keep their package identity; only bone tracks, timing, and the
source-authored animation settings are replaced. Generated playback sequences
bake segment timing and DilationCurve mapping exactly once.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
sys.path.insert(0, str(PROJECT / "Saved/ArtTools/EnemyPython"))
import numpy as np


MANIFEST_PATH = ROOT / "AnimationImportManifest.json"
INVENTORY_PATH = PROJECT / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"
BACKUP_REPORT_PATH = PROJECT / "Saved/ImportReports/Khazan_DAS_AnimationBackup_20260916.json"
ROWS = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
INVENTORY = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
INVENTORY_BY_ASSET = {row.get("asset"): row for row in INVENTORY["assets"]}
SOURCE_VERSION = "20260916_DAS_SourceCompositeUnusedLocomotionV2"
CONTINUITY_VERSION = "20260917_DAS_CompositeRootContinuityV3"
ROOT_MOTION_VERSION = "20260917_DAS_RootMotionScaleAndContinuityV4"
COMPOSITE_VERSION = "20260917_DAS_CompositeExact60HzV5"
VERSION = COMPOSITE_VERSION
PREVIOUS_PIPELINE_VERSIONS = {
    SOURCE_VERSION,
    CONTINUITY_VERSION,
    ROOT_MOTION_VERSION,
}
PREVIOUS_GENERATED_VERSIONS = PREVIOUS_PIPELINE_VERSIONS
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_path(value) -> str | None:
    if not value:
        return None
    return value.get_path_name().split(".", 1)[0]


def load(path: str):
    asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError("Missing UE asset " + path)
    return asset


def target_version(row: dict) -> str:
    if row["kind"] == "CompositePlayback":
        return COMPOSITE_VERSION
    adapter = row["topology_adapter"]
    normalized_player_root_motion = (
        row["skeleton_destination"].endswith("/SK_Khazan")
        and bool(row["properties"].get("bEnableRootMotion", False))
        and abs(float(adapter.get("root_motion_translation_scale", 1.0)) - 1.0)
        > 1.0e-12
    )
    return ROOT_MOTION_VERSION if normalized_player_root_motion else SOURCE_VERSION


def is_pipeline_upgrade(row: dict, prior_version: str) -> bool:
    return (
        target_version(row) in {ROOT_MOTION_VERSION, COMPOSITE_VERSION}
        and prior_version in PREVIOUS_PIPELINE_VERSIONS
    )


def save(asset) -> None:
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Save failed " + asset.get_path_name())


def backup_contract() -> tuple[dict, dict[str, dict]]:
    if not BACKUP_REPORT_PATH.is_file():
        raise RuntimeError("The pre-mutation DAS backup report is missing")
    backup = json.loads(BACKUP_REPORT_PATH.read_text(encoding="utf-8"))
    if backup.get("status") != "passed":
        raise RuntimeError("The DAS backup did not pass")
    if backup["animation_manifest_sha256"] != sha256(MANIFEST_PATH):
        raise RuntimeError("Animation manifest changed after the backup")
    if backup["inventory_sha256"] != sha256(INVENTORY_PATH):
        raise RuntimeError("Project inventory changed after the backup")
    return backup, {row["package"]: row for row in backup["mutated_packages"]}


BACKUP = None
BACKUP_BY_PACKAGE = {}


def ensure_backup() -> None:
    global BACKUP, BACKUP_BY_PACKAGE
    if BACKUP is None:
        BACKUP, BACKUP_BY_PACKAGE = backup_contract()


def assert_original_files(row: dict) -> None:
    ensure_backup()
    package = row["destination"]
    backup = BACKUP_BY_PACKAGE.get(package)
    if not backup:
        raise RuntimeError("Package is absent from the mutation backup: " + package)
    for file in backup["files"]:
        path = PROJECT / file["path"]
        if not path.is_file() or sha256(path) != file["sha256"]:
            raise RuntimeError("Package changed after backup: " + file["path"])


def current_non_bone_contract(sequence) -> dict:
    model = sequence.controller.get_model_interface()
    notify_tracks = [
        str(value) for value in unreal.AnimationLibrary.get_animation_notify_track_names(sequence)
    ]
    import_data = None
    try:
        import_data = sequence.get_editor_property("asset_import_data")
    except Exception:
        pass
    return {
        "skeleton": package_path(sequence.get_editor_property("skeleton")),
        "notify_tracks": notify_tracks,
        "notify_events": [
            value.export_text()
            for value in unreal.AnimationLibrary.get_animation_notify_events(sequence)
        ],
        "sync_markers": {
            track: [
                {"name": str(marker.marker_name), "time": float(marker.time)}
                for marker in unreal.AnimationLibrary.get_animation_sync_markers_for_track(
                    sequence, track
                )
            ]
            for track in notify_tracks
        },
        "float_curve_count": int(model.get_number_of_float_curves()),
        "transform_curve_count": int(model.get_number_of_transform_curves()),
        "import_filenames": list(import_data.extract_filenames()) if import_data else [],
        "metadata": {
            str(key): str(value)
            for key, value in EAL.get_metadata_tag_values(sequence).items()
        },
    }


def expected_non_bone_contract(path: str) -> dict:
    row = INVENTORY_BY_ASSET[path]
    return {
        "skeleton": row["skeleton"],
        "notify_tracks": row.get("notify_tracks", []),
        "notify_events": row.get("notify_events", []),
        "sync_markers": row.get("sync_markers", {}),
        "float_curve_count": row.get("float_curve_count", 0),
        "transform_curve_count": row.get("transform_curve_count", 0),
        "import_filenames": row.get("import_filenames", []),
        "metadata": row.get("metadata", {}),
    }


def assert_preserved_before(sequence, row: dict) -> dict:
    expected = expected_non_bone_contract(row["destination"])
    actual = current_non_bone_contract(sequence)
    if actual != expected:
        raise RuntimeError(
            "Existing non-bone animation data changed since inventory: " + row["destination"]
        )
    return expected


def assert_preserved_after(sequence, expected: dict, row: dict) -> None:
    actual = current_non_bone_contract(sequence)
    for key in (
        "skeleton",
        "notify_tracks",
        "notify_events",
        "float_curve_count",
        "transform_curve_count",
        "import_filenames",
    ):
        if actual[key] != expected[key]:
            raise RuntimeError(f"Existing {key} changed: {row['destination']}")
    expected_markers = expected_sync_markers_after(row, expected)
    if not sync_markers_equal(actual["sync_markers"], expected_markers):
        raise RuntimeError(f"Existing sync_markers changed incorrectly: {row['destination']}")
    for key, value in expected["metadata"].items():
        if actual["metadata"].get(key) != value:
            raise RuntimeError(f"Existing metadata {key} changed: {row['destination']}")


def expected_sync_markers_after(row: dict, expected: dict) -> dict:
    if "sync_marker_remap" not in row:
        return expected["sync_markers"]
    result = {track: [] for track in expected["notify_tracks"]}
    for marker in row["sync_marker_remap"]:
        track = marker["track"]
        if track not in result:
            raise RuntimeError("Sync marker track is not preserved: " + track)
        result[track].append(
            {"name": marker["name"], "time": float(marker["target_time"])}
        )
    return result


def sync_markers_equal(actual: dict, expected: dict) -> bool:
    if set(actual) != set(expected):
        return False
    for track in actual:
        left = actual[track]
        right = expected[track]
        if len(left) != len(right):
            return False
        for a, b in zip(left, right):
            if a["name"] != b["name"] or abs(float(a["time"]) - float(b["time"])) >= 1.0e-5:
                return False
    return True


def apply_sync_marker_remap(sequence, row: dict) -> None:
    if "sync_marker_remap" not in row:
        return
    tracks = {
        str(value)
        for value in unreal.AnimationLibrary.get_animation_notify_track_names(sequence)
    }
    unreal.AnimationLibrary.remove_all_animation_sync_markers(sequence)
    for marker in row["sync_marker_remap"]:
        if marker["track"] not in tracks:
            raise RuntimeError("Missing authored sync-marker track: " + marker["track"])
        unreal.AnimationLibrary.add_animation_sync_marker(
            sequence,
            marker["name"],
            float(marker["target_time"]),
            marker["track"],
        )


def enum_tail(value: str) -> str:
    return str(value).split("::")[-1]


def set_sequence_properties(sequence, row: dict) -> None:
    sequence.set_editor_property("rate_scale", float(row["rate_scale"]))
    properties = row["properties"]
    sequence.set_editor_property(
        "enable_root_motion", bool(properties.get("bEnableRootMotion", False))
    )
    sequence.set_editor_property(
        "force_root_lock", bool(properties.get("bForceRootLock", False))
    )
    if "RootMotionRootLock" in properties:
        values = {
            "RefPose": unreal.RootMotionRootLock.REF_POSE,
            "AnimFirstFrame": unreal.RootMotionRootLock.ANIM_FIRST_FRAME,
            "Zero": unreal.RootMotionRootLock.ZERO,
        }
        key = enum_tail(properties["RootMotionRootLock"])
        if key not in values:
            raise RuntimeError("Unsupported root-motion lock " + key)
        sequence.set_editor_property("root_motion_root_lock", values[key])
    if "AdditiveAnimType" in properties:
        values = {
            "AAT_None": unreal.AdditiveAnimationType.AAT_NONE,
            "AAT_LocalSpaceBase": unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE,
            "AAT_RotationOffsetMeshSpace": unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE,
        }
        key = enum_tail(properties["AdditiveAnimType"])
        if key not in values:
            raise RuntimeError("Unsupported additive animation type " + key)
        sequence.set_editor_property("additive_anim_type", values[key])
    if "RefPoseType" in properties:
        values = {
            "ABPT_None": unreal.AdditiveBasePoseType.ABPT_NONE,
            "ABPT_RefPose": unreal.AdditiveBasePoseType.ABPT_REF_POSE,
            "ABPT_AnimScaled": unreal.AdditiveBasePoseType.ABPT_ANIM_SCALED,
            "ABPT_AnimFrame": unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME,
            "ABPT_LocalAnimFrame": unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME,
        }
        key = enum_tail(properties["RefPoseType"])
        if key not in values:
            raise RuntimeError("Unsupported additive base-pose type " + key)
        sequence.set_editor_property("ref_pose_type", values[key])
    if "RefFrameIndex" in properties:
        sequence.set_editor_property("ref_frame_index", int(properties["RefFrameIndex"]))


def apply_metadata(sequence, row: dict) -> None:
    concise_contract = {
        "kind": row["kind"],
        "source": row["source_package"],
        "samples": row["samples"],
        "duration": row["duration"],
        "fps": row["fps"],
        "authored_duration": row.get("authored_duration", row["duration"]),
        "duration_quantization_error_seconds": row.get(
            "duration_quantization_error_seconds", 0.0
        ),
        "sampling_policy": row.get("sampling_policy"),
        "dilation_applied": bool(row.get("dilation_applied", False)),
        "topology_adapter": row["topology_adapter"],
        "root_motion_bake": row.get("root_motion_bake"),
    }
    EAL.set_metadata_tag(sequence, "OriginalPackage", row["source_package"])
    EAL.set_metadata_tag(sequence, "DASTimingVersion", target_version(row))
    EAL.set_metadata_tag(sequence, "PlaybackDerivation", row["kind"])
    EAL.set_metadata_tag(
        sequence, "TimingContract", json.dumps(concise_contract, ensure_ascii=False)
    )
    EAL.set_metadata_tag(
        sequence, "DASTopologyAdapter", json.dumps(row["topology_adapter"], ensure_ascii=False)
    )
    if row["kind"] == "CompositePlayback":
        usage = (
            "Original AnimComposite trims, segment rates, loops, and active DilationCurve are "
            "baked once. Play this sequence and its future Montage segment at rate 1.0."
        )
        EAL.set_metadata_tag(
            sequence,
            "OriginalNotifyEventReport",
            "Saved/Extracted/DualAxeSword_20260916/PlaybackEvents.json",
        )
    elif row["kind"] == "UnusedLocomotionReplacement":
        usage = (
            "Unused locomotion derivative rebuilt from the original source pose and frame "
            "rate. Current ABP locomotion dependencies were excluded from this import."
        )
    else:
        usage = (
            "Original source AnimSequence timeline. Skill playback should use the matching "
            "generated CompositePlayback asset when one exists."
        )
    EAL.set_metadata_tag(sequence, "PlaybackUsage", usage)


def transform_from_values(value) -> unreal.Transform:
    # The UE 5.8 Transform constructor is exposed through MakeTransform and
    # therefore expects a Rotator.  Assign the native Transform fields after
    # construction so the prepared quaternion is not round-tripped through
    # Euler angles.
    result = unreal.Transform()
    result.translation = unreal.Vector(*[float(item) for item in value[:3]])
    result.rotation = unreal.Quat(*[float(item) for item in value[3:7]])
    result.scale3d = unreal.Vector(*[float(item) for item in value[7:10]])
    return result


def transform_values(transform) -> list[float]:
    return [
        float(transform.translation.x),
        float(transform.translation.y),
        float(transform.translation.z),
        float(transform.rotation.x),
        float(transform.rotation.y),
        float(transform.rotation.z),
        float(transform.rotation.w),
        float(transform.scale3d.x),
        float(transform.scale3d.y),
        float(transform.scale3d.z),
    ]


def transform_error(left, right) -> tuple[float, float, float]:
    a = transform_values(left)
    b = transform_values(right)
    position = max(abs(x - y) for x, y in zip(a[:3], b[:3]))
    rotation = min(
        max(abs(x - y) for x, y in zip(a[3:7], b[3:7])),
        max(abs(x + y) for x, y in zip(a[3:7], b[3:7])),
    )
    scale = max(abs(x - y) for x, y in zip(a[7:], b[7:]))
    return position, rotation, scale


def adapted_pose(row: dict, skeleton, mesh):
    path = pathlib.Path(row["data_file"])
    if not path.is_file() or sha256(path) != row["data_sha256"]:
        raise RuntimeError("Prepared pose data changed: " + str(path))
    source = np.load(path)
    expected_shape = (row["samples"], len(row["bones"]), 10)
    if source.shape != expected_shape or not np.isfinite(source).all():
        raise RuntimeError(f"Invalid prepared pose data {source.shape} != {expected_shape}")

    adapter = row["topology_adapter"]
    inserted = adapter["inserted_root_bone"]
    motion = adapter["source_motion_bone"]
    lower_bones = {name.lower(): index for index, name in enumerate(row["bones"])}
    if motion.lower() not in lower_bones or inserted.lower() in lower_bones:
        raise RuntimeError("Invalid topology adapter track contract: " + row["destination"])
    reference = skeleton.get_reference_pose()
    skeleton_bones = [str(value) for value in reference.get_bone_names()]
    canonical = {name.lower(): name for name in skeleton_bones}
    missing = [name for name in row["bones"] if name.lower() not in canonical]
    if inserted.lower() not in canonical or missing:
        raise RuntimeError(
            "Prepared tracks do not exist on target skeleton: " + repr([inserted] + missing)
        )
    inserted = canonical[inserted.lower()]
    motion = canonical[motion.lower()]
    children = [str(value).lower() for value in mesh.get_bone_children(inserted)]
    if motion.lower() not in children:
        raise RuntimeError(f"{motion} is not a direct child of {inserted}")

    inserted_ref = reference.get_bone_pose(inserted)
    motion_ref = reference.get_bone_pose(motion)
    motion_index = lower_bones[motion.lower()]
    output = np.empty((row["samples"], len(row["bones"]) + 1, 10), dtype=np.float32)
    output[:, 1:, :] = source
    output[:, 1 + motion_index, :] = np.asarray(transform_values(motion_ref), dtype=np.float32)
    maximum_invariant = np.zeros(3, dtype=np.float64)
    inverse_motion_ref = motion_ref.inverse()
    for frame in range(row["samples"]):
        old_motion = transform_from_values(source[frame, motion_index])
        transferred = inverse_motion_ref.multiply(old_motion).multiply(inserted_ref)
        old_component = old_motion.multiply(inserted_ref)
        new_component = motion_ref.multiply(transferred)
        maximum_invariant = np.maximum(
            maximum_invariant, transform_error(old_component, new_component)
        )
        transferred_values = transform_values(transferred)
        if bool(row["properties"].get("bEnableRootMotion", False)):
            translation_scale = float(
                adapter.get("root_motion_translation_scale", 1.0)
            )
            reference_values = transform_values(inserted_ref)
            transferred_values[:3] = [
                reference_values[axis]
                + (transferred_values[axis] - reference_values[axis])
                * translation_scale
                for axis in range(3)
            ]
        output[frame, 0, :] = np.asarray(transferred_values, dtype=np.float32)
    if not (
        maximum_invariant[0] < 0.0001
        and maximum_invariant[1] < 0.00001
        and maximum_invariant[2] < 0.00001
    ):
        raise RuntimeError(
            "Topology transfer changed component pose: " + maximum_invariant.tolist().__repr__()
        )
    return [inserted] + row["bones"], output, maximum_invariant.tolist()


def create_sequence(row: dict):
    skeleton = load(row["skeleton_destination"])
    mesh = load(row["mesh_destination"])
    path = row["destination"]
    existing = EAL.does_asset_exist(path)
    sequence = load(path) if existing else None
    prior_version = EAL.get_metadata_tag(sequence, "DASTimingVersion") if sequence else ""
    expected_version = target_version(row)
    pipeline_upgrade = existing and is_pipeline_upgrade(row, prior_version)
    fresh_replacement = (
        row["operation"] == "replace_existing"
        and prior_version != expected_version
        and not pipeline_upgrade
    )
    generated_upgrade = (
        row["kind"] == "CompositePlayback"
        and row["operation"] == "create_or_replace_generated"
        and existing
        and prior_version in PREVIOUS_GENERATED_VERSIONS
    )
    preserved = None
    skeleton_changed = False

    if existing and not isinstance(sequence, unreal.AnimSequence):
        raise RuntimeError("Destination is not an AnimSequence: " + path)
    if fresh_replacement:
        assert_original_files(row)
        preserved = assert_preserved_before(sequence, row)
    elif pipeline_upgrade and row["operation"] == "replace_existing":
        preserved = expected_non_bone_contract(row["destination"])
        assert_preserved_after(sequence, preserved, row)
    elif (
        existing
        and prior_version != expected_version
        and not pipeline_upgrade
        and not generated_upgrade
    ):
        raise RuntimeError("Unrecognized existing generated animation: " + path)

    # UAnimSequence::Skeleton is read-only through the UE 5.8 Python property
    # bridge.  The four unreferenced weapon-object sequences entered the project
    # on SK_Khazan, so a skeleton correction must recreate their package through
    # UAnimSequenceFactory (which calls SetSkeleton in C++) instead of attempting
    # to assign the property on the existing object.  The original package was
    # already hash-verified in the immutable pre-import backup above.
    if sequence:
        current_skeleton = package_path(sequence.get_editor_property("skeleton"))
        if current_skeleton != row["skeleton_destination"]:
            if not fresh_replacement:
                raise RuntimeError(
                    f"Unexpected skeleton {current_skeleton} for existing asset {path}"
                )
            source_inventory = INVENTORY_BY_ASSET[path]
            if source_inventory.get("referencers"):
                raise RuntimeError("Cannot change skeleton of a referenced asset: " + path)
            if (
                source_inventory.get("notify_events")
                or source_inventory.get("float_curve_count")
                or source_inventory.get("transform_curve_count")
                or any(source_inventory.get("sync_markers", {}).values())
            ):
                raise RuntimeError(
                    "Skeleton-changing source has authored non-bone data: " + path
                )
            if not EAL.delete_asset(path):
                raise RuntimeError("Unable to recreate asset on target skeleton: " + path)
            sequence = None
            skeleton_changed = True

    if not sequence:
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
                "default_frame_rate",
                previous,
                notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER,
            )
        if not sequence:
            raise RuntimeError("Animation creation failed " + path)

    current_skeleton = package_path(sequence.get_editor_property("skeleton"))
    if current_skeleton != row["skeleton_destination"]:
        raise RuntimeError(
            f"Target skeleton assignment failed ({current_skeleton}): {path}"
        )
    output_bones, data, topology_error = adapted_pose(row, skeleton, mesh)
    controller = unreal.AnimationDataController.cast(sequence.controller)
    target_frame_rate = unreal.FrameRate(*row["fps"])

    controller.open_bracket("Restore original DAS animation timing", False)
    try:
        if not skeleton_changed:
            for bone_name in list(controller.get_model_interface().get_bone_track_names()):
                if not controller.remove_bone_track(str(bone_name), False):
                    raise RuntimeError("Unable to remove old bone track " + str(bone_name))
        # Every untouched replacement in the frozen inventory is 24 fps.  UE
        # only permits a populated model to move to a multiple or factor of its
        # current frame rate, so 24 -> 30/60 needs an exact common bridge.  The
        # 120 fps hop preserves play length and lands on an integer frame grid
        # for all source/locomotion targets in this manifest.
        if fresh_replacement and not skeleton_changed:
            source_fps = INVENTORY_BY_ASSET[path]["fps"]
            if source_fps != [24, 1]:
                raise RuntimeError(
                    f"Unexpected pre-import frame rate {source_fps}: {path}"
                )
            controller.set_frame_rate(unreal.FrameRate(120, 1), False)
            target_numerator, target_denominator = row["fps"]
            bridge_frames_numerator = (
                (row["samples"] - 1) * 120 * target_denominator
            )
            if bridge_frames_numerator % target_numerator:
                raise RuntimeError(
                    "Target timeline cannot be represented on the 120 fps bridge: "
                    + path
                )
            controller.set_number_of_frames(
                unreal.FrameNumber(bridge_frames_numerator // target_numerator),
                False,
            )
        controller.set_frame_rate(target_frame_rate, False)
        controller.set_number_of_frames(unreal.FrameNumber(row["samples"] - 1), False)
        for bone_index, bone_name in enumerate(output_bones):
            values = data[:, bone_index, :].tolist()
            positions = [unreal.Vector(*value[:3]) for value in values]
            rotations = [unreal.Quat(*value[3:7]) for value in values]
            scales = [unreal.Vector(*value[7:]) for value in values]
            if not controller.add_bone_curve(bone_name, False):
                raise RuntimeError("Unable to add bone track " + bone_name)
            if not controller.set_bone_track_keys(
                bone_name, positions, rotations, scales, False
            ):
                raise RuntimeError("Unable to write bone track " + bone_name)

        # PlatformTargetFrameRate is exposed as a read-only UAnimSequence
        # property, but its live FPerPlatformFrameRate value is editable.  Set
        # it only after the data-model grid and all tracks are final: changing
        # it requests compression immediately, so doing this before the model
        # moves from 24 fps would briefly create an invalid fractional grid.
        platform_frame_rate = sequence.get_editor_property(
            "platform_target_frame_rate"
        )
        platform_frame_rate.set_editor_property("default", target_frame_rate)
        overrides = platform_frame_rate.get_editor_property("per_platform")
        if overrides:
            platform_frame_rate.set_editor_property(
                "per_platform", {name: target_frame_rate for name in overrides}
            )
    finally:
        controller.close_bracket(False)

    set_sequence_properties(sequence, row)
    apply_sync_marker_remap(sequence, row)
    apply_metadata(sequence, row)
    save(sequence)
    if preserved is not None and not skeleton_changed:
        assert_preserved_after(sequence, preserved, row)
    return sequence, data, output_bones, topology_error, existing, skeleton_changed


def pose_errors(row: dict, sequence, expected, output_bones: list[str]) -> dict:
    maximum = np.zeros(3, dtype=np.float64)
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
    frames = sorted({0, (row["samples"] - 1) // 2, row["samples"] - 1})
    for mode, option in zip(modes, options):
        for frame in frames:
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(sequence, frame, option)
            if not pose.is_valid():
                raise RuntimeError("Invalid animation pose " + row["destination"])
            for bone_index, bone_name in enumerate(output_bones):
                transform = pose.get_bone_pose(bone_name, unreal.AnimPoseSpaces.LOCAL)
                actual = transform_values(transform)
                target = expected[frame, bone_index]
                error = [
                    max(abs(left - right) for left, right in zip(actual[:3], target[:3])),
                    min(
                        max(abs(left - right) for left, right in zip(actual[3:7], target[3:7])),
                        max(abs(left + right) for left, right in zip(actual[3:7], target[3:7])),
                    ),
                    max(abs(left - right) for left, right in zip(actual[7:], target[7:])),
                ]
                if any(error[index] > maximum[index] for index in range(3)):
                    worst = {
                        "bone": bone_name,
                        "frame": frame,
                        "mode": str(mode),
                        "errors": [float(value) for value in error],
                    }
                maximum = np.maximum(maximum, error)
    # Numerical import/compression limits; these are validation tolerances, not gameplay values.
    if not (maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001):
        raise RuntimeError(
            f"Pose mismatch {row['destination']}: {maximum.tolist()} {worst}"
        )
    return {
        "max_position_error_cm": float(maximum[0]),
        "max_quaternion_component_error": float(maximum[1]),
        "max_scale_error": float(maximum[2]),
        "worst_pose_sample": worst,
    }


def verify(row: dict, sequence, expected, output_bones, topology_error) -> dict:
    duration = float(sequence.get_play_length())
    duration_error = abs(duration - row["duration"])
    if duration_error >= 1.0e-5:
        raise RuntimeError(
            f"Duration mismatch {row['destination']}: {duration} != {row['duration']}"
        )
    if abs(float(sequence.get_editor_property("rate_scale")) - row["rate_scale"]) >= 1.0e-6:
        raise RuntimeError("Rate Scale mismatch " + row["destination"])
    if package_path(sequence.get_editor_property("skeleton")) != row["skeleton_destination"]:
        raise RuntimeError("Skeleton mismatch " + row["destination"])
    model = sequence.controller.get_model_interface()
    frame_rate = model.get_frame_rate()
    if [int(frame_rate.numerator), int(frame_rate.denominator)] != row["fps"]:
        raise RuntimeError("Frame rate mismatch " + row["destination"])
    if (
        int(model.get_number_of_keys()) != row["samples"]
        or int(model.get_number_of_frames()) != row["samples"] - 1
    ):
        raise RuntimeError("Frame/sample count mismatch " + row["destination"])
    actual_tracks = [str(value).lower() for value in model.get_bone_track_names()]
    if actual_tracks != [value.lower() for value in output_bones]:
        raise RuntimeError("Bone track order/content mismatch " + row["destination"])
    properties = row["properties"]
    if bool(sequence.get_editor_property("enable_root_motion")) != bool(
        properties.get("bEnableRootMotion", False)
    ):
        raise RuntimeError("Root Motion flag mismatch " + row["destination"])
    if bool(sequence.get_editor_property("force_root_lock")) != bool(
        properties.get("bForceRootLock", False)
    ):
        raise RuntimeError("Force Root Lock flag mismatch " + row["destination"])
    if EAL.get_metadata_tag(sequence, "DASTimingVersion") != target_version(row):
        raise RuntimeError("Timing metadata version mismatch " + row["destination"])
    result = {
        "asset": row["destination"],
        "source": row["source_package"],
        "kind": row["kind"],
        "samples": row["samples"],
        "fps": row["fps"],
        "duration": duration,
        "target_duration": row["duration"],
        "duration_error_seconds": duration_error,
        "dilation_applied": bool(row.get("dilation_applied", False)),
        "root_motion": bool(properties.get("bEnableRootMotion", False)),
        "force_root_lock": bool(properties.get("bForceRootLock", False)),
        "timing_version": target_version(row),
        "root_motion_translation_scale": float(
            row["topology_adapter"].get("root_motion_translation_scale", 1.0)
        ),
        "skeleton": row["skeleton_destination"],
        "source_track_count": len(row["bones"]),
        "written_track_count": len(output_bones),
        "topology_component_pose_invariant_max_error": topology_error,
    }
    result.update(pose_errors(row, sequence, expected, output_bones))
    return result


def command_range() -> tuple[int, int]:
    start = 0
    count = len(ROWS)
    for part in unreal.SystemLibrary.get_command_line().split():
        if part.startswith("-DASStart="):
            start = int(part.split("=", 1)[1])
        elif part.startswith("-DASCount="):
            count = int(part.split("=", 1)[1])
    return start, count


def requires_original_backup(row: dict) -> bool:
    if row["operation"] != "replace_existing":
        return False
    if not EAL.does_asset_exist(row["destination"]):
        return True
    sequence = load(row["destination"])
    prior_version = EAL.get_metadata_tag(sequence, "DASTimingVersion")
    return (
        prior_version != target_version(row)
        and not is_pipeline_upgrade(row, prior_version)
    )


def main() -> None:
    start, count = command_range()
    selected_rows = ROWS[start : start + count]
    if any(requires_original_backup(row) for row in selected_rows):
        ensure_backup()
    report_path = (
        PROJECT / "Saved/ImportReports/DASAnimationBatches" / f"{start:04d}.json"
    )
    report = {
        "status": "running",
        "version": VERSION,
        "start": start,
        "count": count,
        "backup": BACKUP["backup_root"] if BACKUP else None,
        "assets": [],
    }
    try:
        for index, row in enumerate(selected_rows, start):
            already_current = (
                EAL.does_asset_exist(row["destination"])
                and EAL.get_metadata_tag(
                    load(row["destination"]), "DASTimingVersion"
                )
                == target_version(row)
            )
            if already_current:
                sequence = load(row["destination"])
                skeleton = load(row["skeleton_destination"])
                mesh = load(row["mesh_destination"])
                output_bones, expected, topology_error = adapted_pose(
                    row, skeleton, mesh
                )
                entry = verify(
                    row, sequence, expected, output_bones, topology_error
                )
                entry["existed_before_batch"] = True
                entry["skeleton_corrected"] = False
            else:
                (
                    sequence,
                    expected,
                    output_bones,
                    topology_error,
                    existed,
                    skeleton_changed,
                ) = create_sequence(row)
                entry = verify(
                    row, sequence, expected, output_bones, topology_error
                )
                entry["existed_before_batch"] = existed
                entry["skeleton_corrected"] = skeleton_changed
            entry["skipped_already_current"] = already_current
            entry["manifest_index"] = index
            report["assets"].append(entry)
            write(report_path, report)
            print(
                "DAS_ANIMATION",
                index + 1,
                "/",
                len(ROWS),
                row["destination"],
                flush=True,
            )
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        write(report_path, report)


if __name__ == "__main__":
    main()
