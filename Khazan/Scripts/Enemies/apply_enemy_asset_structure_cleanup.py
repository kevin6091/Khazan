"""Apply the canonical Enemy asset-library folder cleanup inside Unreal Editor."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORTS = PROJECT / "Saved/ImportReports"
PLAN_PATH = REPORTS / "EnemyAssetStructurePlan_20260915.json"
BACKUP_PATH = REPORTS / "EnemyAssetStructureBackup_20260915.json"
EXECUTION_PATH = REPORTS / "EnemyAssetStructureExecution_20260915.json"
ROOT = "/Game/_Art/Enemies"
CONTENT_ROOT = (PROJECT / "Content/_Art/Enemies").resolve()
VERSION = "20260915_EnemyLibraryV2"
EAL = unreal.EditorAssetLibrary


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


def data_for(registry, package: str):
    return list(registry.get_assets_by_package_name(package, include_only_on_disk_assets=False) or [])


def asset_class(registry, package: str) -> str | None:
    rows = data_for(registry, package)
    return str(rows[0].asset_class_path.asset_name) if len(rows) == 1 else None


def remove_empty_directories() -> list[str]:
    removed = []
    while True:
        changed = False
        directories = sorted(
            (value for value in CONTENT_ROOT.rglob("*") if value.is_dir()),
            key=lambda value: len(value.parts),
            reverse=True,
        )
        for directory in directories:
            resolved = directory.resolve()
            assert resolved.is_relative_to(CONTENT_ROOT) and resolved != CONTENT_ROOT
            if any(directory.iterdir()):
                continue
            relative = directory.relative_to(CONTENT_ROOT).as_posix()
            directory.rmdir()
            removed.append(relative)
            changed = True
        if not changed:
            break
    return removed


def resave_referencer(registry, package: str) -> None:
    rows = data_for(registry, package)
    classes = {str(value.asset_class_path.asset_name) for value in rows}
    if "World" in classes:
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        assert levels.load_level(package), "Cannot load redirector referencer map: " + package
        assert levels.save_current_level(), "Cannot save redirector referencer map: " + package
        return
    asset = unreal.load_asset(package)
    assert asset is not None, "Cannot load redirector referencer: " + package
    assert EAL.save_loaded_asset(asset, only_if_is_dirty=False), "Cannot save redirector referencer: " + package


def verify_backup(plan: dict, backup: dict) -> None:
    assert plan["status"] == "planned" and plan["rename_count"] == 21
    assert plan["structure_version"] == VERSION
    assert backup["status"] == "backed_up"
    assert backup["plan_sha256"] == sha256(PLAN_PATH)
    assert backup["asset_count"] == plan["affected_asset_count"]
    backup_root = pathlib.Path(backup["backup_root"])
    backed_up = {row["asset"]: row for row in backup["assets"]}
    for row in plan["affected_assets"]:
        expected = backed_up[row["asset"]]
        copy = backup_root / "ProjectAssetsBefore" / row["file"]
        assert copy.is_file() and sha256(copy) == expected["sha256"] == row["sha256"], (
            "Backup mismatch",
            row["asset"],
        )


def verify_pristine_affected_assets(plan: dict) -> None:
    for row in plan["affected_assets"]:
        source = PROJECT / row["file"]
        assert source.is_file() and sha256(source) == row["sha256"], ("Pre-apply drift", row["asset"])


def main() -> None:
    plan = read(PLAN_PATH)
    backup = read(BACKUP_PATH)
    verify_backup(plan, backup)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    if not any(asset_class(registry, row["new_asset"]) is not None for row in plan["renames"]):
        verify_pristine_affected_assets(plan)
    options = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=True,
        include_soft_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=True,
        include_hard_management_references=True,
    )
    dirty = (
        unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    )
    assert not any(package.get_name().startswith(ROOT) for package in dirty), "Enemy packages must be clean"

    progress = {
        "status": "running",
        "date": datetime.datetime.now().astimezone().isoformat(),
        "structure_version": VERSION,
        "planned_renames": len(plan["renames"]),
        "renamed": 0,
        "metadata_saved": 0,
        "redirectors_deleted": 0,
        "redirector_files_unlinked": [],
        "redirector_referencers_resaved": [],
        "directories_removed": [],
        "error": None,
    }
    write(EXECUTION_PATH, progress)
    try:
        pending = []
        already_moved = 0
        for row in plan["renames"]:
            old_rows = data_for(registry, row["old_asset"])
            old_classes = {str(value.asset_class_path.asset_name) for value in old_rows}
            new_class = asset_class(registry, row["new_asset"])
            assert not row["external_referencers"]
            if new_class == row["class"] and (not old_rows or old_classes == {"ObjectRedirector"}):
                already_moved += 1
                continue
            assert old_classes == {row["class"]} and new_class is None, (
                row["old_asset"],
                sorted(old_classes),
                row["new_asset"],
                new_class,
            )
            source_file = PROJECT / next(
                value["file"] for value in plan["affected_assets"] if value["asset"] == row["old_asset"]
            )
            assert source_file.is_file() and sha256(source_file) == next(
                value["sha256"] for value in plan["affected_assets"] if value["asset"] == row["old_asset"]
            ), ("Pre-rename drift", row["old_asset"])
            asset = unreal.load_asset(row["old_asset"])
            assert asset is not None, row["old_asset"]
            rename = unreal.AssetRenameData()
            rename.set_editor_property("asset", asset)
            rename.set_editor_property("new_package_path", row["new_folder"])
            rename.set_editor_property("new_name", row["new_name"])
            pending.append(rename)
        if pending:
            assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets(pending), "Enemy rename batch failed"
        progress["renamed"] = already_moved + len(pending)
        write(EXECUTION_PATH, progress)
        registry.search_all_assets(True)

        for row in plan["renames"]:
            target = unreal.load_asset(row["new_asset"])
            assert target is not None and asset_class(registry, row["new_asset"]) == row["class"], row["new_asset"]
            EAL.set_metadata_tag(target, "PreviousEnemyAssetPath", row["old_asset"])
            EAL.set_metadata_tag(target, "CanonicalEnemyStructureVersion", VERSION)
            EAL.set_metadata_tag(target, "CanonicalEnemyAssetPath", row["new_asset"])
            if not EAL.save_loaded_asset(target, only_if_is_dirty=False):
                raise RuntimeError("Save failed " + row["new_asset"])
            progress["metadata_saved"] += 1
        write(EXECUTION_PATH, progress)
        registry.search_all_assets(True)

        redirectors = []
        for row in plan["renames"]:
            rows = data_for(registry, row["old_asset"])
            if not rows:
                continue
            assert all(str(value.asset_class_path.asset_name) == "ObjectRedirector" for value in rows), (
                row["old_asset"],
                rows,
            )
            referencers = sorted(str(value) for value in registry.get_referencers(row["old_asset"], options))
            for referencer in referencers:
                resave_referencer(registry, referencer)
                progress["redirector_referencers_resaved"].append(
                    {"redirector": row["old_asset"], "referencer": referencer}
                )
            if referencers:
                registry.search_all_assets(True)
            remaining = sorted(str(value) for value in registry.get_referencers(row["old_asset"], options))
            assert not remaining, ("Old redirector remains referenced after resave", row["old_asset"], remaining)
            objects = []
            seen = set()
            for value in rows:
                redirector = value.get_asset()
                assert redirector is not None and redirector.get_class().get_name() == "ObjectRedirector"
                path = redirector.get_path_name()
                if path not in seen:
                    seen.add(path)
                    objects.append(redirector)
            redirectors.append({"package": row["old_asset"], "objects": objects})
        for entry in redirectors:
            assert EAL.delete_loaded_assets(entry["objects"]), (
                "Redirector object deletion failed",
                entry["package"],
                [value.get_path_name() for value in entry["objects"]],
            )
            redirector_file = PROJECT / (entry["package"].replace("/Game/", "Content/") + ".uasset")
            resolved = redirector_file.resolve()
            assert resolved.is_relative_to(CONTENT_ROOT)
            if redirector_file.is_file():
                redirector_file.unlink()
                progress["redirector_files_unlinked"].append(entry["package"])
            progress["redirectors_deleted"] += 1
            write(EXECUTION_PATH, progress)
        registry.search_all_assets(True)

        for row in plan["renames"]:
            assert asset_class(registry, row["new_asset"]) == row["class"]
            old_file = PROJECT / (row["old_asset"].replace("/Game/", "Content/") + ".uasset")
            assert not old_file.exists(), row["old_asset"]
        progress["directories_removed"] = remove_empty_directories()

        current = registry.get_assets_by_path(ROOT, recursive=True, include_only_on_disk_assets=True)
        current_on_disk = []
        for value in current:
            package = str(value.package_name)
            cls = str(value.asset_class_path.asset_name)
            suffix = ".umap" if cls == "World" else ".uasset"
            disk = PROJECT / (package.replace("/Game/", "Content/") + suffix)
            if disk.is_file():
                current_on_disk.append(value)
        assert len(current_on_disk) == plan["asset_count_before"]
        assert not any(str(row.asset_class_path.asset_name) == "ObjectRedirector" for row in current_on_disk)
        dirty_after = (
            unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        )
        assert not any(package.get_name().startswith(ROOT) for package in dirty_after), [
            package.get_name() for package in dirty_after if package.get_name().startswith(ROOT)
        ]
        progress["status"] = "passed"
    except Exception:
        progress["status"] = "failed"
        progress["error"] = traceback.format_exc()
        raise
    finally:
        write(EXECUTION_PATH, progress)
    print(
        "ENEMY_ASSET_STRUCTURE_APPLY_PASSED",
        json.dumps(
            {
                "renamed": progress["renamed"],
                "metadata_saved": progress["metadata_saved"],
                "redirectors_deleted": progress["redirectors_deleted"],
                "redirector_files_unlinked": len(progress["redirector_files_unlinked"]),
                "redirector_referencers_resaved": len(progress["redirector_referencers_resaved"]),
                "directories_removed": len(progress["directories_removed"]),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
