"""Run checkpointed DAS animation timing imports in isolated UE processes."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
ENGINE = pathlib.Path(
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
)
ROWS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
BATCH_SIZE = 50
VERSION = "20260917_DAS_CompositeExact60HzV5"


def editor_is_open() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "UnrealEditor.exe" in result.stdout


def main() -> None:
    if editor_is_open():
        raise SystemExit("UnrealEditor.exe is open; close it before the mutation batches")
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    requested = int(sys.argv[2]) if len(sys.argv) > 2 else len(ROWS) - first
    if first < 0 or requested < 0 or first > len(ROWS):
        raise SystemExit("Usage: run_das_animation_batches.py [start>=0] [count>=0]")
    end = min(first + requested, len(ROWS))
    reports = []
    for start in range(first, end, BATCH_SIZE):
        if editor_is_open():
            raise SystemExit("UnrealEditor.exe was opened during the mutation batches")
        count = min(BATCH_SIZE, end - start)
        report_path = PROJECT / "Saved/ImportReports/DASAnimationBatches" / f"{start:04d}.json"
        prior = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        if (
            prior.get("status") == "passed"
            and prior.get("version") == VERSION
            and len(prior.get("assets", [])) == count
        ):
            reports.append(prior)
            print("DAS_BATCH_REUSED", start, count, flush=True)
            continue
        log = PROJECT / "Saved/Logs" / f"DASAnimations_{start:04d}_20260917.log"
        stdout = log.with_suffix(".stdout.txt")
        args = [
            str(ENGINE),
            str(PROJECT / "Khazan.uproject"),
            "-run=pythonscript",
            "-script=" + str(PROJECT / "Scripts/Animation/import_das_animation_timing.py"),
            f"-DASStart={start}",
            f"-DASCount={count}",
            "-unattended",
            "-nullrhi",
            "-nosound",
            "-nosplash",
            "-NoSourceControl",
            "-DisablePlugins=ModelContextProtocol",
            "-EnablePlugins=GameFeatures",
            "-abslog=" + str(log),
        ]
        with stdout.open("w", encoding="utf-8") as output:
            process = subprocess.run(
                args,
                stdout=output,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        data = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        if (
            process.returncode
            or data.get("status") != "passed"
            or len(data.get("assets", [])) != count
        ):
            print(
                "DAS_BATCH_FAILED",
                start,
                process.returncode,
                data.get("error"),
                "stdout",
                stdout,
                flush=True,
            )
            raise SystemExit(1)
        reports.append(data)
        print(
            "DAS_BATCH_PASSED",
            start,
            count,
            "total",
            sum(len(report["assets"]) for report in reports),
            "/",
            len(ROWS),
            flush=True,
        )

    assets = [asset for report in reports for asset in report["assets"]]
    if len(assets) != end - first:
        raise RuntimeError("Batch aggregation is incomplete")
    if first == 0 and end == len(ROWS):
        result = {
            "status": "passed",
            "version": VERSION,
            "assets": len(assets),
            "source_timeline_assets": sum(
                asset["kind"] == "SourceTimelineReplacement" for asset in assets
            ),
            "unused_locomotion_assets": sum(
                asset["kind"] == "UnusedLocomotionReplacement" for asset in assets
            ),
            "composite_playback_assets": sum(
                asset["kind"] == "CompositePlayback" for asset in assets
            ),
            "dilation_bakes": sum(asset["dilation_applied"] for asset in assets),
            "root_motion_assets": sum(asset["root_motion"] for asset in assets),
            "player_root_motion_normalized_assets": sum(
                asset["root_motion"] and asset["skeleton"].endswith("/SK_Player")
                for asset in assets
            ),
            "skipped_already_current": sum(
                asset.get("skipped_already_current", False) for asset in assets
            ),
            "force_root_lock_assets": sum(asset["force_root_lock"] for asset in assets),
            "weapon_skeleton_assets": sum(
                asset["skeleton"].endswith("DualAxeSword_Imperial_R_Skeleton")
                for asset in assets
            ),
            "skeleton_corrections": sum(asset["skeleton_corrected"] for asset in assets),
            "maximum_duration_error_seconds": max(
                asset["duration_error_seconds"] for asset in assets
            ),
            "maximum_pose_errors": {
                "position_cm": max(asset["max_position_error_cm"] for asset in assets),
                "quaternion_component": max(
                    asset["max_quaternion_component_error"] for asset in assets
                ),
                "scale": max(asset["max_scale_error"] for asset in assets),
            },
            "maximum_topology_invariant_errors": {
                "position_cm": max(
                    asset["topology_component_pose_invariant_max_error"][0]
                    for asset in assets
                ),
                "quaternion_component": max(
                    asset["topology_component_pose_invariant_max_error"][1]
                    for asset in assets
                ),
                "scale": max(
                    asset["topology_component_pose_invariant_max_error"][2]
                    for asset in assets
                ),
            },
            "backup": reports[0]["backup"],
            "batch_reports": [
                str(
                    PROJECT
                    / "Saved/ImportReports/DASAnimationBatches"
                    / f"{report['start']:04d}.json"
                )
                for report in reports
            ],
        }
        target = (
            PROJECT
            / "Saved/ImportReports/Khazan_DAS_CompositeExact60PipelineImport_20260917.json"
        )
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
    else:
        result = {
            "status": "passed",
            "version": VERSION,
            "manifest_start": first,
            "manifest_end_exclusive": end,
            "assets": len(assets),
            "source_timeline_assets": sum(
                asset["kind"] == "SourceTimelineReplacement" for asset in assets
            ),
            "unused_locomotion_assets": sum(
                asset["kind"] == "UnusedLocomotionReplacement" for asset in assets
            ),
            "composite_playback_assets": sum(
                asset["kind"] == "CompositePlayback" for asset in assets
            ),
            "player_root_motion_normalized_assets": sum(
                asset["root_motion"] and asset["skeleton"].endswith("/SK_Player")
                for asset in assets
            ),
            "skipped_already_current": sum(
                asset.get("skipped_already_current", False) for asset in assets
            ),
            "maximum_duration_error_seconds": max(
                asset["duration_error_seconds"] for asset in assets
            ) if assets else 0.0,
            "maximum_pose_errors": {
                "position_cm": max(
                    (asset["max_position_error_cm"] for asset in assets), default=0.0
                ),
                "quaternion_component": max(
                    (asset["max_quaternion_component_error"] for asset in assets),
                    default=0.0,
                ),
                "scale": max(
                    (asset["max_scale_error"] for asset in assets), default=0.0
                ),
            },
            "batch_reports": [
                str(
                    PROJECT
                    / "Saved/ImportReports/DASAnimationBatches"
                    / f"{report['start']:04d}.json"
                )
                for report in reports
            ],
        }
        target = (
            PROJECT
            / "Saved/ImportReports/Khazan_DAS_CompositeExact60PipelinePartialImport_20260917.json"
        )
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
