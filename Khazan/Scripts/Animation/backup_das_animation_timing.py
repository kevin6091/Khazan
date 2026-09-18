"""Back up every existing DAS animation package that the timing import will replace.

This is a filesystem-only preflight.  It also records hashes for every
locomotion package protected by the user so the final audit can prove that the
timing restoration did not touch them.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
MANIFEST = ROOT / "AnimationImportManifest.json"
INVENTORY = PROJECT / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"
REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_AnimationBackup_20260916.json"
BACKUP_PARENT = PROJECT / "Saved/ArtBackups"
PACKAGE_EXTENSIONS = (".uasset", ".uexp", ".ubulk", ".uptnl")


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


def relative_package_files(package: str) -> list[pathlib.Path]:
    if not package.startswith("/Game/") or ".." in package.split("/"):
        raise RuntimeError("Unsafe package path: " + package)
    stem = PROJECT / "Content" / pathlib.Path(package.removeprefix("/Game/"))
    files = [stem.with_suffix(extension) for extension in PACKAGE_EXTENSIONS]
    return [path for path in files if path.is_file()]


def relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(PROJECT.resolve()):
        raise RuntimeError("Path escaped project: " + str(path))
    return resolved.relative_to(PROJECT.resolve()).as_posix()


def editor_is_open() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "UnrealEditor.exe" in result.stdout


def main() -> None:
    if editor_is_open():
        raise RuntimeError(
            "UnrealEditor.exe is open. Save and close it before creating the mutation backup."
        )
    if REPORT.exists():
        raise RuntimeError("Backup report already exists; inspect it before another backup: " + str(REPORT))

    rows = read(MANIFEST)
    inventory = read(INVENTORY)
    replacements = [row for row in rows if row["operation"] == "replace_existing"]
    if len(replacements) != 608:
        raise RuntimeError(f"Expected 608 existing packages, found {len(replacements)}")
    protected_packages = set(inventory["protected_locomotion_sequences"])
    mutation_packages = {row["destination"] for row in replacements}
    overlap = sorted(mutation_packages & protected_packages)
    if overlap:
        raise RuntimeError("Protected locomotion entered mutation set: " + repr(overlap))

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = BACKUP_PARENT / f"DAS_Animation_PreTimingFix_{stamp}"
    backup_root.mkdir(parents=True, exist_ok=False)
    result = {
        "schema": 1,
        "status": "running",
        "backup_root": str(backup_root),
        "animation_manifest": str(MANIFEST),
        "animation_manifest_sha256": sha256(MANIFEST),
        "inventory": str(INVENTORY),
        "inventory_sha256": sha256(INVENTORY),
        "mutated_packages": [],
        "protected_locomotion_packages": [],
        "current_locomotion_dependencies": inventory["current_locomotion_dependencies"],
    }
    try:
        for package in sorted(mutation_packages):
            files = relative_package_files(package)
            if not files or not any(path.suffix == ".uasset" for path in files):
                raise RuntimeError("Existing package file is missing: " + package)
            file_rows = []
            for source in files:
                project_relative = relative(source)
                target = backup_root / project_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                source_hash = sha256(source)
                shutil.copy2(source, target)
                backup_hash = sha256(target)
                if backup_hash != source_hash:
                    raise RuntimeError("Backup hash mismatch: " + project_relative)
                file_rows.append(
                    {
                        "path": project_relative,
                        "sha256": source_hash,
                        "bytes": source.stat().st_size,
                        "backup_path": str(target),
                    }
                )
            result["mutated_packages"].append({"package": package, "files": file_rows})

        for package in sorted(protected_packages):
            files = relative_package_files(package)
            if not files or not any(path.suffix == ".uasset" for path in files):
                raise RuntimeError("Protected package file is missing: " + package)
            result["protected_locomotion_packages"].append(
                {
                    "package": package,
                    "files": [
                        {
                            "path": relative(path),
                            "sha256": sha256(path),
                            "bytes": path.stat().st_size,
                        }
                        for path in files
                    ],
                }
            )

        result["status"] = "passed"
        result["mutation_package_count"] = len(result["mutated_packages"])
        result["mutation_file_count"] = sum(
            len(row["files"]) for row in result["mutated_packages"]
        )
        result["backup_bytes"] = sum(
            file["bytes"]
            for row in result["mutated_packages"]
            for file in row["files"]
        )
        result["protected_package_count"] = len(result["protected_locomotion_packages"])
        result["protected_file_count"] = sum(
            len(row["files"]) for row in result["protected_locomotion_packages"]
        )
    except Exception as error:
        result["status"] = "failed"
        result["error"] = str(error)
        raise
    finally:
        write(backup_root / "BackupManifest.json", result)
        write(REPORT, result)
    print(json.dumps({key: value for key, value in result.items() if key.endswith("count") or key in {"status", "backup_root", "backup_bytes"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
