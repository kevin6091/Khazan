"""Build HeinMach navigation in a real editor session and verify playability in PIE.

Run with ``UnrealEditor.exe -ExecutePythonScript=...`` rather than a commandlet.
Commandlets keep the editor navigation system under its initial build lock; a
normal editor tick releases that lock after asynchronous asset compilation.

The script saves only the already-authorized HeinMach map after navigation has
finished.  Its PIE phase is diagnostic: it injects the project's IA_Move action,
checks the possessed player and CharacterMovement displacement, and proves that
one reconstructed source wall blocks the Pawn collision profile.
"""

from __future__ import annotations

import builtins
import json
import math
import os
import traceback

import unreal


# ``-ExecutePythonScript`` closes the editor on the frame after the top-level
# script returns unless this editor-only flag is held for our asynchronous
# navigation/PIE callback.
unreal.EditorPythonScripting.set_keep_python_script_alive(True)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_Playability_RuntimeVerification.json",
)
ANCHOR_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_PlayableCameraAnchors.json",
)
ROUTE_COLLISION_MAPPING_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RouteCollision_SourceMapping.json",
)
AUTOMATION_ROUTE_REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_OriginalAutomationRoute.json",
)
ROUTE_COLLISION_LABEL = "HM_RouteCollision_Source_Chrcollision"
NAV_LINK_LABEL_PREFIX = "HM_NavLink_Source_"
AUTOMATION_NAV_LINK_LABEL_PREFIX = "HM_NavLink_AutomationRoute_"
SOURCE_START = unreal.Vector(x=12073.493, y=24725.363, z=303.5308)
EXPECTED_PLAYER_START = unreal.Vector(
    x=12073.493, y=24725.363, z=450.70317567901657
)
MOVE_ACTION_PATH = "/Game/Input/Locomotion/IA_Move"
STATE_KEY = "_khazan_heinmach_playability_verification"


def write_json(payload):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def vector_payload(value):
    return [float(value.x), float(value.y), float(value.z)]


def distance(a, b):
    return math.sqrt(
        (float(a.x) - float(b.x)) ** 2
        + (float(a.y) - float(b.y)) ** 2
        + (float(a.z) - float(b.z)) ** 2
    )


def actor_label(actor):
    if not actor:
        return None
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def break_hit(hit):
    if not hit:
        return None
    gameplay_statics = unreal.get_default_object(unreal.GameplayStatics)
    values = gameplay_statics.call_method("BreakHitResult", args=(hit,))
    return {
        "blocking_hit": bool(values[0]),
        "initial_overlap": bool(values[1]),
        "time": float(values[2]),
        "distance": float(values[3]),
        "location": values[4],
        "impact_point": values[5],
        "normal": values[6],
        "impact_normal": values[7],
        "actor": values[9],
        "component": values[10],
        "item_index": int(values[13]),
        "element_index": int(values[14]),
        "face_index": int(values[15]),
    }


def trace_surface_at(world, location, upward_cm=5000.0, downward_cm=10000.0):
    start = unreal.Vector(
        x=location.x, y=location.y, z=location.z + upward_cm
    )
    end = unreal.Vector(
        x=location.x, y=location.y, z=location.z - downward_cm
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
    if not hit:
        return {
            "blocking_hit": False,
            "trace_start_cm": vector_payload(start),
            "trace_end_cm": vector_payload(end),
        }
    result = break_hit(hit)
    if not result:
        return {
            "blocking_hit": False,
            "trace_start_cm": vector_payload(start),
            "trace_end_cm": vector_payload(end),
        }
    component = result["component"]
    owner = result["actor"]
    return {
        "blocking_hit": result["blocking_hit"],
        "initial_overlap": result["initial_overlap"],
        "trace_start_cm": vector_payload(start),
        "trace_end_cm": vector_payload(end),
        "location_cm": vector_payload(result["location"]),
        "impact_point_cm": vector_payload(result["impact_point"]),
        "impact_normal": vector_payload(result["impact_normal"]),
        "distance_cm": result["distance"],
        "item_index": result["item_index"],
        "element_index": result["element_index"],
        "face_index": result["face_index"],
        "actor": actor_label(owner),
        "component": component.get_name() if component else None,
    }


def trace_tutorial_surface(world):
    return trace_surface_at(world, SOURCE_START)


def instance_transform(component, index):
    value = component.get_instance_transform(index, True)
    if isinstance(value, tuple):
        if len(value) == 2 and bool(value[0]):
            return value[1]
        return None
    return value


def transform_scale(transform):
    for attribute in ("scale3d", "scale"):
        try:
            return getattr(transform, attribute)
        except Exception:
            pass
    return unreal.Vector(x=1.0, y=1.0, z=1.0)


def find_route_collision_actor(world):
    actors = unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.KZLevelRouteCollisionActor
    )
    for actor in actors:
        if actor_label(actor) == ROUTE_COLLISION_LABEL:
            return actor
    return actors[0] if len(actors) == 1 else None


