"""Resolve all deferred StormPass fog-sheet MIDs from FModel Level JSON.

The deferred actor manifest contains references to per-actor
MaterialInstanceDynamic exports.  Their exact scalar/vector parameters live in
the original Level JSON, so this read-only analysis resolves those object
indices before any Fog assets or actors are created in Unreal.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
FMODEL_EXPORT_ROOT = FMODEL_ROOT / "Exports"
DEFERRED_METADATA_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_DeferredFog.json"
)
OUTPUT_METADATA_PATH = DEFERRED_METADATA_PATH.with_name(
    "StormPass_FogMaterials.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_FogMaterial_SourceAudit.json"
)
BLUEPRINT_JSON = {
    "WBP_FogSheet_C": (
        FMODEL_EXPORT_ROOT
        / "BBQ"
        / "Content"
        / "_Kazan_"
        / "Art"
        / "Terrain"
        / "Terrain_VFX"
        / "WBP_FogSheet.json"
    ),
    "WBP_FogSheet_Local_C": (
        FMODEL_EXPORT_ROOT
        / "BBQ"
        / "Content"
        / "Art"
        / "World"
        / "World_Data"
        / "WBP"
        / "WBP_FogSheet_Local.json"
    ),
}
EXPECTED_COUNT = 53
EXPECTED_TYPE_COUNTS = {"WBP_FogSheet_C": 51, "WBP_FogSheet_Local_C": 2}
EXPECTED_LEVEL_COUNTS = {
    "StormPass_Boss_Phase_2": 7,
    "StormPass_Boss_Phase_Clear": 12,
    "StormPass_Light": 34,
}
EXPECTED_PARENT_COUNTS = {
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_01": 6,
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_02": 45,
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/BBQ_Material/World/FM_FogSheet_Local": 2,
}
EXPECTED_NOISE_PACKAGE = (
    "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/BBQ_Texture/World/"
    "FTW_Smoke_Noise_001"
)
OBJECT_INDEX_RE = re.compile(r"\.(\d+)$")


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def package_without_object(path):
    value = str(path or "").replace("\\", "/")
    return OBJECT_INDEX_RE.sub("", value)


def source_json_path(package):
    relative = Path(*str(package).replace("\\", "/").split("/"))
    return FMODEL_EXPORT_ROOT / relative.with_suffix(".json")


def one_static_mesh_component(record):
    components = [
        component
        for component in record.get("components", [])
        if component.get("type") == "StaticMeshComponent"
    ]
    if len(components) != 1:
        raise RuntimeError(
            "Fog actor {} has {} StaticMeshComponents".format(
                record.get("actor_name"), len(components)
            )
        )
    return components[0]


def parameter_map(entries):
    result = {}
    for entry in entries or []:
        name = str((entry.get("ParameterInfo") or {}).get("Name", ""))
        if not name or name in result:
            raise RuntimeError("Invalid or duplicate MID parameter: " + name)
        result[name] = entry.get("ParameterValue")
    return result


def blueprint_template(actor_type):
    path = BLUEPRINT_JSON[actor_type]
    objects = load_json(path)
    matches = [
        obj
        for obj in objects
        if obj.get("Type") == "StaticMeshComponent"
        and obj.get("Name") == "StaticMesh_GEN_VARIABLE"
    ]
    if len(matches) != 1:
        raise RuntimeError("Fog Blueprint mesh template inventory changed")
    properties = matches[0].get("Properties") or {}
    mesh = package_without_object((properties.get("StaticMesh") or {}).get("ObjectPath"))
    materials = properties.get("OverrideMaterials") or []
    if len(materials) != 1:
        raise RuntimeError("Fog Blueprint material template inventory changed")
    body = properties.get("BodyInstance") or {}
    return {
        "source_json": str(path),
        "source_json_sha256": sha256_file(path),
        "static_mesh_package": mesh,
        "default_material_package": package_without_object(
            materials[0].get("ObjectPath")
        ),
        "receives_decals": bool(properties.get("bReceivesDecals", True)),
        "use_as_occluder": bool(properties.get("bUseAsOccluder", True)),
        "cast_shadow": bool(properties.get("CastShadow", True)),
        "cast_dynamic_shadow": bool(properties.get("bCastDynamicShadow", True)),
        "cast_static_shadow": bool(properties.get("bCastStaticShadow", True)),
        "affect_dynamic_indirect_lighting": bool(
            properties.get("bAffectDynamicIndirectLighting", True)
        ),
        "affect_distance_field_lighting": bool(
            properties.get("bAffectDistanceFieldLighting", True)
        ),
        "can_character_step_up_on": properties.get("CanCharacterStepUpOn"),
        "collision_enabled": body.get("CollisionEnabled"),
        "collision_profile_name": body.get("CollisionProfileName"),
        "can_ever_affect_navigation": bool(
            properties.get("bCanEverAffectNavigation", True)
        ),
    }


def main():
    deferred = load_json(DEFERRED_METADATA_PATH)
    actors = list(deferred.get("actors", []))
    if (
        deferred.get("schema_version") != 1
        or deferred.get("level") != "StormPass"
        or deferred.get("restoration_state") != "deferred_until_final_pass"
        or len(actors) != EXPECTED_COUNT
    ):
        raise RuntimeError("Deferred StormPass Fog metadata is incomplete")
    type_counts = collections.Counter(actor.get("actor_type") for actor in actors)
    level_counts = collections.Counter(actor.get("source_level") for actor in actors)
    if dict(sorted(type_counts.items())) != EXPECTED_TYPE_COUNTS:
        raise RuntimeError("Deferred Fog actor-type inventory changed")
    if dict(sorted(level_counts.items())) != EXPECTED_LEVEL_COUNTS:
        raise RuntimeError("Deferred Fog source-level inventory changed")

    templates = {
        actor_type: blueprint_template(actor_type)
        for actor_type in EXPECTED_TYPE_COUNTS
    }
    source_cache = {}
    source_hashes = {}
    results = []
    parent_counts = collections.Counter()
    mesh_counts = collections.Counter()
    scalar_name_counts = collections.Counter()
    vector_name_counts = collections.Counter()
    texture_name_counts = collections.Counter()
    cached_texture_counts = collections.Counter()
    two_sided_parent_pairs = collections.Counter()
    component_setting_counts = collections.Counter()

    for actor in actors:
        actor_type = actor["actor_type"]
        component = one_static_mesh_component(actor)
        overrides = component.get("properties", {}).get("OverrideMaterials") or []
        if len(overrides) != 1:
            raise RuntimeError("Fog actor does not have one dynamic material")
        reference_path = str(overrides[0].get("ObjectPath", ""))
        index_match = OBJECT_INDEX_RE.search(reference_path)
        if not index_match:
            raise RuntimeError("Fog MID reference has no source object index")
        export_index = int(index_match.group(1))
        json_path = source_json_path(actor["source_package"])
        if json_path not in source_cache:
            source_cache[json_path] = load_json(json_path)
            source_hashes[str(json_path)] = sha256_file(json_path)
        objects = source_cache[json_path]
        if export_index < 0 or export_index >= len(objects):
            raise RuntimeError("Fog MID source object index is outside Level JSON")
        dynamic = objects[export_index]
        if dynamic.get("Type") != "MaterialInstanceDynamic":
            raise RuntimeError("Fog material reference did not resolve to a MID")
        outer_name = str((dynamic.get("Outer") or {}).get("ObjectName", ""))
        if actor["actor_name"] not in outer_name:
            raise RuntimeError("Fog MID outer does not match its actor")

        properties = dynamic.get("Properties") or {}
        parent_package = package_without_object(
            (properties.get("Parent") or {}).get("ObjectPath")
        )
        scalars = parameter_map(properties.get("ScalarParameterValues"))
        vectors = parameter_map(properties.get("VectorParameterValues"))
        textures = parameter_map(properties.get("TextureParameterValues"))
        cached_textures = sorted(
            package_without_object(item.get("ObjectPath"))
            for item in properties.get("CachedReferencedTextures") or []
            if isinstance(item, dict) and item.get("ObjectPath")
        )
        effective_two_sided = bool(actor.get("properties", {}).get("Two Side", True))

        template = templates[actor_type]
        mesh_package = template["static_mesh_package"]
        parent_counts[parent_package] += 1
        mesh_counts[mesh_package] += 1
        scalar_name_counts.update(scalars.keys())
        vector_name_counts.update(vectors.keys())
        texture_name_counts.update(textures.keys())
        cached_texture_counts.update(cached_textures)
        two_sided_parent_pairs[(effective_two_sided, parent_package)] += 1
        component_properties = component.get("properties") or {}
        component_setting_counts[
            "receives_decals_true"
            if bool(component_properties.get("bReceivesDecals", template["receives_decals"]))
            else "receives_decals_false"
        ] += 1
        component_setting_counts[
            "translucency_sort_priority_{}".format(
                int(component_properties.get("TranslucencySortPriority", 0))
            )
        ] += 1

        results.append(
            {
                "source_level": actor["source_level"],
                "source_package": actor["source_package"],
                "source_actor_object_index": actor["source_object_index"],
                "source_actor_name": actor["actor_name"],
                "actor_type": actor_type,
                "transform": actor["transform"],
                "effective_two_sided": effective_two_sided,
                "static_mesh_package": mesh_package,
                "component_settings": {
                    "receives_decals": bool(
                        component_properties.get(
                            "bReceivesDecals", template["receives_decals"]
                        )
                    ),
                    "translucency_sort_priority": int(
                        component_properties.get("TranslucencySortPriority", 0)
                    ),
                    "collision_profile_name": "NoCollision",
                    "cast_shadow": template["cast_shadow"],
                    "cast_dynamic_shadow": template["cast_dynamic_shadow"],
                    "cast_static_shadow": template["cast_static_shadow"],
                    "use_as_occluder": template["use_as_occluder"],
                    "affect_dynamic_indirect_lighting": template[
                        "affect_dynamic_indirect_lighting"
                    ],
                    "affect_distance_field_lighting": template[
                        "affect_distance_field_lighting"
                    ],
                    "can_ever_affect_navigation": template[
                        "can_ever_affect_navigation"
                    ],
                },
                "dynamic_material": {
                    "source_level_json": str(json_path),
                    "source_export_index": export_index,
                    "source_reference_path": reference_path,
                    "source_name": dynamic.get("Name"),
                    "parent_package": parent_package,
                    "scalar_parameters": scalars,
                    "vector_parameters": vectors,
                    "texture_parameters": textures,
                    "cached_texture_packages": cached_textures,
                    "base_property_overrides": properties.get(
                        "BasePropertyOverrides"
                    ),
                    "static_parameters": properties.get("StaticParameters"),
                },
            }
        )

    if dict(sorted(parent_counts.items())) != EXPECTED_PARENT_COUNTS:
        raise RuntimeError("Fog MID parent inventory changed")
    if cached_texture_counts != collections.Counter(
        {EXPECTED_NOISE_PACKAGE: EXPECTED_COUNT}
    ):
        raise RuntimeError("Fog MID cached texture inventory changed")
    if any(record["dynamic_material"]["texture_parameters"] for record in results):
        raise RuntimeError("Unexpected explicit Fog MID texture parameter")
    if any(record["dynamic_material"]["base_property_overrides"] for record in results):
        raise RuntimeError("Unexpected Fog MID base-property override")
    if any(record["dynamic_material"]["static_parameters"] for record in results):
        raise RuntimeError("Unexpected Fog MID static parameter")
    expected_pairs = collections.Counter(
        {
            (
                True,
                "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_01",
            ): 6,
            (
                False,
                "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/World/MI/FMI_FogSheet_02",
            ): 45,
            (
                True,
                "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/BBQ_Material/World/FM_FogSheet_Local",
            ): 2,
        }
    )
    if two_sided_parent_pairs != expected_pairs:
        raise RuntimeError("Fog two-sided/parent mapping changed")
    if any(len(record["dynamic_material"]["scalar_parameters"]) != 12 for record in results if record["actor_type"] == "WBP_FogSheet_C"):
        raise RuntimeError("Standard Fog MID scalar inventory changed")
    if any(len(record["dynamic_material"]["scalar_parameters"]) != 11 for record in results if record["actor_type"] == "WBP_FogSheet_Local_C"):
        raise RuntimeError("Local Fog MID scalar inventory changed")
    if any(len(record["dynamic_material"]["vector_parameters"]) != 1 for record in results):
        raise RuntimeError("Fog MID vector inventory changed")

    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    summary = {
        "fog_actor_count": len(results),
        "actor_type_counts": dict(sorted(type_counts.items())),
        "source_level_counts": dict(sorted(level_counts.items())),
        "dynamic_material_parent_counts": dict(sorted(parent_counts.items())),
        "static_mesh_package_counts": dict(sorted(mesh_counts.items())),
        "scalar_parameter_name_counts": dict(sorted(scalar_name_counts.items())),
        "vector_parameter_name_counts": dict(sorted(vector_name_counts.items())),
        "texture_parameter_name_counts": dict(sorted(texture_name_counts.items())),
        "cached_texture_package_counts": dict(sorted(cached_texture_counts.items())),
        "component_setting_counts": dict(sorted(component_setting_counts.items())),
        "source_level_json_count": len(source_cache),
        "blueprint_template_json_count": len(templates),
    }
    payload = {
        "schema_version": 1,
        "level": "StormPass",
        "generated_at": generated_at,
        "status": "passed",
        "operation": "fmodel_level_mid_resolution_before_final_fog_pass",
        "deferred_metadata_path": str(DEFERRED_METADATA_PATH),
        "source_level_json_sha256": dict(sorted(source_hashes.items())),
        "blueprint_templates": templates,
        "summary": summary,
        "fog_actors": results,
        "content_boundary": (
            "Visual fog-sheet metadata only; no gameplay, collision, character, "
            "enemy, quest, cinema, audio, or source-code content."
        ),
    }
    write_json(OUTPUT_METADATA_PATH, payload)
    write_json(
        REPORT_PATH,
        {
            "status": "passed",
            "operation": payload["operation"],
            "output_metadata_path": str(OUTPUT_METADATA_PATH),
            "summary": summary,
            "source_level_json_sha256": payload["source_level_json_sha256"],
            "blueprint_templates": templates,
            "map_modified": False,
            "fog_restoration_state": "analyzed_not_yet_placed",
        },
    )
    print(
        "KHAZAN_STORMPASS_FOG_SOURCE_AUDIT "
        + json.dumps(summary, ensure_ascii=False, sort_keys=True)
    )
    return payload


if __name__ == "__main__":
    main()
