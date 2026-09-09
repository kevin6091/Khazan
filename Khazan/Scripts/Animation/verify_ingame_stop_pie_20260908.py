"""One-player PIE diagnostic. Injects Enhanced Input, never edits/saves assets.

Run with PIE active and no other input driver. Results remain in builtins as
_khazan_ingame_stop_verification. No guessed animation-node indices are used.
The caller reads results and ends its own PIE session after inspection.
"""


def start_verification():
    import builtins
    import unreal

    previous = getattr(builtins, "_khazan_stop_probe", None)
    if previous and previous.get("handle") and not previous.get("done"):
        unreal.unregister_slate_post_tick_callback(previous["handle"])
        previous["done"] = True
    existing = getattr(builtins, "_khazan_ingame_stop_verification", None)
    if existing and not existing.get("done"):
        raise RuntimeError("A verification is already running")

    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    if len(worlds) != 1:
        raise RuntimeError("Requires exactly one PIE world")
    world = worlds[0]
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = controller.get_controlled_pawn()
    anim = pawn.mesh.get_anim_instance()
    library = unreal.get_default_object(
        unreal.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary")
    )
    subsystem = library.call_method(
        "GetLocalPlayerSubSystemFromPlayerController",
        args=(controller, unreal.EnhancedInputLocalPlayerSubsystem.static_class()),
    )
    move = unreal.load_asset("/Game/Input/Locomotion/IA_Move")
    sprint = unreal.load_asset("/Game/Input/Locomotion/IA_Sprint")
    jump = unreal.load_asset("/Game/Input/Locomotion/IA_Jump")
    # Move X is already the action's forward axis, after IMC swizzling.
    schedule = [
        (1.0, "walk", 0.25),
        (2.0, "walk_stop_early", 0.0),
        (3.3, "reinput_run", 1.0),
        (4.0, "run_stop_early", 0.0),
        (5.4, "reinput_sprint", 1.0),
        (10.5, "sprint_stop_full", 0.0),
        (11.4, "walk_again", 0.25),
        (13.7, "walk_stop_full", 0.0),
        (14.9, "run_again", 1.0),
        (19.1, "run_stop_full", 0.0),
        (19.9, "deadzone", 0.05),
        (20.8, "run_before_jump", 1.0),
        (24.3, "release_airborne", 0.0),
        (25.2, "threshold_060", 0.6),
        (26.1, "threshold_061", 0.61),
        (27.3, "sprint_toggle_on", 1.0),
        (28.4, "sprint_toggle_off", 1.0),
        (29.5, "walk_after_sprint", 0.25),
        (32.0, "final_stop", 0.0),
    ]
    state = {
        "t0": unreal.GameplayStatics.get_time_seconds(world),
        "samples": [], "events": [], "schedule": schedule,
        "done": False, "error": None, "handle": None,
        "sent": set(), "last_signature": None,
        "last_sample_t": -1.0,
        "actor": pawn.get_path_name(), "anim": anim.get_path_name(),
    }

    def enum_name(value):
        return str(value).split(".")[-1].split(":")[0].replace(">", "")

    def stop(error=None):
        if state["done"]:
            return
        state["done"] = True
        state["error"] = error
        unreal.unregister_slate_post_tick_callback(state["handle"])
        subsystem.inject_input_vector_for_action(move, unreal.Vector(), [], [])
        unreal.log("KHAZAN_INGAME_STOP_VERIFY_DONE " + str(error))

    def tick(_delta_seconds):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - state["t0"]
            segment, amount = "final_stop", 0.0
            for end, name, value in schedule:
                if t < end:
                    segment, amount = name, value
                    break
            row = {"t": round(t, 4), "segment": segment}
            for prop in [
                "GroundSpeed", "InputAmount", "bIsGrounded", "bIsFalling",
                "bHasMovementInput", "bShouldEnterStop", "StopEntrySpeed",
                "LocomotionGait", "StopGait", "StopEntryFoot",
                "bShouldWalkRun", "bShouldSprint", "bShouldBeIdle",
            ]:
                value = anim.get_editor_property(prop)
                row[prop] = value if isinstance(value, (float, bool, int)) else enum_name(value)
            row["MaxWalkSpeed"] = pawn.character_movement.max_walk_speed
            position = pawn.get_actor_location()
            row["position"] = [position.x, position.y, position.z]
            for bone in ["C_P_Kazan", "Root"]:
                transform = pawn.mesh.get_socket_transform(
                    bone, unreal.RelativeTransformSpace.RTS_COMPONENT
                )
                p = transform.translation
                row[bone] = [p.x, p.y, p.z]
            signature = tuple(row[p] for p in [
                "segment", "bHasMovementInput", "bIsFalling",
                "bShouldEnterStop", "LocomotionGait", "StopGait",
                "StopEntryFoot", "bShouldWalkRun", "bShouldSprint",
            ])
            if signature != state["last_signature"]:
                state["events"].append(row)
                state["last_signature"] = signature
            if t - state["last_sample_t"] >= 0.05:
                state["samples"].append(row)
                state["last_sample_t"] = t

            subsystem.inject_input_vector_for_action(
                move, unreal.Vector(amount, 0.0, 0.0), [], []
            )
            for trigger_time, key, action in [
                (4.1, "sprint_reinput", sprint),
                (20.65, "jump", jump),
                (26.2, "sprint_on", sprint),
                (27.4, "sprint_off", sprint),
            ]:
                if t >= trigger_time and key not in state["sent"]:
                    subsystem.inject_input_vector_for_action(
                        action, unreal.Vector(1.0, 0.0, 0.0), [], []
                    )
                    state["sent"].add(key)
            if t >= 32.0:
                stop()
        except Exception as exc:
            stop(str(exc))

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    builtins._khazan_ingame_stop_verification = state
    print("KHAZAN_INGAME_STOP_VERIFY_STARTED; duration 32 game seconds")


start_verification()
