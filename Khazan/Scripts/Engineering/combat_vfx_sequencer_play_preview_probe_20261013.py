"""Observe visible Niagara during actual Sequencer playback, not a paused seek."""
from pathlib import Path
import json
import os
import time
import traceback
import unreal as u
import kz_combat_vfx_sequencer as tool

OUT = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
report = {'status': 'running'}
phase = 'open'
started = time.monotonic()
busy = False


def write():
    (OUT / 'PlayingPreviewReport.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def finish():
    global phase
    phase = 'done'
    write()
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
            manifest = tool._metadata(sequence)
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(18)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            body = next(b for b in sequence.get_bindings() if tool._guid(b) == manifest['body_binding'])
            actor = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(body))[0]
            base = actor.get_actor_location()
            camera = base + u.Vector(80, -480, 320)
            u.EditorLevelLibrary.set_level_viewport_camera_info(camera, u.MathLibrary.find_look_at_rotation(camera, base))
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            phase = 'compile'
            started = time.monotonic()
            busy = False
        elif phase == 'compile' and elapsed >= 5:
            sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            u.LevelSequenceEditorBlueprintLibrary.play()
            phase = 'play'
            started = time.monotonic()
        elif phase == 'play':
            current = u.LevelSequenceEditorBlueprintLibrary.get_current_time()
            frame = int(current)
            if frame >= 20:
                sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
                manifest = tool._metadata(sequence)
                binding = next(b for b in sequence.get_bindings() if tool._guid(b.get_parent()) in manifest['bindings'])
                objects = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(binding))
                component = objects[0]
                report.update({'status': 'passed', 'frame': frame, 'active': component.is_active(),
                               'desired_age': component.get_desired_age(), 'age_mode': str(component.get_age_update_mode())})
                u.LevelSequenceEditorBlueprintLibrary.pause()
                u.AutomationLibrary.take_high_res_screenshot(1600, 900, str(OUT / 'PlayingPreview.png'))
                phase = 'screenshot'
                started = time.monotonic()
                write()
            elif elapsed > 15:
                raise RuntimeError('Sequencer playback did not reach the effect frame.')
        elif phase == 'screenshot' and elapsed >= 8:
            finish()
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        u.log_error(report['error'])
        finish()


handle = u.register_slate_post_tick_callback(tick)
