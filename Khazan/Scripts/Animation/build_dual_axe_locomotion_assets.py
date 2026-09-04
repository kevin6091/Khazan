"""Build deterministic runtime locomotion assets for Khazan's DualAxeSword stance.

The imported FBX sequences are preserved as source assets.  FModel/Blender FBX
exports in the current snapshot all arrived as 249-frame sequences even when the
real clip ends much earlier.  This script duplicates only the selected clips,
trims the duplicate to the measured active range, adds reusable foot sync markers,
creates the weapon profile DataAsset, and assigns it to ABP_Player.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import unreal


SOURCE_ROOT = "/Game/_Art/Kazan/Animation/Weapons/DualAxeSword/Shared/Locomotion"
RUNTIME_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword"
PROFILE_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Profiles"
PROFILE_PATH = f"{PROFILE_ROOT}/DA_Locomotion_DualAxeSword"
ABP_PATH = "/Game/_Art/Kazan/Character/Bluprints/ABP_Player"
SYNC_TRACK = "LocomotionSync"


@dataclass(frozen=True)
class ClipSpec:
    source: str
    target_name: str
    final_frame: int
    markers: tuple[tuple[str, int], ...] = ()

    @property
    def source_path(self) -> str:
        return f"{SOURCE_ROOT}/{self.source}"

    @property
    def target_path(self) -> str:
        return f"{RUNTIME_ROOT}/{self.target_name}"


CLIPS = (
    ClipSpec("Idle/CA_P_Kazan_DualAxeSword_Off_Stand", "RT_DAS_Idle", 249),
    ClipSpec(
        "Walk/CA_P_Kazan_DualAxeSword_Walk_F",
        "RT_DAS_Walk_Loop",
        33,
        (("LeftFoot", 8), ("RightFoot", 23)),
    ),
    ClipSpec(
        "Run/CA_P_Kazan_DualAxeSword_Run_F",
        "RT_DAS_Run_Loop",
        20,
        (("LeftFoot", 8), ("RightFoot", 17)),
    ),
    ClipSpec("Bridge/CA_P_Kazan_DualAxeSword_Bridge_Idle_WalkRun_F", "RT_DAS_Walk_Start", 2),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_Start_F_LF", "RT_DAS_Run_Start_LF", 14),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_Start_F_RF", "RT_DAS_Run_Start_RF", 17),
    ClipSpec("Transitions/CA_P_Kazan_DualAxeSword_ReturnIdle_Walk_F_LF", "RT_DAS_Walk_Stop_LF", 23),
    ClipSpec("Transitions/CA_P_Kazan_DualAxeSword_ReturnIdle_Walk_F_RF", "RT_DAS_Walk_Stop_RF", 23),
    ClipSpec("Transitions/CA_P_Kazan_DualAxeSword_ReturnIdle_Run_F_LF", "RT_DAS_Run_Stop_LF", 19),
    ClipSpec("Transitions/CA_P_Kazan_DualAxeSword_ReturnIdle_Run_F_RF", "RT_DAS_Run_Stop_RF", 19),
    ClipSpec("Walk/CA_P_Kazan_DualAxeSword_Walk_StandTurn_L_180", "RT_DAS_TurnInPlace_L_180", 14),
    ClipSpec("Walk/CA_P_Kazan_DualAxeSword_Walk_StandTurn_R_180", "RT_DAS_TurnInPlace_R_180", 14),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_90", "RT_DAS_MovingTurn_L_90", 12),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_90", "RT_DAS_MovingTurn_R_90", 12),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_L_180", "RT_DAS_MovingTurn_L_180", 11),
    ClipSpec("Sprint/CA_P_Kazan_DualAxeSword_Sprint_MovingTurn_R_180", "RT_DAS_MovingTurn_R_180", 11),
)


PROFILE_CLIPS = {
    "idle": "RT_DAS_Idle",
    "walk_loop": "RT_DAS_Walk_Loop",
    "run_loop": "RT_DAS_Run_Loop",
    "walk_start": "RT_DAS_Walk_Start",
    "run_start_left": "RT_DAS_Run_Start_LF",
    "run_start_right": "RT_DAS_Run_Start_RF",
    "walk_stop_left": "RT_DAS_Walk_Stop_LF",
    "walk_stop_right": "RT_DAS_Walk_Stop_RF",
    "run_stop_left": "RT_DAS_Run_Stop_LF",
    "run_stop_right": "RT_DAS_Run_Stop_RF",
    "turn_in_place_left180": "RT_DAS_TurnInPlace_L_180",
    "turn_in_place_right180": "RT_DAS_TurnInPlace_R_180",
    "moving_turn_left90": "RT_DAS_MovingTurn_L_90",
    "moving_turn_right90": "RT_DAS_MovingTurn_R_90",
    "moving_turn_left180": "RT_DAS_MovingTurn_L_180",
    "moving_turn_right180": "RT_DAS_MovingTurn_R_180",
}


PROFILE_VALUES = {
    "profile_name": "DualAxeSword",
    "move_start_speed": 8.0,
    "run_enter_speed": 300.0,
    "run_exit_speed": 240.0,
    "walk_reference_speed": 170.0,
    "run_reference_speed": 470.0,
    "minimum_play_rate": 0.75,
    "maximum_play_rate": 1.3,
    "loop_blend_time": 0.14,
    "one_shot_blend_time": 0.1,
    "stop_blend_time": 0.16,
    "walk_left_contact_phase": 8.0 / 33.0,
    "walk_right_contact_phase": 23.0 / 33.0,
    "run_left_contact_phase": 8.0 / 20.0,
    "run_right_contact_phase": 17.0 / 20.0,
    "moving_turn_minimum_angle": 65.0,
    "turn180_minimum_angle": 135.0,
    "moving_turn_minimum_speed": 100.0,
    "turn_retrigger_delay": 0.3,
    "slot_name": "DefaultSlot",
}


def _load_required(path: str):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"Required asset is missing: {path}")
    return asset


def _build_runtime_clip(spec: ClipSpec) -> dict:
    source = _load_required(spec.source_path)
    source_frames = unreal.AnimationLibrary.get_num_frames(source)
    if source_frames < spec.final_frame:
        raise RuntimeError(
            f"{spec.source_path}: source has {source_frames} frames, expected at least {spec.final_frame}"
        )

    if unreal.EditorAssetLibrary.does_asset_exist(spec.target_path):
        if not unreal.EditorAssetLibrary.delete_asset(spec.target_path):
            raise RuntimeError(f"Could not replace generated asset: {spec.target_path}")

    target = unreal.EditorAssetLibrary.duplicate_asset(spec.source_path, spec.target_path)
    if target is None:
        raise RuntimeError(f"Could not duplicate {spec.source_path} -> {spec.target_path}")

    if source_frames != spec.final_frame:
        target.controller.set_number_of_frames(unreal.FrameNumber(spec.final_frame), False)

    unreal.AnimationLibrary.set_root_motion_enabled(target, False)
    unreal.AnimationLibrary.set_is_root_motion_lock_forced(target, True)
    unreal.AnimationLibrary.set_root_motion_lock_type(target, unreal.RootMotionRootLock.REF_POSE)
    unreal.AnimationLibrary.remove_all_animation_sync_markers(target)

    if spec.markers:
        track_names = {str(name) for name in unreal.AnimationLibrary.get_animation_notify_track_names(target)}
        if SYNC_TRACK not in track_names:
            unreal.AnimationLibrary.add_animation_notify_track(target, SYNC_TRACK)
        for marker_name, frame in spec.markers:
            unreal.AnimationLibrary.add_animation_sync_marker(
                target,
                marker_name,
                frame / 24.0,
                SYNC_TRACK,
            )

    unreal.EditorAssetLibrary.save_asset(spec.target_path, only_if_is_dirty=False)
    target_frames = unreal.AnimationLibrary.get_num_frames(target)
    marker_report = []
    for marker in unreal.AnimationLibrary.get_animation_sync_markers(target):
        marker_report.append(
            {
                "name": str(marker.get_editor_property("marker_name")),
                "time": round(float(marker.get_editor_property("time")), 6),
            }
        )

    return {
        "source": spec.source_path,
        "target": spec.target_path,
        "source_frames": source_frames,
        "target_frames": target_frames,
        "target_seconds": round(float(target.get_play_length()), 6),
        "root_motion_enabled": unreal.AnimationLibrary.is_root_motion_enabled(target),
        "force_root_lock": unreal.AnimationLibrary.is_root_motion_lock_forced(target),
        "markers": marker_report,
        "hard_suffix_excluded": "_Hard" not in spec.source_path,
    }


def _create_or_load_profile():
    profile = unreal.load_asset(PROFILE_PATH)
    if profile is not None:
        return profile

    profile_class = getattr(unreal, "KhazanLocomotionProfile", None)
    if profile_class is None:
        raise RuntimeError("KhazanLocomotionProfile is not loaded. Build the C++ Editor target and restart UE.")

    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", profile_class)
    profile = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "DA_Locomotion_DualAxeSword",
        PROFILE_ROOT,
        profile_class,
        factory,
    )
    if profile is None:
        raise RuntimeError(f"Could not create profile: {PROFILE_PATH}")
    return profile


def _configure_profile(profile) -> None:
    for property_name, target_name in PROFILE_CLIPS.items():
        profile.set_editor_property(property_name, _load_required(f"{RUNTIME_ROOT}/{target_name}"))
    for property_name, value in PROFILE_VALUES.items():
        profile.set_editor_property(property_name, value)
    unreal.EditorAssetLibrary.save_asset(PROFILE_PATH, only_if_is_dirty=False)


def _configure_animation_blueprint(profile) -> dict:
    bp = _load_required(ABP_PATH)
    generated_class = bp.generated_class()
    if generated_class is None:
        raise RuntimeError("ABP_Player has no generated class")

    cdo = unreal.get_default_object(generated_class)
    cdo.set_editor_property("locomotion_profile", profile)

    sequence_players = bp.get_nodes_of_class(unreal.AnimGraphNode_SequencePlayer)
    if len(sequence_players) != 1:
        raise RuntimeError(f"ABP_Player expected one fallback SequencePlayer, got {len(sequence_players)}")
    fallback_node = sequence_players[0]
    fallback_data = fallback_node.get_editor_property("node")
    fallback_data.set_editor_property("sequence", _load_required(f"{RUNTIME_ROOT}/RT_DAS_Idle"))
    fallback_data.set_editor_property("loop_animation", True)
    fallback_node.set_editor_property("node", fallback_data)

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    status = str(bp.get_editor_property("status"))
    unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)

    slot_nodes = bp.get_nodes_of_class(unreal.AnimGraphNode_Slot)
    root_nodes = bp.get_nodes_of_class(unreal.AnimGraphNode_Root)
    state_machine_nodes = bp.get_nodes_of_class(unreal.AnimGraphNode_StateMachine)
    return {
        "path": ABP_PATH,
        "parent_class": bp.get_blueprint_parent_class().get_path_name(),
        "compile_status": status,
        "slot_node_count": len(slot_nodes),
        "root_node_count": len(root_nodes),
        "state_machine_node_count": len(state_machine_nodes),
        "profile_on_cdo": cdo.get_editor_property("locomotion_profile").get_path_name(),
    }


def main() -> None:
    clip_report = [_build_runtime_clip(spec) for spec in CLIPS]
    profile = _create_or_load_profile()
    _configure_profile(profile)
    abp_report = _configure_animation_blueprint(profile)

    report = {
        "schema": 1,
        "source_snapshot": "FModel -> Blender FBX Part_08_351_to_400",
        "source_root": SOURCE_ROOT,
        "runtime_root": RUNTIME_ROOT,
        "profile": PROFILE_PATH,
        "hard_suffix_policy": "excluded",
        "clips": clip_report,
        "animation_blueprint": abp_report,
        "all_checks_passed": all(
            row["target_frames"] <= row["source_frames"]
            and not row["root_motion_enabled"]
            and row["force_root_lock"]
            and row["hard_suffix_excluded"]
            for row in clip_report
        ),
    }

    report_dir = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "Khazan_DualAxe_Locomotion_Build.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    unreal.log(f"Khazan locomotion runtime assets built: {len(clip_report)} clips")
    unreal.log(f"Report: {report_path}")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
