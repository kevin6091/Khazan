"""Build a source-of-truth manifest for the StormPass environment stack.

This pass is offline and does not touch Unreal content.  It resolves the cooked
WEP inheritance exported by FModel, inventories the original post-process
volume bounds, sky/cloud proxy meshes, global light/fog profiles, and spherical
reflection captures.  The resulting manifest is consumed by the final Level
content restoration pass.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
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
WORLD_ASSET_ROOT = (
    FMODEL_ROOT
    / "BBQ"
    / "Content"
    / "_Kazan_"
    / "Level"
    / "StormPass"
)
AR_DATA_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "Art"
    / "ArtRendering"
    / "AR_Data"
)
WEP_ROOT = (
    FMODEL_ROOT
    / "Exports"
    / "BBQ"
    / "Content"
    / "Art"
    / "ArtRendering"
    / "AR_PostProcess"
    / "WEP"
)
RAW_ASSET_ROOT = FMODEL_ROOT / "BBQ" / "Content"
METADATA_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_EnvironmentProfile.json"
)
SCOPE_PATH = METADATA_PATH.parent / "StormPass_SourceScope.json"
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_EnvironmentProfile_SourceAudit.json"
)

PROFILE_PACKAGES = {
    "outside": "WEP_StormPass_Outside.json",
    "cave": "WEP_StormPass_Cave.json",
    "ice_outside": "WEP_StormPass_IceOutside.json",
    "storm_outside": "WEP_StormPass_StormOutside.json",
    "boss_phase_1": "WEP_StormPass_Boss_Phase1.json",
    "boss_phase_2": "WEP_StormPass_Boss_Phase2.json",
}
BASE_COMPONENT_FILES = {
    "EMP_Outdoor_C": AR_DATA_ROOT / "EnvMaterial" / "EMP_Outdoor.json",
    "EMP_Rainy_C": AR_DATA_ROOT / "EnvMaterial" / "EMP_Rainy.json",
    "ERP_Base_C": AR_DATA_ROOT / "EnvRenderParams" / "ERP_Base.json",
    "FOG_Deep_C": AR_DATA_ROOT / "Fog" / "FOG_Deep.json",
    "FOG_Outdoor_C": AR_DATA_ROOT / "Fog" / "FOG_Outdoor.json",
    "WDL_Midday_C": AR_DATA_ROOT / "Light" / "WDL_Midday.json",
    "WDL_Dawn_C": AR_DATA_ROOT / "Light" / "WDL_Dawn.json",
    "WDL_Sunset_C": AR_DATA_ROOT / "Light" / "WDL_Sunset.json",
    "WSL_Base_C": AR_DATA_ROOT / "Light" / "WSL_Base.json",
}
BASE_POST_PROCESS_PATH = (
    AR_DATA_ROOT / "PostProcess" / "WEP_Base_PostProcess.json"
)
MATERIAL_FILES = {
    "cloud_layer_1": (
        AR_DATA_ROOT / "CloudMaterial" / "CCM_WhiteCloud_Layer1.json"
    ),
    "cloud_layer_2": (
        AR_DATA_ROOT / "CloudMaterial" / "CCM_GloomyDawnCloud_Layer2.json"
    ),
    "sky_gloomy_day": (
        AR_DATA_ROOT / "SkyMaterial" / "SCM_SkyColor_GloomyDay.json"
    ),
    "sky_proxy_original": (
        AR_DATA_ROOT / "SkyMaterial" / "SCM_SkyColor_Midday.json"
    ),
}
ENVIRONMENT_WORLD_PATH = SOURCE_ROOT / "StormPass_Light.json"
EXPECTED_PROFILE_COUNT = 6
EXPECTED_WEP_INSTANCE_COUNT = 10
EXPECTED_REFLECTION_CAPTURE_COUNT = 9
EXPECTED_CLOUD_COMPONENT_COUNT = 2
EXPECTED_SKY_COMPONENT_COUNT = 1


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def object_index(reference) -> int | None:
    if not isinstance(reference, dict):
        return None
    path = str(reference.get("ObjectPath", ""))
    tail = path.rsplit(".", 1)[-1]
    return int(tail) if tail.isdigit() else None


def merge_dict(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def default_properties(objects: list[dict], expected_type: str) -> dict:
    matches = [
        obj
        for obj in objects
        if obj.get("Type") == expected_type
        and str(obj.get("Name", "")).startswith("Default__")
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one {expected_type} CDO, found {len(matches)}"
        )
    return copy.deepcopy(matches[0].get("Properties") or {})


def first_component(objects: list[dict], prefix: str) -> dict | None:
    matches = [obj for obj in objects if str(obj.get("Type", "")).startswith(prefix)]
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {prefix} component, found {len(matches)}")
    return matches[0]


def reference_package(value) -> str | None:
    if not isinstance(value, dict):
        return None
    path = value.get("ObjectPath")
    if not isinstance(path, str) or not path:
        return None
    return path.rsplit(".", 1)[0]


def normalize_transform(properties: dict) -> dict:
    location = properties.get("RelativeLocation") or {}
    rotation = properties.get("RelativeRotation") or {}
    scale = properties.get("RelativeScale3D") or {}
    return {
        "location_cm": {
            "x": float(location.get("X", 0.0)),
            "y": float(location.get("Y", 0.0)),
            "z": float(location.get("Z", 0.0)),
        },
        "rotation_degrees": {
            "pitch": float(rotation.get("Pitch", 0.0)),
            "yaw": float(rotation.get("Yaw", 0.0)),
            "roll": float(rotation.get("Roll", 0.0)),
        },
        "scale": {
            "x": float(scale.get("X", 1.0)),
            "y": float(scale.get("Y", 1.0)),
            "z": float(scale.get("Z", 1.0)),
        },
    }


def color_payload(value):
    if not isinstance(value, dict):
        return value
    return {
        key: value[key]
        for key in ("R", "G", "B", "A", "Hex")
        if key in value
    }


def material_parameters(path: Path) -> dict:
    objects = load_json(path)
    materials = [obj for obj in objects if obj.get("Type") == "MaterialInstanceConstant"]
    if len(materials) != 1:
        raise RuntimeError(f"Expected one material instance in {path}")
    obj = materials[0]
    properties = obj.get("Properties") or {}

    def parameter_rows(source, value_key):
        rows = []
        for row in source or []:
            info = row.get("ParameterInfo") or {}
            rows.append(
                {
                    "name": info.get("Name"),
                    "value": copy.deepcopy(row.get(value_key)),
                }
            )
        return rows

    return {
        "source_json": str(path),
        "source_sha256": sha256(path),
        "name": obj.get("Name"),
        "parent_package": reference_package(properties.get("Parent")),
        "scalar_parameters": parameter_rows(
            properties.get("ScalarParameterValues"), "ParameterValue"
        ),
        "vector_parameters": parameter_rows(
            properties.get("VectorParameterValues"), "ParameterValue"
        ),
        "texture_parameters": parameter_rows(
            properties.get("TextureParameterValues"), "ParameterValue"
        ),
        "base_property_overrides": copy.deepcopy(
            properties.get("BasePropertyOverrides") or {}
        ),
        "cached_referenced_textures": [
            reference_package(value)
            for value in properties.get("CachedReferencedTextures") or []
            if reference_package(value)
        ],
    }


def resolve_profiles() -> dict:
    base_post_process = default_properties(
        load_json(BASE_POST_PROCESS_PATH), "WEP_Base_PostProcess_C"
    )
    base_components = {
        type_name: default_properties(load_json(path), type_name)
        for type_name, path in BASE_COMPONENT_FILES.items()
    }
    profiles = {}
    for key, filename in PROFILE_PACKAGES.items():
        path = WEP_ROOT / filename
        objects = load_json(path)
        class_objects = [obj for obj in objects if obj.get("Type") == "BlueprintGeneratedClass"]
        if len(class_objects) != 1:
            raise RuntimeError(f"Unexpected class inventory in {path}")
        class_name = class_objects[0].get("Name")
        profile_default = default_properties(objects, class_name)
        merged_default = merge_dict(base_post_process, profile_default)
        components = {}
        for prefix, label in (
            ("EMP_", "environment_material"),
            ("ERP_", "render_parameters"),
            ("FOG_", "fog"),
            ("WDL_", "directional_light"),
            ("WSL_", "sky_light"),
        ):
            obj = first_component(objects, prefix)
            if obj is None:
                continue
            type_name = obj.get("Type")
            base = base_components.get(type_name)
            if base is None:
                raise RuntimeError(
                    f"Missing extracted base component {type_name} for {filename}"
                )
            components[label] = {
                "source_type": type_name,
                "source_name": obj.get("Name"),
                "properties": merge_dict(base, obj.get("Properties") or {}),
                "explicit_overrides": copy.deepcopy(obj.get("Properties") or {}),
            }
        profiles[key] = {
            "source_json": str(path),
            "source_sha256": sha256(path),
            "source_class": class_name,
            "default_properties": merged_default,
            "explicit_default_overrides": profile_default,
            "components": components,
        }
    return profiles


def is_axis_aligned_box(model: dict) -> bool:
    points = model.get("Points") or []
    bounds = model.get("Bounds") or {}
    origin = bounds.get("Origin") or {}
    extent = bounds.get("BoxExtent") or {}
    if len(points) != 8:
        return False
    expected = set()
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                expected.add(
                    (
                        round(float(origin.get("X", 0.0)) + sx * float(extent.get("X", 0.0)), 4),
                        round(float(origin.get("Y", 0.0)) + sy * float(extent.get("Y", 0.0)), 4),
                        round(float(origin.get("Z", 0.0)) + sz * float(extent.get("Z", 0.0)), 4),
                    )
                )
    actual = {
        (
            round(float(point.get("X", 0.0)), 4),
            round(float(point.get("Y", 0.0)), 4),
            round(float(point.get("Z", 0.0)), 4),
        )
        for point in points
    }
    return actual == expected


def world_actor_transform(actor: dict, objects: list[dict]) -> dict:
    properties = actor.get("Properties") or {}
    root_index = object_index(properties.get("RootComponent"))
    root_properties = {}
    if root_index is not None and 0 <= root_index < len(objects):
        root_properties = objects[root_index].get("Properties") or {}
    return normalize_transform(merge_dict(properties, root_properties))


def source_profile_key(actor_type: str) -> str:
    mapping = {
        "WEP_StormPass_Outside_C": "outside",
        "WEP_StormPass_Cave_C": "cave",
        "WEP_StormPass_IceOutside_C": "ice_outside",
        "WEP_StormPass_StormOutside_C": "storm_outside",
        "WEP_StormPass_Boss_Phase1_C": "boss_phase_1",
        "WEP_StormPass_Boss_Phase2_C": "boss_phase_2",
    }
    if actor_type not in mapping:
        raise RuntimeError(f"Unknown StormPass WEP type: {actor_type}")
    return mapping[actor_type]


def volume_inventory(visual_levels: list[str]) -> list[dict]:
    rows = []
    for level_name in visual_levels:
        path = SOURCE_ROOT / f"{level_name}.json"
        objects = load_json(path)
        for actor_index, actor in enumerate(objects):
            actor_type = str(actor.get("Type", ""))
            if not actor_type.startswith("WEP_StormPass_"):
                continue
            properties = actor.get("Properties") or {}
            brush_index = object_index(properties.get("Brush"))
            if brush_index is None or not (0 <= brush_index < len(objects)):
                raise RuntimeError(
                    f"Missing WEP brush model: {level_name}[{actor_index}]"
                )
            model = objects[brush_index]
            bounds = model.get("Bounds") or {}
            extent = bounds.get("BoxExtent") or {}
            origin = bounds.get("Origin") or {}
            rows.append(
                {
                    "source_level": level_name,
                    "source_json": str(path),
                    "source_actor_index": actor_index,
                    "source_actor_type": actor_type,
                    "source_actor_name": actor.get("Name"),
                    "profile_key": source_profile_key(actor_type),
                    "priority": float(properties.get("Priority", 0.0)),
                    "blend_radius": float(properties.get("BlendRadius", 100.0)),
                    "blend_weight": float(properties.get("BlendWeight", 1.0)),
                    "enabled": bool(properties.get("bEnabled", True)),
                    "unbound": bool(properties.get("bUnbound", False)),
                    "trigger_volume": bool(properties.get("bTriggerVolume", False)),
                    "transform": world_actor_transform(actor, objects),
                    "model_object_index": brush_index,
                    "model_origin_cm": {
                        "x": float(origin.get("X", 0.0)),
                        "y": float(origin.get("Y", 0.0)),
                        "z": float(origin.get("Z", 0.0)),
                    },
                    "model_box_extent_cm": {
                        "x": float(extent.get("X", 0.0)),
                        "y": float(extent.get("Y", 0.0)),
                        "z": float(extent.get("Z", 0.0)),
                    },
                    "model_point_count": len(model.get("Points") or []),
                    "axis_aligned_box_model": is_axis_aligned_box(model),
                    "model_points_cm": [
                        {
                            "x": float(point.get("X", 0.0)),
                            "y": float(point.get("Y", 0.0)),
                            "z": float(point.get("Z", 0.0)),
                        }
                        for point in model.get("Points") or []
                    ],
                    "model_planes": [
                        copy.deepcopy((node.get("Plane") or {}))
                        for node in model.get("Nodes") or []
                    ],
                }
            )
    return rows


def dynamic_material_record(obj: dict) -> dict:
    properties = obj.get("Properties") or {}
    rows = {
        "source_object_type": obj.get("Type"),
        "source_object_name": obj.get("Name"),
        "parent_package": reference_package(properties.get("Parent")),
    }
    for source_key, output_key, value_key in (
        ("ScalarParameterValues", "scalar_parameters", "ParameterValue"),
        ("VectorParameterValues", "vector_parameters", "ParameterValue"),
        ("TextureParameterValues", "texture_parameters", "ParameterValue"),
    ):
        values = []
        for row in properties.get(source_key) or []:
            info = row.get("ParameterInfo") or {}
            values.append(
                {
                    "name": info.get("Name"),
                    "value": copy.deepcopy(row.get(value_key)),
                }
            )
        rows[output_key] = values
    return rows


def environment_proxy_inventory(objects: list[dict]) -> dict:
    actors = [
        (index, obj)
        for index, obj in enumerate(objects)
        if obj.get("Type") == "xxEnvironmentProxy"
    ]
    if len(actors) != 1:
        raise RuntimeError(f"Expected one environment proxy, found {len(actors)}")
    actor_index, actor = actors[0]
    actor_path_suffix = f".{actor_index}"
    children = [
        (index, obj)
        for index, obj in enumerate(objects)
        if str((obj.get("Outer") or {}).get("ObjectPath", "")).endswith(
            actor_path_suffix
        )
    ]
    components = []
    for index, obj in children:
        obj_type = str(obj.get("Type", ""))
        if obj_type not in {
            "xxEnvCloudComponent",
            "xxSkyMeshComponent",
            "xxWindDSComponent",
            "xxEnvironmentMaterialParameterComponent",
        }:
            continue
        properties = obj.get("Properties") or {}
        row = {
            "source_object_index": index,
            "source_object_type": obj_type,
            "source_object_name": obj.get("Name"),
            "transform": normalize_transform(properties),
            "properties": copy.deepcopy(properties),
        }
        mesh = reference_package(properties.get("StaticMesh"))
        if mesh:
            row["static_mesh_package"] = mesh
        override_materials = []
        for reference in properties.get("OverrideMaterials") or []:
            material_index = object_index(reference)
            if material_index is None or not (0 <= material_index < len(objects)):
                raise RuntimeError("Environment proxy material reference is unresolved")
            override_materials.append(
                {
                    "source_object_index": material_index,
                    **dynamic_material_record(objects[material_index]),
                }
            )
        if override_materials:
            row["override_materials"] = override_materials
        components.append(row)
    return {
        "source_actor_index": actor_index,
        "source_actor_name": actor.get("Name"),
        "source_actor_type": actor.get("Type"),
        "components": components,
    }


def reflection_capture_inventory(objects: list[dict]) -> list[dict]:
    rows = []
    for actor_index, actor in enumerate(objects):
        if actor.get("Type") != "SphereReflectionCapture":
            continue
        properties = actor.get("Properties") or {}
        component_index = object_index(properties.get("CaptureComponent"))
        if component_index is None or not (0 <= component_index < len(objects)):
            raise RuntimeError("Reflection capture component reference is unresolved")
        component = objects[component_index]
        component_properties = component.get("Properties") or {}
        rows.append(
            {
                "source_actor_index": actor_index,
                "source_actor_name": actor.get("Name"),
                "source_component_index": component_index,
                "transform": normalize_transform(component_properties),
                "influence_radius_cm": float(
                    component_properties.get("InfluenceRadius", 3000.0)
                ),
                "brightness": float(component_properties.get("Brightness", 1.0)),
                "capture_source_type": component_properties.get(
                    "ReflectionSourceType", "RS_CapturedScene"
                ),
                "specified_cubemap_package": reference_package(
                    component_properties.get("Cubemap")
                ),
            }
        )
    return rows


def main():
    required = [
        SOURCE_ROOT,
        WEP_ROOT,
        BASE_POST_PROCESS_PATH,
        ENVIRONMENT_WORLD_PATH,
        SCOPE_PATH,
        *BASE_COMPONENT_FILES.values(),
        *MATERIAL_FILES.values(),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing StormPass source data: " + "; ".join(missing))

    scope = load_json(SCOPE_PATH)
    visual_levels = list(scope.get("visual_levels") or [])
    profiles = resolve_profiles()
    volumes = volume_inventory(visual_levels)
    light_objects = load_json(ENVIRONMENT_WORLD_PATH)
    proxy = environment_proxy_inventory(light_objects)
    captures = reflection_capture_inventory(light_objects)
    materials = {
        key: material_parameters(path) for key, path in MATERIAL_FILES.items()
    }

    cloud_components = [
        row
        for row in proxy["components"]
        if row["source_object_type"] == "xxEnvCloudComponent"
    ]
    sky_components = [
        row
        for row in proxy["components"]
        if row["source_object_type"] == "xxSkyMeshComponent"
    ]
    failures = []
    if len(profiles) != EXPECTED_PROFILE_COUNT:
        failures.append("profile_count")
    if len(volumes) != EXPECTED_WEP_INSTANCE_COUNT:
        failures.append("wep_instance_count")
    if len(captures) != EXPECTED_REFLECTION_CAPTURE_COUNT:
        failures.append("reflection_capture_count")
    if len(cloud_components) != EXPECTED_CLOUD_COMPONENT_COUNT:
        failures.append("cloud_component_count")
    if len(sky_components) != EXPECTED_SKY_COMPONENT_COUNT:
        failures.append("sky_component_count")
    if any(
        not str(row["capture_source_type"]).endswith("SpecifiedCubemap")
        for row in captures
    ):
        failures.append("reflection_capture_source_type")
    if any(not row["specified_cubemap_package"] for row in captures):
        failures.append("reflection_capture_cubemap")

    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    payload = {
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
        "level": "StormPass",
        "generated_at": generated_at,
        "content_boundary": (
            "Environment Level content only: transforms, materials, lighting, "
            "post process, reflections, sky/cloud, and Fog. No gameplay/source code."
        ),
        "default_profile_key": "outside",
        "fog_restore_order": "last",
        "profiles": profiles,
        "post_process_volumes": volumes,
        "environment_proxy": proxy,
        "reflection_captures": captures,
        "source_material_profiles": materials,
        "asset_sources": {
            "cloud_mesh_usda": str(
                RAW_ASSET_ROOT
                / "Art"
                / "ArtRendering"
                / "AR_Data"
                / "Atmosphere"
                / "WAS_CloudMesh.usda"
            ),
            "sky_mesh_usda": str(
                RAW_ASSET_ROOT
                / "Art"
                / "ArtRendering"
                / "AR_Data"
                / "Atmosphere"
                / "WAS_SkyMesh.usda"
            ),
            "reflection_cubemap_hdr": str(
                RAW_ASSET_ROOT / "_Common" / "CommonTexture" / "Base_Cube.hdr"
            ),
            "sky_textures": [
                str(
                    RAW_ASSET_ROOT
                    / "_Kazan_"
                    / "Art"
                    / "VFX"
                    / "VFX_Texture"
                    / "BBQ_Texture"
                    / "World"
                    / f"{name}.png"
                )
                for name in (
                    "FTW_Sky_Cloud_Distortion",
                    "FTW_Sky_Cloud_LookUp",
                    "FTW_Sky_Cloud_Nomal",
                    "FTW_Sky_Nebula",
                    "FTW_Sky_Star_Mask_001",
                    "FTW_Smoke_Noise_002",
                )
            ],
        },
        "counts": {
            "profile_count": len(profiles),
            "post_process_volume_count": len(volumes),
            "axis_aligned_box_volume_count": sum(
                row["axis_aligned_box_model"] for row in volumes
            ),
            "reflection_capture_count": len(captures),
            "environment_proxy_component_count": len(proxy["components"]),
            "cloud_component_count": len(cloud_components),
            "sky_component_count": len(sky_components),
            "source_material_profile_count": len(materials),
        },
        "failures": failures,
    }
    for source in payload["asset_sources"].values():
        values = source if isinstance(source, list) else [source]
        for value in values:
            if not Path(value).is_file():
                failures.append("missing_asset_source:" + value)
    payload["status"] = "passed" if not failures else "failed"
    payload["failures"] = failures
    dump_json(METADATA_PATH, payload)
    dump_json(REPORT_PATH, payload)
    print(
        "KHAZAN_STORMPASS_ENVIRONMENT_SOURCE_AUDIT "
        + json.dumps(
            {
                "status": payload["status"],
                "counts": payload["counts"],
                "failures": failures,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if failures:
        raise RuntimeError("StormPass environment source audit failed")
    return payload


if __name__ == "__main__":
    main()
