"""Reconstruct inherited HeinMach override materials and repair render-slot use.

The root-template restoration recovered 6,439 previously omitted prop actors,
but 128 actor-only MaterialInstanceConstant packages were not present in the
USD import.  This script rebuilds those instances from raw FModel Properties
JSON and texture exports, maps original LOD0 bindings to UE slots by texture
fingerprint, clears stale direct-index overrides, and applies all render-slot
overrides.  Original LOD-only material indices are recorded but deliberately
not forced onto the imported LOD0 mesh.

Fog actors and Fog materials are outside this operation.  A transform hash is
captured before and after the change and the save is refused if it changes.
"""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreInheritedMaterialFix"
)
CORRECTED_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets"
)
OVERRIDE_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/OverrideMaterials"
)
MATERIAL_ROOT = OVERRIDE_ROOT + "/Inherited/Materials"
TEXTURE_ROOT = OVERRIDE_ROOT + "/Textures"
USD_PREVIEW_PARENT = (
    "/USDCore/Materials/UsdPreviewSurfaceTranslucent."
    "UsdPreviewSurfaceTranslucent"
)

ROOT_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RootTemplateCoverage_Audit.json",
)
SOURCE_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_InheritedOverrideSource_Audit.json",
)
ROOT_RESTORATION_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_InheritedRootProp_Restoration.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_InheritedOverrideMaterial_Restoration.json",
)
REPAIR_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "repair_heinmach_materials.py")
EXCLUSION_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "heinmach_exclusions.py")

EXPECTED_PLACEMENT_COUNT = 9104
EXPECTED_MESH_COUNT = 313
EXPECTED_REBUILT_MATERIAL_COUNT = 128
EXPECTED_REBUILT_REFERENCE_COUNT = 6962
EXPECTED_FOG_COUNT = 50
MANAGED_LABEL_PREFIX = "HM_Prop_"
FOG_LABEL_PREFIX = "HM_FogSheet_"
SKIP_REBUILD_PACKAGES = set()
EXTERNAL_MATERIAL_PATHS = {}
UPDATE_MATERIAL_INSTANCES = True
USE_LEGACY_TEXTURE_FACTORY = False
VARIANT_SUFFIX_RE = re.compile(
    r"(?:_opaque|_portal|_va\d+|_noemissive|_lod\d*)$", re.IGNORECASE
)


