"""Own only this task's editor/PIE; native tests own gameplay and assertions."""
from pathlib import Path
import json, os, time, traceback, hashlib, ctypes, unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT']);MODE=os.environ['KZ_MONSTER_REPAIR_MODE']
TEST=os.environ['KZ_MONSTER_REPAIR_TEST'] or ('Khazan.MonsterRepair.AuthorParticles' if MODE=='asset_editor' else 'Khazan.MonsterRepair.PIE')
assert ROOT in [Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]
report={'status':'running','project':str(ROOT),'test':TEST,'asset_saves':'only task-private author when explicitly selected'}
manifest=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));module=ROOT/'Binaries/Win64'/manifest['Modules']['Khazan']
report['manifest_module']=str(module);report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)
assert loaded and kernel.GetModuleFileNameW(loaded,buffer,len(buffer))
assert Path(buffer.value).resolve()==module.resolve()
report['actual_loaded_module']=buffer.value
os.environ['KZ_COMBAT_UI_OUTPUT']=str(OUT)
unreal.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
if MODE!='asset_editor':
    # Both selected projects retain Config/DefaultEngine.ini EditorStartupMap=/Game/Maps/DevMap.DevMap.
    assert 'EditorStartupMap=/Game/Maps/DevMap.DevMap' in (ROOT/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')
START=time.monotonic();started=requested=finished=busy=False
def finish(error=None):
    global finished
    if finished:return
    finished=True;unreal.unregister_slate_post_tick_callback(handle)
    report['status']='failed' if error else 'passed';report['seconds']=time.monotonic()-START
    if error:report['error']=error;unreal.log_error(error)
    (OUT/'Driver.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if MODE!='asset_editor':unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()
def tick(delta):
    global started,requested,busy
    if busy or finished:return
    busy=True
    try:
        elapsed=time.monotonic()-START
        if elapsed>1300:finish('Task-owned editor test watchdog');return
        if elapsed<8:return
        log=(OUT/'Editor.log').read_text(encoding='utf-8',errors='replace')
        done=[x for x in log.splitlines() if 'Test Completed' in x and TEST in x]
        if done:
            report['completion']=done[-1];bad=[x for x in log.splitlines() if 'Failed to compile Material' in x or 'Default Material will be used' in x]
            report['material_compile_failures']=bad;finish(bad[0] if bad else None if 'Success' in done[-1] else done[-1]);return
        if not started:
            started=True;unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60');unreal.SystemLibrary.execute_console_command(None,'Automation RunTests '+TEST)
        elif not requested and 'Test Started' in log and TEST in log and MODE!='asset_editor' and TEST not in ['Khazan.MonsterRepair.PIE','Khazan.CombatUI.PIE']:
            requested=True;unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=unreal.register_slate_post_tick_callback(tick)
