"""Finalize only from saved main receipts and actual completed test reports."""
from pathlib import Path
import datetime
import hashlib
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def read(relative):
    return json.loads((BASE / relative).read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

audit = read("AuditFinal/Audit.json")
old_roots = read("AuditBefore02/RootAudit.json")
roots = read("AuditFinal/RootAudit.json")
main = read("FinalMain01/Driver.json")
alias = read("PursuitFinal/Driver.json")
rhi = read("FinalRHI01/Driver.json")
physics = read("Physics03/Driver.json")
author = read("Author02/Author.json")
assert audit["status"] == "passed" and old_roots["assets"] == roots["assets"]
for run in (main, alias, rhi):
    assert run["status"] == "passed" and all(row["passed"] for row in run["tests"])
assert all(row["passed"] for row in physics["tests"] if row["test"] != "Khazan.GiantCombatFeel.PIE")
guard = audit["guard"]
assert guard["parry_billboard_distortion"] == "/Game/VFX/03_SlashHit/KZ_Parring_Distort.KZ_Parring_Distort"
assert len(guard["brutal_effects"]) == 3
assert guard["parry_impact_effect"] is None and guard["parry_screen_distortion"] is None
manifest = json.loads((ROOT / "Binaries/Win64/UnrealEditor.modules").read_text(encoding="utf-8-sig"))
module = ROOT / "Binaries/Win64" / manifest["Modules"]["Khazan"]
assert str(module) == main["actual_module"] and sha(module) == main["module_sha256"]
for name in ("Build11.log", "Build12.log"):
    assert "Result: Succeeded" in (BASE / name).read_text(encoding="utf-16")
assets = []
for row in author["backups"]:
    current = sha(row["file"])
    assert current == row["after_sha256"], row["asset"]
    assets.append({"asset": row["asset"], "file": row["file"], "author02_sha256": row["after_sha256"], "current_sha256": current})
sources = []
for row in read("SourceBaseline.json"):
    current = sha(ROOT / row["Path"])
    sources.append({"path": row["Path"], "before_sha256": row["Sha256"].lower(), "current_sha256": current,
                    "changed_since_baseline": current != row["Sha256"].lower()})
for relative in ("Source/Khazan/Character/KZMonster.h", "Source/Khazan/Data/KZCharacterDefinitionData.h",
                 "Source/Khazan/Tests/KZGiantFallPIETest.cpp", "Source/Khazan/Tests/KZCombatPresentationPIETest.cpp"):
    sources.append({"path": relative, "current_sha256": sha(ROOT / relative), "before_sha256": None})
log = (BASE / "FinalMain01/Editor.log").read_text(encoding="utf-8", errors="replace")
events = [line for line in log.splitlines() if any(token in line for token in
          ("GIANT_FAR_PURSUIT ", "GIANT_LONG_CAPTURE ", "GIANT_FAR_ARMAGEDDON ", "GIANT_COMBAT_FEEL_COMPLETE "))]
reaction = read("Physics03/PIE.json")["cases"]
death = read("FinalRHI01/Native/Result.json")
report = {
    "status": "complete_main_verified", "generated_at_local": datetime.datetime.now().isoformat(),
    "project": str(ROOT), "remaining": [], "new_runtime_files": 0, "new_runtime_classes_or_managers": 0,
    "builds": {"standard": "Build11.log", "suffix": "Build12.log", "current_module": str(module),
               "current_module_sha256": sha(module), "manifest": str(ROOT / "Binaries/Win64/UnrealEditor.modules")},
    "assets": assets, "source_at_completion": sources,
    "runs": {"latest_main_ai_and_grabs": main, "suffix_ai_and_grabs": alias,
             "parry_and_lethal_brutal_rhi": rhi, "camera_root_groggy_earlier": physics},
    "run_scope_note": "Physics03 failed GiantCombatFeel is preserved and superseded by PursuitFinal/FinalMain01. Its camera/reaction successes remain valid. FinalRHI01 used Build09 before the final AI-only pursuit fix. All runs retain their own actual DLL hash; no result is relabelled as another module run.",
    "saved_readback": "AuditFinal/Audit.json", "root_read_only_audit": "AuditFinal/RootAudit.json",
    "root_assets_identical_to_before": len(roots["assets"]), "weak_point_runtime": reaction,
    "root_debugger_evidence": "RootRuntimeDebugBefore.json (actual Apes PartGroggy only)",
    "parry": {"niagara": guard["parry_billboard_distortion"], "brutal_contact_effects": guard["brutal_effects"],
              "alignment": "Actor XY midpoint, average live Bip001-Spine2 Z; original camera-facing renderers; no camera pull",
              "old_runtime_paths_removed": ["ParryImpactEffect", "ParryScreenDistortion volume", "floor-only plunge Niagara hookup"],
              "rhi_cases": 17, "shared_particle_assets_modified_by_this_task": False},
    "giant_runtime_events": events, "lethal_brutal_cases": len(death["paired_cases"]),
    "temporary_tunings": {
        "camera": {"owner": "KZCombatCameraModifier EditDefaultsOnly", "minimum_rise_seconds": .08,
                   "minimum_return_seconds": .16, "maximum_repetition_hz": 4,
                   "policy": "TEMP linear force and return; source amplitude/scale/distance windows preserved; alternating pulses. Existing variation .12, cross-axis .06, 90cm/2degree clamps retained."},
        "yetuga": {"owner": "BP_Monster_Yetuga AISettings", "chance": .3, "cooldown_seconds": 20,
                   "range_cm": [800, 5000], "provenance": "Range uses original BT058 split 800 and Armageddon BT037 maxDistance 5000. Chance/cooldown are assistant TEMP; source end cooldown 240 overridden only on requested ranged policy. Source HP ceiling bypassed only for configured ranged eligibility."},
        "combo": {"owner": "KZMonsterPatternAbility MinimumTransitionBlendSeconds", "minimum_seconds": .12,
                  "policy": "TEMP floor over zero/short source blends; longer source blends preserved; existing Slot inertialization reused."},
        "death": {"owner": "FKZMonsterStaminaSettings DeathTransitionBlendSeconds", "minimum_seconds": .24,
                  "policy": "TEMP minimum joining completed paired victim into the existing death montage."},
        "parry": {"owner": "KZGuardAbility / saved Guard BP", "requested_native_scale": 1,
                  "emission_stop_seconds": .5, "maximum_lifetime_seconds": 2.5,
                  "policy": "Emission/lifetime TEMP; Brutal PSC duration copied from original WindowEndTime minus WindowStartTime; native alpha drain preserved."}},
    "limits": ["Distant capture QA used a stationary player at 2000cm; moving-player evasion remains authored behavior.",
               "Forced 0/1 chance boundaries validate selection; saved .3 probability is not an empirical frequency measurement.",
               "Captures and runtime assertions do not certify original shader pixel identity or Shipping/network performance."],
    "failed_attempts_preserved": ["Build01/03/05 failures", "Build10 DLL lock failure", "PIE01", "PIE02",
                                  "Physics03 GiantCombatFeel failure", "PursuitTelemetry", "PursuitProbe/02 failed getters",
                                  "PursuitProbe03 pre-fix no-input evidence", "Niagara/Brutal layer diagnostics are not suite passes"]
}
(BASE / "FinalVerification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("complete_main_verified; sources", len(sources), "packages", len(assets), "unchanged root rows", len(roots["assets"]))
