"""Add Player/Monster respawn TargetPoints without touching current world art.

The user's saved PlayerStart transform and current StaticMeshActor set are
preserved as hard preconditions.  The script creates one Player respawn marker,
reuses the two existing tutorial Monster markers, creates the remaining original
Monster spawn markers, and saves only after all in-memory preservation checks
pass.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import shutil
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment"
MAP_FILE = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Player",
    "Environment",
    "HeinMach",
    "Maps",
    "L_HeinMach_Environment.umap",
)
LEVEL_DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Player",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_LevelData.json",
)
PREFLIGHT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RespawnTarget_Preflight_20260930.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RespawnTarget_Apply_20260930.json",
)
BACKUP_ROOT = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ArtBackups",
    "HeinMach_RespawnTargets_PreApply_20260930",
)

PLAYER_START_LABEL = "HM_Tutorial_PlayerStart_DualAxeSword"
PLAYER_RESPAWN_LABEL = "HM_PlayerRespawn_WeaponTutorial"
MONSTER_PREFIX = "HM_MonsterRespawn_"
PLAYER_FOLDER = "HeinMach/Gameplay/RespawnTargets/Player"
MONSTER_FOLDER = "HeinMach/Gameplay/RespawnTargets/Monsters"
COMMON_MONSTER_TAG = "HeinMachMonsterRespawn"
TUTORIAL_EXISTING_TARGETS = {
    "SA_EmpireSword_Early3_Item": "HM_TutorialSpawn_01_EmpireSword",
    "SA_Empire_SwordShield_2": "HM_TutorialSpawn_02_EmpireSwordShield",
}
LOCATION_TOLERANCE_CM = 0.1
ROTATION_TOLERANCE_DEGREES = 0.1


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def actor_label(actor):
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def vector_payload(value):
    return [float(value.x), float(value.y), float(value.z)]


def rotator_payload(value):
    return [float(value.pitch), float(value.yaw), float(value.roll)]


def transform_payload(actor):
    return {
        "location_cm": vector_payload(actor.get_actor_location()),
        "rotation_degrees": rotator_payload(actor.get_actor_rotation()),
        "scale": vector_payload(actor.get_actor_scale3d()),
    }


def vector_from_list(values):
    return unreal.Vector(
        x=float(values[0]), y=float(values[1]), z=float(values[2])
    )


def vector_from_record(record):
    value = record["transform"]["location_cm"]
    return unreal.Vector(x=float(value["x"]), y=float(value["y"]), z=float(value["z"]))


def rotator_from_record(record):
    value = record["transform"]["rotation_degrees"]
    return unreal.Rotator(
        pitch=float(value["pitch"]),
        yaw=float(value["yaw"]),
        roll=float(value["roll"]),
    )


def spatial_distance(a, b):
    return math.sqrt(
        (float(a.x) - float(b.x)) ** 2
        + (float(a.y) - float(b.y)) ** 2
        + (float(a.z) - float(b.z)) ** 2
    )


def normalized_angle_delta(a, b):
    return (float(a) - float(b) + 180.0) % 360.0 - 180.0


def rotation_delta(a, b):
    return max(
        abs(normalized_angle_delta(a.pitch, b.pitch)),
        abs(normalized_angle_delta(a.yaw, b.yaw)),
        abs(normalized_angle_delta(a.roll, b.roll)),
    )


def set_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def merge_tags(actor, values):
    current = [str(value) for value in actor.get_editor_property("tags")]
    merged = list(current)
    for value in values:
        if value not in merged:
            merged.append(value)
    actor.set_editor_property("tags", [unreal.Name(value) for value in merged])
    return current, merged


def load_level():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")
        world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()
    return level_subsystem, world


def transforms_match(left, right, tolerance=0.0001):
    for field in ("location_cm", "rotation_degrees", "scale"):
        for a, b in zip(left[field], right[field]):
            if abs(float(a) - float(b)) > tolerance:
                return False
    return True


def main():
    preflight = load_json(PREFLIGHT_PATH)
    if preflight.get("status") not in {
        "passed",
        "passed_with_runtime_surface_unverified",
    }:
        raise RuntimeError("Respawn preflight is not usable")
    level_data = load_json(LEVEL_DATA_PATH)
    map_hash_before = sha256(MAP_FILE)

    level_subsystem, _world = load_level()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    before_by_label = {actor_label(actor): actor for actor in before_actors}
    before_by_path = {actor.get_path_name(): actor for actor in before_actors}
    before_transforms = {
        path: transform_payload(actor) for path, actor in before_by_path.items()
    }
    before_static_count = sum(
        1 for actor in before_actors if isinstance(actor, unreal.StaticMeshActor)
    )

    player_start = before_by_label.get(PLAYER_START_LABEL)
    if not player_start or not isinstance(player_start, unreal.PlayerStart):
        raise RuntimeError("Current user PlayerStart is missing")
    expected_start = preflight["current_player_start"]
    expected_location = vector_from_list(expected_start["location_cm"])
    expected_rotation = unreal.Rotator(
        pitch=float(expected_start["rotation_degrees"][0]),
        yaw=float(expected_start["rotation_degrees"][1]),
        roll=float(expected_start["rotation_degrees"][2]),
    )
    if spatial_distance(player_start.get_actor_location(), expected_location) > 0.01:
        raise RuntimeError("PlayerStart moved after preflight; rerun read-only preflight")
    if rotation_delta(player_start.get_actor_rotation(), expected_rotation) > 0.01:
        raise RuntimeError("PlayerStart rotated after preflight; rerun read-only preflight")

    proposal = preflight["player_respawn_target"]["proposed_candidate"]
    proposal_values = proposal.get("target_location_cm") or proposal.get(
        "spawn_center_cm"
    )
    if not proposal_values:
        raise RuntimeError("Preflight did not produce a Player respawn proposal")
    player_target_location = vector_from_list(proposal_values)
    player_target_rotation = player_start.get_actor_rotation()

    monster_records = sorted(
        list(level_data.get("monster_spawns", [])),
        key=lambda record: int(record.get("source_object_index", -1)),
    )
    if len(monster_records) != 47:
        raise RuntimeError("Original Monster spawn count is not 47")

    specifications = []
    for record in monster_records:
        source_name = record["actor_name"]
        source_index = int(record["source_object_index"])
        label = TUTORIAL_EXISTING_TARGETS.get(
            source_name,
            "{}{:04d}_{}".format(MONSTER_PREFIX, source_index, source_name),
        )
        existing = before_by_label.get(label)
        if existing and not isinstance(existing, unreal.TargetPoint):
            raise RuntimeError("Respawn target label has wrong class: " + label)
        if source_name in TUTORIAL_EXISTING_TARGETS and not existing:
            raise RuntimeError("Existing tutorial TargetPoint is missing: " + label)
        if existing:
            if (
                spatial_distance(existing.get_actor_location(), vector_from_record(record))
                > LOCATION_TOLERANCE_CM
            ):
                raise RuntimeError(
                    "Existing TargetPoint transform differs from source: " + label
                )
        specifications.append((record, label, existing))

    existing_player_target = before_by_label.get(PLAYER_RESPAWN_LABEL)
    if existing_player_target and not isinstance(
        existing_player_target, unreal.TargetPoint
    ):
        raise RuntimeError("Player respawn label has wrong class")
    if existing_player_target:
        if (
            spatial_distance(
                existing_player_target.get_actor_location(), player_target_location
            )
            > LOCATION_TOLERANCE_CM
        ):
            raise RuntimeError("Existing Player respawn target differs from proposal")

    os.makedirs(BACKUP_ROOT, exist_ok=True)
    backup_file = os.path.join(BACKUP_ROOT, os.path.basename(MAP_FILE))
    if not os.path.isfile(backup_file):
        shutil.copy2(MAP_FILE, backup_file)
    backup_hash = sha256(backup_file)
    if backup_hash != map_hash_before:
        raise RuntimeError(
            "Existing pre-apply backup does not match the current saved map"
        )

    created_labels = []
    reused_labels = []
    tutorial_tag_changes = []

    if existing_player_target:
        player_target = existing_player_target
        reused_labels.append(PLAYER_RESPAWN_LABEL)
    else:
        player_target = actor_subsystem.spawn_actor_from_class(
            unreal.TargetPoint, player_target_location, player_target_rotation
        )
        if not player_target:
            raise RuntimeError("Failed to create Player respawn TargetPoint")
        player_target.set_actor_label(PLAYER_RESPAWN_LABEL, mark_dirty=True)
        set_folder(player_target, PLAYER_FOLDER)
        created_labels.append(PLAYER_RESPAWN_LABEL)
    merge_tags(
        player_target,
        (
            "HeinMachPlayerRespawn",
            "WeaponTutorial",
            "UserPlayerStartNearby",
            "OriginalAutomationRoute",
            "RouteAction_{}".format(proposal.get("source_action_index")),
            "RoutePoint_{}".format(proposal.get("point_index")),
            "RuntimeSurfaceUnverified",
        ),
    )

    target_mapping = []
    for record, label, existing in specifications:
        source_name = record["actor_name"]
        source_index = int(record["source_object_index"])
        if existing:
            actor = existing
            reused_labels.append(label)
        else:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.TargetPoint,
                vector_from_record(record),
                rotator_from_record(record),
            )
            if not actor:
                raise RuntimeError("Failed to create Monster respawn target: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            set_folder(actor, MONSTER_FOLDER)
            created_labels.append(label)

        old_tags, new_tags = merge_tags(
            actor,
            (
                COMMON_MONSTER_TAG,
                "OriginalMetadataAnchor",
                "Source_{}".format(source_name),
                "SourceObject_{}".format(source_index),
            ),
        )
        if source_name in TUTORIAL_EXISTING_TARGETS and old_tags != new_tags:
            tutorial_tag_changes.append(
                {"label": label, "before": old_tags, "after": new_tags}
            )
        target_mapping.append(
            {
                "source_name": source_name,
                "source_object_index": source_index,
                "target_label": label,
                "location_cm": vector_payload(actor.get_actor_location()),
                "rotation_degrees": rotator_payload(actor.get_actor_rotation()),
                "created": not bool(existing),
            }
        )

    after_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    after_by_path = {actor.get_path_name(): actor for actor in after_actors}
    missing_preexisting = sorted(set(before_by_path) - set(after_by_path))
    if missing_preexisting:
        raise RuntimeError("Pre-existing actors disappeared before save")
    changed_preexisting_transforms = []
    for path, before_transform in before_transforms.items():
        after_transform = transform_payload(after_by_path[path])
        if not transforms_match(before_transform, after_transform):
            changed_preexisting_transforms.append(path)
    if changed_preexisting_transforms:
        raise RuntimeError("A pre-existing actor transform changed")
    after_static_count = sum(
        1 for actor in after_actors if isinstance(actor, unreal.StaticMeshActor)
    )
    if after_static_count != before_static_count:
        raise RuntimeError("StaticMeshActor count changed")
    if spatial_distance(player_start.get_actor_location(), expected_location) > 0.01:
        raise RuntimeError("PlayerStart moved during respawn targeting")
    if rotation_delta(player_start.get_actor_rotation(), expected_rotation) > 0.01:
        raise RuntimeError("PlayerStart rotated during respawn targeting")

    coverage = []
    for record, label, _existing in specifications:
        actor = next(
            (value for value in after_actors if actor_label(value) == label), None
        )
        if not actor:
            raise RuntimeError("Monster target missing before save: " + label)
        tags = [str(value) for value in actor.get_editor_property("tags")]
        source_tag = "Source_{}".format(record["actor_name"])
        if COMMON_MONSTER_TAG not in tags or source_tag not in tags:
            raise RuntimeError("Monster target tags are incomplete: " + label)
        if (
            spatial_distance(actor.get_actor_location(), vector_from_record(record))
            > LOCATION_TOLERANCE_CM
        ):
            raise RuntimeError("Monster target location mismatch: " + label)
        coverage.append(label)
    if len(set(coverage)) != 47:
        raise RuntimeError("Monster target coverage is not 47/47")

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach respawn TargetPoints")

    map_hash_after = sha256(MAP_FILE)
    report = {
        "schema_version": 1,
        "date": "2026-09-30",
        "status": "applied",
        "map": MAP_PATH,
        "map_sha256_before": map_hash_before,
        "map_sha256_after": map_hash_after,
        "backup_file": backup_file,
        "backup_sha256": backup_hash,
        "player_start_preserved": {
            "label": PLAYER_START_LABEL,
            "transform_before": before_transforms[player_start.get_path_name()],
            "transform_after": transform_payload(player_start),
        },
        "player_respawn_target": {
            "label": PLAYER_RESPAWN_LABEL,
            "transform": transform_payload(player_target),
            "proposal_basis": preflight["player_respawn_target"][
                "proposal_basis"
            ],
            "runtime_surface_validation": proposal.get(
                "runtime_surface_validation", "passed"
            ),
        },
        "monster_respawn_target_count": len(coverage),
        "monster_respawn_target_labels": coverage,
        "monster_target_mapping": target_mapping,
        "created_actor_count": len(created_labels),
        "created_labels": created_labels,
        "reused_labels": reused_labels,
        "tutorial_target_tag_changes": tutorial_tag_changes,
        "actor_count_before": len(before_actors),
        "actor_count_after": len(after_actors),
        "static_mesh_actor_count_before": before_static_count,
        "static_mesh_actor_count_after": after_static_count,
        "preexisting_actor_count": len(before_by_path),
        "missing_preexisting_actor_count": 0,
        "changed_preexisting_transform_count": 0,
        "preservation_contract": {
            "player_start_transform_changed": False,
            "static_mesh_actor_created_deleted_or_restored": False,
            "preexisting_actor_transform_changed": False,
            "existing_tutorial_target_transform_changed": False,
        },
        "runtime_boundary": (
            "TargetPoints are stable spawn anchors. Actual Player/Monster respawn "
            "execution and PIE surface validation remain gameplay integration work."
        ),
    }
    write_json(
        os.path.join(BACKUP_ROOT, "BackupManifest.json"),
        {
            "date": datetime.datetime.now().isoformat(),
            "source_map": MAP_FILE,
            "backup_file": backup_file,
            "sha256": backup_hash,
        },
    )
    write_json(REPORT_PATH, report)
    print("KZ_HEINMACH_RESPAWN_TARGETS_APPLIED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        write_json(
            REPORT_PATH,
            {
                "schema_version": 1,
                "date": "2026-09-30",
                "status": "failed",
                "error": traceback.format_exc(),
            },
        )
        raise
