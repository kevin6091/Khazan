"""Rebuild Khazan character materials from the exported JSON and PNG files.

Run with UnrealEditor-Cmd and the PythonScriptPlugin.  The script is intentionally
idempotent: generated parent assets are rebuilt, imported textures are reused, and
the FBX-created material instances already referenced by the skeletal meshes are
updated in place.
"""

import json
import os
import re
import traceback

import unreal


SOURCE_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
KHAZAN_ROOT = "/Game/_Art/Kazan"
GENERATED_ROOT = KHAZAN_ROOT + "/Material/Generated"
MASTER_ROOT = GENERATED_ROOT + "/Masters"
BASE_ROOT = GENERATED_ROOT + "/Base"
INSTANCE_ROOT = GENERATED_ROOT + "/Instances"
TEXTURE_ROOT = KHAZAN_ROOT + "/Texture/Generated"

CHARACTER_MASTER_NAME = "M_AKCartoonCharacter"
EYE_SHADOW_MASTER_NAME = "M_Khazan_EyeShadow"
EYE_SHADOW_NAME = "EyeShadow"

KNOWN_PARENTS = {
    "BASE_AllMaster_AK": CHARACTER_MASTER_NAME,
    "BASE_Default_AK": "BASE_AllMaster_AK",
    "BASE_Skin_AK": "BASE_AllMaster_AK",
    "Base_Eyes_AK": "BASE_AllMaster_AK",
    "BASE_Face_AK": "BASE_AllMaster_AK",
    "BASE_Hair_AK": "BASE_AllMaster_AK",
    "BASE_Metal_AK": "BASE_AllMaster_AK",
    "Base_Ghost_AK": "BASE_AllMaster_AK",
    "BASE_PCDefault_AK": "BASE_Default_AK",
    "BASE_PCSkin_AK": "BASE_Skin_AK",
    "Base_PCEyes_AK": "Base_Eyes_AK",
    "BASE_PCFace_AK": "BASE_Face_AK",
    "BASE_PCHair_AK": "BASE_Hair_AK",
    "BASE_PCMetal_AK": "BASE_Metal_AK",
}

CATEGORY_OVERRIDES = {
    "BASE_AllMaster_AK": {
        "scalars": {
            "UseEyeTexture": 0.0,
            "UseGhostLook": 0.0,
            "UseNormalMap": 1.0,
            "UseDiffuseAlpha": 1.0,
            "UseSpecularAsMetallic": 0.0,
            "BaseColorBrightness": 1.15,
            "RoughnessScale": 1.0,
            "RoughnessBias": 0.0,
            "MetallicStrength": 1.0,
            "SpecularStrength": 0.5,
            "EyeEmissiveStrength": 0.0,
            "GhostFresnelStrength": 0.0,
        },
        "vectors": {
            "BaseColorTint": (1.0, 1.0, 1.0, 1.0),
            "FlatNormal": (0.0, 0.0, 1.0, 1.0),
            "GhostColor": (0.13, 0.22, 0.30, 1.0),
        },
    },
    "BASE_Default_AK": {
        "scalars": {
            "BaseColorBrightness": 1.2,
            "RoughnessScale": 1.0,
            "MetallicStrength": 1.0,
            "SpecularStrength": 0.5,
        }
    },
    "BASE_Skin_AK": {
        "scalars": {
            "BaseColorBrightness": 1.0,
            "RoughnessScale": 0.78,
            "MetallicStrength": 0.0,
            "SpecularStrength": 0.38,
        }
    },
    "BASE_Face_AK": {
        "scalars": {
            "BaseColorBrightness": 1.0,
            "RoughnessScale": 0.76,
            "MetallicStrength": 0.0,
            "SpecularStrength": 0.4,
        }
    },
    "BASE_Hair_AK": {
        "scalars": {
            "BaseColorBrightness": 1.1,
            "RoughnessScale": 0.55,
            "MetallicStrength": 0.0,
            "SpecularStrength": 0.7,
            "UseDiffuseAlpha": 1.0,
        }
    },
    "Base_Eyes_AK": {
        "scalars": {
            "UseEyeTexture": 1.0,
            "UseNormalMap": 0.0,
            "UseDiffuseAlpha": 0.0,
            "BaseColorBrightness": 1.0,
            "RoughnessScale": 0.18,
            "MetallicStrength": 0.0,
            "SpecularStrength": 0.85,
            "EyeEmissiveStrength": 0.035,
        }
    },
    "BASE_Metal_AK": {
        "scalars": {
            "BaseColorBrightness": 1.2,
            "RoughnessScale": 0.85,
            "MetallicStrength": 1.0,
            "SpecularStrength": 0.55,
            "UseSpecularAsMetallic": 1.0,
        }
    },
    "Base_Ghost_AK": {
        "scalars": {
            "UseGhostLook": 1.0,
            "UseDiffuseAlpha": 0.0,
            "UseNormalMap": 1.0,
            "RoughnessScale": 0.4,
            "MetallicStrength": 0.0,
            "SpecularStrength": 0.65,
            "GhostFresnelStrength": 0.85,
        },
        "vectors": {
            "GhostColor": (0.10, 0.24, 0.34, 1.0),
        },
    },
}

FUNCTIONAL_SCALARS = {
    "UseEyeTexture": 0.0,
    "UseGhostLook": 0.0,
    "UseNormalMap": 1.0,
    "UseDiffuseAlpha": 1.0,
    "UseSpecularAsMetallic": 0.0,
    "BaseColorBrightness": 1.0,
    "RoughnessScale": 1.0,
    "RoughnessBias": 0.0,
    "MetallicStrength": 1.0,
    "SpecularStrength": 0.5,
    "EyeEmissiveStrength": 0.0,
    "GhostFresnelStrength": 0.0,
    "SolidOpacity": 1.0,
}

