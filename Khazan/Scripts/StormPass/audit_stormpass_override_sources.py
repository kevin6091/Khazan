"""Audit raw FModel sources required by StormPass actor material overrides."""

from __future__ import annotations

import importlib.util
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
SHARED_SCRIPT = os.path.join(
    PROJECT_ROOT,
    "Scripts",
    "HeinMach",
    "audit_heinmach_inherited_override_sources.py",
)


def load_shared():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_override_source_audit", SHARED_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared override-source audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    shared = load_shared()
    shared.RESTORATION_REPORT = (
        shared.Path(PROJECT_ROOT)
        / "Saved"
        / "ImportReports"
        / "StormPass_StaticMesh_Reconstruction.json"
    )
    shared.REPORT_PATH = (
        shared.Path(PROJECT_ROOT)
        / "Saved"
        / "ImportReports"
        / "StormPass_OverrideSource_Audit.json"
    )
    shared.main()


if __name__ == "__main__":
    main()
