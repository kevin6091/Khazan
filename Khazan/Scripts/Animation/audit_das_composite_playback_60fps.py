"""Fresh-process audit for the exact-60 DualAxeSword Composite playback migration."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
PREFLIGHT_PATH = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Preflight_20260917.json"
)
BACKUP_PATH = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Backup_20260917.json"
)
IMPORT_PATH = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_Import_20260917.json"
)
REPORT_PATH = (
    PROJECT
    / "Saved/ImportReports/Khazan_DAS_CompositeExact60_FinalAudit_20260917.json"
)
MONTAGE_PATH = "/Game/_Art/Kazan/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAtkCombo"
TEMP_ROOT = "/Game/__DAS_Exact60_Migration"
VERSION = "20260917_DAS_CompositeExact60HzV5"
EAL = unreal.EditorAssetLibrary


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(value) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def package_path(value) -> str | None:
    if not value:
        return None
    return value.get_path_name().split(".", 1)[0]


def rate_pair(value) -> list[int]:
    return [int(value.numerator), int(value.denominator)]


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
    if not all(math.isfinite(value) for value in a + b):
        raise RuntimeError("Non-finite animation transform")
    return [
        max(abs(x - y) for x, y in zip(a[:3], b[:3])),
        min(
            max(abs(x - y) for x, y in zip(a[3:7], b[3:7])),
            max(abs(x + y) for x, y in zip(a[3:7], b[3:7])),
        ),
        max(abs(x - y) for x, y in zip(a[7:], b[7:])),
    ]


def verify_backup(backup: dict) -> int:
    count = 0
    for row in backup["files"]:
        path = pathlib.Path(row["backup"])
        if (
            not path.is_file()
            or path.stat().st_size != int(row["bytes"])
            or sha256(path) != str(row["sha256"]).upper()
        ):
            raise RuntimeError("Immutable backup verification failed: " + str(path))
        count += 1
    return count


def pose_compression_error(sequence, names, frames) -> list[float]:
    raw_options = unreal.AnimPoseEvaluationOptions(
        evaluation_type=unreal.AnimDataEvalType.RAW,
        should_retarget=False,
        extract_root_motion=False,
        incorporate_root_motion_into_pose=True,
    )
    compressed_options = unreal.AnimPoseEvaluationOptions(
        evaluation_type=unreal.AnimDataEvalType.COMPRESSED,
        should_retarget=False,
        extract_root_motion=False,
        incorporate_root_motion_into_pose=True,
    )
    maximum = [0.0, 0.0, 0.0]
    for frame in frames:
        raw = unreal.AnimPoseExtensions.get_anim_pose_at_frame(
            sequence, frame, raw_options
        )
        compressed = unreal.AnimPoseExtensions.get_anim_pose_at_frame(
            sequence, frame, compressed_options
        )
        if not raw.is_valid() or not compressed.is_valid():
            raise RuntimeError("Invalid RAW/COMPRESSED pose")
        for name in names:
            error = transform_error(
                raw.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL),
                compressed.get_bone_pose(name, unreal.AnimPoseSpaces.LOCAL),
            )
            maximum = [max(maximum[index], error[index]) for index in range(3)]
    if not (maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001):
        raise RuntimeError("Compressed pose error exceeds the reviewed limits: " + repr(maximum))
    return maximum


def verify_montage() -> dict:
    montage = unreal.load_asset(MONTAGE_PATH)
    if not isinstance(montage, unreal.AnimMontage):
        raise RuntimeError("WeakAttack montage is missing")
    slots = list(montage.get_editor_property("slot_anim_tracks"))
    segments = [
        segment
        for slot in slots
        for segment in slot.get_editor_property("anim_track").get_editor_property(
            "anim_segments"
        )
    ]
    if len(segments) != 1:
        raise RuntimeError("WeakAttack montage changed during the exact-60 migration")
    segment = segments[0]
    reference = segment.get_editor_property("anim_reference")
    expected_path = "/Game/_Art/Kazan/Animation/InGame/DAS/WeakAttack/DAS_Khazan_WeakAtk01"
    if package_path(reference) != expected_path:
        raise RuntimeError("WeakAttack montage reference changed unexpectedly")
    reference_length = float(reference.get_play_length())
    end_time = float(segment.get_editor_property("anim_end_time"))
    cached = float(segment.get_editor_property("cached_play_length"))
    montage_length = float(montage.get_play_length())
    if (
        abs(end_time - reference_length) >= 1.0e-5
        or abs(cached - reference_length) >= 1.0e-5
        or abs(montage_length - reference_length) >= 1.0e-5
    ):
        raise RuntimeError("WeakAttack montage cached timing was not refreshed")
    if abs(float(segment.get_editor_property("anim_play_rate")) - 1.0) >= 1.0e-7:
        raise RuntimeError("WeakAttack montage segment rate is not 1.0")
    if abs(float(montage.get_editor_property("rate_scale")) - 1.0) >= 1.0e-7:
        raise RuntimeError("WeakAttack montage rate scale is not 1.0")
    return {
        "asset": MONTAGE_PATH,
        "sequence": expected_path,
        "segment_end": end_time,
        "cached_play_length": cached,
        "montage_length": montage_length,
        "segment_rate": float(segment.get_editor_property("anim_play_rate")),
        "montage_rate_scale": float(montage.get_editor_property("rate_scale")),
        "sections": [
            str(montage.get_section_name(index))
            for index in range(montage.get_num_sections())
        ],
    }


def main() -> None:
    result = {"schema": 1, "status": "running", "version": VERSION, "assets": []}
    try:
        preflight = read(PREFLIGHT_PATH)
        backup = read(BACKUP_PATH)
        imported = read(IMPORT_PATH)
        if preflight.get("status") != "passed" or preflight.get("target_count") != 360:
            raise RuntimeError("Preflight contract is not passed")
        if backup.get("status") != "passed" or backup.get("package_count") != 361:
            raise RuntimeError("Backup contract is not passed")
        if imported.get("status") != "passed" or imported.get("completed_count") != 360:
            raise RuntimeError("Import contract is not passed")
        if len(imported.get("assets", [])) != 360:
            raise RuntimeError("Import asset report is incomplete")
        result["backup_files_verified"] = verify_backup(backup)

        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.search_all_assets(True)
        current = []
        for data in registry.get_assets_by_path(
            "/Game/_Art/Kazan/Animation", True, True
        ):
            if str(data.asset_class_path.asset_name) != "AnimSequence":
                continue
            path = str(data.package_name)
            sequence = unreal.load_asset(path)
            if EAL.get_metadata_tag(sequence, "PlaybackDerivation") == "CompositePlayback":
                current.append(path)
        current.sort()
        expected_rows = {row["asset"]: row for row in preflight["assets"]}
        if current != sorted(expected_rows):
            raise RuntimeError("CompositePlayback inventory changed")

        compression_maximum = [0.0, 0.0, 0.0]
        root_motion_assets = 0
        force_root_lock_assets = 0
        weak_attack = []
        for index, path in enumerate(current):
            expected = expected_rows[path]
            sequence = unreal.load_asset(path)
            model = sequence.controller.get_model_interface()
            rate = model.get_frame_rate()
            frames = int(model.get_number_of_frames())
            keys = int(model.get_number_of_keys())
            duration = float(sequence.get_play_length())
            if rate_pair(rate) != [60, 1]:
                raise RuntimeError("Non-exact frame rate: " + path)
            if frames != int(expected["target_frames"]) or keys != frames + 1:
                raise RuntimeError("Frame/key invariant failed: " + path)
            if abs(duration - frames / 60.0) >= 1.0e-5:
                raise RuntimeError("Duration/grid invariant failed: " + path)
            if EAL.get_metadata_tag(sequence, "DASTimingVersion") != VERSION:
                raise RuntimeError("Timing version mismatch: " + path)
            contract = json.loads(EAL.get_metadata_tag(sequence, "TimingContract"))
            if (
                contract.get("fps") != [60, 1]
                or int(contract.get("samples", 0)) != keys
                or abs(float(contract.get("duration", -1.0)) - frames / 60.0) >= 1.0e-7
            ):
                raise RuntimeError("Timing metadata mismatch: " + path)
            platform_rate = sequence.get_editor_property("platform_target_frame_rate")
            if rate_pair(platform_rate.get_editor_property("default")) != [60, 1]:
                raise RuntimeError("Platform target frame rate mismatch: " + path)
            overrides = platform_rate.get_editor_property("per_platform")
            if any(rate_pair(value) != [60, 1] for value in overrides.values()):
                raise RuntimeError("Platform frame-rate override mismatch: " + path)
            if abs(float(sequence.get_editor_property("rate_scale")) - float(expected["rate_scale"])) >= 1.0e-7:
                raise RuntimeError("RateScale changed: " + path)
            root_motion = bool(sequence.get_editor_property("enable_root_motion"))
            force_root_lock = bool(sequence.get_editor_property("force_root_lock"))
            if root_motion != bool(expected["root_motion"]):
                raise RuntimeError("Root Motion flag changed: " + path)
            if force_root_lock != bool(expected["force_root_lock"]):
                raise RuntimeError("Force Root Lock flag changed: " + path)
            names = list(model.get_bone_track_names())
            if len(names) != int(expected["track_count"]):
                raise RuntimeError("Track count changed: " + path)
            maximum = pose_compression_error(
                sequence, names, sorted({0, frames // 2, frames})
            )
            compression_maximum = [
                max(compression_maximum[axis], maximum[axis]) for axis in range(3)
            ]
            row = {
                "asset": path,
                "fps": [60, 1],
                "frames": frames,
                "keys": keys,
                "duration": duration,
                "duration_quantization_error_seconds": frames / 60.0
                - float(expected["old_duration"]),
                "track_count": len(names),
                "root_motion": root_motion,
                "force_root_lock": force_root_lock,
                "compression_error": maximum,
            }
            result["assets"].append(row)
            if "/InGame/DAS/WeakAttack/" in path:
                weak_attack.append(row)
            root_motion_assets += int(root_motion)
            force_root_lock_assets += int(force_root_lock)
            if (index + 1) % 50 == 0:
                print("DAS_EXACT60_AUDIT", index + 1, "/", len(current), flush=True)

        if EAL.does_directory_exist(TEMP_ROOT) and EAL.list_assets(
            TEMP_ROOT, recursive=True, include_folder=False
        ):
            raise RuntimeError("Migration temp assets remain")
        result["asset_count"] = len(result["assets"])
        result["exact_60_assets"] = len(result["assets"])
        result["root_motion_assets"] = root_motion_assets
        result["force_root_lock_assets"] = force_root_lock_assets
        result["weak_attack_assets"] = weak_attack
        result["maximum_abs_duration_quantization_seconds"] = max(
            abs(row["duration_quantization_error_seconds"])
            for row in result["assets"]
        )
        result["maximum_compression_error"] = {
            "position_cm": compression_maximum[0],
            "quaternion_component": compression_maximum[1],
            "scale": compression_maximum[2],
        }
        result["montage"] = verify_montage()
        result["temporary_mesh_component_scale_used"] = False
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
                "exact_60_assets": result.get("exact_60_assets"),
                "backup_files_verified": result.get("backup_files_verified"),
                "maximum_compression_error": result.get("maximum_compression_error"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