FUNCTIONAL_VECTORS = {
    "BaseColorTint": (1.0, 1.0, 1.0, 1.0),
    "FlatNormal": (0.0, 0.0, 1.0, 1.0),
    "GhostColor": (0.13, 0.22, 0.30, 1.0),
}

FUNCTIONAL_TEXTURES = {
    "Tex_D",
    "Tex_S",
    "Tex_N",
    "Tex_I",
    "Tex_E",
    "Tex_R",
    "Tex_NTP",
    "Tex_F1",
    "Tex_F2",
    "Tex_M1",
    "Tex_M2",
    "CurveTex",
    "DissolveTex",
}

STATS = {
    "meshes": 0,
    "slots": 0,
    "target_materials": 0,
    "json_records": 0,
    "textures_required": 0,
    "textures_imported": 0,
    "textures_reused": 0,
    "textures_missing_optional": 0,
    "instances_updated": 0,
    "mesh_slots_reassigned": 0,
}


def log(message):
    unreal.log("KHAZAN_BUILD: " + str(message))


def warn(message):
    unreal.log_warning("KHAZAN_BUILD: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_BUILD: " + str(message))


def valid_parameter_name(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value or len(value) > 128:
        return False
    return all(32 <= ord(character) < 127 for character in value)


def clean_object_path(value):
    if not isinstance(value, str):
        return ""
    return value.replace("\r", "").replace("\n", "").strip()


def object_reference_name(value):
    if isinstance(value, dict):
        value = value.get("ObjectName", "")
    if not isinstance(value, str):
        return ""
    match = re.search(r"'([^']+)'", value)
    return match.group(1) if match else value.strip()


def texture_reference(parameter, texture_name, object_path=""):
    return {
        "parameter": parameter,
        "name": texture_name,
        "object_path": clean_object_path(object_path),
    }


def empty_record(name, path=""):
    return {
        "name": name,
        "path": path,
        "parent": "",
        "textures": {},
        "scalars": {},
        "vectors": {},
        "switches": {},
        "blend_mode": "",
        "two_sided": None,
    }


def parse_full_record(name, path, entry):
    record = empty_record(name, path)
    properties = entry.get("Properties", {}) if isinstance(entry, dict) else {}
    record["parent"] = object_reference_name(properties.get("Parent"))

    for value in properties.get("TextureParameterValues", []) or []:
        if not isinstance(value, dict):
            continue
        parameter = (value.get("ParameterInfo") or {}).get("Name", "")
        reference = value.get("ParameterValue")
        if not valid_parameter_name(parameter) or not isinstance(reference, dict):
            continue
        texture_name = object_reference_name(reference)
        if texture_name:
            record["textures"][parameter] = texture_reference(
                parameter, texture_name, reference.get("ObjectPath", "")
            )

    for value in properties.get("ScalarParameterValues", []) or []:
        if not isinstance(value, dict):
            continue
        parameter = (value.get("ParameterInfo") or {}).get("Name", "")
        scalar = value.get("ParameterValue")
        if valid_parameter_name(parameter) and isinstance(scalar, (int, float)):
            record["scalars"][parameter] = float(scalar)

    for value in properties.get("VectorParameterValues", []) or []:
        if not isinstance(value, dict):
            continue
        parameter = (value.get("ParameterInfo") or {}).get("Name", "")
        vector = value.get("ParameterValue")
        if valid_parameter_name(parameter) and isinstance(vector, dict):
            record["vectors"][parameter] = (
                float(vector.get("R", 0.0)),
                float(vector.get("G", 0.0)),
                float(vector.get("B", 0.0)),
                float(vector.get("A", 1.0)),
            )

    static_parameters = properties.get("StaticParameters", {}) or {}
    for value in static_parameters.get("StaticSwitchParameters", []) or []:
        if not isinstance(value, dict):
            continue
        parameter = (value.get("ParameterInfo") or {}).get("Name", "")
        if valid_parameter_name(parameter) and isinstance(value.get("Value"), bool):
            record["switches"][parameter] = value["Value"]

    overrides = properties.get("BasePropertyOverrides", {}) or {}
    record["blend_mode"] = overrides.get("BlendMode", "")
    if "TwoSided" in overrides:
        record["two_sided"] = bool(overrides["TwoSided"])
    return record


def simple_texture_name(value):
    value = clean_object_path(value).replace("\\", "/")
    if not value:
        return ""
    leaf = value.rsplit("/", 1)[-1]
    return leaf.split(".", 1)[0]


def parse_simple_record(name, path, document):
    record = empty_record(name, path)
    for parameter, value in (document.get("Textures", {}) or {}).items():
        if not valid_parameter_name(parameter):
            continue
        if not (parameter.startswith("Tex_") or parameter in FUNCTIONAL_TEXTURES):
            continue
        texture_name = simple_texture_name(value)
        if texture_name:
            record["textures"][parameter] = texture_reference(parameter, texture_name, value)

    parameters = document.get("Parameters", {}) or {}
    for parameter, value in (parameters.get("Scalars", {}) or {}).items():
        if valid_parameter_name(parameter) and isinstance(value, (int, float)):
            record["scalars"][parameter] = float(value)
    for parameter, value in (parameters.get("Colors", {}) or {}).items():
        if valid_parameter_name(parameter) and isinstance(value, dict):
            record["vectors"][parameter] = (
                float(value.get("R", 0.0)),
                float(value.get("G", 0.0)),
                float(value.get("B", 0.0)),
                float(value.get("A", 1.0)),
            )
    for parameter, value in (parameters.get("Switches", {}) or {}).items():
        if valid_parameter_name(parameter) and isinstance(value, bool):
            record["switches"][parameter] = value

    overrides = ((parameters.get("Properties", {}) or {}).get("BasePropertyOverrides", {}) or {})
    record["blend_mode"] = overrides.get("BlendMode", "")
    if "TwoSided" in overrides:
        record["two_sided"] = bool(overrides["TwoSided"])
    return record


def array_body(raw, property_name):
    match = re.search(
        r'"' + re.escape(property_name) + r'"\s*:\s*\[(.*?)\]\s*(?:,|\})',
        raw,
        re.DOTALL,
    )
    return match.group(1) if match else ""


def object_body(raw, property_name, next_property):
    match = re.search(
        r'"' + re.escape(property_name) + r'"\s*:\s*\{(.*?)\}\s*,\s*"'
        + re.escape(next_property)
        + r'"',
        raw,
        re.DOTALL,
    )
    return match.group(1) if match else ""


def parse_fallback_record(name, path, raw):
    record = empty_record(name, path)
    parent_match = re.search(
        r'"Parent"\s*:\s*\{.*?"ObjectName"\s*:\s*"(?:MaterialInstanceConstant|Material)\'([^\']+)\'"',
        raw,
        re.DOTALL,
    )
    if parent_match:
        record["parent"] = parent_match.group(1)

    texture_body = array_body(raw, "TextureParameterValues")
    for match in re.finditer(
        r'"Name"\s*:\s*"([^"\r\n]{1,128})".*?'
        r'"ParameterValue"\s*:\s*\{.*?'
        r'"ObjectName"\s*:\s*"Texture2D\'([^\']+)\'".*?'
        r'"ObjectPath"\s*:\s*"(.*?)"',
        texture_body,
        re.DOTALL,
    ):
        parameter, texture_name, object_path_value = match.groups()
        if valid_parameter_name(parameter):
            record["textures"][parameter] = texture_reference(
                parameter, texture_name, object_path_value
            )

    if not record["textures"] and '"Textures"' in raw:
        body = object_body(raw, "Textures", "Parameters")
        for match in re.finditer(r'"([^"\r\n]+)"\s*:\s*"([^"\r\n]+)"', body):
            parameter, value = match.groups()
            if not valid_parameter_name(parameter):
                continue
            if not (parameter.startswith("Tex_") or parameter in FUNCTIONAL_TEXTURES):
                continue
            texture_name = simple_texture_name(value)
            if texture_name:
                record["textures"][parameter] = texture_reference(parameter, texture_name, value)

    scalar_body = array_body(raw, "ScalarParameterValues")
    for match in re.finditer(
        r'"Name"\s*:\s*"([^"\r\n]{1,128})".*?'
        r'"ParameterValue"\s*:\s*(-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)',
        scalar_body,
        re.DOTALL,
    ):
        parameter, value = match.groups()
        if valid_parameter_name(parameter):
            record["scalars"][parameter] = float(value)

    vector_body = array_body(raw, "VectorParameterValues")
    vector_pattern = (
        r'"Name"\s*:\s*"([^"\r\n]{1,128})".*?'
        r'"ParameterValue"\s*:\s*\{.*?'
        r'"R"\s*:\s*(-?[\d.]+).*?'
        r'"G"\s*:\s*(-?[\d.]+).*?'
        r'"B"\s*:\s*(-?[\d.]+).*?'
        r'"A"\s*:\s*(-?[\d.]+)'
    )
    for match in re.finditer(vector_pattern, vector_body, re.DOTALL):
        parameter, red, green, blue, alpha = match.groups()
        if valid_parameter_name(parameter):
            record["vectors"][parameter] = tuple(
                float(value) for value in (red, green, blue, alpha)
            )

    switch_body = array_body(raw, "StaticSwitchParameters")
    for match in re.finditer(
        r'"Value"\s*:\s*(true|false).*?"Name"\s*:\s*"([^"\r\n]{1,128})"',
        switch_body,
        re.DOTALL | re.IGNORECASE,
    ):
        value, parameter = match.groups()
        if valid_parameter_name(parameter):
            record["switches"][parameter] = value.lower() == "true"

    if '"Textures"' in raw:
        scalar_object = object_body(raw, "Scalars", "Switches")
        for match in re.finditer(
            r'"([^"\r\n]+)"\s*:\s*(-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)',
            scalar_object,
        ):
            parameter, value = match.groups()
            if valid_parameter_name(parameter):
                record["scalars"][parameter] = float(value)

        color_object = object_body(raw, "Colors", "Scalars")
        for match in re.finditer(
            r'"([^"\r\n]+)"\s*:\s*\{.*?'
            r'"R"\s*:\s*(-?[\d.]+).*?'
            r'"G"\s*:\s*(-?[\d.]+).*?'
            r'"B"\s*:\s*(-?[\d.]+).*?'
            r'"A"\s*:\s*(-?[\d.]+)',
            color_object,
            re.DOTALL,
        ):
            parameter, red, green, blue, alpha = match.groups()
            if valid_parameter_name(parameter):
                record["vectors"][parameter] = tuple(
                    float(value) for value in (red, green, blue, alpha)
                )

        switch_object = object_body(raw, "Switches", "Properties")
        for match in re.finditer(
            r'"([^"\r\n]+)"\s*:\s*(true|false)', switch_object, re.IGNORECASE
        ):
            parameter, value = match.groups()
            if valid_parameter_name(parameter):
                record["switches"][parameter] = value.lower() == "true"

    blend_match = re.search(r'"BlendMode"\s*:\s*"([^"\r\n]+)"', raw)
    if blend_match:
        record["blend_mode"] = blend_match.group(1)
    two_sided_match = re.search(r'"TwoSided"\s*:\s*(true|false)', raw, re.IGNORECASE)
    if two_sided_match:
        record["two_sided"] = two_sided_match.group(1).lower() == "true"
    return record


def parse_json_record(name, path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        raw = handle.read()
    try:
        document = json.loads(raw)
        if isinstance(document, list) and document:
            return parse_full_record(name, path, document[0])
        if isinstance(document, dict):
            return parse_simple_record(name, path, document)
    except (ValueError, TypeError):
        pass
    return parse_fallback_record(name, path, raw)


def build_source_indices():
    json_index = {}
    png_index = {}
    for directory, _, files in os.walk(SOURCE_ROOT):
        for filename in files:
            stem, extension = os.path.splitext(filename)
            path = os.path.join(directory, filename)
            extension = extension.lower()
            if extension == ".json":
                size = os.path.getsize(path)
                previous = json_index.get(stem)
                if not previous or size > previous[0]:
                    json_index[stem] = (size, path)
            elif extension == ".png":
                png_index.setdefault(stem, []).append(path)
    return {name: value[1] for name, value in json_index.items()}, png_index


def collect_project_assets():
    mesh_paths = []
    for root in (
        KHAZAN_ROOT + "/Character/Meshs",
        KHAZAN_ROOT + "/Item",
    ):
        mesh_paths.extend(unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False))

    material_paths = []
    for root in (
        KHAZAN_ROOT + "/Character/Meshs",
        KHAZAN_ROOT + "/Item",
        KHAZAN_ROOT + "/Material",
    ):
        material_paths.extend(unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False))

    meshes = []
    for path in sorted(set(mesh_paths)):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset and isinstance(asset, unreal.SkeletalMesh):
            meshes.append(asset)

    instances_by_name = {}
    for path in sorted(set(material_paths)):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset and isinstance(asset, unreal.MaterialInstanceConstant):
            instances_by_name.setdefault(asset.get_name(), []).append(asset)
    return meshes, instances_by_name


