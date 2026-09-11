"""Validate the saved catalogue after real editor frames have warmed resources."""
import pathlib
import sys
import time
import traceback
import unreal

PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(PROJECT / "Scripts/Enemies"))
import verify_yetuga_render as verifier

LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
LEVELS.load_level(verifier.MAP_PATH)
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        component.set_update_animation_in_editor(True)

# Resource warmup is a tool timing condition, not an animation/gameplay setting.
START = time.monotonic()
HANDLE = None

def on_tick(delta_seconds):
    if time.monotonic() - START < 5.0:
        return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    try:
        verifier.main()
    except Exception:
        (PROJECT / "Saved/ImportReports/Yetuga_EditorPreviewFailure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        unreal.log_error(traceback.format_exc())
    finally:
        unreal.SystemLibrary.quit_editor()

HANDLE = unreal.register_slate_post_tick_callback(on_tick)
