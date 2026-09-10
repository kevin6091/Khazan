"""Remove only interrupted BigBear import staging assets.

Run this in a fresh Unreal process so no mesh or skeleton object from an earlier
upgrade step is still referenced by Python locals.
"""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = PROJECT / "Saved/ImportReports/BigBear_TemporaryAssetCleanup_20260910.json"
ROOT = "/Game/_Art/Enemies/Shared/Beasts/BigBear"
TEMP_ROOTS = [ROOT + "/_ImportStaging", ROOT + "/_ImportStaging79V1", ROOT + "/_UpgradeBackup"]
EAL = unreal.EditorAssetLibrary


def main() -> None:
    report = {"status": "running", "deleted": []}
    try:
        for root in TEMP_ROOTS:
            assets = [str(value) for value in EAL.list_assets(root, recursive=True, include_folder=False)]
            for object_path in assets:
                package_path = object_path.split(".", 1)[0]
                if not package_path.startswith(root + "/"):
                    raise RuntimeError("Refusing unexpected cleanup path " + package_path)
                if not EAL.delete_asset(package_path):
                    raise RuntimeError("Unable to delete temporary asset " + package_path)
                report["deleted"].append(package_path)
            EAL.delete_directory(root)

        remaining = {
            root: [str(value) for value in EAL.list_assets(root, recursive=True, include_folder=False)]
            for root in TEMP_ROOTS
        }
        if any(remaining.values()):
            raise RuntimeError("Temporary assets remain: " + json.dumps(remaining))
        report.update({"status": "passed", "remaining": remaining})
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("BIG_BEAR_TEMPORARY_ASSET_CLEANUP_PASSED", flush=True)


if __name__ == "__main__":
    main()
