"""Owned PIE visual alignment trials; never save the level or shared Niagara assets."""
from pathlib import Path
import json, os, time, traceback, unreal as u

out = Path(os.environ['KZ_PORTAL_OUT'])
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/Maps/L_HeinMach_Environment')
for command in ['sg.TextureQuality 2', 'sg.EffectsQuality 2', 'r.Streaming.PoolSize 800', 't.MaxFPS 30']:
    u.SystemLibrary.execute_console_command(None, command)
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
report = dict(status='running', asset_saves=0, views=[], qa_only_texture_quality=2, qa_only_streaming_pool_mb=800)
start = time.monotonic()
world = pc = pawn = camera = portal = effect = None
index = -1
settled = 0
done = False
trials = [('Saved', 0, 1), ('Rotate90', 90, 1), ('Rotate90Outside', 90, -1)]

def finish(error=None):
    global done
    if done:
        return
    done = True
    report['status'] = 'failed' if error else 'passed'
    if error:
        report['error'] = error
    (out / 'Review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle)
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.SystemLibrary.quit_editor()

def tick(delta):
    global world, pc, pawn, camera, portal, effect, index, settled
    try:
        if time.monotonic() - start > 300:
            finish('Preview watchdog')
            return
        if world is None:
            worlds = u.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                return
            world = worlds[0]
            pc = u.GameplayStatics.get_player_controller(world, 0)
            pawn = u.GameplayStatics.get_player_pawn(world, 0)
            if not pc or not pawn:
                world = None
                return
            portal = u.GameplayStatics.get_all_actors_of_class(world, u.KZBossPortal)[0]
            portal.get_editor_property('entry_volume').set_editor_property('generate_overlap_events', False)
            pc.set_ignore_move_input(True)
            pc.set_ignore_look_input(True)
            pawn.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_NONE)
            pawn.set_actor_hidden_in_game(True)
            camera = next(c for c in pawn.get_components_by_class(u.CameraComponent) if c.is_active())
            camera.detach_from_component(u.DetachmentRule.KEEP_WORLD, u.DetachmentRule.KEEP_WORLD, u.DetachmentRule.KEEP_WORLD)
            camera.set_editor_property('use_pawn_control_rotation', False)
            effect = portal.get_editor_property('portal_effect')
            report['initial'] = dict(controller_class=pc.get_class().get_path_name(), pawn_class=pawn.get_class().get_path_name(),
                active=effect.is_active(), auto_activate=effect.get_editor_property('auto_activate'),
                visible=effect.get_editor_property('visible'), hidden_in_game=effect.get_editor_property('hidden_in_game'),
                transform=effect.get_world_transform().export_text(), system=effect.get_asset().get_path_name())
        if index >= 0 and time.monotonic() - settled < 3:
            return
        if index >= 0:
            name, yaw, side = trials[index]
            u.SystemLibrary.execute_console_command(world, 'KZ.QA.ColourShot ' + str(out / (name + '.png')))
            report['views'].append(dict(name=name, relative_yaw=yaw, side=side, active=effect.is_active(),
                effect_transform=effect.get_world_transform().export_text(), camera=camera.get_world_transform().export_text()))
        index += 1
        if index == len(trials):
            finish()
            return
        name, yaw, side = trials[index]
        effect.set_relative_rotation(u.Rotator(pitch=0, yaw=yaw, roll=0), False, False)
        effect.reinitialize_system()
        center = portal.get_actor_location()
        position = center + portal.get_actor_forward_vector() * (600 * side) + u.Vector(0, 0, 40)
        camera.set_world_location(position, False, False)
        camera.set_world_rotation(u.MathLibrary.find_look_at_rotation(position, center), False, False)
        settled = time.monotonic()
    except Exception:
        finish(traceback.format_exc())

handle = u.register_slate_post_tick_callback(tick)
