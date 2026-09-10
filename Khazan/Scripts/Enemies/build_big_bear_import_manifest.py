"""Create the canonical UE import manifest for the shared BigBear_E library."""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import shutil
import struct


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/BigBear_20260910"
META = ROOT / "Metadata"
DEST = "/Game/_Art/Enemies/Shared/Beasts/BigBear"
PROJECT_META = PROJECT / "Content/_Art/Enemies/Shared/Beasts/BigBear/Metadata/Extraction_20260910"

CB = "BBQ/Content/_Kazan_/Design/Monster/Beast/BigBear_E/Base_Setting/CB_BigBear_E"
AP = "BBQ/Content/_Kazan_/Design/Monster/Beast/BigBear_E/Base_Setting/AP_BigBear_E"
BODY = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/BigBear/Model/C_M_BigBear"
CARRIER = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/BigBear/Model/C_M_BigBear_EmptyMesh"
UNUSED_BODY = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/BigBear/Model/C_M_BigBearV2"
ACTORX_HEADER = struct.Struct("<20siii")


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def source(package: str):
    return read(META / f"{package}.json")


def package(value) -> str | None:
    if not value or not isinstance(value, dict):
        return None
    result = value.get("ObjectPath", value.get("AssetPathName", "")).split(".", 1)[0]
    return result.replace("/Game/", "BBQ/Content/") or None


def source_object(package_name: str, kind: str):
    values = [value for value in source(package_name) if value.get("Type") == kind]
    exact = [value for value in values if value.get("Name") == package_name.rsplit("/", 1)[-1]]
    selected = exact or values
    if len(selected) != 1:
        raise RuntimeError(f"Expected one {kind} in {package_name}, found {len(selected)}")
    return selected[0]


def actorx_chunks(path: pathlib.Path):
    data = path.read_bytes()
    offset = 0
    result = []
    while offset < len(data):
        tag, flags, size, count = ACTORX_HEADER.unpack_from(data, offset)
        offset += ACTORX_HEADER.size
        payload = data[offset : offset + size * count]
        offset += size * count
        result.append((tag, flags, size, count, payload))
    if offset != len(data):
        raise RuntimeError(f"ActorX chunk boundary mismatch in {path}")
    return result


def bone_name(record: bytes) -> str:
    return record[:64].split(b"\0", 1)[0].decode("utf-8")


