"""Create and verify an external backup for Enemy assets affected by the cleanup."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import shutil


PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / "Saved/ImportReports"
EXTRACTED = PROJECT / "Saved/Extracted/EnemyAssetStructureCleanup_20260915"
PLAN = REPORTS / "EnemyAssetStructurePlan_20260915.json"
WORKSPACE_BASELINE = EXTRACTED / "WorkspaceBaseline.json"
BACKUP_REPORT = REPORTS / "EnemyAssetStructureBackup_20260915.json"
DESTINATION = pathlib.Path.home() / "Desktop/카잔/EnemyExtracts/EnemyAssetStructureCleanup_20260915"


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_copy(source: pathlib.Path, target: pathlib.Path, expected: str | None = None) -> str:
    value = sha256(source)
    if expected is not None:
        assert value == expected, ("Source changed before backup", source)
    if target.exists():
        assert target.is_file() and sha256(target) == value, ("Refusing to overwrite different backup", target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    assert sha256(target) == value
    return value


def main() -> None:
    plan = read(PLAN)
    workspace = read(WORKSPACE_BASELINE)
    assert plan["status"] == "planned" and plan["rename_count"] == 21
    assert workspace["status"] == "captured"
    assert not (DESTINATION / "BackupManifest.json").exists(), "Never replace a completed backup manifest"

    copied = []
    for row in plan["affected_assets"]:
        source = PROJECT / row["file"]
        assert source.is_file(), row["asset"]
        target = DESTINATION / "ProjectAssetsBefore" / row["file"]
        value = verified_copy(source, target, row["sha256"])
        copied.append(
            {
                "asset": row["asset"],
                "class": row["class"],
                "file": row["file"],
                "sha256": value,
                "bytes": source.stat().st_size,
                "change_roles": row["change_roles"],
            }
        )

    evidence = [
        PLAN,
        WORKSPACE_BASELINE,
        REPORTS / "EnemyAssetStructureInspection_20260915.json",
    ]
    evidence.extend(sorted((PROJECT / "Scripts/Enemies").glob("*enemy_asset_structure*.py")))
    evidence_rows = []
    for source in evidence:
        assert source.is_file(), source
        relative = source.relative_to(PROJECT).as_posix()
        target = DESTINATION / "EvidenceBefore" / relative
        value = verified_copy(source, target)
        evidence_rows.append({"file": relative, "sha256": value, "bytes": source.stat().st_size})

    result = {
        "status": "backed_up",
        "date": datetime.datetime.now().astimezone().isoformat(),
        "backup_root": str(DESTINATION),
        "structure_version": plan["structure_version"],
        "plan_sha256": sha256(PLAN),
        "workspace_baseline_sha256": sha256(WORKSPACE_BASELINE),
        "asset_count": len(copied),
        "asset_bytes": sum(row["bytes"] for row in copied),
        "assets": copied,
        "evidence": evidence_rows,
    }
    write(BACKUP_REPORT, result)
    write(DESTINATION / "BackupManifest.json", result)
    archive_hashes = []
    for path in sorted(value for value in DESTINATION.rglob("*") if value.is_file()):
        if path.name == "ArchiveSHA256.json":
            continue
        archive_hashes.append(
            {
                "file": path.relative_to(DESTINATION).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write(DESTINATION / "ArchiveSHA256.json", {"status": "verified", "files": archive_hashes})
    print(
        "ENEMY_ASSET_STRUCTURE_BACKUP_PASSED",
        json.dumps(
            {
                "assets": len(copied),
                "bytes": result["asset_bytes"],
                "evidence": len(evidence_rows),
                "destination": str(DESTINATION),
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
