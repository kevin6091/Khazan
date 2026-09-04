#!/usr/bin/env python3
"""Audit non-root HeinMach StaticMeshComponents inherited from templates.

The earlier render-gap scan only accepted StaticMesh serialized directly on a
level component.  This read-only audit resolves the same Blueprint template
chain used by the root-template audit, while excluding foliage HISM and Fog.
"""

from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
PROPERTIES_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "HeinMach"
)
LEVEL_PACKAGE_ROOT = "BBQ/Content/_Kazan_/Level/HeinMach"
ROOT_AUDIT_SCRIPT = SCRIPT_DIR / "audit_heinmach_root_template_coverage.py"
OLD_GAP_REPORT = (
    PROJECT_ROOT / "Saved" / "ImportReports" / "HeinMach_Render_Gap_Analysis.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "HeinMach_ChildTemplateCoverage_Audit.json"
)


def load_root_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_root_template_helpers", ROOT_AUDIT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load root-template audit helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


root = load_root_module()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=False)
        output.write("\n")


def actor_object_path(package: str, actor_index: int) -> str:
    return f"{package}.{actor_index}"


def inherited_value(
    resolver,
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
    name: str,
):
    return resolver.inherited_property(component, package, objects, name)


def inherited_vector(
    resolver,
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
    name: str,
    axes: tuple[str, ...],
    defaults: tuple[float, ...],
) -> dict[str, float]:
    value, _, _, _ = inherited_value(
        resolver, component, package, objects, name
    )
    return root.vector(value, axes, defaults)


def local_transform(
    resolver,
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "location_cm": inherited_vector(
            resolver,
            component,
            package,
            objects,
            "RelativeLocation",
            ("X", "Y", "Z"),
            (0.0, 0.0, 0.0),
        ),
        "rotation_degrees": inherited_vector(
            resolver,
            component,
            package,
            objects,
            "RelativeRotation",
            ("Pitch", "Yaw", "Roll"),
            (0.0, 0.0, 0.0),
        ),
        "scale": inherited_vector(
            resolver,
            component,
            package,
            objects,
            "RelativeScale3D",
            ("X", "Y", "Z"),
            (1.0, 1.0, 1.0),
        ),
    }


def template_lineage_keys(
    resolver,
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
    object_index: int,
) -> set[tuple[str, int]]:
    """Return the local component and every external template it inherits."""
    result = {(package, object_index)}
    current = component
    current_package = package
    current_objects = objects
    while isinstance(current, dict) and len(result) < 32:
        target, target_package, target_objects, target_index = resolver.resolve_ref(
            current.get("Template"), current_package, current_objects
        )
        if (
            target is None
            or target_package is None
            or target_objects is None
            or target_index is None
        ):
            break
        key = (target_package, target_index)
        if key in result:
            break
        result.add(key)
        current = target
        current_package = target_package
        current_objects = target_objects
    return result


def non_default_attachment_policy(
    resolver,
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
) -> dict[str, Any]:
    flags = {}
    for name in ("bAbsoluteLocation", "bAbsoluteRotation", "bAbsoluteScale"):
        value, _, _, _ = inherited_value(
            resolver, component, package, objects, name
        )
        flags[name] = bool(value)
    socket, _, _, _ = inherited_value(
        resolver, component, package, objects, "AttachSocketName"
    )
    socket_name = str(socket or "")
    if socket_name.lower() in {"", "none"}:
        socket_name = ""
    return {"absolute_flags": flags, "attach_socket_name": socket_name}


