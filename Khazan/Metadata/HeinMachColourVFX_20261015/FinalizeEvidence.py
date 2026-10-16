"""Check existing final receipts and write the task summary; no game writes."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import difflib
import hashlib
import json
from PIL import Image

R = Path(__file__).resolve().parent
ROOT = R.parents[1]


def read(relative):
    return json.loads((R / relative).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log_text(path):
    raw = path.read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig", errors="replace")


receipt = read("MainDelivery01/Receipt.json")
assert receipt["status"] == "delivered" and len(receipt["rows"]) == 105
for row in receipt["rows"]:
    assert sha(ROOT / row["file"]) == row["after_sha256"], row["file"]
saved = read("MainSaved01/SavedVerification.json")
assert saved["status"] == "passed" and saved["asset_saves"] == 0
assert len(saved["definitions"]) == 7 and len(saved["materials"]) == 95
hits = read("MainHitsHein01/Driver.json")
assert hits["status"] == "passed" and len(hits["tests"]) == 3
assert all(t["passed"] for t in hits["tests"])
assert hits["saved_packages"] == 0 and hits["material_compile_failures"] == []
assert "Result: Succeeded" in log_text(R / "MainCaptureBuild02/Output.log")

probes = []
for run, count in [("NativeAllDev01", 321), ("NativeAllHein01", 321),
                   ("RefractionOpaqueDev01", 6), ("RefractionOpaqueHein01", 6)]:
    probe = read(run + "/Probe.json")
    assert probe["status"] == "passed" and len(probe["rows"]) == count
    assert probe["asset_saves"] == 0 and read(run + "/Exit.json")["exit"] == 0
    sizes = set()
    for row in probe["rows"]:
        with Image.open(R / run / row["image"]) as picture:
            sizes.add(picture.size)
            picture.verify()
    errors = [line for line in log_text(R / run / "Editor.log").splitlines()
              if "Failed to compile Material" in line or "Default Material will be used in game" in line]
    assert not errors, errors[:2]
    probes.append(dict(run=run, map=probe["map"], images_verified=count,
                       actual_resolutions=sorted(sizes), exit=0, asset_saves=0,
                       shader_compile_fallback_failures=errors))

dev = read("NativeAllDev01/Probe.json")["rows"]
hein = read("NativeAllHein01/Probe.json")["rows"]
assert [x["asset"] for x in dev] == [x["asset"] for x in hein]
assert len({x["asset"] for x in dev}) == 321
comparison = read("NativeColourComparison/Comparison.json")
opaque = read("RefractionOpaqueComparison/Comparison.json")
assert comparison["paired_images"] == 321 and comparison["visible_in_both"] == 275
assert opaque["paired_images"] == 6 and opaque["review_flags"] == 0
flags = [{k: row[k] for k in ("asset", "signature_angle_deg", "energy_ratio")}
         for row in comparison["rows"] if row["review_flag"]]
assert len(flags) == 7

source = []
for relative in ["Source/Khazan/Character/KZCharacter.cpp",
                 "Source/Khazan/Tests/KZMonsterPresentationRepairPIETest.cpp"]:
    current, baseline = ROOT / relative, R / "Before" / relative
    delta = "".join(difflib.unified_diff(
        baseline.read_text(encoding="utf-8-sig").splitlines(True),
        current.read_text(encoding="utf-8-sig").splitlines(True),
        fromfile="task-before/" + relative, tofile="main/" + relative))
    patch = current.stem + "_TaskDiff.patch"
    (R / patch).write_text(delta, encoding="utf-8")
    source.append(dict(file=relative, sha256=sha(current),
                       baseline_sha256=sha(baseline), task_diff=patch))
module = ROOT / "Binaries/Win64/UnrealEditor-Khazan.dll"
manifest = json.loads((ROOT / "Binaries/Win64/UnrealEditor.modules").read_text(encoding="utf-8-sig"))
assert manifest["Modules"]["Khazan"] == module.name
now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
report = dict(
    status="complete_main_verified", time_kst=now, main_project=str(ROOT),
    delivered_package_count=105, delivered_packages_verified_now=receipt["rows"],
    asset_scope=dict(maps=2, character_definitions=7, current_surface_vfx_roots=95, blood_ground_material=1),
    delivery="MainDelivery01/Receipt.json", saved_readback="MainSaved01/SavedVerification.json",
    build=dict(report="MainCaptureBuild02/Output.log", result="Succeeded",
               current_canonical_module=str(module), current_module_sha256=sha(module)),
    runtime_tests=dict(report="MainHitsHein01/Driver.json", tests=hits["tests"],
                       actual_module_at_test=hits["actual_module"], module_sha256_at_test=hits["module_sha256"],
                       saved_packages=0, shader_compile_failures=[],
                       scope="Gameplay suites passed before the later DEV-only viewport screenshot command. Final command build and native captures passed. The two module hashes are distinct evidence."),
    source_changes=source, new_runtime_classes=0, native_probes=probes,
    current_catalog_delta="CurrentCatalogDelta.json",
    colour_comparison=dict(
        report="NativeColourComparison/Comparison.json", systems_in_each_map=321,
        visible_in_both_at_sample=275, requires_other_context_or_time=46,
        initial_review_flags=flags,
        review_resolution="Five low-angle energy flags show independent random size/spawn support. Two refraction systems sampled different opaque world backgrounds through the original translucent QA panel; same opaque QA backgrounds resolve that discrepancy without product changes.",
        refraction_retest="RefractionOpaqueComparison/Comparison.json", opaque_pairs=6,
        refraction_remaining_heuristic_flags=0,
        refraction_max_signature_angle_degrees=max(x["signature_angle_deg"] for x in opaque["rows"]),
        refraction_energy_ratio_range=[min(x["energy_ratio"] for x in opaque["rows"]), max(x["energy_ratio"] for x in opaque["rows"])]),
    scene=dict(capture="NativeHein05/Capture.json", quantitative_roi="SceneComparison.json",
               actors_before_after=[10009, 10009], actor_pose_changes=0,
               original_reference="Saved/ImportReports/HeinMachReference_20261006/OriginalReferences.jpg"),
    presentation_contract="Removed two map-specific Arcane Kuwahara blendable connections; colour grading/LUT disabled, LocalExposure identity; current Surface VFX vertex fog off and missing emissive exposure compensation added. Native film tonemapping, AA, physical lighting, depth and refraction remain.",
    blood_contract="Exact existing Brutal PP_Dmg_Blood_Trail_Sub on approved-hit feedback for Player and six monsters at receiver capsule surface. Particle modules/count/timing and existing decal scatter/lifetime preserved.",
    numerical_provenance="Light/fog/exposure and blood RGB/readability values are explicit TEMP art tuning, not original shader metadata. See Docs/Art/HEINMACH_COLOUR_VFX_20261015.md.",
    retained_diagnostics=[
        "Early Shot photos that captured the wrong editor viewport are superseded by the complete NativeAll ReadPixels captures.",
        "ActualHitsHein01 missed fixtures/reference setup. ActualHitsHein02 targeted tests passed, but seeded AI interrupted the broader historical CombatEffect montage review.",
        "ActualAttacksHein03 broader historical CombatEffect run hit its wall watchdog before completion and is not a full attack-suite pass. Targeted final Main tests above passed.",
        "Concurrent generated-header/DEV errors and later foreign hot-reload DLL locking caused early build failures; the final canonical build succeeded without stopping foreign editors."],
    limits=[
        "Original custom shader and same-camera/frame pixel parity are unverified; supplied photos guided TEMP art tuning.",
        "321-system screen test samples .2 game seconds. 46 require target/skeletal/user parameters, later bursts or another age; their appearance is not claimed verified by this one frame.",
        "Lit physical fragments and refraction intentionally respond to the world. Native HDR tonemapping is not universally bypassed.",
        "No Shipping FPS or whole-level performance benchmark was run.",
        "The broad historical CombatEffect montage suite was partial this session; notify/montage clocks and particle templates were unchanged."],
    process_policy="Only owned hidden/background editors used; foreign/Rider editors not stopped or controlled. Final probe exit receipts are zero; final OS inventory showed no UnrealEditor processes.",
    remaining=[])
(R / "FinalVerification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
state = dict(status="complete_main_verified", time_kst=now, final_verification="FinalVerification.json",
             main_assets_verified=105, remaining=[],
             resume=["Router then domain latest completion sections and FinalVerification.json.",
                     "Do not repeat author/delivery or restore old DLL, Source or whole work copy.",
                     "For new visual changes start from the current Main system/parameter/shot and repeat only relevant QA."],
             preserve="Keep concurrent edits and historical failed candidates; never control or stop foreign/Rider editors.")
(R / "ResumeState03.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(dict(status=report["status"], main_packages=105,
                      native_images_verified=sum(p["images_verified"] for p in probes),
                      tests_passed=len(hits["tests"]), canonical_module_sha256=sha(module),
                      refraction_max_angle_deg=report["colour_comparison"]["refraction_max_signature_angle_degrees"],
                      remaining=[])))