def prove_route_wall_blocks_pawn(world, origin):
    route_actor = find_route_collision_actor(world)
    if not route_actor:
        return {"passed": False, "error": "Route collision actor is missing in PIE"}
    component = route_actor.get_component_by_class(
        unreal.HierarchicalInstancedStaticMeshComponent
    )
    if not component:
        return {"passed": False, "error": "Route collision HISM is missing in PIE"}

    candidates = []
    count = int(component.get_instance_count())
    for index in range(count):
        transform = instance_transform(component, index)
        if not transform:
            continue
        center = transform.translation
        planar_distance = math.hypot(center.x - origin.x, center.y - origin.y)
        candidates.append((planar_distance, index, transform))

    # The closest walls give the most relevant proof for the tutorial route.
    # Continue farther if nearby wall centers overlap visible environment mesh.
    candidates.sort(key=lambda item: item[0])
    attempts = []
    for planar_distance, index, transform in candidates:
        center = transform.translation
        scale = transform_scale(transform)
        half_extent = unreal.Vector(
            x=abs(float(scale.x)) * 50.0,
            y=abs(float(scale.y)) * 50.0,
            z=abs(float(scale.z)) * 50.0,
        )
        if half_extent.x <= half_extent.y:
            local_normal = unreal.Vector(x=1.0, y=0.0, z=0.0)
            normal_extent = half_extent.x
        else:
            local_normal = unreal.Vector(x=0.0, y=1.0, z=0.0)
            normal_extent = half_extent.y
        normal = unreal.MathLibrary.transform_direction(transform, local_normal)
        normal_length = math.sqrt(normal.x * normal.x + normal.y * normal.y + normal.z * normal.z)
        if normal_length <= 0.001:
            continue
        normal = unreal.Vector(
            x=normal.x / normal_length,
            y=normal.y / normal_length,
            z=normal.z / normal_length,
        )
        span = normal_extent + 100.0
        start = unreal.Vector(
            x=center.x - normal.x * span,
            y=center.y - normal.y * span,
            z=center.z - normal.z * span,
        )
        end = unreal.Vector(
            x=center.x + normal.x * span,
            y=center.y + normal.y * span,
            z=center.z + normal.z * span,
        )
        hit = unreal.SystemLibrary.line_trace_single_by_profile(
            world,
            start,
            end,
            "Pawn",
            False,
            [],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        result = break_hit(hit)
        blocking_actor = result["actor"] if result else None
        hit_label = actor_label(blocking_actor)
        if len(attempts) < 20:
            attempts.append(
                {
                    "instance_index": index,
                    "distance_from_tutorial_start_cm": float(planar_distance),
                    "blocking_hit": bool(result and result["blocking_hit"]),
                    "hit_actor": hit_label,
                }
            )
        if result and result["blocking_hit"] and blocking_actor == route_actor:
            return {
                "passed": True,
                "route_actor": actor_label(route_actor),
                "instance_count": count,
                "blocking_instance_index": index,
                "distance_from_tutorial_start_cm": float(planar_distance),
                "box_center_cm": vector_payload(center),
                "box_half_extent_cm": vector_payload(half_extent),
                "trace_start_cm": vector_payload(start),
                "trace_end_cm": vector_payload(end),
                "hit_location_cm": vector_payload(result["location"]),
                "hit_component": (
                    result["component"].get_name() if result["component"] else None
                ),
                "profile": "Pawn",
                "sample_attempts": attempts,
            }
    return {
        "passed": False,
        "route_actor": actor_label(route_actor),
        "instance_count": count,
        "error": "No source wall produced a blocking Pawn-profile trace",
        "sample_attempts": attempts,
    }


def unpack_projection(value):
    if isinstance(value, tuple):
        if len(value) >= 2:
            return bool(value[0]), value[1]
        return False, None
    return value is not None, value


def load_route_collision_mapping():
    if not os.path.isfile(ROUTE_COLLISION_MAPPING_PATH):
        return {}
    with open(ROUTE_COLLISION_MAPPING_PATH, "r", encoding="utf-8-sig") as source:
        payload = json.load(source)
    return {
        int(item["instance_index"]): item
        for item in payload.get("instances", [])
    }


def planar_distance_to_source_wall(location, source_record):
    center = source_record["world_center_cm"]
    extent = source_record["box_half_extent_cm"]
    rotation = source_record["world_rotation_degrees"]
    delta_x = float(location.x) - float(center[0])
    delta_y = float(location.y) - float(center[1])
    yaw = math.radians(float(rotation[1]))
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    local_x = cosine * delta_x + sine * delta_y
    local_y = -sine * delta_x + cosine * delta_y
    outside_x = max(abs(local_x) - float(extent[0]), 0.0)
    outside_y = max(abs(local_y) - float(extent[1]), 0.0)
    return math.hypot(outside_x, outside_y), local_x, local_y


def nearest_source_walls(location, source_mapping, limit=8):
    candidates = []
    for instance_index, source_record in source_mapping.items():
        planar_distance, local_x, local_y = planar_distance_to_source_wall(
            location, source_record
        )
        candidates.append(
            (planar_distance, instance_index, local_x, local_y, source_record)
        )
    candidates.sort(key=lambda item: (item[0], item[1]))
    result = []
    for planar_distance, instance_index, local_x, local_y, source_record in candidates[
        :limit
    ]:
        result.append(
            {
                "instance_index": instance_index,
                "planar_distance_to_box_cm": float(planar_distance),
                "point_in_box_local_xy_cm": [float(local_x), float(local_y)],
                "source_component_index": source_record.get(
                    "source_component_index"
                ),
                "source_component_name": source_record.get("source_component_name"),
                "source_owner_index": source_record.get("source_owner_index"),
                "source_owner_type": source_record.get("source_owner_type"),
                "source_owner_name": source_record.get("source_owner_name"),
                "world_center_cm": source_record.get("world_center_cm"),
                "world_rotation_degrees": source_record.get(
                    "world_rotation_degrees"
                ),
                "box_half_extent_cm": source_record.get("box_half_extent_cm"),
            }
        )
    return result


def trace_path_boundary_forward(world, endpoint, direction):
    start = unreal.Vector(
        x=endpoint.x - direction.x * 100.0,
        y=endpoint.y - direction.y * 100.0,
        z=endpoint.z + 88.0,
    )
    end = unreal.Vector(
        x=endpoint.x + direction.x * 1200.0,
        y=endpoint.y + direction.y * 1200.0,
        z=endpoint.z + 88.0,
    )
    hit = unreal.SystemLibrary.line_trace_single_by_profile(
        world,
        start,
        end,
        "Pawn",
        False,
        [],
        unreal.DrawDebugTrace.NONE,
        True,
    )
    result = break_hit(hit)
    return {
        "trace_start_cm": vector_payload(start),
        "trace_end_cm": vector_payload(end),
        "blocking_hit": bool(result and result["blocking_hit"]),
        "hit_actor": actor_label(result["actor"]) if result else None,
        "hit_component": (
            result["component"].get_name()
            if result and result["component"]
            else None
        ),
        "hit_item_index": result["item_index"] if result else None,
        "hit_location_cm": (
            vector_payload(result["location"]) if result else None
        ),
        "distance_cm": result["distance"] if result else None,
    }


def probe_partial_path_boundary(world, path_points, target, source_mapping):
    if not path_points:
        return {"error": "Partial path has no points"}
    endpoint = path_points[-1]
    if len(path_points) >= 2:
        direction_x = float(endpoint.x - path_points[-2].x)
        direction_y = float(endpoint.y - path_points[-2].y)
        direction_basis = "final_path_segment"
    else:
        direction_x = float(target.x - endpoint.x)
        direction_y = float(target.y - endpoint.y)
        direction_basis = "target_vector"
    direction_length = math.hypot(direction_x, direction_y)
    if direction_length <= 0.001:
        return {"error": "Partial path endpoint has no planar direction"}
    direction = unreal.Vector(
        x=direction_x / direction_length,
        y=direction_y / direction_length,
        z=0.0,
    )
    samples = []
    for offset in (-100.0, 0.0, 50.0, 100.0, 200.0, 400.0, 800.0, 1200.0):
        location = unreal.Vector(
            x=endpoint.x + direction.x * offset,
            y=endpoint.y + direction.y * offset,
            z=endpoint.z,
        )
        surface = trace_surface_at(world, location, 3000.0, 12000.0)
        projection_result = unreal.NavigationSystemV1.project_point_to_navigation(
            world,
            location,
            None,
            None,
            unreal.Vector(x=75.0, y=75.0, z=1000.0),
        )
        projected, projected_location = unpack_projection(projection_result)
        samples.append(
            {
                "offset_from_path_endpoint_cm": offset,
                "sample_location_cm": vector_payload(location),
                "surface_blocking_hit": bool(surface.get("blocking_hit")),
                "surface_actor": surface.get("actor"),
                "surface_component": surface.get("component"),
                "surface_location_cm": surface.get("location_cm"),
                "surface_item_index": surface.get("item_index"),
                "projected_to_navigation": projected,
                "projected_location_cm": (
                    vector_payload(projected_location)
                    if projected_location
                    else None
                ),
            }
        )
    return {
        "path_endpoint_cm": vector_payload(endpoint),
        "forward_direction_xy": [float(direction.x), float(direction.y)],
        "direction_basis": direction_basis,
        "forward_pawn_profile_trace": trace_path_boundary_forward(
            world, endpoint, direction
        ),
        "nearest_source_walls": nearest_source_walls(
            endpoint, source_mapping
        ),
        "forward_samples": samples,
    }


def verify_navigation_routes(world):
    if not os.path.isfile(ANCHOR_REPORT_PATH):
        return {"passed": False, "error": "Route anchor report is missing"}
    with open(ANCHOR_REPORT_PATH, "r", encoding="utf-8-sig") as source:
        anchor_payload = json.load(source)
    anchors = {
        item["tag"]: unreal.Vector(
            x=float(item["world_location_cm"][0]),
            y=float(item["world_location_cm"][1]),
            z=float(item["world_location_cm"][2]),
        )
        for item in anchor_payload.get("all_player_starts", [])
    }
    order = list(anchor_payload.get("route_order", []))
    projected = {}
    projections = []
    for tag in order:
        source_location = anchors[tag]
        result = unreal.NavigationSystemV1.project_point_to_navigation(
            world,
            source_location,
            None,
            None,
            unreal.Vector(x=500.0, y=500.0, z=1000.0),
        )
        success, location = unpack_projection(result)
        projections.append(
            {
                "tag": tag,
                "source_location_cm": vector_payload(source_location),
                "projected": success,
                "projected_location_cm": vector_payload(location) if location else None,
            }
        )
        if success and location:
            projected[tag] = location

    segments = []
    source_mapping = load_route_collision_mapping()
    for start_tag, end_tag in zip(order, order[1:]):
        if start_tag not in projected or end_tag not in projected:
            segments.append(
                {
                    "from": start_tag,
                    "to": end_tag,
                    "valid": False,
                    "partial": None,
                    "error": "One or both route anchors did not project to navigation",
                }
            )
            continue
        path = unreal.NavigationSystemV1.find_path_to_location_synchronously(
            world, projected[start_tag], projected[end_tag]
        )
        valid = bool(path and path.is_valid())
        partial = bool(path.is_partial()) if path else None
        points = path.get_editor_property("path_points") if path else []
        segment = {
                "from": start_tag,
                "to": end_tag,
                "valid": valid,
                "partial": partial,
                "path_length_cm": float(path.get_path_length()) if valid else None,
                "path_point_count": len(points),
                "path_points_cm": [vector_payload(point) for point in points],
                "remaining_planar_distance_cm": (
                    float(
                        math.hypot(
                            points[-1].x - projected[end_tag].x,
                            points[-1].y - projected[end_tag].y,
                        )
                    )
                    if points and end_tag in projected
                    else None
                ),
            }
        if partial and points:
            segment["boundary_probe"] = probe_partial_path_boundary(
                world, points, projected[end_tag], source_mapping
            )
        segments.append(segment)
    anchor_coverage_passed = bool(order) and len(projected) == len(order)
    continuous_segment_count = sum(
        1 for item in segments if item["valid"] and not item["partial"]
    )
    partial_segment_count = sum(
        1 for item in segments if item["valid"] and item["partial"]
    )
    return {
        "passed": anchor_coverage_passed
        and all(item["valid"] and not item["partial"] for item in segments),
        "anchor_coverage_passed": anchor_coverage_passed,
        "route_collision_mapping_record_count": len(source_mapping),
        "continuous_segment_count": continuous_segment_count,
        "partial_segment_count": partial_segment_count,
        "route_order": order,
        "projections": projections,
        "segments": segments,
    }


def verify_source_navigation_links(world):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = sorted(
        (
            actor
            for actor in actor_subsystem.get_all_level_actors()
            if actor and actor_label(actor).startswith(NAV_LINK_LABEL_PREFIX)
        ),
        key=actor_label,
    )
    results = []
    connected_directions = 0
    expected_directions = 0
    for actor in actors:
        point_links = actor.get_editor_property("point_links")
        if len(point_links) != 1:
            results.append(
                {
                    "label": actor_label(actor),
                    "passed": False,
                    "error": "Expected exactly one point link",
                    "point_link_count": len(point_links),
                }
            )
            continue

        link = point_links[0]
        transform = actor.get_actor_transform()
        left_local = link.get_editor_property("left")
        right_local = link.get_editor_property("right")
        left_world = unreal.MathLibrary.transform_location(transform, left_local)
        right_world = unreal.MathLibrary.transform_location(transform, right_local)
        direction = str(link.get_editor_property("direction"))

        endpoint_results = {}
        projected_endpoints = {}
        for name, location in (("left", left_world), ("right", right_world)):
            narrow_result = unreal.NavigationSystemV1.project_point_to_navigation(
                world,
                location,
                None,
                None,
                unreal.Vector(x=60.0, y=60.0, z=100.0),
            )
            narrow_success, narrow_location = unpack_projection(narrow_result)
            broad_result = unreal.NavigationSystemV1.project_point_to_navigation(
                world,
                location,
                None,
                None,
                unreal.Vector(x=150.0, y=150.0, z=1000.0),
            )
            broad_success, broad_location = unpack_projection(broad_result)
            selected = narrow_location if narrow_success else broad_location
            projected_endpoints[name] = selected
            endpoint_results[name] = {
                "local_cm": vector_payload(
                    left_local if name == "left" else right_local
                ),
                "world_cm": vector_payload(location),
                "narrow_projected": bool(narrow_success),
                "narrow_projected_cm": (
                    vector_payload(narrow_location) if narrow_location else None
                ),
                "broad_projected": bool(broad_success),
                "broad_projected_cm": (
                    vector_payload(broad_location) if broad_location else None
                ),
            }

        is_bidirectional = "BOTH_WAYS" in direction or "BothWays" in direction

        path_results = []
        for path_name, start_name, end_name in (
            ("left_to_right", "left", "right"),
            ("right_to_left", "right", "left"),
        ):
            start = projected_endpoints[start_name]
            end = projected_endpoints[end_name]
            path = (
                unreal.NavigationSystemV1.find_path_to_location_synchronously(
                    world, start, end
                )
                if start and end
                else None
            )
            valid = bool(path and path.is_valid())
            partial = bool(path.is_partial()) if path else None
            path_points = path.get_editor_property("path_points") if path else []
            connected = valid and not partial
            path_results.append(
                {
                    "direction": path_name,
                    "connected": connected,
                    "valid": valid,
                    "partial": partial,
                    "path_length_cm": float(path.get_path_length()) if valid else None,
                    "path_points_cm": [
                        vector_payload(point) for point in path_points
                    ],
                }
            )

        connected_path_count = sum(
            1 for item in path_results if item["connected"]
        )
        required_path_count = 2 if is_bidirectional else 1
        expected_directions += required_path_count
        connected_directions += min(connected_path_count, required_path_count)

        results.append(
            {
                "label": actor_label(actor),
                "source_index": next(
                    (
                        int(str(tag).split("_", 1)[1])
                        for tag in actor.tags
                        if str(tag).startswith("SourceIndex_")
                    ),
                    None,
                ),
                "direction": direction,
                "left_project_height_cm": float(
                    link.get_editor_property("left_project_height")
                ),
                "right_project_height_cm": float(
                    link.get_editor_property("max_fall_down_length")
                ),
                "snap_radius_cm": float(link.get_editor_property("snap_radius")),
                "snap_height_cm": float(link.get_editor_property("snap_height")),
                "endpoints": endpoint_results,
                "paths": path_results,
                "required_connected_direction_count": required_path_count,
                "connected_direction_count": connected_path_count,
                "passed": connected_path_count >= required_path_count,
            }
        )

    return {
        "passed": len(actors) == 14 and connected_directions == expected_directions,
        "actor_count": len(actors),
        "expected_direction_count": expected_directions,
        "connected_direction_count": connected_directions,
        "links": results,
    }


def verify_original_automation_route(world):
    if not os.path.isfile(AUTOMATION_ROUTE_REPORT_PATH):
        return {"passed": False, "error": "Original automation route report is missing"}
    with open(AUTOMATION_ROUTE_REPORT_PATH, "r", encoding="utf-8-sig") as source:
        payload = json.load(source)
    move_actions = payload.get("move_actions", [])
    action_results = []
    total_points = 0
    projected_points = 0
    total_segments = 0
    complete_segments = 0
    collapsed_segments = 0
    for action in move_actions:
        points = action.get("points", [])
        projected = []
        projection_details = []
        projection_failures = []
        previous_source_location = None
        previous_projected_location = None
        for point in points:
            source_location = unreal.Vector(
                x=float(point["world_location_cm"][0]),
                y=float(point["world_location_cm"][1]),
                z=float(point["world_location_cm"][2]),
            )
            if previous_source_location and previous_projected_location:
                continuity_location = unreal.Vector(
                    x=source_location.x,
                    y=source_location.y,
                    z=(
                        previous_projected_location.z
                        + source_location.z
                        - previous_source_location.z
                    ),
                )
            else:
                continuity_location = source_location

            attempts = (
                (
                    "spline_height_continuity",
                    continuity_location,
                    unreal.Vector(x=150.0, y=150.0, z=175.0),
                ),
                (
                    "source_height_local",
                    source_location,
                    unreal.Vector(x=150.0, y=150.0, z=300.0),
                ),
                (
                    "source_height_broad_fallback",
                    source_location,
                    unreal.Vector(x=100.0, y=100.0, z=1000.0),
                ),
            )
            success = False
            location = None
            projection_method = None
            for method, query_location, query_extent in attempts:
                result = unreal.NavigationSystemV1.project_point_to_navigation(
                    world,
                    query_location,
                    None,
                    None,
                    query_extent,
                )
                success, location = unpack_projection(result)
                if success and location:
                    projection_method = method
                    break
            projected.append(location if success else None)
            projection_details.append(
                {
                    "point_index": int(point["point_index"]),
                    "method": projection_method,
                    "source_location_cm": point["world_location_cm"],
                    "continuity_query_location_cm": vector_payload(
                        continuity_location
                    ),
                    "projected_location_cm": (
                        vector_payload(location) if location else None
                    ),
                }
            )
            if not success or not location:
                projection_failures.append(
                    {
                        "point_index": int(point["point_index"]),
                        "source_location_cm": point["world_location_cm"],
                    }
                )
            previous_source_location = source_location
            if success and location:
                previous_projected_location = location

        segment_failures = []
        action_complete_segments = 0
        for point_index in range(max(len(points) - 1, 0)):
            start = projected[point_index]
            end = projected[point_index + 1]
            if not start or not end:
                segment_failures.append(
                    {
                        "from_point_index": point_index,
                        "to_point_index": point_index + 1,
                        "reason": "projection_failed",
                    }
                )
                continue
            if distance(start, end) <= 1.0:
                action_complete_segments += 1
                collapsed_segments += 1
                continue
            path = unreal.NavigationSystemV1.find_path_to_location_synchronously(
                world, start, end
            )
            valid = bool(path and path.is_valid())
            partial = bool(path.is_partial()) if path else None
            if valid and not partial:
                action_complete_segments += 1
                continue
            path_points = path.get_editor_property("path_points") if path else []
            segment_failures.append(
                {
                    "from_point_index": point_index,
                    "to_point_index": point_index + 1,
                    "reason": "partial_path" if valid and partial else "invalid_path",
                    "source_from_cm": points[point_index]["world_location_cm"],
                    "source_to_cm": points[point_index + 1]["world_location_cm"],
                    "projected_from_cm": vector_payload(start),
                    "projected_to_cm": vector_payload(end),
                    "path_endpoint_cm": (
                        vector_payload(path_points[-1]) if path_points else None
                    ),
                    "source_point_distance_cm": float(
                        distance(
                            unreal.Vector(
                                x=float(points[point_index]["world_location_cm"][0]),
                                y=float(points[point_index]["world_location_cm"][1]),
                                z=float(points[point_index]["world_location_cm"][2]),
                            ),
                            unreal.Vector(
                                x=float(
                                    points[point_index + 1]["world_location_cm"][0]
                                ),
                                y=float(
                                    points[point_index + 1]["world_location_cm"][1]
                                ),
                                z=float(
                                    points[point_index + 1]["world_location_cm"][2]
                                ),
                            ),
                        )
                    ),
                }
            )

        action_point_count = len(points)
        action_segment_count = max(action_point_count - 1, 0)
        action_projected_count = action_point_count - len(projection_failures)
        action_passed = (
            action_point_count > 0
            and action_projected_count == action_point_count
            and action_complete_segments == action_segment_count
        )
        action_results.append(
            {
                "sequence_index": action.get("sequence_index"),
                "source_action_index": action.get("source_action_index"),
                "action_name": action.get("action_name"),
                "end_action_at_sequence": action.get("end_action_at_sequence"),
                "point_count": action_point_count,
                "projected_point_count": action_projected_count,
                "segment_count": action_segment_count,
                "complete_segment_count": action_complete_segments,
                "passed": action_passed,
                "projection_failures": projection_failures,
                "projection_details": projection_details,
                "segment_failures": segment_failures,
            }
        )
        total_points += action_point_count
        projected_points += action_projected_count
        total_segments += action_segment_count
        complete_segments += action_complete_segments

    first_tutorial_source_actions = {625, 626}
    first_tutorial_results = [
        item
        for item in action_results
        if item["source_action_index"] in first_tutorial_source_actions
    ]
    first_tutorial_passed = (
        len(first_tutorial_results) == len(first_tutorial_source_actions)
        and all(item["passed"] for item in first_tutorial_results)
    )
    passed = (
        len(move_actions) == 63
        and total_points == 1485
        and projected_points == total_points
        and complete_segments == total_segments
    )
    return {
        "passed": passed,
        "first_tutorial_route_passed": first_tutorial_passed,
        "source_report": AUTOMATION_ROUTE_REPORT_PATH,
        "move_action_count": len(move_actions),
        "point_count": total_points,
        "projected_point_count": projected_points,
        "segment_count": total_segments,
        "complete_segment_count": complete_segments,
        "collapsed_segment_count": collapsed_segments,
        "failed_action_count": sum(1 for item in action_results if not item["passed"]),
        "actions": action_results,
    }


def editor_inventory(world):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    route_actor = next(
        (actor for actor in actors if actor_label(actor) == ROUTE_COLLISION_LABEL), None
    )
    route_count = (
        int(route_actor.get_boundary_instance_count()) if route_actor else 0
    )
    nav_bounds = [
        actor
        for actor in actors
        if actor.get_class().get_name() == "KZNavMeshBoundsBox"
    ]
    nav_modifiers = [
        actor
        for actor in actors
        if actor.get_class().get_name() == "KZNavModifierBox"
    ]
    nav_links = [
        actor
        for actor in actors
        if actor.get_actor_label().startswith(NAV_LINK_LABEL_PREFIX)
    ]
    automation_nav_links = [
        actor
        for actor in actors
        if actor.get_actor_label().startswith(AUTOMATION_NAV_LINK_LABEL_PREFIX)
    ]
    recast = [
        actor for actor in actors if "RecastNavMesh" in actor.get_class().get_name()
    ]
    return {
        "actor_count": len(actors),
        "route_collision_actor_count": 1 if route_actor else 0,
        "route_collision_instance_count": route_count,
        "source_nav_bounds_actor_count": len(nav_bounds),
        "source_nav_modifier_actor_count": len(nav_modifiers),
        "source_nav_link_actor_count": len(nav_links),
        "automation_route_nav_link_actor_count": len(automation_nav_links),
        "recast_nav_mesh_actors": [actor_label(actor) for actor in recast],
    }


def start():
    previous = getattr(builtins, STATE_KEY, None)
    if previous and previous.get("handle") is not None:
        try:
            unreal.unregister_slate_post_tick_callback(previous["handle"])
        except Exception:
            pass

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Unable to load HeinMach map")

    state = {
        "handle": None,
        "elapsed": 0.0,
        "phase_elapsed": 0.0,
        "phase": "wait_navigation_unlock",
        "last_progress_log": -10.0,
        "nav_stable_ticks": 0,
        "report": {
            "status": "running",
            "map": MAP_PATH,
            "navigation": {},
            "pie": {},
        },
        "pie_initial_location": None,
        "pie_controller": None,
        "pie_pawn": None,
        "input_subsystem": None,
        "move_action": None,
        "finished": False,
    }

    def set_phase(name):
        state["phase"] = name
        state["phase_elapsed"] = 0.0
        state["last_progress_log"] = -10.0
        unreal.log("KZ_HEINMACH_RUNTIME_VERIFY phase=" + name)

    def finish(error=None):
        if state["finished"]:
            return
        state["finished"] = True
        try:
            if state["input_subsystem"] and state["move_action"]:
                state["input_subsystem"].inject_input_vector_for_action(
                    state["move_action"], unreal.Vector(), [], []
                )
        except Exception:
            pass
        try:
            if level_subsystem.is_in_play_in_editor():
                level_subsystem.editor_request_end_play()
        except Exception:
            pass
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])

        report = state["report"]
        report["error"] = error
        checks = {
            "navigation_inventory": (
                report.get("navigation", {})
                .get("inventory_after_build", {})
                .get("route_collision_instance_count")
                == 2281
                and report.get("navigation", {})
                .get("inventory_after_build", {})
                .get("source_nav_bounds_actor_count")
                == 242
                and report.get("navigation", {})
                .get("inventory_after_build", {})
                .get("source_nav_modifier_actor_count")
                == 26
                and report.get("navigation", {})
                .get("inventory_after_build", {})
                .get("source_nav_link_actor_count")
                == 14
                and report.get("navigation", {})
                .get("inventory_after_build", {})
                .get("automation_route_nav_link_actor_count")
                == 10
            ),
            "navigation_route": bool(
                report.get("navigation", {})
                .get("original_automation_route", {})
                .get("passed")
                and report.get("navigation", {})
                .get("original_automation_route", {})
                .get("first_tutorial_route_passed")
                and report.get("navigation", {})
                .get("source_navigation_links", {})
                .get("passed")
            ),
            "map_saved": bool(report.get("navigation", {}).get("map_saved")),
            "player_spawned": bool(report.get("pie", {}).get("player_spawned")),
            "player_moved": bool(report.get("pie", {}).get("movement", {}).get("passed")),
            "route_wall_blocks_pawn": bool(
                report.get("pie", {}).get("route_wall_collision", {}).get("passed")
            ),
        }
        report["checks"] = checks
        report["all_checks_passed"] = error is None and all(checks.values())
        report["status"] = "passed" if report["all_checks_passed"] else "failed"
        write_json(report)
        unreal.log("KZ_HEINMACH_RUNTIME_VERIFY_RESULT " + json.dumps(report, ensure_ascii=False))
        setattr(builtins, STATE_KEY, state)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def tick(delta_seconds):
        try:
            state["elapsed"] += float(delta_seconds)
            state["phase_elapsed"] += float(delta_seconds)
            phase = state["phase"]

            if state["elapsed"] - state["last_progress_log"] >= 10.0:
                state["last_progress_log"] = state["elapsed"]
                unreal.log(
                    "KZ_HEINMACH_RUNTIME_VERIFY progress phase={} elapsed={:.1f}s".format(
                        phase, state["elapsed"]
                    )
                )

            if state["elapsed"] > 300.0:
                finish("Verification timed out after 300 seconds")
                return

            if phase == "wait_navigation_unlock":
                world = unreal.get_editor_subsystem(
                    unreal.UnrealEditorSubsystem
                ).get_editor_world()
                if not world or not world.get_path_name().startswith(MAP_PATH + "."):
                    return
                locked = unreal.NavigationSystemV1.is_navigation_being_built_or_locked(world)
                state["report"]["navigation"]["initially_locked"] = bool(locked)
                if locked:
                    return
                state["report"]["navigation"]["inventory_before_build"] = editor_inventory(
                    world
                )
                unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
                set_phase("wait_navigation_build")
                return

            if phase == "wait_navigation_build":
                world = unreal.get_editor_subsystem(
                    unreal.UnrealEditorSubsystem
                ).get_editor_world()
                building = unreal.NavigationSystemV1.is_navigation_being_built_or_locked(world)
                inventory = editor_inventory(world)
                has_recast = bool(inventory["recast_nav_mesh_actors"])
                if not building and has_recast:
                    state["nav_stable_ticks"] += 1
                else:
                    state["nav_stable_ticks"] = 0
                if state["nav_stable_ticks"] < 10:
                    return
                state["report"]["navigation"]["inventory_after_build"] = inventory
                state["report"]["navigation"]["tutorial_surface_trace"] = (
                    trace_tutorial_surface(world)
                )
                state["report"]["navigation"]["route_verification"] = (
                    verify_navigation_routes(world)
                )
                state["report"]["navigation"]["source_navigation_links"] = (
                    verify_source_navigation_links(world)
                )
                state["report"]["navigation"]["original_automation_route"] = (
                    verify_original_automation_route(world)
                )
                state["report"]["navigation"]["map_saved"] = bool(
                    level_subsystem.save_current_level()
                )
                level_subsystem.editor_request_begin_play()
                set_phase("wait_pie")
                return

            if phase == "wait_pie":
                worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
                if len(worlds) != 1:
                    return
                world = worlds[0]
                controller = unreal.GameplayStatics.get_player_controller(world, 0)
                pawn = controller.get_controlled_pawn() if controller else None
                if not controller or not pawn:
                    return
                library = unreal.get_default_object(
                    unreal.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary")
                )
                input_subsystem = library.call_method(
                    "GetLocalPlayerSubSystemFromPlayerController",
                    args=(
                        controller,
                        unreal.EnhancedInputLocalPlayerSubsystem.static_class(),
                    ),
                )
                move_action = unreal.load_asset(MOVE_ACTION_PATH)
                if not input_subsystem or not move_action:
                    finish("Enhanced Input movement dependencies are unavailable")
                    return

                location = pawn.get_actor_location()
                movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
                definition = None
                try:
                    definition = pawn.get_editor_property("character_definition")
                except Exception:
                    pass
                skeletal_components = pawn.get_components_by_class(
                    unreal.SkeletalMeshComponent
                )
                meshes = []
                for component in skeletal_components:
                    mesh = component.get_editor_property("skeletal_mesh_asset")
                    meshes.append(
                        {
                            "component": component.get_name(),
                            "mesh": mesh.get_path_name() if mesh else None,
                            "attach_parent": (
                                component.get_attach_parent().get_name()
                                if component.get_attach_parent()
                                else None
                            ),
                        }
                    )
                state["report"]["pie"].update(
                    {
                        "player_spawned": True,
                        "world": world.get_path_name(),
                        "controller_class": controller.get_class().get_path_name(),
                        "pawn_class": pawn.get_class().get_path_name(),
                        "spawn_location_cm": vector_payload(location),
                        "distance_from_expected_player_start_cm": distance(
                            location, EXPECTED_PLAYER_START
                        ),
                        "source_anchor_location_cm": vector_payload(SOURCE_START),
                        "expected_player_start_location_cm": vector_payload(
                            EXPECTED_PLAYER_START
                        ),
                        "character_movement_class": (
                            movement.get_class().get_path_name() if movement else None
                        ),
                        "character_definition": (
                            definition.get_path_name() if definition else None
                        ),
                        "skeletal_mesh_components": meshes,
                    }
                )
                state["pie_controller"] = controller
                state["pie_pawn"] = pawn
                state["pie_initial_location"] = location
                state["input_subsystem"] = input_subsystem
                state["move_action"] = move_action
                set_phase("move_player")
                return

            if phase == "move_player":
                pawn = state["pie_pawn"]
                if not pawn:
                    finish("Player pawn was destroyed during movement test")
                    return
                amount = 1.0 if state["phase_elapsed"] < 2.0 else 0.0
                state["input_subsystem"].inject_input_vector_for_action(
                    state["move_action"], unreal.Vector(x=amount, y=0.0, z=0.0), [], []
                )
                if state["phase_elapsed"] < 3.0:
                    return
                final_location = pawn.get_actor_location()
                initial_location = state["pie_initial_location"]
                planar_displacement = math.hypot(
                    final_location.x - initial_location.x,
                    final_location.y - initial_location.y,
                )
                movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
                grounded = bool(movement and movement.is_moving_on_ground())
                state["report"]["pie"]["movement"] = {
                    "passed": planar_displacement >= 50.0 and abs(
                        final_location.z - initial_location.z
                    ) < 500.0,
                    "input_action": MOVE_ACTION_PATH,
                    "injected_value": [1.0, 0.0, 0.0],
                    "input_duration_seconds": 2.0,
                    "initial_location_cm": vector_payload(initial_location),
                    "final_location_cm": vector_payload(final_location),
                    "planar_displacement_cm": float(planar_displacement),
                    "vertical_displacement_cm": float(
                        final_location.z - initial_location.z
                    ),
                    "moving_on_ground_after_release": grounded,
                    "velocity_cm_per_second": (
                        vector_payload(movement.velocity) if movement else None
                    ),
                }
                world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
                state["report"]["pie"]["route_wall_collision"] = (
                    prove_route_wall_blocks_pawn(world, SOURCE_START)
                )
                finish()
        except Exception as exception:
            state["report"]["traceback"] = traceback.format_exc()
            finish(str(exception))

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    setattr(builtins, STATE_KEY, state)
    unreal.log("KZ_HEINMACH_RUNTIME_VERIFY started")


try:
    start()
except Exception as exception:
    payload = {
        "status": "failed",
        "map": MAP_PATH,
        "error": str(exception),
        "traceback": traceback.format_exc(),
        "all_checks_passed": False,
    }
    write_json(payload)
    unreal.log_error("KZ_HEINMACH_RUNTIME_VERIFY startup failed: " + str(exception))
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)
    unreal.SystemLibrary.quit_editor()