def mesh_material_targets(meshes):
    targets = set()
    for mesh in meshes:
        for skeletal_material in mesh.get_editor_property("materials"):
            slot_name = str(skeletal_material.get_editor_property("material_slot_name"))
            if slot_name and slot_name != "None":
                targets.add(slot_name)
                STATS["slots"] += 1
    STATS["meshes"] = len(meshes)
    STATS["target_materials"] = len(targets)
    return targets


def infer_target_parent(name):
    if name == EYE_SHADOW_NAME:
        return ""
    if name == "CM_I_DualAxeSword_GhostOriginal001_R":
        return "Base_Ghost_AK"
    if name.startswith("CM_I_"):
        return "BASE_PCMetal_AK"
    return "BASE_PCDefault_AK"


def collect_records(targets, json_index):
    records = {}

    def load_record(name, is_target=False):
        if not name or name == CHARACTER_MASTER_NAME:
            return None
        if name in records:
            return records[name]
        path = json_index.get(name, "")
        if path:
            record = parse_json_record(name, path)
        else:
            record = empty_record(name)
        if not record["parent"]:
            if name in KNOWN_PARENTS:
                record["parent"] = KNOWN_PARENTS[name]
            elif is_target:
                record["parent"] = infer_target_parent(name)
        records[name] = record
        if record["parent"] and record["parent"] != CHARACTER_MASTER_NAME:
            load_record(record["parent"], False)
        return record

    for target in sorted(targets):
        load_record(target, True)

    STATS["json_records"] = sum(1 for value in records.values() if value["path"])
    return records


