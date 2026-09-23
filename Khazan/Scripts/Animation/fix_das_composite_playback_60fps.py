"""Normalize every generated DualAxeSword Composite playback asset to 60/1 Hz.

The previous bake chose an integer sample count, kept the cooked Composite's
floating-point duration, and then encoded ``samples / duration`` as the model
frame rate.  That produced a different rational frame rate for nearly every
asset.  This migration keeps the baked pose and Root Motion trajectory, moves
the duration to the nearest 60 Hz frame boundary, and samples the complete old
timeline onto that exact grid.

Run from a live editor in bounded batches with ``run_batch(start, count)``.
``preflight_and_backup`` is intentionally external to this file: the immutable
package backup and read-only preflight reports must already exist before the
first batch can write Content.
"""

from __future__ import annotations

import datetime
import json
import math
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
PREFLIGHT = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Preflight_20260917.json"
)
BACKUP = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Backup_20260917.json"
)
REPORT = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Import_20260917.json"
)
MONTAGE_PATH = "/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAtkCombo"
TEMP_ROOT = "/Game/__DAS_Exact60_Migration"
TARGET_RATE = unreal.FrameRate(60, 1)
VERSION = "20260917_DAS_CompositeExact60HzV5"
EXPECTED_TARGET_COUNT = 360
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

COPY_PROPERTIES = (
    "rate_scale",
    "enable_root_motion",
    "force_root_lock",
    "root_motion_root_lock",
    "use_normalized_root_motion_scale",
    "additive_anim_type",
    "ref_pose_type",
    "ref_pose_seq",
    "ref_frame_index",
    "retarget_source",
    "retarget_source_asset",
    "interpolation",
    "bone_compression_settings",
    "curve_compression_settings",
    "variable_frame_stripping_settings",
    "compression_error_threshold_scale",
    "do_not_override_compression",
    "allow_frame_stripping",
    "preview_pose_asset",
)


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def package_path(value) -> str | None:
    if not value:
        return None
    return value.get_path_name().split(".", 1)[0]


def frame_rate(model) -> list[int]:
    value = model.get_frame_rate()
    return [int(value.numerator), int(value.denominator)]


def metadata(asset) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in EAL.get_metadata_tag_values(asset).items()
    }


def discover_targets() -> list[str]:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    result = []
    for data in registry.get_assets_by_path(
        "/Game/_Art/Player/Animation",
        recursive=True,
        include_only_on_disk_assets=True,
    ):
        if str(data.asset_class_path.asset_name) != "AnimSequence":
            continue
        path = str(data.package_name)
        sequence = unreal.load_asset(path)
        if EAL.get_metadata_tag(sequence, "PlaybackDerivation") == "CompositePlayback":
            result.append(path)
    result.sort()
    if len(result) != EXPECTED_TARGET_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TARGET_COUNT} CompositePlayback assets, got {len(result)}"
        )
    allowed_roots = (
        "/Game/_Art/Player/Animation/Playback/DualAxeSword/",
        "/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/",
    )
    outside = [path for path in result if not path.startswith(allowed_roots)]
    if outside:
        raise RuntimeError("CompositePlayback asset left the reviewed roots: " + repr(outside))
    return result


def ensure_write_preconditions(targets: list[str]) -> None:
    if not PREFLIGHT.is_file() or not BACKUP.is_file():
        raise RuntimeError("Exact-60 preflight or immutable backup report is missing")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    backup = json.loads(BACKUP.read_text(encoding="utf-8-sig"))
    if preflight.get("status") != "passed" or preflight.get("target_count") != len(targets):
        raise RuntimeError("Exact-60 preflight contract is not passed")
    if backup.get("status") != "passed" or backup.get("package_count") != len(targets) + 1:
        raise RuntimeError("Exact-60 backup contract is not passed")
    for row in backup["files"]:
        path = pathlib.Path(row["backup"])
        if not path.is_file() or path.stat().st_size != int(row["bytes"]):
            raise RuntimeError("Backup package is missing or changed: " + str(path))


