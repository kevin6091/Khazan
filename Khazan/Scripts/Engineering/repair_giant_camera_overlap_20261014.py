"""Merge only camera states lost to concurrent grab-warning asset saves."""
import hashlib
import importlib.util
import json
import shutil
import traceback
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantCamera_20261014"
SPEC = importlib.util.spec_from_file_location("giant_camera_author", ROOT / "Scripts/Engineering/author_giant_camera_shakes_20261014.py")
author = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(author)
PLAN = json.loads((OUT / "OriginalCameraEvents.json").read_text(encoding="utf-8"))
TARGETS = (
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_CloseGrab_Start",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_CloseGrab_Start_Ori",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_RushGrab",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_RushGrab_Slow",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report = {"schema": "Khazan.GiantCamera.OverlapMerge.v1", "status": "running", "assets": []}
    try:
        for path in TARGETS:
            rows = [row for row in PLAN["events"] if row["author_supported"] and row["current_asset"] == path]
            assert rows, path
            file = author.disk_path(path)
            asset = unreal.load_asset(path)
            assert isinstance(asset, unreal.AnimSequence), path
            before = author.snapshot(asset)
            tracks = [str(name) for name in author.AL.get_animation_notify_track_names(asset)]
            states = {str(state.get_editor_property("CameraEventId")) for event in author.AL.get_animation_notify_events(asset)
                      if (state := event.get_editor_property("notify_state_class")) and
                      isinstance(state, unreal.KZAnimNotifyState_MonsterVisual) and
                      state.get_editor_property("bSourceCameraShake")}
            missing = [row for row in rows if row["event_id"] not in states]
            record = {"path": path, "before_sha256": sha(file), "before_notifies": len(before),
                      "existing_camera_events": len(states), "missing_camera_events": len(missing)}
            if missing:
                backup = ROOT / "Saved/ImportReports/GiantCamera_20261014/BeforeOverlapRepairFinal" / file.relative_to(ROOT)
                backup.parent.mkdir(parents=True, exist_ok=True)
                assert not backup.exists(), "Overlap merge already attempted: " + path
                shutil.copy2(file, backup)
                assert sha(backup) == record["before_sha256"]
                record["backup"] = str(backup)
                if "MonsterCamera" not in tracks:
                    author.AL.add_animation_notify_track(asset, "MonsterCamera", unreal.LinearColor(0.5, 0.2, 0.85, 1))
                for row in sorted(missing, key=lambda value: (value["current_start_seconds"], value["event_id"])):
                    start = author.f32(row["current_start_seconds"])
                    end = author.f32(row["current_end_seconds"])
                    state = author.AL.add_animation_notify_state_event(asset, "MonsterCamera", start, author.f32(end-start), author.STATE)
                    assert state, row["event_id"]
                    author.apply_state(state, author.source_fields(row))
                after = author.snapshot(asset)
                texts = {item["text"] for item in after}
                assert len(after) == len(before) + len(missing)
                assert all(item["text"] in texts for item in before), "Non-camera notify changed: " + path
                assert author.EAL.save_loaded_asset(asset, only_if_is_dirty=False), path
            record["after_sha256"] = sha(file)
            record["after_notifies"] = len(author.snapshot(asset))
            report["assets"].append(record)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    (OUT / "OverlapMergeFinal.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise RuntimeError(report["error"])
    print("KZ_GIANT_CAMERA_OVERLAP_MERGE_PASSED", flush=True)


run()
