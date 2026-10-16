"""Read the latest completed PlayerParts.PIE block and positive-dt Iron samples.

Example: python native_motion.py Candidate
Optional --log/--csv paths select fresh saved-reload files explicitly.
QA angles/counts repeat the current native test and saved baseline contracts;
this report does not establish complete visual quality or zero penetration.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

TEST_PATH = "Khazan.PlayerParts.PIE"
IRON = ("B_Iron_01_01_R_Pelvis", "B_Iron_01_01_L_Pelvis")
PHASES = ("IdleLate", "AfterReleaseLate")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def fields(line):
    result = {}
    for key, value in re.findall(r"(\w+)=([^\s]+)", line):
        try:
            result[key] = int(value) if re.fullmatch(r"[-+]?\d+", value) else float(value)
        except ValueError:
            result[key] = value
    return result


def parse_native_log(path, label=None):
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    started = [i for i, line in enumerate(lines) if "Test Started." in line and f"Path={{{TEST_PATH}}}" in line]
    result = {"log": str(path), "logSha256": sha256(path), "issues": [], "assertionErrors": [], "hair": {}, "cloth": {}, "clothScope": {}}
    issues = result["issues"]
    if not started:
        issues.append("Missing PlayerParts.PIE start; no older event fallback permitted.")
        return result
    start = started[-1]
    completed = next((i for i in range(start + 1, len(lines)) if "Test Completed." in lines[i] and f"Path={{{TEST_PATH}}}" in lines[i]), None)
    begin = next((i for i in range(start + 1, len(lines)) if f"BeginEvents: {TEST_PATH}" in lines[i]), None)
    end = next((i for i in range((begin + 1) if begin is not None else len(lines), len(lines)) if f"EndEvents: {TEST_PATH}" in lines[i]), None)
    result["selectedBlock"] = {"startLine": start + 1, "completedLine": completed + 1 if completed is not None else None, "beginEventsLine": begin + 1 if begin is not None else None, "endEventsLine": end + 1 if end is not None else None, "start": lines[start]}
    if completed is None or begin is None or end is None:
        issues.append("Latest PIE is incomplete; no previous complete block was selected.")
        return result
    native_result = re.search(r"Result=\{([^}]+)\}", lines[completed])
    result["nativeResult"] = native_result.group(1) if native_result else None
    if result["nativeResult"] != "Success":
        issues.append("Latest native PIE did not return Success.")
    selected = lines[start:end + 1]
    result["assertionErrors"] = [line for line in selected if re.search(r"LogAutomationController:\s+(?:Error:|.*\bError:\s)", line)]
    if result["assertionErrors"]:
        issues.append("Latest native event block contains automation errors.")
    counts = {}
    for line in lines[begin + 1:end]:
        match = re.search(r"LogAutomationController:\s+(?:Display:\s+)?(HairMotion|ClothMotionScope|ClothMotion|WaistJitterScope)\s+", line)
        if not match:
            continue
        name, metric = match.group(1), fields(line[match.end():])
        key = (name, metric.get("part"))
        counts[key] = counts.get(key, 0) + 1
        if name == "HairMotion":
            result["hair"] = metric
        elif name == "ClothMotion":
            result["cloth"][metric.get("part")] = metric
        elif name == "ClothMotionScope":
            result["clothScope"][metric.get("part")] = metric
        else:
            result["waistScope"] = metric
        if any(isinstance(value, float) and not math.isfinite(value) for value in metric.values()):
            issues.append(f"Nonfinite {name} value.")
            for field, value in metric.items():
                if isinstance(value, float) and not math.isfinite(value):
                    metric[field] = None
    for name, part in (("HairMotion", None), ("ClothMotion", "Torso"), ("ClothMotion", "Leg"), ("ClothMotionScope", "Torso"), ("ClothMotionScope", "Leg"), ("WaistJitterScope", None)):
        if counts.get((name, part)) != 1:
            issues.append(f"Expected exactly one {name}/{part} in the selected block.")
    hair = result["hair"]
    peak = hair.get("bendPeakDegrees")
    if hair.get("independentlyRespondingJoints") != 65 or not isinstance(peak, (int, float)) or not 0 <= peak < 35:
        issues.append("Hair must report exactly 65 responding joints and peak below native 35-degree envelope.")
    for part, expected_joints in (("Torso", 8), ("Leg", 30)):
        metric, scope = result["cloth"].get(part, {}), result["clothScope"].get(part, {})
        peak = metric.get("bendPeakDegrees")
        if not isinstance(peak, (int, float)) or not 0 <= peak < 45:
            issues.append(f"{part} exceeds native 45-degree envelope or has no peak.")
        if metric.get("directSimulatedBones") != expected_joints or scope.get("observedJoints") != expected_joints or metric.get("independentlyRespondingJoints", 0) <= 0:
            issues.append(f"{part} saved-joint count/response differs from current baseline contract.")
        if scope.get("angular") != "SavedDirectSimulatedJointFrames":
            issues.append(f"{part} angular scope is not saved simulated joint frames.")
    waist = result.get("waistScope", {})
    if label is not None and waist.get("label") != label:
        issues.append(f"Waist label {waist.get('label')!r} does not match requested {label!r}.")
    if waist.get("saved") != 1 or waist.get("noIronContactDiagnostic") != 0:
        issues.append("Candidate CSV was not saved or collision-disable diagnostic is still active.")
    return result


def rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else None


def parse_iron_csv(path, cause, normal_delta=False, speed_reference=None):
    groups = {(phase, bone): [] for phase in PHASES for bone in IRON}
    issues = []
    excluded = {"zeroOrNegativeDt": 0, "noPreviousOrActor": 0}
    required = {"phase", "bone", "deltaSeconds", "hasPrevious", "actorValid", "actorEnabled", "actorHasCollision", "meshJointStepDegrees", "actorJointStepDegrees", "meshJointSpeedDegreesPerSecond", "activeContactPoints", "accumulatedImpulse"}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            return {"csv": str(path), "issues": ["Missing required native CSV columns."], "rows": []}
        for row in reader:
            key = (row["phase"], row["bone"])
            if key not in groups:
                continue
            numeric = {name: float(row[name]) for name in ("deltaSeconds", "meshJointStepDegrees", "actorJointStepDegrees", "meshJointSpeedDegreesPerSecond", "activeContactPoints", "accumulatedImpulse")}
            if not all(math.isfinite(value) for value in numeric.values()):
                issues.append(f"Nonfinite CSV sample {key}.")
                continue
            if numeric["deltaSeconds"] <= 0:
                excluded["zeroOrNegativeDt"] += 1
                continue
            if row["hasPrevious"] != "1" or row["actorValid"] != "1":
                excluded["noPreviousOrActor"] += 1
                continue
            groups[key].append((row, numeric))
    proof = {(row["phase"], row["bone"]): row for row in cause["rows"]}
    results = []
    for key, samples in groups.items():
        phase, bone = key
        reference = proof.get(key, {})
        steps = [sample[1]["meshJointStepDegrees"] for sample in samples]
        candidate = rms(steps)
        before = reference.get("baselineJointStepRmsDegrees")
        control = reference.get("contactIsolatedJointStepRmsDegrees")
        flags = sorted({sample[0]["actorHasCollision"] for sample in samples})
        enabled = sorted({sample[0]["actorEnabled"] for sample in samples})
        if not samples or (not normal_delta and len(samples) != reference.get("samples")):
            issues.append(f"{phase}/{bone}: missing positive-dt valid actor samples or fixed-time count differs from CauseProof.")
        if flags != ["1"] or enabled != ["1"]:
            issues.append(f"{phase}/{bone}: simulated actor must remain enabled with collision.")
        speed = rms([sample[1]["meshJointSpeedDegreesPerSecond"] for sample in samples])
        reference_speed = (speed_reference or {}).get(key, {})
        before_speed, control_speed = reference_speed.get("baseline"), reference_speed.get("control")
        if normal_delta and (before_speed is None or control_speed is None):
            issues.append(f"{phase}/{bone}: missing actual baseline/control speed reference for normal delta comparison.")
        metric, before_metric, control_metric = (speed, before_speed, control_speed) if normal_delta else (candidate, before, control)
        results.append({"phase": phase, "bone": bone, "samples": len(samples), "expectedFixedSamples": reference.get("samples") if not normal_delta else None, "meanObservedDeltaSeconds": sum(sample[1]["deltaSeconds"] for sample in samples) / len(samples) if samples else None, "candidateJointStepRmsDegrees": candidate, "candidateActorJointStepRmsDegrees": rms([sample[1]["actorJointStepDegrees"] for sample in samples]), "candidateJointSpeedRmsDegreesPerSecond": speed, "baselineJointSpeedRmsDegreesPerSecond": before_speed, "contactIsolatedJointSpeedRmsDegreesPerSecond": control_speed, "baselineJointStepRmsDegrees": before, "contactIsolatedJointStepRmsDegrees": control, "comparisonMetric": "JointSpeedRmsDegreesPerSecond" if normal_delta else "JointStepRmsDegrees", "reductionPercentVsCauseBaseline": 100 * (1 - metric / before_metric) if metric is not None and before_metric else None, "ratioVsContactIsolatedControl": metric / control_metric if metric is not None and control_metric else None, "improvedVsCauseBaseline": metric is not None and before_metric is not None and metric < before_metric, "activeContactSamples": sum(sample[1]["activeContactPoints"] for sample in samples), "contactImpulseSum": sum(sample[1]["accumulatedImpulse"] for sample in samples), "collisionFlags": flags, "enabledFlags": enabled})
    return {"csv": str(path), "csvSha256": sha256(path), "timeMode": "NormalVariableDelta" if normal_delta else "Fixed30", "sampleCountPolicy": "Positive valid samples required; counts are observed, not fixed" if normal_delta else "CauseProof fixed-time 90/60 sample counts", "positiveDtOnly": True, "initialPhysicsOffExcluded": True, "excludedLateSamples": excluded, "issues": issues, "rows": results, "allLateRowsImprovedVsCauseBaseline": all(row["improvedVsCauseBaseline"] for row in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--log", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--cause-proof", type=Path)
    parser.add_argument("--reference-comparison", type=Path, help="Baseline/NoIronContact actual speed RMS JSON; no inferred frame-rate conversion.")
    parser.add_argument("--normal-delta", action="store_true", help="Allow variable positive sample counts; compare speed per second instead of angle per frame. Native Hair/cloth envelopes remain unchanged.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    log = args.log or folder / f"{args.label}Native.log"
    csv_path = args.csv or folder / f"PlayerWaistJitter_{args.label}.csv"
    cause_path = args.cause_proof or folder / "CauseProof.json"
    comparison_path = args.reference_comparison or folder / "Comparison_Baseline_NoIronContact.json"
    report = {"label": args.label, "limitations": ["Native angle/count checks and limited positive-dt fixture samples; no complete visual or zero-penetration claim.", "Improvement against CauseProof is reported separately from native success; isolated control had collision disabled and is not an approved final configuration."]}
    if args.normal_delta:
        report["limitations"].append("Normal-delta comparisons use observed joint speed per elapsed second, not angle per frame. Fixed-reference versus variable-candidate sampling/timestep and concurrent source differences remain; reported percentages are descriptive, not a matched-timestep controlled improvement.")
    try:
        cause = json.loads(cause_path.read_text(encoding="utf-8-sig"))
        report["causeProof"] = {"path": str(cause_path), "sha256": sha256(cause_path), "limitations": cause.get("limitations", [])}
        speed_reference = {}
        if comparison_path.exists():
            comparison = json.loads(comparison_path.read_text(encoding="utf-8-sig"))["runs"]
            for phase in PHASES:
                for bone in IRON:
                    key = f"{phase}|{bone}"
                    speed_reference[(phase, bone)] = {"baseline": comparison["Baseline"]["bones"][key]["meshJointSpeedRmsDegreesPerSecond"], "control": comparison["NoIronContact"]["bones"][key]["meshJointSpeedRmsDegreesPerSecond"]}
            report["actualSpeedReference"] = {"path": str(comparison_path), "sha256": sha256(comparison_path), "sourceFields": "runs.Baseline/NoIronContact.bones.phase|bone.meshJointSpeedRmsDegreesPerSecond"}
        report["native"] = parse_native_log(log, args.label)
        report["iron"] = parse_iron_csv(csv_path, cause, args.normal_delta, speed_reference)
        report["nativeMotionChecksPassed"] = not report["native"]["issues"]
        report["lateSampleCollisionChecksPassed"] = not report["iron"]["issues"]
        report["ironJitterImprovedVsCauseBaseline"] = report["iron"]["allLateRowsImprovedVsCauseBaseline"]
        report["allChecksPassed"] = report["nativeMotionChecksPassed"] and report["lateSampleCollisionChecksPassed"] and report["ironJitterImprovedVsCauseBaseline"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        report["parserFailure"] = str(error)
        report["allChecksPassed"] = False
    output = args.output or folder / f"{args.label}MotionVerification.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "allChecksPassed": report["allChecksPassed"], "nativeIssues": report.get("native", {}).get("issues", []), "ironIssues": report.get("iron", {}).get("issues", []), "parserFailure": report.get("parserFailure")}, ensure_ascii=False))
    return 0 if report["allChecksPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
