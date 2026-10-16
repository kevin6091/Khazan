"""Targeted Main authoring of source camera notify windows and parry Niagara.

Use KZ_GIANT_CAMERA_MODE=probe first. Apply saves only the 48 mapped monster
sequences and GA_Player_Guard, backing up exact bytes before each save.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import traceback
from collections import defaultdict
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve()
EXPECTED = Path("C:/Users/user/Desktop/GitProject/Khazan/Khazan")
assert ROOT == EXPECTED
OUT = ROOT / "Metadata/GiantCamera_20261014"
PLAN = json.loads((OUT / "OriginalCameraEvents.json").read_text(encoding="utf-8"))
MODE = os.environ.get("KZ_GIANT_CAMERA_MODE", "probe")
assert MODE in ("probe", "apply")
TRACK = "MonsterCamera"
GUARD = "/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard"
DISTORTION = "/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort"
AL = unreal.AnimationLibrary
EAL = unreal.EditorAssetLibrary
STATE = unreal.load_class(None, "/Script/Khazan.KZAnimNotifyState_MonsterVisual")


def f32(value):
    return struct.unpack("f", struct.pack("f", float(value)))[0]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset):
    return ROOT / "Content" / (asset.removeprefix("/Game/") + ".uasset")


def write(name, data):
    target = OUT / name
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, target)


def backup(asset, row):
    source = disk_path(asset)
    destination = ROOT / "Saved/ImportReports/GiantCamera_20261014/Before" / source.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    current_hash = sha(source)
    if destination.exists():
        assert sha(destination) == current_hash, "Baseline changed after a prior backup: " + asset
    else:
        shutil.copy2(source, destination)
    row.update(before_sha256=current_hash, backup=str(destination), backup_sha256=sha(destination))


def snapshot(asset):
    result = []
    for event in AL.get_animation_notify_events(asset):
        state = event.get_editor_property("notify_state_class")
        result.append({
            "text": event.export_text(),
            "trigger": AL.get_anim_notify_event_trigger_time(event),
            "duration": AL.get_anim_notify_event_duration(event),
            "state": state.get_path_name() if state else None,
        })
    return result


def source_fields(row):
    raw = row["raw_camera_properties"]
    ranges = row["raw_show_range"]
    max_radius = float(ranges.get("ScaleMaxRadius", 0))
    min_radius = float(ranges.get("ScaleMinRadius", 0))
    if max_radius and min_radius:
        near, far = sorted((max_radius, min_radius))
    elif max_radius:
        near = far = max_radius
    else:
        near, far = 0, min_radius
    return {
        "bSourceCameraShake": True,
        "CameraEventId": row["event_id"],
        "CameraAmplitudeCm": unreal.Vector(*(row["raw_axis_amplitude_cm"][axis] for axis in "XYZ")),
        "CameraFrequencyHz": unreal.Vector(*(row["raw_axis_frequency_hz"][axis] for axis in "XYZ")),
        "CameraFOVAmplitudeDegrees": row["raw_fov_amplitude_degrees"],
        "CameraFOVFrequencyHz": row["raw_fov_frequency_hz"],
        "CameraShakeScale": raw.get("CameraShakeScale", 1.0),
        "CameraFinalScale": raw.get("FinalScale", 0.1),
        "CameraFadeInSeconds": raw.get("FadeIn", {}).get("BlendTime", 0.0),
        "CameraFadeOutSeconds": raw.get("FadeOut", {}).get("BlendTime", 0.0),
        "CameraNearRadiusCm": near,
        "CameraFarRadiusCm": far,
        "CameraDistanceBone": ranges.get("BoneName", "None"),
    }


def apply_state(state, fields):
    for name, value in fields.items():
        state.set_editor_property(name, value)


def run():
    report = {"schema": "Khazan.GiantCamera.Authoring.v1", "mode": MODE, "status": "running",
              "plan_sha256": sha(OUT / "OriginalCameraEvents.json"), "assets": [], "events": [],
              "ga_guard": {}, "source_defaults_inferred": "Missing CameraShakeScale -> 1; missing FinalScale -> modal explicit 0.1 (assistant TEMP); missing frequency -> smooth finite pulse; radius order sorted for attenuation"}
    try:
        assert STATE is not None
        assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
        distortion = unreal.load_asset(DISTORTION)
        guard = unreal.load_asset(GUARD)
        guard_class = unreal.EditorAssetLibrary.load_blueprint_class(GUARD)
        assert distortion and guard and guard_class
        default = unreal.get_default_object(guard_class)
        assert default.get_editor_property("ParryBillboardDistortion") is None or \
               default.get_editor_property("ParryBillboardDistortion") == distortion
        supported = [row for row in PLAN["events"] if row["author_supported"]]
        groups = defaultdict(list)
        for row in supported:
            groups[row["current_asset"]].append(row)
        assert len(groups) == 48 and len(supported) == 86
        for path, rows in sorted(groups.items()):
            file = disk_path(path)
            assert file.exists(), path
            asset = unreal.load_asset(path)
            assert isinstance(asset, unreal.AnimSequence), path
            assert TRACK not in [str(x) for x in AL.get_animation_notify_track_names(asset)], path
            for row in rows:
                assert 0 <= row["current_start_seconds"] < row["current_end_seconds"] <= asset.get_play_length() + 1e-4, row["event_id"]
            report["assets"].append({"path": path, "before_sha256": sha(file), "planned_events": len(rows),
                                     "play_seconds": asset.get_play_length(), "before_notifies": len(snapshot(asset))})
        report["preflight"] = {"mapped_events": len(supported), "target_assets": len(groups),
                               "distortion": distortion.get_path_name(), "guard": guard.get_path_name(),
                               "unmapped_source_events": PLAN["summary"]["missing_current_asset"]}
        if MODE == "probe":
            path = sorted(groups)[0]
            asset = unreal.load_asset(path)
            before = snapshot(asset)
            row = sorted(groups[path], key=lambda value: (value["current_start_seconds"], value["event_id"]))[0]
            AL.add_animation_notify_track(asset, TRACK, unreal.LinearColor(0.5, 0.2, 0.85, 1))
            start = f32(row["current_start_seconds"])
            end = f32(row["current_end_seconds"])
            state = AL.add_animation_notify_state_event(asset, TRACK, start, f32(end-start), STATE)
            assert state
            apply_state(state, source_fields(row))
            after = snapshot(asset)
            assert len(after) == len(before) + 1
            texts = {item["text"] for item in after}
            assert all(item["text"] in texts for item in before), "Existing notify changed in transient probe"
            created = next(item for item in AL.get_animation_notify_events(asset)
                           if item.get_editor_property("notify_state_class") == state)
            assert abs(AL.get_anim_notify_event_trigger_time(created) - start) <= 1e-4
            report["transient_author_probe"] = {"asset": path, "source_event": row["event_id"],
                                                 "existing_notifies_preserved": True,
                                                 "disk_sha256_unchanged": sha(disk_path(path)) == report["assets"][0]["before_sha256"]}
            report["status"] = "passed"
            return report
        guard_row = {"path": GUARD}
        backup(GUARD, guard_row)
        default.set_editor_property("ParryBillboardDistortion", distortion)
        assert EAL.save_loaded_asset(guard, only_if_is_dirty=False)
        guard_row["after_sha256"] = sha(disk_path(GUARD))
        report["ga_guard"] = guard_row
        write("AuthoringProgress.json", report)
        for path, rows in sorted(groups.items()):
            asset = unreal.load_asset(path)
            before = snapshot(asset)
            target = next(item for item in report["assets"] if item["path"] == path)
            backup(path, target)
            AL.add_animation_notify_track(asset, TRACK, unreal.LinearColor(0.5, 0.2, 0.85, 1))
            for row in sorted(rows, key=lambda value: (value["current_start_seconds"], value["event_id"])):
                start = f32(row["current_start_seconds"])
                end = f32(row["current_end_seconds"])
                state = AL.add_animation_notify_state_event(asset, TRACK, start, f32(end-start), STATE)
                assert state, row["event_id"]
                fields = source_fields(row)
                apply_state(state, fields)
                event = next(item for item in AL.get_animation_notify_events(asset)
                             if item.get_editor_property("notify_state_class") == state)
                actual_start = AL.get_anim_notify_event_trigger_time(event)
                actual_end = actual_start + AL.get_anim_notify_event_duration(event)
                assert abs(actual_start-start) <= 1e-4 and abs(actual_end-end) <= 1e-4, row["event_id"]
                report["events"].append({"event_id": row["event_id"], "asset": path,
                                         "start": actual_start, "end": actual_end,
                                         "source_sha256": row["source_sha256"],
                                         "state_path": state.get_path_name()})
            after = snapshot(asset)
            original_texts = {item["text"] for item in after}
            assert all(item["text"] in original_texts for item in before), "Pre-existing notify altered: " + path
            assert len(after) == len(before)+len(rows)
            assert EAL.save_loaded_asset(asset, only_if_is_dirty=False), "save failed: " + path
            target["after_sha256"] = sha(disk_path(path))
            target["after_notifies"] = len(after)
            write("AuthoringProgress.json", report)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    return report


if __name__ == "__main__":
    result = run()
    write("AuthoringProbe.json" if MODE == "probe" else "Authoring.json", result)
    print("KZ_GIANT_CAMERA_AUTHOR_" + result["status"].upper(), flush=True)
