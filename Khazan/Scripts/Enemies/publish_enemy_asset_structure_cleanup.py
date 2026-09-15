"""Publish the current Enemy structure index and archive final cleanup evidence."""

from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import io
import json
import pathlib
import shutil


PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / "Saved/ImportReports"
EXTRACTED = PROJECT / "Saved/Extracted/EnemyAssetStructureCleanup_20260915"
PLAN_PATH = REPORTS / "EnemyAssetStructurePlan_20260915.json"
BACKUP_PATH = REPORTS / "EnemyAssetStructureBackup_20260915.json"
EXECUTION_PATH = REPORTS / "EnemyAssetStructureExecution_20260915.json"
AUDIT_PATH = REPORTS / "EnemyAssetStructureAudit_20260915.json"
INSPECTION_PATH = REPORTS / "EnemyAssetStructureInspection_20260915.json"
WORKSPACE_PATH = EXTRACTED / "WorkspaceBaseline.json"
DESTINATION = PROJECT / "Content/_Art/Enemies/Metadata/Structure_20260915"
VERSION = "20260915_EnemyLibraryV2"


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_file(package: str, cls: str) -> pathlib.Path:
    suffix = ".umap" if cls == "World" else ".uasset"
    value = PROJECT / (package.replace("/Game/", "Content/") + suffix)
    assert value.resolve().is_relative_to((PROJECT / "Content/_Art/Enemies").resolve())
    return value


def family_for(package: str) -> str:
    parts = package.removeprefix("/Game/_Art/Enemies/").split("/")
    if parts[:2] == ["HeinMach", "Bosses"]:
        return "/".join(parts[:3])
    if parts[:2] == ["HeinMach", "Humanoids"]:
        return "/".join(parts[:3])
    if parts[:2] == ["HeinMach", "Shared"]:
        return "HeinMach/Shared"
    if parts[:2] == ["OtherRegions", "Humanoids"]:
        return "/".join(parts[:3])
    if parts[:2] == ["Shared", "Beasts"] or parts[:2] == ["Shared", "Elites"]:
        return "/".join(parts[:3])
    return "/".join(parts[:2])


def verified_copy(source: pathlib.Path, target: pathlib.Path) -> None:
    value = sha256(source)
    if not target.exists() or not target.is_file() or sha256(target) != value:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    assert sha256(target) == value


