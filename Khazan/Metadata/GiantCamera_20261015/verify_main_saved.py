"""Read-only Main verification; preserve the previous day's evidence."""
import ctypes
import hashlib
import json
from pathlib import Path

import unreal


root = Path(unreal.Paths.project_dir()).resolve()
assert root == Path("C:/Users/user/Desktop/GitProject/Khazan/Khazan")
output = root / "Metadata/GiantCamera_20261015/MainSavedReadback.json"
verifier = root / "Scripts/Engineering/verify_giant_camera_saved_20261014.py"
source = verifier.read_text(encoding="utf-8")
old = '(OUT / "SavedReadback.json").write_text'
new = '(ROOT / "Metadata/GiantCamera_20261015/MainSavedReadback.json").write_text'
assert source.count(old) == 1
exec(compile(source.replace(old, new), str(verifier), "exec"), {"__file__": str(verifier), "__name__": "__main__"})

manifest = json.loads((root / "Binaries/Win64/UnrealEditor.modules").read_text(encoding="utf-8-sig"))
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
buffer = ctypes.create_unicode_buffer(32768)
handle = kernel.GetModuleHandleW(manifest["Modules"]["Khazan"])
assert handle and kernel.GetModuleFileNameW(handle, buffer, len(buffer))
module = Path(buffer.value).resolve()
assert module == (root / "Binaries/Win64" / manifest["Modules"]["Khazan"]).resolve()
assert unreal.load_class(None, "/Script/Khazan.KZCombatCameraModifier")
report = json.loads(output.read_text(encoding="utf-8"))
report.update(project=str(root), actual_module=str(module), module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(), saved_packages=0)
output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("KZ_GIANT_CAMERA_MAIN_RECHECK_PASSED", report["module_sha256"], flush=True)
