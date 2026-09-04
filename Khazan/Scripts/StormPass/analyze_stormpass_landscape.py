"""Build a compact, reusable StormPass Landscape source inventory.

The two exported level-property JSON files contain hundreds of embedded
Landscape material instances and textures.  This analyzer deliberately keeps
only the references and small parameter records needed for reconstruction; it
never serializes texture payloads or other large arrays into the report.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
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
METADATA_PATH = METADATA_ROOT / "StormPass_LandscapeComponents.json"
REPORT_PATH = (
    PROJECT_ROOT / "Saved" / "ImportReports" / "StormPass_Landscape_SourceAudit.json"
)

LEVELS = {
    "StormPass_Landscape": {
        "landscape": "Landscape_mainfield",
        "component_count": 440,
        "material": (
            "BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/"
            "Landscape_Material/WLM_Stormpass.0"
        ),
    },
    "StormPass_Boss_Phase_2": {
        "landscape": "Landscape_0",
        "component_count": 16,
        "material": (
            "BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/"
            "Landscape_Material/WLM_Stormpass_Phase2.0"
        ),
    },
}
EXPECTED_TOTAL_COMPONENTS = 456
LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def object_path(value) -> str | None:
    if isinstance(value, dict):
        path = value.get("ObjectPath")
        return str(path) if path else None
    return None


def local_index(reference, package: str, object_count: int) -> int | None:
    path = object_path(reference) if isinstance(reference, dict) else str(reference or "")
    if not path or not path.startswith(package + "."):
        return None
    match = LOCAL_INDEX_RE.search(path)
    if not match:
        return None
    index = int(match.group(1))
    return index if 0 <= index < object_count else None


def package_name(objects: list[dict], fallback: str) -> str:
    for item in objects:
        if isinstance(item, dict) and item.get("Type") == "World":
            package = item.get("Package")
            if isinstance(package, str) and package:
                return package
    return fallback


def axes(value, defaults=(0.0, 0.0, 0.0)) -> dict[str, float]:
    value = value if isinstance(value, dict) else {}
    return {
        axis: float(value.get(axis.upper(), default))
        for axis, default in zip(("x", "y", "z"), defaults)
    }


def parameter_info(value) -> dict:
    value = value if isinstance(value, dict) else {}
    return {
        "name": value.get("Name"),
        "association": value.get("Association"),
        "index": value.get("Index"),
    }


def compact_color(value):
    value = value if isinstance(value, dict) else {}
    return {
        channel.lower(): value.get(channel)
        for channel in ("R", "G", "B", "A")
        if channel in value
    }


def compact_parameter_array(values, kind: str) -> list[dict]:
    result = []
    for item in values or []:
        if not isinstance(item, dict):
            continue
        value = item.get("ParameterValue")
        record = {"parameter": parameter_info(item.get("ParameterInfo"))}
        if kind == "texture":
            record["value"] = object_path(value)
        elif kind == "vector":
            record["value"] = compact_color(value)
        else:
            record["value"] = value
        if item.get("ExpressionGUID"):
            record["expression_guid"] = item.get("ExpressionGUID")
        result.append(record)
    return result


def compact_static_parameters(value) -> dict:
    value = value if isinstance(value, dict) else {}
    result = {}
    for key in (
        "StaticSwitchParameters",
        "StaticComponentMaskParameters",
        "TerrainLayerWeightParameters",
    ):
        rows = []
        for item in value.get(key) or []:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "parameter": parameter_info(item.get("ParameterInfo")),
                    "value": item.get("Value"),
                    "override": item.get("bOverride"),
                    "weightmap_index": item.get("WeightmapIndex"),
                }
            )
        if rows:
            result[key] = rows
    return result


def compact_material_instance(
    objects: list[dict], package: str, index: int
) -> dict:
    item = objects[index]
    properties = item.get("Properties") or {}
    return {
        "source_object_index": index,
        "type": item.get("Type"),
        "name": item.get("Name"),
        "parent": object_path(properties.get("Parent")),
        "scalar_parameters": compact_parameter_array(
            properties.get("ScalarParameterValues"), "scalar"
        ),
        "vector_parameters": compact_parameter_array(
            properties.get("VectorParameterValues"), "vector"
        ),
        "texture_parameters": compact_parameter_array(
            properties.get("TextureParameterValues"), "texture"
        ),
        "static_parameters": compact_static_parameters(
            properties.get("StaticParameters")
        ),
        "base_property_overrides": {
            key: value
            for key, value in (properties.get("BasePropertyOverrides") or {}).items()
            if not isinstance(value, (dict, list))
        },
    }


def material_chain(
    objects: list[dict], package: str, first_reference
) -> list[dict]:
    result = []
    seen = set()
    reference = first_reference
    while True:
        index = local_index(reference, package, len(objects))
        if index is None or index in seen:
            break
        seen.add(index)
        record = compact_material_instance(objects, package, index)
        result.append(record)
        reference = (objects[index].get("Properties") or {}).get("Parent")
    return result


def texture_record(objects: list[dict], package: str, reference) -> dict:
    path = object_path(reference)
    record = {"object_path": path}
    index = local_index(reference, package, len(objects))
    if index is None:
        return record
    item = objects[index]
    properties = item.get("Properties") or {}
    record.update(
        {
            "source_object_index": index,
            "type": item.get("Type"),
            "name": item.get("Name"),
            "size_x": properties.get("SizeX"),
            "size_y": properties.get("SizeY"),
            "pixel_format": properties.get("PixelFormat"),
            "srgb": properties.get("SRGB"),
            "lod_group": properties.get("LODGroup"),
            "compression_settings": properties.get("CompressionSettings"),
        }
    )
    return record


def layer_record(value) -> dict:
    value = value if isinstance(value, dict) else {}
    layer = value.get("LayerInfo") or {}
    return {
        "layer_name": layer.get("ObjectName"),
        "layer_path": layer.get("ObjectPath"),
        "weightmap_texture_index": int(value.get("WeightmapTextureIndex", 0)),
        "weightmap_texture_channel": int(value.get("WeightmapTextureChannel", 0)),
    }


def actor_root_transform(objects: list[dict], package: str, properties: dict) -> dict:
    index = local_index(properties.get("RootComponent"), package, len(objects))
    if index is None:
        raise RuntimeError("Landscape root component reference is invalid")
    root = objects[index]
    root_properties = root.get("Properties") or {}
    rotation = root_properties.get("RelativeRotation") or {}
    return {
        "source_object_index": index,
        "name": root.get("Name"),
        "location_cm": axes(root_properties.get("RelativeLocation")),
        "rotation_degrees": {
            "pitch": float(rotation.get("Pitch", 0.0)),
            "yaw": float(rotation.get("Yaw", 0.0)),
            "roll": float(rotation.get("Roll", 0.0)),
        },
        "scale": axes(root_properties.get("RelativeScale3D"), (1.0, 1.0, 1.0)),
    }


def existing_texture_candidates(level_name: str, texture_names: set[str]) -> dict:
    roots = [
        SOURCE_ROOT / level_name,
        WORLD_ROOT / level_name,
    ]
    candidates = {}
    for name in sorted(texture_names):
        found = []
        for root in roots:
            if not root.is_dir():
                continue
            for extension in (".png", ".tga", ".dds", ".jpg", ".exr"):
                found.extend(str(path) for path in root.rglob(name + extension))
        candidates[name] = sorted(set(found))
    return candidates


def analyze_level(level_name: str, expectation: dict) -> dict:
    source_json = SOURCE_ROOT / (level_name + ".json")
    if not source_json.is_file():
        raise RuntimeError(f"Missing Landscape JSON: {source_json}")
    objects = load_json(source_json)
    if not isinstance(objects, list):
        raise RuntimeError(f"Expected object array: {source_json}")
    fallback_package = "BBQ/Content/_Kazan_/Level/StormPass/" + level_name
    package = package_name(objects, fallback_package)
    actors = [
        (index, item)
        for index, item in enumerate(objects)
        if isinstance(item, dict) and item.get("Type") == "Landscape"
    ]
    if len(actors) != 1:
        raise RuntimeError(f"Expected one Landscape actor in {level_name}")
    actor_index, actor = actors[0]
    if actor.get("Name") != expectation["landscape"]:
        raise RuntimeError(f"Landscape name changed in {level_name}")
    properties = actor.get("Properties") or {}
    source_material = object_path(properties.get("LandscapeMaterial"))
    if source_material != expectation["material"]:
        raise RuntimeError(f"Landscape material changed in {level_name}")
    root_transform = actor_root_transform(objects, package, properties)

    component_records = []
    material_instances = {}
    referenced_texture_names = set()
    missing_usd = []
    layer_counter = Counter()
    layer_combination_counter = Counter()
    weightmap_channel_counter = Counter()
    for component_reference in properties.get("LandscapeComponents") or []:
        component_index = local_index(component_reference, package, len(objects))
        if component_index is None:
            raise RuntimeError(f"Invalid LandscapeComponent reference in {level_name}")
        component = objects[component_index]
        component_properties = component.get("Properties") or {}
        component_name = str(component.get("Name"))
        source_usd = (
            WORLD_ROOT
            / level_name
            / "PersistentLevel"
            / str(actor.get("Name"))
            / (component_name + ".usda")
        )
        if not source_usd.is_file():
            missing_usd.append(str(source_usd))
        allocations = [
            layer_record(item)
            for item in component_properties.get("WeightmapLayerAllocations") or []
        ]
        for allocation in allocations:
            layer_counter[allocation["layer_path"] or "<none>"] += 1
            weightmap_channel_counter[
                "{}:{}".format(
                    allocation["weightmap_texture_index"],
                    allocation["weightmap_texture_channel"],
                )
            ] += 1
        layer_combination_counter[
            "|".join(sorted(item["layer_path"] or "<none>" for item in allocations))
        ] += 1
        heightmap = texture_record(
            objects, package, component_properties.get("HeightmapTexture")
        )
        weightmaps = [
            texture_record(objects, package, item)
            for item in component_properties.get("WeightmapTextures") or []
        ]
        for texture in [heightmap, *weightmaps]:
            if texture.get("name"):
                referenced_texture_names.add(texture["name"])
        material_refs = component_properties.get("MaterialInstances") or []
        chains = []
        for material_ref in material_refs:
            chain = material_chain(objects, package, material_ref)
            chains.append(
                {
                    "material_reference": object_path(material_ref),
                    "chain_object_indices": [
                        item["source_object_index"] for item in chain
                    ],
                    "terminal_parent": chain[-1]["parent"] if chain else None,
                }
            )
            for item in chain:
                material_instances[str(item["source_object_index"])] = item
        cached_box = component_properties.get("CachedLocalBox") or {}
        component_records.append(
            {
                "source_level": level_name,
                "landscape_name": actor.get("Name"),
                "component_name": component_name,
                "source_object_index": component_index,
                "source_usd": str(source_usd),
                "source_usd_bytes": source_usd.stat().st_size if source_usd.is_file() else 0,
                "section_base": {
                    "x": int(component_properties.get("SectionBaseX", 0)),
                    "y": int(component_properties.get("SectionBaseY", 0)),
                },
                "component_size_quads": int(
                    component_properties.get("ComponentSizeQuads", 63)
                ),
                "subsection_size_quads": int(
                    component_properties.get("SubsectionSizeQuads", 63)
                ),
                "num_subsections": int(component_properties.get("NumSubsections", 1)),
                "relative_location": axes(component_properties.get("RelativeLocation")),
                "cached_local_box": {
                    "min": axes((cached_box or {}).get("Min")),
                    "max": axes((cached_box or {}).get("Max"), (63.0, 63.0, 0.0)),
                },
                "heightmap": heightmap,
                "weightmaps": weightmaps,
                "weightmap_scale_bias": component_properties.get("WeightmapScaleBias"),
                "heightmap_scale_bias": component_properties.get("HeightmapScaleBias"),
                "weightmap_subsection_offset": component_properties.get(
                    "WeightmapSubsectionOffset"
                ),
                "layer_allocations": allocations,
                "material_instances": chains,
                "root_transform": root_transform,
            }
        )

    if len(component_records) != expectation["component_count"]:
        raise RuntimeError(
            f"Component count changed in {level_name}: "
            f"{len(component_records)} != {expectation['component_count']}"
        )
    image_candidates = existing_texture_candidates(level_name, referenced_texture_names)
    return {
        "source_level": level_name,
        "source_package": package,
        "source_json": str(source_json),
        "source_json_bytes": source_json.stat().st_size,
        "source_object_count": len(objects),
        "source_actor_index": actor_index,
        "landscape_name": actor.get("Name"),
        "landscape_material": source_material,
        "root_transform": root_transform,
        "component_count": len(component_records),
        "components": component_records,
        "embedded_material_instances": [
            material_instances[key]
            for key in sorted(material_instances, key=lambda item: int(item))
        ],
        "referenced_texture_names": sorted(referenced_texture_names),
        "texture_image_candidates": image_candidates,
        "summary": {
            "embedded_texture2d_object_count": sum(
                1 for item in objects if isinstance(item, dict) and item.get("Type") == "Texture2D"
            ),
            "referenced_heightmap_count": len(
                {item["heightmap"].get("object_path") for item in component_records}
            ),
            "referenced_weightmap_count": len(
                {
                    texture.get("object_path")
                    for item in component_records
                    for texture in item["weightmaps"]
                }
            ),
            "embedded_material_instance_count": len(material_instances),
            "missing_usd_count": len(missing_usd),
            "missing_usd": missing_usd,
            "layer_allocation_counts": dict(sorted(layer_counter.items())),
            "layer_combination_counts": dict(sorted(layer_combination_counter.items())),
            "weightmap_channel_counts": dict(sorted(weightmap_channel_counter.items())),
            "texture_image_candidate_count": sum(
                1 for paths in image_candidates.values() if paths
            ),
        },
    }


def main() -> dict:
    levels = [analyze_level(name, expectation) for name, expectation in LEVELS.items()]
    component_count = sum(item["component_count"] for item in levels)
    missing_usd_count = sum(item["summary"]["missing_usd_count"] for item in levels)
    if component_count != EXPECTED_TOTAL_COMPONENTS:
        raise RuntimeError(
            f"Total Landscape component count changed: {component_count}"
        )
    payload = {
        "schema_version": 1,
        "source_scope": [item["source_json"] for item in levels],
        "levels": levels,
        "summary": {
            "level_count": len(levels),
            "component_count": component_count,
            "missing_usd_count": missing_usd_count,
            "source_usd_total_bytes": sum(
                component["source_usd_bytes"]
                for level in levels
                for component in level["components"]
            ),
            "referenced_heightmap_count": sum(
                level["summary"]["referenced_heightmap_count"] for level in levels
            ),
            "referenced_weightmap_count": sum(
                level["summary"]["referenced_weightmap_count"] for level in levels
            ),
            "embedded_material_instance_count": sum(
                level["summary"]["embedded_material_instance_count"] for level in levels
            ),
            "texture_image_candidate_count": sum(
                level["summary"]["texture_image_candidate_count"] for level in levels
            ),
            "fog_deferred": True,
        },
    }
    write_json(METADATA_PATH, payload)
    report = {
        "status": "passed" if missing_usd_count == 0 else "failed",
        "metadata_path": str(METADATA_PATH),
        "source_scope": payload["source_scope"],
        "summary": payload["summary"],
        "levels": [
            {
                "source_level": item["source_level"],
                "landscape_name": item["landscape_name"],
                "landscape_material": item["landscape_material"],
                "component_count": item["component_count"],
                **item["summary"],
            }
            for item in levels
        ],
        "policy": {
            "geometry": "Use exact FModel component USDA geometry and root transform.",
            "materials": (
                "Preserve source layer, weightmap, and embedded MIC references for "
                "a weightmap-aware reconstruction pass."
            ),
            "fog": "Strictly deferred until all geometry, materials, foliage and lights pass.",
        },
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("StormPass Landscape source audit failed")
    return payload


if __name__ == "__main__":
    main()
