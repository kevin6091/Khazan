"""Inject a deterministic PIE movement pattern and save AnimInstance state transitions.

Run only while a one-player PIE session is active.  The trace is diagnostic and
does not modify the level or gameplay assets.
"""

from __future__ import annotations

import builtins
import json
import os

import unreal


TRACE_KEY = "_khazan_locomotion_pie_trace"
REPORT_NAME = "Khazan_Locomotion_PIE_Trace.json"


def _enum_name(value) -> str:
    text = str(value)
    if "." in text:
        return text.split(".")[-1].split(":")[0].replace(">", "")
    return text


def _stop_previous_trace() -> None:
    previous = getattr(builtins, TRACE_KEY, None)
    if previous and previous.get("handle") is not None:
        try:
            unreal.unregister_slate_post_tick_callback(previous["handle"])
        except Exception:
            pass
    setattr(builtins, TRACE_KEY, None)


def start_trace() -> None:
    _stop_previous_trace()
    # Unreal executes Slate callbacks after the one-shot Python command has
    # released its module globals.  Keep every callback dependency in this
    # closure (or import it locally) so the trace survives that boundary.
    report_name = REPORT_NAME

    def enum_name(value) -> str:
        text = str(value)
        if "." in text:
            return text.split(".")[-1].split(":")[0].replace(">", "")
        return text

    state = {
        "elapsed": 0.0,
        "sample_accumulator": 0.0,
        "handle": None,
        "initial_forward": None,
        "initial_right": None,
        "reverse_right_xyz": None,
        "samples": [],
        "last_signature": None,
        "finished": False,
    }

    def finish(error: str | None = None) -> None:
        import json as callback_json
        import os as callback_os
        import unreal as callback_unreal

        if state["finished"]:
            return
        state["finished"] = True
        if state["handle"] is not None:
            callback_unreal.unregister_slate_post_tick_callback(state["handle"])

        observed_states = sorted({sample["state"] for sample in state["samples"]})
        observed_sequences = sorted(
            {sample["sequence"] for sample in state["samples"] if sample["sequence"]}
        )
        observed_foot_leads = sorted({sample["foot_lead"] for sample in state["samples"]})
        required = {"IDLE", "START", "WALK", "RUN", "MOVING_TURN", "STOP"}
        required_sequences = {
            "RT_DAS_MovingTurn_R_90",
            "RT_DAS_MovingTurn_R_180",
        }
        required_foot_leads = {"LEFT", "RIGHT"}
        report = {
            "schema": 1,
            "duration_seconds": round(state["elapsed"], 4),
            "input_schedule": [
                {"start": 0.0, "end": 1.0, "input": "idle"},
                {"start": 1.0, "end": 2.8, "input": "forward_analog_0.25"},
                {"start": 2.8, "end": 4.5, "input": "forward_analog_1.0"},
                {"start": 4.5, "end": 5.5, "input": "right_90"},
                {"start": 5.5, "end": 6.4, "input": "reverse_180"},
                {"start": 6.4, "end": 8.8, "input": "released"},
            ],
            "samples": state["samples"],
            "observed_states": observed_states,
            "observed_sequences": observed_sequences,
            "observed_foot_leads": observed_foot_leads,
            "required_states": sorted(required),
            "required_sequences": sorted(required_sequences),
            "required_foot_leads": sorted(required_foot_leads),
            "error": error,
            "all_checks_passed": (
                error is None
                and required.issubset(observed_states)
                and required_sequences.issubset(observed_sequences)
                and required_foot_leads.issubset(observed_foot_leads)
            ),
        }

        report_dir = callback_os.path.join(
            callback_unreal.Paths.project_saved_dir(), "ImportReports"
        )
        callback_os.makedirs(report_dir, exist_ok=True)
        report_path = callback_os.path.join(report_dir, report_name)
        with open(report_path, "w", encoding="utf-8") as handle:
            callback_json.dump(report, handle, ensure_ascii=False, indent=2)
        callback_unreal.log(f"Locomotion PIE trace finished: {report_path}")
        print(callback_json.dumps(report, ensure_ascii=False))

    def tick(delta_seconds: float) -> None:
        import unreal as callback_unreal

        try:
            state["elapsed"] += float(delta_seconds)
            state["sample_accumulator"] += float(delta_seconds)
            worlds = callback_unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                if state["elapsed"] > 2.0:
                    finish("PIE world was not available")
                return

            world = worlds[0]
            controller = callback_unreal.GameplayStatics.get_player_controller(world, 0)
            pawn = controller.get_controlled_pawn() if controller is not None else None
            if pawn is None:
                if state["elapsed"] > 2.0:
                    finish("Player pawn was not available")
                return

            if state["initial_forward"] is None:
                state["initial_forward"] = pawn.get_actor_forward_vector()
                state["initial_right"] = pawn.get_actor_right_vector()
                state["reverse_right_xyz"] = (
                    -float(state["initial_right"].x),
                    -float(state["initial_right"].y),
                    -float(state["initial_right"].z),
                )

            elapsed = state["elapsed"]
            segment = "idle"
            if 1.0 <= elapsed < 2.8:
                pawn.add_movement_input(state["initial_forward"], 0.25, True)
                segment = "walk"
            elif 2.8 <= elapsed < 4.5:
                pawn.add_movement_input(state["initial_forward"], 1.0, True)
                segment = "run"
            elif 4.5 <= elapsed < 5.5:
                pawn.add_movement_input(state["initial_right"], 1.0, True)
                segment = "turn_90"
            elif 5.5 <= elapsed < 6.4:
                reverse_x, reverse_y, reverse_z = state["reverse_right_xyz"]
                pawn.add_movement_input(
                    callback_unreal.Vector(reverse_x, reverse_y, reverse_z), 1.0, True
                )
                segment = "turn_180"
            elif elapsed >= 6.4:
                segment = "released"

            mesh = pawn.mesh
            anim_instance = mesh.get_anim_instance() if mesh is not None else None
            if anim_instance is None:
                finish("ABP_Player AnimInstance was not available")
                return

            sequence = anim_instance.get_editor_property("active_locomotion_sequence")
            sequence_name = sequence.get_name() if sequence is not None else None
            anim_velocity = anim_instance.get_editor_property("velocity")
            anim_acceleration = anim_instance.get_editor_property("acceleration")
            sample = {
                "time": round(elapsed, 3),
                "segment": segment,
                "state": enum_name(anim_instance.get_editor_property("locomotion_state")),
                "gait": enum_name(anim_instance.get_editor_property("gait")),
                "foot_lead": enum_name(anim_instance.get_editor_property("foot_lead")),
                "turn_direction": enum_name(anim_instance.get_editor_property("turn_direction")),
                "speed": round(float(anim_instance.get_editor_property("ground_speed")), 2),
                "velocity_xy": [round(float(anim_velocity.x), 2), round(float(anim_velocity.y), 2)],
                "acceleration_xy": [
                    round(float(anim_acceleration.x), 2),
                    round(float(anim_acceleration.y), 2),
                ],
                "actor_yaw": round(float(pawn.get_actor_rotation().yaw), 2),
                "turn_angle": round(float(anim_instance.get_editor_property("requested_turn_angle")), 2),
                "cycle_phase": round(float(anim_instance.get_editor_property("locomotion_cycle_phase")), 4),
                "play_rate": round(float(anim_instance.get_editor_property("active_play_rate")), 3),
                "sequence": sequence_name,
            }
            signature = (
                sample["segment"],
                sample["state"],
                sample["gait"],
                sample["foot_lead"],
                sample["turn_direction"],
                sample["sequence"],
            )
            if signature != state["last_signature"] or state["sample_accumulator"] >= 0.25:
                state["samples"].append(sample)
                state["last_signature"] = signature
                state["sample_accumulator"] = 0.0

            if elapsed >= 8.8:
                finish()
        except Exception as exc:
            finish(str(exc))

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    setattr(builtins, TRACE_KEY, state)
    unreal.log("Khazan locomotion PIE trace started")


start_trace()
