"""Validate and compact the exact StormPass Landscape material sources.

The CUE4Parse extractor writes decoded full-landscape layer maps and every
texture overridden by WLM_Stormpass/WLM_Stormpass_Phase2.  This audit turns
that extraction into a small canonical reconstruction plan and explicitly
records the two special Phase2 branches (Layer8 and Puddle).
"""

from __future__ import annotations

import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
EXTRACT_MANIFEST = (
    PROJECT_ROOT
    / "Saved"
    / "Extracted"
    / "StormPass"
    / "LandscapeWeightmaps"
    / "StormPass_LandscapeWeightmaps.json"
)
METADATA_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "StormPass"
    / "Metadata"
    / "StormPass_LandscapeMaterialSources.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "StormPass_Landscape_MaterialSourceAudit.json"
)


EXPECTED_LANDSCAPES = {
    "StormPass_Landscape": {
        "dimensions": (1387, 1261),
        "components": 440,
        "material": "WLM_Stormpass",
        "mappings": {
            "Layer1_LayerInfo": "Layer1",
            "Layer2_LayerInfo": "Layer2",
            "Layer4_LayerInfo": "Layer4",
            "WLI_StormPass_Field_DeepSnow": "DeepSnow",
            "WLI_StormPass_Field_DeepSnow2": "DeepSnow2",
        },
    },
    "StormPass_Boss_Phase_2": {
        "dimensions": (253, 253),
        "components": 16,
        "material": "WLM_Stormpass_Phase2",
        "mappings": {
            "WLI_StormPass_Layer8": "Layer8",
            "WLI_StormPass_Phase2_Layer1": "Layer1",
            "WLI_StormPass_Phase2_Layer2": "Layer2",
            "WLI_StormPass_Phase2_Layer3": "Layer3",
            "WLI_StormPass_Phase2_Layer4": "Layer4",
            "WLI_StormPass_Phase2_Layer5": "Layer5",
            "WLI_StormPass_Phase2_Layer6": "Layer6",
            "WLI_StormPass_Phase2_Layer7": "Layer7",
            "WLI_StormPass_Phase2_Puddle": "Puddle",
        },
    },
}

