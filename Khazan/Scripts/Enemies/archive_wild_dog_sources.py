"""Finalize the WildDog source archive without copying any game key."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import shutil
import zipfile


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/WildDog_20260915"
REPORTS = PROJECT / "Saved/ImportReports"
META = PROJECT / "Content/_Art/Enemies/Shared/Beasts/WildDog/Metadata/Extraction_20260915"
ARCHIVE = pathlib.Path.home() / "Desktop" / "카잔" / "EnemyExtracts" / "WildDog_20260915"
README = PROJECT / "Docs/Art/WILD_DOG_EXTRACTION_2026-09-15.md"
SCRIPT_NAMES = [
    "prepare_wild_dog_sources.py",
    "build_wild_dog_import_manifest.py",
    "prepare_wild_dog_animation_timing.py",
    "import_wild_dog_library.py",
    "import_wild_dog_animations.py",
    "run_wild_dog_animation_batches.py",
    "build_wild_dog_assemblies.py",
    "audit_wild_dog_library.py",
    "verify_wild_dog_render.py",
    "capture_wild_dog_editor_preview.py",
    "archive_wild_dog_sources.py",
    "run_wild_dog_editor_stage.py",
    "audit_wild_dog_sources.py",
    "prepare_yetuga_sources.py",  # extraction helper imported by the new discovery script
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
        raise RuntimeError("WildDog final validation has not passed")
    if "capture_wild_dog_editor_preview.py" not in render.get("command_line", ""):
        raise RuntimeError("Final visual capture must follow real editor resource warmup")
    for stage in ["library", "assemblies", "audit", "render"]:
        process = read(REPORTS / f"WildDog_Process_{stage}_20260915.json")
        if process["process_exit_code"] != 0:
            raise RuntimeError("Final stage process did not exit successfully: " + stage)

    raw = ARCHIVE / "RawCookedArchive"
    missing_raw = [package for package in closure["packages"] if not (raw / (package + ".uasset")).is_file()]
    if missing_raw:
        raise RuntimeError("Missing archived cooked packages: " + repr(missing_raw))

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    copy_and_verify(README, ARCHIVE / "README_KO.md")
    copy_and_verify(README, META / "README_KO.md")
    for name in ["WildDog_RenderPreview_20260915.png", "WildDog_BaseColorPreview_20260915.png"]:
        copy_and_verify(REPORTS / name, META / "Preview" / name)
        copy_and_verify(REPORTS / name, ARCHIVE / "Preview" / name)
    for folder in ["Assets", "Derived", "Discovery", "Metadata", "MetadataInitial", "Requests"]:
        source = ROOT / folder
        if source.is_dir():
            shutil.copytree(source, ARCHIVE / folder, dirs_exist_ok=True)
    for source in ROOT.iterdir():
        if source.is_file() and source.suffix.lower() in {".json", ".csv"}:
            copy_and_verify(source, ARCHIVE / source.name)

    # Keep all original JSON accessible from Git without thousands of Content files.
    metadata_index = {}
    with zipfile.ZipFile(META / "SourceMetadata.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        # Classification evidence for excluded PicaroonDog/Ghost candidates is
        # also preserved as JSON, without importing those variants into UE.
        classified = {p.relative_to(ROOT / "Metadata").as_posix().removesuffix(".json")
                      for p in (ROOT / "Metadata/BBQ").rglob("*.json")}
        for package in sorted(set(closure["packages"]) | classified):
            file = ROOT / "Metadata" / (package + ".json")
            if not file.exists():
                raise RuntimeError("Missing source metadata " + package)
            bundle.write(file, package + ".json")
            metadata_index[package] = {"sha256":sha256(file),"bytes":file.stat().st_size}
    write(META / "SourceMetadataIndex.json", metadata_index)
    copy_and_verify(META / "SourceMetadata.zip", ARCHIVE / "SourceMetadata.zip")
    copy_and_verify(META / "SourceMetadataIndex.json", ARCHIVE / "SourceMetadataIndex.json")

    archive_reports = ARCHIVE / "Reports"
    project_reports = META / "Reports"
    for source in REPORTS.glob("WildDog_*.json"):
        copy_and_verify(source, archive_reports / source.name)
        copy_and_verify(source, project_reports / source.name)
    batch_root = REPORTS / "WildDogAnimationBatches"
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
        "scope": "Live StormPass CB_WhiteDog coat outcomes and source-timed playback library.",
        "source_metadata_packages": len(metadata_index),
        "source_levels": manifest["source_levels"],
        "source_character": manifest["source_character"],
        "source_animation_profile": manifest["source_animation_profile"],
        "selected_dependency_packages": len(closure["packages"]),
        "metadata_failures": closure["metadata_failures"],
        "external_reference_packages": len(closure["external_references"]),
        "raw_cooked_packages_verified": len(closure["packages"]),
        "project_assets": validation["asset_structure"],
        "mesh": validation["mesh"],
        "meshes": validation["meshes"],
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
        REPORTS / "WildDog_FinalExtraction_20260915.json",
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
