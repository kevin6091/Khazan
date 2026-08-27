"""Independent Unreal-side validation for the generated Khazan materials."""

import math
import os
import sys
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import build_khazan_materials as build


def log(message):
    unreal.log("KHAZAN_VERIFY: " + str(message))


def fail(message):
    raise RuntimeError(message)


def close(a, b, tolerance=0.0002):
    return math.isclose(float(a), float(b), abs_tol=tolerance, rel_tol=tolerance)


def asset_path(asset):
    return asset.get_path_name() if asset else "None"


def expected_parent_name(target, record):
    if target == build.EYE_SHADOW_NAME:
        return build.EYE_SHADOW_MASTER_NAME
    return record.get("parent") or build.infer_target_parent(target)


def check_master_inputs(master):
    properties = (
        unreal.MaterialProperty.MP_BASE_COLOR,
        unreal.MaterialProperty.MP_NORMAL,
        unreal.MaterialProperty.MP_ROUGHNESS,
        unreal.MaterialProperty.MP_METALLIC,
        unreal.MaterialProperty.MP_SPECULAR,
        unreal.MaterialProperty.MP_EMISSIVE_COLOR,
        unreal.MaterialProperty.MP_OPACITY_MASK,
    )
    for material_property in properties:
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(
            master, material_property
        )
        if not node:
            fail("Character master input is disconnected: {}".format(material_property))


def check_texture_settings(texture_name, texture, references):
    if build.is_normal_texture(texture_name, references):
        if texture.get_editor_property("srgb"):
            fail("Normal texture is sRGB: " + texture.get_path_name())
        if texture.get_editor_property("compression_settings") != unreal.TextureCompressionSettings.TC_NORMALMAP:
            fail("Normal texture compression is wrong: " + texture.get_path_name())
    elif build.is_color_texture(references):
        if not texture.get_editor_property("srgb"):
            fail("Diffuse texture is not sRGB: " + texture.get_path_name())
        if texture.get_editor_property("compression_settings") != unreal.TextureCompressionSettings.TC_DEFAULT:
            fail("Diffuse texture compression is wrong: " + texture.get_path_name())
    else:
        if texture.get_editor_property("srgb"):
            fail("Data texture is sRGB: " + texture.get_path_name())
        if texture.get_editor_property("compression_settings") != unreal.TextureCompressionSettings.TC_MASKS:
            fail("Data texture compression is wrong: " + texture.get_path_name())


def check_record_parameters(instance, record, available_texture_names):
    for parameter, reference in record["textures"].items():
        if reference["name"] not in available_texture_names:
            continue
        actual = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
            instance, parameter
        )
        if not actual or actual.get_name() != reference["name"]:
            fail(
                "{} texture {} expected {}, got {}".format(
                    instance.get_path_name(), parameter, reference["name"], asset_path(actual)
                )
            )
    for parameter, expected in record["scalars"].items():
        if not build.valid_parameter_name(parameter):
            continue
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            instance, parameter
        )
        if not close(actual, expected):
            fail(
                "{} scalar {} expected {}, got {}".format(
                    instance.get_path_name(), parameter, expected, actual
                )
            )
    for parameter, expected in record["vectors"].items():
        if not build.valid_parameter_name(parameter):
            continue
        actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
            instance, parameter
        )
        actual_tuple = (actual.r, actual.g, actual.b, actual.a)
        if any(not close(a, b) for a, b in zip(actual_tuple, expected)):
            fail(
                "{} vector {} expected {}, got {}".format(
                    instance.get_path_name(), parameter, expected, actual_tuple
                )
            )