ACTIVE_GROUPS = {
    "WLM_Stormpass": {
        "Layer1": "BaseGround",
        "Layer2": "Layer2",
        "Layer4": "Layer4",
        "DeepSnow": "DeepSnow",
        "DeepSnow2": "DeepSnow2",
    },
    "WLM_Stormpass_Phase2": {
        "Layer1": "BaseGround",
        "Layer2": "Layer2",
        "Layer3": "Layer3",
        "Layer4": "Layer4",
        "Layer5": "Layer5",
        "Layer6": "Layer6",
        "Layer7": "Layer7",
    },
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def value(row, *names):
    for name in names:
        if name in row:
            return row[name]
    return None


def parameter_maps(material: dict):
    scalars = {
        row["name"]: row["value"] for row in material.get("scalar_parameters", [])
    }
    textures = {
        value(row, "ParameterName", "parameter_name"): {
            "object_path": value(row, "ObjectPath", "object_path"),
            "object_name": value(row, "ObjectName", "object_name"),
        }
        for row in material.get("texture_parameters", [])
    }
    vectors = {
        row["name"]: row["value"] for row in material.get("vector_parameters", [])
    }
    return scalars, vectors, textures


def texture_parameters_for_group(group: str):
    if group == "BaseGround":
        return {
            "diffuse": "BaseGroundTex_D",
            "normal": "BaseGroundTex_N",
            "surface": "BaseGroundTex_S",
        }
    return {
        "diffuse": "Tex_D-" + group,
        "normal": "Tex_N-" + group,
        "surface": "Tex_S-" + group,
    }


def build_surface_plan(material: dict, inherited_material: dict):
    name = material["material_name"]
    inherited_scalars, inherited_vectors, _inherited_textures = parameter_maps(
        inherited_material
    )
    local_scalars, local_vectors, textures = parameter_maps(material)
    scalars = {**inherited_scalars, **local_scalars}
    vectors = {**inherited_vectors, **local_vectors}
    layers = []
    for layer_name, group in ACTIVE_GROUPS[name].items():
        parameters = texture_parameters_for_group(group)
        bindings = {}
        for semantic, parameter_name in parameters.items():
            if parameter_name not in textures:
                raise RuntimeError(f"{name} is missing {parameter_name}")
            bindings[semantic] = {
                "parameter": parameter_name,
                **textures[parameter_name],
            }
        tiling_name = "Tiling-" + layer_name
        if tiling_name not in scalars:
            raise RuntimeError(f"{name} is missing {tiling_name}")
        layers.append(
            {
                "layer_name": layer_name,
                "source_texture_group": group,
                "tiling_meters": float(scalars[tiling_name]),
                "textures": bindings,
            }
        )
    result = {"material_name": name, "layers": layers}
    if name == "WLM_Stormpass_Phase2":
        cover = texture_parameters_for_group("DeepSnow")
        result["covering"] = {
            "enabled_by_inherited_parent": True,
            "snow_height": float(scalars["SnowHeight"]),
            "height_intensity": float(scalars["HeightIntensity-DeepSnow"]),
            "tiling_meters": float(scalars["Tiling-DeepSnow"]),
            "textures": {
                semantic: {"parameter": parameter, **textures[parameter]}
                for semantic, parameter in cover.items()
            },
        }
        result["layer8_policy"] = {
            "source_override_present": False,
            "restoration_fallback": "Layer1 surface",
            "reason": (
                "Layer8 is inherited from Base_Terrain5, has no Phase2 texture "
                "override, and its decoded source weight is at most 3/255 on only "
                "26 of 64,009 pixels."
            ),
        }
        result["puddle"] = {
            "weight_layer": "Puddle",
            "wet_surface_darkness": float(scalars["WetSurfaceDarkness"]),
            "metallic": float(scalars["Puddle1Metalic"]),
            "roughness": float(scalars["Puddle1Roughness"]),
            "color": {
                channel.lower(): float(vectors["Puddle1Color"][channel])
                for channel in ("R", "G", "B", "A")
            },
        }
    return result


def main():
    manifest = load_json(EXTRACT_MANIFEST)
    if manifest.get("status") != "passed":
        raise RuntimeError("Landscape extraction manifest is not passed")
    if int(manifest.get("surface_texture_count", -1)) != 37:
        raise RuntimeError("Expected exactly 37 decoded WLM texture overrides")

    materials = {
        material["material_name"]: material
        for material in manifest.get("source_materials", [])
    }
    for required in ("WLM_Stormpass", "WLM_Stormpass_Phase2", "WLM_Base_Terrain5_Inst"):
        if required not in materials:
            raise RuntimeError("Missing source material summary: " + required)

    landscapes = []
    for source in manifest.get("landscapes", []):
        name = source["output_name"]
        expected = EXPECTED_LANDSCAPES.get(name)
        if expected is None:
            raise RuntimeError("Unexpected Landscape extraction: " + name)
        if int(source["component_count"]) != expected["components"]:
            raise RuntimeError("Landscape component count changed: " + name)
        layers = {row["layer_name"]: row for row in source.get("layers", [])}
        normal = layers.pop("NormalMap_DX", None)
        if normal is None:
            raise RuntimeError("Landscape normal map missing: " + name)
        width, height = expected["dimensions"]
        for row in [normal, *layers.values()]:
            if (int(row["width"]), int(row["height"])) != (width, height):
                raise RuntimeError("Landscape texture dimensions changed: " + name)
            if not Path(row["path"]).is_file():
                raise RuntimeError("Landscape texture file missing: " + row["path"])
        mappings = {
            row["exported_layer_name"]: row["material_layer_names"][0]
            for row in source.get("layer_info_mappings", [])
        }
        if mappings != expected["mappings"] or set(layers) != set(mappings):
            raise RuntimeError("Landscape LayerInfo mapping changed: " + name)
        landscapes.append(
            {
                "source_level": name,
                "component_count": expected["components"],
                "dimensions": {"width": width, "height": height},
                "material_name": expected["material"],
                "normal_map": normal,
                "weight_layers": [
                    {
                        "exported_layer_name": exported,
                        "material_layer_name": material_layer,
                        **layers[exported],
                    }
                    for exported, material_layer in sorted(mappings.items())
                ],
            }
        )

    surface_textures = []
    for texture in manifest.get("surface_textures", []):
        path = Path(texture["path"])
        if not path.is_file() or path.stat().st_size != int(texture["bytes"]):
            raise RuntimeError("Decoded surface texture is missing or changed: " + str(path))
        surface_textures.append(texture)

    plans = [
        build_surface_plan(
            materials["WLM_Stormpass"], materials["WLM_Base_Terrain5_Inst"]
        ),
        build_surface_plan(
            materials["WLM_Stormpass_Phase2"],
            materials["WLM_Base_Terrain5_Inst"],
        ),
    ]
    payload = {
        "schema_version": 1,
        "status": "passed",
        "extraction_backend": manifest["extraction_backend"],
        "source_material_parent": materials["WLM_Base_Terrain5_Inst"],
        "landscapes": landscapes,
        "surface_plans": plans,
        "decoded_surface_texture_count": len(surface_textures),
        "decoded_surface_textures": surface_textures,
        "packed_surface_channel_policy": {
            "ambient_occlusion": "R",
            "roughness": "G",
            "metallic": "B",
        },
        "fog_policy": "deferred_until_final_pass",
    }
    write_json(METADATA_PATH, payload)
    report = {
        "status": "passed",
        "canonical_metadata": str(METADATA_PATH),
        "landscape_count": len(landscapes),
        "component_count": sum(row["component_count"] for row in landscapes),
        "weight_layer_count": sum(len(row["weight_layers"]) for row in landscapes),
        "landscape_normal_map_count": len(landscapes),
        "decoded_surface_texture_count": len(surface_textures),
        "active_surface_layer_count": sum(len(row["layers"]) for row in plans),
        "fog_actor_count": 0,
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
