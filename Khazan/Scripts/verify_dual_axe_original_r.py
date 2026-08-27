"""Read-only verification for the corrected right-hand Original dual axe."""

import unreal


MESH_PATH = "/Game/_Art/Kazan/Item/Original/DualAxeSword_Original_R"
INSTANCE_PATH = "/Game/_Art/Kazan/Material/Item/CM_I_DualAxeSword_Original001V2_R"
PARENT_PATH = "/Game/_Art/Kazan/Material/Generated/Base/BASE_PCMetal_AK"
SLOT_NAME = "CM_I_DualAxeSword_Original001_R"
TEXTURE_ROOT = "/Game/_Art/Kazan/Texture/Generated/"
EXPECTED = {
    "Tex_D": "CT_I_DualAxeSword_Original001V2_R_D",
    "Tex_S": "CT_I_DualAxeSword_Original001V2_R_S",
    "Tex_N": "CT_I_DualAxeSword_Original001_R_N",
    "Tex_I": "CT_I_DualAxeSword_Original001_R_I",
    "Tex_R": "CT_I_DualAxeSword_Original001V2_R_R",
}


def require(condition, message):
    if not condition:
        raise RuntimeError("DUALAXE_R_VERIFY: " + message)


mesh = unreal.load_asset(MESH_PATH)
instance = unreal.load_asset(INSTANCE_PATH)
require(mesh and isinstance(mesh, unreal.SkeletalMesh), "target mesh is missing")
require(
    instance and isinstance(instance, unreal.MaterialInstanceConstant),
    "target material instance is missing",
)

materials = list(mesh.get_editor_property("materials"))
require(len(materials) == 1, "target mesh does not have exactly one slot")
slot = materials[0]
require(str(slot.get_editor_property("material_slot_name")) == SLOT_NAME, "wrong slot name")
require(slot.get_editor_property("material_interface") == instance, "wrong slot material")

parent = instance.get_editor_property("parent")
require(parent is not None, "material parent is missing")
require(parent.get_path_name().split(".", 1)[0] == PARENT_PATH, "wrong material parent")

for parameter, texture_name in EXPECTED.items():
    expected_texture = unreal.load_asset(TEXTURE_ROOT + texture_name)
    require(expected_texture is not None, texture_name + " is missing")
    actual_texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
        instance, parameter
    )
    require(actual_texture == expected_texture, parameter + " has the wrong texture")

    expected_srgb = parameter == "Tex_D"
    require(
        bool(expected_texture.get_editor_property("srgb")) == expected_srgb,
        texture_name + " has the wrong sRGB setting",
    )
    expected_compression = {
        "Tex_D": unreal.TextureCompressionSettings.TC_DEFAULT,
        "Tex_N": unreal.TextureCompressionSettings.TC_NORMALMAP,
    }.get(parameter, unreal.TextureCompressionSettings.TC_MASKS)
    require(
        expected_texture.get_editor_property("compression_settings") == expected_compression,
        texture_name + " has the wrong compression setting",
    )

unreal.log(
    "DUALAXE_R_VERIFY: SUCCESS mesh={} slot={} material={} parent={} textures={}".format(
        mesh.get_path_name(),
        SLOT_NAME,
        instance.get_path_name(),
        parent.get_path_name(),
        EXPECTED,
    )
)
