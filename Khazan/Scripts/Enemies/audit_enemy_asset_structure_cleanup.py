"""Audit the Enemy asset-library cleanup in a fresh Unreal Editor process."""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPOSITORY = PROJECT.parent
REPORTS = PROJECT / "Saved/ImportReports"
EXTRACTED = PROJECT / "Saved/Extracted/EnemyAssetStructureCleanup_20260915"
INSPECTION_PATH = REPORTS / "EnemyAssetStructureInspection_20260915.json"
PLAN_PATH = REPORTS / "EnemyAssetStructurePlan_20260915.json"
BACKUP_PATH = REPORTS / "EnemyAssetStructureBackup_20260915.json"
EXECUTION_PATH = REPORTS / "EnemyAssetStructureExecution_20260915.json"
WORKSPACE_BASELINE_PATH = EXTRACTED / "WorkspaceBaseline.json"
AUDIT_PATH = REPORTS / "EnemyAssetStructureAudit_20260915.json"
ROOT = "/Game/_Art/Enemies"
CONTENT_ROOT = (PROJECT / "Content/_Art/Enemies").resolve()
VERSION = "20260915_EnemyLibraryV2"

sys.path.insert(0, str(PROJECT / "Scripts/Enemies"))
import inspect_enemy_asset_structure as contract_reader  # noqa: E402


CATALOGUES = [
    ROOT + "/HeinMach/Preview/L_HeinMach_EnemyCatalogue",
    ROOT + "/HeinMach/Bosses/Yetuga/Preview/L_EN_Yetuga_Catalogue",
    ROOT + "/Shared/Beasts/BigBear/Preview/L_EN_BigBear_Catalogue",
    ROOT + "/Shared/Beasts/WildDog/Preview/L_EN_WildDog_Catalogue",
    ROOT + "/Shared/Beasts/WildBoar/Preview/L_EN_WildBoar_Catalogue",
    ROOT + "/Shared/Elites/ApesStoneHandElite/Preview/L_EN_ApesStoneHandElite_Catalogue",
]


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(value) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_file(package: str, cls: str) -> pathlib.Path:
    suffix = ".umap" if cls == "World" else ".uasset"
    value = PROJECT / (package.replace("/Game/", "Content/") + suffix)
    assert value.resolve().is_relative_to(CONTENT_ROOT)
    return value


def recursively_remap(value, rename_map: dict[str, str]):
    if isinstance(value, str):
        return rename_map.get(value, value)
    if isinstance(value, list):
        return [recursively_remap(item, rename_map) for item in value]
    if isinstance(value, dict):
        return {key: recursively_remap(item, rename_map) for key, item in value.items()}
    return value


def compare_contract(expected, actual, path: str, errors: list[dict], maximum: list[float]) -> None:
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if expected != actual:
            errors.append({"path": path, "expected": expected, "actual": actual})
        return
    if isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)):
            errors.append({"path": path, "expected": expected, "actual": actual})
            return
        delta = abs(float(expected) - float(actual))
        maximum[0] = max(maximum[0], delta)
        tolerance = 1.0e-6 * max(1.0, abs(float(expected)))
        if delta > tolerance:
            errors.append({"path": path, "expected": expected, "actual": actual, "delta": delta})
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            errors.append({"path": path, "expected_length": len(expected), "actual": actual})
            return
        for index, item in enumerate(expected):
            compare_contract(item, actual[index], f"{path}[{index}]", errors, maximum)
        return
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            errors.append(
                {
                    "path": path,
                    "expected_keys": sorted(expected),
                    "actual_keys": sorted(actual) if isinstance(actual, dict) else actual,
                }
            )
            return
        for key in sorted(expected):
            compare_contract(expected[key], actual[key], f"{path}.{key}", errors, maximum)
        return
    if expected != actual:
        errors.append({"path": path, "expected": expected, "actual": actual})


def contract_index(rows: list[dict]) -> dict[str, dict]:
    return {row["asset"]: row for row in rows}


def current_contracts(assets: dict[str, object]) -> dict[str, list[dict]]:
    mesh_editor = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    return {
        "animation_contracts": [
            contract_reader.animation_contract(package)
            for package, data in sorted(assets.items())
            if str(data.asset_class_path.asset_name) == "AnimSequence"
        ],
        "skeletal_mesh_contracts": [
            contract_reader.mesh_contract(package, mesh_editor)
            for package, data in sorted(assets.items())
            if str(data.asset_class_path.asset_name) == "SkeletalMesh"
        ],
        "blueprint_contracts": [
            contract_reader.blueprint_contract(package, subobjects, library)
            for package, data in sorted(assets.items())
            if str(data.asset_class_path.asset_name) == "Blueprint"
        ],
    }


