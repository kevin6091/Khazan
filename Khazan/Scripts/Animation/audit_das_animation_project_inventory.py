"""Read-only inventory for the DualAxeSword timing restoration.

The report separates the imported source library from locomotion presentation
assets and records the dependency closure of the current player Anim Blueprint.
It never saves a package.
"""

from __future__ import annotations

import collections
import json
import pathlib

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"

SOURCE_ROOT = "/Game/_Art/Kazan/Animation/Weapons/DualAxeSword"
INGAME_ROOT = "/Game/_Art/Kazan/Animation/InGame/DAS"
LOCOMOTION_RUNTIME_ROOT = "/Game/_Art/Kazan/Animation/Locomotion/Runtime/DualAxeSword"
PLAYBACK_ROOT = "/Game/_Art/Kazan/Animation/Playback/DualAxeSword"
PLAYER_ANIM_BLUEPRINT = "/Game/_Art/Kazan/Character/Bluprints/ABP_Player"
TARGET_SKELETONS = {
    "/Game/_Art/Kazan/Character/Meshs/SK_Khazan": "/Game/_Art/Kazan/Character/Meshs/SKM_Khazan",
    "/Game/_Art/Kazan/Item/Imperial/DualAxeSword_Imperial_R_Skeleton": "/Game/_Art/Kazan/Item/Imperial/DualAxeSword_Imperial_R",
}


def package_path(value) -> str | None:
    if not value:
        return None
    return value.get_path_name().split(".", 1)[0]


def editor_property(value, name: str, default=None):
    try:
        return value.get_editor_property(name)
    except Exception:
        return default


def metadata(sequence) -> dict[str, str]:
    library = unreal.EditorAssetLibrary
    return {
        str(key): str(value)
        for key, value in library.get_metadata_tag_values(sequence).items()
    }


def sequence_contract(package: str) -> dict:
    sequence = unreal.load_asset(package)
    if not isinstance(sequence, unreal.AnimSequence):
        raise RuntimeError("Cannot load AnimSequence " + package)
    model = sequence.controller.get_model_interface()
    rate = model.get_frame_rate()
    track_names = [str(value) for value in model.get_bone_track_names()]
    notify_tracks = [
        str(value) for value in unreal.AnimationLibrary.get_animation_notify_track_names(sequence)
    ]
    notify_events = [
        value.export_text()
        for value in unreal.AnimationLibrary.get_animation_notify_events(sequence)
    ]
    sync_markers = {
        track: [
            {"name": str(marker.marker_name), "time": float(marker.time)}
            for marker in unreal.AnimationLibrary.get_animation_sync_markers_for_track(sequence, track)
        ]
        for track in notify_tracks
    }
    import_data = editor_property(sequence, "asset_import_data")
    import_filenames = list(import_data.extract_filenames()) if import_data else []
    return {
        "asset": package,
        "name": package.rsplit("/", 1)[-1],
        "skeleton": package_path(editor_property(sequence, "skeleton")),
        "preview_mesh": package_path(editor_property(sequence, "preview_skeletal_mesh")),
        "fps": [int(rate.numerator), int(rate.denominator)],
        "samples": int(model.get_number_of_keys()),
        "frames": int(model.get_number_of_frames()),
        "seconds": float(sequence.get_play_length()),
        "rate_scale": float(editor_property(sequence, "rate_scale", 1.0)),
        "enable_root_motion": bool(editor_property(sequence, "enable_root_motion", False)),
        "force_root_lock": bool(editor_property(sequence, "force_root_lock", False)),
        "root_motion_root_lock": str(editor_property(sequence, "root_motion_root_lock")),
        "additive_anim_type": str(editor_property(sequence, "additive_anim_type")),
        "ref_pose_type": str(editor_property(sequence, "ref_pose_type")),
        "ref_frame_index": int(editor_property(sequence, "ref_frame_index", 0)),
        "track_count": len(track_names),
        "track_names": track_names,
        "float_curve_count": int(model.get_number_of_float_curves()),
        "transform_curve_count": int(model.get_number_of_transform_curves()),
        "notify_tracks": notify_tracks,
        "notify_events": notify_events,
        "sync_markers": sync_markers,
        "import_filenames": import_filenames,
        "metadata": metadata(sequence),
    }


