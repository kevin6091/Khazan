"""Import the shared HeinMach/StormPass BigBear render library into Unreal.

The original cooked shader graph is unavailable, so the two generated master
materials are explicit preview adapters. Every source leaf parameter, parent
path, texture property, mesh slot and archive path remains attached as metadata.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/BigBear_20260910"
MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
DEST = MANIFEST["destination_root"]
VERSION = MANIFEST["library_version"]
MATERIAL_ADAPTER_VERSION = "20260910_BigBearPreviewV2_AllLeafParameters"
SKELETON_VERSION = "20260910_BigBearFull79BoneV1"
REPORT = PROJECT / "Saved/ImportReports/BigBear_LibraryBuild_20260910.json"
BASELINE = PROJECT / "Saved/ImportReports/BigBear_ProtectedBaseline_20260910.json"
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_baseline() -> None:
    protected = [
        "Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md",
        "Source/Khazan/Animation/KhazanAnimInstance.cpp",
        "Source/Khazan/Character/Component/KhazanLocomotionComponent.cpp",
        "Source/Khazan/Character/Component/KhazanLocomotionComponent.h",
        "Source/Khazan/Character/Locomotion/KhazanLocomotionType.cpp",
        "Source/Khazan/Character/Locomotion/KhazanLocomotionType.h",
    ]
    target = PROJECT / "Content/_Art/Enemies/Shared/Beasts/BigBear"
    data = {
        "captured_before_ue_asset_mutation": True,
        "target_uassets_before": sorted(
            str(path.relative_to(PROJECT)).replace("\\", "/")
            for path in target.rglob("*.uasset")
        )
        if target.exists()
        else [],
        "protected_files": {
            relative: sha256(PROJECT / relative) for relative in protected if (PROJECT / relative).is_file()
        },
    }
    if data["target_uassets_before"]:
        relative = data["target_uassets_before"][0]
        existing = unreal.load_asset("/Game/" + relative.removeprefix("Content/").removesuffix(".uasset"))
        if not existing:
            raise RuntimeError("BigBear target contains an unrecognized pre-existing asset")
    write(BASELINE, data)


def save(asset) -> None:
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Save failed " + asset.get_path_name())


def load(path: str):
    asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError("Missing UE asset " + path)
    return asset


def package(value) -> str | None:
    if not value:
        return None
    return value.get("ObjectPath", value.get("AssetPathName", "")).split(".", 1)[0].replace(
        "/Game/", "BBQ/Content/"
    ) or None


def asset_path(asset) -> str:
    return asset.get_path_name().split(".", 1)[0]


def clear_asset_directory(path: str) -> list[str]:
    assets = [str(value) for value in EAL.list_assets(path, recursive=True, include_folder=False)]
    if assets:
        EAL.delete_directory(path)
        remaining = [str(value) for value in EAL.list_assets(path, recursive=True, include_folder=False)]
        if remaining:
            raise RuntimeError(f"Unable to clear assets from {path}: {remaining}")
    return assets


def set_common_metadata(asset, source_package: str, role: str) -> None:
    EAL.set_metadata_tag(asset, "OriginalPackage", source_package)
    EAL.set_metadata_tag(asset, "EnemyArtRole", role)
    EAL.set_metadata_tag(asset, "EnemySourceLevels", json.dumps(MANIFEST["source_levels"]))
    EAL.set_metadata_tag(asset, "BigBearLibraryVersion", VERSION)


def new_asset(path: str, cls, factory):
    if EAL.does_asset_exist(path):
        asset = load(path)
        if EAL.get_metadata_tag(asset, "BigBearLibraryVersion") != VERSION:
            raise RuntimeError("Unrecognized existing BigBear asset " + path)
        return asset, False
    folder, name = path.rsplit("/", 1)
    asset = TOOLS.create_asset(name, folder, cls, factory)
    if not asset:
        raise RuntimeError("Create failed " + path)
    return asset, True


def import_one(source: str, destination: str, factory):
    if EAL.does_asset_exist(destination):
        asset = load(destination)
        if EAL.get_metadata_tag(asset, "BigBearLibraryVersion") != VERSION:
            raise RuntimeError("Unrecognized existing BigBear import " + destination)
        return asset, False
    folder, name = destination.rsplit("/", 1)
    task = unreal.AssetImportTask()
    for key, value in {
        "filename": source,
        "destination_path": folder,
        "destination_name": name,
        "automated": True,
        "replace_existing": False,
        "save": False,
        "factory": factory,
    }.items():
        task.set_editor_property(key, value)
    TOOLS.import_asset_tasks([task])
    asset = unreal.load_asset(destination)
    if not asset:
        raise RuntimeError(f"Import failed {source}: {task.imported_object_paths}")
    return asset, True


def expression(material, cls, **properties):
    node = MEL.create_material_expression(material, cls)
    if not node:
        raise RuntimeError("Material expression creation failed")
    for key, value in properties.items():
        node.set_editor_property(key, value)
    return node


def connect(left, output_name: str, right, input_name: str) -> None:
    if not MEL.connect_material_expressions(left, output_name, right, input_name):
        raise RuntimeError(f"Material connection failed: {output_name} -> {input_name}")


def connect_output(node, output_name: str, material_property) -> None:
    if not MEL.connect_material_property(node, output_name, material_property):
        raise RuntimeError("Material output connection failed: " + str(material_property))


def import_textures(report: dict) -> dict[str, object]:
    compression = {
        "TC_Default": unreal.TextureCompressionSettings.TC_DEFAULT,
        "TC_Normalmap": unreal.TextureCompressionSettings.TC_NORMALMAP,
        "TC_Masks": unreal.TextureCompressionSettings.TC_MASKS,
        "TC_Grayscale": unreal.TextureCompressionSettings.TC_GRAYSCALE,
        "TC_Alpha": unreal.TextureCompressionSettings.TC_ALPHA,
        "TC_BC7": unreal.TextureCompressionSettings.TC_BC7,
        "TC_HDR": unreal.TextureCompressionSettings.TC_HDR,
    }
    groups = {
        "TEXTUREGROUP_Character": unreal.TextureGroup.TEXTUREGROUP_CHARACTER,
        "TEXTUREGROUP_CharacterSpecular": unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR,
        "TEXTUREGROUP_CharacterNormalMap": unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP,
    }
    mapping = {}
    for index, row in enumerate(MANIFEST["textures"], 1):
        source_file = pathlib.Path(row["source_file"])
        if not source_file.is_file():
            raise RuntimeError("Missing source texture " + str(source_file))
        texture, created = import_one(str(source_file), row["destination"], unreal.TextureFactory())
        properties = row["properties"]
        texture.set_editor_property("srgb", properties.get("SRGB", True))
        key = properties.get("CompressionSettings", "TC_Default").split("::")[-1]
        if key in compression:
            texture.set_editor_property("compression_settings", compression[key])
        group = properties.get("LODGroup", "").split("::")[-1]
        if group in groups:
            texture.set_editor_property("lod_group", groups[group])
        set_common_metadata(texture, row["source_package"], "SourceTexture")
        EAL.set_metadata_tag(texture, "OriginalPropertiesJSON", json.dumps(properties, ensure_ascii=False))
        EAL.set_metadata_tag(
            texture,
            "SourceCookedPayloadSizeJSON",
            json.dumps({"X": row["source_object"]["SizeX"], "Y": row["source_object"]["SizeY"]}),
        )
        EAL.set_metadata_tag(
            texture,
            "TextureResolutionContract",
            "UE pixels reproduce the exported cooked SizeX/SizeY payload; ImportedSize remains source authoring metadata.",
        )
        save(texture)
        mapping[row["source_package"]] = texture
        report["textures"].append(
            {
                "source": row["source_package"],
                "asset": asset_path(texture),
                "created": created,
                "size": [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()],
                "srgb": texture.get_editor_property("srgb"),
                "compression": str(texture.get_editor_property("compression_settings")),
                "lod_group": str(texture.get_editor_property("lod_group")),
            }
        )
        if index % 10 == 0 or index == len(MANIFEST["textures"]):
            print("BIG_BEAR_TEXTURE", index, "/", len(MANIFEST["textures"]), flush=True)
    return mapping


def collect_parameters(category: str, texture_map: dict[str, object]):
    scalars = {}
    vectors = {}
    textures = {}
    for row in MANIFEST["materials"]:
        if row["category"] != category:
            continue
        properties = row["source_object"].get("Properties", {})
        for value in properties.get("ScalarParameterValues", []):
            scalars.setdefault(value["ParameterInfo"]["Name"], value["ParameterValue"])
        for value in properties.get("VectorParameterValues", []):
            vectors.setdefault(value["ParameterInfo"]["Name"], value["ParameterValue"])
        for value in properties.get("TextureParameterValues", []):
            source_package = package(value.get("ParameterValue"))
            if source_package in texture_map:
                textures.setdefault(value["ParameterInfo"]["Name"], texture_map[source_package])
    return scalars, vectors, textures


def build_master(category: str, texture_map: dict[str, object], report: dict):
    name = "M_EN_BigBear_EyePreview" if category == "Eye" else "M_EN_BigBear_SurfacePreview"
    path = f"{DEST}/Materials/Masters/{name}"
    if EAL.does_asset_exist(path):
        existing = load(path)
        if EAL.get_metadata_tag(existing, "BigBearMaterialAdapterVersion") != MATERIAL_ADAPTER_VERSION:
            if not EAL.delete_asset(path):
                raise RuntimeError("Unable to replace incomplete preview master " + path)
    master, created = new_asset(path, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        report["masters"].append({"asset": path, "created": False, "category": category})
        return master

    master.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    master.set_editor_property("opacity_mask_clip_value", 0.3333)
    MEL.set_material_usage(master, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    scalars, vectors, textures = collect_parameters(category, texture_map)
    scalar_nodes = {
        name: expression(
            master,
            unreal.MaterialExpressionScalarParameter,
            parameter_name=name,
            default_value=float(value),
        )
        for name, value in scalars.items()
    }
    vector_nodes = {
        name: expression(
            master,
            unreal.MaterialExpressionVectorParameter,
            parameter_name=name,
            default_value=unreal.LinearColor(value["R"], value["G"], value["B"], value.get("A", 1.0)),
        )
        for name, value in vectors.items()
    }
    texture_nodes = {}
    for parameter_name, texture in textures.items():
        node = expression(
            master,
            unreal.MaterialExpressionTextureSampleParameter2D,
            parameter_name=parameter_name,
            texture=texture,
        )
        if texture.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_NORMALMAP:
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
        elif texture.get_editor_property("srgb"):
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
        else:
            sampler = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        node.set_editor_property("sampler_type", sampler)
        texture_nodes[parameter_name] = node

    one = expression(master, unreal.MaterialExpressionConstant, r=1.0)
    connect_output(one, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    if category == "Eye":
        required = ["EyeWhiteColor0", "Pupil_Circle0"]
        if not all(name in vector_nodes for name in required) or "Tex_E" not in texture_nodes:
            raise RuntimeError("Eye preview adapter is missing source parameters")
        blend = expression(master, unreal.MaterialExpressionLinearInterpolate)
        connect(vector_nodes["EyeWhiteColor0"], "", blend, "A")
        connect(vector_nodes["Pupil_Circle0"], "", blend, "B")
        connect(texture_nodes["Tex_E"], "R", blend, "Alpha")
        base_color = blend
        if "SpeculaBrightness" in scalar_nodes:
            connect_output(scalar_nodes["SpeculaBrightness"], "", unreal.MaterialProperty.MP_SPECULAR)
    else:
        for required in ["Tex_D", "Tex_N", "Tex_S"]:
            if required not in texture_nodes:
                raise RuntimeError("Surface preview adapter is missing " + required)
        base_color = texture_nodes["Tex_D"]
        connect_output(texture_nodes["Tex_D"], "A", unreal.MaterialProperty.MP_OPACITY_MASK)
        connect_output(texture_nodes["Tex_N"], "RGB", unreal.MaterialProperty.MP_NORMAL)
        inverse = expression(master, unreal.MaterialExpressionOneMinus)
        connect(texture_nodes["Tex_S"], "G", inverse, "None")
        connect_output(inverse, "", unreal.MaterialProperty.MP_ROUGHNESS)
        connect_output(texture_nodes["Tex_S"], "R", unreal.MaterialProperty.MP_SPECULAR)

    # Keep every source leaf parameter addressable on the generated instances.
    # The aggregate is multiplied by exact zero before it joins Base Color, so
    # it changes no rendered value while remaining part of the material graph.
    preserved = list(scalar_nodes.values()) + list(vector_nodes.values()) + list(texture_nodes.values())
    aggregate = preserved[0]
    for node in preserved[1:]:
        add = expression(master, unreal.MaterialExpressionAdd)
        connect(aggregate, "", add, "A")
        connect(node, "", add, "B")
        aggregate = add
    zero = expression(master, unreal.MaterialExpressionConstant, r=0.0)
    hidden = expression(master, unreal.MaterialExpressionMultiply)
    connect(aggregate, "", hidden, "A")
    connect(zero, "", hidden, "B")
    final_color = expression(master, unreal.MaterialExpressionAdd)
    connect(base_color, "", final_color, "A")
    connect(hidden, "", final_color, "B")
    connect_output(final_color, "", unreal.MaterialProperty.MP_BASE_COLOR)

    set_common_metadata(master, "GeneratedPreviewAdapter/" + category, "PreviewMaterialMaster")
    EAL.set_metadata_tag(
        master,
        "ShaderFidelity",
        "Explicit UE preview adapter; original cooked BBQ shader topology is unavailable",
    )
    EAL.set_metadata_tag(
        master,
        "SourceBaseProperty",
        "BLEND_Masked; OpacityMaskClipValue=0.3333 from BASE_AllMaster_AK/Base_Eyes_AK",
    )
    EAL.set_metadata_tag(master, "BigBearMaterialAdapterVersion", MATERIAL_ADAPTER_VERSION)
    MEL.recompile_material(master)
    save(master)
    report["masters"].append({"asset": path, "created": True, "category": category})
    return master


def build_materials(texture_map: dict[str, object], report: dict) -> dict[str, object]:
    masters = {
        "Surface": build_master("Surface", texture_map, report),
        "Eye": build_master("Eye", texture_map, report),
    }
    mapping = {}
    for row in MANIFEST["materials"]:
        material, created = new_asset(
            row["destination"], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew()
        )
        MEL.set_material_instance_parent(material, masters[row["category"]])
        properties = row["source_object"].get("Properties", {})
        for value in properties.get("ScalarParameterValues", []):
            parameter_name = value["ParameterInfo"]["Name"]
            expected = float(value["ParameterValue"])
            MEL.set_material_instance_scalar_parameter_value(material, parameter_name, expected)
            actual = MEL.get_material_instance_scalar_parameter_value(material, parameter_name)
            if abs(actual - expected) > 1e-6:
                raise RuntimeError(
                    f"Scalar parameter {parameter_name} failed in {row['destination']}: {actual} != {expected}"
                )
        for value in properties.get("VectorParameterValues", []):
            color = value["ParameterValue"]
            parameter_name = value["ParameterInfo"]["Name"]
            expected = unreal.LinearColor(color["R"], color["G"], color["B"], color.get("A", 1.0))
            MEL.set_material_instance_vector_parameter_value(
                material,
                parameter_name,
                expected,
            )
            actual = MEL.get_material_instance_vector_parameter_value(material, parameter_name)
            if max(abs(actual.r - expected.r), abs(actual.g - expected.g), abs(actual.b - expected.b), abs(actual.a - expected.a)) > 1e-6:
                raise RuntimeError("Vector parameter failed in " + row["destination"] + ": " + parameter_name)
        bindings = {}
        for value in properties.get("TextureParameterValues", []):
            source_package = package(value.get("ParameterValue"))
            if source_package not in texture_map:
                raise RuntimeError("Missing material texture " + str(source_package))
            parameter_name = value["ParameterInfo"]["Name"]
            MEL.set_material_instance_texture_parameter_value(material, parameter_name, texture_map[source_package])
            actual = MEL.get_material_instance_texture_parameter_value(material, parameter_name)
            if asset_path(actual) != asset_path(texture_map[source_package]):
                raise RuntimeError("Texture parameter failed in " + row["destination"] + ": " + parameter_name)
            bindings[parameter_name] = asset_path(texture_map[source_package])
        MEL.update_material_instance(material)
        set_common_metadata(material, row["source_package"], "ReconstructedMaterialInstance")
        EAL.set_metadata_tag(material, "OriginalParentPackage", row["source_parent"] or "")
        EAL.set_metadata_tag(material, "OriginalPropertiesJSON", json.dumps(properties, ensure_ascii=False))
        EAL.set_metadata_tag(
            material,
            "ShaderFidelity",
            "Source leaf parameters restored on explicit UE preview adapter; proprietary graph unavailable",
        )
        save(material)
        mapping[row["source_package"]] = material
        report["materials"].append(
            {
                "source": row["source_package"],
                "asset": row["destination"],
                "created": created,
                "category": row["category"],
                "source_parent": row["source_parent"],
                "texture_bindings": bindings,
            }
        )
    return mapping


def import_mesh(material_map: dict[str, object], report: dict):
    row = MANIFEST["body"]
    destination = row["destination"]
    skeleton_destination = row["skeleton_destination"]
    staging_root = DEST + "/_ImportStaging79V1"
    upgrade_root = DEST + "/_UpgradeBackup"
    upgraded_from_partial_skeleton = False
    if EAL.does_asset_exist(destination):
        mesh = load(destination)
        if EAL.get_metadata_tag(mesh, "BigBearSkeletonVersion") != SKELETON_VERSION:
            if EAL.get_metadata_tag(mesh, "BigBearLibraryVersion") != VERSION:
                raise RuntimeError("Unrecognized existing BigBear mesh")
            for temporary_root in [staging_root, upgrade_root]:
                clear_asset_directory(temporary_root)
            backup_mesh = upgrade_root + "/SK_EN_BigBear_71Bone"
            backup_skeleton = upgrade_root + "/SKEL_EN_BigBear_71Bone"
            if not EAL.rename_asset(destination, backup_mesh):
                raise RuntimeError("Unable to stage the partial BigBear mesh for replacement")
            if EAL.does_asset_exist(skeleton_destination) and not EAL.rename_asset(
                skeleton_destination, backup_skeleton
            ):
                raise RuntimeError("Unable to stage the partial BigBear skeleton for replacement")
            mesh = None
            upgraded_from_partial_skeleton = True
        else:
            created = False
    else:
        mesh = None
    if mesh is None:
        # A prior interrupted upgrade may have left a valid-looking but
        # unversioned staging import. Recreate it from the deterministic PSK.
        clear_asset_directory(staging_root)
        source_file = pathlib.Path(row["source_file"])
        if not source_file.is_file():
            raise RuntimeError("Missing full-skeleton BigBear PSK " + str(source_file))
        factory_class = unreal.load_class(None, "/Script/UnrealPSKPSA.PSKFactory")
        if not factory_class:
            raise RuntimeError("Project UnrealPSKPSA importer is unavailable")
        staging = staging_root + "/SK_EN_BigBear_Full79V1"
        mesh, created = import_one(str(source_file), staging, unreal.new_object(factory_class))
        skeleton = mesh.get_editor_property("skeleton")
        save(skeleton)
        save(mesh)
        if not EAL.rename_asset(staging, destination):
            raise RuntimeError("BigBear mesh relocation failed")
        mesh = load(destination)
        skeleton = mesh.get_editor_property("skeleton")
        current_skeleton = asset_path(skeleton)
        if current_skeleton != skeleton_destination:
            if EAL.does_asset_exist(skeleton_destination):
                raise RuntimeError("Unexpected pre-existing BigBear skeleton")
            if not EAL.rename_asset(current_skeleton, skeleton_destination):
                raise RuntimeError("BigBear skeleton relocation failed")
            skeleton = load(skeleton_destination)
            mesh.skeleton = skeleton
    skeleton = load(skeleton_destination)
    mesh.skeleton = skeleton
    slots = list(mesh.get_editor_property("materials"))
    if len(slots) != len(row["materials"]):
        raise RuntimeError(f"BigBear slot count {len(slots)} != {len(row['materials'])}")
    for index, (slot, source_material) in enumerate(zip(slots, row["materials"])):
        if source_material not in material_map:
            raise RuntimeError("Missing BigBear material " + source_material)
        slot.set_editor_property("material_interface", material_map[source_material])
        slot.set_editor_property("material_slot_name", row["source_slot_names"][index])
    mesh.set_editor_property("materials", slots)
    skeleton.set_skeleton_preview_mesh(mesh)
    set_common_metadata(mesh, row["source_package"], "SkeletalMesh")
    set_common_metadata(skeleton, row["source_skeleton"], "Skeleton")
    EAL.set_metadata_tag(mesh, "SourceBoundsJSON", json.dumps(row["bounds"], ensure_ascii=False))
    EAL.set_metadata_tag(mesh, "SourceLODArchive", json.dumps(row["lod_files"], ensure_ascii=False))
    EAL.set_metadata_tag(mesh, "SourceLODCount", str(row["source_lod_count"]))
    EAL.set_metadata_tag(mesh, "ImportedLODCount", "1")
    EAL.set_metadata_tag(mesh, "SourceMorphTargetNames", json.dumps(row["morph_targets"]))
    EAL.set_metadata_tag(mesh, "BigBearSkeletonVersion", SKELETON_VERSION)
    EAL.set_metadata_tag(skeleton, "BigBearSkeletonVersion", SKELETON_VERSION)
    EAL.set_metadata_tag(
        skeleton,
        "SkeletonDerivationJSON",
        json.dumps(
            {
                key: row[key]
                for key in [
                    "original_source_file",
                    "mesh_reference_bones",
                    "animation_reference_bones",
                    "added_unweighted_animation_bones",
                    "derivation",
                    "animation_layout_files_verified",
                ]
            },
            ensure_ascii=False,
        ),
    )
    save(skeleton)
    save(mesh)

    staging_assets = clear_asset_directory(staging_root)
    legacy_staging_assets = clear_asset_directory(DEST + "/_ImportStaging")
    upgrade_assets = clear_asset_directory(upgrade_root)
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    report["mesh"] = {
        "source": row["source_package"],
        "asset": destination,
        "skeleton": skeleton_destination,
        "created": created,
        "upgraded_from_partial_skeleton": upgraded_from_partial_skeleton,
        "material_slots": [str(slot.material_slot_name) for slot in slots],
        "lod0_vertices": subsystem.get_num_verts(mesh, 0),
        "source_lod_count": row["source_lod_count"],
        "imported_lod_count": subsystem.get_lod_count(mesh),
        "mesh_reference_bones": row["mesh_reference_bones"],
        "animation_reference_bones": row["animation_reference_bones"],
        "added_unweighted_animation_bones": row["added_unweighted_animation_bones"],
        "source_lod_sha256": {str(path): sha256(pathlib.Path(path)) for path in row["lod_files"]},
        "removed_staging_assets": staging_assets,
        "removed_legacy_staging_assets": legacy_staging_assets,
        "removed_upgrade_assets": upgrade_assets,
    }
    return mesh, skeleton


def main() -> None:
    report = {"status": "running", "version": VERSION, "textures": [], "masters": [], "materials": []}
    try:
        capture_baseline()
        texture_map = import_textures(report)
        material_map = build_materials(texture_map, report)
        import_mesh(material_map, report)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        write(REPORT, report)
    print("BIG_BEAR_LIBRARY_BUILD_PASSED", flush=True)


if __name__ == "__main__":
    main()
