"""Build the source-backed HeinMach Yetuga boss art and animation closure.

The HeinMach boss spawn references CB_Yetuga.  This script
starts from their exact spawn handlers and follows only Yetuga character,
material and animation references.  Audio, VFX and gameplay execution assets
remain recorded as external references instead of being imported as art.
"""

from __future__ import annotations

import collections
import json
import pathlib
import shutil
import subprocess
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
META = ROOT / "Metadata"
DOTNET = pathlib.Path.home() / ".dotnet/dotnet.exe"
DLL = PROJECT / "Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.dll"
FMODEL_ROOT = pathlib.Path.home() / "Desktop/카잔"
EXTERNAL = FMODEL_ROOT / "EnemyExtracts/Yetuga_20260911"
INDEX_PATH = ROOT / "Discovery/TargetedPackageIndex.json"

LEVEL_SOURCES = {
    "HeinMach": FMODEL_ROOT
    / "Exports/BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Spawn_Main01.json",
}

BASE_ROOT = "BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Base_Setting/"
DESIGN_ROOT = "BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/"
MODEL_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/"
RECIPE_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Data/RandomLookInfo/MonsterType/CD_RD_M_Yetuga"
MATERIAL_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Material/"
SELECTED_MESHES = {
    MODEL_ROOT + "Model/C_M_Yetuga",
    MODEL_ROOT + "Model/C_I_YetugaRock",
    MODEL_ROOT + "Model/C_I_YetugaRock_Small",
}


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def package_path(value: str) -> str | None:
    if value.startswith("/Game/"):
        value = "BBQ/Content/" + value[len("/Game/") :]
    if value.startswith(("BBQ/Content/", "Engine/Content/")):
        return value.split(".", 1)[0]
    return None


def references(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"AssetPathName", "ObjectPath"} and isinstance(child, str):
                result = package_path(child)
                if result:
                    yield result
            if isinstance(child, (dict, list)):
                yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def run_exporter(mode: str, output: pathlib.Path, packages: list[str], label: str) -> None:
    request = ROOT / "Requests" / f"{label}.json"
    write(request, sorted(set(packages)))
    output.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "Logs" / f"{label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            [str(DOTNET), str(DLL), mode, str(output), str(request)],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}; inspect {log_path}")


def ensure_metadata(packages: set[str], label: str) -> tuple[dict[str, list[dict]], list[dict]]:
    requested = sorted(set(packages))
    missing = [package for package in requested if not (META / f"{package}.json").exists()]
    failures: list[dict] = []
    if missing:
        run_exporter("metadata", META, missing, label)
        report_path = META / "MetadataExtractionReport.json"
        report = read(report_path)
        failures = [entry for entry in report if entry.get("status") != "ok"]
    objects = {
        package: read(META / f"{package}.json")
        for package in requested
        if (META / f"{package}.json").exists()
    }
    return objects, failures


def source_spawn_records() -> tuple[list[dict], set[str]]:
    records: list[dict] = []
    roots: set[str] = set()
    for level, source in LEVEL_SOURCES.items():
        objects = read(source)
        matches = [
            value
            for value in objects
            if value.get("Type") == "xxSpawnHandler_Character"
            and "Yetuga" in json.dumps(value, ensure_ascii=False)
        ]
        if not matches:
            raise RuntimeError(f"No Yetuga spawn handler in {source}")
        for value in matches:
            refs = sorted(set(references(value)))
            roots.update(ref for ref in refs if ref.startswith(DESIGN_ROOT))
            records.append(
                {
                    "level": level,
                    "source_level_package": value.get("Outer", {}).get("ObjectPath", "").split(".", 1)[0],
                    "actor_name": value["Name"],
                    "actor_type": value["Type"],
                    "properties": value.get("Properties", {}),
                    "references": refs,
                }
            )
    return records, roots


def should_follow(owner_package: str, owner_type: str, target: str) -> bool:
    if owner_type == "AnimComposite" and "CA_M_ApesStoneHandElite_DamageGrapple_Atk_B_0" in target:
        return True  # Inspect the two cross-species references before excluding their skeleton.
    # Materials may inherit shared base shaders/textures outside CHA_Material.
    # Follow only this typed art dependency chain, not every gameplay/VFX edge.
    if owner_type in {"Material", "MaterialInstanceConstant", "MaterialFunction", "Texture2D"}:
        return target.startswith("BBQ/Content/")
    if owner_type == "SkeletalMesh" and "/Material/" in target:
        return True
    if target.startswith((DESIGN_ROOT, MODEL_ROOT, RECIPE_ROOT)):
        return True
    if target.startswith(MATERIAL_ROOT):
        return owner_type in {
            "SkeletalMesh",
            "Material",
            "MaterialInstanceConstant",
            "Texture2D",
        } or owner_type.startswith("CD_RD_M_Yetuga") or owner_package.startswith(
            (MODEL_ROOT, RECIPE_ROOT, MATERIAL_ROOT)
        )
    return False


