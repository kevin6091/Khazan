"""Finalize the BigBear source archive without copying any game key."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import shutil


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/BigBear_20260910"
REPORTS = PROJECT / "Saved/ImportReports"
META = PROJECT / "Content/_Art/Enemies/Shared/Beasts/BigBear/Metadata/Extraction_20260910"
ARCHIVE = pathlib.Path.home() / "Desktop" / "카잔" / "EnemyExtracts" / "BigBear_20260910"
README = PROJECT / "Docs/Art/BIG_BEAR_EXTRACTION_2026-09-10.md"
SCRIPT_NAMES = [
    "prepare_big_bear_sources.py",
    "build_big_bear_import_manifest.py",
    "prepare_big_bear_animation_timing.py",
    "import_big_bear_library.py",
    "cleanup_big_bear_temp_assets.py",
    "audit_big_bear_skeleton.py",
    "import_big_bear_animations.py",
    "run_big_bear_animation_batches.py",
    "build_big_bear_assemblies.py",
    "audit_big_bear_library.py",
    "verify_big_bear_render.py",
    "archive_big_bear_sources.py",
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


def copy_and_verify(source: pathlib.Path, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256(source) != sha256(destination):
        raise RuntimeError("Archive copy hash mismatch: " + str(source))


def main() -> None:
    closure = read(ROOT / "SourceClosure.json")
    manifest = read(ROOT / "ImportManifest.json")
    animations = read(ROOT / "AnimationImportManifest.json")
    validation = read(META / "ValidationSummary.json")
    render = read(META / "RenderValidationSummary.json")
    if validation["status"] != "passed" or render["status"] != "passed":
        raise RuntimeError("BigBear final validation has not passed")

    raw = ARCHIVE / "RawCookedArchive"
    missing_raw = [package for package in closure["packages"] if not (raw / (package + ".uasset")).is_file()]
    if missing_raw:
        raise RuntimeError("Missing archived cooked packages: " + repr(missing_raw))

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    copy_and_verify(README, ARCHIVE / "README_KO.md")
    copy_and_verify(README, META / "README_KO.md")
    for folder in ["Assets", "Derived", "Discovery", "Metadata", "MetadataInitial", "Requests"]:
        source = ROOT / folder
        if source.is_dir():
            shutil.copytree(source, ARCHIVE / folder, dirs_exist_ok=True)
    for source in ROOT.iterdir():
        if source.is_file() and source.suffix.lower() in {".json", ".csv"}:
            copy_and_verify(source, ARCHIVE / source.name)

    archive_reports = ARCHIVE / "Reports"
    project_reports = META / "Reports"
    for source in REPORTS.glob("BigBear_*.json"):
        copy_and_verify(source, archive_reports / source.name)
        copy_and_verify(source, project_reports / source.name)
    batch_root = REPORTS / "BigBearAnimationBatches"
    if batch_root.is_dir():
        shutil.copytree(batch_root, archive_reports / "AnimationBatches", dirs_exist_ok=True)
        shutil.copytree(batch_root, project_reports / "AnimationBatches", dirs_exist_ok=True)

    pipeline = ARCHIVE / "PipelineScripts"
    for name in SCRIPT_NAMES:
        source = PROJECT / "Scripts/Enemies" / name
        if source.is_file():
            copy_and_verify(source, pipeline / name)
    shutil.copytree(
        PROJECT / "Scripts/Enemies/EnemyExtractor",
        pipeline / "EnemyExtractor",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("bin", "obj"),
    )

    settings = read(pathlib.Path.home() / "AppData/Roaming/FModel/AppSettings.json")
    game_paks = pathlib.Path(settings["GameDirectory"]) / "Content/Paks"
    source_snapshot = [
        {
            "file": path.name,
            "bytes": path.stat().st_size,
            "mtime_utc": datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat(),
        }
        for path in sorted(game_paks.iterdir())
        if path.suffix.lower() in {".pak", ".ucas", ".utoc"}
    ]
    native = PROJECT / "Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/CUE4Parse-Natives.dll"
    extractor = PROJECT / "Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.dll"
    final = {
        "status": "passed",
        "date": datetime.datetime.now().astimezone().isoformat(),
        "scope": "Shared HeinMach/StormPass BigBear visual Enemy library and source-timed animation playback assets.",
        "source_levels": manifest["source_levels"],
        "source_character": manifest["source_character"],
        "source_animation_profile": manifest["source_animation_profile"],
        "selected_dependency_packages": len(closure["packages"]),
        "metadata_failures": closure["metadata_failures"],
        "external_reference_packages": len(closure["external_references"]),
        "raw_cooked_packages_verified": len(closure["packages"]),
        "project_assets": validation["asset_structure"],
        "mesh": validation["mesh"],
        "textures": validation["textures_verified"],
        "texture_resolution_contract": validation["texture_resolution_contract"],
        "preview_material_masters": validation["preview_masters_verified"],
        "material_instances": validation["materials_verified"],
        "material_parameters_verified": validation["material_parameters_verified"],
        "assemblies": validation["assemblies"],
        "animations": validation["animations"],
        "render_materials_verified": len(render["materials"]),
        "render_assemblies_verified": len(render["assemblies"]),
        "catalogue_map": validation["catalogue_map"],
        "external_archive": str(ARCHIVE),
        "source_snapshot": source_snapshot,
        "extractor_sha256": sha256(extractor),
        "cue4parse_natives_sha256": sha256(native),
        "limitations": manifest["limitations"],
        "hash_manifest": "ArchiveSHA256.json",
    }
    for destination in [
        ROOT / "FinalExtractionReport.json",
        ARCHIVE / "FinalExtractionReport.json",
        META / "FinalExtractionReport.json",
        REPORTS / "BigBear_FinalExtraction_20260910.json",
    ]:
        write(destination, final)

    hashes = {
        path.relative_to(ARCHIVE).as_posix(): sha256(path)
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name != "ArchiveSHA256.json"
    }
    write(ARCHIVE / "ArchiveSHA256.json", hashes)
    mismatched = [relative for relative, digest in hashes.items() if sha256(ARCHIVE / relative) != digest]
    if mismatched:
        raise RuntimeError("Archive verification failed: " + repr(mismatched))
    write(META / "ArchiveSummary.json", {
        "status": "passed",
        "external_archive": str(ARCHIVE),
        "files_hashed": len(hashes),
        "files_verified": len(hashes),
        "archive_bytes": sum(path.stat().st_size for path in ARCHIVE.rglob("*") if path.is_file()),
        "hash_manifest": str(ARCHIVE / "ArchiveSHA256.json"),
    })
    print(
        json.dumps(
            {
                "status": "passed",
                "source_packages": len(closure["packages"]),
                "animations": len(animations),
                "files_hashed": len(hashes),
                "archive": str(ARCHIVE),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
