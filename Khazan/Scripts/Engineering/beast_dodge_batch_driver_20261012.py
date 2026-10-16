"""Run native integration tests with a fresh PIE world for each test."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import time
import traceback
import unreal

PROJECT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path(__file__).resolve().parents[2]
assert PROJECT==MAIN or PROJECT==MAIN.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'
OUT=Path(os.environ['KZ_BEAST_OUT'])
TESTS=os.environ['KZ_BEAST_TEST'].split(',')
manifest=json.loads((PROJECT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768)
module_handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert module_handle and kernel.GetModuleFileNameW(module_handle,buffer,len(buffer))
module=Path(buffer.value).resolve();assert module.is_relative_to(PROJECT/'Binaries')
report={'status':'running','project':str(PROJECT),'actual_module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'tests':[],'input_driver':'native automation only; fresh PIE world per test'}
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
START=LAST=time.monotonic();INDEX=0;STAGE='warmup';BUSY=DONE=False

def finish(error=None):
    global DONE
    if DONE:return
    DONE=True;unreal.unregister_slate_post_tick_callback(HANDLE)
    report['status']='failed' if error or any(not t['passed'] for t in report['tests']) else 'passed'
    if error:report['error']=error
    (OUT/'Driver.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global INDEX,STAGE,LAST,BUSY
    if BUSY or DONE:return
    BUSY=True
    try:
        if time.monotonic()-START>1500:finish('Batch watchdog');return
        if INDEX>=len(TESTS):finish();return
        if STAGE=='warmup':
            if time.monotonic()-LAST<8:return
            unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            STAGE='start'
        if STAGE=='between':
            if unreal.EditorLevelLibrary.get_pie_worlds(False):return
            if time.monotonic()-LAST<1:return
            STAGE='start'
        test=TESTS[INDEX]
        if STAGE=='start':
            LAST=time.monotonic();STAGE='await_test'
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+test);return
        text=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        completed=[line for line in text.splitlines() if 'Test Completed' in line and ('Path={'+test+'}') in line]
        if completed:
            report['tests'].append({'test':test,'passed':'Result={Success}' in completed[-1],'completion':completed[-1]})
            (OUT/'Progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if unreal.EditorLevelLibrary.get_pie_worlds(False):
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            INDEX+=1;STAGE='between';LAST=time.monotonic();return
        if STAGE=='await_test' and any('Test Started' in line and ('Path={'+test+'}') in line for line in text.splitlines()):
            STAGE='running'
            # Parry starts PIE itself; the synchronous source audit needs no PIE.
            if test not in ('Khazan.Parry.PIE', 'Khazan.BeastDodge.SourceAudit'):
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        if time.monotonic()-LAST>650:finish('Per-test watchdog: '+test)
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=unreal.register_slate_post_tick_callback(tick)
