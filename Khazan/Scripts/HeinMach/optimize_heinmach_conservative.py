"""Conservatively remove only provably redundant HeinMach prop actors.

The live map contains environment layers that overlap by design.  This pass
does not infer visibility from names, distance, bounds, or collision tags.  It
only removes a managed root prop when another managed root prop has the exact
same mesh, resolved materials, transform, render state, and collision state.

Run ``main(False)`` for a read-only audit and ``main(True)`` to apply.  Every
removed label is written to a report so it can be persisted as a restoration
tombstone before any reconstruction script is run again.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_ConservativeOptimization.json",
)
USER_EXCLUSIONS_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_UserExclusions.json",
)
MANAGED_LABEL_PREFIX = "HM_Prop_"
MAX_REPORT_GROUPS = 500


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def object_path(value):
    return value.get_path_name() if value else None


def round_float(value, digits=6):
    value = float(value)
    if abs(value) < 10.0 ** (-digits):
        value = 0.0
    return round(value, digits)


def canonical_quaternion(rotation):
    quaternion = rotation.quaternion()
    values = [
        float(quaternion.x),
        float(quaternion.y),
        float(quaternion.z),
        float(quaternion.w),
    ]
    for value in values:
        if abs(value) > 1.0e-8:
            if value < 0.0:
                values = [-item for item in values]
            break
    return tuple(round_float(item, 7) for item in values)


def vector_key(value):
    return tuple(round_float(item, 4) for item in (value.x, value.y, value.z))


def component_state(component):
    materials = tuple(
        object_path(component.get_material(slot_index))
        for slot_index in range(component.get_num_materials())
    )
    collision_profile = None
    try:
        collision_profile = str(component.get_collision_profile_name())
    except Exception:
        collision_profile = str(safe_property(component, "collision_profile_name", ""))
    return {
        "mesh": object_path(safe_property(component, "static_mesh")),
        "materials": materials,
        "visible": bool(safe_property(component, "visible", True)),
        "hidden_in_game": bool(safe_property(component, "hidden_in_game", False)),
        "cast_shadow": bool(safe_property(component, "cast_shadow", True)),
        "reverse_culling": bool(safe_property(component, "reverse_culling", False)),
        "receives_decals": bool(safe_property(component, "receives_decals", True)),
        "render_in_main_pass": bool(
            safe_property(component, "render_in_main_pass", True)
        ),
        "render_in_depth_pass": bool(
            safe_property(component, "render_in_depth_pass", True)
        ),
        "visible_in_ray_tracing": bool(
            safe_property(component, "visible_in_ray_tracing", True)
        ),
        "collision_enabled": str(component.get_collision_enabled()),
        "collision_profile": collision_profile,
        "mobility": str(safe_property(component, "mobility", "")),
    }


def actor_record(actor):
    components = list(actor.get_components_by_class(unreal.StaticMeshComponent))
    if len(components) != 1:
        return None, "static_mesh_component_count_{}".format(len(components))
    tags = tuple(sorted(str(tag) for tag in (safe_property(actor, "tags", []) or [])))
    if tags:
        return None, "actor_has_tags"
    component = components[0]
    state = component_state(component)
    if not state["mesh"]:
        return None, "static_mesh_missing"
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    try:
        actor_collision = bool(actor.get_actor_enable_collision())
    except Exception:
        actor_collision = True
    record = {
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_path_name(),
        "location": vector_key(location),
        "rotation_quaternion": canonical_quaternion(rotation),
        "scale": vector_key(scale),
        "actor_collision": actor_collision,
        "component": state,
    }
    return record, None


def strict_key(record):
    state = record["component"]
    return (
        record["class"],
        record["location"],
        record["rotation_quaternion"],
        record["scale"],
        record["actor_collision"],
        state["mesh"],
        state["materials"],
        state["visible"],
        state["hidden_in_game"],
        state["cast_shadow"],
        state["reverse_culling"],
        state["receives_decals"],
        state["render_in_main_pass"],
        state["render_in_depth_pass"],
        state["visible_in_ray_tracing"],
        state["collision_enabled"],
        state["collision_profile"],
        state["mobility"],
    )


def visual_key(record):
    state = record["component"]
    return (
        record["location"],
        record["rotation_quaternion"],
        record["scale"],
        state["mesh"],
        state["materials"],
        state["visible"],
        state["hidden_in_game"],
        state["reverse_culling"],
    )


def keeper_priority(record):
    label = record["label"]
    # The opening DualAxeSword tutorial space lives in SubLV01_OP.  Prefer its
    # authored copy when a later streaming layer contains the same instance.
    tutorial_source_priority = 0 if "_HeinMach_SubLV01_OP_" in label else 1
    return tutorial_source_priority, label


def group_payload(records):
    ordered = sorted(records, key=keeper_priority)
    keeper = ordered[0]
    removals = ordered[1:]
    state = keeper["component"]
    return {
        "keep_label": keeper["label"],
        "remove_labels": [record["label"] for record in removals],
        "mesh": state["mesh"],
        "materials": list(state["materials"]),
        "location": list(keeper["location"]),
        "rotation_quaternion": list(keeper["rotation_quaternion"]),
        "scale": list(keeper["scale"]),
        "collision_enabled": state["collision_enabled"],
        "collision_profile": state["collision_profile"],
    }


def signature(labels):
    encoded = json.dumps(sorted(labels), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def user_exclusion_labels():
    payload = load_json(USER_EXCLUSIONS_PATH, {}) or {}
    return {
        str(record.get("label"))
        for record in payload.get("exclusions", [])
        if record.get("do_not_restore") and record.get("label")
    }


def load_level_if_needed():
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if world and world.get_path_name().startswith(MAP_PATH + "."):
        return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach environment map")
    return level_subsystem


def main(apply_changes=False):
    level_subsystem = load_level_if_needed()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    by_label = {actor.get_actor_label(): actor for actor in all_actors}

    exclusions = user_exclusion_labels()
    resurrected = sorted(exclusions.intersection(by_label))
    if resurrected:
        raise RuntimeError(
            "User-deleted actor unexpectedly exists: {}".format(resurrected[0])
        )

    managed = [
        actor
        for actor in all_actors
        if actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    ]
    records = []
    skipped = collections.Counter()
    record_by_label = {}
    for actor in managed:
        record, reason = actor_record(actor)
        if reason:
            skipped[reason] += 1
            continue
        records.append(record)
        record_by_label[record["label"]] = record

    strict_groups = collections.defaultdict(list)
    visual_groups = collections.defaultdict(list)
    for record in records:
        strict_groups[strict_key(record)].append(record)
        visual_groups[visual_key(record)].append(record)
    strict_duplicates = [group for group in strict_groups.values() if len(group) > 1]
    visual_duplicates = [group for group in visual_groups.values() if len(group) > 1]
    groups = sorted(
        (group_payload(group) for group in strict_duplicates),
        key=lambda item: (item["keep_label"], item["remove_labels"]),
    )
    remove_labels = [
        label for group in groups for label in group["remove_labels"]
    ]
    keep_labels = [group["keep_label"] for group in groups]
    if set(remove_labels).intersection(exclusions):
        raise RuntimeError("User exclusions entered the optimization removal set")
    if len(remove_labels) != len(set(remove_labels)):
        raise RuntimeError("Duplicate removal labels were generated")

    destroyed = []
    failures = []
    before_actor_count = len(all_actors)
    if apply_changes:
        for label in remove_labels:
            actor = by_label.get(label)
            if not actor:
                failures.append({"label": label, "error": "actor_missing"})
                continue
            try:
                result = actor_subsystem.destroy_actor(actor)
                if result is False:
                    failures.append({"label": label, "error": "destroy_returned_false"})
                else:
                    destroyed.append(label)
            except Exception as exception:
                failures.append({"label": label, "error": str(exception)})
        if failures:
            raise RuntimeError("Actor deletion failed: {}".format(failures[0]))
        remaining_labels = {
            actor.get_actor_label()
            for actor in actor_subsystem.get_all_level_actors()
            if actor
        }
        undeleted = sorted(set(remove_labels).intersection(remaining_labels))
        lost_keepers = sorted(set(keep_labels) - remaining_labels)
        if undeleted or lost_keepers:
            raise RuntimeError(
                "Optimization validation failed: undeleted={} lost_keepers={}".format(
                    undeleted[:3], lost_keepers[:3]
                )
            )
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save optimized HeinMach map")

    final_actor_count = len(
        [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    )
    report = {
        "status": "optimized" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "policy": {
            "deletion_scope": "HM_Prop_ actors with one StaticMeshComponent",
            "proof_required": (
                "Exact mesh, resolved materials, transform, visibility, render flags, "
                "shadow, reverse culling, mobility, and collision state"
            ),
            "never_delete_by": [
                "name containing Collision",
                "distance from route",
                "occlusion guess",
                "source layer name alone",
            ],
            "tutorial_keeper_priority": "HeinMach_SubLV01_OP",
        },
        "apply_changes": bool(apply_changes),
        "counts": {
            "all_actor_before": before_actor_count,
            "managed_prop_actor": len(managed),
            "eligible_actor": len(records),
            "visual_duplicate_group": len(visual_duplicates),
            "visual_redundant_actor": sum(len(group) - 1 for group in visual_duplicates),
            "strict_duplicate_group": len(groups),
            "strict_redundant_actor": len(remove_labels),
            "destroyed_actor": len(destroyed),
            "all_actor_after": final_actor_count,
        },
        "skipped_actor_reasons": dict(sorted(skipped.items())),
        "user_exclusion_count": len(exclusions),
        "user_exclusions_resurrected": resurrected,
        "removal_label_sha256": signature(remove_labels),
        "removed_labels": destroyed if apply_changes else [],
        "planned_remove_labels": remove_labels,
        "duplicate_groups": groups[:MAX_REPORT_GROUPS],
        "report_group_truncated": len(groups) > MAX_REPORT_GROUPS,
        "failures": failures,
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    try:
        main(False)
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        raise
