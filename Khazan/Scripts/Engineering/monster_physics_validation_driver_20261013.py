"""Owned process only: explicit native tests, fresh PIE per integration case, save nothing."""
from pathlib import Path
import ctypes,hashlib,json,os,time,traceback,unreal
MAIN=Path(__file__).resolve().parents[2]
PROJECT=Path(unreal.Paths.project_dir()).resolve()
assert PROJECT in (MAIN,MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan')
OUT=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
TESTS=os.environ['KZ_MONSTER_PHYSICS_TESTS'].split(',')
manifest=json.loads((PROJECT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768)
handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer))
module=Path(buffer.value).resolve();assert module.is_relative_to(PROJECT/'Binaries')
report=dict(project=str(PROJECT),actual_module=str(module),module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),tests=[],status='running',saved_packages=0)
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')
START=LAST=time.monotonic();INDEX=0;STAGE='warmup';BUSY=DONE=False

def finish(error=None):
    global DONE
    if DONE:return
    DONE=True;unreal.unregister_slate_post_tick_callback(CALLBACK)
    report['status']='failed' if error or any(not t['passed'] for t in report['tests']) else 'passed'
    if error:report['error']=error
    (OUT/'Driver.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if unreal.EditorLevelLibrary.get_pie_worlds(False):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global INDEX,STAGE,LAST,BUSY
    if BUSY or DONE:return
    BUSY=True
    try:
        if time.monotonic()-START>1200:finish('Batch watchdog');return
        if INDEX>=len(TESTS):finish();return
        if STAGE=='warmup':
            if time.monotonic()-LAST<5:return
            unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60');STAGE='start'
        if STAGE=='between':
            if unreal.EditorLevelLibrary.get_pie_worlds(False) or time.monotonic()-LAST<1:return
            STAGE='start'
        test=TESTS[INDEX]
        if STAGE=='start':
            LAST=time.monotonic();STAGE='await_test'
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+test);return
        log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        if 'No automation tests matched' in log:finish('Requested test not registered: '+test);return
        completed=[x for x in log.splitlines() if 'Test Completed' in x and ('Path={'+test+'}') in x]
        if completed:
            report['tests'].append(dict(test=test,passed='Result={Success}' in completed[-1],completion=completed[-1]))
            (OUT/'Progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if unreal.EditorLevelLibrary.get_pie_worlds(False):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            INDEX+=1;STAGE='between';LAST=time.monotonic();return
        if STAGE=='await_test' and any('Test Started' in x and ('Path={'+test+'}') in x for x in log.splitlines()):
            STAGE='running'
            if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        if time.monotonic()-LAST>650:finish('Per-test watchdog: '+test)
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

CALLBACK=unreal.register_slate_post_tick_callback(tick)
