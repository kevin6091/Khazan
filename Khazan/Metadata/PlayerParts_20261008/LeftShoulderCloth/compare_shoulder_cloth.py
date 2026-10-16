"""Offline comparison of the last completed native PlayerParts PIE event block."""
import argparse, hashlib, json, math, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
COMPLETE = re.compile(r"Test Completed\. Result=\{([^}]+)\}.*Path=\{Khazan\.PlayerParts\.PIE\}")
GROUPS = ("Whole8", "ShortPanel02_02", "LongCloth7")

def evidence(path):
    p = Path(path)
    return {"path": str(p.resolve()), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest().upper()} if p.is_file() else None

def tokens(line):
    out = {}
    for key, value in TOKEN.findall(line):
        try:
            numeric = float(value)
            out[key] = numeric if math.isfinite(numeric) else value
        except ValueError:
            out[key] = value
    return out

def read_run(path):
    run = dict(available=False, file=None, selectedResult="Missing", lastCompletedResult=None, eventsComplete=False,
               warnings=[], shoulder={}, clothMotion={}, hairMotion=None, surface={}, surfaceWeights={}, skippedSurface=[])
    if not Path(path).is_file():
        run["warnings"].append("Log not copied yet.")
        return run
    lines = Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    run.update(available=True, file=evidence(path))
    started, completed, result = -1, -1, None
    for i, line in enumerate(lines):
        if "Test Started." in line and "Path={Khazan.PlayerParts.PIE}" in line:
            started = i
        match = COMPLETE.search(line)
        if match:
            completed, result = i, match[1]
            run["lastCompletedResult"] = dict(result=result, line=i+1, raw=line)
    begin, end = -1, -1
    if started > completed:
        run["selectedResult"], begin = "Incomplete", started
        run["warnings"].append("Later PIE has no completed result; prior completed result is not current success.")
    elif completed >= 0:
        run["selectedResult"] = result
        # Completion precedes UE's buffered event records, so select the following matching block.
        for i in range(completed+1, len(lines)):
            if begin < 0 and lines[i].endswith("BeginEvents: Khazan.PlayerParts.PIE"):
                begin = i
            if begin >= 0 and lines[i].endswith("EndEvents: Khazan.PlayerParts.PIE"):
                end = i
                break
        if begin < 0:
            begin = completed
            run["warnings"].append("Completed result lacks buffered event block.")
    else:
        run["selectedResult"], begin = "NoCompletedPIE", max(0, started)
        run["warnings"].append("No completed native PlayerParts PIE found.")
    run["eventsComplete"] = end >= 0
    if end < 0:
        end = len(lines)-1
    run["selectedLineRange"] = [begin+1, end+1]
    for line in lines[begin:end+1]:
        if "LogAutomationController: ShoulderFlutterMetrics " in line:
            f = tokens(line); run["shoulder"][f["group"]] = f
        elif "LogAutomationController: ClothMotion part=" in line:
            f = tokens(line); run["clothMotion"][f["part"]] = f
        elif "LogAutomationController: HairMotion " in line:
            run["hairMotion"] = tokens(line)
        elif "LogAutomationController: ClothSurfaceProbe part=" in line:
            f = tokens(line); key = f'{f["part"]}:{int(f["stage"])}'; run["surface"][key] = f
            if f["sampledVertices"] <= 0 or f["externalActors"] <= 0 or f["finite"] != 1:
                run["warnings"].append(f"Invalid/empty surface sample {key}; zero inside does not prove clearance.")
        elif "LogAutomationController: ClothSurfaceWeights part=" in line:
            f = tokens(line); run["surfaceWeights"][f'{f["part"]}:{int(f["stage"])}'] = f
        elif "LogAutomationController: ClothSurfaceProbe skipped:" in line:
            run["skippedSurface"].append(line)
    for group in GROUPS:
        if run["shoulder"].get(group, {}).get("samples", 0) <= 0:
            run["warnings"].append(f"Missing/empty shoulder group {group}.")
    return run

def numeric_diff(before, after):
    before, after = before or {}, after or {}
    return [dict(field=k, baseline=v, candidate=after[k], delta=after[k]-v,
                 changePercent=100*(after[k]-v)/abs(v) if v else None)
            for k, v in before.items() if isinstance(v, (int, float)) and k in after and isinstance(after[k], (int, float))]

def surface_summary(run):
    stages = []
    for stage in (3, 4, 5):
        key = f"Torso:{stage}"; p = run["surface"].get(key)
        valid = bool(p and p["sampledVertices"] > 0 and p["externalActors"] == 18 and p["finite"] == 1)
        stages.append(dict(stage=stage, valid=valid, probe=p, dominant=run["surfaceWeights"].get(key)))
    complete = all(s["valid"] for s in stages)
    return dict(threeStagesComplete=complete,
                allSampledTorsoVerticesOutside=all(s["probe"]["insideVertices"] == 0 for s in stages) if complete else None,
                stages=stages, caveat="Sampled linear LOD0 vertices against 18 body proxies, not skin triangles/all poses/continuous collision.")

def flatten(value, prefix=""):
    if isinstance(value, dict):
        return {p: v for k, child in value.items() for p, v in flatten(child, f"{prefix}.{k}" if prefix else k).items()}
    if isinstance(value, list):
        return {p: v for i, child in enumerate(value) for p, v in flatten(child, f"{prefix}[{i}]").items()}
    return {prefix: value}