def assert_no_non_bone_data(sequence, path: str) -> None:
    model = sequence.controller.get_model_interface()
    tracks = [
        str(value)
        for value in unreal.AnimationLibrary.get_animation_notify_track_names(sequence)
    ]
    marker_count = sum(
        len(unreal.AnimationLibrary.get_animation_sync_markers_for_track(sequence, track))
        for track in tracks
    )
    if (
        unreal.AnimationLibrary.get_animation_notify_events(sequence)
        or marker_count
        or int(model.get_number_of_float_curves())
        or int(model.get_number_of_transform_curves())
    ):
        raise RuntimeError(
            "Composite playback gained Notify/Marker/Curve data after preflight: " + path
        )


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


def transform_error(left, right) -> list[float]:
    a = transform_values(left)
    b = transform_values(right)
    return [
        max(abs(x - y) for x, y in zip(a[:3], b[:3])),
        min(
            max(abs(x - y) for x, y in zip(a[3:7], b[3:7])),
            max(abs(x + y) for x, y in zip(a[3:7], b[3:7])),
        ),
        max(abs(x - y) for x, y in zip(a[7:], b[7:])),
    ]


def property_snapshot(sequence) -> dict:
    result = {}
    for name in COPY_PROPERTIES:
        try:
            result[name] = sequence.get_editor_property(name)
        except Exception:
            pass
    return result


def clone_properties(sequence, values: dict) -> None:
    for name, value in values.items():
        sequence.set_editor_property(name, value)
    platform_rate = sequence.get_editor_property("platform_target_frame_rate")
    platform_rate.set_editor_property("default", TARGET_RATE)
    overrides = platform_rate.get_editor_property("per_platform")
    if overrides:
        platform_rate.set_editor_property(
            "per_platform", {name: TARGET_RATE for name in overrides}
        )


def metadata_for_exact_grid(
    old_metadata: dict[str, str],
    old_rate: list[int],
    old_frames: int,
    old_duration: float,
    target_frames: int,
    target_duration: float,
) -> dict[str, str]:
    result = dict(old_metadata)
    try:
        contract = json.loads(result.get("TimingContract", "{}"))
    except json.JSONDecodeError:
        contract = {"legacy_text": result.get("TimingContract", "")}
    contract.update(
        {
            "samples": target_frames + 1,
            "duration": target_duration,
            "fps": [60, 1],
            "authored_duration": contract.get("authored_duration", old_duration),
            "pre_exact60_fps": old_rate,
            "pre_exact60_frames": old_frames,
            "pre_exact60_duration": old_duration,
            "duration_quantization_error_seconds": target_duration - old_duration,
            "sampling_policy": (
                "Exact 60/1 Hz; nearest interval count; previous baked timeline "
                "sampled by normalized time so first and last poses remain exact."
            ),
        }
    )
    result["TimingContract"] = json.dumps(contract, ensure_ascii=False)
    result["DASPreviousTimingVersion"] = result.get("DASTimingVersion", "")
    result["DASTimingVersion"] = VERSION
    result["DASExact60Migration"] = json.dumps(
        {
            "previous_fps": old_rate,
            "previous_frames": old_frames,
            "previous_duration": old_duration,
            "fps": [60, 1],
            "frames": target_frames,
            "duration": target_duration,
            "endpoint_preserved": True,
            "mesh_component_scale_used": False,
        },
        ensure_ascii=False,
    )
    return result


def apply_metadata(sequence, values: dict[str, str]) -> None:
    for key, value in values.items():
        EAL.set_metadata_tag(sequence, key, value)


def temp_path(path: str) -> str:
    relative = path.removeprefix("/Game/")
    return TEMP_ROOT + "/" + relative


