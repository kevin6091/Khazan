"""Create the canonical UE import manifest for the HeinMach Yetuga boss."""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import shutil
import struct


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
META = ROOT / "Metadata"
DEST = "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga"
PROJECT_META = PROJECT / "Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911"

CB = "BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Base_Setting/CB_Yetuga"
AP = CB.rsplit("/", 1)[0] + "/AP_Yetuga"
BODY = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/Model/C_M_Yetuga"
ROCK = BODY.rsplit("/", 1)[0] + "/C_I_YetugaRock_Small"
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
    reference_record_hashes = set()
    animation_reference = None
    for path in animation_files:
        chunks = actorx_chunks(path)
        bones = next(value for value in chunks if value[0].split(b"\0", 1)[0] == b"BONENAMES")
        size, count, payload = bones[2], bones[3], bones[4]
        reference_record_hashes.add(hashlib.sha256(payload).hexdigest())
        if size != 120:
            raise RuntimeError(f"Unexpected PSA reference-bone record size {size} in {path}")
        names = tuple(bone_name(payload[index * size : (index + 1) * size]) for index in range(count))
        layouts.setdefault(names, []).append(path)
        animation_reference = animation_reference or bones
    if len(layouts) != 1:
        raise RuntimeError(f"Yetuga animation skeleton layouts differ: {[len(value) for value in layouts]}")
    if len(reference_record_hashes) != 1:
        raise RuntimeError("PSA parent/reference-pose records differ across the selected skeleton")
    animation_names = next(iter(layouts))
    _, _, animation_size, animation_count, animation_payload = animation_reference
    mesh_names = tuple(
        bone_name(ref_payload[index * ref_size : (index + 1) * ref_size]) for index in range(ref_count)
    )
    if animation_names[:ref_count] != mesh_names or animation_count < ref_count:
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
    # The project's PSKFactory registers .psk only, but its reader supports
    # FACE3200/32-bit indices. Preserve those chunks while selecting that factory.
    destination = ROOT / "Derived/Mesh" / (body_file.stem + "_FullAnimationSkeleton.psk")
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
        "derivation": "Original body PSK geometry/weights/materials with source PSA-only reference bones appended after handedness conversion.",
        "animation_layout_files_verified": len(animation_files),
        "animation_reference_layout_sha256": next(iter(reference_record_hashes)),
    }


def unique_name(prefix: str, source_package: str, used: dict[str, str]) -> str:
    name = prefix + source_package.rsplit("/", 1)[-1]
    if name in used and used[name] != source_package:
        name += "_" + hashlib.sha256(source_package.encode("utf-8")).hexdigest()[:8]
    if name in used and used[name] != source_package:
        raise RuntimeError(f"Unresolved name collision for {source_package}")
    used[name] = source_package
    return name


def cached_parameters(obj):
    """Recover cooked master defaults; indices pair with matching RuntimeEntries."""
    result = {}
    parameters = obj.get("CachedExpressionData", {}).get("Parameters", {})
    for values, entry, field in [
        ("ScalarValues", "RuntimeEntries", "ScalarParameterValues"),
        ("VectorValues", "RuntimeEntries[1]", "VectorParameterValues"),
        ("TextureValues", "RuntimeEntries[2]", "TextureParameterValues"),
    ]:
        infos = parameters.get(entry, {}).get("ParameterInfos", [])
        vals = parameters.get(values, [])
        if len(infos) != len(vals):
            raise RuntimeError("Cached parameter index mismatch: " + obj["Name"])
        result[field] = [{"ParameterInfo": info, "ParameterValue": val} for info, val in zip(infos, vals)]
    return result