def semantic_diff(before, after):
    a, b = flatten(before), flatten(after)
    return [dict(path=k, baseline=a.get(k), candidate=b.get(k)) for k in sorted(a.keys() | b.keys())
            if k not in a or k not in b or a[k] != b[k]]

def profiles(before_path, after_path):
    report = dict(available=False, baselineFile=evidence(before_path), candidateFile=evidence(after_path),
                  joints=[], onlySlerpStiffnessChangedAcrossEightProfiles=None)
    if not report["baselineFile"] or not report["candidateFile"]:
        return report
    base = json.loads(Path(before_path).read_text(encoding="utf-8-sig"))
    candidate = json.loads(Path(after_path).read_text(encoding="utf-8-sig"))
    report.update(available=True, baselineSuccess=base["success"], candidateSuccess=candidate["success"],
                  candidateApplyRequested=candidate["apply_requested"], springScale=candidate["spring_scale"])
    only = base["success"] and candidate["success"] and len(base["joints"]) == len(candidate["joints"]) == 8
    for joint in base["joints"]:
        matches = [j for j in candidate["joints"] if j["bone"] == joint["bone"]]
        if len(matches) != 1:
            only = False; report["joints"].append(dict(bone=joint["bone"], error="Missing/duplicate candidate bone.")); continue
        next_joint = matches[0]
        diff = semantic_diff(joint["after_profile"], next_joint["after_profile"])
        saved_diff = semantic_diff(next_joint["after_profile"], next_joint["saved_default_profile"])
        expected = (len(diff) == 1 and diff[0]["path"].lower() == "angulardrive.slerpdrive.stiffness"
                    and next_joint["after_stiffness"] == next_joint["expected_adjusted_stiffness"]
                    and joint["parent"] == next_joint["parent"] and not saved_diff
                    and next_joint["full_constraint_matches_expected"])
        only = only and expected
        report["joints"].append(dict(bone=joint["bone"], parentUnchanged=joint["parent"] == next_joint["parent"],
            expectedOnly=expected, profileDiff=diff, candidateSavedDefaultDiff=saved_diff,
            nativeFullConstraintAssertionPassed=next_joint["full_constraint_matches_expected"],
            baselineStiffness=joint["after_stiffness"], candidateStiffness=next_joint["after_stiffness"],
            baselineDamping=joint["damping"], candidateDamping=next_joint["damping"]))
    report["onlySlerpStiffnessChangedAcrossEightProfiles"] = only
    report["scope"] = "Eight exported profiles and native full-constraint assertion, not all PA body/asset semantics."
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key, filename in (("baseline-log","BaselineNative.log"),("candidate-log","CandidateNative.log"),
                          ("baseline-profile","BaselineProfileAudit.json"),("candidate-profile","CandidateProfileAudit.json"),
                          ("output","NativeComparison.json")):
        parser.add_argument("--"+key, default=str(ROOT/filename))
    parser.add_argument("--baseline-screenshots", nargs="*", default=[])
    parser.add_argument("--candidate-screenshots", nargs="*", default=[])
    args = parser.parse_args()
    baseline, candidate = read_run(args.baseline_log), read_run(args.candidate_log)
    hair = numeric_diff(baseline["hairMotion"], candidate["hairMotion"])
    leg = numeric_diff(baseline["clothMotion"].get("Leg"), candidate["clothMotion"].get("Leg"))
    report = dict(generatedUtc=datetime.now(timezone.utc).isoformat(),
        scope="Offline last native PIE buffered event block; no editor/input/camera/physics changes.",
        baseline=baseline, candidate=candidate,
        comparison=dict(shoulder={g:numeric_diff(baseline["shoulder"].get(g),candidate["shoulder"].get(g)) for g in GROUPS},
            torso=numeric_diff(baseline["clothMotion"].get("Torso"),candidate["clothMotion"].get("Torso")), leg=leg, hair=hair,
            hairLoggedNumericValuesExactlyEqual=all(r["delta"] == 0 for r in hair) if hair else None,
            legLoggedNumericValuesExactlyEqual=all(r["delta"] == 0 for r in leg) if leg else None,
            caveat="Percentages use rounded logged values; zero baseline gives null percent. Moving-stage quaternion deltas exclude static sag. No automatic tiny-flutter threshold or full-asset invariance claim."),
        torsoSurface=dict(baseline=surface_summary(baseline), candidate=surface_summary(candidate)),
        profileComparison=profiles(args.baseline_profile,args.candidate_profile),
        screenshots=dict(baseline=[evidence(p) for p in (args.baseline_screenshots or sorted(ROOT.glob("Baseline*.png")))],
                         candidate=[evidence(p) for p in (args.candidate_screenshots or sorted(ROOT.glob("Candidate*.png")))],
                         visualReviewPerformedByScript=False))
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(report=str(Path(args.output).resolve()), baselineResult=baseline["selectedResult"],
        candidateResult=candidate["selectedResult"], baselineWarnings=len(baseline["warnings"]),
        candidateWarnings=len(candidate["warnings"]), profilesAvailable=report["profileComparison"]["available"])))

if __name__ == "__main__":
    main()

