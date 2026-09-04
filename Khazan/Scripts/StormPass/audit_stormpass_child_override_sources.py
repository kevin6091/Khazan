"""Audit FModel sources for StormPass child-only material overrides."""

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
CHILD_AUDIT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_ChildTemplateCoverage_Audit.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_ChildOverrideSource_Audit.json"
)


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_child_override_source_audit", SHARED_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared override-source audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    child = shared.load_json(CHILD_AUDIT_PATH)
    required = {
        str(package)
        for record in child.get("resolved_child_mesh_components", [])
        for package in record.get("override_material_packages", [])
        if package
    }
    root_report = shared.load_json(
        PROJECT_ROOT
        / "Saved"
        / "ImportReports"
        / "StormPass_OverrideMaterial_Restoration.json"
    )
    rebuilt = {
        item["package"] for item in root_report.get("material_results", [])
    }
    imported_names = {
        "WM_Castle_Ceiling_Base_002_a",
        "WM_Castle_Pillar_004",
    }
    unresolved = {
        package
        for package in required
        if package not in rebuilt and package.rsplit("/", 1)[-1] not in imported_names
    }
    shared.RESTORATION_REPORT = CHILD_AUDIT_PATH
    shared.REPORT_PATH = REPORT_PATH
    shared.PACKAGES_OVERRIDE = unresolved
    shared.main()
    report = shared.load_json(REPORT_PATH)
    report["required_child_override_packages"] = sorted(required)
    report["already_resolved_packages"] = sorted(required - unresolved)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    return report


if __name__ == "__main__":
    main()