def sample_tracks(sequence, names, target_frames: int, old_duration: float):
    options = unreal.AnimPoseEvaluationOptions(
        evaluation_type=unreal.AnimDataEvalType.RAW,
        should_retarget=False,
        extract_root_motion=False,
        incorporate_root_motion_into_pose=True,
    )
    positions = [[] for _ in names]
    rotations = [[] for _ in names]
    scales = [[] for _ in names]
    checkpoints = {}
    checkpoint_frames = {
        0,
        target_frames // 4,
        target_frames // 2,
        (target_frames * 3) // 4,
        target_frames,
    }
    for frame in range(target_frames + 1):
        source_time = old_duration * frame / target_frames
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(
            sequence, source_time, options
        )
        if not pose.is_valid():
            raise RuntimeError("Invalid source pose at " + str(source_time))
        checkpoint = {} if frame in checkpoint_frames else None
        for index, name in enumerate(names):
            transform = pose.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
            positions[index].append(
                unreal.Vector(
                    transform.translation.x,
                    transform.translation.y,
                    transform.translation.z,
                )
            )
            rotations[index].append(
                unreal.Quat(
                    transform.rotation.x,
                    transform.rotation.y,
                    transform.rotation.z,
                    transform.rotation.w,
                )
            )
            scales[index].append(
                unreal.Vector(
                    transform.scale3d.x,
                    transform.scale3d.y,
                    transform.scale3d.z,
                )
            )
            if checkpoint is not None:
                checkpoint[str(name)] = transform_values(transform)
        if checkpoint is not None:
            checkpoints[frame] = checkpoint
    return positions, rotations, scales, checkpoints


def make_transform(values: list[float]):
    result = unreal.Transform()
    result.translation = unreal.Vector(*values[:3])
    result.rotation = unreal.Quat(*values[3:7])
    result.scale3d = unreal.Vector(*values[7:10])
    return result


def create_replacement(
    path: str,
    source,
    names,
    positions,
    rotations,
    scales,
    target_frames: int,
    properties: dict,
    metadata_values: dict[str, str],
):
    destination = temp_path(path)
    if EAL.does_asset_exist(destination):
        if not EAL.delete_asset(destination):
            raise RuntimeError("Cannot clear stale migration asset " + destination)
    skeleton = source.get_editor_property("skeleton")
    factory = unreal.AnimSequenceFactory()
    factory.set_editor_property("target_skeleton", skeleton)
    preview_mesh = skeleton.get_skeleton_preview_mesh()
    if preview_mesh:
        factory.set_editor_property("preview_skeletal_mesh", preview_mesh)
    settings = unreal.get_default_object(unreal.AnimationSettings)
    prior_default = settings.get_editor_property("default_frame_rate")
    settings.set_editor_property(
        "default_frame_rate",
        TARGET_RATE,
        notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER,
    )
    try:
        folder, name = destination.rsplit("/", 1)
        replacement = TOOLS.create_asset(name, folder, unreal.AnimSequence, factory)
    finally:
        settings.set_editor_property(
            "default_frame_rate",
            prior_default,
            notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER,
        )
    if not replacement:
        raise RuntimeError("Cannot create exact-60 replacement " + destination)
    controller = unreal.AnimationDataController.cast(replacement.controller)
    controller.open_bracket("Resample DAS Composite playback to exact 60 Hz", False)
    try:
        controller.set_frame_rate(TARGET_RATE, False)
        controller.set_number_of_frames(unreal.FrameNumber(target_frames), False)
        for index, name in enumerate(names):
            if not controller.add_bone_curve(str(name), False):
                raise RuntimeError("Cannot add bone track " + str(name))
            if not controller.set_bone_track_keys(
                str(name), positions[index], rotations[index], scales[index], False
            ):
                raise RuntimeError("Cannot write bone track " + str(name))
    finally:
        controller.close_bracket(False)
    clone_properties(replacement, properties)
    apply_metadata(replacement, metadata_values)
    if not EAL.save_loaded_asset(replacement, only_if_is_dirty=False):
        raise RuntimeError("Cannot save exact-60 replacement " + destination)
    return replacement