def derive_full_animation_skeleton_psk(body_file: pathlib.Path, animation_files: list[pathlib.Path]):
    body_chunks = actorx_chunks(body_file)
    ref_index = next(
        index for index, value in enumerate(body_chunks) if value[0].split(b"\0", 1)[0] == b"REFSKELT"
    )
    ref_tag, ref_flags, ref_size, ref_count, ref_payload = body_chunks[ref_index]
    if ref_size != 120:
        raise RuntimeError(f"Unexpected PSK reference-bone record size {ref_size}")

    layouts = {}
    animation_reference = None
    for path in animation_files:
        chunks = actorx_chunks(path)
        bones = next(value for value in chunks if value[0].split(b"\0", 1)[0] == b"BONENAMES")
        size, count, payload = bones[2], bones[3], bones[4]
        if size != 120:
            raise RuntimeError(f"Unexpected PSA reference-bone record size {size} in {path}")
        names = tuple(bone_name(payload[index * size : (index + 1) * size]) for index in range(count))
        layouts.setdefault(names, []).append(path)
        animation_reference = animation_reference or bones
    if len(layouts) != 1:
        raise RuntimeError(f"BigBear animation skeleton layouts differ: {[len(value) for value in layouts]}")
    animation_names = next(iter(layouts))
    _, _, animation_size, animation_count, animation_payload = animation_reference
    mesh_names = tuple(
        bone_name(ref_payload[index * ref_size : (index + 1) * ref_size]) for index in range(ref_count)
    )
    if animation_names[:ref_count] != mesh_names or animation_count <= ref_count:
        raise RuntimeError("Animation skeleton is not a strict extension of the exported mesh skeleton")

    # CUE4Parse PSK and PSA reference records use opposite Y handedness. Match
    # each shared transform first, then append the missing unweighted bones in
    # PSK space. Existing mesh records stay byte-for-byte intact.
    for index in range(ref_count):
        mesh_record = ref_payload[index * ref_size : (index + 1) * ref_size]
        animation_record = animation_payload[index * animation_size : (index + 1) * animation_size]
        mesh_parent = struct.unpack_from("<i", mesh_record, 72)[0]
        animation_parent = struct.unpack_from("<i", animation_record, 72)[0]
        if mesh_parent != animation_parent:
            raise RuntimeError(f"Parent mismatch at reference bone {mesh_names[index]}")
        mesh_transform = struct.unpack_from("<7f", mesh_record, 76)
        converted = list(struct.unpack_from("<7f", animation_record, 76))
        converted[1] *= -1.0
        converted[5] *= -1.0
        if index == 0:
            converted[3] *= -1.0
        if max(abs(left - right) for left, right in zip(mesh_transform, converted)) >= 1e-5:
            raise RuntimeError(f"Reference-pose mismatch at shared bone {mesh_names[index]}")

    extended = bytearray(ref_payload)
    for index in range(ref_count, animation_count):
        record = bytearray(animation_payload[index * animation_size : (index + 1) * animation_size])
        transform = list(struct.unpack_from("<11f", record, 76))
        transform[1] *= -1.0
        transform[5] *= -1.0
        transform[7:] = [0.0, 0.0, 0.0, 0.0]
        struct.pack_into("<11f", record, 76, *transform)
        extended.extend(record)

    body_chunks[ref_index] = (ref_tag, ref_flags, ref_size, animation_count, bytes(extended))
    destination = ROOT / "Derived/Mesh/C_M_BigBear_FullAnimationSkeleton.psk"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        for tag, flags, size, count, payload in body_chunks:
            output.write(ACTORX_HEADER.pack(tag, flags, size, count))
            output.write(payload)
    return {
        "source_file": str(destination),
        "original_source_file": str(body_file),
        "mesh_reference_bones": ref_count,
        "animation_reference_bones": animation_count,
        "added_unweighted_animation_bones": list(animation_names[ref_count:]),
        "derivation": "Original body PSK geometry/weights/materials with the eight source PSA-only reference bones appended after handedness conversion.",
        "animation_layout_files_verified": len(animation_files),
    }


def unique_name(prefix: str, source_package: str, used: dict[str, str]) -> str:
    name = prefix + source_package.rsplit("/", 1)[-1]
    if name in used and used[name] != source_package:
        name += "_" + hashlib.sha256(source_package.encode("utf-8")).hexdigest()[:8]
    if name in used and used[name] != source_package:
        raise RuntimeError(f"Unresolved name collision for {source_package}")
    used[name] = source_package
    return name


def material_name(source_package: str) -> str:
    name = source_package.rsplit("/", 1)[-1]
    if name == "CM_M_BigBear_Eye":
        return "MI_EN_BigBear_Eye"
    part = name.rsplit("_", 1)[-1]
    if name.startswith("CM_M_BigBearV2_"):
        variant = "V02"
    elif name.startswith("CM_M_BigBearV3_"):
        variant = "V03"
    elif name.startswith("CM_M_BigBear_"):
        variant = "V01"
    else:
        raise RuntimeError(f"Unexpected BigBear leaf material {name}")
    return f"MI_EN_BigBear_{part}_{variant}"