def filesystem_diagnostics() -> tuple[list[str], list[str]]:
    directories = sorted(value for value in CONTENT_ROOT.rglob("*") if value.is_dir())
    empty = [value.relative_to(CONTENT_ROOT).as_posix() for value in directories if not any(value.iterdir())]
    legacy = []
    fragments = ("_ImportStaging", "SourceSequences", "PlaybackClips", "SourceReferences", "Archive")
    for directory in directories:
        relative = directory.relative_to(CONTENT_ROOT).as_posix()
        if any(fragment in relative for fragment in fragments):
            legacy.append(relative)
    return empty, legacy


def workspace_drift(workspace: dict) -> tuple[list[dict], list[dict]]:
    protected = []
    for row in workspace["protected_worktree"]:
        path = REPOSITORY / row["file"]
        current = sha256(path) if path.is_file() else None
        if current != row["sha256"]:
            protected.append({"file": row["file"], "before": row["sha256"], "after": current})
    source_config = []
    for row in workspace["source_config"]:
        path = PROJECT / row["file"]
        current = sha256(path) if path.is_file() else None
        if current != row["sha256"]:
            source_config.append({"file": row["file"], "before": row["sha256"], "after": current})
    return protected, source_config


def main() -> None:
    result = {"status": "running", "structure_version": VERSION, "error": None}
    write(result)
    try:
        inspection = read(INSPECTION_PATH)
        plan = read(PLAN_PATH)
        backup = read(BACKUP_PATH)
        execution = read(EXECUTION_PATH)
        workspace = read(WORKSPACE_BASELINE_PATH)
        assert inspection["status"] == "passed"
        assert plan["status"] == "planned" and plan["structure_version"] == VERSION
        assert backup["status"] == "backed_up" and backup["plan_sha256"] == sha256(PLAN_PATH)
        assert execution["status"] == "passed" and execution["renamed"] == 21

        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.search_all_assets(True)
        options = unreal.AssetRegistryDependencyOptions(
            include_hard_package_references=True,
            include_soft_package_references=True,
            include_searchable_names=False,
            include_soft_management_references=True,
            include_hard_management_references=True,
        )
        assets = {
            str(data.package_name): data
            for data in registry.get_assets_by_path(ROOT, recursive=True, include_only_on_disk_assets=True)
        }
        dirty_at_start = (
            unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        )
        dirty_enemy_at_start = sorted(
            package.get_name() for package in dirty_at_start if package.get_name().startswith(ROOT)
        )
        assert not dirty_enemy_at_start, dirty_enemy_at_start
        expected = {row["asset"]: row["class"] for row in plan["expected_assets_after"]}
        current = {package: str(data.asset_class_path.asset_name) for package, data in assets.items()}
        assert current == expected, {
            "missing": sorted(set(expected) - set(current))[:20],
            "unexpected": sorted(set(current) - set(expected))[:20],
            "class_mismatch": sorted(
                package for package in set(current) & set(expected) if current[package] != expected[package]
            )[:20],
        }
        assert len(assets) == inspection["asset_count"] == 1940
        redirectors = sorted(
            package for package, data in assets.items()
            if str(data.asset_class_path.asset_name) == "ObjectRedirector"
        )
        assert not redirectors

        rename_map = {row["old_asset"]: row["new_asset"] for row in plan["renames"]}
        for row in plan["renames"]:
            assert row["old_asset"] not in assets
            target = unreal.load_asset(row["new_asset"])
            assert target is not None
            assert unreal.EditorAssetLibrary.get_metadata_tag(target, "PreviousEnemyAssetPath") == row["old_asset"]
            assert unreal.EditorAssetLibrary.get_metadata_tag(target, "CanonicalEnemyStructureVersion") == VERSION
            assert unreal.EditorAssetLibrary.get_metadata_tag(target, "CanonicalEnemyAssetPath") == row["new_asset"]

        empty_directories, legacy_directories = filesystem_diagnostics()
        assert not empty_directories, empty_directories
        assert not legacy_directories, legacy_directories
        assert not any(
            package.startswith(tuple(plan["obsolete_prefixes_after"]))
            or any(fragment in package + "/" for fragment in plan["obsolete_fragments_after"])
            for package in assets
        )
        for name in plan["preserved_history_files"]:
            assert (PROJECT / name).is_file(), name

        affected_before = {row["asset"] for row in plan["affected_assets"]}
        unchanged_hashes = 0
        for row in inspection["inventory"]:
            if row["asset"] in affected_before:
                continue
            disk = PROJECT / row["file"]
            assert disk.is_file() and sha256(disk) == row["sha256"], ("Unrelated Enemy asset changed", row["asset"])
            unchanged_hashes += 1

        contracts = current_contracts(assets)
        contract_errors = []
        maximum_numeric_delta = [0.0]
        contract_counts = {}
        for key in ("animation_contracts", "skeletal_mesh_contracts", "blueprint_contracts"):
            before = contract_index([recursively_remap(row, rename_map) for row in inspection[key]])
            after = contract_index(contracts[key])
            assert set(before) == set(after), (key, sorted(set(before) - set(after)), sorted(set(after) - set(before)))
            for package in sorted(before):
                compare_contract(before[package], after[package], f"{key}:{package}", contract_errors, maximum_numeric_delta)
            contract_counts[key] = len(after)
        assert not contract_errors, contract_errors[:20]

        loaded_affected = 0
        for old in sorted(affected_before):
            package = rename_map.get(old, old)
            assert unreal.load_asset(package) is not None, package
            loaded_affected += 1

        missing_dependencies = []
        for package in sorted(assets):
            for dependency in registry.get_dependencies(package, options):
                value = str(dependency)
                if value.startswith(ROOT + "/") and value not in assets:
                    missing_dependencies.append({"asset": package, "dependency": value})
        assert not missing_dependencies, missing_dependencies[:20]

        animations = sorted(
            package for package, data in assets.items()
            if str(data.asset_class_path.asset_name) == "AnimSequence"
        )
        assert len(animations) == 1354
        assert all(package.rsplit("/", 1)[1].startswith("A_EN_PLAY_") for package in animations)
        assert all("/Animations/Playback/" in package for package in animations)

        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        catalogue_counts = {}
        for package in CATALOGUES:
            assert levels.load_level(package), package
            count = len(actors.get_all_level_actors())
            assert count > 0, package
            catalogue_counts[package] = count

        dirty = (
            unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        )
        post_load_dirty_enemy = sorted(package.get_name() for package in dirty if package.get_name().startswith(ROOT))
        protected_drift, source_config_drift = workspace_drift(workspace)
        counts_by_class = dict(
            sorted(collections.Counter(str(data.asset_class_path.asset_name) for data in assets.values()).items())
        )
        assert counts_by_class == inspection["counts_by_class"]
        result = {
            "status": "passed",
            "structure_version": VERSION,
            "asset_count": len(assets),
            "counts_by_class": counts_by_class,
            "renamed_assets": len(plan["renames"]),
            "redirectors": redirectors,
            "empty_directories": empty_directories,
            "legacy_directories": legacy_directories,
            "unchanged_non_affected_enemy_hashes": unchanged_hashes,
            "loaded_affected_assets": loaded_affected,
            "missing_enemy_dependencies": missing_dependencies,
            "semantic_contract_counts": contract_counts,
            "semantic_contract_errors": contract_errors,
            "maximum_numeric_contract_delta": maximum_numeric_delta[0],
            "animation_naming_and_folder_contract": {
                "count": len(animations),
                "name_prefix": "A_EN_PLAY_",
                "folder_fragment": "/Animations/Playback/",
            },
            "catalogue_actor_counts": catalogue_counts,
            "dirty_enemy_packages_at_audit_start": dirty_enemy_at_start,
            "transient_post_load_dirty_enemy_count": len(post_load_dirty_enemy),
            "transient_post_load_dirty_enemy_sample": post_load_dirty_enemy[:20],
            "protected_worktree_drift": protected_drift,
            "source_config_drift": source_config_drift,
            "scope": (
                "Fresh Asset Registry, exact inventory/classes, SHA-256 for every unaffected Enemy package, "
                "all animation timing/root settings, all skeletal mesh skeleton/LOD/material-slot contracts, "
                "all Blueprint skeletal-component contracts, affected-asset loading, internal dependencies, "
                "redirectors, empty/obsolete directories, and six catalogue maps. PostLoad-only dirty packages "
                "are recorded but never saved by this read-only audit."
            ),
        }
        write(result)
    except Exception:
        result["status"] = "failed"
        result["error"] = traceback.format_exc()
        write(result)
        raise
    print(
        "ENEMY_ASSET_STRUCTURE_AUDIT_PASSED",
        json.dumps(
            {
                "assets": result["asset_count"],
                "renamed": result["renamed_assets"],
                "unaffected_hashes": result["unchanged_non_affected_enemy_hashes"],
                "animations": result["semantic_contract_counts"]["animation_contracts"],
                "meshes": result["semantic_contract_counts"]["skeletal_mesh_contracts"],
                "blueprints": result["semantic_contract_counts"]["blueprint_contracts"],
                "max_numeric_delta": result["maximum_numeric_contract_delta"],
                "catalogues": result["catalogue_actor_counts"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