def verify_replacement(
    replacement,
    path: str,
    names,
    target_frames: int,
    target_duration: float,
    checkpoints: dict,
    properties: dict,
) -> dict:
    model = replacement.controller.get_model_interface()
    if frame_rate(model) != [60, 1]:
        raise RuntimeError("Replacement frame rate is not 60/1: " + path)
    if int(model.get_number_of_frames()) != target_frames:
        raise RuntimeError("Replacement frame count mismatch: " + path)
    if int(model.get_number_of_keys()) != target_frames + 1:
        raise RuntimeError("Replacement key count mismatch: " + path)
    duration = float(replacement.get_play_length())
    if abs(duration - target_duration) >= 1.0e-5:
        raise RuntimeError("Replacement duration mismatch: " + path)
    actual_names = [str(value).lower() for value in model.get_bone_track_names()]
    if actual_names != [str(value).lower() for value in names]:
        raise RuntimeError("Replacement track order/content mismatch: " + path)
    for name, expected in properties.items():
        actual = replacement.get_editor_property(name)
        if str(actual) != str(expected):
            raise RuntimeError(f"Replacement property mismatch {name}: {path}")
    maximum = [0.0, 0.0, 0.0]
    worst = None
    for mode in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
        options = unreal.AnimPoseEvaluationOptions(
            evaluation_type=mode,
            should_retarget=False,
            extract_root_motion=False,
            incorporate_root_motion_into_pose=True,
        )
        for frame, expected_bones in checkpoints.items():
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(
                replacement, frame, options
            )
            if not pose.is_valid():
                raise RuntimeError("Invalid replacement pose: " + path)
            for name in names:
                actual = pose.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL)
                error = transform_error(actual, make_transform(expected_bones[str(name)]))
                if any(error[index] > maximum[index] for index in range(3)):
                    worst = {
                        "mode": str(mode),
                        "frame": frame,
                        "bone": str(name),
                        "error": error,
                    }
                maximum = [max(maximum[index], error[index]) for index in range(3)]
    if not (maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001):
        raise RuntimeError(f"Replacement pose error {maximum} {worst}: {path}")
    return {
        "duration": duration,
        "maximum_position_error_cm": maximum[0],
        "maximum_quaternion_component_error": maximum[1],
        "maximum_scale_error": maximum[2],
        "worst_pose_sample": worst,
    }


def redirect_live_montage(old_path: str, replacement, duration_scale: float) -> bool:
    montage = unreal.load_asset(MONTAGE_PATH)
    slots = list(montage.get_editor_property("slot_anim_tracks"))
    changed = False
    segment_count = sum(
        len(slot.get_editor_property("anim_track").get_editor_property("anim_segments"))
        for slot in slots
    )
    if segment_count != 1:
        raise RuntimeError(
            "WeakAttack montage changed after preflight; preserve its authored layout before migration"
        )
    for slot_index, slot in enumerate(slots):
        track = slot.get_editor_property("anim_track")
        segments = list(track.get_editor_property("anim_segments"))
        for segment_index, segment in enumerate(segments):
            reference = package_path(segment.get_editor_property("anim_reference"))
            if reference != old_path:
                continue
            start = float(segment.get_editor_property("anim_start_time")) * duration_scale
            end = float(segment.get_editor_property("anim_end_time")) * duration_scale
            play_rate = float(segment.get_editor_property("anim_play_rate"))
            loops = int(segment.get_editor_property("looping_count"))
            segment.set_editor_property("anim_reference", replacement)
            segment.set_editor_property("anim_start_time", start)
            segment.set_editor_property("anim_end_time", end)
            segment.set_editor_property(
                "cached_play_length", (end - start) * loops / abs(play_rate)
            )
            segments[segment_index] = segment
            changed = True
        track.set_editor_property("anim_segments", segments)
        slot.set_editor_property("anim_track", track)
        slots[slot_index] = slot
    if changed:
        montage.set_editor_property("slot_anim_tracks", slots)
        montage_end = max(
            float(segment.get_editor_property("start_pos"))
            + float(segment.get_editor_property("cached_play_length"))
            for slot in slots
            for segment in slot.get_editor_property("anim_track").get_editor_property(
                "anim_segments"
            )
        )
        montage_model = montage.controller.get_model_interface()
        montage_rate = montage_model.get_frame_rate()
        montage_frames = round(
            montage_end * float(montage_rate.numerator) / float(montage_rate.denominator)
        )
        montage.controller.set_number_of_frames(
            unreal.FrameNumber(montage_frames), False
        )
        if not EAL.save_loaded_asset(montage, only_if_is_dirty=False):
            raise RuntimeError("Cannot save redirected WeakAttack montage")
    return changed


