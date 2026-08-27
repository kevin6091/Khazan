#!/usr/bin/env python3
"""Analyze FModel HeinMach exports and preserve reconstruction metadata.

This script is intentionally independent from Unreal's Python runtime. It reads
FModel property JSON and USDA files, then writes deterministic manifests that
the Unreal import script can consume.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


OBJECT_REF_KEYS = {"ObjectName", "ObjectPath"}
LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")
USD_REF_RE = re.compile(r"@([^@]+)@")


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def package_from_object_path(path: str | None) -> str | None:
    if not path or not isinstance(path, str):
        return None
    normalized = path.replace("\\", "/")
    if normalized.startswith("/Script/"):
        return None
    if normalized.startswith("/Game/"):
        normalized = "BBQ/Content/" + normalized[len("/Game/"):]
    elif normalized.startswith("/Engine/"):
        normalized = "Engine/Content/" + normalized[len("/Engine/"):]
    if not normalized.startswith(("BBQ/Content/", "Engine/Content/")):
        return None
    slash = normalized.rfind("/")
    dot = normalized.find(".", slash + 1)
    return normalized[:dot] if dot >= 0 else normalized


def object_ref_kind(key_path: tuple[str, ...], object_name: str) -> str:
    key = ".".join(key_path).lower()
    name = object_name.lower()
    if "staticmesh" in key or name.startswith("staticmesh'"):
        return "static_mesh"
    if "skeletalmesh" in key or name.startswith("skeletalmesh'"):
        return "skeletal_mesh"
    if "texture" in key or name.startswith(("texture2d'", "texturecube'", "virtualtexture2d'")):
        return "texture"
    if "material" in key or name.startswith(("material'", "materialinstance", "materialfunction")):
        return "material"
    if key_path and key_path[-1].lower() == "template":
        return "template"
    if key_path and key_path[-1].lower() in {"class", "superstruct"}:
        return "class"
    return "other"


def walk_object_refs(value: Any, key_path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], dict[str, Any]]]:
    if isinstance(value, dict):
        if OBJECT_REF_KEYS.issubset(value.keys()) and isinstance(value.get("ObjectPath"), str):
            yield key_path, value
        for key, child in value.items():
            yield from walk_object_refs(child, key_path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_object_refs(child, key_path + (str(index),))


def is_actor(obj: dict[str, Any]) -> bool:
    outer = obj.get("Outer")
    if not isinstance(outer, dict):
        return False
    outer_name = str(outer.get("ObjectName", ""))
    return outer_name.startswith("Level'") and "PersistentLevel" in outer_name


def local_index(reference: Any, package: str) -> int | None:
    if not isinstance(reference, dict):
        return None
    path = reference.get("ObjectPath")
    if not isinstance(path, str) or package_from_object_path(path) != package:
        return None
    match = LOCAL_INDEX_RE.search(path)
    return int(match.group(1)) if match else None


def vector(value: Any, axes: tuple[str, ...]) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, float] = {}
    for axis in axes:
        raw = value.get(axis)
        if not isinstance(raw, (int, float)):
            return None
        result[axis.lower()] = float(raw)
    return result


def actor_transform(actor: dict[str, Any], objects: list[dict[str, Any]], package: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    properties = actor.get("Properties") if isinstance(actor.get("Properties"), dict) else {}
    component: dict[str, Any] | None = None
    index = local_index(properties.get("RootComponent"), package)
    if index is not None and 0 <= index < len(objects):
        candidate = objects[index]
        if isinstance(candidate, dict):
            component = candidate

    component_properties = component.get("Properties") if isinstance(component, dict) and isinstance(component.get("Properties"), dict) else {}
    transform_source = component_properties or properties

    location = (
        vector(transform_source.get("RelativeLocation"), ("X", "Y", "Z"))
        or vector(transform_source.get("ActorLocation"), ("X", "Y", "Z"))
        or {"x": 0.0, "y": 0.0, "z": 0.0}
    )
    rotation = (
        vector(transform_source.get("RelativeRotation"), ("Pitch", "Yaw", "Roll"))
        or vector(transform_source.get("ActorRotation"), ("Pitch", "Yaw", "Roll"))
        or {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    )
    scale = vector(transform_source.get("RelativeScale3D"), ("X", "Y", "Z")) or {"x": 1.0, "y": 1.0, "z": 1.0}
    return {
        "location_cm": location,
        "rotation_degrees": rotation,
        "scale": scale,
    }, component


def actor_object_path(package: str, index: int) -> str:
    return f"{package}.{index}"


def template_package(actor: dict[str, Any]) -> str | None:
    template = actor.get("Template")
    if isinstance(template, dict):
        return package_from_object_path(template.get("ObjectPath"))
    class_value = actor.get("Class")
    if isinstance(class_value, str) and "'" in class_value:
        inner = class_value.split("'", 1)[1].rstrip("'")
        return package_from_object_path(inner)
    return None


def child_components(package: str, actor_index: int, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target = actor_object_path(package, actor_index)
    result: list[dict[str, Any]] = []
    for index, obj in enumerate(objects):
        outer = obj.get("Outer")
        if not isinstance(outer, dict) or outer.get("ObjectPath") != target:
            continue
        result.append({
            "source_object_index": index,
            "type": obj.get("Type"),
            "name": obj.get("Name"),
            "template": obj.get("Template"),
            "properties": obj.get("Properties", {}),
        })
    return result


def actor_record(level_name: str, package: str, index: int, actor: dict[str, Any], objects: list[dict[str, Any]], include_properties: bool) -> dict[str, Any]:
    transform, component = actor_transform(actor, objects, package)
    record: dict[str, Any] = {
        "source_level": level_name,
        "source_package": package,
        "source_object_index": index,
        "actor_type": actor.get("Type"),
        "actor_name": actor.get("Name"),
        "class": actor.get("Class"),
        "template_package": template_package(actor),
        "transform": transform,
        "root_component_type": component.get("Type") if isinstance(component, dict) else None,
        "root_component_template": component.get("Template") if isinstance(component, dict) else None,
    }
    if include_properties:
        record["properties"] = actor.get("Properties", {})
        record["components"] = child_components(package, index, objects)
    return record


def classify_actor(actor: dict[str, Any]) -> set[str]:
    haystack = " ".join(str(actor.get(key, "")) for key in ("Type", "Name", "Class")).lower()
    actor_type = str(actor.get("Type", "")).lower()
    categories: set[str] = set()
    if "spawnhandler_character" in haystack:
        categories.add("monster_spawn")
    if "playerstart" in haystack or "respawn" in haystack:
        categories.add("player_respawn")
    if "spawnhandler" in haystack or "spawnarea" in haystack or "spawner" in haystack:
        categories.add("spawn_other")
    if any(token in actor_type for token in ("pointlight", "spotlight", "directionallight", "rectlight", "skylight")):
        categories.add("light")
    if "reflectioncapture" in actor_type:
        categories.add("reflection_capture")
    if actor_type.startswith(("wep_", "was_", "wsl_", "wdl_", "fog_", "emp_", "ppw_", "erp_")) or any(
        token in actor_type for token in ("environment", "weather", "skyatmosphere", "volumetricmist")
    ):
        categories.add("environment_controller")
    return categories


def scan_world_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        objects = json.load(handle)
    if not isinstance(objects, list):
        raise ValueError(f"Expected a JSON array: {path}")

    package = f"BBQ/Content/_Kazan_/Level/HeinMach/{path.stem}"
    type_counts: Counter[str] = Counter()
    refs_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    template_placements: Counter[str] = Counter()
    placements: list[dict[str, Any]] = []
    metadata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    streaming_levels: list[dict[str, Any]] = []

    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            continue
        obj_type = str(obj.get("Type", "Unknown"))
        type_counts[obj_type] += 1

        for key_path, ref in walk_object_refs(obj):
            ref_path = str(ref.get("ObjectPath", ""))
            ref_package = package_from_object_path(ref_path)
            if not ref_package or ref_package == package:
                continue
            kind = object_ref_kind(key_path, str(ref.get("ObjectName", "")))
            refs_by_kind[kind][ref_package] += 1

        if obj_type.startswith("LevelStreaming"):
            props = obj.get("Properties") if isinstance(obj.get("Properties"), dict) else {}
            streaming_levels.append({
                "source_object_index": index,
                "type": obj_type,
                "name": obj.get("Name"),
                "properties": props,
            })

        if not is_actor(obj):
            continue

        placement = actor_record(path.stem, package, index, obj, objects, include_properties=False)
        placements.append(placement)
        if placement["template_package"]:
            template_placements[str(placement["template_package"])] += 1

        for category in classify_actor(obj):
            metadata[category].append(actor_record(path.stem, package, index, obj, objects, include_properties=True))

    return {
        "level_name": path.stem,
        "package": package,
        "object_count": len(objects),
        "actor_count": len(placements),
        "type_counts": type_counts,
        "refs_by_kind": refs_by_kind,
        "template_placements": template_placements,
        "placements": placements,
        "metadata": metadata,
        "streaming_levels": streaming_levels,
    }


def find_exported_candidates(export_root: Path, package: str) -> list[str]:
    relative = Path(*package.split("/"))
    base = export_root / relative
    roots = [base, export_root / "Exports" / relative]
    suffixes = (".json", ".usda", ".fbx", ".psk", ".pskx", ".uemodel", ".uasset", ".umap")
    found: list[str] = []
    for candidate_root in roots:
        for suffix in suffixes:
            candidate = candidate_root.with_suffix(suffix)
            if candidate.is_file():
                found.append(str(candidate))
    return sorted(set(found))


def scan_usd_graph(export_root: Path) -> dict[str, Any]:
    files = sorted(export_root.rglob("*.usda"))
    references: list[dict[str, Any]] = []
    for source in files:
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in USD_REF_RE.finditer(text):
            raw = match.group(1)
            resolved = (source.parent / Path(raw.replace("/", str(Path('/'))))).resolve()
            references.append({
                "source": str(source),
                "reference": raw,
                "resolved": str(resolved),
                "exists": resolved.is_file(),
            })
    return {
        "file_count": len(files),
        "reference_count": len(references),
        "unique_reference_count": len({item["resolved"] for item in references}),
        "missing_references": [item for item in references if not item["exists"]],
    }


def counter_to_rows(counter: Counter[str], limit: int | None = None) -> list[dict[str, Any]]:
    rows = [{"name": name, "count": count} for name, count in counter.most_common(limit)]
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmodel-root", type=Path, default=Path(r"C:\Users\user\Desktop\카잔"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    fmodel_root = args.fmodel_root.resolve()
    properties_dir = fmodel_root / "Exports" / "BBQ" / "Content" / "_Kazan_" / "Level" / "HeinMach"
    if not properties_dir.is_dir():
        raise FileNotFoundError(f"FModel HeinMach properties directory not found: {properties_dir}")

    world_jsons = sorted(path for path in properties_dir.glob("HeinMach_*.json") if path.parent == properties_dir)
    scans: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in world_jsons:
        try:
            scans.append(scan_world_json(path))
        except Exception as exc:  # Keep the batch useful when one package is malformed.
            errors.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})

    global_types: Counter[str] = Counter()
    global_refs: dict[str, Counter[str]] = defaultdict(Counter)
    global_templates: Counter[str] = Counter()
    placements: list[dict[str, Any]] = []
    metadata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    streaming_levels: list[dict[str, Any]] = []
    level_summaries: list[dict[str, Any]] = []

    for scan in scans:
        global_types.update(scan["type_counts"])
        global_templates.update(scan["template_placements"])
        placements.extend(scan["placements"])
        for kind, counter in scan["refs_by_kind"].items():
            global_refs[kind].update(counter)
        for kind, entries in scan["metadata"].items():
            metadata[kind].extend(entries)
        for entry in scan["streaming_levels"]:
            streaming_levels.append({"source_level": scan["level_name"], **entry})
        level_summaries.append({
            "level_name": scan["level_name"],
            "package": scan["package"],
            "object_count": scan["object_count"],
            "actor_count": scan["actor_count"],
        })

    template_status = []
    for package, count in global_templates.most_common():
        candidates = find_exported_candidates(fmodel_root, package)
        template_status.append({
            "package": package,
            "placement_count": count,
            "exported_files": candidates,
            "has_properties_json": any(item.lower().endswith(".json") for item in candidates),
        })

    asset_refs: dict[str, list[dict[str, Any]]] = {}
    for kind, counter in sorted(global_refs.items()):
        asset_refs[kind] = [
            {
                "package": package,
                "reference_count": count,
                "exported_files": find_exported_candidates(fmodel_root, package),
            }
            for package, count in counter.most_common()
        ]

    usd_graph = scan_usd_graph(fmodel_root)
    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    output_dir = args.output_dir.resolve()

    level_data = {
        "schema_version": 1,
        "source_game": "The First Berserker: Khazan",
        "level": "HeinMach",
        "generated_at": generated_at,
        "coordinate_system": {
            "source": "Unreal Engine centimeters, Z-up",
            "note": "FModel USDA negates Unreal Y for USD coordinates; JSON transforms below remain original Unreal coordinates.",
        },
        "placement_policy": "Preserved only. Spawn and light metadata are not automatically spawned by the import script.",
        "source_world_json_count": len(world_jsons),
        "parsed_world_json_count": len(scans),
        "parse_errors": errors,
        "level_summaries": level_summaries,
        "streaming_levels": streaming_levels,
        "player_respawn_points": metadata.get("player_respawn", []),
        "monster_spawns": metadata.get("monster_spawn", []),
        "other_spawn_handlers": metadata.get("spawn_other", []),
        "lights": metadata.get("light", []),
        "reflection_captures": metadata.get("reflection_capture", []),
        "environment_controllers": metadata.get("environment_controller", []),
        "counts": {
            "player_respawn_points": len(metadata.get("player_respawn", [])),
            "monster_spawns": len(metadata.get("monster_spawn", [])),
            "other_spawn_handlers": len(metadata.get("spawn_other", [])),
            "lights": len(metadata.get("light", [])),
            "reflection_captures": len(metadata.get("reflection_capture", [])),
            "environment_controllers": len(metadata.get("environment_controller", [])),
        },
    }

    manifest = {
        "schema_version": 1,
        "level": "HeinMach",
        "generated_at": generated_at,
        "fmodel_root": str(fmodel_root),
        "properties_directory": str(properties_dir),
        "level_summaries": level_summaries,
        "total_actor_placements": len(placements),
        "actor_type_histogram": counter_to_rows(global_types),
        "template_packages": template_status,
        "asset_references": asset_refs,
        "usd_graph": usd_graph,
    }

    missing = {
        "schema_version": 1,
        "level": "HeinMach",
        "generated_at": generated_at,
        "parse_errors": errors,
        "usd_missing_references": usd_graph["missing_references"],
        "template_packages_missing_properties_json": [
            item for item in template_status if not item["has_properties_json"]
        ],
        "asset_packages_without_exported_files": {
            kind: [item for item in rows if not item["exported_files"]]
            for kind, rows in asset_refs.items()
        },
    }

    json_dump(output_dir / "HeinMach_LevelData.json", level_data)
    json_dump(output_dir / "HeinMach_AssetManifest.json", manifest)
    json_dump(output_dir / "HeinMach_EnvironmentPlacements.json", {
        "schema_version": 1,
        "level": "HeinMach",
        "generated_at": generated_at,
        "placements": placements,
    })
    json_dump(output_dir / "HeinMach_MissingAssets.json", missing)

    summary = {
        "world_json_files": len(world_jsons),
        "parsed": len(scans),
        "errors": len(errors),
        "actors": len(placements),
        "template_packages": len(template_status),
        "templates_missing_json": sum(not item["has_properties_json"] for item in template_status),
        "monster_spawns": len(metadata.get("monster_spawn", [])),
        "player_respawn_points": len(metadata.get("player_respawn", [])),
        "lights": len(metadata.get("light", [])),
        "usd_files": usd_graph["file_count"],
        "usd_missing_references": len(usd_graph["missing_references"]),
        "output_dir": str(output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
