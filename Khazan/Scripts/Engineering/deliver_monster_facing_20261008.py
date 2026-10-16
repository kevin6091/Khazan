"""Offline, hash-guarded Monster Facing delivery. Never run while Main is saving.

Usage: python deliver_monster_facing_20261008.py preflight|deliver
Preflight is read-only. Delivery preserves existing modules and publishes the
new alias by atomically replacing the current Main manifest as its final step.
"""

from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parents[1] / "Khazan_MonsterWork_20261006" / "Khazan"
OUT = ROOT / "Metadata/MonsterMotion_20261008"
MANIFEST = "Binaries/Win64/UnrealEditor.modules"
MODULE = "Binaries/Win64/UnrealEditor-Khazan.dll"
ALIAS = "Binaries/Win64/UnrealEditor-KhazanMonsterFacing20261008.dll"
MAILBOX = "Scripts/Engineering/monster_isolated_editor.py"
SOURCE = (
    "Source/Khazan/AI/KZMonsterAIController.cpp",
    "Source/Khazan/AI/KZMonsterAIController.h",
    "Source/Khazan/Character/KZMonster.cpp",
    "Source/Khazan/Character/KZMonster.h",
    "Source/Khazan/Ability/Combo/KZComboActionAbility.cpp",
    "Source/Khazan/Ability/Combo/KZComboActionAbility.h",
    "Source/Khazan/Tests/KZMonsterAIPIETest.cpp",
    "Source/Khazan/Tests/KZHealAbilityPIETest.cpp",
)
ASSETS = tuple(
    f"Content/Monsters/{family}/Animations/BS_Combat_{family}.uasset"
    for family in ("Swordsman", "SwordShield", "HeavySwordsman", "HalberdElite")
)


class SafetyError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise SafetyError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value),
            f"Invalid SHA-256: {value!r}")
    return value.lower()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def path_in(root, relative):
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), f"Path escapes project: {relative}")
    return path


def hash_map(value, label):
    require(isinstance(value, dict), f"{label} must be a SHA-256 map")
    return {relative: digest(expected) for relative, expected in value.items()}


def source_inventory(root):
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted((root / "Source").rglob("*")) if p.is_file()}


def check_map(root, expected, label):
    for relative, expected_sha in expected.items():
        path = path_in(root, relative)
        require(path.is_file() and sha(path) == expected_sha,
                f"{label} hash changed: {relative}")


def baseline(filename, allowed):
    rows = read(OUT / filename)
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            f"Invalid baseline: {filename}")
    require(len(rows) == len(allowed) and {r.get("file") for r in rows} == set(allowed),
            f"Unexpected owned paths in {filename}")
    return {r["file"]: digest(r["mainBefore"]) for r in rows}


