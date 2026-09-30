"""Read-only audit of character camera mount candidates.

The audit distinguishes authored Skeleton/SkeletalMesh sockets from reference
bones that Unreal can also accept as an attachment socket name.  It also reads
the saved Blueprint CDO component hierarchy, but never saves an asset.
"""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = PROJECT / "Saved/ImportReports/KZ_CharacterCameraMountAudit_20260930.json"

MESHES = {
    "player": "/Game/_Art/Player/Character/Meshs/SKM_Player",
    "yetuga_boss": "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga",
    "yetuga_ice_rock": "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Meshes/SK_EN_Yetuga_IceRock",
    "big_bear": "/Game/_Art/Enemies/Shared/Beasts/BigBear/Meshes/SK_EN_BigBear",
    "apes_stone_hand_elite": "/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Meshes/SK_EN_ApesStoneHandElite",
}

BLUEPRINTS = {
    "player": "/Game/_Art/Player/Character/Bluprints/BP_Player",
    "yetuga_boss": "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Blueprints/BP_EN_Boss_Yetuga",
    "big_bear_v1": "/Game/_Art/Enemies/Shared/Beasts/BigBear/Blueprints/BP_EN_BigBear_V01",
}

EXPLICIT_CANDIDATES = {
    "Cine_Cam_Start",
    "Cine_Cam_End",
    "Camera",
    "CameraSocket",
    "CameraRoot",
    "CameraPivot",
    "LookAt01",
}


def asset_path(value) -> str | None:
    if value is None:
        return None
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def vector(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def rotator(value):
    if value is None:
        return None
    return {
        "pitch": float(value.pitch),
        "yaw": float(value.yaw),
        "roll": float(value.roll),
    }


def socket_row(socket):
    return {
        "name": str(socket.socket_name),
        "parent_bone": str(socket.bone_name),
        "relative_location_cm": vector(socket.get_editor_property("relative_location")),
        "relative_rotation_deg": rotator(socket.get_editor_property("relative_rotation")),
        "relative_scale": vector(socket.get_editor_property("relative_scale")),
    }


def audit_mesh(path: str):
    mesh = unreal.load_asset(path)
    if mesh is None:
        return {"asset": path, "loaded": False}

    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skinned_asset_and_update(mesh)
    skeleton = mesh.get_editor_property("skeleton")
    reference_pose = skeleton.get_reference_pose()
    bones = [str(component.get_bone_name(index)) for index in range(component.get_num_bones())]
    sockets = [socket_row(mesh.get_socket_by_index(index)) for index in range(mesh.num_sockets())]
    socket_names = {row["name"] for row in sockets}
    bone_names = set(bones)

    candidate_names = sorted(
        name
        for name in socket_names | bone_names
        if name in EXPLICIT_CANDIDATES
        or "camera" in name.lower()
        or "cine_cam" in name.lower()
    )
    candidates = []
    for name in candidate_names:
        kinds = []
        if name in socket_names:
            kinds.append("authored_socket")
        if name in bone_names:
            kinds.append("reference_bone")
        candidate = {
            "name": name,
            "kinds": kinds,
            "bone_index": bones.index(name) if name in bone_names else None,
            "parent_bone": str(component.get_parent_bone(name)) if name in bone_names else None,
            "accepted_by_scene_attachment_api": bool(component.does_socket_exist(name)),
        }
        if name in bone_names:
            local_pose = reference_pose.get_bone_pose(name)
            candidate["reference_pose_local_location"] = vector(local_pose.translation)
            candidate["reference_pose_local_rotation_deg"] = rotator(local_pose.rotation.rotator())
        candidates.append(candidate)

    return {
        "asset": path,
        "loaded": True,
        "skeleton": asset_path(skeleton),
        "reference_bone_count": len(bones),
        "authored_socket_count": len(sockets),
        "authored_sockets": sockets,
        "camera_mount_candidates": candidates,
    }


def component_row(component):
    row = {
        "name": str(component.get_name()),
        "class": str(component.get_class().get_name()),
    }
    if isinstance(component, unreal.SceneComponent):
        parent = component.get_attach_parent()
        row.update(
            {
                "attach_parent": str(parent.get_name()) if parent else None,
                "attach_socket_name": str(component.get_attach_socket_name()),
                "relative_location_cm": vector(component.get_editor_property("relative_location")),
                "relative_rotation_deg": rotator(component.get_editor_property("relative_rotation")),
                "relative_scale": vector(component.get_editor_property("relative_scale3d")),
            }
        )
    if isinstance(component, unreal.SpringArmComponent):
        row.update(
            {
                "target_arm_length_cm": float(component.get_editor_property("target_arm_length")),
                "use_pawn_control_rotation": bool(component.get_editor_property("use_pawn_control_rotation")),
                "camera_lag_enabled": bool(component.get_editor_property("enable_camera_lag")),
                "camera_rotation_lag_enabled": bool(component.get_editor_property("enable_camera_rotation_lag")),
            }
        )
    if isinstance(component, unreal.CameraComponent):
        row["field_of_view_deg"] = float(component.get_editor_property("field_of_view"))
    return row


def audit_blueprint(path: str):
    blueprint = unreal.load_asset(path)
    if blueprint is None:
        return {"asset": path, "loaded": False}
    generated_class = blueprint.generated_class()
    cdo = unreal.get_default_object(generated_class)
    components = list(cdo.get_components_by_class(unreal.ActorComponent))
    rows = [component_row(component) for component in components]
    return {
        "asset": path,
        "loaded": True,
        "generated_class": asset_path(generated_class),
        "camera_or_spring_arm_components": [
            row for row in rows if row["class"] in {"CameraComponent", "CineCameraComponent", "SpringArmComponent"}
        ],
        "scene_components": [row for row in rows if "attach_parent" in row],
    }


def main():
    result = {
        "schema_version": 1,
        "date": "2026-09-30",
        "status": "running",
        "scope": "Read-only current UE asset audit; no asset save is performed.",
        "meshes": {},
        "blueprints": {},
    }
    try:
        result["meshes"] = {key: audit_mesh(path) for key, path in MESHES.items()}
        result["blueprints"] = {key: audit_blueprint(path) for key, path in BLUEPRINTS.items()}
        result["status"] = "passed"
    except Exception:
        result["status"] = "failed"
        result["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("KZ_CHARACTER_CAMERA_MOUNT_AUDIT_PASSED", flush=True)


if __name__ == "__main__":
    main()
