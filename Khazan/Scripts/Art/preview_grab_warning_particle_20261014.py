"""Isolated game-camera preview of the recovered warning Cascade graph."""
from pathlib import Path
import json
import math
import time
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014/ParticlePreview"
OUT.mkdir(parents=True, exist_ok=True)
START = time.monotonic()
WORLD = None
COMPONENTS = []
FRAMES = 0
DONE = False
REPORT = {"status": "running", "samples": [], "images": []}


def finish(error=None):
    global DONE
    if DONE:
        return
    DONE = True
    REPORT["status"] = "failed" if error else "passed"
    if error:
        REPORT["error"] = error
    (OUT / "Preview.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    u.unregister_slate_post_tick_callback(HANDLE)
    u.SystemLibrary.execute_console_command(WORLD, "QUIT")


def tick(delta):
    global WORLD, FRAMES
    try:
        if time.monotonic() - START > 180:
            finish("Preview watchdog")
            return
        if WORLD is None:
            candidate = u.load_object(None, "/Game/Maps/DevMap.DevMap")
            if not candidate or not u.GameplayStatics.get_player_controller(candidate, 0):
                return
            WORLD = candidate
            u.SystemLibrary.execute_console_command(WORLD, "t.MaxFPS 30")
        FRAMES += 1
        if FRAMES == 90:
            ps = u.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
            camera = u.GameplayStatics.get_player_camera_manager(WORLD, 0)
            cam_location, cam_rotation = camera.get_camera_location(), camera.get_camera_rotation()
            pitch, yaw = math.radians(cam_rotation.pitch), math.radians(cam_rotation.yaw)
            forward = u.Vector(math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
            right = u.Vector(-math.sin(yaw), math.cos(yaw), 0)
            REPORT["camera"] = {"location": str(cam_location), "rotation": str(cam_rotation)}
            for label, side, rotation in (("world_zero", -1, u.Rotator()), ("camera_rotation", 1, cam_rotation)):
                location = cam_location + forward * 400 + right * (side * 160)
                component = u.GameplayStatics.spawn_emitter_at_location(WORLD, ps, location, auto_destroy=False)
                assert component, label
                component.set_world_rotation(rotation, False, False)
                COMPONENTS.append((label, component))
        if COMPONENTS and FRAMES in (93, 96, 102, 108, 120):
            sample = {"frame": FRAMES, "emitters": [
                {"label": label, "particles": component.get_num_active_particles(),
                 "location": str(component.get_world_location()), "active": component.is_active()}
                for label, component in COMPONENTS]}
            REPORT["samples"].append(sample)
            image = OUT / ("Frame_" + str(FRAMES) + ".png")
            u.SystemLibrary.execute_console_command(WORLD, 'Shot filename="' + str(image) + '" -nosuffix')
            REPORT["images"].append(str(image))
        if FRAMES > 125:
            finish()
    except Exception:
        finish(traceback.format_exc())


HANDLE = u.register_slate_post_tick_callback(tick)