def texture_file_from_object_path(object_path_value):
    value = clean_object_path(object_path_value).replace("\\", "/")
    if not value:
        return ""
    if "." in value.rsplit("/", 1)[-1]:
        value = value.rsplit(".", 1)[0]
    candidate = os.path.join(SOURCE_ROOT, *value.split("/")) + ".png"
    return candidate if os.path.isfile(candidate) else ""


def texture_candidate_score(path):
    normalized = path.replace("/", "\\").lower()
    score = 0
    if "\\exports\\" in normalized:
        score += 10
    if "\\backups\\" in normalized:
        score += 20
    if "\\bbq\\content\\_kazan_\\art\\character\\cha_material\\texture\\" not in normalized:
        score += 2
    return score, len(path), path.lower()


def resolve_texture_sources(records, targets, png_index):
    sources = {}
    references_by_texture = {}
    critical_missing = []
    optional_missing = []

    for record_name, record in records.items():
        for reference in record["textures"].values():
            texture_name = reference["name"]
            references_by_texture.setdefault(texture_name, []).append((record_name, reference["parameter"]))
            if texture_name in sources:
                continue
            candidate = texture_file_from_object_path(reference["object_path"])
            if not candidate:
                candidates = sorted(png_index.get(texture_name, []), key=texture_candidate_score)
                candidate = candidates[0] if candidates else ""
            if candidate:
                sources[texture_name] = candidate

    for texture_name, references in sorted(references_by_texture.items()):
        if texture_name in sources:
            continue
        target_reference = any(record_name in targets for record_name, _ in references)
        message = "{} referenced by {}".format(texture_name, references)
        if target_reference:
            critical_missing.append(message)
        else:
            optional_missing.append(message)

    if critical_missing:
        raise RuntimeError("Required target texture files are missing: " + "; ".join(critical_missing))
    for message in optional_missing:
        warn("Optional inherited texture not exported; using graph fallback: " + message)
    STATS["textures_missing_optional"] = len(optional_missing)
    STATS["textures_required"] = len(sources)
    return sources, references_by_texture


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        if not unreal.EditorAssetLibrary.make_directory(path):
            raise RuntimeError("Could not create Unreal content directory " + path)


