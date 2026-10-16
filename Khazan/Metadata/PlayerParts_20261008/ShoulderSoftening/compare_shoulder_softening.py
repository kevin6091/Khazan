"""Offline native PIE comparison, including the first long-cloth simulated joint."""
import argparse
import csv
import importlib.util
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARSER = ROOT.parent / "LeftShoulderCloth" / "compare_shoulder_cloth.py"
spec = importlib.util.spec_from_file_location("shoulder_log_parser", PARSER)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.GROUPS = ("Whole8", "ShortPanel02_02", "LongCloth7", "LongProximal01_02")
IRON = ("B_Iron_01_01_R_Pelvis", "B_Iron_01_01_L_Pelvis")
LATE_PHASES = ("IdleLate", "AfterReleaseLate")


def surface_summary(run, part):
    stages = []
    for stage in (3, 4, 5):
        key = f"{part}:{stage}"
        probe, weights = run["surface"].get(key), run["surfaceWeights"].get(key)
        valid = bool(probe and probe.get("sampledVertices", 0) > 0
                     and probe.get("externalActors") == 18 and probe.get("finite") == 1)
        dominant_valid = bool(valid and weights and weights.get("dominantDirectSimVertices", 0) > 0
                              and "dominantDirectSimInsideVertices" in weights)
        stages.append(dict(stage=stage, valid=valid, dominantValid=dominant_valid,
                           probe=probe, dominant=weights))
    complete = all(s["valid"] for s in stages)
    dominant_complete = all(s["dominantValid"] for s in stages)
    return dict(threeStagesComplete=complete,
                sampledInsideZero=all(s["probe"]["insideVertices"] == 0 for s in stages) if complete else None,
                dominantThreeStagesComplete=dominant_complete,
                dominantInsideZero=all(s["dominant"]["dominantDirectSimInsideVertices"] == 0 for s in stages) if dominant_complete else None,
                stages=stages,
                scope="Linear LOD0 vertices against 18 anatomy proxies at stages 3/4/5; no continuous/all-pose skin collision claim.")


def profile_comparison(before_path, after_path):
    before, after = base.evidence(before_path), base.evidence(after_path)
    report = dict(available=bool(before and after), baselineFile=before, candidateFile=after)
    if report["available"]:
        a = json.loads(Path(before_path).read_text(encoding="utf-8-sig"))
        b = json.loads(Path(after_path).read_text(encoding="utf-8-sig"))
        report["reportSemanticDiff"] = base.semantic_diff(a, b)
        report["scope"] = "Exact JSON report leaf changes; includes audit metadata and does not imply an asset-only diff."
    return report


def waist_summary(path):
    report = dict(file=base.evidence(path), available=Path(path).is_file(), issues=[], bones={})
    if not report["available"]:
        report["issues"].append("Fresh CSV not copied yet.")
        return report
    fields = ("timeSeconds", "deltaSeconds", "meshJointStepDegrees", "meshJointSpeedDegreesPerSecond",
              "parentRelativePositionStepCm", "parentWorldStepDegrees", "actorJointStepDegrees",
              "actorAngularSpeedDegreesPerSecond", "activeContactPoints", "cachedMinSeparationCm", "accumulatedImpulse")
    groups = {}
    for line, row in enumerate(csv.DictReader(Path(path).read_text(encoding="utf-8-sig").splitlines()), 2):
        if row.get("phase") not in LATE_PHASES or row.get("hasPrevious") != "1":
            continue
        try:
            numbers = {f: float(row[f]) for f in fields}
            if not all(math.isfinite(v) for v in numbers.values()) or numbers["deltaSeconds"] <= 0:
                raise ValueError("Non-finite value or non-positive interval")
        except (KeyError, TypeError, ValueError) as exc:
            report["issues"].append(f"CSV line {line}: {exc}")
            continue
        groups.setdefault(row["phase"] + "|" + row["bone"], []).append((row, numbers))
    for key, rows in groups.items():
        def rms(field): return math.sqrt(sum(n[field] ** 2 for _, n in rows) / len(rows))
        steps = [n["meshJointStepDegrees"] for _, n in rows]
        report["bones"][key] = dict(samples=len(rows),
            stepMedianDegrees=statistics.median(steps), stepRmsDegrees=rms("meshJointStepDegrees"), stepPeakDegrees=max(steps),
            speedRmsDegreesPerSecond=rms("meshJointSpeedDegreesPerSecond"),
            speedPeakDegreesPerSecond=max(n["meshJointSpeedDegreesPerSecond"] for _, n in rows),
            positionStepRmsCm=rms("parentRelativePositionStepCm"), parentStepRmsDegrees=rms("parentWorldStepDegrees"),
            actorJointStepRmsDegrees=rms("actorJointStepDegrees"), actorAngularSpeedRmsDegreesPerSecond=rms("actorAngularSpeedDegreesPerSecond"),
            activeContactPointSamples=sum(n["activeContactPoints"] for _, n in rows),
            impulseSum=sum(n["accumulatedImpulse"] for _, n in rows),
            cachedMinimumGapCm=min(n["cachedMinSeparationCm"] for _, n in rows),
            meanDeltaSeconds=sum(n["deltaSeconds"] for _, n in rows)/len(rows),
            elapsedIntervalsSeconds=sum(n["deltaSeconds"] for _, n in rows),
            firstTimeSeconds=rows[0][1]["timeSeconds"], lastTimeSeconds=rows[-1][1]["timeSeconds"],
            actorValidFlags=sorted({r["actorValid"] for r, _ in rows}),
            actorEnabledFlags=sorted({r["actorEnabled"] for r, _ in rows}),
            actorCollisionFlags=sorted({r["actorHasCollision"] for r, _ in rows}))
    expected = [f"{phase}|{bone}" for phase in LATE_PHASES for bone in IRON]
    report["ironFourWindowsComplete"] = all(k in report["bones"] for k in expected) and not report["issues"]
    report["ironValidEnabledAndColliding"] = all(all(report["bones"].get(k, {}).get(f) == ["1"]
        for f in ("actorValidFlags", "actorEnabledFlags", "actorCollisionFlags")) for k in expected)
    report["scope"] = "Idle final 3s/release final 2s; first quaternion excluded. Parent-relative joint steps; cached manifold gap is not skin penetration. No jitter threshold added."
    return report


