"""Targeted material rebuild for DualAxeSword_Original_R only.

This intentionally does not rebuild shared Khazan masters/bases or touch any other
mesh.  It imports the five maps declared by CM_I_DualAxeSword_Original001V2_R,
creates that material instance under the existing Item folder, and assigns it to
the right-hand Original dual axe's only slot.
"""

import json
import os
import sys

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import build_khazan_materials as khazan  # noqa: E402


TARGET_MESH_PATH = "/Game/_Art/Kazan/Item/Original/DualAxeSword_Original_R"
TARGET_JSON_NAME = "CM_I_DualAxeSword_Original001V2_R"
TARGET_INSTANCE_ROOT = "/Game/_Art/Kazan/Material/Item"
TARGET_INSTANCE_PATH = TARGET_INSTANCE_ROOT + "/" + TARGET_JSON_NAME
TARGET_SLOT_NAME = "CM_I_DualAxeSword_Original001_R"
TARGET_PARENT_PATH = "/Game/_Art/Kazan/Material/Generated/Base/BASE_PCMetal_AK"

EXPECTED_CHAIN = (
    "CM_I_DualAxeSword_Original001V2_R",
    "BASE_PCMetal_AK",
    "BASE_Metal_AK",
    "BASE_AllMaster_AK",
    "M_AKCartoonCharacter",
)
EXPECTED_TEXTURES = {
    "Tex_D": "CT_I_DualAxeSword_Original001V2_R_D",
    "Tex_S": "CT_I_DualAxeSword_Original001V2_R_S",
    "Tex_N": "CT_I_DualAxeSword_Original001_R_N",
    "Tex_I": "CT_I_DualAxeSword_Original001_R_I",
    "Tex_R": "CT_I_DualAxeSword_Original001V2_R_R",
}


def log(message):
    unreal.log("DUALAXE_R_BUILD: " + str(message))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def collect_chain(json_index):
    records = {}
    chain = []
    current = TARGET_JSON_NAME
    while current:
        chain.append(current)
        if current == khazan.CHARACTER_MASTER_NAME:
            break
        path = json_index.get(current, "")
        require(path, "Missing hierarchy JSON: " + current)
        record = khazan.parse_json_record(current, path)
        records[current] = record
        parent = record.get("parent") or khazan.KNOWN_PARENTS.get(current, "")
        require(parent, "Hierarchy JSON has no parent: " + current)
        current = parent
    require(tuple(chain) == EXPECTED_CHAIN, "Unexpected hierarchy: " + " -> ".join(chain))
    return chain, records


def resolve_direct_texture_sources(record, png_index):
    sources = {}
    references = {}
    for parameter, expected_name in EXPECTED_TEXTURES.items():
        reference = record["textures"].get(parameter)
        require(reference, "Target JSON is missing parameter " + parameter)
        require(
            reference["name"] == expected_name,
            "{} expected {}, JSON contains {}".format(
                parameter, expected_name, reference["name"]
            ),
        )
        source = khazan.texture_file_from_object_path(reference["object_path"])
        if not source:
            candidates = sorted(
                png_index.get(expected_name, []), key=khazan.texture_candidate_score
            )
            source = candidates[0] if candidates else ""
        require(source and os.path.isfile(source), "Missing texture PNG: " + expected_name)
        sources[expected_name] = source
        references[expected_name] = [(TARGET_JSON_NAME, parameter)]
    return sources, references


def import_target_textures(sources, references):
    khazan.ensure_directory(khazan.TEXTURE_ROOT)
    tasks = []
    for texture_name, source_path in sorted(sources.items()):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source_path)
        task.set_editor_property("destination_path", khazan.TEXTURE_ROOT)
        task.set_editor_property("destination_name", texture_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", False)
        tasks.append(task)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    textures = {}
    for texture_name in sorted(sources):
        asset_path = khazan.TEXTURE_ROOT + "/" + texture_name
        texture = unreal.EditorAssetLibrary.load_asset(asset_path)
        require(
            texture and isinstance(texture, unreal.Texture2D),
            "Texture import failed: " + asset_path,
        )
        parameter = references[texture_name][0][1]
        if parameter == "Tex_D":
            texture.set_editor_property("srgb", True)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT
            )
        elif parameter == "Tex_N":
            texture.set_editor_property("srgb", False)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
            )
        else:
            texture.set_editor_property("srgb", False)
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
            )
        texture.set_editor_property("defer_compression", False)
        unreal.EditorAssetLibrary.set_metadata_tag(
            texture, "Khazan.SourcePng", sources[texture_name]
        )
        unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
        textures[texture_name] = texture
        log("texture {} <- {}".format(asset_path, sources[texture_name]))
    return textures


