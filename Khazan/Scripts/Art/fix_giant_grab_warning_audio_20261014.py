"""Move the warning sound to its source-aligned state Begin (frame-zero safe)."""
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
LIB, ANIM = u.EditorAssetLibrary, u.AnimationLibrary
PARTICLE = LIB.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
SOUND = LIB.load_asset("/Game/Audio/Original/Media/SW_UI_HoldingAttack")
TRACK = "GrabWarning"
R = {"success": False, "assets": [], "errors": []}


def values(asset):
    return list(ANIM.get_animation_notify_events(asset))


def own_notify(event):
    obj = event.get_editor_property("notify") or event.get_editor_property("notify_state_class")
    if isinstance(obj, u.KZAnimNotify_PlayAudio) and obj.get_editor_property("sound") == SOUND:
        return True
    return bool(isinstance(obj, u.KZAnimNotifyState_MonsterVisual) and obj.get_editor_property("effect")
                and obj.get_editor_property("effect").get_editor_property("ParticleTemplate") == PARTICLE)


try:
    for row in PLAN["windows"]:
        path = row["asset"]
        file = ROOT / "Content" / (path.removeprefix("/Game/") + ".uasset")
        assert file.resolve().is_relative_to((ROOT / "Content/_Art/Enemies").resolve())
        asset = LIB.load_asset(path)
        assert isinstance(asset, u.AnimSequence)
        assert LIB.get_metadata_tag(asset, "KZGrabWarningPlan") == "GiantGrabWarning_20261014/WarningPlan.json"
        current = values(asset)
        if any(isinstance(e.get_editor_property("notify_state_class"), u.KZAnimNotifyState_PlayAudio)
               and e.get_editor_property("notify_state_class").get_editor_property("playback")
               and e.get_editor_property("notify_state_class").get_editor_property("playback").get_editor_property("sound") == SOUND
               for e in current):
            assert sum(own_notify(e) for e in current) == 1, path
            assert not any(isinstance(e.get_editor_property("notify"), u.KZAnimNotify_PlayAudio)
                           and e.get_editor_property("notify").get_editor_property("sound") == SOUND for e in current), path
            R["assets"].append({"asset": path, "status": "already_state_audio", "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
            continue
        assert sum(own_notify(e) for e in current) == 2, path
        prior = Counter(e.export_text() for e in current if not own_notify(e))
        before = hashlib.sha256(file.read_bytes()).hexdigest()
        # A separate editor may have added unrelated notifies since the first
        # attempt. Keep each exact current version; never overwrite an earlier backup.
        backup = OUT / "BeforeAudioState" / before[:12] / file.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(file, backup)
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == before
        ANIM.remove_animation_notify_events_by_track(asset, TRACK)
        lingering_point = [e for e in values(asset) if isinstance(e.get_editor_property("notify"), u.KZAnimNotify_PlayAudio)
                           and e.get_editor_property("notify").get_editor_property("sound") == SOUND]
        if lingering_point:
            # UE's track removal leaves a point notify at source time zero on
            # these Apes sequences. Its authored name is unique to this task.
            assert len(lingering_point) == 1 and str(lingering_point[0].get_editor_property("notify_name")) == "KZPlayAudio", path
            assert sum(str(e.get_editor_property("notify_name")) == "KZPlayAudio" for e in values(asset)) == 1, path
            ANIM.remove_animation_notify_events_by_name(asset, "KZPlayAudio")
            assert not any(isinstance(e.get_editor_property("notify"), u.KZAnimNotify_PlayAudio)
                           and e.get_editor_property("notify").get_editor_property("sound") == SOUND for e in values(asset)), path
        visual_count = sum(bool(isinstance(e.get_editor_property("notify_state_class"), u.KZAnimNotifyState_MonsterVisual)
                                and e.get_editor_property("notify_state_class").get_editor_property("effect")
                                and e.get_editor_property("notify_state_class").get_editor_property("effect").get_editor_property("ParticleTemplate") == PARTICLE)
                           for e in values(asset))
        assert visual_count <= 1, (path, visual_count)
        if visual_count == 0:
            state = ANIM.add_animation_notify_state_event(asset, TRACK, row["start"], row["end"] - row["start"], u.KZAnimNotifyState_MonsterVisual)
            assert state
            effect = u.new_object(u.KZAnimNotify_CombatEffect, outer=state, name="OriginalGrabTelegraph")
            state.set_editor_property("effect", effect)
            event_id = "KZGrabWarning_" + hashlib.sha256(path.encode()).hexdigest()[:12]
            for field, value in (("ParticleTemplate", PARTICLE), ("EventId", event_id),
                                 ("SourceSocket", "UI_Chest"), ("bAttached", True),
                                 ("bUseWorldParticleUnits", True), ("bDestroyOnAnimEnd", True),
                                 ("WindowStartTime", row["start"]), ("WindowEndTime", row["end"])):
                effect.set_editor_property(field, value)
        audio_state = ANIM.add_animation_notify_state_event(asset, TRACK, row["start"], row["end"] - row["start"], u.KZAnimNotifyState_PlayAudio)
        assert audio_state
        playback = u.new_object(u.KZAnimNotify_PlayAudio, outer=audio_state, name="Playback")
        audio_state.set_editor_property("playback", playback)
        for field, value in (("sound", SOUND), ("source_package", PLAN["source_audio"]),
                             ("source_field", row["source_package"] + "/Notifies[" + str(row["source_notify_index"]) + "]"),
                             ("only_for_local_or_locked_target", False),
                             ("preserve_finite_tail_on_owner_destroyed", True)):
            playback.set_editor_property(field, value)
        after = values(asset)
        R["debug_first_after"] = [(str(e.get_editor_property("notify_name")),
                                    str((e.get_editor_property("notify") or e.get_editor_property("notify_state_class")).get_class().get_name())
                                    if (e.get_editor_property("notify") or e.get_editor_property("notify_state_class")) else None,
                                    own_notify(e)) for e in after]
        assert sum(own_notify(e) for e in after) == 1, "Visual missing or duplicate: " + path
        assert sum(isinstance(e.get_editor_property("notify_state_class"), u.KZAnimNotifyState_PlayAudio)
                   for e in after) >= 1
        assert Counter(e.export_text() for e in after if not own_notify(e) and
                       not isinstance(e.get_editor_property("notify_state_class"), u.KZAnimNotifyState_PlayAudio)) == prior
        assert LIB.save_loaded_asset(asset, only_if_is_dirty=False)
        R["assets"].append({"asset": path, "status": "audio_state_authored", "before_sha256": before,
                            "after_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                            "prior_notifies_preserved": True})
    R["success"] = True
except Exception:
    R["errors"].append(traceback.format_exc())
    u.log_error(R["errors"][-1])
finally:
    (OUT / "AudioStateFixReport.json").write_text(json.dumps(R, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if not R["success"]:
    raise RuntimeError("Grab audio state fix failed")
