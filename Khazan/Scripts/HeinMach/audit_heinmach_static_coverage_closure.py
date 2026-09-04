"""Close HeinMach static-environment coverage from existing canonical reports.

This is intentionally a report-only aggregation.  It does not rescan Content or
the FModel export root.  Its purpose is to distinguish genuinely unresolved
non-Fog StaticMesh props from navigation, brush, spline, decal, gameplay and
other non-static actor records in the root-template audit.
"""

from __future__ import annotations

import collections
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
REPORT_ROOT = os.path.join(PROJECT_ROOT, "Saved", "ImportReports")
SOURCE_PATHS = {
    "root": os.path.join(REPORT_ROOT, "HeinMach_RootTemplateCoverage_Audit.json"),
    "child": os.path.join(REPORT_ROOT, "HeinMach_ChildTemplateCoverage_Audit.json"),
    "foliage": os.path.join(REPORT_ROOT, "HeinMach_Foliage_Reload_Audit.json"),
    "landscape": os.path.join(REPORT_ROOT, "HeinMach_LandscapeStatic_Integrity_Audit.json"),
    "material": os.path.join(REPORT_ROOT, "HeinMach_MaterialRendering_Audit.json"),
    "final": os.path.join(REPORT_ROOT, "HeinMach_Final_Reconstruction_Audit.json"),
}
REPORT_PATH = os.path.join(
    REPORT_ROOT, "HeinMach_StaticCoverage_Closure_Audit.json"
)
FOG_ACTOR_TYPE = "WBP_FogSheet_C"


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def main():
    sources = {name: load_json(path) for name, path in SOURCE_PATHS.items()}
    root = sources["root"]
    child = sources["child"]
    foliage = sources["foliage"]
    landscape = sources["landscape"]
    material = sources["material"]
    final = sources["final"]

    unresolved = list(root.get("unresolved_root_actors") or [])
    component_types = collections.Counter(
        str(row.get("root_component_type")) for row in unresolved
    )
    actor_types = collections.Counter(str(row.get("actor_type")) for row in unresolved)
    unresolved_static = [
        row for row in unresolved if row.get("root_component_type") == "StaticMeshComponent"
    ]
    unresolved_non_fog_static = [
        row for row in unresolved_static if row.get("actor_type") != FOG_ACTOR_TYPE
    ]

    root_summary = root.get("summary") or {}
    child_summary = child.get("summary") or {}
    foliage_checks = (
        foliage.get("status") == "restored"
        and int(foliage.get("final_batch_actor_count", 0)) == 113
        and int(foliage.get("final_instance_count", 0)) == 12495
        and not foliage.get("mesh_mismatches")
        and not foliage.get("instance_count_mismatches")
        and not foliage.get("instance_transform_mismatches")
        and not foliage.get("actor_transform_mismatches")
        and not foliage.get("material_mismatches")
    )
    checks = {
        "root_non_fog_static_mesh_unresolved_zero": not unresolved_non_fog_static,
        "root_static_mesh_usd_missing_zero": int(
            root_summary.get("missing_usd_static_mesh_count", 1)
        )
        == 0,
        "child_static_mesh_unresolved_zero": int(
            child_summary.get("unresolved_component_count", 1)
        )
        == 0,
        "child_static_mesh_usd_missing_zero": int(
            child_summary.get("missing_usd_static_mesh_count", 1)
        )
        == 0,
        "foliage_batches_and_transforms_passed": foliage_checks,
        "landscape_components_passed": landscape.get("status") == "passed",
        "material_surface_translucency_gap_zero": int(
            (material.get("counts") or {}).get("effective_blend_translucent", 1)
        )
        == 0,
        "integrated_live_map_passed": bool(final.get("all_checks_passed")),
    }
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "mismatch",
        "scope": (
            "HeinMach static environment: root/child StaticMesh, foliage HISM, "
            "Landscape static proxies and live material surfaces; Fog excluded"
        ),
        "source_reports": SOURCE_PATHS,
        "checks": checks,
        "root_coverage": {
            "source_root_component_actor_count": int(
                root_summary.get("root_component_actor_count", 0)
            ),
            "resolved_visible_root_static_mesh_count": int(
                root_summary.get("resolved_visible_root_placement_count", 0)
            ),
            "resolved_unique_static_mesh_count": int(
                root_summary.get("resolved_unique_static_mesh_count", 0)
            ),
            "unresolved_root_record_count": len(unresolved),
            "unresolved_root_component_types": dict(component_types.most_common()),
            "unresolved_root_actor_types": dict(actor_types.most_common()),
            "unresolved_root_static_mesh_count": len(unresolved_static),
            "unresolved_fog_static_mesh_count": sum(
                row.get("actor_type") == FOG_ACTOR_TYPE for row in unresolved_static
            ),
            "unresolved_non_fog_static_mesh_count": len(unresolved_non_fog_static),
            "interpretation": (
                "All unresolved root StaticMeshComponent records are the 50 Fog "
                "sheets kept outside this request. Remaining unresolved root "
                "records are non-static component/actor types."
            ),
        },
        "child_coverage": {
            "resolved_visible_child_static_mesh_count": int(
                child_summary.get(
                    "resolved_visible_non_foliage_non_fog_child_mesh_count", 0
                )
            ),
            "direct_count": int(child_summary.get("direct_level_child_mesh_count", 0)),
            "inherited_count": int(
                child_summary.get("inherited_template_child_mesh_count", 0)
            ),
            "unresolved_count": int(child_summary.get("unresolved_component_count", 0)),
        },
        "foliage_coverage": {
            "batch_actor_count": int(foliage.get("final_batch_actor_count", 0)),
            "instance_count": int(foliage.get("final_instance_count", 0)),
        },
        "landscape_coverage": landscape.get("counts") or {},
        "live_inventory": final.get("inventory") or {},
        "limitations": [
            "Original WLM/weightmap layer graph is unavailable; Landscape uses a recovery material.",
            "Dynamic skeletal props, decals, gameplay volumes/spawners and VFX are not StaticMesh placement gaps.",
            "Fog actors/assets are deliberately unchanged and outside this request.",
        ],
    }
    write_json(REPORT_PATH, payload)
    print(
        json.dumps(
            {
                "report": REPORT_PATH,
                "status": payload["status"],
                "root_static": payload["root_coverage"]["resolved_visible_root_static_mesh_count"],
                "unresolved_non_fog_static": len(unresolved_non_fog_static),
                "child_static": payload["child_coverage"]["resolved_visible_child_static_mesh_count"],
            }
        )
    )
    if payload["status"] != "passed":
        raise RuntimeError("Static coverage closure has mismatches")


if __name__ == "__main__":
    main()
