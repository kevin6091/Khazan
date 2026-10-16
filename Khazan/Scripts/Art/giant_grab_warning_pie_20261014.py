"""Run the saved giant combat fixture and capture actual grab-warning presentation."""
from pathlib import Path
import json
import time
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014/PIE"
OUT.mkdir(exist_ok=True)
LOG = OUT / "Editor.log"
TEST = "Khazan.GiantFall.PIE"
START = time.monotonic()
started = requested = busy = finished = False
seen = set()
pending = []
report = {"status": "running", "test": TEST, "grab_visual_begins": [], "images": [], "source_audio_plays": [], "particle_samples": []}
u.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings").set_editor_property("bThrottleCPUWhenNotForeground", False)


def finish(error=None):
    global finished
    if finished:
        return
    finished = True
    report["status"] = "failed" if error else "passed"
    if error:
        report["error"] = error
        u.log_error(error)
    (OUT / "RuntimeReport.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    u.unregister_slate_post_tick_callback(callback)
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.SystemLibrary.quit_editor()


def tick(delta):
    global started, requested, busy
    if busy or finished:
        return
    busy = True
    try:
        elapsed = time.monotonic() - START
        if elapsed > 540:
            finish("Giant warning PIE watchdog")
            return
        if elapsed < 8:
            return
        data = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        for line in data.splitlines():
            if "MonsterVisual Begin" in line and "KZGrabWarning_" in line and line not in seen:
                seen.add(line)
                report["grab_visual_begins"].append(line)
                pending.append({"at": time.monotonic(), "line": line, "shots": set(), "samples": set()})
            if "KZAudio Play" in line and "SW_UI_HoldingAttack" in line and line not in seen:
                seen.add(line)
                report["source_audio_plays"].append(line)
        for item in pending:
            age = time.monotonic() - item["at"]
            for threshold in (0.0, 0.03, 0.08, 0.13, 0.25, 0.5, 1.0):
                if world and threshold not in item["samples"] and age >= threshold:
                    actor_name = item["line"].split("Actor=", 1)[1].split(" ", 1)[0]
                    actor = next((a for a in u.GameplayStatics.get_all_actors_of_class(world, u.KZMonster)
                                  if a.get_name() == actor_name), None)
                    sample = {"actor": actor_name, "at": threshold, "actual_age": age, "components": []}
                    if actor:
                        for component in actor.get_components_by_class(u.ParticleSystemComponent):
                            tags = [str(t) for t in component.get_editor_property("component_tags")]
                            if "KZCombatEffect" not in tags:
                                continue
                            sample["components"].append({
                                "name": component.get_name(), "tags": tags,
                                "particles": component.get_num_active_particles(),
                                "active": component.is_active(),
                                "location": str(component.get_world_location()),
                                "scale": str(component.get_world_scale()),
                                "template": component.get_editor_property("template").get_path_name()
                                if component.get_editor_property("template") else None})
                    report["particle_samples"].append(sample)
                    item["samples"].add(threshold)
            for threshold in (0.1, 0.4):
                if threshold not in item["shots"] and age >= threshold and world:
                    name = ("Yetuga" if "Yetuga" in item["line"] else "Apes") + "_" + str(len(report["images"])) + ".png"
                    image = OUT / name
                    u.SystemLibrary.execute_console_command(world, 'Shot filename="' + str(image) + '" -nosuffix')
                    item["shots"].add(threshold)
                    report["images"].append({"path": str(image), "warning": item["line"], "at": threshold})
        completed = [line for line in data.splitlines() if "Test Completed" in line and TEST in line]
        if completed:
            report["completion"] = completed[-1]
            count = len(report["grab_visual_begins"])
            particles = {family: any(family in sample["actor"] and any(
                component["particles"] > 0 and any("KZGrabWarning_" in tag for tag in component["tags"])
                for component in sample["components"]) for sample in report["particle_samples"])
                for family in ("Apes", "Yetuga")}
            audio = {family: any(family in line for line in report["source_audio_plays"])
                     for family in ("Apes", "Yetuga")}
            report["verification"] = {"active_warning_particles": particles, "source_audio": audio}
            error = None if "Success" in completed[-1] and count >= 2 and all(particles.values()) and all(audio.values()) else "Grab warning presentation incomplete; inspect verification and particle samples"
            finish(error)
            return
        if not started:
            started = True
            u.SystemLibrary.execute_console_command(None, "t.MaxFPS 60")
            u.SystemLibrary.execute_console_command(None, "log LogTemp Verbose")
            u.SystemLibrary.execute_console_command(None, "Automation RunTests " + TEST)
            return
        if not requested and "Test Started" in data and TEST in data:
            requested = True
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:
        finish(traceback.format_exc())
    finally:
        busy = False


callback = u.register_slate_post_tick_callback(tick)
