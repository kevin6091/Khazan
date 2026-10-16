"""Observe real GAS patterns through the actual AnimBP/CMC without asset saves."""
from pathlib import Path
import json
import os
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
DRIVER = ROOT / 'Scripts/Engineering/monster_physics_validation_driver_20261013.py'
started, last_flush = time.monotonic(), 0.
observed, errors, captures = {}, [], {}

def vector(v):
    return [float(v.x), float(v.y), float(v.z)]

def probe(delta):
    global last_flush
    try:
        for world in unreal.EditorLevelLibrary.get_pie_worlds(False):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KZMonster):
                if not any(name in actor.get_name() for name in ('Yetuga', 'ApesStoneHandElite')):
                    continue
                mesh = actor.mesh
                # Only this owned disposable process; no CDO or package mutation.
                mesh.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
                anim = mesh.get_anim_instance()
                if not anim:
                    continue
                montage = anim.get_current_active_montage()
                section = str(anim.montage_get_current_section(montage)) if montage else 'None'
                key = actor.get_name() + '|' + (montage.get_path_name() if montage else 'None') + '|' + section
                root = mesh.get_socket_transform('Root', unreal.RelativeTransformSpace.RTS_COMPONENT)
                pelvis = mesh.get_socket_transform('Bip001', unreal.RelativeTransformSpace.RTS_COMPONENT)
                row = observed.setdefault(key, {'actor': actor.get_name(), 'montage': montage.get_path_name() if montage else None,
                    'section': section, 'samples': 0, 'maximum_root_offset_cm': 0., 'maximum_pelvis_planar_cm': 0.,
                    'first_actor': vector(actor.get_actor_location()), 'root_modes': [], 'maximum_sample': None})
                row['samples'] += 1
                distance = root.translation.length()
                row['maximum_pelvis_planar_cm'] = max(row['maximum_pelvis_planar_cm'], (pelvis.translation.x**2 + pelvis.translation.y**2)**.5)
                mode = str(anim.get_editor_property('root_motion_mode'))
                if mode not in row['root_modes']:
                    row['root_modes'].append(mode)
                if row['maximum_sample'] is None or distance > row['maximum_root_offset_cm']:
                    row['maximum_root_offset_cm'] = distance
                    cmc = actor.get_component_by_class(unreal.CharacterMovementComponent)
                    row['maximum_sample'] = {'time': unreal.GameplayStatics.get_time_seconds(world),
                        'root_component': root.export_text(), 'pelvis_component': pelvis.export_text(),
                        'actor': actor.get_actor_transform().export_text(), 'mesh_relative': mesh.get_relative_transform().export_text(),
                        'movement_mode': str(cmc.get_editor_property('movement_mode')), 'root_mode': mode}
                if os.environ.get('KZ_GIANT_ROOT_CAPTURE_PART') == '1' and montage and 'PartGroggy' in montage.get_name():
                    position = anim.montage_get_position(montage)
                    segments = montage.get_editor_property('slot_anim_tracks')[0].get_editor_property('anim_track').get_editor_property('anim_segments')
                    for index, segment in enumerate(segments):
                        start = segment.get_editor_property('start_pos')
                        next_start = segments[index+1].get_editor_property('start_pos') if index+1 < len(segments) else montage.get_play_length()
                        if not start <= position < next_start:
                            continue
                        clip = segment.get_editor_property('anim_reference')
                        capture_key = actor.get_name() + '_' + clip.get_name()
                        if capture_key in captures:
                            break
                        file = OUT / (capture_key + '.png')
                        capsule = actor.capsule_component
                        unreal.SystemLibrary.draw_debug_capsule(world, actor.get_actor_location(),
                            capsule.get_scaled_capsule_half_height(), capsule.get_scaled_capsule_radius(),
                            actor.get_actor_rotation(), unreal.LinearColor(0, 1, 0, 1), 0., 1.)
                        unreal.SystemLibrary.execute_console_command(world, 'Shot filename="' + str(file) + '" -nosuffix')
                        captures[capture_key] = {'file': str(file), 'actor': actor.get_name(), 'clip': clip.get_path_name(),
                            'montage_position': position, 'segment_start': start, 'root_offset_cm': distance}
                        (OUT / 'PartCaptures.json').write_text(json.dumps(captures, indent=2), encoding='utf-8')
                        break
        if time.monotonic() - last_flush > 1.:
            last_flush = time.monotonic()
            (OUT / 'RuntimeRoots.json').write_text(json.dumps({'elapsed': time.monotonic()-started,
                'rows': list(observed.values()), 'errors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        error = traceback.format_exc()
        if error not in errors:
            errors.append(error)
            (OUT / 'ObserverErrors.json').write_text(json.dumps(errors), encoding='utf-8')

CALLBACK = unreal.register_slate_post_tick_callback(probe)
source = DRIVER.read_text(encoding='utf-8')
old = "if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
new = "if test != 'Khazan.Parry.PIE' and (test.endswith('PIE') or test.endswith('.PIE')):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()"
assert source.count(old) == 1
exec(compile(source.replace(old, new), str(DRIVER), 'exec'), {'__file__': str(DRIVER), '__name__': '__main__'})