def log(message):
    unreal.log("KHAZAN_HEINMACH_INHERITED_MATERIALS: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def load_repair_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_material_mapping", REPAIR_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HeinMach material mapping helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


repair = load_repair_module()


def load_exclusion_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_material_exclusions", EXCLUSION_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HeinMach exclusion metadata helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exclusions = load_exclusion_module()
TRANSFORM_OVERRIDES = exclusions.transform_overrides("root_prop")


def package_basename(package):
    return str(package).replace("\\", "/").rsplit("/", 1)[-1]


def package_from_object_path(object_path):
    return str(object_path).rsplit(".", 1)[0] if object_path else None


def package_json_path(package):
    relative = os.path.join(*str(package).split("/")) + ".json"
    # Raw Properties exports are authoritative.  USD sidecar JSON has a
    # different schema, so prefer Exports whenever both exist.
    candidates = (
        os.path.join(FMODEL_ROOT, "Exports", relative),
        os.path.join(FMODEL_ROOT, relative),
    )
    return next((path for path in candidates if os.path.isfile(path)), None)


def source_image_path(texture_package):
    relative = os.path.join(*str(texture_package).split("/"))
    for root in (FMODEL_ROOT, os.path.join(FMODEL_ROOT, "Exports")):
        for extension in (".png", ".hdr", ".exr", ".tga"):
            candidate = os.path.join(root, relative) + extension
            if os.path.isfile(candidate):
                return candidate
    return None


def source_package_from_usd(path):
    if not path:
        return None
    relative = os.path.relpath(os.path.splitext(path)[0], FMODEL_ROOT)
    if relative.startswith(".."):
        return None
    return relative.replace(os.sep, "/")


def managed_label(placement):
    return (
        "{}{}_{}_{}".format(
            MANAGED_LABEL_PREFIX,
            placement.get("source_level", "Unknown"),
            placement.get("source_object_index", 0),
            placement.get("actor_name", "Actor"),
        )
    )[:220]


def filter_excluded_placements(placements):
    excluded = exclusions.exclusion_labels("root_prop")
    return [placement for placement in placements if managed_label(placement) not in excluded]


def expected_transform(placement):
    override = TRANSFORM_OVERRIDES.get(managed_label(placement), {})
    return override.get("preserved_transform", placement.get("transform", {}))


def actor_transform_record(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "label": actor.get_actor_label(),
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": [scale.x, scale.y, scale.z],
    }


def fog_signature(actor_subsystem):
    records = sorted(
        (
            actor_transform_record(actor)
            for actor in actor_subsystem.get_all_level_actors()
            if actor and actor.get_actor_label().startswith(FOG_LABEL_PREFIX)
        ),
        key=lambda item: item["label"],
    )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def backup_map_once():
    if unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        return False
    if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
        raise RuntimeError("Failed to create material-fix backup map")
    unreal.EditorAssetLibrary.save_asset(BACKUP_MAP_PATH, only_if_is_dirty=False)
    return True


def raw_material_record(package):
    path = package_json_path(package)
    if not path:
        raise RuntimeError("Raw material JSON is missing: " + package)
    payload = load_json(path)
    if isinstance(payload, list):
        source = next(
            (
                item
                for item in payload
                if isinstance(item, dict)
                and item.get("Type") in {"Material", "MaterialInstanceConstant"}
            ),
            None,
        )
        if not source:
            raise RuntimeError("Material record is missing: " + path)
        properties = source.get("Properties", {})
        texture_values = properties.get("TextureParameterValues", []) or []
        scalar_values = properties.get("ScalarParameterValues", []) or []
        vector_values = properties.get("VectorParameterValues", []) or []
        static_parameters = properties.get("StaticParameters") or {}
        switch_values = static_parameters.get("StaticSwitchParameters", []) or []
        parent_package = package_from_object_path(
            (properties.get("Parent") or {}).get("ObjectPath")
        )
        base_property_overrides = properties.get("BasePropertyOverrides", {}) or {}
    elif isinstance(payload, dict) and isinstance(payload.get("Parameters"), dict):
        parameters = payload["Parameters"]
        properties = parameters.get("Properties", {}) or {}
        texture_values = [
            {
                "ParameterInfo": {"Name": name},
                "ParameterValue": {"ObjectPath": object_path},
            }
            for name, object_path in (payload.get("Textures") or {}).items()
            if object_path
        ]
        scalar_values = [
            {"ParameterInfo": {"Name": name}, "ParameterValue": value}
            for name, value in (parameters.get("Scalars") or {}).items()
        ]
        vector_values = [
            {"ParameterInfo": {"Name": name}, "ParameterValue": value}
            for name, value in (parameters.get("Colors") or {}).items()
        ]
        switch_values = [
            {
                "ParameterInfo": {"Name": name},
                "Value": bool(value),
                "bOverride": True,
            }
            for name, value in (parameters.get("Switches") or {}).items()
        ]
        parent_package = None
        base_property_overrides = properties.get("BasePropertyOverrides", {}) or {}
    else:
        raise RuntimeError("Unsupported FModel material payload: " + path)

    textures = []
    for item in texture_values:
        parameter_name = (item.get("ParameterInfo") or {}).get("Name")
        object_path = (item.get("ParameterValue") or {}).get("ObjectPath")
        texture_package = package_from_object_path(object_path)
        if parameter_name and texture_package:
            textures.append(
                {
                    "name": parameter_name,
                    "package": texture_package,
                    "texture_name": package_basename(texture_package),
                }
            )

    scalars = []
    for item in scalar_values:
        name = (item.get("ParameterInfo") or {}).get("Name")
        value = item.get("ParameterValue")
        if name and isinstance(value, (int, float)):
            scalars.append({"name": name, "value": float(value)})

    vectors = []
    for item in vector_values:
        name = (item.get("ParameterInfo") or {}).get("Name")
        value = item.get("ParameterValue") or {}
        if name and isinstance(value, (dict, list, tuple)):
            if isinstance(value, dict):
                channels = [
                    float(value.get("R", value.get("r", 0.0))),
                    float(value.get("G", value.get("g", 0.0))),
                    float(value.get("B", value.get("b", 0.0))),
                    float(value.get("A", value.get("a", 1.0))),
                ]
            else:
                channels = [float(channel) for channel in value[:4]]
                while len(channels) < 4:
                    channels.append(1.0 if len(channels) == 3 else 0.0)
            vectors.append(
                {
                    "name": name,
                    "value": channels,
                }
            )

    switches = []
    for item in switch_values:
        name = (item.get("ParameterInfo") or {}).get("Name")
        if name and item.get("bOverride", True):
            switches.append({"name": name, "value": bool(item.get("Value"))})

    return {
        "package": package,
        "name": package_basename(package),
        "json_path": path,
        "parent_package": parent_package,
        "textures": textures,
        "scalars": scalars,
        "vectors": vectors,
        "switches": switches,
        "base_property_overrides": base_property_overrides,
    }


def asset_class_name(asset_or_path):
    if not asset_or_path:
        return "Invalid"
    if not isinstance(asset_or_path, str):
        return asset_or_path.get_class().get_name()
    data = unreal.EditorAssetLibrary.find_asset_data(asset_or_path)
    if not data or not data.is_valid():
        return "Invalid"
    return str(data.asset_class_path.asset_name)


def normalized_material_names(asset):
    name = asset.get_name()
    result = {name}
    for prefix in ("MI_", "M_"):
        if name.startswith(prefix):
            result.add(name[len(prefix) :])
    return result


def material_asset_index():
    by_name = collections.defaultdict(list)
    paths = []
    for root in (CORRECTED_ROOT, OVERRIDE_ROOT):
        if not unreal.EditorAssetLibrary.does_directory_exist(root):
            continue
        for path in unreal.EditorAssetLibrary.list_assets(
            root, recursive=True, include_folder=False
        ):
            if asset_class_name(path) not in {"Material", "MaterialInstanceConstant"}:
                continue
            paths.append(path)
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if not asset:
                continue
            for name in normalized_material_names(asset):
                by_name[name].append(path)
    return by_name, sorted(set(paths))


def actual_material_records(mesh):
    records = []
    for ue_slot, static_material in enumerate(
        list(mesh.get_editor_property("static_materials"))
    ):
        material = static_material.get_editor_property("material_interface")
        records.append(
            {
                "ue_slot": ue_slot,
                "material": material,
                "path": material.get_path_name() if material else None,
                "name": material.get_name() if material else None,
                "textures": repair.actual_material_textures(material),
            }
        )
    return records


def build_mesh_mappings(mesh_packages):
    mesh_index = repair.corrected_mesh_index()
    mappings = {}
    source_package_to_actual = collections.defaultdict(list)
    source_name_to_actual = collections.defaultdict(list)
    records = []
    for item_index, mesh_package in enumerate(mesh_packages, start=1):
        mesh = mesh_index.get(package_basename(mesh_package))
        if not mesh:
            raise RuntimeError("Corrected mesh is missing: " + mesh_package)
        parsed = repair.parse_mesh_materials(mesh_package)
        source_records = []
        for source_slot, source_name in sorted(parsed["slots"].items()):
            reference_path = parsed["references"].get(source_name)
            source_records.append(
                {
                    "source_slot": source_slot,
                    "source_name": source_name,
                    "source_package": source_package_from_usd(reference_path),
                    "source": repair.source_material_info(
                        source_name, reference_usd=reference_path
                    ),
                }
            )
        actual_records = actual_material_records(mesh)
        assignments, tie_count = repair.best_slot_assignment(
            source_records, actual_records
        )
        slot_map = {}
        clean_assignments = []
        by_source_slot = {item["source_slot"]: item for item in source_records}
        for assignment in assignments:
            source_slot = int(assignment["source_slot"])
            ue_slot = int(assignment["ue_slot"])
            slot_map[source_slot] = ue_slot
            source_record = by_source_slot[source_slot]
            actual_path = assignment.get("actual_material_path")
            if actual_path:
                source_name_to_actual[source_record["source_name"]].append(actual_path)
                if source_record["source_package"]:
                    source_package_to_actual[source_record["source_package"]].append(
                        actual_path
                    )
            clean_assignments.append(
                {
                    "source_slot": source_slot,
                    "ue_slot": ue_slot,
                    "source_name": source_record["source_name"],
                    "source_package": source_record["source_package"],
                    "actual_material_path": actual_path,
                    "score": assignment.get("score"),
                    "matched_textures": assignment.get("matched_textures", []),
                }
            )
        mappings[mesh_package] = slot_map
        records.append(
            {
                "mesh_package": mesh_package,
                "mesh_path": mesh.get_path_name(),
                "source_binding_slot_count": len(source_records),
                "ue_slot_count": len(actual_records),
                "assignment_tie_count": tie_count,
                "assignments": clean_assignments,
            }
        )
        if item_index % 50 == 0:
            log("Mapped {}/{} mesh material layouts".format(item_index, len(mesh_packages)))
    return mappings, source_package_to_actual, source_name_to_actual, records


def existing_texture_index():
    result = {}
    if not unreal.EditorAssetLibrary.does_directory_exist(TEXTURE_ROOT):
        return result
    for path in unreal.EditorAssetLibrary.list_assets(
        TEXTURE_ROOT, recursive=True, include_folder=False
    ):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        # Pivot Painter position HDRs may be classified as TextureCube by
        # UE 5.8 Interchange.  Keep the imported source asset in the index;
        # incompatible 2D-only parameters are reported by configure_material
        # instead of causing the entire material inventory to look missing.
        if not asset or asset.get_class().get_name() not in {
            "Texture2D",
            "TextureCube",
        }:
            continue
        name = asset.get_name()
        if name.startswith("T_"):
            name = name[2:]
        result[name] = asset
    return result


def import_textures(records):
    required = {}
    usages = collections.defaultdict(set)
    for record in records:
        for item in record["textures"]:
            required[item["texture_name"]] = item["package"]
            usages[item["texture_name"]].add(item["name"])
    index = existing_texture_index()
    tasks = []
    missing = []
    for texture_name, texture_package in sorted(required.items()):
        if texture_name in index:
            continue
        image_path = source_image_path(texture_package)
        if not image_path:
            missing.append({"package": texture_package, "texture": texture_name})
            continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", image_path)
        task.set_editor_property("destination_path", TEXTURE_ROOT)
        task.set_editor_property("destination_name", "T_" + texture_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        if USE_LEGACY_TEXTURE_FACTORY:
            # UE 5.8 Interchange can re-enter TaskGraph while a Python-driven
            # multi-file texture import is waiting synchronously.  Supplying a
            # concrete factory selects the deterministic legacy import path.
            task.set_editor_property("factory", unreal.TextureFactory())
        tasks.append(task)
    if missing:
        raise RuntimeError("Missing source texture images: " + str(missing[:5]))
    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    index = existing_texture_index()
    absent_after = sorted(set(required) - set(index))
    if absent_after:
        raise RuntimeError("Texture import left assets unresolved: " + str(absent_after[:5]))

    configured = []
    for texture_name in sorted(required):
        texture = index[texture_name]
        parameter_names = {name.upper() for name in usages[texture_name]}
        upper_name = texture_name.upper()
        texture.modify()
        if upper_name.endswith("_N") or any("NORMAL" in name for name in parameter_names):
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
            )
            texture.set_editor_property("srgb", False)
        elif upper_name.endswith("_S") or any(
            token in name
            for name in parameter_names
            for token in ("MASK", "HEIGHT", "ROUGHNESS", "METALLIC")
        ):
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
            )
            texture.set_editor_property("srgb", False)
        elif any(
            token in name
            for name in parameter_names
            for token in ("POSITION", "VECTOR", "PIVOT")
        ):
            texture.set_editor_property("srgb", False)
        configured.append(texture.get_path_name())
    unreal.EditorAssetLibrary.save_directory(
        TEXTURE_ROOT, only_if_is_dirty=False, recursive=True
    )
    return index, len(tasks), configured


