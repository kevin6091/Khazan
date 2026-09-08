"""Extract source spawn/checkpoint and streaming-volume context, without gameplay.

Run inside the editor for exact Unreal FTransform composition. Does not load a
map, spawn actors, or change scene objects. Metadata is suitable for subsequent
camera review and an environment-only PlayerStart restoration.
"""

import hashlib
import json
import os
import re

import unreal

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
FMODEL = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE = os.path.join(FMODEL, "Exports", "BBQ", "Content", "_Kazan_", "Level", "StormPass")
DEST = os.path.join(ROOT, "Content", "_Art", "Kazan", "Environment", "StormPass", "Metadata", "StormPass_PlayableCameraAnchors.json")


def read(filename):
    with open(os.path.join(SOURCE, filename), encoding="utf-8-sig") as stream:
        return json.load(stream)


def local_index(reference):
    if not isinstance(reference, dict):
        return None
    match = re.search(r"\.(\d+)$", reference.get("ObjectPath", ""))
    return int(match.group(1)) if match else None


def vector(value, default=0):
    return unreal.Vector(*(float((value or {}).get(axis, default)) for axis in "XYZ"))


def local_transform(properties):
    r = properties.get("RelativeRotation") or {}
    return unreal.Transform(location=vector(properties.get("RelativeLocation")),
                            rotation=unreal.Rotator(pitch=r.get("Pitch", 0), yaw=r.get("Yaw", 0), roll=r.get("Roll", 0)),
                            scale=vector(properties.get("RelativeScale3D"), 1))


def component_transform(exports, index, stack=()):
    if index is None or index < 0 or index >= len(exports) or index in stack:
        raise RuntimeError("Invalid/cyclic source component chain: " + repr(stack + (index,)))
    p = exports[index].get("Properties") or {}
    result = local_transform(p)
    parent = local_index(p.get("AttachParent"))
    if parent is not None:
        result = unreal.MathLibrary.compose_transforms(result, component_transform(exports, parent, stack + (index,)))
    return result


def transform_record(transform):
    p, r = transform.translation, transform.rotation.rotator()
    return {"location_cm": [p.x, p.y, p.z], "rotation_degrees": [r.pitch, r.yaw, r.roll]}


def main():
    spawn = read("StormPass_Spawn_Main01.json")
    world = read("StormPass_All.json")
    anchors = []
    for index, actor in enumerate(spawn):
        if actor.get("Type") != "xxPlayerStart":
            continue
        properties = actor.get("Properties") or {}
        root = local_index(properties.get("RootComponent"))
        pose = transform_record(component_transform(spawn, root))
        anchors.append({"source_actor_index": index, "source_name": actor["Name"],
                        "source_root_index": root, "source_tag": properties.get("PlayerStartTag", ""),
                        "source_json": "StormPass_Spawn_Main01.json", **pose,
                        "review_camera_location_cm": [*pose["location_cm"][:2], pose["location_cm"][2] + 80]})
    volumes = []
    streaming = []
    for index, actor in enumerate(world):
        p = actor.get("Properties") or {}
        if actor.get("Type") == "xxLevelStreamingVolume":
            root = local_index(p.get("RootComponent"))
            volumes.append({"source_index": index, "name": actor["Name"],
                            "streaming_levels": p.get("StreamingLevelNames", []),
                            "usage": p.get("StreamingUsage", "SVB_LoadingAndVisibility"),
                            **transform_record(component_transform(world, root))})
        if str(actor.get("Type", "")).startswith("LevelStreaming"):
            streaming.append({"name": actor["Name"], "class": actor["Type"],
                              "asset": (p.get("WorldAsset") or {}).get("AssetPathName"),
                              "initially_loaded": p.get("bInitiallyLoaded"),
                              "should_be_visible_serialized": p.get("bShouldBeVisible", False)})
    hashes = {}
    for name in ("StormPass_Spawn_Main01.json", "StormPass_All.json"):
        with open(os.path.join(SOURCE, name), "rb") as stream:
            hashes[name] = hashlib.sha256(stream.read()).hexdigest()
    payload = {"schema_version": 1, "level": "StormPass", "source_hashes": hashes,
               "boundary": "Environment spawn/camera anchors only. No gameplay, AI, loadout or streaming controller.",
               "default_start": "Mission02_Start", "anchors": anchors, "streaming_volumes": volumes,
               "streaming_layers": streaming}
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    with open(DEST, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"metadata": DEST, "anchors": len(anchors), "streaming_volumes": len(volumes), "layers": len(streaming)}))
    return payload


if __name__ == "__main__":
    main()
