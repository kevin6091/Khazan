"""Fresh-process readback of the seven saved original grab telegraph bindings."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014"
PLAN = json.loads((OUT / "WarningPlan.json").read_text(encoding="utf-8"))
PS = u.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
SOUND = u.load_asset("/Game/Audio/Original/Media/SW_UI_HoldingAttack")
REPORT = {"status": "running", "assets": [], "errors": []}

try:
    assert PS and SOUND
    for row in PLAN["windows"]:
        seq = u.EditorAssetLibrary.load_asset(row["asset"])
        assert isinstance(seq, u.AnimSequence), row["asset"]
        visual, audio, old_points = [], [], []
        for event in u.AnimationLibrary.get_animation_notify_events(seq):
            state = event.get_editor_property("notify_state_class")
            point = event.get_editor_property("notify")
            if isinstance(state, u.KZAnimNotifyState_MonsterVisual):
                effect = state.get_editor_property("effect")
                if effect and effect.get_editor_property("ParticleTemplate") == PS:
                    visual.append((event, effect))
            if isinstance(state, u.KZAnimNotifyState_PlayAudio):
                playback = state.get_editor_property("playback")
                if playback and playback.get_editor_property("sound") == SOUND:
                    audio.append((event, state))
            if isinstance(point, u.KZAnimNotify_PlayAudio) and point.get_editor_property("sound") == SOUND:
                old_points.append(event)
        assert len(visual) == len(audio) == 1 and not old_points, row["asset"]
        effect = visual[0][1]
        assert str(effect.get_editor_property("SourceSocket")) == "UI_Chest"
        assert effect.get_editor_property("bAttached")
        assert effect.get_editor_property("bUseWorldParticleUnits")
        assert effect.get_editor_property("bFaceCameraOutsideMeshBounds")
        assert effect.get_editor_property("OnNotifyEndDeattach")
        assert not audio[0][1].get_editor_property("bStopAtEnd")
        assert u.EditorAssetLibrary.get_metadata_tag(seq, "KZGrabWarningPlan") == "GiantGrabWarning_20261014/WarningPlan.json"
        REPORT["assets"].append({"asset": row["asset"], "particle": PS.get_path_name(),
                                 "sound": SOUND.get_path_name(), "socket": "UI_Chest",
                                 "visual_notify_count": len(visual), "audio_state_count": len(audio),
                                 "old_audio_point_count": len(old_points),
                                 "camera_facing_outside_mesh": True})
    assert len(REPORT["assets"]) == 7
    REPORT["status"] = "passed"
except Exception:
    REPORT["status"] = "failed"
    REPORT["errors"].append(traceback.format_exc())
    u.log_error(REPORT["errors"][-1])
finally:
    (OUT / "SavedReadback.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if REPORT["status"] != "passed":
    raise RuntimeError("Saved giant grab warning readback failed")
