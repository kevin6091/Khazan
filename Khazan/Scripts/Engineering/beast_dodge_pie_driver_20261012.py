"""Only owns this editor's PIE lifecycle; actual gameplay stimuli are native QA."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import time
import traceback
import unreal

WORK = Path(unreal.Paths.project_dir()).resolve()
assert 'Khazan_BeastDodgeWork_20261012' in str(WORK)
OUT = Path(os.environ['KZ_BEAST_OUT'])
TEST = os.environ.get('KZ_BEAST_TEST', 'Khazan.BeastDodge.DefensePIE')
manifest = json.loads((WORK / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p]; kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint]; kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768)
handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer))
module=Path(buffer.value).resolve()
assert module.is_relative_to(WORK/'Binaries')
report={'status':'running','test':TEST,'actual_module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'input_driver':'native automation; Python does not inject input or move actors'}
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
START=time.monotonic(); STARTED=REQUESTED=FINISHED=BUSY=False


def finish(error=None):
    global FINISHED
    if FINISHED:return
    FINISHED=True; unreal.unregister_slate_post_tick_callback(HANDLE)
    report['status']='failed' if error else 'passed'
    if error:report['error']=error;unreal.log_error(error)
    (OUT/'Driver.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    global STARTED,REQUESTED,BUSY
    if BUSY or FINISHED:return
    BUSY=True
    try:
        if time.monotonic()-START>480:finish('Owned PIE watchdog');return
        if time.monotonic()-START<8:return
        log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        completed=[s for s in log.splitlines() if 'Test Completed' in s and TEST in s]
        if completed:
            report['completion']=completed[-1];finish(None if 'Success' in completed[-1] else completed[-1]);return
        if not STARTED:
            STARTED=True;unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+TEST);return
        if not REQUESTED and 'Test Started' in log and TEST in log:
            REQUESTED=True;unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False


HANDLE=unreal.register_slate_post_tick_callback(tick)
