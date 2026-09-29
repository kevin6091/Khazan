"""Extract the original HeinMach recorded player route from FModel metadata.

The source xxAutomationTestActor contains the ordered MoveTo, combat, pickup,
checkpoint, and level-object actions used by the original level automation.
MoveTo spline control points are retained verbatim and converted to world
coordinates using their root component locations.
"""

from __future__ import annotations

import json
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_SPAWN_JSON = os.path.join(
    FMODEL_ROOT,
    "Exports",
    "BBQ",
    "Content",
    "_Kazan_",
    "Level",
    "HeinMach",
    "HeinMach_Spawn_Main01.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_OriginalAutomationRoute.json",
)
LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def local_index(reference):
    path = reference.get("ObjectPath", "") if isinstance(reference, dict) else ""
    match = LOCAL_INDEX_RE.search(path)
    return int(match.group(1)) if match else None


def vector(value, defaults=(0.0, 0.0, 0.0)):
    value = value if isinstance(value, dict) else {}
    return [
        float(value.get("X", defaults[0])),
        float(value.get("Y", defaults[1])),
        float(value.get("Z", defaults[2])),
    ]


def reference_payload(reference):
    if not isinstance(reference, dict):
        return None
    return {
        "source_index": local_index(reference),
        "object_name": reference.get("ObjectName"),
        "object_path": reference.get("ObjectPath"),
    }


def extract_move_action(objects, source_index, action, sequence_index):
    properties = action.get("Properties") or {}
    spline_actor_index = local_index(properties.get("MoveSplineActor"))
    if spline_actor_index is None:
        raise RuntimeError(
            "Recorded MoveTo action has no MoveSplineActor: {}".format(source_index)
        )
    spline_actor = objects[spline_actor_index]
    root_index = local_index(
        (spline_actor.get("Properties") or {}).get("RootComponent")
    )
    if root_index is None:
        raise RuntimeError(
            "Automation spline actor has no root: {}".format(spline_actor_index)
        )
    root = objects[root_index]
    root_properties = root.get("Properties") or {}
    attach_parent = local_index(root_properties.get("AttachParent"))
    rotation = vector(
        root_properties.get("RelativeRotation"), defaults=(0.0, 0.0, 0.0)
    )
    scale = vector(root_properties.get("RelativeScale3D"), defaults=(1.0, 1.0, 1.0))
    if attach_parent is not None or any(abs(value) > 0.0001 for value in rotation):
        raise RuntimeError(
            "Unexpected transformed automation spline root {}: parent={} rotation={}".format(
                root_index, attach_parent, rotation
            )
        )
    if any(abs(value - 1.0) > 0.0001 for value in scale):
        raise RuntimeError(
            "Unexpected automation spline scale {}: {}".format(root_index, scale)
        )

    origin = vector(root_properties.get("RelativeLocation"))
    spline_points = (
        (((root_properties.get("SplineCurves") or {}).get("Position") or {}).get("Points"))
        or []
    )
    custom_data = root_properties.get("ArrayCustomData") or []
    points = []
    for point_index, point in enumerate(spline_points):
        local_location = vector(point.get("OutVal"))
        movement = custom_data[point_index] if point_index < len(custom_data) else {}
        points.append(
            {
                "point_index": point_index,
                "input_key": float(point.get("InVal", point_index)),
                "interp_mode": point.get("InterpMode"),
                "local_location_cm": local_location,
                "world_location_cm": [
                    origin[axis] + local_location[axis] for axis in range(3)
                ],
                "move_type": movement.get("MoveType"),
                "wait_time_seconds": (
                    float(movement["WaitTime"])
                    if "WaitTime" in movement
                    else None
                ),
            }
        )
    if len(custom_data) not in (0, len(points)):
        raise RuntimeError(
            "Automation spline custom-data count mismatch at root {}: {} vs {}".format(
                root_index, len(custom_data), len(points)
            )
        )
    return {
        "sequence_index": sequence_index,
        "source_action_index": source_index,
        "action_type": action.get("Type"),
        "action_name": action.get("Name"),
        "end_action_at_sequence": bool(properties.get("bEndActionAtSequence", False)),
        "source_spline_actor_index": spline_actor_index,
        "source_spline_actor_name": spline_actor.get("Name"),
        "source_spline_root_index": root_index,
        "source_spline_root_type": root.get("Type"),
        "source_origin_cm": origin,
        "source_rotation_degrees": rotation,
        "source_scale": scale,
        "point_count": len(points),
        "points": points,
    }


def extract_non_move_action(source_index, action, sequence_index):
    properties = action.get("Properties") or {}
    references = {}
    for key, value in properties.items():
        if isinstance(value, dict) and "ObjectPath" in value:
            references[key] = reference_payload(value)
        elif isinstance(value, list) and value and all(
            isinstance(item, dict) and "ObjectPath" in item for item in value
        ):
            references[key] = [reference_payload(item) for item in value]
    return {
        "sequence_index": sequence_index,
        "source_action_index": source_index,
        "action_type": action.get("Type"),
        "action_name": action.get("Name"),
        "references": references,
    }


def main():
    if not os.path.isfile(SOURCE_SPAWN_JSON):
        raise RuntimeError("Missing FModel source: " + SOURCE_SPAWN_JSON)
    objects = load_json(SOURCE_SPAWN_JSON)
    test_actors = [
        (index, item)
        for index, item in enumerate(objects)
        if item.get("Type") == "xxAutomationTestActor"
    ]
    if len(test_actors) != 1:
        raise RuntimeError(
            "Expected one xxAutomationTestActor, found {}".format(len(test_actors))
        )
    test_actor_index, test_actor = test_actors[0]
    groups = (test_actor.get("Properties") or {}).get("GroupActions") or []
    if len(groups) != 1:
        raise RuntimeError("Expected one recorded automation group")

    actions = []
    move_actions = []
    for sequence_index, reference in enumerate(groups[0].get("Actions") or []):
        source_index = local_index(reference)
        if source_index is None:
            raise RuntimeError("Automation action reference has no local index")
        action = objects[source_index]
        if action.get("Type") == "xxAutomationAction_MoveTo":
            record = extract_move_action(
                objects, source_index, action, sequence_index
            )
            move_actions.append(record)
        else:
            record = extract_non_move_action(source_index, action, sequence_index)
        actions.append(record)

    point_count = sum(item["point_count"] for item in move_actions)
    if len(actions) != 125 or len(move_actions) != 63 or point_count != 1485:
        raise RuntimeError(
            "Unexpected automation inventory: actions={} moves={} points={}".format(
                len(actions), len(move_actions), point_count
            )
        )
    payload = {
        "status": "extracted",
        "source_spawn_json": SOURCE_SPAWN_JSON,
        "source_test_actor_index": test_actor_index,
        "source_test_actor_name": test_actor.get("Name"),
        "transform_basis": (
            "source xxSplineComponent RelativeLocation plus local Position.OutVal; "
            "all recorded roots have no parent, zero rotation, and unit scale"
        ),
        "action_count": len(actions),
        "move_action_count": len(move_actions),
        "move_point_count": point_count,
        "actions": actions,
        "move_actions": move_actions,
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({key: payload[key] for key in (
        "status",
        "source_test_actor_index",
        "source_test_actor_name",
        "action_count",
        "move_action_count",
        "move_point_count",
    )}, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    main()
