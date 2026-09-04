"""Analyze the exported StormPass worlds before any Unreal reconstruction.

The survey is intentionally read-only with respect to Unreal content.  It
separates visual environment layers from gameplay/cinematic layers, records
all source transforms and references, and keeps Fog in a deferred manifest so
that it cannot be restored before geometry, materials, and lighting pass their
audits.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
HEINMACH_ANALYZER = SCRIPT_DIR.parent / "HeinMach" / "analyze_heinmach.py"
FMODEL_ROOT = Path.home() / "Desktop" / "카잔"
SOURCE_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
WORLD_ROOT = (
    FMODEL_ROOT
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
METADATA_ROOT = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
)
REPORT_PATH = (
    PROJECT_ROOT / "Saved" / "ImportReports" / "StormPass_SourceSurvey.json"
)

EXPLICIT_VISUAL_LEVELS = {
    "StormPass_Background",
    "StormPass_Landscape",
    "StormPass_Light",
}
EXCLUDED_LEVEL_PREFIXES = (
    "StormPass_Cinema_",
    "StormPass_BGM",
    "StormPass_Sound",
    "StormPass_Spawn_",
    "StormPass_ChrCollision",
    "StormPass_POS",
)
EXCLUDED_EXACT_LEVELS = {
    "StormPass_All",
    "StormPass_SubLV100_Design",
}
LIGHT_TOKENS = (
    "directionallight",
    "pointlight",
    "rectlight",
    "skylight",
    "spotlight",
)
FOG_TOKENS = ("fog", "mist")
USD_REF_RE = re.compile(r"@([^@]+)@")


def load_helper():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_analysis_helpers", HEINMACH_ANALYZER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared FModel analysis helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load_helper()


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_for_world(path: Path, objects: list[dict]) -> str:
    for obj in objects:
        if isinstance(obj, dict) and obj.get("Type") == "World":
            package = obj.get("Package")
            if isinstance(package, str) and package:
                return package
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    return "BBQ/Content/_Kazan_/Level/StormPass/" + relative.as_posix()


def source_object_text(obj: dict) -> str:
    return " ".join(
        str(obj.get(key, "")) for key in ("Type", "Name", "Class", "Template")
    ).lower()


def is_light_actor(obj: dict) -> bool:
    actor_type = str(obj.get("Type", "")).lower()
    return any(token in actor_type for token in LIGHT_TOKENS)


def is_fog_actor(obj: dict) -> bool:
    text = source_object_text(obj)
    return any(token in text for token in FOG_TOKENS)


def level_basename(asset_path: str) -> str:
    value = str(asset_path).rsplit("/", 1)[-1]
    return value.split(".", 1)[0]


def streaming_inventory(all_objects: list[dict]) -> list[dict]:
    rows = []
    for index, obj in enumerate(all_objects):
        if not isinstance(obj, dict) or not str(obj.get("Type", "")).startswith(
            "LevelStreaming"
        ):
            continue
        properties = obj.get("Properties") or {}
        world = (properties.get("WorldAsset") or {}).get("AssetPathName")
        if not world:
            continue
        rows.append(
            {
                "source_object_index": index,
                "type": obj.get("Type"),
                "name": obj.get("Name"),
                "world_asset": world,
                "level_name": level_basename(world),
                "initially_loaded": properties.get("bInitiallyLoaded"),
                "should_be_loaded": properties.get("bShouldBeLoaded"),
                "initially_visible": properties.get("bInitiallyVisible"),
                "should_be_visible": properties.get("bShouldBeVisible"),
                "streaming_volume_count": len(
                    properties.get("EditorStreamingVolumes") or []
                ),
            }
        )
    return rows


def is_visual_level(level_name: str, streamed_names: set[str]) -> bool:
    if level_name not in streamed_names:
        return False
    if level_name in EXCLUDED_EXACT_LEVELS:
        return False
    if level_name.startswith(EXCLUDED_LEVEL_PREFIXES):
        return False
    return (
        level_name in EXPLICIT_VISUAL_LEVELS
        or level_name.startswith("StormPass_SubLV")
        or level_name.startswith("StormPass_Boss_Phase_")
    )


def scan_world(path: Path, include_visual_records: bool) -> dict:
    objects = load_json(path)
    if not isinstance(objects, list):
        raise ValueError(f"Expected an object array: {path}")
    package = package_for_world(path, objects)
    level_name = path.stem
    type_counts = Counter()
    actor_type_counts = Counter()
    refs_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    templates = Counter()
    actors = []
    static_mesh_placements = []
    light_records = []
    deferred_fog_records = []

    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            continue
        obj_type = str(obj.get("Type", "Unknown"))
        type_counts[obj_type] += 1
        for key_path, ref in helper.walk_object_refs(obj):
            ref_package = helper.package_from_object_path(ref.get("ObjectPath"))
            if not ref_package or ref_package == package:
                continue
            kind = helper.object_ref_kind(key_path, str(ref.get("ObjectName", "")))
            refs_by_kind[kind][ref_package] += 1
        if not helper.is_actor(obj):
            continue
        actor_type_counts[obj_type] += 1
        template = helper.template_package(obj)
        if template:
            templates[template] += 1
        if not include_visual_records:
            continue
        record = helper.actor_record(
            level_name, package, index, obj, objects, include_properties=False
        )
        record["deferred_fog"] = is_fog_actor(obj)
        record["source_light"] = is_light_actor(obj)
        actors.append(record)
        if is_fog_actor(obj):
            deferred_fog_records.append(
                helper.actor_record(
                    level_name, package, index, obj, objects, include_properties=True
                )
            )
            continue
        if is_light_actor(obj):
            light_records.append(
                helper.actor_record(
                    level_name, package, index, obj, objects, include_properties=True
                )
            )
        placement = helper.static_mesh_placement(
            level_name, package, index, obj, objects
        )
        if placement:
            static_mesh_placements.append(placement)

    return {
        "level_name": level_name,
        "source_json": str(path),
        "package": package,
        "object_count": len(objects),
        "actor_count": sum(actor_type_counts.values()),
        "type_counts": type_counts,
        "actor_type_counts": actor_type_counts,
        "refs_by_kind": refs_by_kind,
        "templates": templates,
        "actors": actors,
        "static_mesh_placements": static_mesh_placements,
        "lights": light_records,
        "deferred_fog": deferred_fog_records,
    }


def exported_candidates(package: str) -> list[str]:
    return helper.find_exported_candidates(FMODEL_ROOT, package)


def scan_stormpass_usd() -> dict:
    files = sorted(WORLD_ROOT.rglob("*.usda")) if WORLD_ROOT.is_dir() else []
    references = []
    for source in files:
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in USD_REF_RE.finditer(text):
            raw = match.group(1)
            resolved = (source.parent / Path(raw)).resolve()
            references.append(
                {
                    "source": str(source),
                    "reference": raw,
                    "resolved": str(resolved),
                    "exists": resolved.is_file(),
                }
            )
    return {
        "world_file_count": len(files),
        "reference_count": len(references),
        "unique_reference_count": len({row["resolved"] for row in references}),
        "existing_reference_count": sum(row["exists"] for row in references),
        "missing_references": [row for row in references if not row["exists"]],
    }


def main():
    if not SOURCE_ROOT.is_dir():
        raise FileNotFoundError(f"StormPass property exports are missing: {SOURCE_ROOT}")
    all_path = SOURCE_ROOT / "StormPass_All.json"
    all_objects = load_json(all_path)
    streaming = streaming_inventory(all_objects)
    streamed_names = {row["level_name"] for row in streaming}

    root_jsons = sorted(SOURCE_ROOT.glob("*.json"))
    scans = []
    failures = []
    for path in root_jsons:
        try:
            scans.append(scan_world(path, is_visual_level(path.stem, streamed_names)))
        except Exception as exc:
            failures.append(
                {"source_json": str(path), "error": f"{type(exc).__name__}: {exc}"}
            )

    visual_scans = [
        scan for scan in scans if is_visual_level(scan["level_name"], streamed_names)
    ]
    excluded_scans = [scan for scan in scans if scan not in visual_scans]
    templates = Counter()
    refs_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    actors = []
    static_mesh_placements = []
    lights = []
    deferred_fog = []
    for scan in visual_scans:
        templates.update(scan["templates"])
        actors.extend(scan["actors"])
        static_mesh_placements.extend(scan["static_mesh_placements"])
        lights.extend(scan["lights"])
        deferred_fog.extend(scan["deferred_fog"])
        for kind, counter in scan["refs_by_kind"].items():
            refs_by_kind[kind].update(counter)

    template_rows = []
    for package, placement_count in templates.most_common():
        candidates = exported_candidates(package)
        template_rows.append(
            {
                "package": package,
                "placement_count": placement_count,
                "exported_files": candidates,
                "has_properties_json": any(
                    value.lower().endswith(".json") for value in candidates
                ),
            }
        )

    asset_references = {}
    for kind, counter in sorted(refs_by_kind.items()):
        asset_references[kind] = [
            {
                "package": package,
                "reference_count": count,
                "exported_files": exported_candidates(package),
            }
            for package, count in counter.most_common()
        ]

    usd = scan_stormpass_usd()
    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    level_rows = [
        {
            "level_name": scan["level_name"],
            "source_json": scan["source_json"],
            "package": scan["package"],
            "object_count": scan["object_count"],
            "actor_count": scan["actor_count"],
            "direct_static_mesh_placement_count": len(
                scan["static_mesh_placements"]
            ),
            "light_count": len(scan["lights"]),
            "deferred_fog_count": len(scan["deferred_fog"]),
            "top_actor_types": [
                {"name": name, "count": count}
                for name, count in scan["actor_type_counts"].most_common(20)
            ],
        }
        for scan in visual_scans
    ]
    excluded_rows = [
        {
            "level_name": scan["level_name"],
            "actor_count": scan["actor_count"],
            "reason": "not part of the visual environment reconstruction scope",
        }
        for scan in excluded_scans
    ]

    scope = {
        "schema_version": 1,
        "level": "StormPass",
        "generated_at": generated_at,
        "source_properties_root": str(SOURCE_ROOT),
        "source_world_root": str(WORLD_ROOT),
        "streaming_levels": streaming,
        "visual_levels": [row["level_name"] for row in level_rows],
        "excluded_levels": excluded_rows,
        "fog_policy": "Metadata only; all Fog/Mist actors are deferred until the final pass.",
        "content_boundary": (
            "No character, enemy, spawn, quest, cinema, sound, BGM, navigation, "
            "or gameplay-logic restoration."
        ),
        "level_summaries": level_rows,
        "parse_failures": failures,
        "counts": {
            "root_json_count": len(root_jsons),
            "parsed_root_json_count": len(scans),
            "streaming_level_count": len(streaming),
            "visual_level_count": len(visual_scans),
            "visual_actor_count": len(actors),
            "direct_static_mesh_placement_count": len(static_mesh_placements),
            "source_light_count": len(lights),
            "deferred_fog_actor_count": len(deferred_fog),
            "unique_template_package_count": len(template_rows),
            "missing_template_properties_count": sum(
                not row["has_properties_json"] for row in template_rows
            ),
            "world_usda_count": usd["world_file_count"],
            "world_usd_missing_reference_count": len(usd["missing_references"]),
        },
    }
    manifest = {
        "schema_version": 1,
        "level": "StormPass",
        "generated_at": generated_at,
        "template_packages": template_rows,
        "asset_references": asset_references,
        "usd_graph": usd,
    }
    helper.json_dump(METADATA_ROOT / "StormPass_SourceScope.json", scope)
    helper.json_dump(
        METADATA_ROOT / "StormPass_EnvironmentActors.json",
        {
            "schema_version": 1,
            "level": "StormPass",
            "generated_at": generated_at,
            "actors": actors,
        },
    )
    helper.json_dump(
        METADATA_ROOT / "StormPass_DirectStaticMeshPlacements.json",
        {
            "schema_version": 1,
            "level": "StormPass",
            "generated_at": generated_at,
            "placements": static_mesh_placements,
        },
    )
    helper.json_dump(
        METADATA_ROOT / "StormPass_SourceLights.json",
        {
            "schema_version": 1,
            "level": "StormPass",
            "generated_at": generated_at,
            "lights": lights,
        },
    )
    helper.json_dump(
        METADATA_ROOT / "StormPass_DeferredFog.json",
        {
            "schema_version": 1,
            "level": "StormPass",
            "generated_at": generated_at,
            "restoration_state": "deferred_until_final_pass",
            "actors": deferred_fog,
        },
    )
    helper.json_dump(METADATA_ROOT / "StormPass_AssetManifest.json", manifest)
    helper.json_dump(REPORT_PATH, scope)
    print(
        "KHAZAN_STORMPASS_SOURCE_SURVEY "
        + json.dumps(scope["counts"], ensure_ascii=False, sort_keys=True)
    )
    if failures:
        raise RuntimeError("StormPass source survey contains parse failures")
    return scope


if __name__ == "__main__":
    main()
