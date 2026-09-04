"""Build the complete runtime-ready DualAxeSword locomotion library.

The imported 249-frame FBX assets remain untouched.  Every AnimSequence inside
the DAS Locomotion packages is duplicated into the runtime library, trimmed to
its intended imported key range using the matching original PSA metadata, and
configured for CharacterMovementComponent-authoritative in-place locomotion.

Cyclic clips receive LeftFoot/RightFoot sync markers on the LocomotionSync
track.  UE's native FootstepAnimEventsModifier performs the component-space
contact detection at 120 Hz; clustered detections are consolidated and snapped
back to the imported sequence's 24 fps sample grid.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass

import unreal


RUNTIME_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword"
SURVEY_REPORT = "Khazan_DAS_Locomotion_SourceSurvey.json"
PSA_REPORT = "Khazan_DAS_PSA_SourceMetadata.json"
BUILD_REPORT = "Khazan_DAS_Locomotion_RuntimeBuild.json"
SYNC_TRACK = "LocomotionSync"
FOOT_SAMPLE_RATE = 120
FOOT_GROUND_THRESHOLD = 80.0


BASE_NAMES = {
    "CA_P_Kazan_DualAxeSword_Bridge_Idle_Turn_L_180": "RT_DAS_Bridge_IdleToTurn_L_180",
    "CA_P_Kazan_DualAxeSword_Bridge_Idle_Turn_R_180": "RT_DAS_Bridge_IdleToTurn_R_180",
    "CA_P_Kazan_DualAxeSword_Bridge_Idle_WalkRun_F": "RT_DAS_Walk_Start",
    "CA_P_Kazan_DualAxeSword_Bridge_Stop_Turn_L_180": "RT_DAS_Bridge_StopToTurn_L_180",
    "CA_P_Kazan_DualAxeSword_Bridge_Stop_Turn_R_180": "RT_DAS_Bridge_StopToTurn_R_180",
    "CA_P_Kazan_DualAxeSword_Off_Stand": "RT_DAS_Idle",
    "CA_P_Kazan_DualAxeSword_Off_Stand_Idle_01": "RT_DAS_Idle_Variant_01",
    "CA_P_Kazan_DualAxeSword_Off_Stand_Idle_02": "RT_DAS_Idle_Variant_02",
    "CA_P_Kazan_DualAxeSword_ReturnIdle_Run_F_LF": "RT_DAS_Run_Stop_LF",
    "CA_P_Kazan_DualAxeSword_ReturnIdle_Run_F_RF": "RT_DAS_Run_Stop_RF",
    "CA_P_Kazan_DualAxeSword_ReturnIdle_Walk_F_LF": "RT_DAS_Walk_Stop_LF",
    "CA_P_Kazan_DualAxeSword_ReturnIdle_Walk_F_RF": "RT_DAS_Walk_Stop_RF",
    "CA_P_Kazan_DualAxeSword_Run_F": "RT_DAS_Run_Loop",
    "CA_P_Kazan_DualAxeSword_Run_F_Hard": "RT_DAS_Run_Hard_Loop",
    "CA_P_Kazan_DualAxeSword_Run_MovingTurn_L_180": "RT_DAS_Run_MovingTurn_L_180",
    "CA_P_Kazan_DualAxeSword_Run_MovingTurn_R_180": "RT_DAS_Run_MovingTurn_R_180",
    "CA_P_Kazan_DualAxeSword_Run_StandTurn_L_180": "RT_DAS_Run_TurnInPlace_L_180",
    "CA_P_Kazan_DualAxeSword_Run_StandTurn_R_180": "RT_DAS_Run_TurnInPlace_R_180",
    "CA_P_Kazan_DualAxeSword_Run_Stop_F_LF": "RT_DAS_Run_Stop_Long_LF",
    "CA_P_Kazan_DualAxeSword_Run_Stop_F_RF": "RT_DAS_Run_Stop_Long_RF",
    "CA_P_Kazan_DualAxeSword_Sprint_B_Start": "RT_DAS_Sprint_Start_B",
    "CA_P_Kazan_DualAxeSword_Sprint_BL_Start": "RT_DAS_Sprint_Start_BL",
    "CA_P_Kazan_DualAxeSword_Sprint_BR_Start": "RT_DAS_Sprint_Start_BR",
    "CA_P_Kazan_DualAxeSword_Sprint_F": "RT_DAS_Sprint_Loop",
    "CA_P_Kazan_DualAxeSword_Sprint_F_Start_TEST": "RT_DAS_Sprint_Start_F_Test",
    "CA_P_Kazan_DualAxeSword_Sprint_FL_Start": "RT_DAS_Sprint_Start_FL",
    "CA_P_Kazan_DualAxeSword_Sprint_FR_Start": "RT_DAS_Sprint_Start_FR",
    "CA_P_Kazan_DualAxeSword_Sprint_L_Start": "RT_DAS_Sprint_Start_L",
    "CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_180": "RT_DAS_MovingTurn_L_180",
    "CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_90": "RT_DAS_MovingTurn_L_90",
    "CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_180": "RT_DAS_MovingTurn_R_180",
    "CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_90": "RT_DAS_MovingTurn_R_90",
    "CA_P_Kazan_DualAxeSword_Sprint_R_Start": "RT_DAS_Sprint_Start_R",
    "CA_P_Kazan_DualAxeSword_Sprint_Start": "RT_DAS_Sprint_Start_Default",
    "CA_P_Kazan_DualAxeSword_Sprint_Start_F_LF": "RT_DAS_Run_Start_LF",
    "CA_P_Kazan_DualAxeSword_Sprint_Start_F_RF": "RT_DAS_Run_Start_RF",
    "CA_P_Kazan_DualAxeSword_Sprint_Stop_F": "RT_DAS_Sprint_Stop",
    "CA_P_Kazan_DualAxeSword_Sprint_Stop_F_02": "RT_DAS_Sprint_Stop_02",
    "CA_P_Kazan_DualAxeSword_Stand_Hard": "RT_DAS_Idle_Hard",
    "CA_P_Kazan_DualAxeSword_Walk_F": "RT_DAS_Walk_Loop",
    "CA_P_Kazan_DualAxeSword_Walk_F_Hard": "RT_DAS_Walk_Hard_Loop",
    "CA_P_Kazan_DualAxeSword_Walk_StandTurn_L_180": "RT_DAS_TurnInPlace_L_180",
    "CA_P_Kazan_DualAxeSword_Walk_StandTurn_R_180": "RT_DAS_TurnInPlace_R_180",
    "CA_P_Kazan_DualAxeSword_Walk_Stop_F_LF": "RT_DAS_Walk_Stop_Long_LF",
    "CA_P_Kazan_DualAxeSword_Walk_Stop_F_RF": "RT_DAS_Walk_Stop_Long_RF",
}


# These four clips were already inspected manually in the prior base set.  Keep
# their known plant frames stable while the remaining directional sets use the
# native detector below.
MANUAL_LOOP_MARKERS = {
    "CA_P_Kazan_DualAxeSword_Walk_F": (("LeftFoot", 8), ("RightFoot", 23)),
    "CA_P_Kazan_DualAxeSword_Walk_F_Hard": (("RightFoot", 7), ("LeftFoot", 23)),
    "CA_P_Kazan_DualAxeSword_Run_F": (("LeftFoot", 8), ("RightFoot", 17)),
    "CA_P_Kazan_DualAxeSword_Run_F_Hard": (("LeftFoot", 8), ("RightFoot", 17)),
    "CA_P_Kazan_DualAxeSword_Sprint_F": (
        ("LeftFoot", 4),
        ("RightFoot", 11),
        ("LeftFoot", 19),
        ("RightFoot", 26),
        ("LeftFoot", 34),
        ("RightFoot", 41),
        ("LeftFoot", 49),
        ("RightFoot", 56),
    ),
}


@dataclass(frozen=True)
class ClipSpec:
    source_path: str
    source_name: str
    group: str
    target_folder: str
    target_name: str
    final_frame: int
    psa_num_raw_frames: int
    source_truncated_frames: int
    is_loop: bool
    role: str

    @property
    def target_path(self) -> str:
        return f"{self.target_folder}/{self.target_name}"


def _report_dir() -> str:
    path = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(path, exist_ok=True)
    return path


def _load_report(name: str) -> dict:
    with open(os.path.join(_report_dir(), name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _direction_from_name(name: str, prefix: str, suffix: str = "") -> str:
    value = name[len(prefix) :]
    if suffix and value.endswith(suffix):
        value = value[: -len(suffix)]
    return value


def _target_name(row: dict) -> tuple[str, str]:
    name = row["asset_name"]
    group = row["group"]

    if group == "Base":
        if name not in BASE_NAMES:
            raise RuntimeError(f"No reviewed base runtime name for {name}")
        return RUNTIME_ROOT, BASE_NAMES[name]

    if group == "LockOn":
        folder = f"{RUNTIME_ROOT}/LockOn"
        match = re.search(r"_LockOn_(Walk|Run)_([A-Z]+)(?:_1)?$", name)
        if match:
            gait, direction = match.groups()
            return folder, f"RT_DAS_LockOn_{gait}_{direction}_Loop"
        match = re.search(r"_LockOn_SprintStart_([A-Z]+)(?:_1)?$", name)
        if match:
            return folder, f"RT_DAS_LockOn_Sprint_Start_{match.group(1)}"
        if name.endswith("_LockOn_Sprint_Stop_F"):
            return folder, "RT_DAS_LockOn_Sprint_Stop"
        raise RuntimeError(f"No reviewed LockOn runtime name for {name}")

    if group == "Guard":
        folder = f"{RUNTIME_ROOT}/Guard"
        match = re.search(r"_Com_Guard_Walk_([A-Z]+)_Guard_M1$", name)
        if match:
            return folder, f"RT_DAS_Guard_M1_Walk_{match.group(1)}_Loop"
        match = re.search(r"_Com_Walk_([A-Z]+)_Guard$", name)
        if match:
            return folder, f"RT_DAS_Guard_Walk_{match.group(1)}_Loop"
        raise RuntimeError(f"No reviewed Guard runtime name for {name}")

    if group == "Flow":
        folder = f"{RUNTIME_ROOT}/Flow"
        prefix = "CA_P_Kazan_DualAxeSword_A_FlowStance_"
        if not name.startswith(prefix):
            raise RuntimeError(f"Unexpected Flow name: {name}")
        value = name[len(prefix) :]
        exact = {
            "Bridge_Idle_Turn_L_180": "RT_DAS_Flow_Bridge_IdleToTurn_L_180",
            "Bridge_Idle_Turn_R_180": "RT_DAS_Flow_Bridge_IdleToTurn_R_180",
            "Bridge_Stop_Turn_L_180": "RT_DAS_Flow_Bridge_StopToTurn_L_180",
            "Bridge_Stop_Turn_R_180": "RT_DAS_Flow_Bridge_StopToTurn_R_180",
            "ReturnIdle_Walk_F_LF": "RT_DAS_Flow_Walk_ReturnIdle_LF",
            "ReturnIdle_Walk_F_RF": "RT_DAS_Flow_Walk_ReturnIdle_RF",
            "Stand": "RT_DAS_Flow_Idle",
            "Walk_MovingTurn_L_180": "RT_DAS_Flow_Walk_MovingTurn_L_180",
            "Walk_MovingTurn_R_180": "RT_DAS_Flow_Walk_MovingTurn_R_180",
            "Walk_StandTurn_L_180": "RT_DAS_Flow_TurnInPlace_L_180",
            "Walk_StandTurn_R_180": "RT_DAS_Flow_TurnInPlace_R_180",
            "Walk_Stop_F_LF": "RT_DAS_Flow_Walk_Stop_LF",
            "Walk_Stop_F_RF": "RT_DAS_Flow_Walk_Stop_RF",
        }
        if value in exact:
            return folder, exact[value]
        match = re.fullmatch(r"Walk_([A-Z]+)", value)
        if match:
            return folder, f"RT_DAS_Flow_Walk_{match.group(1)}_Loop"
        raise RuntimeError(f"No reviewed Flow runtime name for {name}")

    raise RuntimeError(f"Unsupported DAS locomotion group {group}: {name}")


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
    return name in MANUAL_LOOP_MARKERS


def _role(row: dict, is_loop: bool) -> str:
    name = row["asset_name"]
    if is_loop:
        return "locomotion_loop"
    if "Stand" in name or "Idle" in name and "Bridge" not in name and "ReturnIdle" not in name:
        return "idle"
    if "Start" in name or "Bridge_Idle_WalkRun" in name:
        return "start"
    if "Stop" in name or "ReturnIdle" in name:
        return "stop"
    if "Turn" in name:
        return "turn"
    if "Bridge" in name:
        return "bridge"
    return "transition"


def _intended_final_frame(name: str, source_frames: int, num_raw_frames: int) -> tuple[int, int, str]:
    if name in {
        "CA_P_Kazan_DualAxeSword_Run_F",
        "CA_P_Kazan_DualAxeSword_Run_F_Hard",
    }:
        return 20, 0, "first complete 20-frame cycle from repeated run take"
    if name == "CA_P_Kazan_DualAxeSword_Sprint_F":
        return 60, 0, "first complete 60-frame upper-body cycle from repeated sprint take"

    # In the Blender FBX conversion the final imported sample is a duplicate of
    # the prior source key.  N PSA raw samples therefore use frame N-2 as the
    # last unique imported key; everything afterwards is export padding.
    intended = max(1, num_raw_frames - 2)
    truncated = max(0, intended - source_frames)
    final_frame = min(source_frames, intended)
    reason = "PSA last unique imported key (NumRawFrames - 2)"
    if truncated:
        reason = "available FBX range; original PSA extends beyond the 249-frame export"
    return final_frame, truncated, reason


def _make_specs(survey: dict, psa: dict) -> list[ClipSpec]:
    psa_by_name = {row["base_name"]: row for row in psa["files"]}
    specs = []
    for row in survey["locomotion_sequences"]:
        name = row["asset_name"]
        metadata_file = psa_by_name.get(name)
        if metadata_file is None:
            raise RuntimeError(f"No original PSA metadata for {name}")
        animations = metadata_file["animations"]
        if len(animations) != 1:
            raise RuntimeError(f"Expected one ANIMINFO record for {name}, got {len(animations)}")
        raw_frames = int(animations[0]["num_raw_frames"])
        source_frames = int(row["source_frames"])
        final_frame, truncated, _ = _intended_final_frame(name, source_frames, raw_frames)
        folder, target_name = _target_name(row)
        is_loop = _is_loop(row)
        specs.append(
            ClipSpec(
                source_path=row["source_path"],
                source_name=name,
                group=row["group"],
                target_folder=folder,
                target_name=target_name,
                final_frame=final_frame,
                psa_num_raw_frames=raw_frames,
                source_truncated_frames=truncated,
                is_loop=is_loop,
                role=_role(row, is_loop),
            )
        )

    target_paths = [spec.target_path for spec in specs]
    if len(target_paths) != len(set(target_paths)):
        duplicates = sorted(path for path in set(target_paths) if target_paths.count(path) > 1)
        raise RuntimeError(f"Duplicate runtime target names: {duplicates}")
    if len(specs) != 107:
        raise RuntimeError(f"Expected the reviewed 107 DAS locomotion sequences, got {len(specs)}")
    return sorted(specs, key=lambda spec: spec.target_path)


def _ensure_sync_track(sequence) -> None:
    tracks = {str(name) for name in unreal.AnimationLibrary.get_animation_notify_track_names(sequence)}
    if SYNC_TRACK not in tracks:
        unreal.AnimationLibrary.add_animation_notify_track(sequence, SYNC_TRACK)


def _foot_definition(bone: str, marker: str):
    definition = unreal.FootDefinition()
    definition.set_editor_property("foot_bone_name", bone)
    definition.set_editor_property("should_generate_sync_markers", True)
    definition.set_editor_property("sync_marker_track_name", SYNC_TRACK)
    definition.set_editor_property("sync_marker_name", marker)
    definition.set_editor_property(
        "sync_marker_detection_technique",
        unreal.DetectionTechnique.FOOT_BONE_REACHES_GROUND,
    )
    return definition


def _detected_marker_frames(sequence, sample_rate: float) -> dict[str, list[float]]:
    unreal.AnimationLibrary.remove_all_animation_sync_markers(sequence)
    modifier = unreal.FootstepAnimEventsModifier()
    modifier.set_editor_property("sample_rate", FOOT_SAMPLE_RATE)
    modifier.set_editor_property("ground_threshold", FOOT_GROUND_THRESHOLD)
    modifier.set_editor_property("should_remove_pre_existing_notifies_or_sync_markers", True)
    modifier.set_editor_property(
        "foot_definitions",
        [
            _foot_definition("bip001-l-foot", "LeftFoot"),
            _foot_definition("bip001-r-foot", "RightFoot"),
        ],
    )
    modifier.on_apply(sequence)

    result = {"LeftFoot": [], "RightFoot": []}
    for marker in unreal.AnimationLibrary.get_animation_sync_markers(sequence):
        name = str(marker.get_editor_property("marker_name"))
        if name in result:
            result[name].append(float(marker.get_editor_property("time")) * sample_rate)
    return result


def _circular_mean(values: list[float], period: float) -> float:
    if not values:
        raise ValueError("Cannot compute a circular mean without values")
    angles = [value / period * math.tau for value in values]
    x = sum(math.cos(angle) for angle in angles)
    y = sum(math.sin(angle) for angle in angles)
    angle = math.atan2(y, x)
    if angle < 0.0:
        angle += math.tau
    return angle / math.tau * period


def _snap_frame(value: float, final_frame: int) -> int:
    return max(0, min(final_frame - 1, int(round(value))))


def _consolidate_markers(
    detected: dict[str, list[float]], final_frame: int, expected_per_foot: int
) -> tuple[list[tuple[str, int]], dict]:
    rows = []
    consolidation = {}
    for marker_name in ("LeftFoot", "RightFoot"):
        values = detected[marker_name]
        if not values:
            consolidation[marker_name] = {"detected_frames": [], "fallback": True}
            continue

        if expected_per_foot == 1:
            frames = [_snap_frame(_circular_mean(values, float(final_frame)), final_frame)]
        else:
            stride_period = float(final_frame) / expected_per_foot
            phases = [value % stride_period for value in values]
            phase = _circular_mean(phases, stride_period)
            frames = sorted(
                {
                    _snap_frame(phase + index * stride_period, final_frame)
                    for index in range(expected_per_foot)
                }
            )

        consolidation[marker_name] = {
            "detected_frames": [round(value, 4) for value in values],
            "consolidated_frames": frames,
            "fallback": False,
        }
        rows.extend((marker_name, frame) for frame in frames)

    left = [frame for name, frame in rows if name == "LeftFoot"]
    right = [frame for name, frame in rows if name == "RightFoot"]
    if not left and not right:
        raise RuntimeError("Native foot detector found no contact for either foot")
    if not left:
        left = [int(round((frame + final_frame * 0.5) % final_frame)) for frame in right]
        rows.extend(("LeftFoot", frame) for frame in left)
        consolidation["LeftFoot"]["consolidated_frames"] = left
    if not right:
        right = [int(round((frame + final_frame * 0.5) % final_frame)) for frame in left]
        rows.extend(("RightFoot", frame) for frame in right)
        consolidation["RightFoot"]["consolidated_frames"] = right

    if expected_per_foot == 1:
        separation = abs(left[0] - right[0])
        separation = min(separation, final_frame - separation)
        if separation < final_frame * 0.30:
            right[0] = int(round((left[0] + final_frame * 0.5) % final_frame))
            rows = [(name, frame) for name, frame in rows if name != "RightFoot"]
            rows.append(("RightFoot", right[0]))
            consolidation["RightFoot"]["phase_separation_fallback"] = True
            consolidation["RightFoot"]["consolidated_frames"] = right

    return sorted(set(rows), key=lambda item: (item[1], item[0])), consolidation


def _write_markers(sequence, markers: tuple | list, sample_rate: float) -> None:
    unreal.AnimationLibrary.remove_all_animation_sync_markers(sequence)
    _ensure_sync_track(sequence)
    for marker_name, frame in sorted(markers, key=lambda item: (item[1], item[0])):
        unreal.AnimationLibrary.add_animation_sync_marker(
            sequence,
            marker_name,
            float(frame) / sample_rate,
            SYNC_TRACK,
        )


def _marker_report(sequence, sample_rate: float) -> list[dict]:
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


def _build_clip(spec: ClipSpec) -> dict:
    if not spec.target_path.startswith(RUNTIME_ROOT + "/"):
        raise RuntimeError(f"Refusing to write outside runtime root: {spec.target_path}")

    source = unreal.load_asset(spec.source_path)
    if not isinstance(source, unreal.AnimSequence):
        raise RuntimeError(f"Source is not an AnimSequence: {spec.source_path}")
    source_frames = int(unreal.AnimationLibrary.get_num_frames(source))
    source_seconds = float(source.get_play_length())
    sample_rate = source_frames / source_seconds if source_seconds > 0.0 else 0.0
    if sample_rate <= 0.0:
        raise RuntimeError(f"Invalid sample rate for {spec.source_path}")
    if source_frames < spec.final_frame:
        raise RuntimeError(
            f"Source has {source_frames} frames but target needs {spec.final_frame}: {spec.source_path}"
        )

    unreal.EditorAssetLibrary.make_directory(spec.target_folder)
    if unreal.EditorAssetLibrary.does_asset_exist(spec.target_path):
        if not unreal.EditorAssetLibrary.delete_asset(spec.target_path):
            raise RuntimeError(f"Could not replace generated asset: {spec.target_path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(spec.source_path, spec.target_path)
    if not isinstance(target, unreal.AnimSequence):
        raise RuntimeError(f"Could not duplicate {spec.source_path} -> {spec.target_path}")

    if source_frames != spec.final_frame:
        target.controller.set_number_of_frames(unreal.FrameNumber(spec.final_frame), False)

    unreal.AnimationLibrary.set_root_motion_enabled(target, False)
    unreal.AnimationLibrary.set_is_root_motion_lock_forced(target, True)
    unreal.AnimationLibrary.set_root_motion_lock_type(target, unreal.RootMotionRootLock.REF_POSE)
    unreal.AnimationLibrary.remove_all_animation_sync_markers(target)

    marker_source = "none"
    marker_diagnostics = None
    if spec.is_loop:
        manual = MANUAL_LOOP_MARKERS.get(spec.source_name)
        if manual is not None:
            markers = manual
            marker_source = "reviewed_manual_frame"
        else:
            detected = _detected_marker_frames(target, sample_rate)
            expected_per_foot = 1
            markers, marker_diagnostics = _consolidate_markers(
                detected,
                spec.final_frame,
                expected_per_foot,
            )
            marker_source = "UE FootstepAnimEventsModifier + consolidation"
        _write_markers(target, markers, sample_rate)

    unreal.EditorAssetLibrary.set_metadata_tag(target, "Khazan.SourceAnimation", spec.source_path)
    unreal.EditorAssetLibrary.set_metadata_tag(target, "Khazan.LocomotionRole", spec.role)
    unreal.EditorAssetLibrary.save_asset(spec.target_path, only_if_is_dirty=False)

    target_frames = int(unreal.AnimationLibrary.get_num_frames(target))
    target_markers = _marker_report(target, sample_rate)
    if target_frames != spec.final_frame:
        raise RuntimeError(
            f"Saved target frame count {target_frames} != expected {spec.final_frame}: {spec.target_path}"
        )
    if spec.is_loop:
        names = {row["name"] for row in target_markers}
        if names != {"LeftFoot", "RightFoot"}:
            raise RuntimeError(f"Loop marker names are incomplete for {spec.target_path}: {names}")
    elif target_markers:
        raise RuntimeError(f"Non-loop unexpectedly has sync markers: {spec.target_path}")

    _, _, trim_reason = _intended_final_frame(
        spec.source_name,
        source_frames,
        spec.psa_num_raw_frames,
    )
    return {
        "source": spec.source_path,
        "target": spec.target_path,
        "group": spec.group,
        "role": spec.role,
        "is_loop": spec.is_loop,
        "source_frames": source_frames,
        "source_seconds": round(source_seconds, 6),
        "source_sample_rate": round(sample_rate, 6),
        "psa_num_raw_frames": spec.psa_num_raw_frames,
        "target_final_frame": target_frames,
        "target_seconds": round(float(target.get_play_length()), 6),
        "removed_padding_frames": source_frames - target_frames,
        "source_truncated_frames": spec.source_truncated_frames,
        "trim_reason": trim_reason,
        "root_motion_enabled": unreal.AnimationLibrary.is_root_motion_enabled(target),
        "force_root_lock": unreal.AnimationLibrary.is_root_motion_lock_forced(target),
        "marker_source": marker_source,
        "marker_diagnostics": marker_diagnostics,
        "markers": target_markers,
    }


def main() -> None:
    survey = _load_report(SURVEY_REPORT)
    psa = _load_report(PSA_REPORT)
    specs = _make_specs(survey, psa)

    rows = []
    for index, spec in enumerate(specs, 1):
        unreal.log(f"Building DAS locomotion [{index}/{len(specs)}]: {spec.target_path}")
        rows.append(_build_clip(spec))

    group_counts = {}
    role_counts = {}
    marker_count = 0
    source_limitations = []
    for row in rows:
        group_counts[row["group"]] = group_counts.get(row["group"], 0) + 1
        role_counts[row["role"]] = role_counts.get(row["role"], 0) + 1
        marker_count += len(row["markers"])
        if row["source_truncated_frames"]:
            source_limitations.append(
                {
                    "source": row["source"],
                    "target": row["target"],
                    "missing_original_frames": row["source_truncated_frames"],
                    "reason": "Blender FBX export ends at frame 249 before the original PSA range",
                }
            )

    report = {
        "schema": 1,
        "runtime_root": RUNTIME_ROOT,
        "source_selection": "all 107 AnimSequence assets in DAS /Locomotion/ packages",
        "source_assets_modified": False,
        "runtime_asset_count": len(rows),
        "group_counts": dict(sorted(group_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "loop_asset_count": sum(1 for row in rows if row["is_loop"]),
        "sync_marker_count": marker_count,
        "root_policy": "in-place; root motion disabled; force root lock; reference-pose lock",
        "sync_policy": {
            "track": SYNC_TRACK,
            "markers": ["LeftFoot", "RightFoot"],
            "native_detector_sample_rate": FOOT_SAMPLE_RATE,
            "native_detector_ground_threshold": FOOT_GROUND_THRESHOLD,
        },
        "source_limitations": source_limitations,
        "name_token_matches_outside_locomotion_excluded": survey[
            "token_matches_outside_locomotion"
        ],
        "assets": rows,
    }
    report_path = os.path.join(_report_dir(), BUILD_REPORT)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "report": report_path,
                "runtime_asset_count": len(rows),
                "group_counts": report["group_counts"],
                "loop_asset_count": report["loop_asset_count"],
                "sync_marker_count": marker_count,
                "source_limitation_count": len(source_limitations),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
