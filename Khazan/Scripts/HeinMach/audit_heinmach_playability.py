"""Read-only audit of the reconstructed HeinMach gameplay surface.

The environment reconstruction was originally validated as an Art level.  This
audit measures the additional contracts needed by CharacterMovement: the live
PlayerStart/GameMode binding, collision on restored terrain and props, and the
source-authored route walls stored in ``HeinMach_Chrcollision``.

Run in an isolated UnrealEditor-Cmd process.  The script never saves the map or
assets.
"""

from __future__ import annotations

import collections
import json
import math
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment"
SOURCE_COLLISION_JSON = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "Exports",
    "BBQ",
    "Content",
    "_Kazan_",
    "Level",
    "HeinMach",
    "HeinMach_Chrcollision.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_Playability_Audit.json",
)
TUTORIAL_PLAYER_START = "HM_Tutorial_PlayerStart_DualAxeSword"


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def safe_property(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def object_path(obj):
    return obj.get_path_name() if obj else None


def vector_payload(value):
    return [float(value.x), float(value.y), float(value.z)]


def rotator_payload(value):
    return [float(value.pitch), float(value.yaw), float(value.roll)]


def break_hit(hit):
    if not hit:
        return None
    gameplay_statics = unreal.get_default_object(unreal.GameplayStatics)
    values = gameplay_statics.call_method("BreakHitResult", args=(hit,))
    return {
        "blocking_hit": bool(values[0]),
        "location": values[4],
        "actor": values[9],
        "component": values[10],
        "distance_cm": float(values[3]),
    }


def body_setup_payload(mesh):
    body_setup = safe_property(mesh, "body_setup") if mesh else None
    if not body_setup:
        return {
            "body_setup": None,
            "collision_trace_flag": None,
            "simple_shape_count": 0,
        }

    aggregate = safe_property(body_setup, "agg_geom")
    simple_shape_count = 0
    if aggregate:
        for property_name in (
            "sphere_elems",
            "box_elems",
            "sphyl_elems",
            "convex_elems",
            "tapered_capsule_elems",
            "level_set_elems",
        ):
            simple_shape_count += len(safe_property(aggregate, property_name, []) or [])

    return {
        "body_setup": object_path(body_setup),
        "collision_trace_flag": str(safe_property(body_setup, "collision_trace_flag")),
        "has_cooked_collision_data": safe_property(
            body_setup, "has_cooked_collision_data"
        ),
        "failed_to_create_physics_meshes": safe_property(
            body_setup, "failed_to_create_physics_meshes"
        ),
        "never_needs_cooked_collision_data": safe_property(
            body_setup, "never_needs_cooked_collision_data"
        ),
        "simple_shape_count": simple_shape_count,
    }


def component_collision_payload(component):
    mesh = safe_property(component, "static_mesh")
    try:
        collision_enabled = str(component.get_collision_enabled())
    except Exception:
        body_instance = safe_property(component, "body_instance")
        collision_enabled = str(safe_property(body_instance, "collision_enabled"))

    try:
        collision_profile = str(component.get_collision_profile_name())
    except Exception:
        collision_profile = str(safe_property(component, "collision_profile_name"))

    collision_responses = {}
    for label, channel in (
        ("world_static", unreal.CollisionChannel.ECC_WORLD_STATIC),
        ("world_dynamic", unreal.CollisionChannel.ECC_WORLD_DYNAMIC),
        ("pawn", unreal.CollisionChannel.ECC_PAWN),
        ("visibility", unreal.CollisionChannel.ECC_VISIBILITY),
        ("camera", unreal.CollisionChannel.ECC_CAMERA),
        ("physics_body", unreal.CollisionChannel.ECC_PHYSICS_BODY),
    ):
        try:
            collision_responses[label] = str(
                component.get_collision_response_to_channel(channel)
            )
        except Exception as exc:
            collision_responses[label] = "<error: {}>".format(exc)

    return {
        "mesh": object_path(mesh),
        "mesh_has_navigation_data": bool(
            safe_property(mesh, "has_navigation_data", False)
        ) if mesh else None,
        "mesh_nav_collision": object_path(
            safe_property(mesh, "nav_collision")
        ) if mesh else None,
        "collision_enabled": collision_enabled,
        "collision_profile": collision_profile,
        "collision_responses": collision_responses,
        "can_affect_navigation": bool(
            safe_property(component, "can_ever_affect_navigation", False)
        ),
        **body_setup_payload(mesh),
    }


def source_collision_summary():
    if not os.path.isfile(SOURCE_COLLISION_JSON):
        return {
            "source_json": SOURCE_COLLISION_JSON,
            "available": False,
        }

    with open(SOURCE_COLLISION_JSON, "r", encoding="utf-8-sig") as source:
        objects = json.load(source)

    by_type = collections.Counter(obj.get("Type") for obj in objects)
    wall_extents = []
    collision_types = collections.Counter()
    object_types = collections.Counter()
    wall_world_bounds = {
        "min": [math.inf, math.inf, math.inf],
        "max": [-math.inf, -math.inf, -math.inf],
    }

    # Wall transforms are relative to their owning spline component.  The
    # source actors have no additional actor transform; the spline component is
    # the root and its RelativeLocation is therefore the parent world offset.
    spline_locations = {}
    for obj in objects:
        if obj.get("Type") != "xxSplineVolumeComponent":
            continue
        outer = ((obj.get("Outer") or {}).get("ObjectName") or "")
        actor_name = outer.rsplit(".", 1)[-1].rstrip("'")
        properties = obj.get("Properties") or {}
        value = properties.get("RelativeLocation") or {}
        spline_locations[actor_name] = [
            float(value.get("X", 0.0)),
            float(value.get("Y", 0.0)),
            float(value.get("Z", 0.0)),
        ]

        for wall in list(properties.get("LeftWalls") or []) + list(
            properties.get("RightWalls") or []
        ):
            collision_types[wall.get("CollisionType") or "None"] += 1

    for obj in objects:
        if obj.get("Type") != "xxWallComponent":
            continue
        properties = obj.get("Properties") or {}
        extent = properties.get("BoxExtent") or {}
        relative = properties.get("RelativeLocation") or {}
        outer = ((obj.get("Outer") or {}).get("ObjectName") or "")
        actor_name = outer.rsplit(".", 1)[-1].rstrip("'")
        parent = spline_locations.get(actor_name, [0.0, 0.0, 0.0])
        world = [
            parent[0] + float(relative.get("X", 0.0)),
            parent[1] + float(relative.get("Y", 0.0)),
            parent[2] + float(relative.get("Z", 0.0)),
        ]
        extents = [
            float(extent.get("X", 0.0)),
            float(extent.get("Y", 0.0)),
            float(extent.get("Z", 0.0)),
        ]
        wall_extents.append(extents)
        for axis in range(3):
            wall_world_bounds["min"][axis] = min(
                wall_world_bounds["min"][axis], world[axis] - extents[axis]
            )
            wall_world_bounds["max"][axis] = max(
                wall_world_bounds["max"][axis], world[axis] + extents[axis]
            )

        body = properties.get("BodyInstance") or {}
        object_types[body.get("ObjectType") or "None"] += 1

    return {
        "source_json": SOURCE_COLLISION_JSON,
        "available": True,
        "object_count": len(objects),
        "type_counts": dict(sorted(by_type.items())),
        "spline_collision_types": dict(sorted(collision_types.items())),
        "wall_object_types": dict(sorted(object_types.items())),
        "wall_world_bounds_cm": wall_world_bounds,
        "wall_extent_cm": {
            "min": [min(values[i] for values in wall_extents) for i in range(3)],
            "max": [max(values[i] for values in wall_extents) for i in range(3)],
        }
        if wall_extents
        else None,
    }


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Unable to load HeinMach map: " + MAP_PATH)

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        raise RuntimeError("HeinMach editor world is not active")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    world_settings = world.get_world_settings()

    class_counts = collections.Counter(actor.get_class().get_name() for actor in actors)
    static_collision_counts = collections.Counter()
    static_profile_counts = collections.Counter()
    static_trace_flag_counts = collections.Counter()
    collision_named_trace_flag_counts = collections.Counter()
    collision_named_visibility_counts = collections.Counter()
    unique_meshes = {}
    static_actors = []
    terrain = []
    tutorial_actors = []
    collision_named_actors = []
    route_collision = None
    nav_bounds = []
    nav_modifiers = []
    source_nav_links = []
    automation_route_nav_links = []
    recast_nav_meshes = []
    start_location = None

    for actor in actors:
        label = actor.get_actor_label()
        class_name = actor.get_class().get_name()
        if label == "HM_RouteCollision_Source_Chrcollision":
            component = actor.get_component_by_class(
                unreal.HierarchicalInstancedStaticMeshComponent
            )
            route_collision = {
                "label": label,
                "class": class_name,
                "native_instance_count": int(actor.get_boundary_instance_count()),
                "component_instance_count": int(component.get_instance_count())
                if component
                else None,
                "component": component_collision_payload(component)
                if component
                else None,
                "actor_location_cm": vector_payload(actor.get_actor_location()),
                "actor_scale": vector_payload(actor.get_actor_scale3d()),
            }
        if class_name == "KZNavMeshBoundsBox":
            bounds_origin, bounds_extent = actor.get_actor_bounds(False, False)
            nav_bounds.append(
                {
                    "label": label,
                    "location_cm": vector_payload(actor.get_actor_location()),
                    "scale": vector_payload(actor.get_actor_scale3d()),
                    "bounds_origin_cm": vector_payload(bounds_origin),
                    "bounds_extent_cm": vector_payload(bounds_extent),
                }
            )
        if class_name == "KZNavModifierBox":
            bounds_origin, bounds_extent = actor.get_actor_bounds(False, False)
            nav_modifiers.append(
                {
                    "label": label,
                    "location_cm": vector_payload(actor.get_actor_location()),
                    "rotation_degrees": rotator_payload(
                        actor.get_actor_rotation()
                    ),
                    "scale": vector_payload(actor.get_actor_scale3d()),
                    "bounds_origin_cm": vector_payload(bounds_origin),
                    "bounds_extent_cm": vector_payload(bounds_extent),
                }
            )
        if label.startswith("HM_NavLink_Source_"):
            source_nav_links.append(label)
        if label.startswith("HM_NavLink_AutomationRoute_"):
            automation_route_nav_links.append(label)
        if "RecastNavMesh" in class_name:
            recast_nav_meshes.append({"label": label, "class": class_name})
        if "PlayerStart" in class_name or label.startswith("HM_Tutorial"):
            tutorial_actors.append(
                {
                    "label": label,
                    "class": class_name,
                    "location_cm": vector_payload(actor.get_actor_location()),
                    "rotation_degrees": rotator_payload(actor.get_actor_rotation()),
                }
            )
            if label == TUTORIAL_PLAYER_START:
                start_location = actor.get_actor_location()

        lowered = (label + " " + class_name).lower()
        if any(token in lowered for token in ("collision", "block", "navmesh", "navmodifier")):
            collision_named_actors.append({"label": label, "class": class_name})

        if not isinstance(actor, unreal.StaticMeshActor):
            continue

        component = actor.static_mesh_component
        static_actors.append(actor)
        collision = component_collision_payload(component)
        static_collision_counts[collision["collision_enabled"]] += 1
        static_profile_counts[collision["collision_profile"]] += 1
        static_trace_flag_counts[collision["collision_trace_flag"]] += 1
        if collision["mesh"]:
            unique_meshes.setdefault(collision["mesh"], collision)

        if "collision" in label.lower():
            collision_named_trace_flag_counts[collision["collision_trace_flag"]] += 1
            collision_named_visibility_counts[
                "visible={} hidden_in_game={} render_main_pass={}".format(
                    bool(safe_property(component, "visible", True)),
                    bool(safe_property(component, "hidden_in_game", False)),
                    bool(safe_property(component, "render_in_main_pass", True)),
                )
            ] += 1

        if label.startswith("HM_Landscape_") or label.startswith("HM_Terrain_"):
            terrain.append(
                {
                    "label": label,
                    "location_cm": vector_payload(actor.get_actor_location()),
                    **collision,
                }
            )

    start_bounds_candidates = []
    if start_location:
        for actor in static_actors:
            origin, extent = actor.get_actor_bounds(False, False)
            if (
                abs(start_location.x - origin.x) <= extent.x
                and abs(start_location.y - origin.y) <= extent.y
            ):
                component = actor.static_mesh_component
                collision = component_collision_payload(component)
                start_bounds_candidates.append(
                    {
                        "label": actor.get_actor_label(),
                        "class": actor.get_class().get_name(),
                        "mesh": collision["mesh"],
                        "bounds_origin_cm": vector_payload(origin),
                        "bounds_extent_cm": vector_payload(extent),
                        "bounds_top_z_cm": float(origin.z + extent.z),
                        "bounds_bottom_z_cm": float(origin.z - extent.z),
                        "actor_location_cm": vector_payload(actor.get_actor_location()),
                        "actor_scale": vector_payload(actor.get_actor_scale3d()),
                        **collision,
                    }
                )
        start_bounds_candidates.sort(
            key=lambda item: abs(item["bounds_top_z_cm"] - start_location.z)
        )

    downward_trace = None
    downward_pawn_profile_trace = None
    if start_location:
        start = unreal.Vector(
            x=start_location.x,
            y=start_location.y,
            z=start_location.z + 1000.0,
        )
        end = unreal.Vector(
            x=start_location.x,
            y=start_location.y,
            z=start_location.z - 5000.0,
        )
        try:
            hit = unreal.SystemLibrary.line_trace_single(
                world,
                start,
                end,
                unreal.TraceTypeQuery.ECC_VISIBILITY,
                False,
                [],
                unreal.DrawDebugTrace.NONE,
                True,
            )
            broken_hit = break_hit(hit)
            downward_trace = {
                "blocking_hit": bool(
                    broken_hit and broken_hit["blocking_hit"]
                ),
                "actor": (
                    broken_hit["actor"].get_actor_label()
                    if broken_hit and broken_hit["actor"]
                    else None
                ),
                "component": (
                    broken_hit["component"].get_name()
                    if broken_hit and broken_hit["component"]
                    else None
                ),
                "location_cm": (
                    vector_payload(broken_hit["location"])
                    if broken_hit
                    else None
                ),
                "distance_cm": (
                    broken_hit["distance_cm"] if broken_hit else None
                ),
            }
        except Exception as exc:
            downward_trace = {"error": str(exc)}
        try:
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
            broken_hit = break_hit(hit)
            downward_pawn_profile_trace = {
                "blocking_hit": bool(
                    broken_hit and broken_hit["blocking_hit"]
                ),
                "actor": (
                    broken_hit["actor"].get_actor_label()
                    if broken_hit and broken_hit["actor"]
                    else None
                ),
                "component": (
                    broken_hit["component"].get_name()
                    if broken_hit and broken_hit["component"]
                    else None
                ),
                "location_cm": (
                    vector_payload(broken_hit["location"])
                    if broken_hit
                    else None
                ),
                "distance_cm": (
                    broken_hit["distance_cm"] if broken_hit else None
                ),
            }
        except Exception as exc:
            downward_pawn_profile_trace = {"error": str(exc)}

    default_pawn = {}
    try:
        game_mode_class = safe_property(world_settings, "default_game_mode")
        game_mode_cdo = unreal.get_default_object(game_mode_class)
        pawn_class = safe_property(game_mode_cdo, "default_pawn_class")
        pawn_cdo = unreal.get_default_object(pawn_class)
        capsule = pawn_cdo.get_component_by_class(unreal.CapsuleComponent)
        default_pawn = {
            "class": object_path(pawn_class),
            "capsule_radius_cm": float(capsule.get_scaled_capsule_radius()),
            "capsule_half_height_cm": float(
                capsule.get_scaled_capsule_half_height()
            ),
        }
    except Exception as exc:
        default_pawn = {"error": str(exc)}

    report = {
        "status": "audited",
        "map": MAP_PATH,
        "map_actor_count": len(actors),
        "world_default_game_mode": object_path(
            safe_property(world_settings, "default_game_mode")
        ),
        "default_pawn": default_pawn,
        "class_counts": dict(sorted(class_counts.items())),
        "tutorial_actors": tutorial_actors,
        "tutorial_start_downward_visibility_trace": downward_trace,
        "tutorial_start_downward_pawn_profile_trace": downward_pawn_profile_trace,
        "tutorial_start_render_bounds_candidates": start_bounds_candidates[:100],
        "route_collision": route_collision,
        "source_nav_bounds_actor_count": len(nav_bounds),
        "source_nav_bounds_actors": nav_bounds,
        "source_nav_modifier_actor_count": len(nav_modifiers),
        "source_nav_modifier_actors": nav_modifiers,
        "source_nav_link_actor_count": len(source_nav_links),
        "source_nav_link_actors": sorted(source_nav_links),
        "automation_route_nav_link_actor_count": len(
            automation_route_nav_links
        ),
        "automation_route_nav_link_actors": sorted(
            automation_route_nav_links
        ),
        "recast_nav_meshes": recast_nav_meshes,
        "collision_named_actor_count": len(collision_named_actors),
        "collision_named_actors": collision_named_actors,
        "static_mesh_actor_count": sum(static_collision_counts.values()),
        "static_collision_enabled_counts": dict(sorted(static_collision_counts.items())),
        "static_collision_profile_counts": dict(sorted(static_profile_counts.items())),
        "static_collision_trace_flag_counts": dict(
            sorted(static_trace_flag_counts.items())
        ),
        "collision_named_trace_flag_counts": dict(
            sorted(collision_named_trace_flag_counts.items())
        ),
        "collision_named_visibility_counts": dict(
            sorted(collision_named_visibility_counts.items())
        ),
        "unique_static_mesh_count": len(unique_meshes),
        "unique_static_mesh_body_setup_counts": {
            "missing_body_setup": sum(
                1 for item in unique_meshes.values() if not item["body_setup"]
            ),
            "with_simple_shapes": sum(
                1 for item in unique_meshes.values() if item["simple_shape_count"] > 0
            ),
            "without_simple_shapes": sum(
                1 for item in unique_meshes.values() if item["simple_shape_count"] == 0
            ),
        },
        "terrain_actor_count": len(terrain),
        "terrain_actors": terrain,
        "source_character_collision": source_collision_summary(),
        "map_saved": False,
    }
    write_json(REPORT_PATH, report)
    unreal.log(
        "KZ_HEINMACH_PLAYABILITY_AUDIT: actors={} terrain={} source_walls={} report={}".format(
            len(actors),
            len(terrain),
            report["source_character_collision"].get("type_counts", {}).get(
                "xxWallComponent", 0
            ),
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
                "map_saved": False,
            },
        )
        unreal.log_error("KZ_HEINMACH_PLAYABILITY_AUDIT: " + str(exception))
        raise