def build_instance(record, textures):
    parent = unreal.EditorAssetLibrary.load_asset(TARGET_PARENT_PATH)
    require(
        parent and isinstance(parent, unreal.MaterialInstanceConstant),
        "Missing generated metal parent: " + TARGET_PARENT_PATH,
    )
    instance = khazan.create_instance(TARGET_JSON_NAME, TARGET_INSTANCE_ROOT)
    khazan.reset_instance(instance, parent)
    khazan.apply_record(instance, record, textures)
    unreal.MaterialEditingLibrary.update_material_instance(instance)
    unreal.EditorAssetLibrary.set_metadata_tag(instance, "Khazan.SourceJson", record["path"])
    unreal.EditorAssetLibrary.set_metadata_tag(
        instance, "Khazan.TargetedRebuild", "DualAxeSword_Original_R"
    )
    unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)
    return instance


def assign_target_mesh(instance):
    mesh = unreal.EditorAssetLibrary.load_asset(TARGET_MESH_PATH)
    require(mesh and isinstance(mesh, unreal.SkeletalMesh), "Missing mesh: " + TARGET_MESH_PATH)
    materials = list(mesh.get_editor_property("materials"))
    require(len(materials) == 1, "Target mesh must have exactly one material slot")
    slot = materials[0]
    slot.set_editor_property("material_interface", instance)
    slot.set_editor_property("material_slot_name", unreal.Name(TARGET_SLOT_NAME))
    materials[0] = slot
    mesh.set_editor_property("materials", materials)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
    return mesh


def validate(mesh, instance, record, textures, chain):
    problems = []
    parent = instance.get_editor_property("parent")
    if not parent or parent.get_path_name().split(".", 1)[0] != TARGET_PARENT_PATH:
        problems.append("wrong material parent")

    materials = list(mesh.get_editor_property("materials"))
    if len(materials) != 1:
        problems.append("slot count is not one")
    else:
        slot = materials[0]
        interface = slot.get_editor_property("material_interface")
        if interface != instance:
            problems.append("mesh slot does not reference target instance")
        if str(slot.get_editor_property("material_slot_name")) != TARGET_SLOT_NAME:
            problems.append("mesh slot name is incorrect")

    for parameter, texture_name in EXPECTED_TEXTURES.items():
        actual = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            instance, parameter
        )
        if actual != textures[texture_name]:
            problems.append("{} is not {}".format(parameter, texture_name))
        texture = textures[texture_name]
        expected_srgb = parameter == "Tex_D"
        if bool(texture.get_editor_property("srgb")) != expected_srgb:
            problems.append(texture_name + " has wrong sRGB")
        expected_compression = {
            "Tex_D": unreal.TextureCompressionSettings.TC_DEFAULT,
            "Tex_N": unreal.TextureCompressionSettings.TC_NORMALMAP,
        }.get(parameter, unreal.TextureCompressionSettings.TC_MASKS)
        if texture.get_editor_property("compression_settings") != expected_compression:
            problems.append(texture_name + " has wrong compression")

    if problems:
        raise RuntimeError("Target validation failed: " + "; ".join(problems))
    log(
        "SUCCESS "
        + json.dumps(
            {
                "mesh": mesh.get_path_name(),
                "slot": TARGET_SLOT_NAME,
                "material": instance.get_path_name(),
                "hierarchy": chain,
                "textures": EXPECTED_TEXTURES,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main():
    require(os.path.isdir(khazan.SOURCE_ROOT), "Missing source root: " + khazan.SOURCE_ROOT)
    json_index, png_index = khazan.build_source_indices()
    chain, records = collect_chain(json_index)
    target_record = records[TARGET_JSON_NAME]
    sources, references = resolve_direct_texture_sources(target_record, png_index)
    log("hierarchy=" + " -> ".join(chain))
    log("source_json=" + target_record["path"])
    textures = import_target_textures(sources, references)
    instance = build_instance(target_record, textures)
    mesh = assign_target_mesh(instance)
    validate(mesh, instance, target_record, textures, chain)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        unreal.log_error("DUALAXE_R_BUILD: FAILED " + str(exception))
        raise