def main():
    closure = read(ROOT / "SourceClosure.json")
    types = closure["types"]
    cb_objects = source(CB)
    character_mesh = next(o for o in cb_objects if o.get("Name") == "CharacterMesh0")
    if package(character_mesh["Properties"]["SkeletalMesh"]) != BODY:
        raise RuntimeError("Unexpected source CB mesh")
    mesh_rows = []
    for mesh_package, suffix in [(BODY, "Yetuga"), (ROCK, "Yetuga_IceRock")]:
        obj = source_object(mesh_package, "SkeletalMesh")
        file = next(p for ext in [".psk", ".pskx"] if (p := ROOT / "Assets" / (mesh_package + ext)).exists())
        lods = sorted(str(p) for p in file.parent.glob(file.stem + "_LOD*.psk*"))
        counts = {chunk[0].split(b"\0")[0].decode(): chunk[3] for chunk in actorx_chunks(file)}
        mesh_rows.append({
            "source_package": mesh_package, "source_file": str(file),
            "destination": f"{DEST}/Meshes/SK_EN_{suffix}",
            "source_skeleton": package(obj["Properties"]["Skeleton"]),
            "skeleton_destination": f"{DEST}/Skeletons/SKEL_EN_{suffix}",
            "materials": [package(v["Material"]) for v in obj["SkeletalMaterials"]],
            "source_slot_names": [v["MaterialSlotName"] for v in obj["SkeletalMaterials"]],
            "bounds": obj["ImportedBounds"], "lod_files": lods, "source_lod_count": len(lods) + 1,
            "source_properties": obj["Properties"], "actorx_counts": counts,
            "morph_targets": [o["Name"] for o in source(mesh_package) if o.get("Type") == "MorphTarget"],
        })
    skeleton_mesh = {m["source_skeleton"]: m for m in mesh_rows}
    source_anims, composites, excluded = [], [], []
    for p, ts in sorted(types.items()):
        for kind, target in [("AnimSequence", source_anims), ("AnimComposite", composites)]:
            if kind not in ts:
                continue
            obj = source_object(p, kind)
            skeleton = package(obj["Properties"].get("Skeleton"))
            if skeleton not in skeleton_mesh:
                excluded.append({"source": p, "skeleton": skeleton, "reason": "Shared missile gameplay carrier; not the Yetuga body or ice-rock skeleton."})
                continue
            mesh = skeleton_mesh[skeleton]
            target.append({
                "source_package": p, "source_skeleton": skeleton,
                "mesh_destination": mesh["destination"], "skeleton_destination": mesh["skeleton_destination"],
                "source_file": str(ROOT / "Assets" / (p + ".psa")),
                "properties": obj["Properties"],
            })
    sequences = {row["source_package"] for row in source_anims}
    consumers = collections.defaultdict(set)
    for e in closure["dependencies"]:
        if e["followed"] and e["target"] in sequences and e["owner_type"] != "AnimComposite":
            consumers[e["target"]].add(e["owner_type"])
    names = {}
    for row in source_anims:
        row["direct_consumers"] = sorted(consumers[row["source_package"]])
        row["destination"] = f"{DEST}/Animations/Playback/" + unique_name("A_EN_PLAY_", row["source_package"], names) if row["direct_consumers"] else None
    for row in composites:
        row["destination"] = f"{DEST}/Animations/Playback/" + unique_name("A_EN_PLAY_", row["source_package"], names)
    for mesh in mesh_rows:
        files = [pathlib.Path(row["source_file"]) for row in source_anims if row["source_skeleton"] == mesh["source_skeleton"]]
        mesh.update(derive_full_animation_skeleton_psk(pathlib.Path(mesh["source_file"]), files))
    leaves = set(p for m in mesh_rows for p in m["materials"])
    categories, hierarchy = {}, {}
    def visit_material(p, category):
        if p in hierarchy:
            return
        kind = "MaterialInstanceConstant" if "MaterialInstanceConstant" in types[p] else "Material"
        obj = source_object(p, kind)
        parent = package(obj.get("Properties", {}).get("Parent"))
        if parent:
            visit_material(parent, category)
        hierarchy[p] = obj
        categories[p] = category
    for p in sorted(leaves):
        category = "Eye" if "_Eye" in p else ("Prop" if p not in mesh_rows[0]["materials"] else "Surface")
        visit_material(p, category)
    effective, provenance = {}, {}
    rows, root_defaults, skipped_textures = [], {}, []
    for p, obj in hierarchy.items():
        parent = package(obj.get("Properties", {}).get("Parent"))
        props = obj.get("Properties", {})
        inherited = effective.get(parent, {})
        direct = props if parent else cached_parameters(obj)
        merged = dict(inherited)
        origins = dict(provenance.get(parent, {}))
        for field in ["ScalarParameterValues", "VectorParameterValues", "TextureParameterValues"]:
            entries = {json.dumps(v["ParameterInfo"], sort_keys=True): v for v in inherited.get(field, [])}
            for v in direct.get(field, []):
                key = json.dumps(v["ParameterInfo"], sort_keys=True)
                entries[key] = v
                origins[field + ":" + v["ParameterInfo"]["Name"]] = p
            merged[field] = list(entries.values())
        merged["BasePropertyOverrides"] = dict(inherited.get("BasePropertyOverrides", {}))
        merged["BasePropertyOverrides"].update(props.get("BasePropertyOverrides", {}))
        effective[p], provenance[p] = merged, origins
        if not parent:
            root_defaults[p] = {"defaults": merged, "category": categories[p], "source_object": obj}
            continue
        material_props = dict(merged)
        material_props["TextureParameterValues"] = []
        for v in merged["TextureParameterValues"]:
            texture = package(v.get("ParameterValue"))
            if texture and "Texture2D" in types.get(texture, []):
                material_props["TextureParameterValues"].append(v)
            else:
                skipped_textures.append({"material": p, "parameter": v["ParameterInfo"]["Name"], "source": texture, "reason": "Non-Texture2D cooked parameter; source JSON and cooked package archived."})
        rows.append({
            "source_package": p, "destination": f"{DEST}/Materials/Instances/MI_EN_Yetuga_" + p.rsplit("/", 1)[1],
            "category": categories[p], "source_parent": parent, "source_object": obj,
            "effective_properties": material_props, "parameter_origins": origins,
            "role": "MeshSlot" if p in leaves else "InheritedParent",
        })
    textures = []
    tex_names = {}
    required_textures = {package(v["ParameterValue"]) for row in rows for v in row["effective_properties"]["TextureParameterValues"]}
    for p in sorted(required_textures):
        obj = source_object(p, "Texture2D")
        textures.append({
            "source_package": p, "source_file": str(ROOT / "Assets" / (p + ".png")),
            "destination": f"{DEST}/Textures/" + unique_name("T_EN_Yetuga_", p, tex_names),
            "source_object": obj, "properties": obj.get("Properties", {}),
        })
    material_map = {row["source_package"]: row["destination"] for row in rows}
    anim_map = {row["source_package"]: row["destination"] for row in source_anims + composites if row["destination"]}
    idle = package(source_object(AP, "xxAnimationProfile")["Properties"]["Idle"])
    rock_idle = next(p for p in anim_map if p.endswith("/AC_YetugaRock_Small_Idle"))
    transform = {k:v for k,v in character_mesh["Properties"].items() if k in ["RelativeRotation", "RelativeLocation", "RelativeScale3D"]}
    variants = [{
        "variant": 1, "source_material_index": None, "source_materials": mesh_rows[0]["materials"],
        "materials": [material_map[p] for p in mesh_rows[0]["materials"]],
        "blueprint": DEST + "/Blueprints/BP_EN_Boss_Yetuga", "mesh": mesh_rows[0]["destination"],
        "idle_source": idle, "idle_asset": anim_map[idle],
    }]
    result = {
        "schema_version": 1, "library_version": "20260911_YetugaV1", "destination_root": DEST,
        "source_character": CB, "source_animation_profile": AP, "source_levels": ["HeinMach"],
        "body": mesh_rows[0], "meshes": mesh_rows, "textures": textures, "materials": rows,
        "source_material_parent_packages": [p for p in hierarchy if p not in leaves],
        "source_master_defaults": root_defaults, "metadata_only_texture_parameters": skipped_textures,
        "source_animations": source_anims, "composites": composites,
        "metadata_only_shared_missile_composites": excluded,
        "direct_source_animation_packages": sorted(p for p in consumers if consumers[p]),
        "material_variants": variants, "source_component_transform": transform,
        "prop_preview": {"mesh": mesh_rows[1]["destination"], "idle_asset": anim_map[rock_idle]},
        "preview_component_transform": {
            "RelativeRotation": transform["RelativeRotation"], "RelativeLocation": {"X":0,"Y":0,"Z":0},
            "RelativeScale3D":{"X":1,"Y":1,"Z":1},
            "status": "Presentation-only foot-ground origin; source capsule offset remains separately preserved.",
        },
        "limitations": [
            "Cooked custom BBQ shader graph and custom shading models cannot be recovered as editable stock UE shaders. Source master defaults, full material inheritance, leaf overrides and metadata are preserved; explicit UE preview adapters render the mesh.",
            "Physics, cloth, postprocess control rigs, proprietary notify behavior, VFX/audio and gameplay are source metadata/cooked archives; preview Actor does not implement boss combat.",
            "Exported source LOD geometry is archived; imported LOD support is recorded by the mesh audit.",
            "Asset timing preserves serialized source sequence/segment/dilation timelines. Runtime hit-stop, actor dilation and AI rate changes are separate gameplay contracts.",
        ],
    }
    write(ROOT / "ImportManifest.json", result)
    write(PROJECT_META / "ImportManifest.json", result)
    for name in ["SourceClosure.json","LevelPresence.json","DiscoverySummary.json","SourceExportSummary.json"]:
        shutil.copy2(ROOT / name, PROJECT_META / name)
    summary = {"status":"passed", "meshes":len(mesh_rows), "bones":[m["animation_reference_bones"] for m in mesh_rows],
               "textures":len(textures), "material_instances":len(rows), "source_sequences":len(source_anims),
               "composites":len(composites), "direct_sequences":sum(bool(row["destination"]) for row in source_anims),
               "metadata_only_missile_composites":len(excluded), "metadata_only_texture_parameters":len(skipped_textures)}
    write(ROOT / "ImportManifestSummary.json", summary)
    write(PROJECT_META / "ImportManifestSummary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