def dependency_closure(registry, root: str, options) -> list[str]:
    pending = [root]
    visited = set()
    while pending:
        package = pending.pop()
        if package in visited:
            continue
        visited.add(package)
        for dependency in registry.get_dependencies(package, options):
            value = str(dependency)
            if value.startswith("/Game/") and value not in visited:
                pending.append(value)
    return sorted(visited)


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

    roots = (SOURCE_ROOT, INGAME_ROOT, LOCOMOTION_RUNTIME_ROOT, PLAYBACK_ROOT)
    asset_data = {}
    for root in roots:
        for data in registry.get_assets_by_path(root, recursive=True, include_only_on_disk_assets=True):
            asset_data[str(data.package_name)] = data

    closure = dependency_closure(registry, PLAYER_ANIM_BLUEPRINT, options)
    closure_set = set(closure)
    rows = []
    load_failures = []
    for package, data in sorted(asset_data.items()):
        class_name = str(data.asset_class_path.asset_name)
        base = {
            "asset": package,
            "class": class_name,
            "in_player_anim_blueprint_dependency_closure": package in closure_set,
            "referencers": sorted(str(value) for value in registry.get_referencers(package, options)),
        }
        if class_name == "AnimSequence":
            try:
                base.update(sequence_contract(package))
            except Exception as error:
                load_failures.append({"asset": package, "error": str(error)})
        rows.append(base)

    by_root = collections.Counter()
    by_class = collections.Counter()
    for row in rows:
        by_class[row["class"]] += 1
        for root in roots:
            if row["asset"].startswith(root + "/"):
                by_root[root] += 1
                break

    all_locomotion = sorted(
        row["asset"]
        for row in rows
        if row["class"] == "AnimSequence"
        and (
            row["asset"].startswith(INGAME_ROOT + "/Locomotion/")
            or row["asset"].startswith(LOCOMOTION_RUNTIME_ROOT + "/")
            or (
                row["asset"].startswith(SOURCE_ROOT + "/")
                and "/Locomotion/" in row["asset"]
            )
        )
    )
    current_locomotion_dependencies = sorted(
        row["asset"]
        for row in rows
        if row["class"] == "AnimSequence"
        and row["in_player_anim_blueprint_dependency_closure"]
        and (
            row["asset"].startswith(INGAME_ROOT + "/")
            or row["asset"].startswith(LOCOMOTION_RUNTIME_ROOT + "/")
            or row["asset"].startswith(SOURCE_ROOT + "/")
        )
    )
    protected = list(current_locomotion_dependencies)
    unused_locomotion = sorted(set(all_locomotion) - set(protected))

    target_skeletons = {}
    for skeleton_path, mesh_path in TARGET_SKELETONS.items():
        skeleton = unreal.load_asset(skeleton_path)
        mesh = unreal.load_asset(mesh_path)
        if not skeleton or not mesh:
            load_failures.append(
                {"asset": skeleton_path, "error": "Target skeleton or preview mesh is missing"}
            )
            continue
        reference_pose = skeleton.get_reference_pose()
        bone_names = [str(value) for value in reference_pose.get_bone_names()]
        target_skeletons[skeleton_path] = {
            "preview_mesh": mesh_path,
            "mesh_skeleton": package_path(editor_property(mesh, "skeleton")),
            "bone_names": bone_names,
            "root_bone": bone_names[0],
            "root_children": [str(value) for value in mesh.get_bone_children(bone_names[0])],
        }

    result = {
        "schema": 1,
        "status": "passed" if not load_failures else "failed",
        "read_only": True,
        "roots": list(roots),
        "player_anim_blueprint": PLAYER_ANIM_BLUEPRINT,
        "asset_count": len(rows),
        "counts_by_root": dict(sorted(by_root.items())),
        "counts_by_class": dict(sorted(by_class.items())),
        "player_dependency_package_count": len(closure),
        "current_locomotion_dependencies": current_locomotion_dependencies,
        "all_locomotion_sequences": all_locomotion,
        "unused_locomotion_sequences": unused_locomotion,
        "protected_locomotion_sequences": protected,
        "target_skeletons": target_skeletons,
        "protection_rule": (
            "Audit only: the DAS AnimSequences in the current ABP_Player dependency closure. "
            "Unused source, InGame, and runtime locomotion sequences remain eligible for "
            "source-timing restoration while their authored non-bone data is preserved."
        ),
        "load_failures": load_failures,
        "assets": rows,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "asset_count": result["asset_count"],
                "counts_by_root": result["counts_by_root"],
                "current_locomotion_dependencies": len(current_locomotion_dependencies),
                "all_locomotion_sequences": len(all_locomotion),
                "unused_locomotion_sequences": len(unused_locomotion),
                "protected_locomotion_sequences": len(protected),
                "load_failures": len(load_failures),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