def waist_scope(run, csv_path):
    scopes = []
    if run["available"] and run["eventsComplete"]:
        lines = Path(run["file"]["path"]).read_text(encoding="utf-8-sig", errors="replace").splitlines()
        first, last = run["selectedLineRange"]
        scopes = [base.tokens(line) for line in lines[first-1:last] if "LogAutomationController: WaistJitterScope " in line]
    scope = scopes[0] if len(scopes) == 1 else {}
    return dict(records=scopes, selectedBlockMatchesCsv=bool(scope and
        Path(str(scope.get("csv", "")).replace("\\", "/")).name == Path(csv_path).name),
        savedWithNormalIronContact=scope.get("saved") == 1 and scope.get("noIronContactDiagnostic") == 0,
        expectedLateDurations=scope.get("idleLateSeconds") == 3 and scope.get("afterReleaseLateSeconds") == 2,
        caveat="Filename and selected native event scope bind this copied CSV; original log does not contain its content hash.")


def existing_native_checks(run):
    hair, cloth = run["hairMotion"] or {}, run["clothMotion"]
    return dict(completedSuccess=run["selectedResult"] == "Success" and run["eventsComplete"],
        hair65AndPeakUnder35=hair.get("independentlyRespondingJoints") == 65 and hair.get("bendPeakDegrees", math.inf) < 35,
        cloth={p: dict(expectedSimulatedCount=c, simulatedCountMatches=cloth.get(p, {}).get("directSimulatedBones") == c,
                       peakUnder45=cloth.get(p, {}).get("bendPeakDegrees", math.inf) < 45,
                       responsive=cloth.get(p, {}).get("independentlyRespondingJoints", 0) > 0) for p, c in (("Torso", 8), ("Leg", 30))},
        shoulderGroups={g: run["shoulder"].get(g, {}).get("observedJoints") == c and run["shoulder"].get(g, {}).get("samples", 0) > 0
                        for g, c in zip(base.GROUPS, (8, 1, 7, 1))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key, filename in (("baseline-log", "BaselineNative.log"), ("candidate-log", "CandidateNative.log"),
                          ("baseline-profile", "BaselineProfileAudit.json"), ("candidate-profile", "CandidateProfileAudit.json"),
                          ("baseline-csv", "PlayerWaistJitter_Baseline.csv"), ("candidate-csv", "PlayerWaistJitter_Candidate.csv"),
                          ("output", "NativeComparison.json")):
        parser.add_argument("--" + key, default=str(ROOT / filename))
    args = parser.parse_args()
    before, after = base.read_run(args.baseline_log), base.read_run(args.candidate_log)
    waist_before, waist_after = waist_summary(args.baseline_csv), waist_summary(args.candidate_csv)
    waist_before["nativeScope"] = waist_scope(before, args.baseline_csv)
    waist_after["nativeScope"] = waist_scope(after, args.candidate_csv)
    comparison = dict(
        shoulder={g: base.numeric_diff(before["shoulder"].get(g), after["shoulder"].get(g)) for g in base.GROUPS},
        clothMotion={p: base.numeric_diff(before["clothMotion"].get(p), after["clothMotion"].get(p)) for p in ("Torso", "Leg")},
        hairMotion=base.numeric_diff(before["hairMotion"], after["hairMotion"]),
        exactLoggedHairMetricsEqual=before["hairMotion"] == after["hairMotion"] if before["hairMotion"] and after["hairMotion"] else None,
        exactLoggedLegMetricsEqual=before["clothMotion"].get("Leg") == after["clothMotion"].get("Leg") if before["clothMotion"].get("Leg") and after["clothMotion"].get("Leg") else None,
        surface={p: {"baseline": surface_summary(before, p), "candidate": surface_summary(after, p)} for p in ("Torso", "Leg")},
        waist={k: base.numeric_diff(v, waist_after["bones"].get(k)) for k, v in waist_before["bones"].items()},
        waistSameObservedBoneWindows=bool(waist_before["bones"] and waist_before["bones"].keys() == waist_after["bones"].keys()))
    report = dict(generatedUtc=datetime.now(timezone.utc).isoformat(), parserFile=base.evidence(PARSER),
                  groups=list(base.GROUPS), baseline=before, candidate=after, comparison=comparison,
                  existingNativeChecks={"baseline": existing_native_checks(before), "candidate": existing_native_checks(after)},
                  waist={"baseline": waist_before, "candidate": waist_after},
                  profiles=profile_comparison(args.baseline_profile, args.candidate_profile),
                  screenshots={p.name: base.evidence(p) for p in sorted(ROOT.glob("*.png"))},
                  scope="Offline last native PIE result and following buffered event block; optional observations add no QA threshold or physics changes.")
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(output=str(Path(args.output).resolve()), baselineResult=before["selectedResult"],
                          candidateResult=after["selectedResult"], groups=list(base.GROUPS)), ensure_ascii=False))


if __name__ == "__main__":
    main()