def is_normal_texture(texture_name, references):
    if texture_name.lower().endswith(("_n", "_normal")):
        return True
    return any(parameter == "Tex_N" for _, parameter in references)


def is_color_texture(references):
    return any(parameter == "Tex_D" for _, parameter in references)


def import_textures(texture_sources, references_by_texture):
    ensure_directory(TEXTURE_ROOT)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    tasks = []
    task_names = {}
    textures = {}

    for texture_name, source_path in sorted(texture_sources.items()):
        asset_path = TEXTURE_ROOT + "/" + texture_name
        if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            if texture and isinstance(texture, unreal.Texture2D):
                textures[texture_name] = texture
                STATS["textures_reused"] += 1
                continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source_path)
        task.set_editor_property("destination_path", TEXTURE_ROOT)
        task.set_editor_property("destination_name", texture_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        tasks.append(task)
        task_names[id(task)] = texture_name

    if tasks:
        asset_tools.import_asset_tasks(tasks)
        for task in tasks:
            texture_name = task_names[id(task)]
            texture = unreal.EditorAssetLibrary.load_asset(TEXTURE_ROOT + "/" + texture_name)
            if not texture or not isinstance(texture, unreal.Texture2D):
                raise RuntimeError("Texture import failed for " + texture_name)
            textures[texture_name] = texture
            STATS["textures_imported"] += 1

    for texture_name, texture in textures.items():
        references = references_by_texture.get(texture_name, [])
        if is_normal_texture(texture_name, references):
            texture.set_editor_property("srgb", False)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
            )
        elif is_color_texture(references):
            texture.set_editor_property("srgb", True)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT
            )
        else:
            texture.set_editor_property("srgb", False)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
            )
        texture.set_editor_property("defer_compression", False)
        unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)

    return textures


def create_or_load_asset(asset_name, package_path, asset_class, factory):
    asset_path = package_path + "/" + asset_name
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset or not isinstance(asset, asset_class):
            raise RuntimeError("Existing asset has unexpected type: " + asset_path)
        return asset
    ensure_directory(package_path)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name, package_path, asset_class, factory
    )
    if not asset:
        raise RuntimeError("Could not create asset " + asset_path)
    return asset


def set_property_if_available(asset, property_name, value):
    try:
        asset.set_editor_property(property_name, value)
        return True
    except Exception as exception:
        warn("Could not set {} on {}: {}".format(property_name, asset.get_name(), exception))
        return False


def create_expression(material, expression_class, x, y):
    expression = unreal.MaterialEditingLibrary.create_material_expression(
        material, expression_class, x, y
    )
    if not expression:
        raise RuntimeError("Failed to create " + expression_class.__name__)
    return expression


def connect(from_expression, output_name, to_expression, input_name):
    if not unreal.MaterialEditingLibrary.connect_material_expressions(
        from_expression, output_name, to_expression, input_name
    ):
        raise RuntimeError(
            "Failed material connection {}.{} -> {}.{}".format(
                from_expression.get_name(), output_name, to_expression.get_name(), input_name
            )
        )


def connect_property(expression, output_name, material_property):
    if not unreal.MaterialEditingLibrary.connect_material_property(
        expression, output_name, material_property
    ):
        raise RuntimeError(
            "Failed material property connection {}.{} -> {}".format(
                expression.get_name(), output_name, material_property
            )
        )