def replace_original(path: str, replacement, old_duration: float, target_duration: float):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=True,
        include_soft_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=True,
        include_hard_management_references=True,
    )
    referencers = sorted(
        {
            str(value)
            for value in registry.get_referencers(path, options)
            if str(value).startswith("/Game/")
        }
    )
    unexpected = [value for value in referencers if value != MONTAGE_PATH]
    if unexpected:
        raise RuntimeError("Unexpected playback referencers: " + repr(unexpected))
    montage_changed = redirect_live_montage(
        path, replacement, target_duration / old_duration
    )
    if MONTAGE_PATH in referencers and not montage_changed:
        raise RuntimeError("Registry reports a Montage reference that was not redirected: " + path)
    if not EAL.delete_asset(path):
        raise RuntimeError("Cannot delete superseded playback asset " + path)
    source_temp = package_path(replacement)
    if not EAL.rename_asset(source_temp, path):
        raise RuntimeError(f"Cannot move replacement {source_temp} to {path}")
    current = unreal.load_asset(path)
    if not current:
        raise RuntimeError("Replacement disappeared after rename: " + path)
    if not EAL.save_loaded_asset(current, only_if_is_dirty=False):
        raise RuntimeError("Cannot save renamed replacement " + path)
    if montage_changed:
        montage = unreal.load_asset(MONTAGE_PATH)
        if not EAL.save_loaded_asset(montage, only_if_is_dirty=False):
            raise RuntimeError("Cannot save Montage after replacement rename")
    if EAL.does_asset_exist(source_temp):
        asset = unreal.load_asset(source_temp)
        if asset and asset.get_class().get_name() == "ObjectRedirector":
            EAL.delete_asset(source_temp)
    return current, referencers, montage_changed


def migrate(path: str) -> dict:
    sequence = unreal.load_asset(path)
    if not isinstance(sequence, unreal.AnimSequence):
        raise RuntimeError("Missing target AnimSequence " + path)
    model = sequence.controller.get_model_interface()
    if (
        EAL.get_metadata_tag(sequence, "DASTimingVersion") == VERSION
        and frame_rate(model) == [60, 1]
    ):
        return {"asset": path, "status": "already_current"}
    assert_no_non_bone_data(sequence, path)
    names = list(model.get_bone_track_names())
    old_rate = frame_rate(model)
    old_frames = int(model.get_number_of_frames())
    old_keys = int(model.get_number_of_keys())
    old_duration = float(sequence.get_play_length())
    target_frames = max(1, round(old_duration * 60.0))
    target_duration = target_frames / 60.0
    old_metadata = metadata(sequence)
    properties = property_snapshot(sequence)
    positions, rotations, scales, checkpoints = sample_tracks(
        sequence, names, target_frames, old_duration
    )
    metadata_values = metadata_for_exact_grid(
        old_metadata,
        old_rate,
        old_frames,
        old_duration,
        target_frames,
        target_duration,
    )
    replacement = create_replacement(
        path,
        sequence,
        names,
        positions,
        rotations,
        scales,
        target_frames,
        properties,
        metadata_values,
    )
    verification = verify_replacement(
        replacement,
        path,
        names,
        target_frames,
        target_duration,
        checkpoints,
        properties,
    )
    # ForceDelete refuses to remove an otherwise unreferenced asset while a
    # Python wrapper still owns the old UObject/data-model interface.
    sequence = None
    model = None
    unreal.SystemLibrary.collect_garbage()
    current, referencers, montage_changed = replace_original(
        path, replacement, old_duration, target_duration
    )
    current_model = current.controller.get_model_interface()
    if frame_rate(current_model) != [60, 1]:
        raise RuntimeError("Renamed asset lost exact frame rate: " + path)
    if EAL.get_metadata_tag(current, "DASTimingVersion") != VERSION:
        raise RuntimeError("Renamed asset lost migration metadata: " + path)
    return {
        "asset": path,
        "status": "migrated",
        "source": old_metadata.get("OriginalPackage"),
        "old_fps": old_rate,
        "old_frames": old_frames,
        "old_keys": old_keys,
        "old_duration": old_duration,
        "fps": [60, 1],
        "frames": target_frames,
        "keys": target_frames + 1,
        "duration": verification["duration"],
        "duration_quantization_error_seconds": target_duration - old_duration,
        "track_count": len(names),
        "root_motion": bool(current.get_editor_property("enable_root_motion")),
        "force_root_lock": bool(current.get_editor_property("force_root_lock")),
        "referencers_before_replacement": referencers,
        "montage_reference_updated": montage_changed,
        "mesh_component_scale_used": False,
        **verification,
    }