def most_common_existing(paths):
    valid = [
        path
        for path in paths
        if path and unreal.EditorAssetLibrary.does_asset_exist(path.split(".", 1)[0])
    ]
    if not valid:
        return None
    return collections.Counter(valid).most_common(1)[0][0]


def stripped_variant_names(name):
    result = []
    current = name
    while True:
        stripped = VARIANT_SUFFIX_RE.sub("", current)
        if stripped == current:
            break
        result.append(stripped)
        current = stripped
    return result


def choose_template(
    record,
    live_templates,
    source_package_to_actual,
    source_name_to_actual,
    material_name_index,
    rebuilt_by_name,
):
    live = most_common_existing(live_templates.get(record["package"], []))
    if live:
        return live, "live_component_default"

    parent_package = record.get("parent_package")
    if parent_package:
        parent = most_common_existing(source_package_to_actual.get(parent_package, []))
        if parent:
            return parent, "source_parent_package"
        parent_name = package_basename(parent_package)
        parent = most_common_existing(material_name_index.get(parent_name, []))
        if parent:
            return parent, "source_parent_name"

    for candidate_name in stripped_variant_names(record["name"]):
        rebuilt = rebuilt_by_name.get(candidate_name)
        if rebuilt:
            return rebuilt.get_path_name(), "rebuilt_variant_base"
        candidate = most_common_existing(source_name_to_actual.get(candidate_name, []))
        if candidate:
            return candidate, "stripped_source_name"
        candidate = most_common_existing(material_name_index.get(candidate_name, []))
        if candidate:
            return candidate, "stripped_asset_name"

    exact = most_common_existing(source_name_to_actual.get(record["name"], []))
    if exact:
        return exact, "exact_source_name"
    exact = most_common_existing(material_name_index.get(record["name"], []))
    if exact:
        return exact, "exact_asset_name"
    return USD_PREVIEW_PARENT, "usd_preview_fallback"