def snapshot():
    proof_path = OUT / "VerifiedDeliveryProof.json"
    # Check this first: an unfinished build/test phase cannot stage any delivery.
    require(proof_path.is_file(), f"Missing verification proof: {proof_path}")
    require(not (OUT / "Delivery.json").exists(), "Existing successful receipt; do not repeat delivery")
    proof = read(proof_path)
    require(isinstance(proof, dict), "Verification proof must be an object")
    tests = proof.get("required_tests")
    require(isinstance(tests, dict) and tests and all(value is True for value in tests.values()),
            "Every required test must be explicitly true")
    require(proof.get("build_log") == "IntegratedFinalBuild.log", "Unexpected integrated build log")
    build_log = OUT / proof["build_log"]
    require(build_log.is_file(), "Integrated build log is missing")
    build_bytes = build_log.read_bytes()
    # Windows PowerShell redirection uses UTF-16; retain the original evidence bytes.
    build_encoding = "utf-16" if build_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    require(re.search(r"(?m)^Result:\s*Succeeded\s*$", build_bytes.decode(build_encoding)),
            "Integrated build did not succeed")

    before = baseline("OwnedBaseline.json", SOURCE)
    before.update(baseline("AssetBaseline.json", ASSETS))
    mailbox_baseline = read(OUT / "MailboxBaseline.json")
    require(mailbox_baseline.get("file") == MAILBOX, "Unexpected mailbox baseline path")
    before[MAILBOX] = digest(mailbox_baseline["mainBefore"])
    after_source = hash_map(proof.get("source"), "source")
    after_assets = hash_map(proof.get("assets"), "assets")
    require(set(after_source) == set(SOURCE), "Proof must cover exactly eight owned Source files")
    require(set(after_assets) == set(ASSETS), "Proof must cover exactly four combat BlendSpaces")
    non_owned = hash_map(proof.get("non_owned_source"), "non_owned_source")
    require(all(isinstance(p, str) and p.startswith("Source/") and p not in SOURCE
                for p in non_owned), "Invalid non-owned Source paths")
    for root, owned in ((ROOT, {p: before[p] for p in SOURCE}), (WORK, after_source)):
        require(source_inventory(root) == {**non_owned, **owned},
                f"Complete compiled Source inventory differs: {root}")
    check_map(ROOT, before, "Main baseline/CAS")
    check_map(WORK, after_assets, "Verified Work assets")
    work_mailbox = path_in(WORK, MAILBOX)
    require(work_mailbox.is_file(), "Verified Work mailbox script is missing")
    after = {**after_source, **after_assets, MAILBOX: sha(work_mailbox)}

    manifest_bytes = (ROOT / MANIFEST).read_bytes()
    main_manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    work_manifest = read(WORK / MANIFEST)
    require(isinstance(main_manifest, dict) and isinstance(work_manifest, dict), "Invalid module manifest")
    require(main_manifest.get("BuildId") and
            main_manifest["BuildId"] == work_manifest.get("BuildId"), "Main/Work module BuildId differs")
    require(isinstance(main_manifest.get("Modules"), dict) and "Khazan" in main_manifest["Modules"],
            "Main manifest has no Khazan module")
    live_module = main_manifest["Modules"]["Khazan"]
    require(isinstance(live_module, str) and Path(live_module).name == live_module and
            (ROOT / "Binaries/Win64" / live_module).is_file(), "Invalid current Main module entry")
    require(work_manifest.get("Modules", {}).get("Khazan") == Path(MODULE).name,
            "Work manifest does not reference the verified standard module")
    module_sha = digest(proof.get("module_sha256"))
    require((WORK / MODULE).is_file() and sha(WORK / MODULE) == module_sha,
            "Work DLL differs from integrated build/test proof")
    require((WORK / MODULE).stat().st_mtime_ns <= build_log.stat().st_mtime_ns,
            "Work DLL is newer than the integrated build log")
    pdb_relative = str(Path(MODULE).with_suffix(".pdb")).replace("\\", "/")
    require((WORK / pdb_relative).is_file(), "Verified Work PDB is missing")
    for relative in (ALIAS, str(Path(ALIAS).with_suffix(".pdb")).replace("\\", "/")):
        require(not path_in(ROOT, relative).exists(), f"New alias already exists; never overwrite: {relative}")
    preserved = {p.relative_to(ROOT).as_posix(): sha(p)
                 for pattern in ("UnrealEditor-Khazan*.dll", "UnrealEditor-Khazan*.pdb")
                 for p in (ROOT / "Binaries/Win64").glob(pattern) if p.is_file()}
    next_manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    next_manifest["Modules"]["Khazan"] = Path(ALIAS).name
    evidence = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in
                (proof_path, build_log, OUT / "OwnedBaseline.json", OUT / "AssetBaseline.json",
                 OUT / "MailboxBaseline.json")}
    return dict(before=before, after=after, non_owned=non_owned, preserved=preserved,
                proof=proof, evidence=evidence, manifest_bytes=manifest_bytes,
                manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                next_manifest_bytes=encode(next_manifest), build_id=main_manifest["BuildId"],
                module_sha256=module_sha, pdb_relative=pdb_relative,
                pdb_sha256=sha(WORK / pdb_relative), work_manifest_sha256=sha(WORK / MANIFEST))


def guard(snapshot_data, owned_before=True):
    check_map(ROOT, snapshot_data["evidence"], "Verification evidence")
    check_map(ROOT, snapshot_data["preserved"], "Previously existing modules")
    require(source_inventory(ROOT) == {**snapshot_data["non_owned"], **{
            p: snapshot_data["before" if owned_before else "after"][p] for p in SOURCE}},
            "Main Source changed during delivery")
    require(source_inventory(WORK) == {**snapshot_data["non_owned"], **{
            p: snapshot_data["after"][p] for p in SOURCE}}, "Work compiled Source changed during delivery")
    check_map(WORK, snapshot_data["after"], "Verified Work files")
    require(sha(WORK / MODULE) == snapshot_data["module_sha256"] and
            sha(WORK / snapshot_data["pdb_relative"]) == snapshot_data["pdb_sha256"] and
            sha(WORK / MANIFEST) == snapshot_data["work_manifest_sha256"],
            "Work module/PDB/manifest changed during delivery")


def stage_copy(source, destination, expected):
    # Keep temporary files out of Source so the exact compiled inventory stays unchanged.
    staging = OUT / "Staging"
    staging.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".monster_facing_", suffix=".pending", dir=staging)
    os.close(descriptor)
    pending = Path(name)
    try:
        shutil.copy2(source, pending)
        require(sha(pending) == expected, f"Staging hash differs: {source}")
        return pending
    except BaseException:
        pending.unlink(missing_ok=True)
        raise


def stage_bytes(data, destination):
    descriptor, name = tempfile.mkstemp(prefix=".monster_facing_", suffix=".pending", dir=destination.parent)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return Path(name)


def cas_replace(pending, destination, expected):
    require(destination.is_file() and sha(destination) == expected,
            f"CAS rejected concurrent change: {destination}")
    os.replace(pending, destination)


