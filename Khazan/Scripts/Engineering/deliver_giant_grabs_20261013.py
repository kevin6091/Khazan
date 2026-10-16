"""CAS delivery of the eight verified, independently copied giant-grab assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

MAIN = Path(r"C:\Users\user\Desktop\GitProject\Khazan\Khazan").resolve()
WORK = Path(r"C:\Users\user\Desktop\GitProject\Khazan_GiantGrabsWork_20261013\Khazan").resolve()
OUT = MAIN / "Metadata/GiantGrabs_20261013"
BASELINE = json.loads((OUT / "WorkPreparation.json").read_text(encoding="utf-8"))["targets"]


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def target(root: Path, relative: str) -> Path:
    resolved = (root / relative).resolve()
    if root not in resolved.parents or resolved.suffix != ".uasset":
        raise RuntimeError(f"Unsafe asset path: {resolved}")
    return resolved


def main() -> None:
    apply = len(sys.argv) == 2 and sys.argv[1] == "--apply"
    if len(sys.argv) > 1 and not apply:
        raise SystemExit("Usage: deliver_giant_grabs_20261013.py [--apply]")
    assert json.loads((WORK / "Metadata/GiantGrabs_20261013/FreshReadback.json").read_text(encoding="utf-8"))["status"] == "passed"
    pie = json.loads((WORK / "Metadata/GiantGrabs_20261013/ExpandedPIEDriver.json").read_text(encoding="utf-8"))
    assert pie["status"] == "passed", "Complete owned Work PIE before delivery"
    report = {"status": "preflight", "apply": apply, "assets": []}
    for relative, expected in BASELINE.items():
        current = target(MAIN, relative)
        authored = target(WORK, relative)
        before = target(OUT / "BeforeAssets", relative)
        if digest(current) != expected:
            raise RuntimeError(f"Concurrent Main change: {relative}")
        if digest(before) != expected:
            raise RuntimeError(f"Baseline backup differs: {relative}")
        if authored.stat().st_nlink != 1:
            raise RuntimeError(f"Work asset still has shared hard links: {relative}")
        after_hash = digest(authored)
        if after_hash == expected:
            raise RuntimeError(f"Authored asset unchanged: {relative}")
        report["assets"].append({"path": relative, "before": expected, "after": after_hash})
    report["status"] = "ready"
    (OUT / "DeliveryPlan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not apply:
        return
    try:
        for item in report["assets"]:
            relative = item["path"]
            dest = target(MAIN, relative)
            src = target(WORK, relative)
            if digest(dest) != item["before"]:
                raise RuntimeError(f"Concurrent Main change during delivery: {relative}")
            staged = dest.with_name(dest.name + ".GiantGrabDelivery")
            shutil.copy2(src, staged)
            if digest(staged) != item["after"]:
                raise RuntimeError(f"Staged file mismatch: {relative}")
            os.replace(staged, dest)
            if digest(dest) != item["after"]:
                raise RuntimeError(f"Delivered file mismatch: {relative}")
            item["delivered"] = True
        report["status"] = "delivered"
    except Exception as error:
        report["status"] = "partial_failure"
        report["error"] = repr(error)
        raise
    finally:
        (OUT / "DeliveryResult.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
