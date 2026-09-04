"""Resolve StormPass root render meshes through exported Blueprint templates."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SHARED_SCRIPT = (
    SCRIPT_DIR.parent / "HeinMach" / "audit_heinmach_root_template_coverage.py"
)
FMODEL_ROOT = Path.home() / "Desktop" / "카잔"
PROPERTIES_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
METADATA_ROOT = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
)
SCOPE_PATH = METADATA_ROOT / "StormPass_SourceScope.json"
DIRECT_MANIFEST_PATH = METADATA_ROOT / "StormPass_DirectStaticMeshPlacements.json"
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_RootTemplateCoverage_Audit.json"
)
PLACEMENT_PATH = METADATA_ROOT / "StormPass_ResolvedRootPlacements.json"


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_root_template_helpers", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load root-template coverage helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    scope = shared.load_json(SCOPE_PATH)
    visual_levels = set(scope.get("visual_levels", []))
    if not visual_levels:
        raise RuntimeError("StormPass visual-level scope is empty")
    shared.ENVIRONMENT_LEVELS = visual_levels
    args = SimpleNamespace(
        fmodel_root=FMODEL_ROOT,
        properties_dir=PROPERTIES_ROOT,
        existing_manifest=DIRECT_MANIFEST_PATH,
        package_root="BBQ/Content/_Kazan_/Level/StormPass",
    )
    report = shared.audit(args)
    report["level"] = "StormPass"
    report["scope"]["content_boundary"] = scope.get("content_boundary")
    report["scope"]["fog_policy"] = scope.get("fog_policy")
    report["scope"]["source_scope"] = str(SCOPE_PATH)
    shared.write_json(REPORT_PATH, report)
    shared.write_json(
        PLACEMENT_PATH,
        {
            "schema_version": 1,
            "level": "StormPass",
            "generated_at": report["generated_at"],
            "fog_excluded": True,
            "placements": report["resolved_root_placements"],
        },
    )
    print(
        "KHAZAN_STORMPASS_ROOT_TEMPLATE_AUDIT "
        + json.dumps(report["summary"], ensure_ascii=False, sort_keys=True)
    )
    return report


if __name__ == "__main__":
    main()