def create_or_load_material(record, template_path):
    asset_name = "MI_" + record["name"]
    asset_path = MATERIAL_ROOT + "/" + asset_name
    material = unreal.EditorAssetLibrary.load_asset(asset_path)
    if material:
        return material, False

    template = unreal.EditorAssetLibrary.load_asset(template_path)
    if template and template.get_class().get_name() == "MaterialInstanceConstant":
        duplicated = unreal.EditorAssetLibrary.duplicate_asset(
            template_path.split(".", 1)[0], asset_path
        )
        material = unreal.EditorAssetLibrary.load_asset(asset_path)
        if duplicated and material:
            return material, True

    factory = unreal.MaterialInstanceConstantFactoryNew()
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name, MATERIAL_ROOT, unreal.MaterialInstanceConstant, factory
    )
    if not material:
        raise RuntimeError("Failed to create material: " + asset_path)
    parent = template or unreal.EditorAssetLibrary.load_asset(USD_PREVIEW_PARENT)
    if not parent:
        raise RuntimeError("Material parent is unavailable for: " + record["package"])
    unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
    return material, True


def set_struct_property(struct_value, name, value):
    try:
        struct_value.set_editor_property(name, value)
        return True
    except Exception:
        return False


def blend_mode_value(value):
    mapping = {
        "BLEND_Opaque": unreal.BlendMode.BLEND_OPAQUE,
        "BLEND_Masked": unreal.BlendMode.BLEND_MASKED,
        "BLEND_Translucent": unreal.BlendMode.BLEND_TRANSLUCENT,
        "BLEND_Additive": unreal.BlendMode.BLEND_ADDITIVE,
        "BLEND_Modulate": unreal.BlendMode.BLEND_MODULATE,
        "BLEND_AlphaComposite": unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
        "BLEND_AlphaHoldout": unreal.BlendMode.BLEND_ALPHA_HOLDOUT,
    }
    return mapping.get(str(value))