def discover() -> None:
    index = read(INDEX_PATH)
    indexed = {path[:-7] for path in index if path.endswith(".uasset")}
    spawns, roots = source_spawn_records()
    roots.update(path for path in indexed if path.startswith(BASE_ROOT))
    roots.update(path for path in indexed if path.startswith(RECIPE_ROOT))
    roots.update(path for path in indexed if path.startswith(DESIGN_ROOT + "Moving/") or path.startswith(DESIGN_ROOT + "Skill/"))

    pending = set(roots)
    visited: set[str] = set()
    types: dict[str, list[str]] = {}
    edges: list[dict] = []
    excluded: set[str] = set()
    failures: list[dict] = []
    round_number = 0

    while pending:
        round_number += 1
        objects, round_failures = ensure_metadata(pending, f"Yetuga_Metadata_{round_number:02d}")
        failures.extend(round_failures)
        next_pending: set[str] = set()
        for package, exports in objects.items():
            visited.add(package)
            types[package] = sorted({value.get("Type", "") for value in exports})
            for value in exports:
                owner_type = value.get("Type", "")
                for target in sorted(set(references(value))):
                    if target == package:
                        continue
                    followed = should_follow(package, owner_type, target)
                    edges.append(
                        {
                            "source": package,
                            "target": target,
                            "owner_type": owner_type,
                            "followed": followed,
                        }
                    )
                    if followed and target not in visited and target not in pending:
                        next_pending.add(target)
                    elif not followed:
                        excluded.add(target)
        failed_sources = {entry.get("source") for entry in round_failures}
        visited.update(source for source in failed_sources if source)
        pending = next_pending - visited
        print(
            "YETUGA_CLOSURE",
            round_number,
            "visited",
            len(visited),
            "next",
            len(pending),
            "failures",
            len(round_failures),
            flush=True,
        )

    asset_types = {"SkeletalMesh", "Texture2D", "AnimSequence"}
    exports = sorted(
        package
        for package, values in types.items()
        if asset_types.intersection(values)
        and ("SkeletalMesh" not in values or package in SELECTED_MESHES)
    )
    result = {
        "schema_version": 1,
        "source_character": "CB_Yetuga",
        "levels": sorted(LEVEL_SOURCES),
        "spawn_records": spawns,
        "packages": sorted(visited),
        "exports": exports,
        "types": types,
        "dependencies": edges,
        "external_references": sorted(excluded),
        "metadata_failures": failures,
        "selection": {
            "mesh": "Effective CB_Yetuga CharacterMesh0 and skill props; checked by import manifest",
            "material_variations": "Effective CB mesh material overrides and skill prop materials",
            "animations": "Composite/direct sequence references reachable from HeinMach and CB_Yetuga gameplay metadata",
        },
    }
    write(ROOT / "SourceClosure.json", result)
    write(ROOT / "LevelPresence.json", spawns)
    write(
        ROOT / "DiscoverySummary.json",
        {
            "status": "passed" if not failures else "passed_with_missing_external_metadata",
            "indexed_yetuga_packages": len(indexed),
            "selected_packages": len(visited),
            "export_packages": len(exports),
            "type_counts": dict(
                sorted(collections.Counter(kind for values in types.values() for kind in values).items())
            ),
            "metadata_failures": len(failures),
            "levels": {row["level"]: row["actor_name"] for row in spawns},
        },
    )
    print(json.dumps(read(ROOT / "DiscoverySummary.json"), ensure_ascii=False), flush=True)


def export_sources() -> None:
    closure = read(ROOT / "SourceClosure.json")
    export_packages = closure["exports"]
    run_exporter("export", ROOT / "Assets", export_packages, "Yetuga_ArtAnimationExport")
    run_exporter("raw", EXTERNAL / "RawCookedArchive", closure["packages"], "Yetuga_RawArchive")

    missing_exports = []
    for package in export_packages:
        candidates = [
            ROOT / "Assets" / f"{package}.psk",
            ROOT / "Assets" / f"{package}.pskx",
            ROOT / "Assets" / f"{package}.psa",
            ROOT / "Assets" / f"{package}.png",
        ]
        if not any(path.exists() for path in candidates):
            missing_exports.append(package)
    if missing_exports:
        raise RuntimeError(f"Missing converted exports: {missing_exports}")

    shutil.copytree(META, EXTERNAL / "Metadata", dirs_exist_ok=True)
    shutil.copytree(ROOT / "Assets", EXTERNAL / "Assets", dirs_exist_ok=True)
    for name in ["SourceClosure.json", "LevelPresence.json", "DiscoverySummary.json"]:
        shutil.copy2(ROOT / name, EXTERNAL / name)
    write(
        ROOT / "SourceExportSummary.json",
        {
            "status": "passed",
            "selected_packages": len(closure["packages"]),
            "export_packages": len(export_packages),
            "missing_exports": missing_exports,
            "work_assets": str(ROOT / "Assets"),
            "external_archive": str(EXTERNAL),
        },
    )
    shutil.copy2(ROOT / "SourceExportSummary.json", EXTERNAL / "SourceExportSummary.json")
    print(json.dumps(read(ROOT / "SourceExportSummary.json"), ensure_ascii=False), flush=True)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "discover"
    if mode == "discover":
        discover()
    elif mode == "export":
        export_sources()
    else:
        raise SystemExit("Usage: prepare_yetuga_sources.py [discover|export]")


if __name__ == "__main__":
    main()
