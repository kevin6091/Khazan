from pathlib import Path
import os
import runpy
import unreal

OUT = Path(os.environ["KZ_MONSTER_PHYSICS_OUT"])
DRIVER = Path(unreal.Paths.project_dir()).resolve() / "Scripts/Engineering/monster_physics_validation_driver_20261013.py"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "Ready.txt").write_text(str(os.getpid()), encoding="utf-8")

def start_when_ready(delta):
    if not (OUT / "Go.txt").exists():
        return
    unreal.unregister_slate_post_tick_callback(CALLBACK)
    runpy.run_path(str(DRIVER), run_name="__main__")

CALLBACK = unreal.register_slate_post_tick_callback(start_when_ready)