def try_texture(material, name, texture):
    try:
        return bool(
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                material, name, texture
            )
        )
    except Exception:
        return False


def try_scalar(material, name, value):
    try:
        return bool(
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                material, name, float(value)
            )
        )
    except Exception:
        return False


def try_vector(material, name, value):
    try:
        color = unreal.LinearColor(value[0], value[1], value[2], value[3])
        return bool(
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                material, name, color
            )
        )
    except Exception:
        return False


def try_switch(material, name, value):
    try:
        return bool(
            unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(
                material, name, bool(value)
            )
        )
    except Exception:
        return False


def configure_material(material, record, texture_index):
    material.modify()
    results = collections.Counter()
    source_textures = {}
    for item in record["textures"]:
        texture = texture_index.get(item["texture_name"])
        if not texture:
            continue
        source_textures[item["name"]] = texture
        results["original_texture_attempts"] += 1
        if try_texture(material, item["name"], texture):
            results["original_texture_applied"] += 1

    channel_mapping = {
        "Tex_D": (
            ("BaseColorTexture", "OpacityTexture"),
            ("UseBaseColorTexture", "UseOpacityTexture"),
        ),
        "Tex_S": (
            ("MetallicTexture", "RoughnessTexture"),
            ("UseMetallicTexture", "UseRoughnessTexture"),
        ),
        "Tex_N": (("NormalTexture",), ("UseNormalTexture",)),
        "Tex_E": (("EmissiveColorTexture",), ("UseEmissiveColorTexture",)),
    }
    for source_name, (target_names, toggles) in channel_mapping.items():
        texture = source_textures.get(source_name)
        if not texture:
            continue
        for target_name in target_names:
            results["fallback_texture_attempts"] += 1
            if try_texture(material, target_name, texture):
                results["fallback_texture_applied"] += 1
        for toggle in toggles:
            results["fallback_scalar_attempts"] += 1
            if try_scalar(material, toggle, 1.0):
                results["fallback_scalar_applied"] += 1

    for item in record["scalars"]:
        results["original_scalar_attempts"] += 1
        if try_scalar(material, item["name"], item["value"]):
            results["original_scalar_applied"] += 1
    for item in record["vectors"]:
        results["original_vector_attempts"] += 1
        if try_vector(material, item["name"], item["value"]):
            results["original_vector_applied"] += 1
    for item in record["switches"]:
        results["original_switch_attempts"] += 1
        if try_switch(material, item["name"], item["value"]):
            results["original_switch_applied"] += 1

    overrides = material.get_editor_property("base_property_overrides")
    source_overrides = record["base_property_overrides"]
    if "TwoSided" in source_overrides:
        results["base_override_attempts"] += 1
        if set_struct_property(overrides, "override_two_sided", True) and set_struct_property(
            overrides, "two_sided", bool(source_overrides["TwoSided"])
        ):
            results["base_override_applied"] += 1
    blend_mode = blend_mode_value(source_overrides.get("BlendMode"))
    if blend_mode is not None:
        results["base_override_attempts"] += 1
        if set_struct_property(overrides, "override_blend_mode", True) and set_struct_property(
            overrides, "blend_mode", blend_mode
        ):
            results["base_override_applied"] += 1
    clip = source_overrides.get("OpacityMaskClipValue")
    if isinstance(clip, (int, float)):
        results["base_override_attempts"] += 1
        if set_struct_property(
            overrides, "override_opacity_mask_clip_value", True
        ) and set_struct_property(overrides, "opacity_mask_clip_value", float(clip)):
            results["base_override_applied"] += 1
    if "DitheredLODTransition" in source_overrides:
        results["base_override_attempts"] += 1
        if set_struct_property(
            overrides, "override_dithered_lod_transition", True
        ) and set_struct_property(
            overrides,
            "dithered_lod_transition",
            bool(source_overrides["DitheredLODTransition"]),
        ):
            results["base_override_applied"] += 1
    shading_name = source_overrides.get("ShadingModel")
    if shading_name:
        results["base_override_attempts"] += 1
        shading_model = getattr(unreal.MaterialShadingModel, str(shading_name), None)
        if shading_model is not None and set_struct_property(
            overrides, "override_shading_model", True
        ) and set_struct_property(overrides, "shading_model", shading_model):
            results["base_override_applied"] += 1
        else:
            # Shipping-game custom shading models (for example
            # MSM_BBQHalfCartoon) do not exist in stock UE's Python enum.
            # Keep the selected live template model and make the limitation
            # measurable in every restoration report.
            results["unsupported_shading_model"] += 1
    material.set_editor_property("base_property_overrides", overrides)
    if UPDATE_MATERIAL_INSTANCES:
        try:
            unreal.MaterialEditingLibrary.update_material_instance(material)
        except Exception:
            pass
    return dict(results)