def main():
    json_index, png_index = build.build_source_indices()
    meshes, _ = build.collect_project_assets()
    targets = build.mesh_material_targets(meshes)
    records = build.collect_records(targets, json_index)
    sources, references_by_texture = build.resolve_texture_sources(
        records, targets, png_index
    )

    master = unreal.load_asset(
        build.MASTER_ROOT + "/" + build.CHARACTER_MASTER_NAME
    )
    if not master or not isinstance(master, unreal.Material):
        fail("Character master is missing")
    if master.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_MASKED:
        fail("Character master is not Masked")
    if not master.get_editor_property("two_sided"):
        fail("Character master is not two-sided")
    check_master_inputs(master)
    unreal.MaterialEditingLibrary.recompile_material(master)

    shadow_master = unreal.load_asset(
        build.MASTER_ROOT + "/" + build.EYE_SHADOW_MASTER_NAME
    )
    if not shadow_master or not isinstance(shadow_master, unreal.Material):
        fail("Eye shadow master is missing")
    if shadow_master.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_TRANSLUCENT:
        fail("Eye shadow master is not Translucent")
    unreal.MaterialEditingLibrary.recompile_material(shadow_master)

    textures = {}
    for texture_name in sorted(sources):
        texture = unreal.load_asset(build.TEXTURE_ROOT + "/" + texture_name)
        if not texture or not isinstance(texture, unreal.Texture2D):
            fail("Texture asset is missing: " + texture_name)
        check_texture_settings(
            texture_name, texture, references_by_texture.get(texture_name, [])
        )
        textures[texture_name] = texture

    slot_count = 0
    checked_instances = set()
    parent_counts = {}
    for mesh in meshes:
        for skeletal_material in mesh.get_editor_property("materials"):
            slot_name = str(skeletal_material.get_editor_property("material_slot_name"))
            if slot_name not in targets:
                continue
            slot_count += 1
            instance = skeletal_material.get_editor_property("material_interface")
            if not instance or not isinstance(instance, unreal.MaterialInstanceConstant):
                fail("{} slot {} has no MIC".format(mesh.get_path_name(), slot_name))
            if instance.get_name() != slot_name:
                fail(
                    "{} slot {} references {}".format(
                        mesh.get_path_name(), slot_name, instance.get_path_name()
                    )
                )
            expected_parent = expected_parent_name(slot_name, records[slot_name])
            parent = instance.get_editor_property("parent")
            if not parent or parent.get_name() != expected_parent:
                fail(
                    "{} expected parent {}, got {}".format(
                        instance.get_path_name(), expected_parent, asset_path(parent)
                    )
                )
            parent_counts[expected_parent] = parent_counts.get(expected_parent, 0) + 1
            if instance.get_path_name() not in checked_instances:
                check_record_parameters(instance, records[slot_name], set(textures))
                checked_instances.add(instance.get_path_name())

    if slot_count != 36:
        fail("Expected 36 skeletal material slots, found {}".format(slot_count))
    if len(targets) != 26:
        fail("Expected 26 unique material names, found {}".format(len(targets)))

    # Verify the key category controls that replace the unavailable custom
    # MSM_BBQCartoon shading model.
    category_expectations = {
        "Base_Eyes_AK": ("UseEyeTexture", 1.0),
        "Base_Ghost_AK": ("UseGhostLook", 1.0),
        "BASE_Metal_AK": ("UseSpecularAsMetallic", 1.0),
        "BASE_Skin_AK": ("MetallicStrength", 0.0),
        "BASE_Hair_AK": ("RoughnessScale", 0.55),
    }
    for base_name, (parameter, expected) in category_expectations.items():
        instance = unreal.load_asset(build.BASE_ROOT + "/" + base_name)
        if not instance:
            fail("Generated base instance is missing: " + base_name)
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            instance, parameter
        )
        if not close(actual, expected):
            fail(
                "{} {} expected {}, got {}".format(base_name, parameter, expected, actual)
            )

    log(
        "SUCCESS meshes={} slots={} targets={} checked_instances={} textures={} parents={}".format(
            len(meshes),
            slot_count,
            len(targets),
            len(checked_instances),
            len(textures),
            parent_counts,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        unreal.log_error("KHAZAN_VERIFY: " + str(exception))
        unreal.log_error("KHAZAN_VERIFY: " + traceback.format_exc())
        raise

