"""Plan the 2026-09-15 Enemy asset-library folder cleanup.

This script is read-only. It consumes the fresh Unreal inspection report and
creates the exact rename set plus a worktree preservation baseline.
"""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import pathlib
import subprocess


PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPOSITORY = PROJECT.parent
REPORTS = PROJECT / "Saved/ImportReports"
EXTRACTED = PROJECT / "Saved/Extracted/EnemyAssetStructureCleanup_20260915"
INSPECTION = REPORTS / "EnemyAssetStructureInspection_20260915.json"
PLAN = REPORTS / "EnemyAssetStructurePlan_20260915.json"
WORKSPACE_BASELINE = EXTRACTED / "WorkspaceBaseline.json"
ROOT = "/Game/_Art/Enemies"
VERSION = "20260915_EnemyLibraryV2"


def move(old: str, new: str, group: str, reason: str) -> dict:
    return {"old_asset": ROOT + old, "new_asset": ROOT + new, "group": group, "reason": reason}


FIXED_MOVES = [
    move(
        "/HeinMach/Empire/Equipment/SK_EN_C_I_Empire_Q1Sword002",
        "/HeinMach/Shared/Equipment/SK_EN_C_I_Empire_Q1Sword002",
        "heinmach_shared_equipment",
        "The sword is shared by multiple HeinMach humanoid assemblies.",
    ),
    move(
        "/HeinMach/Empire/Equipment/SK_EN_C_I_SwordShield_Default001V2_L1",
        "/HeinMach/Shared/Equipment/SK_EN_C_I_SwordShield_Default001V2_L1",
        "heinmach_shared_equipment",
        "The sword-and-shield equipment is shared by multiple HeinMach humanoid assemblies.",
    ),
    move(
        "/HeinMach/Empire/Equipment/Skeletons/SKEL_EN_C_I_Empire_Q1Sword002",
        "/HeinMach/Shared/Equipment/Skeletons/SKEL_EN_C_I_Empire_Q1Sword002",
        "heinmach_shared_equipment",
        "Keep the equipment skeleton beside its canonical shared mesh.",
    ),
    move(
        "/HeinMach/Empire/Equipment/Skeletons/SKEL_EN_C_I_SwordShield_Default001V2_L1",
        "/HeinMach/Shared/Equipment/Skeletons/SKEL_EN_C_I_SwordShield_Default001V2_L1",
        "heinmach_shared_equipment",
        "Keep the equipment skeleton beside its canonical shared mesh.",
    ),
    move(
        "/HeinMach/Empire/Parts/PoseCarrier/SK_EN_C_M_Human_Adult_M_EmptyMesh",
        "/HeinMach/Shared/PoseCarriers/SK_EN_C_M_Human_Adult_M_EmptyMesh",
        "heinmach_shared_rig",
        "The pose carrier belongs to the common HeinMach humanoid rig.",
    ),
    move(
        "/HeinMach/Empire/Skeletons/SKEL_EN_EmpireHuman",
        "/HeinMach/Shared/Skeletons/SKEL_EN_EmpireHuman",
        "heinmach_shared_rig",
        "The skeleton is the common dependency for HeinMach humanoid assets.",
    ),
    move(
        "/HeinMach/HalberdElite/Equipment/SK_EN_C_I_Halberd_WeaponV2",
        "/HeinMach/Humanoids/HalberdElite/Equipment/SK_EN_C_I_Halberd_WeaponV2",
        "halberd_elite",
        "Merge the old top-level family into the canonical humanoid family.",
    ),
    move(
        "/HeinMach/HalberdElite/Equipment/Skeletons/SKEL_EN_C_I_Halberd_WeaponV2",
        "/HeinMach/Humanoids/HalberdElite/Equipment/Skeletons/SKEL_EN_C_I_Halberd_WeaponV2",
        "halberd_elite",
        "Merge the old top-level family into the canonical humanoid family.",
    ),
    move(
        "/HeinMach/HalberdElite/Meshes/SK_EN_C_M_HalberdV2",
        "/HeinMach/Humanoids/HalberdElite/Meshes/SK_EN_C_M_HalberdV2",
        "halberd_elite",
        "Merge the old top-level family into the canonical humanoid family.",
    ),
    move(
        "/HeinMach/HalberdElite/Meshes/Skeletons/SKEL_EN_C_M_HalberdV2",
        "/HeinMach/Humanoids/HalberdElite/Meshes/Skeletons/SKEL_EN_C_M_HalberdV2",
        "halberd_elite",
        "Merge the old top-level family into the canonical humanoid family.",
    ),
    move(
        "/OtherRegions/Humanoids/MageHard/Blueprints/BP_EN_MageHard_U01_L01",
        "/OtherRegions/Humanoids/Mage/Blueprints/BP_EN_MageHard_U01_L01",
        "mage_variants",
        "Keep normal and hard Mage variants in one family folder.",
    ),
    move(
        "/OtherRegions/Humanoids/MageHard/Meshes/SK_EN_MageHard_U01_L01",
        "/OtherRegions/Humanoids/Mage/Meshes/SK_EN_MageHard_U01_L01",
        "mage_variants",
        "Keep normal and hard Mage variants in one family folder.",
    ),
]


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


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=REPOSITORY).decode("utf-8", errors="replace")