def main() -> None:
    closure = read(ROOT / "SourceClosure.json")
    types = closure["types"]
    cb_objects = source(CB)
    recipe_component = next(
        value
        for value in cb_objects
        if value.get("Name") == "CD_RD_M_BigBear_001_GEN_VARIABLE"
    )
    face_parts = recipe_component["Properties"]["FacePartsList"]
    if len(face_parts) != 1 or package(face_parts[0]["Mesh"]) != BODY:
        raise RuntimeError("CB_BigBear_E no longer selects the expected C_M_BigBear body")
    variations = face_parts[0]["MaterialVariations"]
    if len(variations) != 3:
        raise RuntimeError(f"Expected three CB material variations, found {len(variations)}")

    material_sets = []
    leaf_materials: set[str] = set()
    for index, variation in enumerate(variations, 1):
        materials = [package(value) for value in variation["Materials"]]
        if len(materials) != 4 or any(value is None for value in materials):
            raise RuntimeError(f"Invalid source material variation {index}: {materials}")
        leaf_materials.update(materials)
        material_sets.append(
            {
                "variant": index,
                "source_material_index": index - 1,
                "source_materials": materials,
                "blueprint": f"{DEST}/Blueprints/BP_EN_BigBear_V{index:02d}",
            }
        )

    material_rows = []
    for source_package in sorted(leaf_materials):
        obj = source_object(source_package, "MaterialInstanceConstant")
        material_rows.append(
            {
                "source_package": source_package,
                "destination": f"{DEST}/Materials/Instances/{material_name(source_package)}",
                "category": "Eye" if source_package.endswith("_Eye") else "Surface",
                "source_parent": package(obj.get("Properties", {}).get("Parent")),
                "source_object": obj,
            }
        )

    texture_rows = []
    used_texture_names: dict[str, str] = {}
    for source_package, values in sorted(types.items()):
        if "Texture2D" not in values:
            continue
        obj = source_object(source_package, "Texture2D")
        basename = source_package.rsplit("/", 1)[-1]
        clean = basename[5:] if basename.startswith("CT_M_") else basename
        target_name = unique_name("T_EN_BigBear_", source_package.rsplit("/", 1)[0] + "/" + clean, used_texture_names)
        texture_rows.append(
            {
                "source_package": source_package,
                "source_file": str(ROOT / "Assets" / f"{source_package}.png"),
                "destination": f"{DEST}/Textures/{target_name}",
                "properties": obj.get("Properties", {}),
                "source_object": obj,
            }
        )

    body_obj = source_object(BODY, "SkeletalMesh")
    skeleton_package = package(body_obj.get("Properties", {}).get("Skeleton"))
    source_file = ROOT / "Assets" / f"{BODY}.psk"
    lod_files = sorted(str(value) for value in source_file.parent.glob(source_file.stem + "_LOD*.psk"))
    body_row = {
        "source_package": BODY,
        "source_file": str(source_file),
        "destination": f"{DEST}/Meshes/SK_EN_BigBear",
        "source_skeleton": skeleton_package,
        "skeleton_destination": f"{DEST}/Skeletons/SKEL_EN_BigBear",
        "materials": [package(value["Material"]) for value in body_obj["SkeletalMaterials"]],
        "source_slot_names": [value["MaterialSlotName"] for value in body_obj["SkeletalMaterials"]],
        "bounds": body_obj["ImportedBounds"],
        "lod_files": lod_files,
        "source_lod_count": 1 + len(lod_files),
        "morph_targets": [value["Name"] for value in source(BODY) if value.get("Type") == "MorphTarget"],
    }

    source_animations = []
    composite_rows = []
    for source_package, values in sorted(types.items()):
        if "AnimSequence" in values:
            obj = source_object(source_package, "AnimSequence")
            source_animations.append(
                {
                    "source_package": source_package,
                    "source_skeleton": package(obj.get("Properties", {}).get("Skeleton")),
                    "source_file": str(ROOT / "Assets" / f"{source_package}.psa"),
                    "properties": obj.get("Properties", {}),
                }
            )
        if "AnimComposite" in values:
            obj = source_object(source_package, "AnimComposite")
            composite_rows.append(
                {
                    "source_package": source_package,
                    "source_skeleton": package(obj.get("Properties", {}).get("Skeleton")),
                    "properties": obj.get("Properties", {}),
                }
            )

    sequence_packages = {row["source_package"] for row in source_animations}
    direct_consumers: dict[str, set[str]] = collections.defaultdict(set)
    for edge in closure["dependencies"]:
        if edge.get("followed") and edge["target"] in sequence_packages and edge["owner_type"] != "AnimComposite":
            direct_consumers[edge["target"]].add(edge["owner_type"])
    direct_packages = sorted(direct_consumers)

    full_skeleton = derive_full_animation_skeleton_psk(
        source_file, [pathlib.Path(row["source_file"]) for row in source_animations]
    )
    body_row.update(full_skeleton)

    used_animation_names: dict[str, str] = {}
    for row in source_animations:
        if row["source_package"] in direct_consumers:
            name = unique_name("A_EN_PLAY_", row["source_package"], used_animation_names)
            row["destination"] = f"{DEST}/Animations/Playback/{name}"
            row["direct_consumers"] = sorted(direct_consumers[row["source_package"]])
        else:
            row["destination"] = None
            row["direct_consumers"] = []
    for row in composite_rows:
        name = unique_name("A_EN_PLAY_", row["source_package"], used_animation_names)
        row["destination"] = f"{DEST}/Animations/Playback/{name}"

    ap_obj = source_object(AP, "xxAnimationProfile")
    idle_package = package(ap_obj["Properties"]["Idle"])
    if idle_package not in direct_packages:
        raise RuntimeError(f"BigBear idle is not retained as a direct sequence: {idle_package}")

    character_mesh = next(value for value in cb_objects if value.get("Name") == "CharacterMesh0")
    source_transform = {
        key: character_mesh.get("Properties", {}).get(key)
        for key in ["RelativeLocation", "RelativeRotation", "RelativeScale3D"]
        if key in character_mesh.get("Properties", {})
    }

    material_map = {row["source_package"]: row["destination"] for row in material_rows}
    animation_map = {
        row["source_package"]: row["destination"]
        for row in source_animations
        if row["destination"]
    }
    for material_set in material_sets:
        material_set["materials"] = [material_map[value] for value in material_set["source_materials"]]
        material_set["idle_source"] = idle_package
        material_set["idle_asset"] = animation_map[idle_package]

    result = {
        "schema_version": 1,
        "library_version": "20260910_BigBearV1",
        "destination_root": DEST,
        "source_character": CB,
        "source_animation_profile": AP,
        "source_levels": ["HeinMach", "StormPass"],
        "body": body_row,
        "carrier_archive": {
            "source_package": CARRIER,
            "source_file": str(ROOT / "Assets" / f"{CARRIER}.psk"),
            "purpose": "Original CB CharacterMesh0 pose carrier; archived with LOD files but not needed by the standalone full-body UE mesh.",
        },
        "excluded_source_mesh": {
            "source_package": UNUSED_BODY,
            "reason": "Present only in recipe FaceMesh editor inventory; absent from effective CB FacePartsList mesh selection.",
        },
        "textures": texture_rows,
        "materials": material_rows,
        "source_material_parent_packages": sorted(
            package_name
            for package_name, values in types.items()
            if "MaterialInstanceConstant" in values and package_name not in leaf_materials
        ),
        "source_animations": source_animations,
        "composites": composite_rows,
        "direct_source_animation_packages": direct_packages,
        "material_variants": material_sets,
        "source_component_transform": source_transform,
        "preview_component_transform": {
            "RelativeRotation": source_transform.get("RelativeRotation"),
            "RelativeLocation": {"X": 0.0, "Y": 0.0, "Z": 0.0},
            "RelativeScale3D": {"X": 1.0, "Y": 1.0, "Z": 1.0},
            "status": "Foot-ground preview origin. Source capsule-relative location remains in metadata; CB scale has no serialized override.",
        },
        "limitations": [
            "Cooked M_AKCartoonCharacter/M_BBQCartoonEye graph topology is unavailable; source parameters and parent paths are preserved while UE uses explicit preview adapters.",
            "Source LOD PSK files are archived. The project PSK importer creates the verified LOD0 mesh; it does not build the source UE LOD chain automatically.",
            "Source PhysicsAsset/socket/control-rig/gameplay metadata is archived; this visual Actor Blueprint does not recreate AI, abilities, collision damage boxes or ragdoll behavior.",
            "Composite notify metadata is preserved. Proprietary notify classes, VFX, audio and hit logic are not implemented by the visual playback sequences.",
        ],
    }

    write(ROOT / "ImportManifest.json", result)
    write(PROJECT_META / "ImportManifest.json", result)
    for name in ["SourceClosure.json", "LevelPresence.json", "DiscoverySummary.json", "SourceExportSummary.json"]:
        shutil.copy2(ROOT / name, PROJECT_META / name)
    write(
        ROOT / "ImportManifestSummary.json",
        {
            "status": "passed",
            "body_meshes": 1,
            "source_lods": body_row["source_lod_count"],
            "textures": len(texture_rows),
            "leaf_materials": len(material_rows),
            "material_variants": len(material_sets),
            "source_sequences_for_bake": len(source_animations),
            "composite_playback_targets": len(composite_rows),
            "direct_playback_targets": len(direct_packages),
            "total_playback_targets_before_timing_validation": len(composite_rows) + len(direct_packages),
        },
    )
    shutil.copy2(ROOT / "ImportManifestSummary.json", PROJECT_META / "ImportManifestSummary.json")
    print(json.dumps(read(ROOT / "ImportManifestSummary.json"), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
