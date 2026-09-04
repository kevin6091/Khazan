"""Read-only integrity audit for the 57 restored HeinMach Landscape proxies.

The source inventory is limited to the two cached Landscape JSON files and does
not repeat a project/FModel-wide scan.  Actor transforms, component mesh bounds,
material, collision, reverse-culling state, and the Fog boundary are validated.
"""

from __future__ import annotations

import importlib.util
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESTORE_PATH = os.path.join(
    SCRIPT_DIR, "restore_heinmach_landscape_static_meshes.py"
)


def load_restore_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_landscape_restore_helpers", RESTORE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Landscape restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_restore_module()
REPORT_PATH = os.path.join(
    restore.PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_LandscapeStatic_Integrity_Audit.json",
)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(restore.MAP_PATH + "."):
        if not level_subsystem.load_level(restore.MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    landscapes, source_records = restore.load_landscape_inventory()
    records = restore.filter_excluded_records(source_records)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = list(actor_subsystem.get_all_level_actors())
    managed = [
        actor
        for actor in all_actors
        if actor and actor.get_actor_label().startswith(restore.MANAGED_LABEL_PREFIX)
    ]
    labels = {}
    for actor in managed:
        labels.setdefault(actor.get_actor_label(), []).append(actor)
    expected_labels = {restore.managed_label(record) for record in records}
    missing = sorted(expected_labels - set(labels))
    unexpected = sorted(set(labels) - expected_labels)
    duplicates = sorted(label for label, actors in labels.items() if len(actors) != 1)

    bound_failures = []
    for record in records:
        mesh = restore.component_mesh(record)
        if not mesh:
            bound_failures.append(
                {"label": restore.managed_label(record), "issues": ["mesh_missing"]}
            )
            continue
        valid, detail = restore.validate_mesh_bound(record, mesh)
        if not valid:
            detail["label"] = restore.managed_label(record)
            bound_failures.append(detail)

    placement_failures = []
    material = unreal.load_asset(restore.MATERIAL_PATH)
    if not missing and not unexpected and not duplicates and material:
        unique_actors = {label: actors[0] for label, actors in labels.items()}
        placement_failures = restore.validate_placements(
            records, unique_actors, material
        )
    elif not material:
        placement_failures.append(
            {"label": restore.MATERIAL_PATH, "issues": ["recovery_material_missing"]}
        )

    fog = restore.fog_signature(actor_subsystem)
    fog_valid = bool(
        fog.get("count") == restore.EXPECTED_FOG_COUNT
        and fog.get("sha256") == restore.EXPECTED_FOG_SHA256
    )
    failures = {
        "missing_labels": missing,
        "unexpected_labels": unexpected,
        "duplicate_labels": duplicates,
        "bound_failures": bound_failures,
        "placement_failures": placement_failures,
    }
    passed = bool(
        len(source_records) == restore.EXPECTED_TOTAL_COMPONENT_COUNT
        and len(managed) == len(records)
        and not any(failures.values())
        and fog_valid
    )
    payload = {
        "status": "passed" if passed else "failed",
        "map_path": restore.MAP_PATH,
        "source_scope": [item["source_json"] for item in landscapes],
        "counts": {
            "source_component_count": len(source_records),
            "active_component_count": len(records),
            "excluded_component_count": len(source_records) - len(records),
            "managed_actor_count": len(managed),
            "landscape1_component_count": sum(
                1 for record in records if record["landscape_name"] == "Landscape1"
            ),
            "landscape2_component_count": sum(
                1 for record in records if record["landscape_name"] == "Landscape2"
            ),
            "bound_failure_count": len(bound_failures),
            "placement_failure_count": len(placement_failures),
        },
        "fog_boundary": {
            "status": "unchanged" if fog_valid else "changed",
            "current": fog,
            "expected": {
                "count": restore.EXPECTED_FOG_COUNT,
                "sha256": restore.EXPECTED_FOG_SHA256,
            },
        },
        "failures": failures,
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({"report": REPORT_PATH, **payload}, ensure_ascii=False, indent=2))
    if not passed:
        raise RuntimeError("Landscape static restoration integrity audit failed")
    return payload


if __name__ == "__main__":
    main()
