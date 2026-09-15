"""Run checkpointed ApesStoneHandElite animation imports in isolated Editor processes."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/ApesStoneHandElite_20260915"
ENGINE = pathlib.Path("C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe")
ROWS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
BATCH_SIZE = 12
VERSION = "20260915_ApesStoneHandElite_SourceCompositePlaybackV2_RootLockPropagation"


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(ROWS)
    reports = []
    for start in range(0, min(limit, len(ROWS)), BATCH_SIZE):
        count = min(BATCH_SIZE, len(ROWS) - start, limit - start)
        report_path = PROJECT / "Saved/ImportReports/ApesStoneHandEliteAnimationBatches" / f"{start:04d}.json"
        prior = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        if (
            prior.get("status") == "passed"
            and prior.get("process_exit_code") == 0
            and prior.get("version") == VERSION
            and len(prior.get("assets", [])) == count
        ):
            reports.append(prior)
            continue
        log = PROJECT / "Saved/Logs" / f"ApesStoneHandEliteAnimations_{start:04d}_20260915.log"
        stdout = log.with_suffix(".stdout.txt")
        args = [
            str(ENGINE),
            str(PROJECT / "Khazan.uproject"),
            "-run=pythonscript",
            "-script=" + str(PROJECT / "Scripts/Enemies/import_apes_stone_hand_animations.py"),
            f"-ApesStoneHandEliteStart={start}",
            f"-ApesStoneHandEliteCount={count}",
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
        data["process_exit_code"] = process.returncode
        report_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        if process.returncode or data.get("status") != "passed" or len(data.get("assets", [])) != count:
            print("APES_STONE_HAND_BATCH_FAILED", start, process.returncode, data.get("error"), flush=True)
            raise SystemExit(1)
        reports.append(data)
        print(
            "APES_STONE_HAND_BATCH_PASSED",
            start,
            count,
            "total",
            sum(len(report["assets"]) for report in reports),
            "/",
            len(ROWS),
            flush=True,
        )

    if limit >= len(ROWS):
        assets = [asset for report in reports for asset in report["assets"]]
        result = {
            "status": "passed",
            "version": VERSION,
            "assets": len(assets),
            "direct_original_timeline": sum(
                asset["derivation"] == "DirectOriginalTimeline" for asset in assets
            ),
            "composite_bakes": sum(asset["derivation"] == "CompositeBake" for asset in assets),
            "dilation_bakes": sum(asset["dilation_applied"] for asset in assets),
            "root_motion_assets": sum(asset["root_motion"] for asset in assets),
            "force_root_lock_assets": sum(asset["force_root_lock"] for asset in assets),
            "additive_assets": sum(bool(asset["additive_type"]) for asset in assets),
            "maximum_duration_error_seconds": max(asset["duration_error_seconds"] for asset in assets),
            "maximum_pose_errors": {
                "position_cm": max(asset["max_position_error_cm"] for asset in assets),
                "quaternion_component": max(asset["max_quaternion_component_error"] for asset in assets),
                "scale": max(asset["max_scale_error"] for asset in assets),
            },
            "batch_reports": [
                str(PROJECT / "Saved/ImportReports/ApesStoneHandEliteAnimationBatches" / f"{report['start']:04d}.json")
                for report in reports
            ],
        }
        target = PROJECT / "Saved/ImportReports/ApesStoneHandElite_AnimationImportAudit_20260915.json"
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
