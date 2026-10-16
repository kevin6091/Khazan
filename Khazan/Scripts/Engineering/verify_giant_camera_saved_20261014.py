"""Fresh-editor readback of the 86 source camera states and parry Niagara binding."""
import hashlib
import json
import traceback
from collections import defaultdict
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantCamera_20261014"
PLAN = json.loads((OUT / "OriginalCameraEvents.json").read_text(encoding="utf-8"))
AUTHOR = json.loads((OUT / "Authoring.json").read_text(encoding="utf-8"))
AL = unreal.AnimationLibrary
GUARD = "/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard"
DISTORTION = "/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort"


def close(actual, expected, name, tolerance=0.0002):
    assert abs(float(actual) - float(expected)) <= tolerance, (name, actual, expected)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vec_match(actual, expected, name):
    for axis in "xyz":
        close(getattr(actual, axis), expected[axis.upper()], name + "." + axis)


def run():
    report = {"schema": "Khazan.GiantCamera.SavedReadback.v1", "status": "running", "assets": [], "events": []}
    try:
        assert AUTHOR["status"] == "passed"
        expected = defaultdict(dict)
        for row in PLAN["events"]:
            if row["author_supported"]:
                expected[row["current_asset"]][row["event_id"]] = row
        assert len(expected) == 48 and sum(map(len, expected.values())) == 86
        distortion = unreal.load_asset(DISTORTION)
        guard_class = unreal.EditorAssetLibrary.load_blueprint_class(GUARD)
        assert distortion is not None and guard_class is not None
        default = unreal.get_default_object(guard_class)
        assert default.get_editor_property("ParryBillboardDistortion") == distortion
        report["guard_distortion"] = distortion.get_path_name()
        for authored in AUTHOR["assets"]:
            path = authored["path"]
            asset = unreal.load_asset(path)
            assert isinstance(asset, unreal.AnimSequence), path
            file = ROOT / "Content" / (path.removeprefix("/Game/") + ".uasset")
            current_sha = sha(file)
            changed_since_authoring = current_sha != authored["after_sha256"]
            assert "MonsterCamera" in [str(x) for x in AL.get_animation_notify_track_names(asset)]
            events = AL.get_animation_notify_events(asset)
            assert len(events) >= authored["before_notifies"] + authored["planned_events"], path
            found = set()
            for event in events:
                state = event.get_editor_property("notify_state_class")
                if not state or not isinstance(state, unreal.KZAnimNotifyState_MonsterVisual) or not state.get_editor_property("bSourceCameraShake"):
                    continue
                key = str(state.get_editor_property("CameraEventId"))
                assert key in expected[path] and key not in found, (path, key)
                found.add(key)
                row = expected[path][key]
                raw = row["raw_camera_properties"]
                start = AL.get_anim_notify_event_trigger_time(event)
                end = start + AL.get_anim_notify_event_duration(event)
                close(start, row["current_start_seconds"], key + ".start")
                close(end, row["current_end_seconds"], key + ".end")
                vec_match(state.get_editor_property("CameraAmplitudeCm"), row["raw_axis_amplitude_cm"], key + ".amplitude")
                vec_match(state.get_editor_property("CameraFrequencyHz"), row["raw_axis_frequency_hz"], key + ".frequency")
                close(state.get_editor_property("CameraFOVAmplitudeDegrees"), row["raw_fov_amplitude_degrees"], key + ".fov")
                close(state.get_editor_property("CameraFOVFrequencyHz"), row["raw_fov_frequency_hz"], key + ".fov_frequency")
                close(state.get_editor_property("CameraShakeScale"), raw.get("CameraShakeScale", 1.0), key + ".scale")
                close(state.get_editor_property("CameraFinalScale"), raw.get("FinalScale", 0.1), key + ".final_scale")
                close(state.get_editor_property("CameraFadeInSeconds"), raw.get("FadeIn", {}).get("BlendTime", 0.0), key + ".fade_in")
                close(state.get_editor_property("CameraFadeOutSeconds"), raw.get("FadeOut", {}).get("BlendTime", 0.0), key + ".fade_out")
                report["events"].append({"event_id": key, "asset": path, "start": start, "end": end})
            assert found == set(expected[path]), (path, sorted(set(expected[path]) - found))
            report["assets"].append({"path": path, "sha256": current_sha, "changed_since_authoring": changed_since_authoring,
                                     "camera_events": len(found), "total_notifies": len(events)})
        assert len(report["assets"]) == 48 and len(report["events"]) == 86
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    (OUT / "SavedReadback.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise RuntimeError(report["error"])
    print("KZ_GIANT_CAMERA_SAVED_READBACK_PASSED", len(report["assets"]), len(report["events"]), flush=True)


run()
