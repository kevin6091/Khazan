"""Own hidden editor lifecycle for existing native giant-pattern regression."""
from pathlib import Path
import ctypes
import json
import time
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
assert ROOT == Path(r"C:\Users\user\Desktop\GitProject\Khazan\Khazan")
OUT = ROOT / "Metadata/GiantGrabs_20261013"
LOG = OUT / "ImmediateMoveMainRHI.log"
TEST = "Khazan.GiantFall.PIE"
START = time.monotonic()
started = requested = busy = finished = False
report = {"project": str(ROOT), "test": TEST}
manifest = json.loads((ROOT / "Binaries/Win64/UnrealEditor.modules").read_text(encoding="utf-8-sig"))
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
buf = ctypes.create_unicode_buffer(32768)
handle = kernel.GetModuleHandleW(manifest["Modules"]["Khazan"])
assert handle and kernel.GetModuleFileNameW(handle, buf, len(buf))
assert Path(buf.value).resolve() == (ROOT / "Binaries/Win64" / manifest["Modules"]["Khazan"]).resolve()
report["module"] = buf.value
unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings").set_editor_property("bThrottleCPUWhenNotForeground", False)


def finish(error=None):
    global finished
    if finished:
        return
    finished = True
    unreal.unregister_slate_post_tick_callback(callback)
    report["status"] = "failed" if error else "passed"
    if error:
        report["error"] = error
        unreal.log_error(error)
    (OUT / "ImmediateMoveMainRHIDriver.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    global started, requested, busy
    if busy or finished:
        return
    busy = True
    try:
        if time.monotonic() - START > 540:
            finish("Native giant PIE watchdog")
            return
        if time.monotonic() - START < 8:
            return
        data = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
        completed = [line for line in data.splitlines() if "Test Completed" in line and TEST in line]
        if completed:
            report["completion"] = completed[-1]
            finish(None if "Success" in completed[-1] else completed[-1])
            return
        if not started:
            started = True
            unreal.SystemLibrary.execute_console_command(None, "t.MaxFPS 60")
            unreal.SystemLibrary.execute_console_command(None, "Automation RunTests " + TEST)
            return
        if not requested and "Test Started" in data and TEST in data:
            requested = True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:
        finish(traceback.format_exc())
    finally:
        busy = False


callback = unreal.register_slate_post_tick_callback(tick)

