"""Ensure a startup audit failure also closes this owned read-only verifier."""
from pathlib import Path
import json
import os
import traceback
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
launch=json.loads((root/'Saved/ImportReports/HeinMachSnow_20261006/MainVerificationLaunch.json').read_text())
assert os.getpid()==launch['pid'] and os.environ.get('KZ_SNOW_MAIN_VERIFY_TOKEN')==launch['token']
try:
    path=root/'Scripts/Art/heinmach_snow_main_verify.py'
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),globals())
except Exception:
    (root/'Saved/ImportReports/HeinMachSnow_20261006/MainStartupFailure.txt').write_text(traceback.format_exc(),encoding='utf-8')
    traceback.print_exc();unreal.SystemLibrary.quit_editor()