def deliver():
    data = snapshot()
    lock = OUT / "Delivery.lock"
    pending = []
    replaced = []
    manifest_published = False
    alias_pdb = str(Path(ALIAS).with_suffix(".pdb")).replace("\\", "/")
    # The exclusive task lock also prevents two invocations racing each other.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        staged = {}
        for relative, expected in data["after"].items():
            staged[relative] = stage_copy(WORK / relative, ROOT / relative, expected)
            pending.append(staged[relative])
        for relative, source, expected in ((ALIAS, WORK / MODULE, data["module_sha256"]),
                (alias_pdb, WORK / data["pdb_relative"], data["pdb_sha256"])):
            staged[relative] = stage_copy(source, ROOT / relative, expected)
            pending.append(staged[relative])
        manifest_pending = stage_bytes(data["next_manifest_bytes"], ROOT / MANIFEST)
        pending.append(manifest_pending)
        guard(data)
        check_map(ROOT, data["before"], "Final Main baseline/CAS")
        require(sha(ROOT / MANIFEST) == data["manifest_sha256"], "Main manifest changed after capture")

        backup = OUT / "Backup/Before"
        backup_expected = {**data["before"], MANIFEST: data["manifest_sha256"]}
        for relative, expected in backup_expected.items():
            destination = backup / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(ROOT / relative, destination)
            require(sha(destination) == expected, f"Existing backup or Main drift: {relative}")

        # Publish the owned assets first: an editor file lock fails before Source/module publication.
        for relative in (*ASSETS, *SOURCE, MAILBOX):
            cas_replace(staged[relative], ROOT / relative, data["before"][relative])
            replaced.append(relative)
        guard(data, owned_before=False)
        check_map(ROOT, data["after"], "Delivered owned files")
        # NTFS hard-link publication is atomic and fails if the alias exists. No replacement of any DLL.
        for relative in (ALIAS, alias_pdb):
            os.link(staged[relative], ROOT / relative)
        require(sha(ROOT / ALIAS) == data["module_sha256"] and
                sha(ROOT / alias_pdb) == data["pdb_sha256"], "Published alias hash differs")
        cas_replace(manifest_pending, ROOT / MANIFEST, data["manifest_sha256"])
        manifest_published = True
        require((ROOT / MANIFEST).read_bytes() == data["next_manifest_bytes"], "Manifest verification failed")
        guard(data, owned_before=False)
        check_map(ROOT, data["after"], "Final owned files")
        files = (*SOURCE, *ASSETS, MAILBOX, ALIAS, alias_pdb, MANIFEST)
        receipt = dict(success=True, hashes={p: sha(ROOT / p) for p in files},
            module=str(ROOT / ALIAS), module_sha256=data["module_sha256"],
            restart_required_for_previously_running_editor=True, needrestart=True,
            native_main_pie_verified=False, non_owned_source=data["non_owned"],
            preserved_modules=data["preserved"], required_tests=data["proof"]["required_tests"],
            proof_sha256=data["evidence"]["Metadata/MonsterMotion_20261008/VerifiedDeliveryProof.json"],
            build_log=data["proof"]["build_log"], main_manifest_before_sha256=data["manifest_sha256"],
            main_build_id=data["build_id"], work_build_id=data["build_id"],
            backup_before_sha256=backup_expected,
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        receipt_pending = stage_bytes(encode(receipt), OUT / "Delivery.json")
        pending.append(receipt_pending)
        os.link(receipt_pending, OUT / "Delivery.json")
        return receipt
    except BaseException as error:
        # Only restore a file still containing our exact staged bytes. Never undo a concurrent edit.
        rollback = {}
        if manifest_published:
            expected = hashlib.sha256(data["next_manifest_bytes"]).hexdigest()
            try:
                restore = stage_bytes(data["manifest_bytes"], ROOT / MANIFEST)
                pending.append(restore)
                cas_replace(restore, ROOT / MANIFEST, expected)
                rollback[MANIFEST] = "restored"
            except Exception as restore_error:
                rollback[MANIFEST] = str(restore_error)
        for relative in reversed(replaced):
            try:
                restore = stage_copy(OUT / "Backup/Before" / relative, ROOT / relative, data["before"][relative])
                pending.append(restore)
                cas_replace(restore, ROOT / relative, data["after"][relative])
                rollback[relative] = "restored"
            except Exception as restore_error:
                rollback[relative] = str(restore_error)
        failure = dict(success=False, error=str(error), rollback=rollback,
                       created_aliases_preserved=[p for p in (ALIAS, alias_pdb) if (ROOT / p).exists()],
                       needrestart=manifest_published,
                       utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        (OUT / f"DeliveryFailure_{stamp}.json").write_bytes(encode(failure))
        raise
    finally:
        for path in pending:
            path.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "deliver"))
    args = parser.parse_args()
    if args.mode == "deliver":
        print(json.dumps(deliver(), ensure_ascii=False))
    else:
        data = snapshot()
        print(json.dumps(dict(success=True, mode="preflight", files=len(data["after"]) + 3,
              module=str(ROOT / ALIAS), module_sha256=data["module_sha256"],
              main_manifest_sha256=data["manifest_sha256"], build_id=data["build_id"],
              required_tests=data["proof"]["required_tests"], needrestart=True), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (SafetyError, OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Delivery safety error: {error}")
