"""Read-only Asset Registry inventory for the Enemy folder cleanup."""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
CONTENT = PROJECT / "Content/_Art/Enemies"
ROOT = "/Game/_Art/Enemies"
REPORT = PROJECT / "Saved/ImportReports/EnemyAssetStructureInspection_20260915.json"
LEGACY_PREFIXES = (
    ROOT + "/HeinMach/Archive",
    ROOT + "/HeinMach/Empire",
    ROOT + "/HeinMach/HalberdElite",
)
LEGACY_FRAGMENTS = (
    "/_ImportStaging/",
    "/SourceSequences/",
    "/PlaybackClips/",
    "SourceReferences/",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(value) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def package_path(value) -> str | None:
    return value.get_path_name().split(".")[0] if value else None


def vector(value) -> dict[str, float]:
    return {"x": value.x, "y": value.y, "z": value.z}


def rotator(value) -> dict[str, float]:
    return {"pitch": value.pitch, "yaw": value.yaw, "roll": value.roll}


def attach_socket(component) -> str:
    getter = getattr(component, "get_attach_socket_name", None)
    return str(getter()) if getter else ""


def animation_contract(package: str) -> dict:
    sequence = unreal.load_asset(package)
    if not isinstance(sequence, unreal.AnimSequence):
        raise RuntimeError("Cannot load AnimSequence " + package)
    model = sequence.controller.get_model_interface()
    rate = model.get_frame_rate()
    return {
        "asset": package,
        "skeleton": package_path(sequence.get_editor_property("skeleton")),
        "fps": [rate.numerator, rate.denominator],
        "samples": model.get_number_of_keys(),
        "frames": model.get_number_of_frames(),
        "seconds": sequence.get_play_length(),
        "rate_scale": sequence.get_editor_property("rate_scale"),
        "enable_root_motion": sequence.get_editor_property("enable_root_motion"),
        "force_root_lock": sequence.get_editor_property("force_root_lock"),
        "root_motion_root_lock": str(sequence.get_editor_property("root_motion_root_lock")),
    }


def mesh_contract(package: str, editor) -> dict:
    mesh = unreal.load_asset(package)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Cannot load SkeletalMesh " + package)
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skinned_asset_and_update(mesh)
    slots = mesh.get_editor_property("materials")
    return {
        "asset": package,
        "skeleton": package_path(mesh.get_editor_property("skeleton")),
        "bones": component.get_num_bones(),
        "lods": editor.get_lod_count(mesh),
        "materials": [
            {
                "slot": str(slot.material_slot_name),
                "material": package_path(slot.material_interface),
            }
            for slot in slots
        ],
    }


def blueprint_contract(package: str, subsystem, library) -> dict:
    blueprint = unreal.load_asset(package)
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError("Cannot load Blueprint " + package)
    components = []
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(blueprint):
        component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
        if not isinstance(component, unreal.SkeletalMeshComponent):
            continue
        animation_data = component.get_editor_property("animation_data")
        components.append(
            {
                "name": component.get_name(),
                "mesh": package_path(component.get_skinned_asset()),
                "animation": package_path(animation_data.anim_to_play),
                "play_rate": animation_data.saved_play_rate,
                "looping": animation_data.saved_looping,
                "playing": animation_data.saved_playing,
                "animation_mode": str(component.get_editor_property("animation_mode")),
                "materials": [
                    package_path(component.get_material(index))
                    for index in range(component.get_num_materials())
                ],
                "location": vector(component.get_editor_property("relative_location")),
                "rotation": rotator(component.get_editor_property("relative_rotation")),
                "scale": vector(component.get_editor_property("relative_scale3d")),
                "socket": attach_socket(component),
                "collision": str(component.get_collision_enabled()),
            }
        )
    return {"asset": package, "components": sorted(components, key=lambda row: row["name"])}


def main() -> None:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    options = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=True,
        include_soft_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=True,
        include_hard_management_references=True,
    )
    assets = {
        str(data.package_name): data
        for data in registry.get_assets_by_path(ROOT, recursive=True, include_only_on_disk_assets=True)
    }
    inventory = []
    for package, data in sorted(assets.items()):
        cls = str(data.asset_class_path.asset_name)
        suffix = ".umap" if cls == "World" else ".uasset"
        disk = PROJECT / (package.replace("/Game/", "Content/") + suffix)
        inventory.append(
            {
                "asset": package,
                "class": cls,
                "file": disk.relative_to(PROJECT).as_posix(),
                "bytes": disk.stat().st_size if disk.is_file() else None,
                "sha256": sha256(disk) if disk.is_file() else None,
            }
        )
    selected = {
        package
        for package in assets
        if package.startswith(LEGACY_PREFIXES)
        or any(fragment in package + "/" for fragment in LEGACY_FRAGMENTS)
        or package.startswith(ROOT + "/HeinMach/Shared/")
        or package.startswith(ROOT + "/HeinMach/Humanoids/Shared/")
        or package.startswith(ROOT + "/OtherRegions/Humanoids/MageHard/")
    }
    references = []
    for package in sorted(selected):
        dependencies = sorted(str(value) for value in registry.get_dependencies(package, options))
        referencers = sorted(str(value) for value in registry.get_referencers(package, options))
        references.append(
            {
                "asset": package,
                "class": str(assets[package].asset_class_path.asset_name),
                "enemy_dependencies": [value for value in dependencies if value.startswith(ROOT + "/")],
                "enemy_referencers": [value for value in referencers if value.startswith(ROOT + "/")],
                "external_referencers": [value for value in referencers if not value.startswith(ROOT + "/")],
            }
        )
    empty_directories = []
    for directory in sorted(path for path in CONTENT.rglob("*") if path.is_dir()):
        if not any(directory.iterdir()):
            empty_directories.append(directory.relative_to(CONTENT).as_posix())
    dirty = sorted(
        package.get_name()
        for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    )
    counts_by_root = collections.Counter()
    counts_by_class = collections.Counter()
    for package, data in assets.items():
        relative = package.removeprefix(ROOT + "/")
        counts_by_root[relative.split("/", 1)[0]] += 1
        counts_by_class[str(data.asset_class_path.asset_name)] += 1
    mesh_editor = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    subobject_library = unreal.SubobjectDataBlueprintFunctionLibrary
    animations = [
        animation_contract(package)
        for package, data in sorted(assets.items())
        if str(data.asset_class_path.asset_name) == "AnimSequence"
    ]
    meshes = [
        mesh_contract(package, mesh_editor)
        for package, data in sorted(assets.items())
        if str(data.asset_class_path.asset_name) == "SkeletalMesh"
    ]
    blueprints = [
        blueprint_contract(package, subobjects, subobject_library)
        for package, data in sorted(assets.items())
        if str(data.asset_class_path.asset_name) == "Blueprint"
    ]
    result = {
        "status": "passed",
        "root": ROOT,
        "asset_count": len(assets),
        "counts_by_root": dict(sorted(counts_by_root.items())),
        "counts_by_class": dict(sorted(counts_by_class.items())),
        "redirectors": sorted(
            package for package, data in assets.items()
            if str(data.asset_class_path.asset_name) == "ObjectRedirector"
        ),
        "empty_directories": empty_directories,
        "dirty_enemy_packages": [value for value in dirty if value.startswith(ROOT)],
        "selected_reference_audit": references,
        "animation_contracts": animations,
        "skeletal_mesh_contracts": meshes,
        "blueprint_contracts": blueprints,
        "inventory": inventory,
    }
    write(result)
    print(
        "ENEMY_ASSET_STRUCTURE_INSPECTION_PASSED",
        json.dumps(
            {
                "assets": result["asset_count"],
                "empty_directories": len(empty_directories),
                "redirectors": len(result["redirectors"]),
                "selected_assets": len(references),
                "external_referencers": sum(len(row["external_referencers"]) for row in references),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
