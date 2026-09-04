#!/usr/bin/env python3
"""Audit visible StormPass child StaticMeshComponents with Fog/HISM deferred."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SHARED_SCRIPT = (
    PROJECT_ROOT / "Scripts" / "HeinMach" / "audit_heinmach_child_template_coverage.py"
)
SCOPE_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_SourceScope.json"
)


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_child_template_coverage", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared child-template audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    with SCOPE_PATH.open("r", encoding="utf-8-sig") as source:
        scope = json.load(source)
    shared.PROPERTIES_ROOT = (
        shared.FMODEL_ROOT
        / "Exports"
        / "BBQ"
        / "Content"
        / "_Kazan_"
        / "Level"
        / "StormPass"
    )
    shared.LEVEL_PACKAGE_ROOT = "BBQ/Content/_Kazan_/Level/StormPass"
    shared.OLD_GAP_REPORT = (
        PROJECT_ROOT / "Saved" / "ImportReports" / "StormPass_Render_Gap_Analysis.json"
    )
    shared.REPORT_PATH = (
        PROJECT_ROOT
        / "Saved"
        / "ImportReports"
        / "StormPass_ChildTemplateCoverage_Audit.json"
    )
    shared.root.ENVIRONMENT_LEVELS = set(scope.get("visual_levels", []))
    payload = shared.audit()
    shared.write_json(shared.REPORT_PATH, payload)
    print(
        json.dumps(
            {"summary": payload["summary"], "report": str(shared.REPORT_PATH)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return payload


if __name__ == "__main__":
    main()
