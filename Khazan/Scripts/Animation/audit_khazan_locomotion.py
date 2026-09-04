"""Audit the generated DualAxeSword locomotion profile and ABP wiring."""

from __future__ import annotations

import json
import os

import unreal


RUNTIME_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword"
PROFILE_PATH = "/Game/_Art/Kazan/Animation/Locomotion/Profiles/DA_Locomotion_DualAxeSword"
ABP_PATH = "/Game/_Art/Kazan/Character/Bluprints/ABP_Player"

EXPECTED_FRAMES = {
    "RT_DAS_Idle": 249,
    "RT_DAS_Walk_Loop": 33,
    "RT_DAS_Run_Loop": 20,
    "RT_DAS_Walk_Start": 2,
    "RT_DAS_Run_Start_LF": 14,
    "RT_DAS_Run_Start_RF": 17,
    "RT_DAS_Walk_Stop_LF": 23,
    "RT_DAS_Walk_Stop_RF": 23,
    "RT_DAS_Run_Stop_LF": 19,
    "RT_DAS_Run_Stop_RF": 19,
    "RT_DAS_TurnInPlace_L_180": 14,
    "RT_DAS_TurnInPlace_R_180": 14,
    "RT_DAS_MovingTurn_L_90": 12,
    "RT_DAS_MovingTurn_R_90": 12,
    "RT_DAS_MovingTurn_L_180": 11,
    "RT_DAS_MovingTurn_R_180": 11,
}

PROFILE_PROPERTIES = (
    "idle",
    "walk_loop",
    "run_loop",
    "walk_start",
    "run_start_left",
    "run_start_right",
    "walk_stop_left",
    "walk_stop_right",
    "run_stop_left",
    "run_stop_right",
    "turn_in_place_left180",
    "turn_in_place_right180",
    "moving_turn_left90",
    "moving_turn_right90",
    "moving_turn_left180",
    "moving_turn_right180",
)


def _connected_node_names(pin) -> list[str]:
    return [item.get_owning_node().get_name() for item in pin.list_connected_pins()]


def main() -> None:
    checks = []
    clip_rows = []

    for asset_name, expected_frames in EXPECTED_FRAMES.items():
        path = f"{RUNTIME_ROOT}/{asset_name}"
        asset = unreal.load_asset(path)
        exists = asset is not None
        frames = unreal.AnimationLibrary.get_num_frames(asset) if exists else None
        root_motion = unreal.AnimationLibrary.is_root_motion_enabled(asset) if exists else None
        force_lock = unreal.AnimationLibrary.is_root_motion_lock_forced(asset) if exists else None
        row = {
            "path": path,
            "exists": exists,
            "frames": frames,
            "expected_frames": expected_frames,
            "root_motion_enabled": root_motion,
            "force_root_lock": force_lock,
            "name_contains_hard": "Hard" in asset_name,
        }
        clip_rows.append(row)
        checks.extend(
            [
                {"name": f"{asset_name}.exists", "passed": exists},
                {"name": f"{asset_name}.frames", "passed": frames == expected_frames},
                {"name": f"{asset_name}.in_place", "passed": exists and not root_motion and force_lock},
                {"name": f"{asset_name}.hard_excluded", "passed": "Hard" not in asset_name},
            ]
        )

    profile = unreal.load_asset(PROFILE_PATH)
    checks.append({"name": "profile.exists", "passed": profile is not None})
    profile_refs = {}
    if profile is not None:
        for property_name in PROFILE_PROPERTIES:
            value = profile.get_editor_property(property_name)
            path = value.get_path_name() if value is not None else None
            profile_refs[property_name] = path
            checks.append(
                {
                    "name": f"profile.{property_name}",
                    "passed": path is not None and path.startswith(RUNTIME_ROOT) and "Hard" not in path,
                }
            )

    bp = unreal.load_asset(ABP_PATH)
    checks.append({"name": "abp.exists", "passed": bp is not None})
    graph_report = {}
    if bp is not None:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        roots = bp.get_nodes_of_class(unreal.AnimGraphNode_Root)
        slots = bp.get_nodes_of_class(unreal.AnimGraphNode_Slot)
        machines = bp.get_nodes_of_class(unreal.AnimGraphNode_StateMachine)
        sequence_players = bp.get_nodes_of_class(unreal.AnimGraphNode_SequencePlayer)

        root_links = _connected_node_names(roots[0].find_input_pin("Result")) if len(roots) == 1 else []
        slot_input_links = _connected_node_names(slots[0].find_input_pin("Source")) if len(slots) == 1 else []
        slot_output_links = _connected_node_names(slots[0].find_output_pin("Pose")) if len(slots) == 1 else []
        fallback_looping = False
        fallback_sequence = None
        if len(sequence_players) == 1:
            node_data = sequence_players[0].get_editor_property("node")
            fallback_looping = bool(node_data.get_editor_property("loop_animation"))
            sequence = node_data.get_editor_property("sequence")
            fallback_sequence = sequence.get_path_name() if sequence is not None else None

        cdo = unreal.get_default_object(bp.generated_class())
        cdo_profile = cdo.get_editor_property("locomotion_profile")
        cdo_profile_path = cdo_profile.get_path_name() if cdo_profile is not None else None
        graph_report = {
            "compile_status": str(bp.get_editor_property("status")),
            "parent_class": bp.get_blueprint_parent_class().get_path_name(),
            "root_count": len(roots),
            "slot_count": len(slots),
            "state_machine_count": len(machines),
            "root_links": root_links,
            "slot_input_links": slot_input_links,
            "slot_output_links": slot_output_links,
            "fallback_sequence": fallback_sequence,
            "fallback_looping": fallback_looping,
            "cdo_profile": cdo_profile_path,
        }
        checks.extend(
            [
                {"name": "abp.compile", "passed": "UP_TO_DATE" in graph_report["compile_status"]},
                {"name": "abp.parent", "passed": graph_report["parent_class"] == "/Script/Khazan.KhazanAnimInstance"},
                {"name": "abp.slot_count", "passed": len(slots) == 1},
                {"name": "abp.root_from_slot", "passed": len(slots) == 1 and slots[0].get_name() in root_links},
                {"name": "abp.slot_from_state_machine", "passed": len(machines) == 1 and machines[0].get_name() in slot_input_links},
                {"name": "abp.fallback_idle", "passed": fallback_looping and fallback_sequence == f"{RUNTIME_ROOT}/RT_DAS_Idle.RT_DAS_Idle"},
                {"name": "abp.profile", "passed": cdo_profile_path == f"{PROFILE_PATH}.DA_Locomotion_DualAxeSword"},
            ]
        )

    failed = [check["name"] for check in checks if not check["passed"]]
    report = {
        "schema": 1,
        "clips": clip_rows,
        "profile": {"path": PROFILE_PATH, "references": profile_refs},
        "animation_blueprint": graph_report,
        "checks": checks,
        "failed_checks": failed,
        "all_checks_passed": not failed,
    }

    report_dir = os.path.join(unreal.Paths.project_saved_dir(), "ImportReports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "Khazan_Locomotion_Audit.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False))
    if failed:
        raise RuntimeError(f"Locomotion audit failed: {failed}")


if __name__ == "__main__":
    main()
