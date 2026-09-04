"""Inventory and measure imported DualAxeSword locomotion AnimSequences.

This script is read-only with respect to Content.  It records every AnimSequence
under a DualAxeSword ``Locomotion`` package, estimates the first frame of a
constant trailing pose, samples root displacement, and exports foot trajectories
for later contact-marker authoring.

Run through UnrealEditor-Cmd with the project closed in the interactive editor.
"""

from __future__ import annotations

import json
import math
import os
from typing import Iterable

import unreal


SOURCE_ROOT = "/Game/_Art/Kazan/Animation/Weapons/DualAxeSword"
REPORT_NAME = "Khazan_DAS_Locomotion_SourceSurvey.json"

LOCOMOTION_TOKENS = (
    "idle",
    "stand",
    "walk",
    "jog",
    "run",
    "sprint",
    "turn",
    "returnidle",
    "stop",
    "bridge",
)

REPRESENTATIVE_BONE_CANDIDATES = (
    "root",
    "bip001",
    "bip001-pelvis",
    "bip001-spine",
    "bip001-spine1",
    "bip001-head",
    "bip001-l-hand",
    "bip001-r-hand",
    "bip001-l-foot",
    "bip001-r-foot",
)

ROOT_BONE_CANDIDATES = ("root", "bip001")
LEFT_FOOT_CANDIDATES = ("bip001-l-foot", "foot_l", "ik_foot_l")
RIGHT_FOOT_CANDIDATES = ("bip001-r-foot", "foot_r", "ik_foot_r")

# The imported clips have exactly repeated trailing keys.  These tolerances are
# deliberately small: they suppress compression noise without considering an
# actual animated pose to be a fixed tail.
TRANSLATION_EPSILON = 1.0e-3
ROTATION_EPSILON_DEGREES = 1.0e-2
SCALE_EPSILON = 1.0e-5


def _vector_tuple(value) -> tuple[float, float, float]:
    return (float(value.x), float(value.y), float(value.z))


def _quat_tuple(value) -> tuple[float, float, float, float]:
    return (float(value.x), float(value.y), float(value.z), float(value.w))