def load_report() -> dict:
    if REPORT.is_file():
        return json.loads(REPORT.read_text(encoding="utf-8"))
    return {
        "schema": 1,
        "status": "running",
        "version": VERSION,
        "started": datetime.datetime.now().isoformat(),
        "target_count": EXPECTED_TARGET_COUNT,
        "assets": [],
        "failures": [],
    }


def run_batch(start: int, count: int) -> None:
    targets = discover_targets()
    ensure_write_preconditions(targets)
    end = min(len(targets), start + count)
    if start < 0 or start >= len(targets) or end <= start:
        raise RuntimeError(f"Invalid batch range {start}:{end}")
    report = load_report()
    by_asset = {row["asset"]: row for row in report["assets"]}
    try:
        for index in range(start, end):
            path = targets[index]
            prior = by_asset.get(path)
            if prior and prior.get("status") in {"migrated", "already_current"}:
                continue
            entry = migrate(path)
            entry["manifest_index"] = index
            by_asset[path] = entry
            report["assets"] = sorted(
                by_asset.values(), key=lambda value: value["manifest_index"]
            )
            report["completed_count"] = len(report["assets"])
            write(REPORT, report)
        report["status"] = (
            "passed" if len(report["assets"]) == EXPECTED_TARGET_COUNT else "running"
        )
    except Exception:
        report["status"] = "failed"
        report["failures"].append(
            {
                "batch_start": start,
                "batch_end": end,
                "error": traceback.format_exc(),
            }
        )
        raise
    finally:
        report["assets"] = sorted(
            by_asset.values(), key=lambda value: value["manifest_index"]
        )
        report["completed_count"] = len(report["assets"])
        report["updated"] = datetime.datetime.now().isoformat()
        write(REPORT, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "batch": [start, end],
                "completed": report["completed_count"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def cleanup_temp_root() -> None:
    if EAL.does_directory_exist(TEMP_ROOT):
        assets = EAL.list_assets(TEMP_ROOT, recursive=True, include_folder=False)
        non_redirectors = []
        for path in assets:
            asset = unreal.load_asset(path)
            if asset and asset.get_class().get_name() != "ObjectRedirector":
                non_redirectors.append(path)
        if non_redirectors:
            raise RuntimeError("Live migration assets remain: " + repr(non_redirectors))
        EAL.delete_directory(TEMP_ROOT)


def command_range() -> tuple[int, int]:
    start = 0
    count = EXPECTED_TARGET_COUNT
    for part in unreal.SystemLibrary.get_command_line().split():
        if part.startswith("-DASExact60Start="):
            start = int(part.split("=", 1)[1])
        elif part.startswith("-DASExact60Count="):
            count = int(part.split("=", 1)[1])
    return start, count


if __name__ == "__main__":
    run_batch(*command_range())
