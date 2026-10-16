"""Verify paused Sequencer scrubbing and an unsaved Transform edit render Niagara."""
from pathlib import Path
import json
import os
import time
import traceback
import unreal as u
import kz_combat_vfx_sequencer as tool

OUT = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
report = {'status': 'running', 'temporary_position_edit_cm': 50, 'saved': False}
phase = 'open'
started = time.monotonic()
busy = False


def save_report():
    (OUT / 'ScrubVisualReport.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def effect_actor(sequence):
    manifest = tool._metadata(sequence)
    binding = next(b for b in sequence.get_bindings() if tool._guid(b) in manifest['bindings'])
    actors = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(binding))
    assert len(actors) == 1
    return binding, actors[0]


def finish():
    global phase
    phase = 'done'
    save_report()
    u.unregister_slate_post_tick_callback(handle)
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    u.SystemLibrary.quit_editor()


def tick(delta):
    global phase, started, busy
    if busy:
        return
    try:
        elapsed = time.monotonic() - started
        if phase == 'open' and elapsed >= 8:
            busy = True
            sequence = tool.open_weak02()
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(18)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            manifest = tool._metadata(sequence)
            body = next(b for b in sequence.get_bindings() if tool._guid(b) == manifest['body_binding'])
            actor = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(body))[0]
            base = actor.get_actor_location()
            camera = base + u.Vector(80, -480, 320)
            u.EditorLevelLibrary.set_level_viewport_camera_info(camera, u.MathLibrary.find_look_at_rotation(camera, base))
            phase = 'compile'
            started = time.monotonic()
            busy = False
        elif phase == 'compile' and elapsed >= 5:
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(20)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            phase = 'before'
            started = time.monotonic()
        elif phase == 'before' and elapsed >= 1:
            sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
            binding, actor = effect_actor(sequence)
            report['before_x'] = actor.get_actor_location().x
            u.AutomationLibrary.take_high_res_screenshot(1600, 900, str(OUT / 'Before.png'))
            phase = 'edit'
            started = time.monotonic()
        elif phase == 'edit' and elapsed >= 2:
            sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
            binding, actor = effect_actor(sequence)
            track = next(t for t in binding.get_tracks() if isinstance(t, u.MovieScene3DTransformTrack))
            section = next(s for s in track.get_sections() if s.get_row_index() == 1)
            channel = section.get_all_channels()[0]
            for key in list(channel.get_keys()):
                channel.remove_key(key)
            channel.set_default(50.0)
            channel.add_key(u.FrameNumber(0), 50.0, interpolation=u.MovieSceneKeyInterpolation.LINEAR)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            phase = 'after'
            started = time.monotonic()
        elif phase == 'after' and elapsed >= 1:
            sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
            binding, actor = effect_actor(sequence)
            report['after_x'] = actor.get_actor_location().x
            report['movement_cm'] = report['after_x'] - report['before_x']
            assert abs(report['movement_cm'] - 50.0) < .01
            u.AutomationLibrary.take_high_res_screenshot(1600, 900, str(OUT / 'After.png'))
            report['status'] = 'passed'
            save_report()
            phase = 'finish'
            started = time.monotonic()
        elif phase == 'finish' and elapsed >= 8:
            finish()
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        u.log_error(report['error'])
        finish()


handle = u.register_slate_post_tick_callback(tick)
