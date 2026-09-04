#!/usr/bin/env python3
"""Audit root StaticMesh coverage hidden behind FModel Blueprint templates.

The original compact manifest only accepted a mesh reference serialized directly
on a level actor's root component. Most Khazan prop actors inherit StaticMesh
from an external Blueprint component template instead. This audit resolves that
template chain without changing Unreal assets and writes reusable candidate data.

Fog is deliberately excluded from candidate reconstruction in this pass.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENVIRONMENT_LEVELS = {
    "HeinMach_Chrcollision",
    "HeinMach_Landscape2",
    "HeinMach_Landscape1",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_Blizzard_2",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV07_BG",
    "HeinMach_SubLV05_Escape_1",
}

LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")
FOG_TOKENS = ("fog", "mist", "volumetric")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def package_from_object_path(path: str | None) -> str | None:
    if not isinstance(path, str) or not path:
        return None
    normalized = path.replace("\\", "/")
    if normalized in {"None", "none"} or normalized.startswith("/Script/"):
        return None
    if normalized.startswith("/Game/"):
        normalized = "BBQ/Content/" + normalized[len("/Game/") :]
    elif normalized.startswith("/Engine/"):
        normalized = "Engine/Content/" + normalized[len("/Engine/") :]
    if not normalized.startswith(("BBQ/Content/", "Engine/Content/")):
        return None
    slash = normalized.rfind("/")
    dot = normalized.find(".", slash + 1)
    return normalized[:dot] if dot >= 0 else normalized


def referenced_package(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return package_from_object_path(value.get("ObjectPath") or value.get("AssetPathName"))


def referenced_package_slots(value: Any) -> list[str | None]:
    if not isinstance(value, list):
        return []
    return [referenced_package(item) for item in value]


def object_index(reference: Any) -> int | None:
    if not isinstance(reference, dict):
        return None
    path = reference.get("ObjectPath")
    if not isinstance(path, str):
        return None
    match = LOCAL_INDEX_RE.search(path)
    return int(match.group(1)) if match else None


def is_actor(obj: dict[str, Any]) -> bool:
    outer = obj.get("Outer")
    if not isinstance(outer, dict):
        return False
    outer_name = str(outer.get("ObjectName", ""))
    return outer_name.startswith("Level'") and "PersistentLevel" in outer_name


def vector(value: Any, axes: tuple[str, ...], default: tuple[float, ...]) -> dict[str, float]:
    if isinstance(value, dict):
        result: dict[str, float] = {}
        for axis in axes:
            raw = value.get(axis)
            if not isinstance(raw, (int, float)):
                break
            result[axis.lower()] = float(raw)
        else:
            return result
    return {axis.lower(): float(raw) for axis, raw in zip(axes, default)}


class PackageResolver:
    def __init__(self, fmodel_root: Path):
        self.fmodel_root = fmodel_root
        self.cache: dict[str, list[dict[str, Any]] | None] = {}
        self.paths: dict[str, str | None] = {}

    def json_candidates(self, package: str) -> list[Path]:
        relative = Path(*package.split("/"))
        return [
            self.fmodel_root / "Exports" / relative.with_suffix(".json"),
            self.fmodel_root / relative.with_suffix(".json"),
        ]

    def source_candidates(self, package: str, suffix: str) -> list[Path]:
        relative = Path(*package.split("/"))
        return [
            self.fmodel_root / relative.with_suffix(suffix),
            self.fmodel_root / "Exports" / relative.with_suffix(suffix),
        ]

    def load_package(self, package: str) -> list[dict[str, Any]] | None:
        if package in self.cache:
            return self.cache[package]
        for candidate in self.json_candidates(package):
            if candidate.is_file():
                payload = load_json(candidate)
                objects = payload if isinstance(payload, list) else None
                self.cache[package] = objects
                self.paths[package] = str(candidate)
                return objects
        self.cache[package] = None
        self.paths[package] = None
        return None

    def resolve_ref(
        self,
        reference: Any,
        current_package: str,
        current_objects: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]] | None, int | None]:
        if not isinstance(reference, dict):
            return None, None, None, None
        path = reference.get("ObjectPath")
        package = package_from_object_path(path)
        index = object_index(reference)
        if package is None or index is None:
            return None, package, None, index
        objects = current_objects if package == current_package else self.load_package(package)
        if objects is None or not (0 <= index < len(objects)):
            return None, package, objects, index
        obj = objects[index]
        return (obj if isinstance(obj, dict) else None), package, objects, index

    def inherited_property(
        self,
        obj: dict[str, Any],
        package: str,
        objects: list[dict[str, Any]],
        name: str,
    ) -> tuple[Any, str | None, int | None, int]:
        current = obj
        current_package = package
        current_objects = objects
        seen: set[tuple[str, int]] = set()
        depth = 0
        while isinstance(current, dict) and depth < 32:
            properties = current.get("Properties")
            if isinstance(properties, dict) and name in properties:
                return properties[name], current_package, None, depth
            template = current.get("Template")
            target, target_package, target_objects, target_index = self.resolve_ref(
                template, current_package, current_objects
            )
            if target is None or target_package is None or target_objects is None or target_index is None:
                return None, target_package, target_index, depth
            key = (target_package, target_index)
            if key in seen:
                return None, target_package, target_index, depth
            seen.add(key)
            current = target
            current_package = target_package
            current_objects = target_objects
            depth += 1
        return None, current_package, None, depth


def actor_transform(
    actor: dict[str, Any],
    root_component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
    resolver: PackageResolver,
) -> dict[str, Any]:
    actor_properties = actor.get("Properties") if isinstance(actor.get("Properties"), dict) else {}

    def inherited(name: str) -> Any:
        value, _source_package, _source_index, _depth = resolver.inherited_property(
            root_component, package, objects, name
        )
        return value

    location_value = inherited("RelativeLocation") or actor_properties.get("ActorLocation")
    rotation_value = inherited("RelativeRotation") or actor_properties.get("ActorRotation")
    scale_value = inherited("RelativeScale3D")
    return {
        "location_cm": vector(location_value, ("X", "Y", "Z"), (0.0, 0.0, 0.0)),
        "rotation_degrees": vector(rotation_value, ("Pitch", "Yaw", "Roll"), (0.0, 0.0, 0.0)),
        "scale": vector(scale_value, ("X", "Y", "Z"), (1.0, 1.0, 1.0)),
    }


def is_fog_candidate(actor: dict[str, Any], mesh_package: str) -> bool:
    haystack = " ".join(
        [str(actor.get("Type", "")), str(actor.get("Name", "")), mesh_package]
    ).lower()
    return any(token in haystack for token in FOG_TOKENS)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    fmodel_root = args.fmodel_root.resolve()
    properties_dir = args.properties_dir.resolve()
    package_root = str(
        getattr(args, "package_root", "BBQ/Content/_Kazan_/Level/HeinMach")
    ).rstrip("/")
    resolver = PackageResolver(fmodel_root)
    existing = load_json(args.existing_manifest.resolve())
    existing_rows = [
        row
        for row in existing.get("placements", [])
        if row.get("source_level") in ENVIRONMENT_LEVELS
        and row.get("visible") is not False
        and row.get("static_mesh_package")
    ]
    existing_keys = {
        (str(row.get("source_level")), int(row.get("source_object_index", -1)))
        for row in existing_rows
    }

    root_candidates: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    counts_by_level: dict[str, Counter[str]] = defaultdict(Counter)
    inherited_templates: Counter[str] = Counter()
    mesh_usage: Counter[str] = Counter()
    actor_total = 0
    root_component_total = 0
    hidden_total = 0
    fog_excluded_total = 0

    for level_name in sorted(ENVIRONMENT_LEVELS):
        level_path = properties_dir / f"{level_name}.json"
        if not level_path.is_file():
            unresolved.append({"source_level": level_name, "reason": "missing_level_json"})
            continue
        objects = load_json(level_path)
        if not isinstance(objects, list):
            unresolved.append({"source_level": level_name, "reason": "invalid_level_json"})
            continue
        package = f"{package_root}/{level_name}"
        for actor_index, actor in enumerate(objects):
            if not isinstance(actor, dict) or not is_actor(actor):
                continue
            actor_total += 1
            counts_by_level[level_name]["actors"] += 1
            actor_properties = actor.get("Properties") if isinstance(actor.get("Properties"), dict) else {}
            root_ref = actor_properties.get("RootComponent")
            root_component, root_package, root_objects, root_index = resolver.resolve_ref(
                root_ref, package, objects
            )
            if root_component is None or root_package != package or root_objects is None:
                counts_by_level[level_name]["no_root_component"] += 1
                continue
            root_component_total += 1

            mesh_value, mesh_source_package, mesh_source_index, inheritance_depth = resolver.inherited_property(
                root_component, package, objects, "StaticMesh"
            )
            mesh_package = referenced_package(mesh_value)
            if not mesh_package:
                counts_by_level[level_name]["root_without_mesh"] += 1
                component_template = root_component.get("Template")
                unresolved.append(
                    {
                        "source_level": level_name,
                        "source_object_index": actor_index,
                        "actor_type": actor.get("Type"),
                        "actor_name": actor.get("Name"),
                        "root_component_type": root_component.get("Type"),
                        "root_component_template": component_template,
                        "template_package": package_from_object_path(
                            component_template.get("ObjectPath")
                            if isinstance(component_template, dict)
                            else None
                        ),
                        "reason": "root_static_mesh_unresolved",
                    }
                )
                continue

            component_properties = (
                root_component.get("Properties")
                if isinstance(root_component.get("Properties"), dict)
                else {}
            )
            direct = referenced_package(component_properties.get("StaticMesh")) is not None
            visibility_value, _visibility_package, _visibility_index, _visibility_depth = resolver.inherited_property(
                root_component, package, objects, "bVisible"
            )
            hidden_in_game, _hidden_package, _hidden_index, _hidden_depth = resolver.inherited_property(
                root_component, package, objects, "bHiddenInGame"
            )
            visible = (
                not bool(actor_properties.get("bHidden", False))
                and visibility_value is not False
                and not bool(hidden_in_game)
            )
            if not visible:
                hidden_total += 1
                counts_by_level[level_name]["hidden_root_mesh"] += 1
                continue

            if is_fog_candidate(actor, mesh_package):
                fog_excluded_total += 1
                counts_by_level[level_name]["fog_excluded"] += 1
                continue

            override_value, _override_package, _override_index, _override_depth = resolver.inherited_property(
                root_component, package, objects, "OverrideMaterials"
            )
            if override_value is None:
                override_value, _saved_package, _saved_index, _saved_depth = resolver.inherited_property(
                    root_component, package, objects, "SavedOverrideMaterials"
                )
            cast_shadow, _cast_package, _cast_index, _cast_depth = resolver.inherited_property(
                root_component, package, objects, "CastShadow"
            )
            draw_distance, _draw_package, _draw_index, _draw_depth = resolver.inherited_property(
                root_component, package, objects, "CachedLDMaxDrawDistance"
            )
            component_template = root_component.get("Template")
            template_package = package_from_object_path(
                component_template.get("ObjectPath")
                if isinstance(component_template, dict)
                else None
            )
            mode = "direct_level_component" if direct else "inherited_component_template"
            key = (level_name, actor_index)
            record = {
                "source_level": level_name,
                "source_package": package,
                "source_object_index": actor_index,
                "actor_type": actor.get("Type"),
                "actor_name": actor.get("Name"),
                "static_mesh_package": mesh_package,
                "override_material_packages": referenced_package_slots(override_value),
                "transform": actor_transform(
                    actor, root_component, package, objects, resolver
                ),
                "cast_shadow": True if cast_shadow is None else bool(cast_shadow),
                "visible": True,
                "cached_max_draw_distance": draw_distance,
                "tags": actor_properties.get("Tags", []),
                "resolution": {
                    "mode": mode,
                    "inheritance_depth": inheritance_depth,
                    "component_template_package": template_package,
                    "mesh_property_source_package": mesh_source_package,
                    "mesh_property_source_index": mesh_source_index,
                    "already_in_compact_manifest": key in existing_keys,
                },
            }
            root_candidates.append(record)
            counts_by_level[level_name]["resolved_root_mesh"] += 1
            counts_by_level[level_name][mode] += 1
            mesh_usage[mesh_package] += 1
            if not direct:
                inherited_templates[template_package or "<unknown>"] += 1

    candidate_keys = {
        (str(row["source_level"]), int(row["source_object_index"]))
        for row in root_candidates
    }
    missing_existing_keys = sorted(existing_keys - candidate_keys)
    inherited_candidates = [
        row
        for row in root_candidates
        if row["resolution"]["mode"] == "inherited_component_template"
    ]
    unique_meshes = sorted(mesh_usage)
    missing_usd = []
    for package in unique_meshes:
        candidates = resolver.source_candidates(package, ".usda")
        if not any(path.is_file() for path in candidates):
            missing_usd.append(
                {
                    "package": package,
                    "placement_count": mesh_usage[package],
                    "expected_paths": [str(path) for path in candidates],
                }
            )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "audited",
        "scope": {
            "environment_levels": sorted(ENVIRONMENT_LEVELS),
            "fog_excluded": True,
            "cinematic_layers_excluded": True,
        },
        "source": {
            "fmodel_root": str(fmodel_root),
            "properties_directory": str(properties_dir),
            "existing_manifest": str(args.existing_manifest.resolve()),
        },
        "summary": {
            "environment_actor_count": actor_total,
            "root_component_actor_count": root_component_total,
            "existing_compact_visible_root_placement_count": len(existing_rows),
            "resolved_visible_root_placement_count": len(root_candidates),
            "new_inherited_root_placement_count": len(inherited_candidates),
            "resolved_unique_static_mesh_count": len(unique_meshes),
            "missing_usd_static_mesh_count": len(missing_usd),
            "hidden_root_mesh_count": hidden_total,
            "fog_excluded_root_mesh_count": fog_excluded_total,
            "existing_manifest_keys_not_reproduced_count": len(missing_existing_keys),
            "unresolved_root_actor_count": len(unresolved),
        },
        "counts_by_level": [
            {"source_level": level, **dict(counts_by_level[level])}
            for level in sorted(counts_by_level)
        ],
        "top_inherited_component_templates": [
            {"package": package, "placement_count": count}
            for package, count in inherited_templates.most_common()
        ],
        "mesh_usage": [
            {"package": package, "placement_count": mesh_usage[package]}
            for package in unique_meshes
        ],
        "missing_usd_static_meshes": missing_usd,
        "existing_manifest_keys_not_reproduced": [
            {"source_level": level, "source_object_index": index}
            for level, index in missing_existing_keys
        ],
        "unresolved_root_actors": unresolved,
        "resolved_root_placements": root_candidates,
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    default_fmodel_root = Path.home() / "Desktop" / "카잔"
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmodel-root", type=Path, default=default_fmodel_root)
    parser.add_argument(
        "--properties-dir",
        type=Path,
        default=default_fmodel_root
        / "Exports"
        / "BBQ"
        / "Content"
        / "_Kazan_"
        / "Level"
        / "HeinMach",
    )
    parser.add_argument(
        "--existing-manifest",
        type=Path,
        default=project_root
        / "Content"
        / "_Art"
        / "Kazan"
        / "Environment"
        / "HeinMach"
        / "Metadata"
        / "HeinMach_RenderableStaticMeshPlacements.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root
        / "Saved"
        / "ImportReports"
        / "HeinMach_RootTemplateCoverage_Audit.json",
    )
    args = parser.parse_args()
    report = audit(args)
    write_json(args.output.resolve(), report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"report={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
