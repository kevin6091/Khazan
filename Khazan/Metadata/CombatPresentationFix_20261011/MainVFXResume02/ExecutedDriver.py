"""Task-owned RHI PIE driver and actual-player captures; saves no game package."""
from pathlib import Path
import json
import os
import time
import traceback
import unreal

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
VERIFY_MAIN = True
assert WORK == (ROOT if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan'))
OUT = Path(os.environ['KZ_CLEAN_OUTPUT'])
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / 'Editor.log'
REPORT = {'status': 'running', 'project': str(WORK), 'captures': [], 'package_saves': 0,
          'verification': 'fresh_saved_Main' if VERIFY_MAIN else 'private_candidate',
          'boundary': 'Real RHI and native test; test fixture is not original-game input or pixel parity.'}
START = time.monotonic()
STARTED = REQUESTED = BUSY = False
CAPTURE = TARGET = None
LAST = {}
CAPTURE_COUNTS = {}

def finish(error=None):
    global HANDLE
    REPORT['status'] = 'failed' if error else 'passed'
    if error:
        REPORT['error'] = error
        unreal.log_error(error)
    (OUT / 'Driver.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global STARTED, REQUESTED, BUSY, CAPTURE, TARGET
    if BUSY:
        return
    BUSY = True
    try:
        elapsed = time.monotonic() - START
        if elapsed > 480:
            finish('Native PIE driver timed out'); return
        if elapsed < 8:
            return
        if not STARTED:
            unreal.SystemLibrary.execute_console_command(None, 'Log LogAbility Verbose')
            unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            unreal.SystemLibrary.execute_console_command(None, 'Automation RunTests Khazan.CombatEffect.PIE')
            STARTED = True
            return
        log = LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else ''
        if 'Khazan.CombatEffect.PIE' in log and 'Test Started' in log and not REQUESTED:
            REQUESTED = True
            capture = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
            capture.set_actor_label('AttackVFXActualPlayerCapture')
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        if 'Test Completed' in log and 'Khazan.CombatEffect.PIE' in log:
            lines = [line for line in log.splitlines() if 'Test Completed' in line and 'Khazan.CombatEffect.PIE' in line]
            if lines:
                REPORT['native_completion'] = lines[-1]
                REPORT['material_compile_failures'] = [line for line in log.splitlines()
                    if 'Failed to compile Material' in line or 'Default Material will be used in game' in line]
                error = None if 'Success' in lines[-1] else lines[-1]
                if REPORT['material_compile_failures']:
                    error = 'RHI material compilation fell back to DefaultMaterial: ' + '\n'.join(REPORT['material_compile_failures'])
                finish(error); return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        player = unreal.GameplayStatics.get_player_character(world, 0)
        if not player:
            return
        if CAPTURE is None:
            CAPTURE = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)
                           if a.get_actor_label() == 'AttackVFXActualPlayerCapture')
            TARGET = unreal.RenderingLibrary.create_render_target2d(world, 960, 540, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
            c = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
            c.set_editor_property('texture_target', TARGET)
            c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            c.set_editor_property('capture_every_frame', False)
            c.set_editor_property('always_persist_rendering_state', True)
        if 'runtime_presentation' not in REPORT:
            monsters=[]
            for owner in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.KZMonster):
                components=[{'path':c.get_path_name(),'camera':str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)),'pawn':str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),'visibility':str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))} for c in owner.get_components_by_class(unreal.PrimitiveComponent)]
                assert all('.ECR_IGNORE: 0>' in c['camera'] for c in components),components
                monsters.append({'class':owner.get_class().get_path_name(),'components':components})
            camera=player.get_component_by_class(unreal.CameraComponent)
            post=camera.get_editor_property('post_process_settings')
            overrides=[]
            for name in dir(post):
                if name.startswith('override_'):
                    try:
                        if post.get_editor_property(name):overrides.append(name)
                    except Exception:pass
            controls={name:unreal.SystemLibrary.get_console_variable_float_value(name) for name in ['r.DefaultFeature.AutoExposure','r.DefaultFeature.Bloom','r.DefaultFeature.MotionBlur','r.DefaultFeature.LensFlare','r.DefaultFeature.LocalExposure.HighlightContrastScale','r.DefaultFeature.LocalExposure.ShadowContrastScale']}
            REPORT['runtime_presentation']={'monsters':monsters,'camera_overrides':overrides,'controls':controls}
            assert controls['r.DefaultFeature.AutoExposure']==1 and controls['r.DefaultFeature.Bloom']==0 and controls['r.DefaultFeature.MotionBlur']==0
        mesh = player.get_editor_property('mesh')
        anim = mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        if not montage:
            return
        position = anim.montage_get_position(montage)
        section = str(anim.montage_get_current_section(montage))
        key = montage.get_name() + '_' + section
        if not any(n in montage.get_name() for n in ('WeakAttackCombo','StrongAttackCombo','Player_DodgeAttack','StrongChargeAttack','OverFury','BrutalFront','BrutalBack')):
            return
        # Inspection cadence only. It neither changes nor quantizes gameplay timing.
        slot = int(position * 6)
        if LAST.get(key) == slot or CAPTURE_COUNTS.get(key, 0) >= 80 or len(REPORT['captures']) >= 900:
            return
        LAST[key] = slot
        CAPTURE_COUNTS[key] = CAPTURE_COUNTS.get(key, 0) + 1
        camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        CAPTURE.set_actor_location(camera.get_camera_location(), False, False)
        CAPTURE.set_actor_rotation(camera.get_camera_rotation(), False)
        c = CAPTURE.get_component_by_class(unreal.SceneCaptureComponent2D)
        c.set_editor_property('fov_angle', camera.get_fov_angle())
        c.capture_scene()
        filename = str(len(REPORT['captures'])).zfill(3) + '_' + key + '.png'
        unreal.RenderingLibrary.export_render_target(world, TARGET, str(OUT), filename)
        active=[]
        for owner in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
            for ps in owner.get_components_by_class(unreal.ParticleSystemComponent):
                template=ps.get_editor_property('template')
                if template and ps.is_active():
                    p=ps.get_world_location()
                    active.append({'component':ps.get_path_name(),'template':template.get_path_name(),'location':[p.x,p.y,p.z],'materials':[ps.get_material(i).get_path_name() if ps.get_material(i) else None for i in range(ps.get_num_materials())]})
        if 'Brutal' in montage.get_name() and CAPTURE_COUNTS[key]%6==0:
            feet=player.get_actor_location()-unreal.Vector(0,0,player.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height())
            loc=feet+unreal.Vector(-450,-120,650)
            CAPTURE.set_actor_location(loc,False,False)
            CAPTURE.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(loc,feet+unreal.Vector(120,0,0)),False)
            c.capture_scene()
            ground='Ground_'+filename
            unreal.RenderingLibrary.export_render_target(world,TARGET,str(OUT),ground)
        REPORT['captures'].append({'particles':active,'montage': montage.get_path_name(), 'section': section,
                                   'position_seconds': position, 'image': str(OUT / filename)})
    except Exception:
        finish(traceback.format_exc())
    finally:
        BUSY = False

HANDLE = unreal.register_slate_post_tick_callback(tick)
