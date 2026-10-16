"""Commandlet asset automation with output archived outside the work project."""
from pathlib import Path
import json,os,shutil,time,traceback,unreal
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
test=os.environ.get('KZ_MONSTER_PHYSICS_TEST','Khazan.MonsterSecondaryPhysics.Audit')
start=time.monotonic()
started=finished=busy=requested=False
root=Path(unreal.Paths.project_dir()).resolve()
unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).set_editor_property('bThrottleCPUWhenNotForeground',False)
if test.endswith('.PIE'):
    unreal.SystemLibrary.execute_console_command(None,'p.RigidBodyNode.DeferredSimulationForceDefault 1')
    unreal.SystemLibrary.execute_console_command(None,'p.RigidBodyNode.DeferredSimulationDefault 0')
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')

def finish(error=None):
    global finished
    if finished:return
    finished=True
    unreal.unregister_slate_post_tick_callback(handle)
    for file in (root/'Saved').glob('MonsterSecondaryPhysics*.json'):
        shutil.copy2(file,out/file.name)
    (out/'Driver.json').write_text(json.dumps(dict(test=test,project=str(root),success=not error,error=error,seconds=time.monotonic()-start),indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global started,busy,requested
    if finished or busy:return
    busy=True
    try:
        if time.monotonic()-start>600:finish('Native test watchdog');return
        if time.monotonic()-start<3:return
        log=(out/'Editor.log').read_text(encoding='utf-8',errors='replace')
        if 'No automation tests matched' in log:finish('Owned build did not register requested test; no author/PIE executed');return
        done=[line for line in log.splitlines() if 'Test Completed' in line and test in line]
        if done:finish(None if 'Success' in done[-1] else done[-1]);return
        if not started:
            started=True
            unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+test)
        elif test=='Khazan.MonsterSecondaryPhysics.PIE' and not requested and 'Test Started' in log:
            requested=True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=unreal.register_slate_post_tick_callback(tick)
