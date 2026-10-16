"""Read-only Main recheck; preserve the 2026-10-14 authoring and PIE evidence."""
from pathlib import Path
import hashlib
import json
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261015"
OUT.mkdir(parents=True, exist_ok=True)
PRIOR = ROOT / "Metadata/GiantGrabWarning_20261014"
PLAN = json.loads((PRIOR / "WarningPlan.json").read_text(encoding="utf-8"))
REFERENCE = json.loads((PRIOR / "CameraFacingAuthorReport.json").read_text(encoding="utf-8"))
EXPECTED_HASHES = {row["asset"]: row["after_sha256"] for row in REFERENCE["assets"]}


def disk_path(asset):
    return ROOT / "Content" / (asset.removeprefix("/Game/") + ".uasset")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        if name.startswith("b_"):
            return obj.get_editor_property(name[2:])
        raise


TRACKED = [disk_path(row["asset"]) for row in PLAN["windows"]]
TRACKED += sorted((ROOT / "Content/_Art/Effects/Combat/GrabWarning").rglob("*.uasset"))
TRACKED += [ROOT / "Content/Audio/Original/Media/SW_UI_HoldingAttack.uasset",
            ROOT / "Content/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite.uasset",
            ROOT / "Content/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga.uasset"]
BEFORE = {str(path.relative_to(ROOT)): sha(path) for path in TRACKED}

# Execute the already-passed targeted verifier with a new report directory.
# Its original plan still comes from the immutable 2026-10-14 evidence.
ORIGINAL = ROOT / "Scripts/Art/verify_giant_grab_warning_saved_20261014.py"
code = ORIGINAL.read_text(encoding="utf-8")
old_out = 'OUT = ROOT / "Metadata/GiantGrabWarning_20261014"'
old_plan = 'PLAN = json.loads((OUT / "WarningPlan.json").read_text(encoding="utf-8"))'
assert code.count(old_out) == code.count(old_plan) == 1
code = code.replace(old_out, 'OUT = ROOT / "Metadata/GiantGrabWarning_20261015"')
code = code.replace(old_plan, 'PLAN = json.loads((PRIOR / "WarningPlan.json").read_text(encoding="utf-8"))')
exec(compile(code, str(ORIGINAL), "exec"), globals())

try:
    REPORT["project"] = str(ROOT)
    REPORT["asset_saves"] = 0
    REPORT["reference_asset_hashes_match"] = all(
        sha(disk_path(path)) == expected for path, expected in EXPECTED_HASHES.items())
    assert REPORT["reference_asset_hashes_match"]
    REPORT["particle_emitters"] = len(u.FXConverterUtilitiesLibrary.get_cascade_system_emitters(PS))
    assert REPORT["particle_emitters"] == 9
    REPORT["sound_duration_seconds"] = SOUND.get_editor_property("duration")
    assert REPORT["sound_duration_seconds"] > 0
    REPORT["capture_nodes"] = []
    for family, names in (("ApesStoneHandElite", ("Dodge_A_Step8", "Dodge_A_Step12", "Level_DashAtk_New_Step8", "Level_DashAtk_New_Step12")),
                          ("Yetuga", ("CloseGrab_Step1", "RushGrab_Step3", "RushGrab_Step5"))):
        definition = u.load_asset(f"/Game/Monsters/{family}/Data/DA_OriginalPatterns_{family}")
        assert definition
        for name in names:
            nodes = [node for node in get(definition, "nodes") if str(get(node, "node_id")) == name]
            assert len(nodes) == 1, name
            windows = list(get(nodes[0], "attack_windows"))
            assert windows and all(get(w, "b_begins_capture") and not get(w, "b_blockable") for w in windows), name
            REPORT["capture_nodes"].append({"family": family, "node": name, "windows": len(windows),
                                             "begins_capture": True, "blockable": False})
    camera_plan = json.loads((ROOT / "Metadata/GiantCamera_20261014/OriginalCameraEvents.json").read_text(encoding="utf-8"))
    REPORT["overlapping_camera_notifies"] = []
    for row in PLAN["windows"]:
        expected = {r["event_id"] for r in camera_plan["events"] if r["author_supported"] and r["current_asset"] == row["asset"]}
        if not expected:
            continue
        seq = u.load_asset(row["asset"])
        actual = set()
        for event in u.AnimationLibrary.get_animation_notify_events(seq):
            state = event.get_editor_property("notify_state_class")
            if isinstance(state, u.KZAnimNotifyState_MonsterVisual) and state.get_editor_property("bSourceCameraShake"):
                actual.add(str(state.get_editor_property("CameraEventId")))
        assert expected.issubset(actual), (row["asset"], sorted(expected - actual))
        REPORT["overlapping_camera_notifies"].append({"asset": row["asset"], "expected": len(expected),
                                                       "actual": len(actual), "missing": []})
    AFTER = {str(path.relative_to(ROOT)): sha(path) for path in TRACKED}
    assert AFTER == BEFORE, "Read-only verification changed an asset"
    REPORT["asset_hashes"] = AFTER
    REPORT["assets_unchanged_during_verification"] = True
    REPORT["source_sha256"] = {str(path.relative_to(ROOT)): sha(path) for path in (
        ROOT / "Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp",
        ROOT / "Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h",
        ROOT / "Source/Khazan/Ability/Combo/KZComboActionAbility.cpp")}
    REPORT["module"] = str(ROOT / "Binaries/Win64/UnrealEditor-Khazan.dll")
    REPORT["module_sha256"] = sha(Path(REPORT["module"]))
    REPORT["previous_rhi_evidence"] = "Metadata/GiantGrabWarning_20261014/PIE/RuntimeReport.json"
    REPORT["status"] = "passed"
except Exception:
    REPORT["status"] = "failed"
    REPORT["errors"].append(traceback.format_exc())
    u.log_error(REPORT["errors"][-1])
finally:
    (OUT / "SavedReadback.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if REPORT["status"] != "passed":
    raise RuntimeError("Main grab warning recheck failed")