def protected_worktree() -> list[dict]:
    task_prefixes = (
        "Khazan/Content/_Art/Enemies/",
        "Khazan/Docs/Art/",
        "Khazan/Scripts/Enemies/",
    )
    rows = []
    for line in git("status", "--porcelain=v1", "--untracked-files=all").splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        name = line[3:]
        if " -> " in name:
            name = name.rsplit(" -> ", 1)[1]
        if name.startswith(task_prefixes):
            continue
        disk = REPOSITORY / name
        rows.append(
            {
                "status": status,
                "file": name,
                "exists": disk.is_file(),
                "sha256": sha256(disk) if disk.is_file() else None,
            }
        )
    return sorted(rows, key=lambda row: row["file"])


def source_config_baseline() -> list[dict]:
    rows = []
    for base in (PROJECT / "Source", PROJECT / "Config"):
        for path in sorted(value for value in base.rglob("*") if value.is_file()):
            rows.append({"file": path.relative_to(PROJECT).as_posix(), "sha256": sha256(path)})
    return rows


def main() -> None:
    inspection = read(INSPECTION)
    assert inspection["status"] == "passed"
    assert inspection["asset_count"] == 1940
    assert not inspection["redirectors"] and not inspection["dirty_enemy_packages"]
    inventory = {row["asset"]: row for row in inspection["inventory"]}
    references = {row["asset"]: row for row in inspection["selected_reference_audit"]}

    shared_prefix = ROOT + "/HeinMach/Humanoids/Shared/Animations/Playback/"
    shared_moves = []
    for package in sorted(value for value in inventory if value.startswith(shared_prefix)):
        basename = package.rsplit("/", 1)[1]
        shared_moves.append(
            {
                "old_asset": package,
                "new_asset": ROOT + "/HeinMach/Shared/Animations/Playback/" + basename,
                "group": "heinmach_shared_animations",
                "reason": "Keep cross-archetype playback under the common HeinMach branch.",
            }
        )
    assert len(shared_moves) == 9
    moves = FIXED_MOVES + shared_moves
    assert len(moves) == 21
    assert len({row["old_asset"] for row in moves}) == len(moves)
    assert len({row["new_asset"] for row in moves}) == len(moves)

    affected = set()
    moved = {row["old_asset"] for row in moves}
    for row in moves:
        old = row["old_asset"]
        new = row["new_asset"]
        assert old in inventory, ("Missing source", old)
        assert new not in inventory, ("Occupied destination", new)
        reference = references[old]
        assert not reference["external_referencers"], (old, reference["external_referencers"])
        row["class"] = inventory[old]["class"]
        row["new_folder"] = new.rsplit("/", 1)[0]
        row["new_name"] = new.rsplit("/", 1)[1]
        row["enemy_referencers"] = reference["enemy_referencers"]
        row["external_referencers"] = reference["external_referencers"]
        affected.add(old)
        affected.update(reference["enemy_referencers"])
    assert affected <= set(inventory)

    affected_rows = []
    for package in sorted(affected):
        source = inventory[package]
        roles = []
        if package in moved:
            roles.append("renamed_asset")
        if any(package in row["enemy_referencers"] for row in moves):
            roles.append("reference_rewrite")
        affected_rows.append({**source, "change_roles": roles})

    rename_map = {row["old_asset"]: row["new_asset"] for row in moves}
    expected = []
    for package, row in sorted(inventory.items()):
        expected.append({"asset": rename_map.get(package, package), "class": row["class"]})
    assert len({row["asset"] for row in expected}) == len(inventory)

    counts_by_group = collections.Counter(row["group"] for row in moves)
    plan = {
        "status": "planned",
        "date": datetime.datetime.now().astimezone().isoformat(),
        "structure_version": VERSION,
        "root": ROOT,
        "inspection": INSPECTION.relative_to(PROJECT).as_posix(),
        "inspection_sha256": sha256(INSPECTION),
        "asset_count_before": len(inventory),
        "counts_by_class_before": inspection["counts_by_class"],
        "empty_leaf_directories_before": inspection["empty_directories"],
        "rename_count": len(moves),
        "rename_counts_by_group": dict(sorted(counts_by_group.items())),
        "renames": moves,
        "affected_asset_count": len(affected_rows),
        "affected_bytes_before": sum(row["bytes"] or 0 for row in affected_rows),
        "affected_assets": affected_rows,
        "expected_assets_after": sorted(expected, key=lambda row: row["asset"]),
        "obsolete_prefixes_after": [
            ROOT + "/HeinMach/Archive",
            ROOT + "/HeinMach/Empire",
            ROOT + "/HeinMach/HalberdElite",
            ROOT + "/HeinMach/Humanoids/Shared",
            ROOT + "/OtherRegions/Humanoids/MageHard",
        ],
        "obsolete_fragments_after": [
            "/_ImportStaging/",
            "/SourceSequences/",
            "/PlaybackClips/",
            "SourceReferences/",
        ],
        "preserved_history_files": [
            "Content/_Art/Enemies/HeinMach/Metadata/AnimationStructure_20260909/LegacyIdleDuplicates.json",
            "Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/LegacyAssetMoves.json",
        ],
    }
    workspace = {
        "status": "captured",
        "date": datetime.datetime.now().astimezone().isoformat(),
        "git_head": git("rev-parse", "HEAD").strip(),
        "protected_worktree": protected_worktree(),
        "source_config": source_config_baseline(),
    }
    write(PLAN, plan)
    write(WORKSPACE_BASELINE, workspace)
    print(
        "ENEMY_ASSET_STRUCTURE_PLAN_PASSED",
        json.dumps(
            {
                "renames": len(moves),
                "affected_assets": len(affected_rows),
                "affected_bytes": plan["affected_bytes_before"],
                "empty_leaf_directories": len(plan["empty_leaf_directories_before"]),
                "protected_worktree": len(workspace["protected_worktree"]),
                "source_config": len(workspace["source_config"]),
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
