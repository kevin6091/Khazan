"""Replay current saved snow systems and movement/action clips with the existing native fixture."""
import ctypes
import hashlib
import json
import os
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = Path(os.environ['KZ_SNOW_LAYOUT_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'Metadata/YetugaSnowLayout_20261015'
audit = json.loads((BASE / 'SavedAudit.json').read_text())
assert audit['status'] == 'passed'
AFTER = os.environ.get('KZ_SNOW_LAYOUT_AFTER', '0') == '1'
selected = ('Footstep_Normal_01', 'Footstep_Strong_01', 'Footstep_dash_normal_01',
            'Slashdust_HalfCircle_Left_01', 'Slashdust_HalfCircle_Right_01', 'HandDust_01', 'BodyDust_01')
particles = [next(item['current'] for item in audit['particles'] if item['original'].endswith('.FP_Boss_Yetuga_' + term)) for term in selected]
probe = json.loads((ROOT / 'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text())
names = ('Locomotion_FastMove', 'Locomotion_SideMove_L_Long', 'Locomotion_TurnBackRun',
         'Idle_Social', 'Attack_NormalAtk01_01', 'Attack_DashAtk_Fast')
animations = [next(path for path in probe['sequences'] if '/Yetuga/' in path and path.endswith('.' + name)) for name in names]
cases = [(str(index) + '_' + name, 'Yetuga', 'particle', asset) for index, (name, asset) in enumerate(zip(selected, particles))]
cases += [(name, 'Yetuga', 'animation', asset) for name, asset in zip(names, animations)]
cases += [(name, 'Yetuga', 'pattern', name) for name in ('NormalAtk01_Step1', 'DempseyRoll_Step1')]
(OUT / 'GiantReviewCases.tsv').write_text('\n'.join('\t'.join(case) for case in cases) + '\n', encoding='utf-8')
os.environ['KZ_MONSTER_REPAIR_OUT'] = str(OUT)
TEST = 'Khazan.GiantVFX.ReviewPIE'
LOG = OUT / 'Editor.log'
u.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground', False)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')
# Only this task-owned unsaved world is changed; unrelated placed NPCs do not contribute review particles.
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
for actor in actors.get_all_level_actors():
    if isinstance(actor, u.KZMonster):
        actors.destroy_actor(actor)

manifest = json.loads((ROOT / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
buffer = ctypes.create_unicode_buffer(32768)
assert kernel.GetModuleFileNameW(kernel.GetModuleHandleW(manifest['Modules']['Khazan']), buffer, len(buffer))
module = Path(buffer.value).resolve()
report = {'status': 'running', 'project': str(ROOT), 'after': AFTER, 'saved_packages': 0,
          'actual_loaded_module': str(module), 'module_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
          'particle_systems': len(particles), 'source_animation_cases': len(animations), 'gas_patterns': 2,
          'fixture': 'Unsaved isolated DevMap; identical closer particle review camera before and after'}
if AFTER:
    authoring = json.loads((BASE / 'Authoring.json').read_text())
    assert authoring['status'] == 'passed' and len(authoring['saved']) == 3
    allowed = {'Content/' + item['instance'].split('.')[0].removeprefix('/Game/') + '.uasset' for item in authoring['reparented']}
    for relative, expected in audit['guard_files'].items():
        if relative not in allowed:
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    for item in authoring['reparented']:
        material = u.load_asset(item['instance'])
        assert material.get_editor_property('parent').get_path_name() == item['after']
        assert u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(material, 'Tex_Opa').get_name() == 'T_Smoke03_SubUV_9x9'
        assert u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, 'SnowTextureColumns') == 9
        assert u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, 'SnowTextureRows') == 9
    report['saved_readback'] = {'parent_bindings': 2, 'single_cloud_texture_grid': [9, 9],
                               'protected_files_unchanged': authoring['protected_files_unchanged'],
                               'particle_systems_unchanged': len(audit['particles'])}
START = time.monotonic()
started = requested = done = busy = False


def finish(error=None):
    global done
    if done:
        return
    done = True
    u.unregister_slate_post_tick_callback(CALLBACK)
    report['status'] = 'failed' if error else 'passed'
    report['seconds'] = time.monotonic() - START
    if error:
        report['error'] = error
        u.log_error(error)
    (OUT / 'Driver.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.SystemLibrary.quit_editor()


def tick(delta):
    global started, requested, busy
    if done or busy:
        return
    busy = True
    try:
        if time.monotonic() - START > 400:
            finish('Scoped snow review watchdog')
            return
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if world:
            controller = u.GameplayStatics.get_player_controller(world, 0)
            camera = controller.get_view_target() if controller else None
            if isinstance(camera, u.CameraActor):
                for actor in u.GameplayStatics.get_all_actors_of_class(world, u.WorldSettings):
                    for component in actor.get_components_by_class(u.ParticleSystemComponent):
                        template = component.get_editor_property('template')
                        if template and template.get_path_name() in particles and component.is_active():
                            focus = component.get_world_location() + u.Vector(0, 0, 70)
                            eye = focus + u.Vector(350, -550, 180)
                            camera.set_actor_location(eye, False, False)
                            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye, focus), False)
        data = LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else ''
        completed = [line for line in data.splitlines() if 'Test Completed' in line and ('Path={' + TEST + '}') in line]
        if completed:
            report['completion'] = completed[-1]
            report['material_compile_failures'] = [line for line in data.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
            review = json.loads((OUT / 'GiantReview.json').read_text())
            assert review['passed'] and 'Result={Success}' in completed[-1] and not report['material_compile_failures']
            summary = [case for case in review['cases'] if 'peak_components' in case]
            assert len(summary) == len(cases)
            assert all(case['peak_components'] > 0 and case['peak_cpu_particles'] > 0 for case in summary if case['kind'] != 'animation')
            report['completed_cases'] = len(summary)
            finish()
            return
        if time.monotonic() - START < 8:
            return
        if not started:
            started = True
            u.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            u.SystemLibrary.execute_console_command(None, 'Automation RunTests ' + TEST)
        elif not requested and 'Test Started' in data and ('Path={' + TEST + '}') in data:
            requested = True
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:
        finish(traceback.format_exc())
    finally:
        busy = False


CALLBACK = u.register_slate_post_tick_callback(tick)
