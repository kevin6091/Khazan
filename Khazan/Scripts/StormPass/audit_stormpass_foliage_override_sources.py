"""Audit FModel sources for all StormPass Foliage material overrides."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SHARED_PATH = (
    PROJECT_ROOT
    / "Scripts"
    / "HeinMach"
    / "audit_heinmach_inherited_override_sources.py"
)
FOLIAGE_METADATA_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_FoliageInstances.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_FoliageOverrideSource_Audit.json"
)


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_foliage_override_source_audit", SHARED_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared material source audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    foliage = shared.load_json(FOLIAGE_METADATA_PATH)
    if foliage.get("status") != "passed":
        raise RuntimeError("StormPass Foliage source metadata is not passed")
    packages = {
        str(package)
        for component in foliage.get("components", [])
        for package in component.get("settings", {}).get(
            "override_material_packages", []
        )
        if package
    }
    if len(packages) != 5:
        raise RuntimeError(
            "StormPass Foliage override inventory changed: {}".format(len(packages))
        )
    shared.RESTORATION_REPORT = FOLIAGE_METADATA_PATH
    shared.REPORT_PATH = REPORT_PATH
    shared.PACKAGES_OVERRIDE = packages
    shared.main()
    report = shared.load_json(REPORT_PATH)
    report["required_foliage_override_packages"] = sorted(packages)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    return report


if __name__ == "__main__":
    main()
