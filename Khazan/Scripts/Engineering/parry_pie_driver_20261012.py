"""New hidden process only. Tests own PIE gameplay; no package saves."""
from pathlib import Path
import ctypes, hashlib, json, os, time, traceback, unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT']);MAIN=Path(os.environ['KZ_PARRY_MAIN'])
assert ROOT in [MAIN,MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan']
TEST=os.environ.get('KZ_PARRY_TEST','Khazan.Parry.PIE');START=time.monotonic();started=requested=finished=busy=False
report={'status':'running','test':TEST,'project':str(ROOT),'asset_saves':0}
manifest=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
module=ROOT/'Binaries/Win64'/manifest['Modules']['Khazan']
kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768);handle=kernel.GetModuleHandleW(module.name)
assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer));assert Path(buffer.value).resolve()==module.resolve()
report['actual_module']={'path':buffer.value,'sha256':hashlib.sha256(module.read_bytes()).hexdigest()}
unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).set_editor_property('bThrottleCPUWhenNotForeground',False)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')
def finish(error=None):
    global finished
    if finished:return
    finished=True;unreal.unregister_slate_post_tick_callback(tick_handle)
    report['status']='failed' if error else 'passed';report['seconds']=time.monotonic()-START
    if error:report['error']=error;unreal.log_error(error)
    (OUT/'Driver.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play();unreal.SystemLibrary.quit_editor()
def tick(delta):
    global started,requested,busy
    if busy or finished:return
    busy=True
    try:
        elapsed=time.monotonic()-START
        if elapsed>900:finish('Owned parry test watchdog');return
        if elapsed<8:return
        log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        done=[s for s in log.splitlines() if 'Test Completed' in s and TEST in s]
        if done:
            report['completion']=done[-1]
            report['shader_failures']=[s for s in log.splitlines() if 'Failed to compile Material' in s or 'Default Material will be used' in s]
            finish(report['shader_failures'][0] if report['shader_failures'] else None if 'Success' in done[-1] else done[-1]);return
        if not started:
            started=True;unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60');unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+TEST)
        elif not requested and 'Test Started' in log and TEST in log and TEST in ['Khazan.Guard.PIE','Khazan.Combat.PlayerAttackCollision.PIE','Khazan.Heal.PIE']:
            requested=True;unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
tick_handle=unreal.register_slate_post_tick_callback(tick)
