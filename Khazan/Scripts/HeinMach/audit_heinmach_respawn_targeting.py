"""Read-only preflight for HeinMach Player and Monster respawn TargetPoints.

The current saved PlayerStart and the user's current map edits are authoritative.
This script never moves, creates, deletes, saves, or otherwise mutates an actor.
It evaluates nearby original automation-route points as Player respawn candidates
and builds the deterministic mapping for every original Monster spawn record.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
ROUTE_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_OriginalAutomationRoute.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RespawnTarget_Preflight_20260930.json",
)

PLAYER_START_LABEL = "HM_Tutorial_PlayerStart_DualAxeSword"
PLAYER_RESPAWN_LABEL = "HM_PlayerRespawn_WeaponTutorial"
MONSTER_PREFIX = "HM_MonsterRespawn_"
TUTORIAL_EXISTING_TARGETS = {
    "SA_EmpireSword_Early3_Item": "HM_TutorialSpawn_01_EmpireSword",
    "SA_Empire_SwordShield_2": "HM_TutorialSpawn_02_EmpireSwordShield",
}

# Measurement extents only. They do not become gameplay tuning values.
TRACE_UP_CM = 5000.0
TRACE_DOWN_CM = 10000.0
NAV_QUERY_EXTENT = unreal.Vector(x=150.0, y=150.0, z=1000.0)

# Existing documented temporary spawn clearance from the 2026-09-29
# HeinMach playability restoration. It remains explicit until replaced by an
# original value or a runtime spawn-collision policy.
SPAWN_CLEARANCE_CM = 8.0


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


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def vector_payload(value):
    if value is None:
        return None
    return [float(value.x), float(value.y), float(value.z)]


def rotator_payload(value):
    return [float(value.pitch), float(value.yaw), float(value.roll)]


def actor_label(actor):
    if not actor:
        return None
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def planar_distance(a, b):
    return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))


def spatial_distance(a, b):
    return math.sqrt(
        (float(a.x) - float(b.x)) ** 2
        + (float(a.y) - float(b.y)) ** 2
        + (float(a.z) - float(b.z)) ** 2
    )


def break_hit(hit):
    if not hit:
        return None
    values = unreal.get_default_object(unreal.GameplayStatics).call_method(
        "BreakHitResult", args=(hit,)
    )
    return {
        "blocking_hit": bool(values[0]),
        "initial_overlap": bool(values[1]),
        "distance_cm": float(values[3]),
        "location": values[4],
        "impact_point": values[5],
        "impact_normal": values[7],
        "actor": values[9],
        "component": values[10],
    }


def trace_surface(world, location):
    start = unreal.Vector(
        x=location.x, y=location.y, z=location.z + TRACE_UP_CM
    )
    end = unreal.Vector(
        x=location.x, y=location.y, z=location.z - TRACE_DOWN_CM
    )
    hit = unreal.SystemLibrary.line_trace_single_by_profile(
        world,
        start,
        end,
        "Pawn",
        True,
        [],
        unreal.DrawDebugTrace.NONE,
        True,
    )
    result = break_hit(hit)
    if not result or not result["blocking_hit"]:
        return {
            "blocking_hit": False,
            "trace_start_cm": vector_payload(start),
            "trace_end_cm": vector_payload(end),
        }
    return {
        "blocking_hit": True,
        "initial_overlap": result["initial_overlap"],
        "location_cm": vector_payload(result["location"]),
        "impact_point_cm": vector_payload(result["impact_point"]),
        "impact_normal": vector_payload(result["impact_normal"]),
        "distance_cm": result["distance_cm"],
        "actor": actor_label(result["actor"]),
        "component": (
            result["component"].get_name() if result["component"] else None
        ),
    }


def unpack_projection(value):
    if isinstance(value, tuple):
        if len(value) >= 2:
            return bool(value[0]), value[1]
        return False, None
    return value is not None, value


def project_to_navigation(world, location):
    try:
        projected, projected_location = unpack_projection(
            unreal.NavigationSystemV1.project_point_to_navigation(
                world, location, None, None, NAV_QUERY_EXTENT
            )
        )
        return {
            "projected": bool(projected),
            "location_cm": (
                vector_payload(projected_location) if projected_location else None
            ),
            "distance_cm": (
                spatial_distance(location, projected_location)
                if projected and projected_location
                else None
            ),
        }
    except Exception as error:
        return {"projected": False, "error": str(error)}


def capsule_clearance(world, center, radius, half_height, actors_to_ignore):
    try:
        end = unreal.Vector(x=center.x, y=center.y, z=center.z + 1.0)
        hit = unreal.SystemLibrary.capsule_trace_single_by_profile(
            world,
            center,
            end,
            radius,
            half_height,
            "Pawn",
            True,
            actors_to_ignore,
            unreal.DrawDebugTrace.NONE,
            True,
        )
        result = break_hit(hit)
        return {
            "clear": not bool(result and result["blocking_hit"]),
            "blocking_actor": (
                actor_label(result["actor"])
                if result and result["blocking_hit"]
                else None
            ),
            "blocking_component": (
                result["component"].get_name()
                if result and result["blocking_hit"] and result["component"]
                else None
            ),
            "initial_overlap": bool(result and result["initial_overlap"]),
        }
    except Exception as error:
        return {"clear": None, "error": str(error)}


def load_level():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach map")
        world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()
    return world


def source_vector(record):
    value = record["transform"]["location_cm"]
    return unreal.Vector(x=float(value["x"]), y=float(value["y"]), z=float(value["z"]))


def soft_path(properties, property_name):
    value = properties.get(property_name) or {}
    return value.get("AssetPathName")


def object_path(properties, property_name):
    value = properties.get(property_name) or {}
    return value.get("ObjectPath")


def source_monster_payload(record, label, representation):
    properties = record.get("properties") or {}
    return {
        "source_name": record.get("actor_name"),
        "source_object_index": record.get("source_object_index"),
        "source_level": record.get("source_level"),
        "target_label": label,
        "representation": representation,
        "transform": record.get("transform"),
        "actor_blueprint": soft_path(properties, "ActorBP_Soft"),
        "ai_data": object_path(properties, "AIData"),
        "spawn_info": object_path(properties, "SpawnInfo"),
        "spawn_index": properties.get("SpawnIDX"),
        "table_index": properties.get("TIDX"),
        "mission_type": properties.get("MissionType"),
        "dependent_level_path": properties.get("DependentLevelPath"),
    }


def main():
    map_hash_before = sha256(MAP_FILE)
    level_data = load_json(LEVEL_DATA_PATH)
    route = load_json(ROUTE_PATH)
    world = load_level()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    actors_by_label = {actor_label(actor): actor for actor in actors}

    player_starts = [actor for actor in actors if isinstance(actor, unreal.PlayerStart)]
    if len(player_starts) != 1:
        raise RuntimeError("Expected exactly one current PlayerStart")
    player_start = player_starts[0]
    if actor_label(player_start) != PLAYER_START_LABEL:
        raise RuntimeError("Current PlayerStart label changed unexpectedly")
    start_location = player_start.get_actor_location()

    world_settings = world.get_world_settings()
    game_mode_class = safe_property(world_settings, "default_game_mode")
    game_mode_cdo = unreal.get_default_object(game_mode_class)
    pawn_class = safe_property(game_mode_cdo, "default_pawn_class")
    pawn_cdo = unreal.get_default_object(pawn_class)
    capsule = pawn_cdo.get_component_by_class(unreal.CapsuleComponent)
    movement = pawn_cdo.get_component_by_class(unreal.CharacterMovementComponent)
    if not capsule or not movement:
        raise RuntimeError("Default Player pawn is missing Capsule/CharacterMovement")
    capsule_radius = float(capsule.get_unscaled_capsule_radius())
    capsule_half_height = float(capsule.get_unscaled_capsule_half_height())
    walkable_floor_angle = float(movement.get_walkable_floor_angle())
    walkable_floor_z = float(movement.get_walkable_floor_z())

    route_points = []
    for action in route.get("move_actions", []):
        for point in action.get("points", []):
            point_values = [float(value) for value in point["world_location_cm"]]
            location = unreal.Vector(
                x=point_values[0], y=point_values[1], z=point_values[2]
            )
            route_points.append(
                {
                    "source_action_index": action.get("source_action_index"),
                    "action_name": action.get("action_name"),
                    "point_index": point.get("point_index"),
                    "location": location,
                    "planar_distance_to_player_start_cm": planar_distance(
                        start_location, location
                    ),
                    "distance_to_player_start_cm": spatial_distance(
                        start_location, location
                    ),
                }
            )
    nearest_route_points = sorted(
        route_points, key=lambda item: item["distance_to_player_start_cm"]
    )[:32]

    candidate_specs = [
        {
            "basis": "current_user_player_start",
            "source_action_index": None,
            "action_name": None,
            "point_index": None,
            "location": start_location,
            "distance_to_player_start_cm": 0.0,
            "planar_distance_to_player_start_cm": 0.0,
        },
        *nearest_route_points,
    ]

    monster_records = sorted(
        list(level_data.get("monster_spawns", [])),
        key=lambda record: int(record.get("source_object_index", -1)),
    )
    if len(monster_records) != 47:
        raise RuntimeError(
            "Expected 47 original Monster spawns, found {}".format(
                len(monster_records)
            )
        )
    nearest_monster = min(
        monster_records,
        key=lambda record: spatial_distance(start_location, source_vector(record)),
    )
    nearest_monster_location = source_vector(nearest_monster)
    source_player_records = list(level_data.get("player_respawn_points", []))
    source_mission_starts = [
        record
        for record in source_player_records
        if record.get("actor_name") == "MISSION01_START"
    ]
    if len(source_mission_starts) != 1:
        raise RuntimeError("Expected one original MISSION01_START record")
    original_mission_start_location = source_vector(source_mission_starts[0])

    candidates = []
    for spec in candidate_specs:
        sample_location = spec["location"]
        surface = trace_surface(world, sample_location)
        spawn_center = None
        nav = {"projected": False, "reason": "no blocking surface"}
        clearance = {"clear": None, "reason": "no blocking surface"}
        walkable = False
        if surface.get("blocking_hit"):
            impact = surface["impact_point_cm"]
            spawn_center = unreal.Vector(
                x=float(impact[0]),
                y=float(impact[1]),
                z=float(impact[2]) + capsule_half_height + SPAWN_CLEARANCE_CM,
            )
            normal = surface.get("impact_normal") or [0.0, 0.0, 0.0]
            walkable = float(normal[2]) >= walkable_floor_z
            nav = project_to_navigation(world, spawn_center)
            clearance = capsule_clearance(
                world,
                spawn_center,
                capsule_radius,
                capsule_half_height,
                [player_start],
            )
        candidate = {
            "basis": spec["basis"] if "basis" in spec else "original_automation_route",
            "source_action_index": spec.get("source_action_index"),
            "action_name": spec.get("action_name"),
            "point_index": spec.get("point_index"),
            "sample_location_cm": vector_payload(sample_location),
            "distance_to_player_start_cm": spec[
                "distance_to_player_start_cm"
            ],
            "planar_distance_to_player_start_cm": spec[
                "planar_distance_to_player_start_cm"
            ],
            "surface": surface,
            "spawn_center_cm": vector_payload(spawn_center),
            "walkable_by_current_cmc": bool(walkable),
            "navigation": nav,
            "capsule_clearance": clearance,
            "distance_to_nearest_monster_cm": (
                spatial_distance(spawn_center, nearest_monster_location)
                if spawn_center
                else None
            ),
        }
        candidate["eligible"] = bool(
            surface.get("blocking_hit")
            and walkable
            and nav.get("projected")
            and clearance.get("clear") is True
        )
        candidates.append(candidate)

    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    eligible.sort(
        key=lambda candidate: (
            candidate["distance_to_player_start_cm"],
            candidate["navigation"].get("distance_cm") or 0.0,
        )
    )
    selected = eligible[0] if eligible else None
    proposed = selected
    proposal_basis = "runtime_validated_candidate"
    if not proposed:
        nearest = nearest_route_points[0]
        proposed = {
            "basis": "nearest_original_automation_route_fallback",
            "source_action_index": nearest["source_action_index"],
            "action_name": nearest["action_name"],
            "point_index": nearest["point_index"],
            "target_location_cm": vector_payload(nearest["location"]),
            "distance_to_player_start_cm": nearest[
                "distance_to_player_start_cm"
            ],
            "planar_distance_to_player_start_cm": nearest[
                "planar_distance_to_player_start_cm"
            ],
            "runtime_surface_validation": "unavailable_in_commandlet",
        }
        proposal_basis = "original_route_fallback_runtime_unverified"

    target_points = [actor for actor in actors if isinstance(actor, unreal.TargetPoint)]
    existing_target_payload = [
        {
            "label": actor_label(actor),
            "location_cm": vector_payload(actor.get_actor_location()),
            "rotation_degrees": rotator_payload(actor.get_actor_rotation()),
            "tags": [str(value) for value in safe_property(actor, "tags", [])],
        }
        for actor in target_points
    ]

    monster_targets = []
    for record in monster_records:
        source_name = record["actor_name"]
        if source_name in TUTORIAL_EXISTING_TARGETS:
            label = TUTORIAL_EXISTING_TARGETS[source_name]
            representation = "reuse_existing_tutorial_target"
            if label not in actors_by_label:
                raise RuntimeError("Existing tutorial TargetPoint is missing: " + label)
        else:
            label = "{}{:04d}_{}".format(
                MONSTER_PREFIX,
                int(record["source_object_index"]),
                source_name,
            )
            representation = (
                "reuse_existing_respawn_target"
                if label in actors_by_label
                else "create_respawn_target"
            )
        monster_targets.append(source_monster_payload(record, label, representation))

    report = {
        "schema_version": 1,
        "date": "2026-09-30",
        "status": (
            "passed" if selected else "passed_with_runtime_surface_unverified"
        ),
        "read_only": True,
        "map": MAP_PATH,
        "map_sha256_before": map_hash_before,
        "map_sha256_after": sha256(MAP_FILE),
        "map_saved_by_script": False,
        "actor_count": len(actors),
        "static_mesh_actor_count": sum(
            1 for actor in actors if isinstance(actor, unreal.StaticMeshActor)
        ),
        "current_player_start": {
            "label": actor_label(player_start),
            "location_cm": vector_payload(start_location),
            "rotation_degrees": rotator_payload(player_start.get_actor_rotation()),
            "player_start_tag": str(safe_property(player_start, "player_start_tag")),
            "tags": [str(value) for value in safe_property(player_start, "tags", [])],
        },
        "current_player_capsule": {
            "radius_cm": capsule_radius,
            "half_height_cm": capsule_half_height,
            "walkable_floor_angle_degrees": walkable_floor_angle,
            "walkable_floor_z": walkable_floor_z,
            "temporary_spawn_clearance_cm": SPAWN_CLEARANCE_CM,
        },
        "nearest_original_route_point": {
            key: value
            for key, value in nearest_route_points[0].items()
            if key != "location"
        }
        | {"location_cm": vector_payload(nearest_route_points[0]["location"])},
        "nearest_original_monster_spawn": {
            "source_name": nearest_monster["actor_name"],
            "source_object_index": nearest_monster["source_object_index"],
            "location_cm": vector_payload(nearest_monster_location),
            "distance_from_player_start_cm": spatial_distance(
                start_location, nearest_monster_location
            ),
        },
        "reference_surface_traces": {
            "original_mission_start": trace_surface(
                world, original_mission_start_location
            ),
            "nearest_monster_spawn": trace_surface(
                world, nearest_monster_location
            ),
        },
        "player_respawn_target": {
            "label": PLAYER_RESPAWN_LABEL,
            "runtime_validated_candidate": selected,
            "proposed_candidate": proposed,
            "proposal_basis": proposal_basis,
            "rotation_basis": "preserve current user PlayerStart rotation",
            "rotation_degrees": rotator_payload(player_start.get_actor_rotation()),
            "candidate_count": len(candidates),
            "eligible_candidate_count": len(eligible),
            "selection_rule": (
                "Nearest original automation-route point or current PlayerStart with "
                "a Pawn-profile surface, current-CMC walkable normal, saved NavMesh "
                "projection, and clear current Player capsule."
            ),
        },
        "candidate_results": candidates,
        "existing_target_points": existing_target_payload,
        "monster_respawn_targets": monster_targets,
        "monster_respawn_target_count": len(monster_targets),
        "monster_targets_reusing_tutorial_points": sum(
            1
            for item in monster_targets
            if item["representation"] == "reuse_existing_tutorial_target"
        ),
        "monster_targets_to_create": sum(
            1
            for item in monster_targets
            if item["representation"] == "create_respawn_target"
        ),
        "preservation_contract": {
            "move_current_player_start": False,
            "create_restore_or_delete_static_mesh_actor": False,
            "modify_existing_actor_transform": False,
            "save_map": False,
        },
    }
    if report["map_sha256_before"] != report["map_sha256_after"]:
        raise RuntimeError("Read-only audit changed the map file")
    write_json(REPORT_PATH, report)
    print("KZ_HEINMACH_RESPAWN_PREFLIGHT_{}".format(report["status"].upper()))


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
                "read_only": True,
                "error": traceback.format_exc(),
            },
        )
        raise
