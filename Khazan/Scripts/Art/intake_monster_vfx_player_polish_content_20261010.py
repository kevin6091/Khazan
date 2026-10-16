"""Offline, receipt-bound intake of fourteen existing Player polish Effects.

Default is a read-only preflight. --apply copies exact saved bytes only into the
physical MonsterVFX checkout. It never imports/resaves assets or writes Main
product files. Original MonsterVFX reports remain immutable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / "Khazan_MonsterVFXWork_20261008" / "Khazan"
OUT = MAIN / "Saved/ImportReports/MonsterVFX_20261008"
PRIVATE_OUT = WORK / "Saved/ImportReports/MonsterVFX_20261008"
RES = PRIVATE_OUT / "Resources"
REPORT = OUT / "Authoring/SharedEffectsRebaseRevision.json"
MIRROR = PRIVATE_OUT / "Authoring/SharedEffectsRebaseRevision.json"
BACKUPS = OUT / "Authoring/SharedEffectsRebaseRevision/ImmutableBeforePrivate"
EXTERNAL = MAIN / "Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery"
DELIVERED_SHA = "a75fa9803d7a40c1d0682b27dc1a085724477c38d2b2c73f632991ddb7ed7fa9"
SCHEMA = "Khazan.MonsterVFX.SharedEffectsRebaseRevision.v1"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def physical(path, root):
    path, root = path.absolute(), root.resolve()
    require(path.resolve().is_relative_to(root), f"Outside owned root: {path}")
    require(os.path.normcase(str(path.resolve())) == os.path.normcase(str(path)),
            f"Junction/symlink mutation path: {path}")
    return path


def write_new(path, data, root):
    physical(path, root)
    require(not path.exists(), f"Refusing to replace existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    physical(path.parent, root)
    with path.open("xb") as stream:
        stream.write(data)


def main_inputs():
    result = {}
    for directory in ("Source", "Config"):
        for path in sorted((MAIN / directory).rglob("*")):
            if path.is_file():
                result[path.relative_to(MAIN).as_posix()] = sha(path)
    for path in sorted(MAIN.glob("*.uproject")):
        result[path.relative_to(MAIN).as_posix()] = sha(path)
    return result


def owned_editor_census():
    command = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' } | "
               "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            check=True, capture_output=True, text=True, encoding="utf-8")
    rows = json.loads(result.stdout) if result.stdout.strip() else []
    rows = [rows] if isinstance(rows, dict) else rows
    needle = str(WORK / "Khazan.uproject").replace("\\", "/").lower()
    owned = [r for r in rows if needle in (r.get("CommandLine") or "").replace("\\", "/").lower()]
    require(not owned, f"Private editor must be closed before byte intake: {owned}")
    return {"private_editors": owned, "method": "Read-only Win32_Process exact private .uproject argument"}


def fingerprint(table):
    text = json.dumps(table, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(apply=False):
    require(MAIN == MAIN.resolve() and WORK == WORK.resolve(), "Checkout root must be physical")
    require(not REPORT.exists() and not MIRROR.exists(), "Revision is immutable; already recorded")
    delivery_path = EXTERNAL / "Delivered.json"
    require(sha(delivery_path) == DELIVERED_SHA, "Unexpected external delivery receipt")
    delivered = load(delivery_path)
    prepared_path, approval_path = EXTERNAL / "Prepared.json", EXTERNAL / "RootApproval.json"
    require(sha(prepared_path) == delivered["prepared_sha256"], "External prepared receipt changed")
    require(sha(approval_path) == delivered["approval_sha256"], "External approval changed")
    prepared, approval = load(prepared_path), load(approval_path)
    require(prepared["files"] == delivered["files"], "External selected files differ")
    require(approval.get("approved") and approval["prepared_sha256"] == delivered["prepared_sha256"],
            "External approval is not bound to the delivered content")
    frozen_path = EXTERNAL.parent / prepared["frozen_manifest"]["path"]
    require(sha(frozen_path) == prepared["frozen_manifest"]["sha256"], "External frozen candidate changed")
    baseline_path, art_path = OUT / "WorkBaseline.json", RES / "ArtCandidateManifest.json"
    baseline, art = load(baseline_path), load(art_path)
    old = {p: h for p, h in baseline["main_sha256"].items()
           if p.startswith("Content/_Art/Effects/") and p.endswith(".uasset")}
    require(len(old) == 2034, "Exact stored original Effects baseline changed")
    actual_names = {p.relative_to(MAIN).as_posix() for p in (MAIN / "Content/_Art/Effects").rglob("*.uasset")}
    require(actual_names == set(old), "Unexpected Main Effects additions/removals")
    approved = [r for r in delivered["files"] if r["file"].startswith("Content/_Art/Effects/")]
    require(len(approved) == 14 and len({r["file"] for r in approved}) == 14,
            "Expected fourteen unique external Effects rows")
    require(len(delivered["files"]) == 17, "External delivery scope changed")
    union_path = RES / "UnionAssetManifest.json"
    union = load(union_path)
    union_rows = union if isinstance(union, list) else union["assets"]
    union_by_path = {"Content/" + r["destination"].removeprefix("/Game/") + ".uasset": r
                     for r in union_rows}
    art_by_path = {r["relative_file"]: r for r in art["assets"]}
    require(len(art_by_path) == 457, "Own Art457 set changed")
    require(not set(art_by_path).intersection(r["file"] for r in approved), "External Art overlaps own candidates")
    immutable = [baseline_path, art_path, union_path, RES / "FinalResourceAudit.json",
                 RES / "NativeAdapterMap.json", RES / "ExecutionRadiusRevision.json",
                 RES / "LightUsageRevision.json", delivery_path, prepared_path, approval_path, frozen_path]
    require(all(p.is_file() for p in immutable), "A required immutable proof is missing")
    immutable_before = {str(p): sha(p) for p in immutable}
    inputs_before = main_inputs()
    main_before = {p: sha(MAIN / p) for p in old}
    private_before = {p: sha(WORK / p) for p in old}
    require(private_before == old, "Private reused Effects differ from original baseline")
    expected = dict(old)
    rows = []
    for r in approved:
        relative = r["file"]
        require(relative in old and r["before"] == old[relative] and r["after"] != r["before"],
                f"External old hash does not bind original baseline: {relative}")
        require(main_before[relative] == r["after"], f"Main does not match external after SHA: {relative}")
        source = union_by_path.get(relative)
        require(source and source.get("reused_native"), f"Unknown reused source resource: {relative}")
        physical(WORK / relative, WORK)
        expected[relative] = r["after"]
        rows.append({"relative": relative, "source_package": source["source_package"],
                     "source_json": source["source_json"], "source_sha256": source["source_sha256"],
                     "prior_private_sha256": r["before"], "original_main_before_sha256": old[relative],
                     "main_before_sha256": r["after"], "after_sha256": r["after"],
                     "backup_path": str(BACKUPS / relative), "backup_sha256": r["before"],
                     "reused_native": True, "external_selected_before_sha256": r["before"],
                     "external_selected_after_sha256": r["after"]})
    require(main_before == expected, "Main Effects drift includes changes outside the delivered fourteen")
    art_before = {}
    for relative, r in art_by_path.items():
        require(sha(WORK / relative) == r["sha256"], f"Own Art candidate drift: {relative}")
        require(sha(MAIN / relative) == r["before_main_sha256"], f"Own Art Main-before CAS drift: {relative}")
        art_before[relative] = r["sha256"]
    census = owned_editor_census()
    result = {"schema": SCHEMA, "utc": datetime.now(timezone.utc).isoformat(),
              "status": "prepared", "mode": "apply" if apply else "preflight", "main_mutations": 0,
              "content_scope": 14, "package_saves": 0, "content_files_copied": 0,
              "new_native_resources": 0, "external_delivery": {"path": str(delivery_path), "sha256": DELIVERED_SHA,
                  "status": delivered["status"], "fresh_Main_actual_RHI_and_saved_audits_required":
                  delivered["fresh_Main_actual_RHI_and_saved_audits_required"],
                  "prepared_sha256": delivered["prepared_sha256"], "approval_sha256": delivered["approval_sha256"]},
              "immutable_report_sha256": immutable_before, "rows": rows,
              "main_input_before_sha256": inputs_before, "private_editor_census": census,
              "boundary": "External saved bytes are a new shared-resource baseline. No source re-extraction, asset import/resave, Main product mutation, or fresh MonsterVFX RHI success is implied."}
    if not apply:
        return result
    for r in rows:
        backup = Path(r["backup_path"])
        write_new(backup, (WORK / r["relative"]).read_bytes(), OUT)
        require(sha(backup) == r["backup_sha256"], "Private backup SHA mismatch")
    copied = []
    try:
        for r in rows:
            relative = r["relative"]
            require(sha(MAIN / relative) == r["after_sha256"] and sha(WORK / relative) == r["prior_private_sha256"],
                    f"CAS failed immediately before private copy: {relative}")
            owned_editor_census()
            target = physical(WORK / relative, WORK)
            temporary = physical(target.with_name(target.name + ".MonsterVFXIntake.tmp"), WORK)
            require(not temporary.exists(), f"Unexpected staging file: {temporary}")
            with temporary.open("xb") as stream:
                stream.write((MAIN / relative).read_bytes())
            require(sha(temporary) == r["after_sha256"], "Staged private content SHA mismatch")
            require(sha(target) == r["prior_private_sha256"], "Private destination changed before replace")
            os.replace(temporary, target)
            copied.append(r)
        main_after = {p: sha(MAIN / p) for p in old}
        private_after = {p: sha(WORK / p) for p in old}
        require(main_after == main_before == expected and private_after == expected,
                "Current Main/private reused Effects hashes do not match")
        require(main_inputs() == inputs_before, "Main Source/Config/uproject changed during intake")
        require({str(p): sha(p) for p in immutable} == immutable_before, "Immutable reports changed during intake")
        for relative, r in art_by_path.items():
            require(sha(WORK / relative) == art_before[relative], f"Own Art changed during intake: {relative}")
            require(sha(MAIN / relative) == r["before_main_sha256"], f"Own Art Main-before changed: {relative}")
        result.update(status="passed", content_files_copied=14,
                      main_input_after_sha256=main_inputs(), main_source_config_uproject_unchanged=True,
                      original_reports_unchanged=True,
                      reuse_audit={"count": 2034, "intentional_updates": 14, "unchanged_count": 2020,
                                  "main_after_sha256": main_after, "private_after_sha256": private_after,
                                  "main_before_fingerprint": fingerprint(main_before),
                                  "private_original_fingerprint": fingerprint(private_before),
                                  "main_private_current_fingerprint": fingerprint(expected)},
                      art457={"count": 457, "hashes_unchanged": True, "main_before_cas_unchanged": True,
                              "original_sha256": art_before},
                      fresh_monster_vfx_saved_and_runtime_validation_required=True)
        data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        write_new(REPORT, data, OUT)
        write_new(MIRROR, data, PRIVATE_OUT)
        require(sha(REPORT) == sha(MIRROR), "Revision mirrors differ")
        return result
    except Exception:
        # Restore only this task's exact copied bytes. Never overwrite a third-party change.
        for r in reversed(copied):
            target = physical(WORK / r["relative"], WORK)
            require(sha(target) == r["after_sha256"], f"Rollback CAS conflict: {target}")
            target.write_bytes(Path(r["backup_path"]).read_bytes())
            require(sha(target) == r["prior_private_sha256"], f"Rollback SHA mismatch: {target}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply the exact approved private byte intake")
    args = parser.parse_args()
    proof = run(args.apply)
    print(json.dumps({"status": proof["status"], "content_scope": proof["content_scope"],
                      "content_files_copied": proof["content_files_copied"], "main_mutations": 0,
                      "report": str(REPORT) if args.apply else None}, ensure_ascii=False))
