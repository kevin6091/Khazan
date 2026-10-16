"""Owned Main RHI PIE lifecycle. The native fixture performs all gameplay operations."""
from pathlib import Path
import ctypes, json, os, time, traceback, unreal
ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_COMBAT_UI_OUTPUT'])
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
START = time.monotonic(); STARTED = REQUESTED = FINISHED = BUSY = False
TEST = 'Khazan.CombatUI.PIE'
manifest = json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel = ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768);handle=kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer))
assert Path(buffer.value).resolve() == (ROOT/'Binaries/Win64'/manifest['Modules']['Khazan']).resolve()
REPORT={'project':str(ROOT),'actual_loaded_module':buffer.value,'driver':'Native actual Controller/Widget/ASC/Ability fixture; Python controls only owned editor lifecycle'}
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)

def finish(error=None):
    global FINISHED
    if FINISHED:return
    FINISHED=True
    unreal.unregister_slate_post_tick_callback(HANDLE)
    REPORT['status']='failed' if error else 'passed'
    if error:REPORT['error']=error;unreal.log_error(error)
    REPORT['seconds']=time.monotonic()-START
    (OUT/'PIEDriver.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()

def tick(delta):
    global STARTED,REQUESTED,BUSY
    if BUSY or FINISHED:return
    BUSY=True
    try:
        if time.monotonic()-START>240:finish('Owned UI PIE watchdog');return
        if time.monotonic()-START<25:return
        log=OUT/'Editor.log';text=log.read_text(encoding='utf-8',errors='replace') if log.exists() else ''
        done=[line for line in text.splitlines() if 'Test Completed' in line and TEST in line]
        if done:
            REPORT['completion']=done[-1]
            bad=[line for line in text.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line or 'Missing ComponentMask input' in line]
            REPORT['material_compile_failures']=bad
            finish(bad[0] if bad else None if 'Success' in done[-1] else done[-1]);return
        if not STARTED:
            STARTED=True
            unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
            unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+TEST)
        elif not REQUESTED and 'Test Started' in text and TEST in text:
            REQUESTED=True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False

HANDLE=unreal.register_slate_post_tick_callback(tick)