def create_scalar_parameter(material, name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    expression.set_editor_property("parameter_name", name)
    expression.set_editor_property("default_value", float(default_value))
    return expression


def create_vector_parameter(material, name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    expression.set_editor_property("parameter_name", name)
    expression.set_editor_property("default_value", unreal.LinearColor(*default_value))
    return expression


def create_texture_parameter(material, name, default_texture, sampler_type, x, y):
    expression = create_expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, x, y
    )
    expression.set_editor_property("parameter_name", name)
    expression.set_editor_property("texture", default_texture)
    expression.set_editor_property("sampler_type", sampler_type)
    return expression


def create_static_switch_parameter(material, name, default_value, x, y):
    expression = create_expression(
        material, unreal.MaterialExpressionStaticSwitchParameter, x, y
    )
    expression.set_editor_property("parameter_name", name)
    expression.set_editor_property("default_value", bool(default_value))
    return expression


def parameter_unions(records, targets):
    texture_names = set(FUNCTIONAL_TEXTURES)
    scalar_names = set(FUNCTIONAL_SCALARS)
    vector_names = set(FUNCTIONAL_VECTORS)
    switch_names = set()
    for record_name, record in records.items():
        if record_name == EYE_SHADOW_NAME:
            continue
        texture_names.update(name for name in record["textures"] if valid_parameter_name(name))
        scalar_names.update(name for name in record["scalars"] if valid_parameter_name(name))
        vector_names.update(name for name in record["vectors"] if valid_parameter_name(name))
        switch_names.update(name for name in record["switches"] if valid_parameter_name(name))
    return texture_names, scalar_names, vector_names, switch_names


def build_character_master(records, targets, textures):
    material = create_or_load_asset(
        CHARACTER_MASTER_NAME, MASTER_ROOT, unreal.Material, unreal.MaterialFactoryNew()
    )
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    set_property_if_available(material, "blend_mode", unreal.BlendMode.BLEND_MASKED)
    set_property_if_available(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    set_property_if_available(material, "two_sided", True)
    set_property_if_available(material, "dithered_lod_transition", True)
    set_property_if_available(material, "opacity_mask_clip_value", 0.3333)
    set_property_if_available(material, "tangent_space_normal", True)

    white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture")
    black = textures.get("BASE_Black") or unreal.load_asset("/Engine/EngineResources/Black.Black")
    normal = unreal.load_asset("/Engine/EngineMaterials/DefaultNormal.DefaultNormal")
    if not white or not black or not normal:
        raise RuntimeError("Engine fallback textures could not be loaded")

    texture_names, scalar_names, vector_names, switch_names = parameter_unions(
        records, targets
    )
    texture_nodes = {}
    for index, name in enumerate(sorted(texture_names)):
        if name == "Tex_N":
            default_texture = normal
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
        elif name == "Tex_D":
            default_texture = white
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
        else:
            default_texture = black
            # All exported non-color/non-normal maps are imported as TC_MASKS.
            # The sampler type must match even for inherited parameters that keep
            # BASE_Black as their default, otherwise SM6 rejects the whole master.
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
        texture_nodes[name] = create_texture_parameter(
            material, name, default_texture, sampler, -1900, -800 + index * 120
        )

    scalar_nodes = {}
    for index, name in enumerate(sorted(scalar_names)):
        scalar_nodes[name] = create_scalar_parameter(
            material,
            name,
            FUNCTIONAL_SCALARS.get(name, 0.0),
            -1500,
            -800 + index * 100,
        )

    vector_nodes = {}
    for index, name in enumerate(sorted(vector_names)):
        vector_nodes[name] = create_vector_parameter(
            material,
            name,
            FUNCTIONAL_VECTORS.get(name, (0.0, 0.0, 0.0, 1.0)),
            -1100,
            -800 + index * 120,
        )

    for index, name in enumerate(sorted(switch_names)):
        create_static_switch_parameter(material, name, False, -700, 1300 + index * 100)

    # Base color: stylized diffuse, with category-controlled eye and ghost branches.
    tint_multiply = create_expression(material, unreal.MaterialExpressionMultiply, -700, -700)
    connect(texture_nodes["Tex_D"], "RGB", tint_multiply, "A")
    connect(vector_nodes["BaseColorTint"], "RGB", tint_multiply, "B")

    brightness_multiply = create_expression(material, unreal.MaterialExpressionMultiply, -450, -700)
    connect(tint_multiply, "", brightness_multiply, "A")
    connect(scalar_nodes["BaseColorBrightness"], "", brightness_multiply, "B")

    eye_lerp = create_expression(material, unreal.MaterialExpressionLinearInterpolate, -150, -700)
    connect(brightness_multiply, "", eye_lerp, "A")
    connect(texture_nodes["Tex_E"], "RGB", eye_lerp, "B")
    connect(scalar_nodes["UseEyeTexture"], "", eye_lerp, "Alpha")

    ghost_lerp = create_expression(material, unreal.MaterialExpressionLinearInterpolate, 150, -700)
    connect(eye_lerp, "", ghost_lerp, "A")
    connect(vector_nodes["GhostColor"], "RGB", ghost_lerp, "B")
    connect(scalar_nodes["UseGhostLook"], "", ghost_lerp, "Alpha")
    connect_property(ghost_lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)

    # Normal map with a flat-normal fallback for eyes and any texture-less category.
    normal_lerp = create_expression(material, unreal.MaterialExpressionLinearInterpolate, -150, -350)
    connect(vector_nodes["FlatNormal"], "RGB", normal_lerp, "A")
    connect(texture_nodes["Tex_N"], "RGB", normal_lerp, "B")
    connect(scalar_nodes["UseNormalMap"], "", normal_lerp, "Alpha")
    connect_property(normal_lerp, "", unreal.MaterialProperty.MP_NORMAL)

    # Packed specular mask: green drives inverse roughness, red drives specular.
    one_minus = create_expression(material, unreal.MaterialExpressionOneMinus, -700, -100)
    connect(texture_nodes["Tex_S"], "G", one_minus, "None")
    roughness_scale = create_expression(material, unreal.MaterialExpressionMultiply, -450, -100)
    connect(one_minus, "", roughness_scale, "A")
    connect(scalar_nodes["RoughnessScale"], "", roughness_scale, "B")
    roughness_add = create_expression(material, unreal.MaterialExpressionAdd, -200, -100)
    connect(roughness_scale, "", roughness_add, "A")
    connect(scalar_nodes["RoughnessBias"], "", roughness_add, "B")
    roughness_saturate = create_expression(material, unreal.MaterialExpressionSaturate, 50, -100)
    connect(roughness_add, "", roughness_saturate, "None")
    connect_property(roughness_saturate, "", unreal.MaterialProperty.MP_ROUGHNESS)

    specular_multiply = create_expression(material, unreal.MaterialExpressionMultiply, -200, 100)
    connect(texture_nodes["Tex_S"], "R", specular_multiply, "A")
    connect(scalar_nodes["SpecularStrength"], "", specular_multiply, "B")
    specular_saturate = create_expression(material, unreal.MaterialExpressionSaturate, 50, 100)
    connect(specular_multiply, "", specular_saturate, "None")
    connect_property(specular_saturate, "", unreal.MaterialProperty.MP_SPECULAR)

    metallic_source = create_expression(material, unreal.MaterialExpressionLinearInterpolate, -450, 300)
    connect(texture_nodes["Tex_R"], "R", metallic_source, "A")
    connect(texture_nodes["Tex_S"], "R", metallic_source, "B")
    connect(scalar_nodes["UseSpecularAsMetallic"], "", metallic_source, "Alpha")
    metallic_multiply = create_expression(material, unreal.MaterialExpressionMultiply, -200, 300)
    connect(metallic_source, "", metallic_multiply, "A")
    connect(scalar_nodes["MetallicStrength"], "", metallic_multiply, "B")
    metallic_saturate = create_expression(material, unreal.MaterialExpressionSaturate, 50, 300)
    connect(metallic_multiply, "", metallic_saturate, "None")
    connect_property(metallic_saturate, "", unreal.MaterialProperty.MP_METALLIC)

    # Eye glow and ghost fresnel are the only intentional emissive paths.  Other
    # Tex_E maps are packed effect masks in the source game and must not glow.
    eye_emissive = create_expression(material, unreal.MaterialExpressionMultiply, -450, 550)
    connect(texture_nodes["Tex_E"], "RGB", eye_emissive, "A")
    connect(scalar_nodes["EyeEmissiveStrength"], "", eye_emissive, "B")
    eye_gate = create_expression(material, unreal.MaterialExpressionMultiply, -200, 550)
    connect(eye_emissive, "", eye_gate, "A")
    connect(scalar_nodes["UseEyeTexture"], "", eye_gate, "B")

    fresnel = create_expression(material, unreal.MaterialExpressionFresnel, -700, 750)
    ghost_fresnel_color = create_expression(material, unreal.MaterialExpressionMultiply, -450, 750)
    connect(fresnel, "", ghost_fresnel_color, "A")
    connect(vector_nodes["GhostColor"], "RGB", ghost_fresnel_color, "B")
    ghost_fresnel_strength = create_expression(material, unreal.MaterialExpressionMultiply, -200, 750)
    connect(ghost_fresnel_color, "", ghost_fresnel_strength, "A")
    connect(scalar_nodes["GhostFresnelStrength"], "", ghost_fresnel_strength, "B")
    ghost_gate = create_expression(material, unreal.MaterialExpressionMultiply, 50, 750)
    connect(ghost_fresnel_strength, "", ghost_gate, "A")
    connect(scalar_nodes["UseGhostLook"], "", ghost_gate, "B")
    emissive_add = create_expression(material, unreal.MaterialExpressionAdd, 300, 600)
    connect(eye_gate, "", emissive_add, "A")
    connect(ghost_gate, "", emissive_add, "B")
    connect_property(emissive_add, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    opacity_lerp = create_expression(material, unreal.MaterialExpressionLinearInterpolate, -150, 1000)
    connect(scalar_nodes["SolidOpacity"], "", opacity_lerp, "A")
    connect(texture_nodes["Tex_D"], "A", opacity_lerp, "B")
    connect(scalar_nodes["UseDiffuseAlpha"], "", opacity_lerp, "Alpha")
    connect_property(opacity_lerp, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material


def build_eye_shadow_master():
    material = create_or_load_asset(
        EYE_SHADOW_MASTER_NAME, MASTER_ROOT, unreal.Material, unreal.MaterialFactoryNew()
    )
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    set_property_if_available(material, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    set_property_if_available(material, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    set_property_if_available(material, "two_sided", True)
    set_property_if_available(material, "dithered_lod_transition", False)

    color = create_vector_parameter(material, "Color", (0.0, 0.0, 0.0, 1.0), -400, -100)
    opacity = create_scalar_parameter(material, "Opacity", 0.6, -400, 100)
    connect_property(color, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    connect_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material


def set_metadata(asset, record):
    try:
        if record and record.get("path"):
            unreal.EditorAssetLibrary.set_metadata_tag(asset, "Khazan.SourceJson", record["path"])
        unreal.EditorAssetLibrary.set_metadata_tag(
            asset, "Khazan.RebuildVersion", "UE5-standard-2026-08-27"
        )
    except Exception as exception:
        warn("Could not set metadata on {}: {}".format(asset.get_name(), exception))


def apply_scalar(instance, name, value):
    # UE 5.8's UMaterialEditingLibrary implementation applies the value but
    # currently returns its never-updated local bResult (always false).
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        instance, name, float(value)
    )


def apply_vector(instance, name, value):
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        instance, name, unreal.LinearColor(*value)
    )


def apply_record(instance, record, textures):
    for parameter, reference in sorted(record["textures"].items()):
        texture = textures.get(reference["name"])
        if texture:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance, parameter, texture
            )
    for parameter, value in sorted(record["scalars"].items()):
        if valid_parameter_name(parameter):
            apply_scalar(instance, parameter, value)
    for parameter, value in sorted(record["vectors"].items()):
        if valid_parameter_name(parameter):
            apply_vector(instance, parameter, value)
    for parameter, value in sorted(record["switches"].items()):
        if valid_parameter_name(parameter):
            unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(
                instance, parameter, bool(value)
            )


def apply_overrides(instance, overrides):
    for parameter, value in (overrides.get("scalars", {}) or {}).items():
        apply_scalar(instance, parameter, value)
    for parameter, value in (overrides.get("vectors", {}) or {}).items():
        apply_vector(instance, parameter, value)


def reset_instance(instance, parent):
    unreal.MaterialEditingLibrary.clear_all_material_instance_parameters(instance)
    unreal.MaterialEditingLibrary.set_material_instance_parent(instance, parent)
    actual_parent = instance.get_editor_property("parent")
    if actual_parent != parent:
        raise RuntimeError(
            "Could not set parent {} on {}".format(parent.get_path_name(), instance.get_path_name())
        )
    # UE 5.8 does not refresh the inherited parameter table immediately when a
    # MaterialInstanceConstant changes parent.  Refresh it before applying JSON
    # overrides or every setter reports a false "parameter missing" result.
    unreal.MaterialEditingLibrary.update_material_instance(instance)


def create_instance(name, package_path):
    return create_or_load_asset(
        name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )


def build_base_instances(records, character_master, textures):
    built = {}

    def build(name):
        if name == CHARACTER_MASTER_NAME:
            return character_master
        if name in built:
            return built[name]
        record = records.get(name)
        if not record:
            record = empty_record(name)
            record["parent"] = KNOWN_PARENTS.get(name, CHARACTER_MASTER_NAME)
            records[name] = record
        parent_name = record.get("parent") or KNOWN_PARENTS.get(name, CHARACTER_MASTER_NAME)
        parent = build(parent_name)
        instance = create_instance(name, BASE_ROOT)
        reset_instance(instance, parent)
        apply_record(instance, record, textures)
        if name in CATEGORY_OVERRIDES:
            apply_overrides(instance, CATEGORY_OVERRIDES[name])
        unreal.MaterialEditingLibrary.update_material_instance(instance)
        set_metadata(instance, record)
        unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
        built[name] = instance
        log("BASE {} -> {}".format(instance.get_path_name(), parent.get_path_name()))
        return instance

    ancestor_names = set()
    for record in records.values():
        parent_name = record.get("parent")
        while parent_name and parent_name != CHARACTER_MASTER_NAME:
            ancestor_names.add(parent_name)
            parent_record = records.get(parent_name)
            parent_name = (
                parent_record.get("parent") if parent_record else KNOWN_PARENTS.get(parent_name, "")
            )
    for name in sorted(ancestor_names):
        build(name)
    return built, build


def update_target_instances(
    targets,
    records,
    instances_by_name,
    base_builder,
    eye_shadow_master,
    textures,
):
    canonical = {}
    for target in sorted(targets):
        record = records[target]
        if target == EYE_SHADOW_NAME:
            parent = eye_shadow_master
        else:
            parent_name = record.get("parent") or infer_target_parent(target)
            parent = base_builder(parent_name)
        instances = list(instances_by_name.get(target, []))
        if not instances:
            instances = [create_instance(target, INSTANCE_ROOT)]
        for instance in instances:
            reset_instance(instance, parent)
            apply_record(instance, record, textures)
            unreal.MaterialEditingLibrary.update_material_instance(instance)
            set_metadata(instance, record)
            unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
            STATS["instances_updated"] += 1
            log("INSTANCE {} -> {}".format(instance.get_path_name(), parent.get_path_name()))
        canonical[target] = instances[0]
    return canonical


def ensure_mesh_assignments(meshes, canonical):
    for mesh in meshes:
        materials = list(mesh.get_editor_property("materials"))
        changed = False
        for skeletal_material in materials:
            slot_name = str(skeletal_material.get_editor_property("material_slot_name"))
            current = skeletal_material.get_editor_property("material_interface")
            if slot_name not in canonical:
                continue
            if current and isinstance(current, unreal.MaterialInstanceConstant) and current.get_name() == slot_name:
                continue
            skeletal_material.set_editor_property("material_interface", canonical[slot_name])
            STATS["mesh_slots_reassigned"] += 1
            changed = True
        if changed:
            mesh.set_editor_property("materials", materials)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)


def validate_results(meshes, targets, records, textures):
    problems = []
    for target in sorted(targets):
        if target not in records:
            problems.append("No parsed record for " + target)
    for mesh in meshes:
        for skeletal_material in mesh.get_editor_property("materials"):
            slot_name = str(skeletal_material.get_editor_property("material_slot_name"))
            material = skeletal_material.get_editor_property("material_interface")
            if slot_name in targets:
                if not material:
                    problems.append("{} slot {} has no material".format(mesh.get_path_name(), slot_name))
                elif not isinstance(material, unreal.MaterialInstanceConstant):
                    problems.append(
                        "{} slot {} is not a material instance".format(mesh.get_path_name(), slot_name)
                    )
                else:
                    parent = material.get_editor_property("parent")
                    if not parent or "/Material/Generated/" not in parent.get_path_name():
                        problems.append(
                            "{} slot {} has unexpected parent {}".format(
                                mesh.get_path_name(),
                                slot_name,
                                parent.get_path_name() if parent else "None",
                            )
                        )
    for texture_name, texture in textures.items():
        if not texture:
            problems.append("Imported texture asset missing: " + texture_name)
    if problems:
        raise RuntimeError("Validation failed: " + "; ".join(problems))


def main():
    if not os.path.isdir(SOURCE_ROOT):
        raise RuntimeError("Source data directory does not exist: " + SOURCE_ROOT)
    log("source=" + SOURCE_ROOT)

    json_index, png_index = build_source_indices()
    log("source index: {} JSON, {} unique PNG names".format(len(json_index), len(png_index)))

    meshes, instances_by_name = collect_project_assets()
    targets = mesh_material_targets(meshes)
    log("project targets: {} meshes, {} slots, {} unique materials".format(
        STATS["meshes"], STATS["slots"], STATS["target_materials"]
    ))

    records = collect_records(targets, json_index)
    missing_json = sorted(target for target in targets if not records[target]["path"])
    if missing_json:
        raise RuntimeError("Material JSON files are missing for slots: " + ", ".join(missing_json))

    texture_sources, references_by_texture = resolve_texture_sources(
        records, targets, png_index
    )
    textures = import_textures(texture_sources, references_by_texture)

    character_master = build_character_master(records, targets, textures)
    eye_shadow_master = build_eye_shadow_master()
    _, base_builder = build_base_instances(records, character_master, textures)
    canonical = update_target_instances(
        targets,
        records,
        instances_by_name,
        base_builder,
        eye_shadow_master,
        textures,
    )
    ensure_mesh_assignments(meshes, canonical)
    validate_results(meshes, targets, records, textures)

    log("SUCCESS " + json.dumps(STATS, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        error(str(exception))
        error(traceback.format_exc())
        raise
