"""Extract authoritative HeinMach route camera anchors from FModel PlayerStarts.

Earlier visual probes used arbitrary sub-level centers and several landed inside
large background rocks.  This audit resolves the actual xxPlayerStart attachment
chains from ``HeinMach_Spawn_Main01.json`` and produces eye-level cameras facing
the next route anchor.  It is read-only and does not restore spawn gameplay.
"""

from __future__ import annotations

import json
import math
import os
import re

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_JSON = os.path.join(
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
    "HeinMach_PlayableCameraAnchors.json",
)
LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")
ROUTE_TAGS = (
    "MISSION01_START",
    "Tomb_01",
    "Tomb_02",
    "Tomb_03",
    "Tomb_04",
    "Mission01_Boss_Start",
)
EYE_HEIGHT_CM = 170.0


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def local_index(reference):
    path = reference.get("ObjectPath", "") if isinstance(reference, dict) else ""
    match = LOCAL_INDEX_RE.search(path)
    return int(match.group(1)) if match else None


def vector(value, keys, defaults):
    value = value if isinstance(value, dict) else {}
    return [float(value.get(key, default)) for key, default in zip(keys, defaults)]


def local_transform(obj):
    properties = obj.get("Properties", {}) if isinstance(obj, dict) else {}
    location = vector(properties.get("RelativeLocation"), ("X", "Y", "Z"), (0, 0, 0))
    rotation = vector(
        properties.get("RelativeRotation"),
        ("Pitch", "Yaw", "Roll"),
        (0, 0, 0),
    )
    scale = vector(properties.get("RelativeScale3D"), ("X", "Y", "Z"), (1, 1, 1))
    return unreal.Transform(
        location=unreal.Vector(x=location[0], y=location[1], z=location[2]),
        rotation=unreal.Rotator(
            pitch=rotation[0], yaw=rotation[1], roll=rotation[2]
        ),
        scale=unreal.Vector(x=scale[0], y=scale[1], z=scale[2]),
    )


def resolve_world_transform(objects, index, cache, stack=()):
    if index in cache:
        return cache[index]
    if index is None or index < 0 or index >= len(objects):
        return unreal.Transform()
    if index in stack:
        raise RuntimeError("Attachment cycle at source object {}".format(index))
    obj = objects[index]
    result = local_transform(obj)
    parent_index = local_index((obj.get("Properties") or {}).get("AttachParent"))
    if parent_index is not None:
        parent = resolve_world_transform(objects, parent_index, cache, stack + (index,))
        result = unreal.MathLibrary.compose_transforms(result, parent)
    cache[index] = result
    return result


def camera_rotation(start, target):
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    dz = target[2] - start[2]
    horizontal = math.sqrt(dx * dx + dy * dy)
    return {
        "pitch": math.degrees(math.atan2(dz, horizontal)),
        "yaw": math.degrees(math.atan2(dy, dx)),
        "roll": 0.0,
    }


def main():
    if not os.path.isfile(SOURCE_JSON):
        raise RuntimeError("PlayerStart source JSON is missing: " + SOURCE_JSON)
    with open(SOURCE_JSON, "r", encoding="utf-8-sig") as source:
        objects = json.load(source)

    cache = {}
    by_tag = {}
    all_starts = []
    for object_index, obj in enumerate(objects):
        if obj.get("Type") != "xxPlayerStart":
            continue
        properties = obj.get("Properties", {}) or {}
        tag = properties.get("PlayerStartTag") or obj.get("Name")
        root_index = local_index(properties.get("RootComponent"))
        transform = resolve_world_transform(objects, root_index, cache)
        location = [float(value) for value in transform.translation.to_tuple()]
        rotation = transform.rotation.rotator()
        record = {
            "source_object_index": object_index,
            "root_component_index": root_index,
            "actor_name": obj.get("Name"),
            "tag": tag,
            "world_location_cm": location,
            "world_rotation_degrees": {
                "pitch": float(rotation.pitch),
                "yaw": float(rotation.yaw),
                "roll": float(rotation.roll),
            },
        }
        all_starts.append(record)
        by_tag[tag] = record

    missing = [tag for tag in ROUTE_TAGS if tag not in by_tag]
    if missing:
        raise RuntimeError("Route PlayerStarts are missing: " + ", ".join(missing))

    cameras = []
    for index, tag in enumerate(ROUTE_TAGS):
        anchor = by_tag[tag]
        location = list(anchor["world_location_cm"])
        eye = [location[0], location[1], location[2] + EYE_HEIGHT_CM]
        if index + 1 < len(ROUTE_TAGS):
            target = by_tag[ROUTE_TAGS[index + 1]]["world_location_cm"]
        else:
            yaw_radians = math.radians(anchor["world_rotation_degrees"]["yaw"])
            target = [
                eye[0] + math.cos(yaw_radians) * 1000.0,
                eye[1] + math.sin(yaw_radians) * 1000.0,
                eye[2],
            ]
        source_rotation = dict(anchor["world_rotation_degrees"])
        cameras.append(
            {
                "tag": tag,
                "location_cm": eye,
                "rotation_degrees": source_rotation,
                "inspection_rotation_degrees": {
                    "pitch": -4.0,
                    "yaw": source_rotation["yaw"],
                    "roll": 0.0,
                },
                "route_to_next_rotation_degrees": camera_rotation(eye, target),
                "look_at_cm": target,
                "basis": "authoritative xxPlayerStart attachment chain and source-facing rotation",
            }
        )

    payload = {
        "status": "audited",
        "source_json": SOURCE_JSON,
        "source_player_start_count": len(all_starts),
        "route_order": list(ROUTE_TAGS),
        "eye_height_cm": EYE_HEIGHT_CM,
        "all_player_starts": all_starts,
        "route_cameras": cameras,
        "usage_note": "Use source-facing rotation for visual inspection; route-to-next rotation can point through curved-path cave walls. No spawn actors are restored by this audit.",
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({"report": REPORT_PATH, "route_camera_count": len(cameras)}))
    return payload


if __name__ == "__main__":
    main()
