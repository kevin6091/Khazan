"""Fresh-process audit for the generated DAS runtime locomotion library.

Run after ``build_das_locomotion_runtime_library.py``.  The audit only reads
Content, reloads every generated package from disk, validates the source/runtime
contract, and writes a machine-readable report under Saved/ImportReports.
"""

from __future__ import annotations

import json
import math
import os

import unreal


RUNTIME_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword"
BUILD_REPORT = "Khazan_DAS_Locomotion_RuntimeBuild.json"
AUDIT_REPORT = "Khazan_DAS_Locomotion_RuntimeAudit.json"
EXPECTED_SKELETON = "/Game/_Art/Kazan/Character/Meshs/SK_Khazan.SK_Khazan"
SYNC_NAMES = {"LeftFoot", "RightFoot"}


def _report_dir() -> str:
    path = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(path, exist_ok=True)
    return path


def _load_report(name: str) -> dict:
    with open(os.path.join(_report_dir(), name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _vector_distance(a, b) -> float:
    dx = float(a.x) - float(b.x)
    dy = float(a.y) - float(b.y)
    dz = float(a.z) - float(b.z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _quat_angle_degrees(a, b) -> float:
    dot = abs(
        float(a.x) * float(b.x)
        + float(a.y) * float(b.y)
        + float(a.z) * float(b.z)
        + float(a.w) * float(b.w)
    )
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def _markers(sequence, sample_rate: float) -> list[dict]:
    rows = []
    for marker in unreal.AnimationLibrary.get_animation_sync_markers(sequence):
        time = float(marker.get_editor_property("time"))
        rows.append(
            {
                "name": str(marker.get_editor_property("marker_name")),
                "time": round(time, 6),
                "frame": int(round(time * sample_rate)),
            }
        )
    return sorted(rows, key=lambda row: (row["time"], row["name"]))


def _normalise_asset_path(path: str) -> str:
    return path.split(".", 1)[0].rstrip("/")


def main() -> None:
    build = _load_report(BUILD_REPORT)
    expected_rows = build["assets"]
    expected_targets = {row["target"] for row in expected_rows}
    inventory = {
        _normalise_asset_path(path)
        for path in unreal.EditorAssetLibrary.list_assets(
            RUNTIME_ROOT,
            recursive=True,
            include_folder=False,
        )
        if not path.endswith("/")
    }

    errors = []
    warnings = []
    audited = []
    source_paths = set()
    authored_root_track_motion = []

    unexpected = sorted(inventory - expected_targets)
    missing_inventory = sorted(expected_targets - inventory)
    if unexpected:
        errors.append(f"Unexpected runtime assets: {unexpected}")
    if missing_inventory:
        errors.append(f"Runtime assets missing from inventory: {missing_inventory}")

    for expected in expected_rows:
        target_path = expected["target"]
        source_path = expected["source"]
        source_paths.add(source_path)
        target = unreal.load_asset(target_path)
        row_errors = []

        if not isinstance(target, unreal.AnimSequence):
            row_errors.append("target is missing or is not AnimSequence")
            errors.append(f"{target_path}: {row_errors[-1]}")
            continue

        frames = int(unreal.AnimationLibrary.get_num_frames(target))
        play_length = float(target.get_play_length())
        sample_rate = frames / play_length if play_length > 0.0 else 0.0
        skeleton = target.get_editor_property("skeleton")
        skeleton_path = skeleton.get_path_name() if skeleton else None
        marker_rows = _markers(target, sample_rate)
        marker_names = {row["name"] for row in marker_rows}
        marker_frames = [row["frame"] for row in marker_rows]
        root_motion = unreal.AnimationLibrary.is_root_motion_enabled(target)
        force_root_lock = unreal.AnimationLibrary.is_root_motion_lock_forced(target)
        source_tag = unreal.EditorAssetLibrary.get_metadata_tag(target, "Khazan.SourceAnimation")
        role_tag = unreal.EditorAssetLibrary.get_metadata_tag(target, "Khazan.LocomotionRole")

        if frames != int(expected["target_final_frame"]):
            row_errors.append(f"frames={frames}, expected={expected['target_final_frame']}")
        if skeleton_path != EXPECTED_SKELETON:
            row_errors.append(f"skeleton={skeleton_path!r}")
        if root_motion:
            row_errors.append("root motion is enabled")
        if not force_root_lock:
            row_errors.append("force root lock is disabled")
        if source_tag != source_path:
            row_errors.append(f"source metadata={source_tag!r}")
        if role_tag != expected["role"]:
            row_errors.append(f"role metadata={role_tag!r}")
        if not target_path.rsplit("/", 1)[-1].startswith("RT_DAS_"):
            row_errors.append("runtime name does not start with RT_DAS_")

        if expected["is_loop"]:
            if marker_names != SYNC_NAMES:
                row_errors.append(f"loop marker names={sorted(marker_names)}")
            expected_count = 8 if target_path.endswith("RT_DAS_Sprint_Loop") else 2
            if len(marker_rows) != expected_count:
                row_errors.append(
                    f"loop marker count={len(marker_rows)}, expected={expected_count}"
                )
            if any(frame < 0 or frame >= frames for frame in marker_frames):
                row_errors.append(f"marker frame outside [0, {frames}): {marker_frames}")
            if len({(row["name"], row["frame"]) for row in marker_rows}) != len(marker_rows):
                row_errors.append("duplicate marker name/frame pair")
        elif marker_rows:
            row_errors.append(f"non-loop has markers: {marker_rows}")

        track_names = {
            str(name) for name in unreal.AnimationLibrary.get_animation_track_names(target)
        }
        missing_tracks = sorted(
            {"root", "bip001-l-foot", "bip001-r-foot"} - track_names
        )
        if missing_tracks:
            row_errors.append(f"missing required tracks: {missing_tracks}")

        root_start = unreal.AnimationLibrary.get_bone_pose_for_frame(target, "root", 0, False)
        root_end = unreal.AnimationLibrary.get_bone_pose_for_frame(
            target,
            "root",
            frames,
            False,
        )
        root_translation = _vector_distance(root_start.translation, root_end.translation)
        root_rotation = _quat_angle_degrees(root_start.rotation, root_end.rotation)
        if root_translation > 0.001 or root_rotation > 0.01:
            authored_root_track_motion.append(
                {
                    "target": target_path,
                    "translation": round(root_translation, 6),
                    "rotation_degrees": round(root_rotation, 6),
                    "contained_at_runtime_by": "root motion disabled + force root lock",
                }
            )
            # Cyclic Blend Space samples must already be stationary at the root.
            # Starts, stops and turns are allowed to carry authored root tracks;
            # the configured Force Root Lock converts those clips to in-place use.
            if expected["is_loop"]:
                row_errors.append(
                    f"loop root track moved translation={root_translation:.6f}, "
                    f"rotation={root_rotation:.6f}"
                )

        for message in row_errors:
            errors.append(f"{target_path}: {message}")
        audited.append(
            {
                "target": target_path,
                "frames": frames,
                "seconds": round(play_length, 6),
                "sample_rate": round(sample_rate, 6),
                "skeleton": skeleton_path,
                "root_motion_enabled": root_motion,
                "force_root_lock": force_root_lock,
                "root_net_translation": round(root_translation, 6),
                "root_net_rotation_degrees": round(root_rotation, 6),
                "markers": marker_rows,
                "errors": row_errors,
            }
        )

    source_audit = []
    for source_path in sorted(source_paths):
        source = unreal.load_asset(source_path)
        source_errors = []
        if not isinstance(source, unreal.AnimSequence):
            source_errors.append("missing or not AnimSequence")
            frames = None
            markers = []
        else:
            frames = int(unreal.AnimationLibrary.get_num_frames(source))
            markers = unreal.AnimationLibrary.get_animation_sync_markers(source)
            if frames != 249:
                source_errors.append(f"source frame count changed to {frames}")
            if markers:
                source_errors.append(f"source acquired {len(markers)} sync markers")
        for message in source_errors:
            errors.append(f"{source_path}: {message}")
        source_audit.append(
            {
                "source": source_path,
                "frames": frames,
                "sync_marker_count": len(markers),
                "errors": source_errors,
            }
        )

    for limitation in build["source_limitations"]:
        warnings.append(
            f"{limitation['target']}: original PSA has "
            f"{limitation['missing_original_frames']} frames beyond the available FBX export"
        )

    report = {
        "schema": 1,
        "fresh_process_content_load": True,
        "runtime_root": RUNTIME_ROOT,
        "expected_runtime_asset_count": len(expected_targets),
        "inventory_runtime_asset_count": len(inventory),
        "audited_runtime_asset_count": len(audited),
        "audited_source_asset_count": len(source_audit),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "authored_root_track_motion_count": len(authored_root_track_motion),
        "errors": errors,
        "warnings": warnings,
        "authored_root_track_motion": authored_root_track_motion,
        "unexpected_runtime_assets": unexpected,
        "missing_runtime_assets": missing_inventory,
        "runtime_assets": audited,
        "source_assets": source_audit,
    }
    report_path = os.path.join(_report_dir(), AUDIT_REPORT)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "report": report_path,
                "runtime_assets": len(audited),
                "source_assets": len(source_audit),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            ensure_ascii=False,
        )
    )
    if errors:
        raise RuntimeError(f"DAS locomotion audit failed with {len(errors)} errors")


if __name__ == "__main__":
    main()