def attachment_parent_chain(
    resolver,
    component: dict[str, Any],
    component_index: int,
    root_component: dict[str, Any],
    root_index: int,
    package: str,
    objects: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    """Resolve transforms between a child component and the actor root."""
    root_keys = template_lineage_keys(
        resolver, root_component, package, objects, root_index
    )
    chain = []
    current = component
    current_package = package
    current_objects = objects
    seen = {(package, component_index)}
    while len(chain) < 32:
        attach_value, attach_source_package, _, _ = inherited_value(
            resolver, current, current_package, current_objects, "AttachParent"
        )
        if not isinstance(attach_value, dict):
            return chain, "attach_parent_unresolved"
        source_package = attach_source_package or current_package
        source_objects = (
            current_objects
            if source_package == current_package
            else resolver.load_package(source_package)
        )
        if source_objects is None:
            return chain, "attach_parent_source_package_missing"
        parent, parent_package, parent_objects, parent_index = resolver.resolve_ref(
            attach_value, source_package, source_objects
        )
        if (
            parent is None
            or parent_package is None
            or parent_objects is None
            or parent_index is None
        ):
            return chain, "attach_parent_reference_unresolved"
        key = (parent_package, parent_index)
        if key in root_keys:
            return chain, None
        if key in seen:
            return chain, "attach_parent_cycle"
        seen.add(key)
        chain.append(
            {
                "package": parent_package,
                "object_index": parent_index,
                "component_type": parent.get("Type"),
                "component_name": parent.get("Name"),
                "local_transform": local_transform(
                    resolver, parent, parent_package, parent_objects
                ),
                "attachment_policy": non_default_attachment_policy(
                    resolver, parent, parent_package, parent_objects
                ),
            }
        )
        current = parent
        current_package = parent_package
        current_objects = parent_objects
    return chain, "attach_parent_depth_exceeded"


def is_identity_transform(transform: dict[str, Any]) -> bool:
    location = transform["location_cm"]
    rotation = transform["rotation_degrees"]
    scale = transform["scale"]
    return (
        all(abs(float(location[axis])) <= 1.0e-6 for axis in ("x", "y", "z"))
        and all(
            abs(float(rotation[axis])) <= 1.0e-6
            for axis in ("pitch", "yaw", "roll")
        )
        and all(
            abs(float(scale[axis]) - 1.0) <= 1.0e-6
            for axis in ("x", "y", "z")
        )
    )


def visible(
    resolver,
    actor: dict[str, Any],
    component: dict[str, Any],
    package: str,
    objects: list[dict[str, Any]],
) -> bool:
    actor_properties = (
        actor.get("Properties")
        if isinstance(actor.get("Properties"), dict)
        else {}
    )
    component_visible, _, _, _ = inherited_value(
        resolver, component, package, objects, "bVisible"
    )
    hidden_in_game, _, _, _ = inherited_value(
        resolver, component, package, objects, "bHiddenInGame"
    )
    return (
        not bool(actor_properties.get("bHidden", False))
        and component_visible is not False
        and not bool(hidden_in_game)
    )


def fog_candidate(actor: dict[str, Any], component: dict[str, Any], mesh: str) -> bool:
    searchable = " ".join(
        str(value)
        for value in (
            actor.get("Type"),
            actor.get("Name"),
            component.get("Type"),
            component.get("Name"),
            mesh,
        )
    ).lower()
    return any(token in searchable for token in ("fog", "mist", "volumetric"))


def foliage_candidate(actor: dict[str, Any], component: dict[str, Any]) -> bool:
    searchable = " ".join(
        str(value)
        for value in (
            actor.get("Type"),
            component.get("Type"),
            component.get("Name"),
        )
    ).lower()
    return "foliage" in searchable or "hierarchicalinstancedstaticmesh" in searchable


def old_direct_keys() -> set[tuple[str, int, int]]:
    if not OLD_GAP_REPORT.is_file():
        return set()
    payload = load_json(OLD_GAP_REPORT)
    return {
        (
            str(item.get("source_level")),
            int(item.get("actor_object_index", -1)),
            int(item.get("component_object_index", -1)),
        )
        for item in payload.get("non_root_static_mesh_components", [])
    }


def audit() -> dict[str, Any]:
    resolver = root.PackageResolver(FMODEL_ROOT)
    direct_keys = old_direct_keys()
    candidates = []
    unresolved = []
    counts_by_level: dict[str, Counter[str]] = defaultdict(Counter)
    mesh_usage: Counter[str] = Counter()
    template_usage: Counter[str] = Counter()
    component_object_count = 0
    fog_excluded = 0
    foliage_excluded = 0
    hidden_excluded = 0
    nested_attachment_count = 0
    absolute_attachment_policy_count = 0
    socket_attachment_count = 0
    max_attachment_depth = 0

    for level_name in sorted(root.ENVIRONMENT_LEVELS):
        level_path = PROPERTIES_ROOT / f"{level_name}.json"
        if not level_path.is_file():
            unresolved.append(
                {"source_level": level_name, "reason": "missing_level_json"}
            )
            continue
        objects = load_json(level_path)
        if not isinstance(objects, list):
            unresolved.append(
                {"source_level": level_name, "reason": "invalid_level_json"}
            )
            continue
        package = f"{LEVEL_PACKAGE_ROOT}/{level_name}"
        components_by_outer: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for object_index, obj in enumerate(objects):
            if not isinstance(obj, dict):
                continue
            outer = obj.get("Outer")
            if isinstance(outer, dict) and isinstance(outer.get("ObjectPath"), str):
                components_by_outer[outer["ObjectPath"]].append((object_index, obj))

        for actor_index, actor in enumerate(objects):
            if not isinstance(actor, dict) or not root.is_actor(actor):
                continue
            actor_properties = (
                actor.get("Properties")
                if isinstance(actor.get("Properties"), dict)
                else {}
            )
            root_index = root.object_index(actor_properties.get("RootComponent"))
            root_component = (
                objects[root_index]
                if root_index is not None
                and 0 <= root_index < len(objects)
                and isinstance(objects[root_index], dict)
                else None
            )
            if root_component is None:
                continue
            actor_world_transform = root.actor_transform(
                actor, root_component, package, objects, resolver
            )
            owner_path = actor_object_path(package, actor_index)

            for component_index, component in components_by_outer.get(owner_path, []):
                if component_index == root_index:
                    continue
                component_object_count += 1
                counts_by_level[level_name]["local_non_root_components"] += 1

                mesh_value, mesh_source_package, mesh_source_index, inheritance_depth = inherited_value(
                    resolver, component, package, objects, "StaticMesh"
                )
                mesh_package = root.referenced_package(mesh_value)
                if not mesh_package:
                    counts_by_level[level_name]["non_mesh_components"] += 1
                    continue
                if foliage_candidate(actor, component):
                    foliage_excluded += 1
                    counts_by_level[level_name]["foliage_excluded"] += 1
                    continue
                if fog_candidate(actor, component, mesh_package):
                    fog_excluded += 1
                    counts_by_level[level_name]["fog_excluded"] += 1
                    continue
                if not visible(resolver, actor, component, package, objects):
                    hidden_excluded += 1
                    counts_by_level[level_name]["hidden_mesh_components"] += 1
                    continue

                component_properties = (
                    component.get("Properties")
                    if isinstance(component.get("Properties"), dict)
                    else {}
                )
                direct = (
                    root.referenced_package(component_properties.get("StaticMesh"))
                    is not None
                )
                override_value, _, _, _ = inherited_value(
                    resolver, component, package, objects, "OverrideMaterials"
                )
                if override_value is None:
                    override_value, _, _, _ = inherited_value(
                        resolver,
                        component,
                        package,
                        objects,
                        "SavedOverrideMaterials",
                    )
                attach_value, attach_source_package, _, _ = inherited_value(
                    resolver, component, package, objects, "AttachParent"
                )
                cast_shadow, _, _, _ = inherited_value(
                    resolver, component, package, objects, "CastShadow"
                )
                draw_distance, _, _, _ = inherited_value(
                    resolver,
                    component,
                    package,
                    objects,
                    "CachedLDMaxDrawDistance",
                )
                template = component.get("Template")
                template_package = root.package_from_object_path(
                    template.get("ObjectPath") if isinstance(template, dict) else None
                )
                key = (level_name, actor_index, component_index)
                transform = local_transform(
                    resolver, component, package, objects
                )
                attachment_chain, attachment_error = attachment_parent_chain(
                    resolver,
                    component,
                    component_index,
                    root_component,
                    root_index,
                    package,
                    objects,
                )
                if attachment_error:
                    unresolved.append(
                        {
                            "source_level": level_name,
                            "actor_object_index": actor_index,
                            "component_object_index": component_index,
                            "actor_name": actor.get("Name"),
                            "component_name": component.get("Name"),
                            "reason": attachment_error,
                        }
                    )
                    counts_by_level[level_name]["unresolved_attachment_chain"] += 1
                    continue
                attachment_policy = non_default_attachment_policy(
                    resolver, component, package, objects
                )
                policies = [attachment_policy] + [
                    item["attachment_policy"] for item in attachment_chain
                ]
                absolute_policy = any(
                    any(policy["absolute_flags"].values()) for policy in policies
                )
                socket_policy = any(
                    bool(policy["attach_socket_name"]) for policy in policies
                )
                if attachment_chain:
                    nested_attachment_count += 1
                if absolute_policy:
                    absolute_attachment_policy_count += 1
                if socket_policy:
                    socket_attachment_count += 1
                max_attachment_depth = max(
                    max_attachment_depth, 1 + len(attachment_chain)
                )
                record = {
                    "source_level": level_name,
                    "source_package": package,
                    "actor_object_index": actor_index,
                    "actor_type": actor.get("Type"),
                    "actor_name": actor.get("Name"),
                    "actor_world_transform": actor_world_transform,
                    "root_component_object_index": root_index,
                    "component_object_index": component_index,
                    "component_type": component.get("Type"),
                    "component_name": component.get("Name"),
                    "attach_parent_object_index": root.object_index(attach_value),
                    "attach_parent_package": root.package_from_object_path(
                        attach_value.get("ObjectPath")
                        if isinstance(attach_value, dict)
                        else None
                    )
                    or attach_source_package,
                    "local_transform": transform,
                    "attachment_parent_chain": attachment_chain,
                    "attachment_policy": attachment_policy,
                    "has_absolute_attachment_policy": absolute_policy,
                    "has_socket_attachment": socket_policy,
                    "static_mesh_package": mesh_package,
                    "override_material_packages": root.referenced_package_slots(
                        override_value
                    ),
                    "cast_shadow": True if cast_shadow is None else bool(cast_shadow),
                    "cached_max_draw_distance": draw_distance,
                    "visible": True,
                    "resolution": {
                        "mode": (
                            "direct_level_component"
                            if direct
                            else "inherited_component_template"
                        ),
                        "inheritance_depth": inheritance_depth,
                        "component_template_package": template_package,
                        "mesh_property_source_package": mesh_source_package,
                        "mesh_property_source_index": mesh_source_index,
                        "already_in_old_direct_gap_report": key in direct_keys,
                        "identity_local_transform": is_identity_transform(transform),
                    },
                }
                candidates.append(record)
                mesh_usage[mesh_package] += 1
                counts_by_level[level_name]["resolved_visible_child_mesh"] += 1
                counts_by_level[level_name][record["resolution"]["mode"]] += 1
                if not direct:
                    template_usage[template_package or "<unknown>"] += 1

    missing_usd = []
    for package in sorted(mesh_usage):
        candidates_for_package = resolver.source_candidates(package, ".usda")
        if not any(path.is_file() for path in candidates_for_package):
            missing_usd.append(
                {
                    "package": package,
                    "placement_count": mesh_usage[package],
                    "expected_paths": [str(path) for path in candidates_for_package],
                }
            )

    inherited_candidates = [
        item
        for item in candidates
        if item["resolution"]["mode"] == "inherited_component_template"
    ]
    new_candidates = [
        item
        for item in candidates
        if not item["resolution"]["already_in_old_direct_gap_report"]
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "audited",
        "scope": {
            "environment_levels": sorted(root.ENVIRONMENT_LEVELS),
            "foliage_hism_excluded": True,
            "fog_excluded": True,
            "cinematic_layers_excluded": True,
        },
        "source": {
            "fmodel_root": str(FMODEL_ROOT),
            "properties_directory": str(PROPERTIES_ROOT),
            "prior_direct_gap_report": str(OLD_GAP_REPORT),
        },
        "summary": {
            "local_non_root_component_object_count": component_object_count,
            "resolved_visible_non_foliage_non_fog_child_mesh_count": len(candidates),
            "direct_level_child_mesh_count": sum(
                item["resolution"]["mode"] == "direct_level_component"
                for item in candidates
            ),
            "inherited_template_child_mesh_count": len(inherited_candidates),
            "new_child_mesh_count_not_in_old_direct_report": len(new_candidates),
            "identity_local_transform_count": sum(
                item["resolution"]["identity_local_transform"]
                for item in candidates
            ),
            "non_identity_local_transform_count": sum(
                not item["resolution"]["identity_local_transform"]
                for item in candidates
            ),
            "unique_child_static_mesh_count": len(mesh_usage),
            "missing_usd_static_mesh_count": len(missing_usd),
            "foliage_component_excluded_count": foliage_excluded,
            "fog_component_excluded_count": fog_excluded,
            "hidden_child_mesh_excluded_count": hidden_excluded,
            "nested_attachment_component_count": nested_attachment_count,
            "max_attachment_depth": max_attachment_depth,
            "absolute_attachment_policy_count": absolute_attachment_policy_count,
            "socket_attachment_count": socket_attachment_count,
            "unresolved_component_count": len(unresolved),
        },
        "counts_by_level": [
            {"source_level": name, **dict(sorted(counts.items()))}
            for name, counts in sorted(counts_by_level.items())
        ],
        "top_inherited_component_templates": [
            {"package": package, "placement_count": count}
            for package, count in template_usage.most_common()
        ],
        "mesh_usage": [
            {"package": package, "placement_count": count}
            for package, count in sorted(mesh_usage.items())
        ],
        "missing_usd_static_meshes": missing_usd,
        "unresolved_components": unresolved,
        "resolved_child_mesh_components": candidates,
    }


def main() -> None:
    payload = audit()
    write_json(REPORT_PATH, payload)
    print(
        json.dumps(
            {
                "summary": payload["summary"],
                "report": str(REPORT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