def existing_material_for_package(
    package, source_package_to_actual, material_name_index
):
    external_path = EXTERNAL_MATERIAL_PATHS.get(package)
    if external_path:
        external = unreal.EditorAssetLibrary.load_asset(external_path)
        if external:
            return external
    path = most_common_existing(source_package_to_actual.get(package, []))
    if not path:
        path = most_common_existing(material_name_index.get(package_basename(package), []))
    return unreal.EditorAssetLibrary.load_asset(path) if path else None


def main():
    root_audit = load_json(ROOT_AUDIT_PATH)
    source_audit = load_json(SOURCE_AUDIT_PATH)
    restoration = load_json(ROOT_RESTORATION_PATH)
    source_placements = list(root_audit.get("resolved_root_placements", []))
    mesh_packages = sorted(
        {
            str(item.get("static_mesh_package"))
            for item in source_placements
            if item.get("static_mesh_package")
        }
    )
    if len(source_placements) != EXPECTED_PLACEMENT_COUNT or len(mesh_packages) != EXPECTED_MESH_COUNT:
        raise RuntimeError(
            "Unexpected placement inventory: placements={} meshes={}".format(
                len(source_placements), len(mesh_packages)
            )
        )
    placements = filter_excluded_placements(source_placements)
    if source_audit.get("missing_json_count") or source_audit.get("missing_texture_image_count"):
        raise RuntimeError("Inherited override source audit is incomplete")

    rebuild_packages = sorted(
        item["package"]
        for item in restoration.get("placement_result", {}).get(
            "unresolved_override_materials", []
        )
        if item["package"] not in SKIP_REBUILD_PACKAGES
    )
    rebuilt_reference_count = sum(
        int(item.get("placement_count", 0))
        for item in restoration.get("placement_result", {}).get(
            "unresolved_override_materials", []
        )
        if item.get("package") not in SKIP_REBUILD_PACKAGES
    )
    if (
        len(rebuild_packages) != EXPECTED_REBUILT_MATERIAL_COUNT
        or rebuilt_reference_count != EXPECTED_REBUILT_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Unexpected rebuild inventory: materials={} references={}".format(
                len(rebuild_packages), rebuilt_reference_count
            )
        )
    records = [raw_material_record(package) for package in rebuild_packages]

    (
        mesh_mappings,
        source_package_to_actual,
        source_name_to_actual,
        mesh_mapping_records,
    ) = build_mesh_mappings(mesh_packages)
    material_name_index, _ = material_asset_index()

    backup_created = backup_map_once()
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load HeinMach environment map")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_LABEL_PREFIX)
    }
    if len(actors_by_label) != len(placements):
        raise RuntimeError(
            "Managed actor inventory mismatch: {}".format(len(actors_by_label))
        )
    fog_before = fog_signature(actor_subsystem)
    if fog_before["count"] != EXPECTED_FOG_COUNT:
        raise RuntimeError("Fog boundary count mismatch: " + str(fog_before))

    live_templates = collections.defaultdict(list)
    missing_actor_labels = []
    missing_components = []
    for placement in placements:
        label = managed_label(placement)
        actor = actors_by_label.get(label)
        if not actor:
            missing_actor_labels.append(label)
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            missing_components.append(label)
            continue
        slot_map = mesh_mappings[str(placement["static_mesh_package"])]
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if package not in rebuild_packages or source_slot not in slot_map:
                continue
            material = component.get_material(slot_map[source_slot])
            if material:
                live_templates[package].append(material.get_path_name())
    if missing_actor_labels or missing_components:
        raise RuntimeError(
            "Placement actors/components missing: actors={} components={}".format(
                len(missing_actor_labels), len(missing_components)
            )
        )

    texture_index, texture_import_count, configured_textures = import_textures(records)
    materials_by_package = {}
    rebuilt_by_name = {}
    material_results = []
    parameter_totals = collections.Counter()
    for index, record in enumerate(records, start=1):
        template_path, template_reason = choose_template(
            record,
            live_templates,
            source_package_to_actual,
            source_name_to_actual,
            material_name_index,
            rebuilt_by_name,
        )
        material, created = create_or_load_material(record, template_path)
        parameter_result = configure_material(material, record, texture_index)
        parameter_totals.update(parameter_result)
        materials_by_package[record["package"]] = material
        rebuilt_by_name[record["name"]] = material
        material_results.append(
            {
                "package": record["package"],
                "material_path": material.get_path_name(),
                "created": created,
                "template_path": template_path,
                "template_reason": template_reason,
                "source_texture_count": len(record["textures"]),
                "source_scalar_count": len(record["scalars"]),
                "source_vector_count": len(record["vectors"]),
                "source_static_switch_count": len(record["switches"]),
                "parameter_result": parameter_result,
            }
        )
        if index % 25 == 0:
            log("Rebuilt {}/{} override materials".format(index, len(records)))
    unreal.EditorAssetLibrary.save_directory(
        MATERIAL_ROOT, only_if_is_dirty=False, recursive=True
    )

    existing_cache = {}
    total_override_references = 0
    render_slot_references = 0
    applied_references = 0
    verified_references = 0
    rebuilt_applied = 0
    existing_applied = 0
    non_render_slot_references = 0
    non_render_by_package = collections.Counter()
    unresolved = collections.Counter()
    cleared_component_count = 0

    for index, placement in enumerate(placements, start=1):
        actor = actors_by_label[managed_label(placement)]
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        try:
            component.set_editor_property("override_materials", [])
        except Exception:
            component.empty_override_materials()
        cleared_component_count += 1
        slot_map = mesh_mappings[str(placement["static_mesh_package"])]
        for source_slot, package in enumerate(
            placement.get("override_material_packages", [])
        ):
            if not package:
                continue
            total_override_references += 1
            ue_slot = slot_map.get(source_slot)
            if ue_slot is None:
                non_render_slot_references += 1
                non_render_by_package[package] += 1
                continue
            render_slot_references += 1
            material = materials_by_package.get(package)
            if material:
                rebuilt_applied += 1
            else:
                if package not in existing_cache:
                    existing_cache[package] = existing_material_for_package(
                        package, source_package_to_actual, material_name_index
                    )
                material = existing_cache[package]
                if material:
                    existing_applied += 1
            if not material:
                unresolved[package] += 1
                continue
            component.set_material(ue_slot, material)
            applied_references += 1
            actual = component.get_material(ue_slot)
            if actual and actual.get_path_name() == material.get_path_name():
                verified_references += 1
        if index % 1000 == 0:
            log("Applied render-slot overrides for {}/{} actors".format(index, len(placements)))

    fog_after = fog_signature(actor_subsystem)
    if fog_after != fog_before:
        raise RuntimeError(
            "Fog boundary guard failed: before={} after={}".format(
                fog_before, fog_after
            )
        )
    if unresolved or applied_references != render_slot_references:
        raise RuntimeError(
            "Render-slot override restoration unresolved: applied={}/{} packages={}".format(
                applied_references, render_slot_references, dict(unresolved)
            )
        )
    if verified_references != applied_references:
        raise RuntimeError(
            "Material assignment verification failed: {}/{}".format(
                verified_references, applied_references
            )
        )
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save inherited material restoration")

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "source_reports": {
            "root_template_coverage": ROOT_AUDIT_PATH,
            "root_restoration": ROOT_RESTORATION_PATH,
            "override_source_audit": SOURCE_AUDIT_PATH,
        },
        "inventory": {
            "placement_count": len(placements),
            "mesh_count": len(mesh_packages),
            "rebuilt_material_count": len(material_results),
            "required_texture_count": len(texture_index),
            "texture_import_task_count": texture_import_count,
            "configured_texture_count": len(configured_textures),
            "cleared_component_count": cleared_component_count,
        },
        "slot_restoration": {
            "total_source_override_reference_count": total_override_references,
            "render_slot_reference_count": render_slot_references,
            "applied_reference_count": applied_references,
            "verified_reference_count": verified_references,
            "rebuilt_material_applied_count": rebuilt_applied,
            "existing_material_applied_count": existing_applied,
            "non_render_lod_or_unused_reference_count": non_render_slot_references,
            "unresolved_render_slot_reference_count": sum(unresolved.values()),
            "non_render_lod_or_unused_by_package": [
                {"package": package, "reference_count": count}
                for package, count in sorted(non_render_by_package.items())
            ],
            "unresolved_render_slot_packages": [
                {"package": package, "reference_count": count}
                for package, count in sorted(unresolved.items())
            ],
            "policy": (
                "Only source slots explicitly bound by FModel's LOD0 USDA are mapped "
                "to UE. Original LOD-only/unused indices are recorded and not forced "
                "onto the imported LOD0 mesh."
            ),
        },
        "parameter_application_totals": dict(parameter_totals),
        "material_results": material_results,
        "mesh_mappings": mesh_mapping_records,
        "fog_boundary": {
            "status": "unchanged",
            "before": fog_before,
            "after": fog_after,
        },
        "excluded_content": [
            "Managed FogSheet actors and Fog materials",
            "All HeinMach_Cine_* layers",
            "Character/spawn/sound/BGM/POS/spline layers",
            "Barehanded staggering movement scene",
        ],
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT materials={} textures={} render_overrides={}/{} lod_only={} fog={} report={}".format(
            len(material_results),
            len(texture_index),
            applied_references,
            render_slot_references,
            non_render_slot_references,
            fog_after["count"],
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        unreal.log_error("KHAZAN_HEINMACH_INHERITED_MATERIALS: " + str(exception))
        unreal.log_error(failure["traceback"])
        raise
