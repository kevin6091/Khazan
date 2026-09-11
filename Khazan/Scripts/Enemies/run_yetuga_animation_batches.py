"""Run checkpointed Yetuga animation imports in isolated Editor processes."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
ENGINE = pathlib.Path("C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe")
ROWS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
BATCH_SIZE = 12
VERSION = "20260911_Yetuga_SourceCompositePlaybackV2_RootLockPropagation"


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(ROWS)
    reports = []
    for start in range(0, min(limit, len(ROWS)), BATCH_SIZE):
        count = min(BATCH_SIZE, len(ROWS) - start, limit - start)
        report_path = PROJECT / "Saved/ImportReports/YetugaAnimationBatches" / f"{start:04d}.json"
        prior = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        if (
            prior.get("status") == "passed"
            and prior.get("version") == VERSION
            and len(prior.get("assets", [])) == count
        ):
            reports.append(prior)
            continue
        log = PROJECT / "Saved/Logs" / f"YetugaAnimations_{start:04d}_20260911.log"
        stdout = log.with_suffix(".stdout.txt")
        args = [
            str(ENGINE),
            str(PROJECT / "Khazan.uproject"),
            "-run=pythonscript",
            "-script=" + str(PROJECT / "Scripts/Enemies/import_yetuga_animations.py"),
            f"-YetugaStart={start}",
            f"-YetugaCount={count}",
            "-unattended",
            "-nullrhi",
            "-nosound",
            "-nosplash",
            "-NoSourceControl",
            "-DisablePlugins=ModelContextProtocol",
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
        if process.returncode or data.get("status") != "passed" or len(data.get("assets", [])) != count:
            print("YETUGA_BATCH_FAILED", start, process.returncode, data.get("error"), flush=True)
            raise SystemExit(1)
        reports.append(data)
        print(
            "YETUGA_BATCH_PASSED",
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
                str(PROJECT / "Saved/ImportReports/YetugaAnimationBatches" / f"{report['start']:04d}.json")
                for report in reports
            ],
        }
        target = PROJECT / "Saved/ImportReports/Yetuga_AnimationImportAudit_20260911.json"
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()


