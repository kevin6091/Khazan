"""Add the original grab warning to seven current AnimSequences, preserve all prior tracks."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014"
PLAN = json.loads((OUT / "WarningPlan.json").read_text(encoding="utf-8"))
LIB = u.EditorAssetLibrary
ANIM = u.AnimationLibrary
PARTICLE = LIB.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
SOUND = LIB.load_asset("/Game/Audio/Original/Media/SW_UI_HoldingAttack")
STATE = u.load_class(None, "/Script/Khazan.KZAnimNotifyState_MonsterVisual")
EFFECT = u.load_class(None, "/Script/Khazan.KZAnimNotify_CombatEffect")
AUDIO = u.load_class(None, "/Script/Khazan.KZAnimNotify_PlayAudio")
assert PARTICLE and SOUND and STATE and EFFECT and AUDIO
TRACK = "GrabWarning"
REPORT = {"success": False, "sequences": [], "errors": []}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_for(asset):
    path = ROOT / "Content" / (asset.removeprefix("/Game/") + ".uasset")
    assert path.resolve().is_relative_to((ROOT / "Content/_Art/Enemies").resolve())
    assert path.exists(), path
    return path


try:
    for row in PLAN["windows"]:
        path = row["asset"]
        file = file_for(path)
        before_sha = sha(file)
        asset = LIB.load_asset(path)
        assert isinstance(asset, u.AnimSequence), path
        tracks = [str(t) for t in ANIM.get_animation_notify_track_names(asset)]
        if TRACK in tracks:
            assert LIB.get_metadata_tag(asset, "KZGrabWarningPlan") == "GiantGrabWarning_20261014/WarningPlan.json", path
            notifies = ANIM.get_animation_notify_events(asset)
            visuals = [n.get_editor_property("notify_state_class") for n in notifies]
            visuals = [v for v in visuals if isinstance(v, u.KZAnimNotifyState_MonsterVisual)
                       and v.get_editor_property("effect") and v.get_editor_property("effect").get_editor_property("ParticleTemplate") == PARTICLE]
            sounds = [n.get_editor_property("notify") for n in notifies]
            sounds = [a for a in sounds if isinstance(a, u.KZAnimNotify_PlayAudio)
                      and a.get_editor_property("sound") == SOUND]
            assert len(visuals) == len(sounds) == 1, (path, len(visuals), len(sounds))
            REPORT["sequences"].append({"asset": path, "file": str(file), "saved_sha256": before_sha,
                                        "start": row["start"], "end": row["end"],
                                        "status": "already_authored_verified", "visual_count": 1, "audio_count": 1})
            continue
        assert row["end"] <= asset.get_play_length() + 1e-4, (path, row, asset.get_play_length())
        before_events = [e.export_text() for e in ANIM.get_animation_notify_events(asset)]
        before_settings = {"length": asset.get_play_length(),
                           "root_motion": asset.get_editor_property("enable_root_motion")}
        assert sha(file) == before_sha, "Concurrent asset change: " + path
        backup = OUT / "Before" / file.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert not backup.exists(), ("Previous authoring attempt; inspect before rerun", backup)
        shutil.copy2(file, backup)
        assert sha(backup) == before_sha

        ANIM.add_animation_notify_track(asset, TRACK, u.LinearColor(1., .65, .1, 1.))
        state = ANIM.add_animation_notify_state_event(asset, TRACK, row["start"], row["end"] - row["start"], STATE)
        assert state, path
        effect = u.new_object(EFFECT, outer=state, name="OriginalGrabTelegraph")
        state.set_editor_property("effect", effect)
        event_id = "KZGrabWarning_" + hashlib.sha256(path.encode()).hexdigest()[:12]
        for field, value in (("ParticleTemplate", PARTICLE), ("EventId", event_id),
                             ("SourceSocket", "UI_Chest"), ("bAttached", True),
                             ("bUseWorldParticleUnits", True), ("bDestroyOnAnimEnd", True),
                             ("WindowStartTime", row["start"]), ("WindowEndTime", row["end"])):
            effect.set_editor_property(field, value)
        audio = ANIM.add_animation_notify_event(asset, TRACK, row["start"], AUDIO)
        assert audio, path
        for field, value in (("sound", SOUND), ("source_package", PLAN["source_audio"]),
                             ("source_field", row["source_package"] + "/Notifies[" + str(row["source_notify_index"]) + "]"),
                             ("only_for_local_or_locked_target", False),
                             ("preserve_finite_tail_on_owner_destroyed", True)):
            audio.set_editor_property(field, value)

        after_events = [e.export_text() for e in ANIM.get_animation_notify_events(asset)]
        old = Counter(before_events)
        now = Counter(after_events)
        assert all(now[k] >= v for k, v in old.items()), "Existing event modified: " + path
        assert len(after_events) == len(before_events) + 2, path
        assert asset.get_play_length() == before_settings["length"]
        assert asset.get_editor_property("enable_root_motion") == before_settings["root_motion"]
        LIB.set_metadata_tag(asset, "KZGrabWarningSource", row["source_package"] + "/xxHoldingAttackWarning")
        LIB.set_metadata_tag(asset, "KZGrabWarningPlan", "GiantGrabWarning_20261014/WarningPlan.json")
        assert LIB.save_loaded_asset(asset, only_if_is_dirty=False), path
        REPORT["sequences"].append({"asset": path, "file": str(file), "before_sha256": before_sha,
                                    "after_sha256": sha(file), "start": row["start"], "end": row["end"],
                                    "existing_events_preserved": True, "root_motion_preserved": True,
                                    "particle": PARTICLE.get_path_name(), "sound": SOUND.get_path_name(),
                                    "event_id": event_id})
    REPORT["success"] = True
except Exception:
    REPORT["errors"].append(traceback.format_exc())
    u.log_error(REPORT["errors"][-1])
finally:
    (OUT / "NotifyAuthorReport.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if not REPORT["success"]:
    raise RuntimeError("Grab warning authoring failed; see NotifyAuthorReport.json")
