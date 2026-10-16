"""Reuse completed read-only verifiers against the current Main module and assets."""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
RUN = ROOT / "Metadata/MainIntegration_20261015"
REPORT = {"status": "running", "package_saves": 0, "checked_files": [], "verifiers": []}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(relative, expected):
    actual = sha(ROOT / relative)
    assert actual == expected.lower(), (relative, expected, actual)
    REPORT["checked_files"].append({"file": relative, "sha256": actual})


def staged_verifier(script, original_output, label, inputs):
    output = RUN / label
    output.mkdir(parents=True, exist_ok=True)
    for name in inputs:
        shutil.copy2(ROOT / original_output / name, output / name)
    path = ROOT / script
    source = path.read_text(encoding="utf-8")
    old = 'OUT = ROOT / "' + original_output + '"'
    new = 'OUT = ROOT / "Metadata/MainIntegration_20261015/' + label + '"'
    assert source.count(old) == 1, script
    # Only report/input location is redirected; all original assertions are reused.
    exec(compile(source.replace(old, new), str(path), "exec"), {"__file__": str(path), "__name__": "__main__"})
    REPORT["verifiers"].append({"script": script, "script_sha256": sha(path), "output": label})


try:
    prior = read("Metadata/MainIntegration_20261014/FinalVerification.json")
    check(prior["applied"]["asset"], prior["applied"]["after_sha256"])
    check(prior["applied"]["source"], prior["applied"]["source_sha256"])
    camera = read("Metadata/GiantCamera_20261014/SavedReadback.json")
    assert camera["status"] == "passed" and len(camera["assets"]) == 48
    for row in camera["assets"]:
        check("Content/" + row["path"].removeprefix("/Game/") + ".uasset", row["sha256"])
    camera_final = read("Metadata/GiantCamera_20261014/FinalVerification.json")
    check("Content/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.uasset", camera_final["guard_asset_sha256"])
    slash = read("Metadata/PlayerSlashOuter_20261014/MainApply/Receipt.json")
    for relative, row in slash["targets"].items():
        check(relative, row["after_sha256"])
    latest = read("Metadata/PlayerSlashOuter_20261014/FinalVerification.json")
    check("Binaries/Win64/UnrealEditor-Khazan.dll", latest["main_composed"]["module_sha256"])
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    module = kernel.GetModuleHandleW("UnrealEditor-Khazan.dll")
    buffer = ctypes.create_unicode_buffer(32768)
    assert module and kernel.GetModuleFileNameW(module, buffer, len(buffer))
    assert Path(buffer.value).resolve() == (ROOT / "Binaries/Win64/UnrealEditor-Khazan.dll").resolve()
    REPORT["loaded_module"] = buffer.value
    staged_verifier("Scripts/Engineering/verify_giant_camera_saved_20261014.py", "Metadata/GiantCamera_20261014", "Camera", ["OriginalCameraEvents.json", "Authoring.json"])
    staged_verifier("Scripts/Art/verify_giant_grab_warning_saved_20261014.py", "Metadata/GiantGrabWarning_20261014", "GrabWarning", ["WarningPlan.json"])
    os.environ["KZ_AUDIO_MAIN"] = str(ROOT)
    os.environ["KZ_AUDIO_OUTPUT"] = str(RUN / "PlayerImpact")
    (RUN / "PlayerImpact").mkdir(exist_ok=True)
    runpy.run_path(str(ROOT / "Scripts/Art/verify_player_impact_main_20261014.py"), run_name="__main__")
    os.environ["KZ_SLASH_OUT"] = str(RUN / "PlayerSlash")
    runpy.run_path(str(ROOT / "Scripts/Art/verify_player_slash_outer_20261014.py"), run_name="__main__")
    for row in REPORT["checked_files"]:
        assert sha(ROOT / row["file"]) == row["sha256"], row["file"]
    REPORT["status"] = "passed"
except Exception:
    REPORT["status"] = "failed"
    REPORT["error"] = traceback.format_exc()
    u.log_error(REPORT["error"])
finally:
    REPORT["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (RUN / "SavedVerification.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")

assert REPORT["status"] == "passed", REPORT.get("error")
