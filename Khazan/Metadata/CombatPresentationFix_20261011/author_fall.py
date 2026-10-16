"""Owned editor lifecycle/read-only observation. All gameplay input lives in the native test."""
from pathlib import Path
import ctypes,json,time,traceback,os
import unreal

WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK in [Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]
OUT=Path(os.environ['KZ_CLEAN_OUTPUT'])
LOG=OUT/'Editor.log'
TEST='Khazan.CombatPresentation.AuthorFall'
START=time.monotonic()
REQUESTED=STARTED=BUSY=FINISHED=False
REPORT={'project':str(WORK),'input_driver':'native C++ EnhancedInput/CMC fixture; Python does not move actors or inject input'}
manifest=json.loads((WORK/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768)
handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer))
assert Path(buffer.value).resolve()==(WORK/'Binaries/Win64'/manifest['Modules']['Khazan']).resolve()
REPORT['actual_module']=buffer.value
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)

def finish(error=None):
    global FINISHED
    if FINISHED:return
    FINISHED=True
    unreal.unregister_slate_post_tick_callback(HANDLE)
    REPORT['status']='failed' if error else 'passed'
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'PIEDriver.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global REQUESTED,STARTED,BUSY
    if BUSY or FINISHED:return
    BUSY=True
    try:
        if time.monotonic()-START>540:finish('Owned native PIE watchdog');return
        if time.monotonic()-START<8:return
        text=LOG.read_text(encoding='utf-8',errors='replace') if LOG.exists() else ''
        done=[line for line in text.splitlines() if 'Test Completed' in line and TEST in line]
        if done:
            REPORT['completion']=done[-1];finish(None if 'Success' in done[-1] else done[-1]);return
        if not STARTED:
            STARTED=True
            for cmd in ['t.MaxFPS 60','sg.ViewDistanceQuality 1','sg.ShadowQuality 3','sg.PostProcessQuality 3']:
                unreal.SystemLibrary.execute_console_command(None,cmd)
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+TEST)
            return
        if False:
            REQUESTED=True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=unreal.register_slate_post_tick_callback(tick)