def _vector_distance(a, b) -> float:
    dx = float(a.x) - float(b.x)
    dy = float(a.y) - float(b.y)
    dz = float(a.z) - float(b.z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _quat_angle_degrees(a, b) -> float:
    ax, ay, az, aw = _quat_tuple(a)
    bx, by, bz, bw = _quat_tuple(b)
    dot = abs(ax * bx + ay * by + az * bz + aw * bw)
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def _max_scale_delta(a, b) -> float:
    return max(
        abs(float(a.x) - float(b.x)),
        abs(float(a.y) - float(b.y)),
        abs(float(a.z) - float(b.z)),
    )


def _transform_delta(a, b) -> tuple[float, float, float]:
    return (
        _vector_distance(a.translation, b.translation),
        _quat_angle_degrees(a.rotation, b.rotation),
        _max_scale_delta(a.scale3d, b.scale3d),
    )


def _transforms_differ(a, b) -> bool:
    translation, rotation, scale = _transform_delta(a, b)
    return (
        translation > TRANSLATION_EPSILON
        or rotation > ROTATION_EPSILON_DEGREES
        or scale > SCALE_EPSILON
    )


def _pose(sequence, bone_name: str, frame: int):
    return unreal.AnimationLibrary.get_bone_pose_for_frame(
        sequence,
        bone_name,
        int(frame),
        False,
    )


def _first_existing(track_names: set[str], candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in track_names:
            return candidate
    return None


def _estimate_final_frame(sequence, frame_count: int, bones: list[str]) -> tuple[int, int]:
    """Return (frame-to-keep, repeated-tail-frame-count).

    ``set_number_of_frames(N)`` keeps animation time through frame N.  If frame
    N is the first key of the final constant pose, N is the correct value to use.
    """

    if frame_count <= 1 or not bones:
        return frame_count, 0

    final_poses = {bone: _pose(sequence, bone, frame_count) for bone in bones}
    last_frame_different_from_final = -1

    for frame in range(frame_count - 1, -1, -1):
        if any(_transforms_differ(_pose(sequence, bone, frame), final_poses[bone]) for bone in bones):
            last_frame_different_from_final = frame
            break

    if last_frame_different_from_final < 0:
        return 1, max(0, frame_count - 1)

    first_constant_final_frame = min(frame_count, last_frame_different_from_final + 1)
    repeated_tail_frames = max(0, frame_count - first_constant_final_frame)
    return max(1, first_constant_final_frame), repeated_tail_frames


def _sample_bone_track(sequence, bone_name: str | None, final_frame: int) -> list[list[float]]:
    if not bone_name:
        return []
    samples = []
    for frame in range(final_frame + 1):
        transform = _pose(sequence, bone_name, frame)
        samples.append([round(value, 6) for value in _vector_tuple(transform.translation)])
    return samples


def _root_report(sequence, track_names: set[str], final_frame: int) -> dict:
    rows = []
    for bone_name in ROOT_BONE_CANDIDATES:
        if bone_name not in track_names:
            continue
        start = _pose(sequence, bone_name, 0)
        end = _pose(sequence, bone_name, final_frame)
        translation = _vector_distance(start.translation, end.translation)
        rotation = _quat_angle_degrees(start.rotation, end.rotation)
        rows.append(
            {
                "bone": bone_name,
                "start_translation": [round(v, 6) for v in _vector_tuple(start.translation)],
                "end_translation": [round(v, 6) for v in _vector_tuple(end.translation)],
                "net_translation": round(translation, 6),
                "net_rotation_degrees": round(rotation, 6),
            }
        )
    authored_root = next((row for row in rows if row["bone"] == "root"), None)
    return {
        "tracks": rows,
        "authored_root_track": authored_root,
        "root_track_stationary": bool(authored_root)
        and authored_root["net_translation"] <= 0.001
        and authored_root["net_rotation_degrees"] <= 0.01,
        "note": "bip001 is reported as a body track and is not used to decide whether the authored root track is stationary.",
    }


def _marker_report(sequence) -> list[dict]:
    markers = []
    for marker in unreal.AnimationLibrary.get_animation_sync_markers(sequence):
        markers.append(
            {
                "name": str(marker.get_editor_property("marker_name")),
                "time": round(float(marker.get_editor_property("time")), 6),
                "track_index": int(marker.get_editor_property("track_index")),
            }
        )
    return sorted(markers, key=lambda row: (row["time"], row["name"]))


def _group(path: str) -> str:
    if "/Shared/Combat/Defense/Guard/Locomotion/" in path:
        return "Guard"
    if "/Styles/Flow/Locomotion/" in path:
        return "Flow"
    if "/Shared/Locomotion/LockOn/" in path:
        return "LockOn"
    if "/Shared/Locomotion/" in path:
        return "Base"
    return "Other"


def _is_locomotion_package(path: str) -> bool:
    return "/Locomotion/" in path


def _has_locomotion_token(asset_name: str) -> bool:
    lowered = asset_name.lower().replace("_", "")
    return any(token in lowered for token in LOCOMOTION_TOKENS)


def _analyze(path: str, sequence) -> dict:
    track_names = {str(name) for name in unreal.AnimationLibrary.get_animation_track_names(sequence)}
    representative_bones = [bone for bone in REPRESENTATIVE_BONE_CANDIDATES if bone in track_names]
    source_frames = int(unreal.AnimationLibrary.get_num_frames(sequence))
    final_frame, tail_frames = _estimate_final_frame(sequence, source_frames, representative_bones)
    play_length = float(sequence.get_play_length())
    frame_rate = source_frames / play_length if play_length > 0.0 else 0.0

    skeleton = sequence.get_editor_property("skeleton")
    skeleton_path = skeleton.get_path_name() if skeleton else None
    left_foot = _first_existing(track_names, LEFT_FOOT_CANDIDATES)
    right_foot = _first_existing(track_names, RIGHT_FOOT_CANDIDATES)

    return {
        "source_path": path,
        "asset_name": path.rsplit("/", 1)[-1],
        "group": _group(path),
        "source_frames": source_frames,
        "source_seconds": round(play_length, 6),
        "sample_rate": round(frame_rate, 6),
        "estimated_final_frame": final_frame,
        "estimated_seconds": round(final_frame / frame_rate, 6) if frame_rate > 0.0 else 0.0,
        "constant_tail_frames": tail_frames,
        "constant_tail_seconds": round(tail_frames / frame_rate, 6) if frame_rate > 0.0 else 0.0,
        "skeleton": skeleton_path,
        "track_count": len(track_names),
        "track_names": sorted(track_names),
        "representative_bones": representative_bones,
        "left_foot_bone": left_foot,
        "right_foot_bone": right_foot,
        "root": _root_report(sequence, track_names, final_frame),
        "existing_markers": _marker_report(sequence),
        "left_foot_positions": _sample_bone_track(sequence, left_foot, final_frame),
        "right_foot_positions": _sample_bone_track(sequence, right_foot, final_frame),
    }


def main() -> None:
    all_paths = sorted(
        path
        for path in unreal.EditorAssetLibrary.list_assets(SOURCE_ROOT, recursive=True, include_folder=False)
        if not path.endswith("/")
    )

    locomotion_rows = []
    token_matches_outside_locomotion = []
    non_sequence_locomotion_assets = []

    for object_path in all_paths:
        package_path = object_path.split(".", 1)[0]
        asset_name = package_path.rsplit("/", 1)[-1]
        in_locomotion_path = _is_locomotion_package(package_path)
        token_match = _has_locomotion_token(asset_name)

        if not in_locomotion_path and not token_match:
            continue

        asset = unreal.load_asset(package_path)
        if not isinstance(asset, unreal.AnimSequence):
            if in_locomotion_path:
                non_sequence_locomotion_assets.append(
                    {
                        "path": package_path,
                        "class": asset.get_class().get_path_name() if asset else None,
                    }
                )
            continue

        if in_locomotion_path:
            unreal.log(f"Surveying DAS locomotion: {package_path}")
            locomotion_rows.append(_analyze(package_path, asset))
        else:
            token_matches_outside_locomotion.append(
                {
                    "path": package_path,
                    "reason": "locomotion-name token outside a Locomotion package",
                }
            )

    group_counts = {}
    for row in locomotion_rows:
        group_counts[row["group"]] = group_counts.get(row["group"], 0) + 1

    report = {
        "schema": 3,
        "source_root": SOURCE_ROOT,
        "selection_rule": "AnimSequence assets whose package path contains /Locomotion/",
        "locomotion_sequence_count": len(locomotion_rows),
        "group_counts": dict(sorted(group_counts.items())),
        "locomotion_sequences": locomotion_rows,
        "token_matches_outside_locomotion": token_matches_outside_locomotion,
        "non_sequence_locomotion_assets": non_sequence_locomotion_assets,
    }

    report_dir = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, REPORT_NAME)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    unreal.log(f"DAS locomotion source survey complete: {len(locomotion_rows)} sequences")
    unreal.log(f"Report: {report_path}")
    print(json.dumps({key: report[key] for key in ("schema", "locomotion_sequence_count", "group_counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
