"""Fresh-process audit and preview catalogue for the shared Yetuga library."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
CONTENT_ROOT = PROJECT / "Content/_Art/Enemies/HeinMach/Bosses/Yetuga"
META = CONTENT_ROOT / "Metadata/Extraction_20260911"
MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
ANIMATIONS = json.loads((ROOT / "AnimationImportManifest.json").read_text(encoding="utf-8"))
CATALOG = json.loads((META / "YetugaAssemblyCatalog.json").read_text(encoding="utf-8"))
EVENTS = json.loads((META / "PlaybackEventTimes.json").read_text(encoding="utf-8"))["events"]
ANIMATION_IMPORT_AUDIT = json.loads(
    (PROJECT / "Saved/ImportReports/Yetuga_AnimationImportAudit_20260911.json").read_text(encoding="utf-8")
)
sys.path.insert(0, str(PROJECT / "Saved/ArtTools/EnemyPython"))
import numpy as np


DEST = MANIFEST["destination_root"]
MESH_PATH = MANIFEST["body"]["destination"]
SKELETON_PATH = MANIFEST["body"]["skeleton_destination"]
MAP_PATH = DEST + "/Preview/L_EN_Yetuga_Catalogue"
REPORT = PROJECT / "Saved/ImportReports/Yetuga_FreshAudit_20260911.json"
SUMMARY = META / "ValidationSummary.json"
TIMING_VERSION = "20260911_Yetuga_SourceCompositePlaybackV2_RootLockPropagation"
ASSEMBLY_VERSION = "20260911_YetugaVisualAssemblyV1"
MATERIAL_ADAPTER_VERSION = "20260911_YetugaPreviewV4_BoundedParameterRetention"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
MESH_EDITOR = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
HELPER_BONES = set(MANIFEST["body"]["added_unweighted_animation_bones"])


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load(path: str):
    asset = unreal.load_asset(path)
    check(asset is not None, "Missing UE asset " + path)
    return asset


def asset_path(value) -> str | None:
    return value.get_path_name().split(".", 1)[0] if value else None


def source_package(value) -> str | None:
    if not value:
        return None
    return value.get("ObjectPath", value.get("AssetPathName", "")).split(".", 1)[0].replace(
        "/Game/", "BBQ/Content/"
    ) or None


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_catalogue(report: dict) -> None:
    if EAL.does_asset_exist(MAP_PATH):
        check(LEVELS.load_level(MAP_PATH), "Unable to load Yetuga catalogue")
    else:
        check(LEVELS.new_level(MAP_PATH), "Unable to create Yetuga catalogue")

    existing = {actor.get_actor_label(): actor for actor in ACTORS.get_all_level_actors()}
    spacing_cm = 650.0
    for index, row in enumerate(CATALOG):
        label = row["asset"].rsplit("/", 1)[1]
        actor = existing.get(label)
        if actor is None:
            actor = ACTORS.spawn_actor_from_class(
                EAL.load_blueprint_class(row["asset"]),
                unreal.Vector(0.0, index * spacing_cm, 0.0),
            )
        check(actor is not None, "Unable to place " + label)
        actor.set_actor_label(label)
        actor.set_folder_path("EnemyCatalogue/Yetuga")

    if "YetugaCatalogue_KeyLight" not in existing:
        key = ACTORS.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(-300.0, 0.0, 700.0),
            unreal.Rotator(pitch=-40.0, yaw=-35.0, roll=0.0),
        )
        key.set_actor_label("YetugaCatalogue_KeyLight")
        key.set_folder_path("PreviewOnly")
        key.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(3.0)

        fill = ACTORS.spawn_actor_from_class(
            unreal.DirectionalLight,
            unreal.Vector(300.0, 0.0, 500.0),
            unreal.Rotator(pitch=-25.0, yaw=145.0, roll=0.0),
        )
        fill.set_actor_label("YetugaCatalogue_FillLight")
        fill.set_folder_path("PreviewOnly")
        fill.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(1.0)

        floor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, -10.0))
        floor.set_actor_label("YetugaCatalogue_Floor")
        floor.set_folder_path("PreviewOnly")
        floor.static_mesh_component.set_static_mesh(load("/Engine/BasicShapes/Cube"))
        floor.set_actor_scale3d(unreal.Vector(20.0, 20.0, 0.1))
        floor.static_mesh_component.set_material(0, load("/Engine/EngineMaterials/DefaultMaterial"))

        camera = ACTORS.spawn_actor_from_class(
            unreal.CameraActor,
            unreal.Vector(-1400.0, 0.0, 320.0),
            unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0),
        )
        camera.set_actor_label("YetugaCatalogue_Camera")
        camera.set_folder_path("PreviewOnly")
        camera.get_component_by_class(unreal.CameraComponent).set_editor_property("field_of_view", 70.0)

    if "Yetuga_IceRock_Preview" not in existing:
        prop = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0.0, 500.0, 110.1))
        prop.set_actor_label("Yetuga_IceRock_Preview")
        prop.set_folder_path("EnemyCatalogue/Yetuga")
        component = prop.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_skinned_asset_and_update(load(MANIFEST["prop_preview"]["mesh"]))
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        anim = component.get_editor_property("animation_data")
        anim.set_editor_property("anim_to_play", load(MANIFEST["prop_preview"]["idle_asset"]))
        anim.set_editor_property("saved_looping", True)
        anim.set_editor_property("saved_playing", True)
        anim.set_editor_property("saved_play_rate", 1.0)
        component.set_editor_property("animation_data", anim)
    check(LEVELS.save_current_level(), "Unable to save Yetuga catalogue")
    report["catalogue_map"] = MAP_PATH
    report["preview_settings"] = {
        "source_status": "Assistant-selected presentation values; not original gameplay metadata.",
        "spacing_cm": spacing_cm,
        "directional_light_intensities": [3.0, 1.0],
        "camera_fov_degrees": 70.0,
    }


def verify_textures(report: dict) -> None:
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
        "TEXTUREGROUP_WorldNormalMap": unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP,
        "TEXTUREGROUP_WorldSpecular": unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR,
        "TEXTUREGROUP_Effects": unreal.TextureGroup.TEXTUREGROUP_EFFECTS,
        "TEXTUREGROUP_CharacterSpecular": unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR,
        "TEXTUREGROUP_CharacterNormalMap": unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP,
    }
    authoring_size_differs = []
    for row in MANIFEST["textures"]:
        texture = load(row["destination"])
        check(isinstance(texture, unreal.Texture2D), "Texture type mismatch " + row["destination"])
        properties = row["properties"]
        size = {"X": row["source_object"]["SizeX"], "Y": row["source_object"]["SizeY"]}
        check(
            [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()] == [size["X"], size["Y"]],
            "Texture size mismatch " + row["destination"],
        )
        check(
            json.loads(EAL.get_metadata_tag(texture, "SourceCookedPayloadSizeJSON")) == size,
            "Cooked payload metadata mismatch " + row["destination"],
        )
        if properties.get("ImportedSize") != size:
            authoring_size_differs.append(
                {
                    "asset": row["destination"],
                    "source_imported_size": properties.get("ImportedSize"),
                    "source_cooked_payload_size": size,
                }
            )
        check(texture.get_editor_property("srgb") == properties.get("SRGB", True), "sRGB mismatch " + row["destination"])
        compression_key = properties.get("CompressionSettings", "TC_Default").split("::")[-1]
        if compression_key in compression:
            check(
                texture.get_editor_property("compression_settings") == compression[compression_key],
                "Compression mismatch " + row["destination"],
            )
        group_key = properties.get("LODGroup", "").split("::")[-1]
        if group_key in groups:
            check(texture.get_editor_property("lod_group") == groups[group_key], "LOD group mismatch " + row["destination"])
        check(EAL.get_metadata_tag(texture, "OriginalPackage") == row["source_package"], "Texture provenance mismatch")
        saved_properties = json.loads(EAL.get_metadata_tag(texture, "OriginalPropertiesJSON"))
        check(saved_properties == properties, "Texture metadata mismatch " + row["destination"])
    report["textures_verified"] = len(MANIFEST["textures"])
    report["texture_resolution_contract"] = {
        "ue_uses_source_cooked_payload_size": True,
        "authoring_imported_size_differs": authoring_size_differs,
    }


def verify_materials(report: dict) -> None:
    texture_paths = {row["source_package"]: row["destination"] for row in MANIFEST["textures"]}
    master_paths = {
        "Surface": DEST + "/Materials/Masters/M_EN_Yetuga_SurfacePreview",
        "Eye": DEST + "/Materials/Masters/M_EN_Yetuga_EyePreview",
        "Prop": DEST + "/Materials/Masters/M_EN_Yetuga_PropPreview",
    }
    for path in master_paths.values():
        master = load(path)
        check(isinstance(master, unreal.Material), "Preview master type mismatch " + path)
        check(EAL.get_metadata_tag(master, "YetugaMaterialAdapterVersion") == MATERIAL_ADAPTER_VERSION, "Master version " + path)
        check(
            EAL.get_metadata_tag(master, "ShaderFidelity")
            == "Explicit UE preview adapter; original cooked BBQ shader topology is unavailable",
            "Master fidelity tag " + path,
        )

    material_paths = {row["source_package"]: row["destination"] for row in MANIFEST["materials"]}
    scalar_parameters = 0
    vector_parameters = 0
    texture_parameters = 0
    for row in MANIFEST["materials"]:
        material = load(row["destination"])
        check(isinstance(material, unreal.MaterialInstanceConstant), "Material type mismatch " + row["destination"])
        check(asset_path(material.get_editor_property("parent")) == material_paths.get(row["source_parent"], master_paths[row["category"]]), "Material parent mismatch " + row["destination"])
        check(EAL.get_metadata_tag(material, "OriginalParentPackage") == (row["source_parent"] or ""), "Source parent metadata mismatch")
        properties = row["effective_properties"]
        check(json.loads(EAL.get_metadata_tag(material, "OriginalPropertiesJSON")) == row["source_object"].get("Properties", {}), "Material metadata mismatch " + row["destination"])
        check(json.loads(EAL.get_metadata_tag(material, "EffectivePropertiesJSON")) == properties, "Effective material metadata mismatch")
        actual_base = material.get_editor_property("base_property_overrides")
        source_base = properties.get("BasePropertyOverrides", {})
        if "TwoSided" in source_base:
            check(actual_base.get_editor_property("override_two_sided") and actual_base.get_editor_property("two_sided") == source_base["TwoSided"], "Two-sided source override mismatch")
        if "OpacityMaskClipValue" in source_base:
            check(actual_base.get_editor_property("override_opacity_mask_clip_value") and abs(actual_base.get_editor_property("opacity_mask_clip_value") - source_base["OpacityMaskClipValue"]) < 1e-6, "Opacity mask source override mismatch")
        for value in properties.get("ScalarParameterValues", []):
            name = value["ParameterInfo"]["Name"]
            actual = MEL.get_material_instance_scalar_parameter_value(material, name)
            check(abs(actual - float(value["ParameterValue"])) <= max(1e-6, abs(float(value["ParameterValue"])) * 1e-6), "Scalar mismatch " + row["destination"] + " " + name)
            scalar_parameters += 1
        for value in properties.get("VectorParameterValues", []):
            name = value["ParameterInfo"]["Name"]
            expected = value["ParameterValue"]
            actual = MEL.get_material_instance_vector_parameter_value(material, name)
            error = max(
                abs(actual.r - expected["R"]),
                abs(actual.g - expected["G"]),
                abs(actual.b - expected["B"]),
                abs(actual.a - expected.get("A", 1.0)),
            )
            check(error <= max(1e-6, max(abs(expected[k]) for k in ["R","G","B","A"])*1e-6), "Vector mismatch " + row["destination"] + " " + name)
            vector_parameters += 1
        for value in properties.get("TextureParameterValues", []):
            name = value["ParameterInfo"]["Name"]
            expected = texture_paths[source_package(value.get("ParameterValue"))]
            actual = MEL.get_material_instance_texture_parameter_value(material, name)
            check(asset_path(actual) == expected, "Texture parameter mismatch " + row["destination"] + " " + name)
            texture_parameters += 1
    report["materials_verified"] = len(MANIFEST["materials"])
    report["material_parameters_verified"] = {
        "scalar": scalar_parameters,
        "vector": vector_parameters,
        "texture": texture_parameters,
    }
    report["preview_masters_verified"] = len(master_paths)


def verify_mesh(report):
    verified = []
    for row in MANIFEST["meshes"]:
        mesh, skeleton = load(row["destination"]), load(row["skeleton_destination"])
        check(mesh.skeleton == skeleton, "Mesh skeleton mismatch")
        slots = list(mesh.get_editor_property("materials"))
        check([str(slot.material_slot_name) for slot in slots] == row["source_slot_names"], "Mesh slot names mismatch")
        mats = {m["source_package"]: m["destination"] for m in MANIFEST["materials"]}
        check([asset_path(slot.material_interface) for slot in slots] == [mats[p] for p in row["materials"]], "Mesh material mapping mismatch")
        component = unreal.new_object(unreal.SkeletalMeshComponent)
        component.set_skinned_asset_and_update(mesh)
        names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
        check(len(names) == row["animation_reference_bones"], "Mesh reference bone count mismatch")
        check(set(row["added_unweighted_animation_bones"]).issubset(names), "Animation helper bones missing")
        reference_anim = next(a for a in ANIMATIONS if a["skeleton_destination"] == row["skeleton_destination"])
        check(names == reference_anim["bones"], "Skeleton bone name/order mismatch")
        expected_sockets = json.loads((ROOT / "Metadata" / (row["source_skeleton"] + ".json")).read_text(encoding="utf-8"))
        expected_sockets = [o["Properties"] for o in expected_sockets if o["Type"] == "SkeletalMeshSocket"]
        actual_sockets = {str(mesh.get_socket_by_index(i).socket_name): mesh.get_socket_by_index(i) for i in range(mesh.num_sockets())}
        for props in expected_sockets:
            sock = actual_sockets.get(props["SocketName"])
            check(sock is not None and str(sock.bone_name) == props["BoneName"], "Socket parent mismatch")
            for field, attr, default in [("RelativeLocation","relative_location",0),("RelativeScale","relative_scale",1)]:
                expected = props.get(field, {"X":default,"Y":default,"Z":default})
                actual = sock.get_editor_property(attr)
                check(max(abs(getattr(actual,k.lower())-expected[k]) for k in ["X","Y","Z"]) < 1e-4, "Socket vector mismatch")
            rot = sock.get_editor_property("relative_rotation")
            expected_rot = props.get("RelativeRotation",{"Pitch":0,"Yaw":0,"Roll":0})
            check(max(abs(getattr(rot,k.lower())-v) for k,v in expected_rot.items()) < 1e-4, "Socket rotation mismatch")
        check(MESH_EDITOR.get_lod_count(mesh) == 1, "Unexpected LOD count")
        files = [pathlib.Path(row["source_file"]), pathlib.Path(row["original_source_file"])] + [pathlib.Path(f) for f in row["lod_files"]]
        check(all(p.exists() for p in files), "Missing source LOD archive")
        verified.append({
            "asset":row["destination"],"skeleton":row["skeleton_destination"],
            "reference_bones":len(names),"sockets_verified":len(expected_sockets),
            "source_points":row["actorx_counts"]["PNTS0000"],"source_wedges":row["actorx_counts"]["VTXW0000"],
            "lod0_vertices":MESH_EDITOR.get_num_verts(mesh,0),"source_lods_archived":row["source_lod_count"],
            "project_lods":MESH_EDITOR.get_lod_count(mesh),"material_slots":len(slots),
            "source_file_sha256":{str(p):sha256(p) for p in files},
        })
    report["meshes"] = verified
    report["mesh"] = verified[0]
    return load(MESH_PATH), load(SKELETON_PATH)


def verify_animation_pose(row: dict, sequence, mesh) -> list[float]:
    expected_data = np.load(row["data_file"])
    maximum = np.zeros(3)
    for evaluation_type in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
        options = unreal.AnimPoseEvaluationOptions(
            evaluation_type=evaluation_type,
            should_retarget=False,
            extract_root_motion=False,
            incorporate_root_motion_into_pose=True,
            optional_skeletal_mesh=mesh,
        )
        for frame in sorted({0, (row["samples"] - 1) // 2, row["samples"] - 1}):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(sequence, frame, options)
            check(pose.is_valid(), "Invalid animation pose " + row["destination"])
            for bone_index, bone_name in enumerate(row["bones"]):
                transform = pose.get_bone_pose(bone_name, unreal.AnimPoseSpaces.LOCAL)
                expected = expected_data[frame, bone_index]
                position = [transform.translation.x, transform.translation.y, transform.translation.z]
                rotation = [transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w]
                scale = [transform.scale3d.x, transform.scale3d.y, transform.scale3d.z]
                errors = [
                    max(abs(left - right) for left, right in zip(position, expected[:3])),
                    min(
                        max(abs(left - right) for left, right in zip(rotation, expected[3:7])),
                        max(abs(left + right) for left, right in zip(rotation, expected[3:7])),
                    ),
                    max(abs(left - right) for left, right in zip(scale, expected[7:])),
                ]
                maximum = np.maximum(maximum, errors)
    check(maximum[0] < 0.05 and maximum[1] < 0.003 and maximum[2] < 0.001, "Animation pose mismatch " + row["destination"])
    return [float(value) for value in maximum]


def verify_animations(report: dict, mesh, skeleton) -> None:
    check(ANIMATION_IMPORT_AUDIT["status"] == "passed", "Animation batch audit did not pass")
    check(ANIMATION_IMPORT_AUDIT["version"] == TIMING_VERSION, "Animation batch audit version mismatch")
    check(ANIMATION_IMPORT_AUDIT["assets"] == len(ANIMATIONS), "Animation count mismatch")
    expected_paths = {row["destination"] for row in ANIMATIONS}
    actual_paths = {
        str(value).split(".", 1)[0]
        for value in EAL.list_assets(DEST + "/Animations", recursive=True, include_folder=False)
    }
    check(actual_paths == expected_paths, "Animations folder contains missing or extra assets")
    check(all(path.rsplit("/", 1)[1].startswith("A_EN_PLAY_") for path in actual_paths), "Animation naming mismatch")

    max_duration = 0.0
    max_pose = np.zeros(3)
    fps_values = set()
    force_root_lock = 0
    root_motion = 0
    additive = 0
    for index, row in enumerate(ANIMATIONS, 1):
        sequence = load(row["destination"])
        check(isinstance(sequence, unreal.AnimSequence), "Animation type mismatch " + row["destination"])
        mesh = load(row["mesh_destination"])
        skeleton = load(row["skeleton_destination"])
        check(sequence.get_editor_property("skeleton") == skeleton, "Animation skeleton mismatch " + row["destination"])
        check(EAL.get_metadata_tag(sequence, "EnemyTimingVersion") == TIMING_VERSION, "Timing version mismatch " + row["destination"])
        check(EAL.get_metadata_tag(sequence, "OriginalPackage") == row["source_package"], "Animation provenance mismatch")
        model = sequence.controller.get_model_interface()
        frame_rate = model.get_frame_rate()
        actual_fps = [frame_rate.numerator, frame_rate.denominator]
        check(actual_fps == row["fps"], "Animation FPS mismatch " + row["destination"])
        check(model.get_number_of_keys() == row["samples"], "Animation sample count mismatch " + row["destination"])
        check(model.get_number_of_frames() == row["samples"] - 1, "Animation frame count mismatch " + row["destination"])
        duration_error = abs(sequence.get_play_length() - row["duration"])
        check(duration_error < 1e-5, "Animation duration mismatch " + row["destination"])
        check(abs(sequence.get_editor_property("rate_scale") - row["rate_scale"]) < 1e-6, "Rate Scale mismatch " + row["destination"])
        properties = row["properties"]
        expected_root_motion = bool(properties.get("bEnableRootMotion", False))
        expected_force_lock = bool(properties.get("bForceRootLock", False))
        check(sequence.get_editor_property("enable_root_motion") == expected_root_motion, "Root motion mismatch " + row["destination"])
        check(sequence.get_editor_property("force_root_lock") == expected_force_lock, "Force Root Lock mismatch " + row["destination"])
        if "AdditiveAnimType" in properties:
            additive_values = {
                "AAT_None": unreal.AdditiveAnimationType.AAT_NONE,
                "AAT_LocalSpaceBase": unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE,
                "AAT_RotationOffsetMeshSpace": unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE,
            }
            key = properties["AdditiveAnimType"].split("::")[-1]
            check(sequence.get_editor_property("additive_anim_type") == additive_values[key], "Additive type mismatch")
            additive += int(key != "AAT_None")
        pose_error = verify_animation_pose(row, sequence, mesh)
        max_pose = np.maximum(max_pose, pose_error)
        max_duration = max(max_duration, duration_error)
        fps_values.add(tuple(actual_fps))
        root_motion += int(expected_root_motion)
        force_root_lock += int(expected_force_lock)
        if index % 20 == 0 or index == len(ANIMATIONS):
            print("YETUGA_AUDIT_ANIMATION", index, "/", len(ANIMATIONS), flush=True)

    check(root_motion == ANIMATION_IMPORT_AUDIT["root_motion_assets"], "Root-motion aggregate mismatch")
    check(force_root_lock == ANIMATION_IMPORT_AUDIT["force_root_lock_assets"], "Force-lock aggregate mismatch")
    check(additive == ANIMATION_IMPORT_AUDIT["additive_assets"], "Additive aggregate mismatch")
    report["animations"] = {
        "verified": len(ANIMATIONS),
        "direct_original_timeline": ANIMATION_IMPORT_AUDIT["direct_original_timeline"],
        "composite_bakes": ANIMATION_IMPORT_AUDIT["composite_bakes"],
        "dilation_bakes": ANIMATION_IMPORT_AUDIT["dilation_bakes"],
        "root_motion": root_motion,
        "force_root_lock": force_root_lock,
        "additive": additive,
        "fps_contracts": len(fps_values),
        "maximum_duration_error_seconds": max_duration,
        "maximum_pose_errors": {
            "position_cm": float(max_pose[0]),
            "quaternion_component": float(max_pose[1]),
            "scale": float(max_pose[2]),
        },
        "source_notify_event_rows_preserved_as_metadata": len(EVENTS),
    }


def verify_assemblies(report: dict, mesh) -> None:
    check(len(CATALOG) == len(MANIFEST["material_variants"]) == 1, "Assembly variant count mismatch")
    for catalog_row, source_row in zip(CATALOG, MANIFEST["material_variants"]):
        blueprint = load(source_row["blueprint"])
        check(isinstance(blueprint, unreal.Blueprint), "Blueprint type mismatch " + source_row["blueprint"])
        check(EAL.get_metadata_tag(blueprint, "EnemyArtRole") == "VisualAssembly_NoGameplayAI", "Blueprint role mismatch")
        check(EAL.get_metadata_tag(blueprint, "EnemySpecies") == "Yetuga", "Blueprint species mismatch")
        check(EAL.get_metadata_tag(blueprint, "YetugaAssemblyVersion") == ASSEMBLY_VERSION, "Blueprint version mismatch")
        selection = json.loads(EAL.get_metadata_tag(blueprint, "AssemblySelection"))
        check(selection["source_material_index"] == source_row["source_material_index"], "Blueprint source variant mismatch")
        check(selection["level_context"].keys() == {"HeinMach"}, "Blueprint level provenance mismatch")
        check(catalog_row["asset"] == source_row["blueprint"], "Assembly catalogue mismatch")

    actors = {actor.get_actor_label(): actor for actor in ACTORS.get_all_level_actors()}
    for row in MANIFEST["material_variants"]:
        label = row["blueprint"].rsplit("/", 1)[1]
        actor = actors.get(label)
        check(actor is not None, "Catalogue actor missing " + label)
        components = actor.get_components_by_class(unreal.SkeletalMeshComponent)
        check(len(components) == 1, "Visual Yetuga BP must have exactly one skeletal component " + label)
        component = components[0]
        check(asset_path(component.get_skinned_asset()) == MESH_PATH, "Blueprint mesh mismatch " + label)
        check(component.get_num_bones() == MANIFEST["body"]["animation_reference_bones"], "Blueprint bone count mismatch " + label)
        check(
            [asset_path(component.get_material(index)) for index in range(len(row["materials"]))] == row["materials"],
            "Blueprint material override mismatch " + label,
        )
        animation_data = component.get_editor_property("animation_data")
        check(asset_path(animation_data.anim_to_play) == row["idle_asset"], "Blueprint idle mismatch " + label)
        check(animation_data.saved_looping and animation_data.saved_playing, "Blueprint idle playback flags " + label)
        check(abs(animation_data.saved_play_rate - 1.0) < 1e-6, "Blueprint play rate mismatch " + label)
    report["assemblies"] = {
        "verified": len(CATALOG),
        "assets": [row["blueprint"] for row in MANIFEST["material_variants"]],
        "role": "VisualAssembly_NoGameplayAI",
        "single_skeletal_component": True,
        "source_material_variation_indices": [row["source_material_index"] for row in MANIFEST["material_variants"]],
    }


def verify_structure(report: dict) -> None:
    expected = {
        MESH_PATH,
        SKELETON_PATH,
        MAP_PATH,
        DEST + "/Materials/Masters/M_EN_Yetuga_SurfacePreview",
        DEST + "/Materials/Masters/M_EN_Yetuga_EyePreview",
        DEST + "/Materials/Masters/M_EN_Yetuga_PropPreview",
    }
    expected.update(row[key] for row in MANIFEST["meshes"] for key in ["destination","skeleton_destination"])
    expected.update(row["destination"] for row in MANIFEST["textures"])
    expected.update(row["destination"] for row in MANIFEST["materials"])
    expected.update(row["destination"] for row in ANIMATIONS)
    expected.update(row["blueprint"] for row in MANIFEST["material_variants"])
    actual = {
        str(value).split(".", 1)[0]
        for value in EAL.list_assets(DEST, recursive=True, include_folder=False)
    }
    check(actual == expected, "Yetuga asset set mismatch: missing=" + repr(expected-actual) + "; extra=" + repr(actual-expected))
    orphan_files = [
        str(path.relative_to(PROJECT)).replace("\\", "/")
        for path in CONTENT_ROOT.rglob("*.uasset")
        if "_ImportStaging" in str(path) or "_UpgradeBackup" in str(path)
    ]
    check(not orphan_files, "Temporary physical packages remain: " + repr(orphan_files))
    report["asset_structure"] = {
        "root": DEST,
        "registered_assets": len(actual),
        "expected_assets": len(expected),
        "temporary_packages": orphan_files,
        "playback_naming": "Animations/Playback/A_EN_PLAY_*",
    }


def main() -> None:
    report = {
        "status": "running",
        "source_levels": MANIFEST["source_levels"],
        "source_character": MANIFEST["source_character"],
    }
    try:
        build_catalogue(report)
        verify_textures(report)
        verify_materials(report)
        mesh, skeleton = verify_mesh(report)
        verify_animations(report, mesh, skeleton)
        verify_assemblies(report, mesh)
        verify_structure(report)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        compact = {
            key: report.get(key)
            for key in [
                "status",
                "source_levels",
                "source_character",
                "textures_verified",
                "texture_resolution_contract",
                "preview_masters_verified",
                "materials_verified",
                "material_parameters_verified",
                "mesh",
                "meshes",
                "animations",
                "assemblies",
                "asset_structure",
                "catalogue_map",
                "preview_settings",
                "error",
            ]
            if key in report
        }
        SUMMARY.write_text(json.dumps(compact, indent=2, ensure_ascii=False), encoding="utf-8")
    print("YETUGA_FRESH_AUDIT_PASSED", flush=True)


if __name__ == "__main__":
    main()
