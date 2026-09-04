#!/usr/bin/env python3
"""Find renderable HeinMach components omitted by root-only placement extraction.

This read-only diagnostic scans the original FModel UObject JSON exports.  It
separates direct non-root StaticMeshComponent geometry from template-provided
fog sheets so reconstruction work can be scoped without guessing from the UE
viewport.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from analyze_heinmach import (
    actor_object_path,
    actor_transform,
    is_actor,
    local_index,
    package_from_object_path,
    referenced_package,
)
from audit_fmodel_mesh_orientation import audit_mesh


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
SOURCE_ROOT = FMODEL_ROOT / "Exports" / "BBQ" / "Content" / "_Kazan_" / "Level" / "HeinMach"
REPORT_PATH = PROJECT_ROOT / "Saved" / "ImportReports" / "HeinMach_Render_Gap_Analysis.json"
FOG_MESH_PACKAGE = "BBQ/Content/_Kazan_/Art/VFX/VFX_Mesh/FS_FogSheet_Plane"

ENVIRONMENT_LEVELS = {
    "HeinMach_Chrcollision",
    "HeinMach_Landscape1",
    "HeinMach_Landscape2",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_Blizzard_2",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV05_Escape_1",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV07_BG",
}


def load_objects(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as source:
        payload = json.load(source)
    if not isinstance(payload, list):
        raise ValueError(f"Expected UObject array: {path}")
    return payload


def component_local_transform(component: dict[str, Any]) -> dict[str, Any]:
    props = component.get("Properties")
    props = props if isinstance(props, dict) else {}

    def vector(name: str, axes: tuple[str, ...], defaults: tuple[float, ...]) -> dict[str, float]:
        value = props.get(name)
        value = value if isinstance(value, dict) else {}
        return {
            axis.lower(): float(value.get(axis, default))
            for axis, default in zip(axes, defaults)
        }

    return {
        "location_cm": vector("RelativeLocation", ("X", "Y", "Z"), (0.0, 0.0, 0.0)),
        "rotation_degrees": vector(
            "RelativeRotation", ("Pitch", "Yaw", "Roll"), (0.0, 0.0, 0.0)
        ),
        "scale": vector("RelativeScale3D", ("X", "Y", "Z"), (1.0, 1.0, 1.0)),
    }


def visible(actor: dict[str, Any], component: dict[str, Any]) -> bool:
    actor_props = actor.get("Properties")
    actor_props = actor_props if isinstance(actor_props, dict) else {}
    component_props = component.get("Properties")
    component_props = component_props if isinstance(component_props, dict) else {}
    return (
        not bool(actor_props.get("bHidden", False))
        and component_props.get("bVisible", True) is not False
        and not bool(component_props.get("bHiddenInGame", False))
    )


def main() -> None:
    non_root_mesh_components: list[dict[str, Any]] = []
    fog_sheet_actors: list[dict[str, Any]] = []
    level_actor_counts: Counter[str] = Counter()

    for level_name in sorted(ENVIRONMENT_LEVELS):
        path = SOURCE_ROOT / f"{level_name}.json"
        objects = load_objects(path)
        package = f"BBQ/Content/_Kazan_/Level/HeinMach/{level_name}"

        for actor_index, actor in enumerate(objects):
            if not isinstance(actor, dict) or not is_actor(actor):
                continue
            level_actor_counts[level_name] += 1
            actor_type = str(actor.get("Type", ""))
            actor_name = str(actor.get("Name", ""))
            actor_world_transform, root_component = actor_transform(actor, objects, package)

            if actor_type.startswith("WBP_FogSheet"):
                actor_props = actor.get("Properties")
                actor_props = actor_props if isinstance(actor_props, dict) else {}
                root_props = root_component.get("Properties") if isinstance(root_component, dict) else {}
                root_props = root_props if isinstance(root_props, dict) else {}
                dynamic_material = None
                overrides = root_props.get("OverrideMaterials")
                if isinstance(overrides, list) and overrides:
                    material_index = local_index(overrides[0], package)
                    if material_index is not None and 0 <= material_index < len(objects):
                        candidate = objects[material_index]
                        if isinstance(candidate, dict):
                            dynamic_material = candidate
                dynamic_props = (
                    dynamic_material.get("Properties")
                    if isinstance(dynamic_material, dict)
                    else {}
                )
                dynamic_props = dynamic_props if isinstance(dynamic_props, dict) else {}
                scalar_parameters = {}
                for item in dynamic_props.get("ScalarParameterValues", []):
                    if not isinstance(item, dict):
                        continue
                    info = item.get("ParameterInfo")
                    info = info if isinstance(info, dict) else {}
                    name = info.get("Name")
                    if name is not None and isinstance(item.get("ParameterValue"), (int, float)):
                        scalar_parameters[str(name)] = float(item["ParameterValue"])
                vector_parameters = {}
                for item in dynamic_props.get("VectorParameterValues", []):
                    if not isinstance(item, dict):
                        continue
                    info = item.get("ParameterInfo")
                    info = info if isinstance(info, dict) else {}
                    value = item.get("ParameterValue")
                    if info.get("Name") is not None and isinstance(value, dict):
                        vector_parameters[str(info["Name"])] = {
                            channel.lower(): float(value.get(channel, default))
                            for channel, default in (
                                ("R", 1.0),
                                ("G", 1.0),
                                ("B", 1.0),
                                ("A", 1.0),
                            )
                        }
                fog_sheet_actors.append(
                    {
                        "source_level": level_name,
                        "source_package": package,
                        "source_object_index": actor_index,
                        "actor_type": actor_type,
                        "actor_name": actor_name,
                        "transform": actor_world_transform,
                        "two_sided": bool(actor_props.get("Two Side", False)),
                        "actor_parameters": {
                            key: actor_props.get(key)
                            for key in (
                                "Emmisive Strength",
                                "Opacity",
                                "Panning Speed",
                                "Fading Start",
                                "Panning Rotation",
                                "UV Control",
                                "Edge Depth Fade",
                            )
                            if key in actor_props
                        },
                        "translucency_sort_priority": int(
                            root_props.get("TranslucencySortPriority", 0)
                        ),
                        "dynamic_material_parent_package": referenced_package(
                            dynamic_props.get("Parent")
                        ),
                        "dynamic_scalar_parameters": scalar_parameters,
                        "dynamic_vector_parameters": vector_parameters,
                        "cached_texture_packages": [
                            package_name
                            for package_name in (
                                referenced_package(item)
                                for item in dynamic_props.get(
                                    "CachedReferencedTextures", []
                                )
                            )
                            if package_name
                        ],
                    }
                )

            actor_props = actor.get("Properties")
            actor_props = actor_props if isinstance(actor_props, dict) else {}
            root_index = local_index(actor_props.get("RootComponent"), package)
            owner_path = actor_object_path(package, actor_index)

            for component_index, component in enumerate(objects):
                if component_index == root_index or not isinstance(component, dict):
                    continue
                outer = component.get("Outer")
                if not isinstance(outer, dict) or outer.get("ObjectPath") != owner_path:
                    continue
                component_props = component.get("Properties")
                component_props = component_props if isinstance(component_props, dict) else {}
                mesh_package = referenced_package(component_props.get("StaticMesh"))
                if not mesh_package:
                    continue
                non_root_mesh_components.append(
                    {
                        "source_level": level_name,
                        "source_package": package,
                        "actor_object_index": actor_index,
                        "actor_type": actor_type,
                        "actor_name": actor_name,
                        "actor_world_transform": actor_world_transform,
                        "component_object_index": component_index,
                        "component_type": component.get("Type"),
                        "component_name": component.get("Name"),
                        "static_mesh_package": mesh_package,
                        "override_material_packages": [
                            referenced_package(item)
                            for item in component_props.get("OverrideMaterials", [])
                        ]
                        if isinstance(component_props.get("OverrideMaterials"), list)
                        else [],
                        "attach_parent_object_index": local_index(
                            component_props.get("AttachParent"), package
                        ),
                        "local_transform": component_local_transform(component),
                        "visible": visible(actor, component),
                    }
                )

    payload = {
        "status": "analyzed",
        "source_root": str(SOURCE_ROOT),
        "environment_levels": sorted(ENVIRONMENT_LEVELS),
        "level_actor_counts": dict(sorted(level_actor_counts.items())),
        "non_root_static_mesh_component_count": len(non_root_mesh_components),
        "visible_non_root_static_mesh_component_count": sum(
            record["visible"] for record in non_root_mesh_components
        ),
        "fog_sheet_actor_count": len(fog_sheet_actors),
        "non_root_static_mesh_components": non_root_mesh_components,
        "fog_sheet_actors": fog_sheet_actors,
    }
    orientation_packages = sorted(
        {record["static_mesh_package"] for record in non_root_mesh_components}
        | {FOG_MESH_PACKAGE}
    )
    orientation_records = []
    orientation_errors = []
    for package in orientation_packages:
        try:
            orientation_records.append(audit_mesh(package))
        except Exception as exception:
            orientation_errors.append(
                {"package": package, "error": f"{type(exception).__name__}: {exception}"}
            )
    payload["orientation_audit"] = {
        "package_count": len(orientation_packages),
        "audited_mesh_count": len(orientation_records),
        "error_count": len(orientation_errors),
        "normal_winding_totals": {
            key: sum(record["normal_winding_agreement"][key] for record in orientation_records)
            for key in ("positive", "negative", "near_zero")
        },
        "meshes_with_more_negative_than_positive": sum(
            record["normal_winding_agreement"]["negative"]
            > record["normal_winding_agreement"]["positive"]
            for record in orientation_records
        ),
        "errors": orientation_errors,
        "meshes": orientation_records,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    print(
        "HeinMach render gaps: non-root meshes={} visible={} fog sheets={} report={}".format(
            payload["non_root_static_mesh_component_count"],
            payload["visible_non_root_static_mesh_component_count"],
            payload["fog_sheet_actor_count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    main()