def main() -> None:
    plan = read(PLAN_PATH)
    backup = read(BACKUP_PATH)
    execution = read(EXECUTION_PATH)
    audit = read(AUDIT_PATH)
    inspection = read(INSPECTION_PATH)
    workspace = read(WORKSPACE_PATH)
    assert plan["status"] == "planned" and plan["structure_version"] == VERSION
    assert backup["status"] == "backed_up"
    assert execution["status"] == "passed"
    assert audit["status"] == "passed" and audit["asset_count"] == 1940
    assert inspection["status"] == "passed"

    current_assets = []
    for row in plan["expected_assets_after"]:
        disk = package_file(row["asset"], row["class"])
        assert disk.is_file(), row["asset"]
        current_assets.append(
            {
                "asset": row["asset"],
                "class": row["class"],
                "family": family_for(row["asset"]),
                "file": disk.relative_to(PROJECT).as_posix(),
                "bytes": disk.stat().st_size,
                "sha256": sha256(disk),
            }
        )
    current_assets.sort(key=lambda row: row["asset"])
    assert len(current_assets) == 1940

    folder_direct = collections.Counter(row["asset"].rsplit("/", 1)[0] for row in current_assets)
    family_counts = collections.Counter(row["family"] for row in current_assets)
    family_class_counts = collections.defaultdict(collections.Counter)
    for row in current_assets:
        family_class_counts[row["family"]][row["class"]] += 1
    folders = []
    for folder, direct_count in sorted(folder_direct.items()):
        prefix = folder + "/"
        folders.append(
            {
                "folder": folder,
                "direct_asset_count": direct_count,
                "recursive_asset_count": sum(1 for row in current_assets if row["asset"].startswith(prefix)),
            }
        )

    DESTINATION.mkdir(parents=True, exist_ok=True)
    rename_rows = [
        {
            "old_asset": row["old_asset"],
            "new_asset": row["new_asset"],
            "class": row["class"],
            "group": row["group"],
            "reason": row["reason"],
            "direct_enemy_referencers": len(row["enemy_referencers"]),
        }
        for row in plan["renames"]
    ]
    write_json(
        DESTINATION / "CurrentAssets.json",
        {
            "status": "current",
            "date": datetime.datetime.now().astimezone().isoformat(),
            "structure_version": VERSION,
            "asset_count": len(current_assets),
            "counts_by_class": audit["counts_by_class"],
            "assets": current_assets,
        },
    )
    write_json(
        DESTINATION / "RenameMap.json",
        {"structure_version": VERSION, "rename_count": len(rename_rows), "renames": rename_rows},
    )
    write_json(
        DESTINATION / "FolderStructure.json",
        {
            "structure_version": VERSION,
            "families": [
                {
                    "family": family,
                    "asset_count": family_counts[family],
                    "counts_by_class": dict(sorted(family_class_counts[family].items())),
                }
                for family in sorted(family_counts)
            ],
            "folders": folders,
        },
    )
    write_json(
        DESTINATION / "EmptyDirectoryCleanup.json",
        {
            "structure_version": VERSION,
            "empty_leaf_directories_before": plan["empty_leaf_directories_before"],
            "removed_directories": execution["directories_removed"],
            "empty_directories_after": audit["empty_directories"],
            "legacy_directories_after": audit["legacy_directories"],
            "preserved_history_files": plan["preserved_history_files"],
        },
    )
    write_json(
        DESTINATION / "ValidationSummary.json",
        {
            "status": audit["status"],
            "structure_version": VERSION,
            "asset_count": audit["asset_count"],
            "counts_by_class": audit["counts_by_class"],
            "renamed_assets": audit["renamed_assets"],
            "redirectors": audit["redirectors"],
            "unchanged_non_affected_enemy_hashes": audit["unchanged_non_affected_enemy_hashes"],
            "loaded_affected_assets": audit["loaded_affected_assets"],
            "semantic_contract_counts": audit["semantic_contract_counts"],
            "semantic_contract_errors": audit["semantic_contract_errors"],
            "maximum_numeric_contract_delta": audit["maximum_numeric_contract_delta"],
            "catalogue_actor_counts": audit["catalogue_actor_counts"],
            "scope": audit["scope"],
        },
    )
    write_json(
        DESTINATION / "WorkspacePreservation.json",
        {
            "structure_version": VERSION,
            "baseline_git_head": workspace["git_head"],
            "protected_worktree_at_start": workspace["protected_worktree"],
            "protected_worktree_drift_during_cleanup": audit["protected_worktree_drift"],
            "source_config_drift_during_cleanup": audit["source_config_drift"],
        },
    )

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["asset", "class", "family", "file", "bytes", "sha256"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(current_assets)
    (DESTINATION / "AssetLibrary.csv").write_text(output.getvalue(), encoding="utf-8-sig")
    (DESTINATION / "README.md").write_text(
        "# Enemy Asset Library Structure 2026-09-15\n\n"
        "`CurrentAssets.json` and `AssetLibrary.csv` are the canonical lookup for all current Enemy assets.\n"
        "`RenameMap.json` maps the 21 former package paths to their current paths.\n"
        "`FolderStructure.json` summarizes each gameplay family and asset class.\n"
        "`ValidationSummary.json` records the fresh Unreal audit.\n"
        "`EmptyDirectoryCleanup.json` records removed folders. Historical files whose names include "
        "Legacy or Archive remain as provenance records and are not runtime assets.\n",
        encoding="utf-8",
    )

    published = []
    for path in sorted(
        value for value in DESTINATION.iterdir()
        if value.is_file() and value.name != "PublishedFiles.json"
    ):
        published.append(
            {"file": path.relative_to(PROJECT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    write_json(
        DESTINATION / "PublishedFiles.json",
        {"status": "published", "structure_version": VERSION, "files": published},
    )

    archive_root = pathlib.Path(backup["backup_root"])
    final_evidence = [INSPECTION_PATH, PLAN_PATH, BACKUP_PATH, EXECUTION_PATH, AUDIT_PATH, WORKSPACE_PATH]
    final_evidence.extend(sorted((PROJECT / "Scripts/Enemies").glob("*enemy_asset_structure*.py")))
    final_evidence.extend(sorted(value for value in DESTINATION.iterdir() if value.is_file()))
    art_doc = PROJECT / "Docs/Art/ENEMY_ASSET_LIBRARY_STRUCTURE_2026-09-15.md"
    if art_doc.is_file():
        final_evidence.append(art_doc)
    for source in final_evidence:
        if source.is_relative_to(PROJECT):
            relative = source.relative_to(PROJECT)
        else:
            relative = pathlib.Path(source.name)
        verified_copy(source, archive_root / "EvidenceAfter" / relative)
    hashes = []
    for path in sorted(value for value in archive_root.rglob("*") if value.is_file()):
        if path.name == "ArchiveSHA256.json":
            continue
        hashes.append(
            {"file": path.relative_to(archive_root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    write_json(archive_root / "ArchiveSHA256.json", {"status": "verified", "files": hashes})
    print(
        "ENEMY_ASSET_STRUCTURE_PUBLISH_PASSED",
        json.dumps(
            {
                "assets": len(current_assets),
                "families": len(family_counts),
                "folders": len(folders),
                "published_files": len(published) + 1,
                "archive": str(archive_root),
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
