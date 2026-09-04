"""Measure component-space foot contacts and loop seams for DAS cyclic clips.

This script is read-only with respect to Content.  It evaluates the raw pose in
component/world space, ranks likely planted-foot frames, and writes the evidence
used by the runtime asset builder when authoring sync markers.
"""

from __future__ import annotations

import json
import math
import os

import unreal


SURVEY_REPORT = "Khazan_DAS_Locomotion_SourceSurvey.json"
PSA_REPORT = "Khazan_DAS_PSA_SourceMetadata.json"
OUTPUT_REPORT = "Khazan_DAS_Locomotion_LoopContacts.json"
LEFT_FOOT = "bip001-l-foot"
RIGHT_FOOT = "bip001-r-foot"
POSE_BONES = (
    "root",
    "bip001",
    "bip001-pelvis",
    "bip001-l-foot",
    "bip001-r-foot",
    "bip001-l-hand",
    "bip001-r-hand",
    "bip001-head",
)


def _reports_dir() -> str:
    path = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(path, exist_ok=True)
    return path


def _load_json(name: str) -> dict:
    with open(os.path.join(_reports_dir(), name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_loop(row: dict) -> bool:
    name = row["asset_name"]
    group = row["group"]

    if group == "Guard":
        return True
    if group == "LockOn":
        return "_Walk_" in name or "_Run_" in name
    if group == "Flow":
        return (
            "_FlowStance_Walk_" in name
            and "ReturnIdle" not in name
            and "Stop" not in name
            and "Turn" not in name
            and "Bridge" not in name
        )
    if group == "Base":
        return name in {
            "CA_P_Kazan_DualAxeSword_Walk_F",
            "CA_P_Kazan_DualAxeSword_Walk_F_Hard",
            "CA_P_Kazan_DualAxeSword_Run_F",
            "CA_P_Kazan_DualAxeSword_Run_F_Hard",
            "CA_P_Kazan_DualAxeSword_Sprint_F",
        }
    return False


def _intended_final_frame(name: str, num_raw_frames: int) -> tuple[int, str]:
    if name.endswith("_Run_F") or name.endswith("_Run_F_Hard"):
        return 20, "first complete 20-frame cycle in the repeated run take"
    if name.endswith("_Sprint_F"):
        return 60, "first complete 60-frame upper-body cycle in the repeated sprint take"
    return max(1, num_raw_frames - 2), "single cycle through the last unique imported key"


def _location(transform) -> list[float]:
    value = transform.translation
    return [float(value.x), float(value.y), float(value.z)]


def _distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def _pose_at(sequence, frame: int):
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    options.set_editor_property("should_retarget", True)
    options.set_editor_property("extract_root_motion", False)
    return unreal.AnimPoseExtensions.get_anim_pose_at_frame(sequence, frame, options)


def _bone_world(pose, bone_name: str) -> list[float]:
    transform = unreal.AnimPoseExtensions.get_bone_pose(
        pose,
        bone_name,
        unreal.AnimPoseSpaces.WORLD,
    )
    return _location(transform)


def _normalise(values: list[float]) -> list[float]:
    low = min(values)
    high = max(values)
    span = high - low
    if span <= 1.0e-8:
        return [0.0 for _ in values]
    return [(value - low) / span for value in values]


def _contact_ranking(positions: list[list[float]], final_frame: int) -> tuple[list[dict], list[float]]:
    # Frame ``final_frame`` is the closing sample and duplicates the loop start.
    # Rank only the unique samples [0, final_frame).
    unique_count = max(1, final_frame)
    heights = [positions[index][2] for index in range(unique_count)]
    speeds = []
    for index in range(unique_count):
        previous_index = (index - 1) % unique_count
        next_index = (index + 1) % unique_count
        speeds.append(_distance(positions[previous_index], positions[next_index]) * 0.5)

    height_score = _normalise(heights)
    speed_score = _normalise(speeds)
    # A planted foot is both low and slow.  Height gets a little more weight so
    # a stationary airborne apex cannot win merely because its speed is zero.
    combined = [0.65 * height_score[i] + 0.35 * speed_score[i] for i in range(unique_count)]
    ranking = sorted(
        (
            {
                "frame": index,
                "height": round(heights[index], 6),
                "speed_per_frame": round(speeds[index], 6),
                "score": round(combined[index], 6),
            }
            for index in range(unique_count)
        ),
        key=lambda row: (row["score"], row["frame"]),
    )
    return ranking[:8], combined


def _circular_distance(a: int, b: int, period: int) -> int:
    direct = abs(a - b)
    return min(direct, period - direct)


def _pick_contact(ranking: list[dict], period: int) -> int:
    # Neighboring frames describe the same plant.  Prefer the center/local best
    # represented by the lowest combined score.
    return int(ranking[0]["frame"])


def _pose_seam(sequence, final_frame: int) -> dict:
    first = _pose_at(sequence, 0)
    candidates = sorted(set(frame for frame in (final_frame - 1, final_frame) if frame >= 0))
    rows = []
    for frame in candidates:
        candidate = _pose_at(sequence, frame)
        deltas = []
        for bone in POSE_BONES:
            start = _bone_world(first, bone)
            end = _bone_world(candidate, bone)
            deltas.append(_distance(start, end))
        rows.append(
            {
                "frame": frame,
                "mean_representative_bone_translation_delta": round(sum(deltas) / len(deltas), 6),
                "max_representative_bone_translation_delta": round(max(deltas), 6),
            }
        )
    return {"candidate_closing_frames": rows}


def main() -> None:
    survey = _load_json(SURVEY_REPORT)
    psa = _load_json(PSA_REPORT)
    psa_by_name = {row["base_name"]: row for row in psa["files"]}

    rows = []
    for source in survey["locomotion_sequences"]:
        if not _is_loop(source):
            continue

        name = source["asset_name"]
        metadata = psa_by_name[name]["animations"][0]
        final_frame, range_reason = _intended_final_frame(name, int(metadata["num_raw_frames"]))
        sequence = unreal.load_asset(source["source_path"])
        if sequence is None:
            raise RuntimeError(f"Could not load loop source: {source['source_path']}")
        if int(unreal.AnimationLibrary.get_num_frames(sequence)) < final_frame:
            raise RuntimeError(f"Source is too short for frame {final_frame}: {source['source_path']}")

        unreal.log(f"Measuring DAS loop contacts: {source['source_path']}")
        poses = [_pose_at(sequence, frame) for frame in range(final_frame + 1)]
        left_positions = [_bone_world(pose, LEFT_FOOT) for pose in poses]
        right_positions = [_bone_world(pose, RIGHT_FOOT) for pose in poses]
        left_ranking, _ = _contact_ranking(left_positions, final_frame)
        right_ranking, _ = _contact_ranking(right_positions, final_frame)
        left_contact = _pick_contact(left_ranking, final_frame)
        right_contact = _pick_contact(right_ranking, final_frame)

        rows.append(
            {
                "source_path": source["source_path"],
                "asset_name": name,
                "group": source["group"],
                "psa_num_raw_frames": int(metadata["num_raw_frames"]),
                "final_frame": final_frame,
                "range_reason": range_reason,
                "left_contact_frame": left_contact,
                "right_contact_frame": right_contact,
                "contact_separation_frames": _circular_distance(
                    left_contact, right_contact, final_frame
                ),
                "left_ranked_candidates": left_ranking,
                "right_ranked_candidates": right_ranking,
                "left_positions": [[round(value, 6) for value in row] for row in left_positions],
                "right_positions": [[round(value, 6) for value in row] for row in right_positions],
                "seam": _pose_seam(sequence, final_frame),
            }
        )

    report = {
        "schema": 1,
        "evaluation_space": "component/world",
        "evaluation_data": "raw",
        "sampled_bones": {"left": LEFT_FOOT, "right": RIGHT_FOOT},
        "note": "Ranked contact candidates are analysis evidence; final authored markers are recorded in the runtime build report.",
        "loop_count": len(rows),
        "loops": rows,
    }
    output = os.path.join(_reports_dir(), OUTPUT_REPORT)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps({"report": output, "loop_count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
