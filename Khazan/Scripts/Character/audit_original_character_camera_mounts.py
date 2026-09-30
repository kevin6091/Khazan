"""Audit saved FModel/ActorX evidence for character camera attachment points.

This is a read-only filesystem audit.  It records direct camera attachments in
the exported level JSON set, Player camera-named ActorX reference records, and
the available Yetuga/BigBear Skeleton socket metadata.
"""

from __future__ import annotations

import json
import pathlib
import struct
import traceback


PROJECT = pathlib.Path(__file__).resolve().parents[2]
DESKTOP_ARCHIVE = pathlib.Path.home() / "Desktop" / "\uce74\uc794"
PLAYER_PSK = (
    DESKTOP_ARCHIVE
    / "BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Model/C_P_Kazan.psk"
)
PLAYER_STAND_PSA = (
    DESKTOP_ARCHIVE
    / "BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/Normal/CA_P_Kazan_Stand.psa"
)
LEVEL_ROOT = DESKTOP_ARCHIVE / "Exports/BBQ/Content/_Kazan_/Level"
YETUGA_SKELETON_JSON = (
    DESKTOP_ARCHIVE
    / "EnemyExtracts/Yetuga_20260911/Metadata/BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/Model/C_M_Yetuga_Skeleton.json"
)
BIG_BEAR_SKELETON_JSON = (
    DESKTOP_ARCHIVE
    / "EnemyExtracts/BigBear_20260910/Metadata/BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/BigBear/Model/C_M_BigBear_Skeleton.json"
)
REPORT = PROJECT / "Saved/ImportReports/KZ_OriginalCharacterCameraMountAudit_20260930.json"

CHUNK_HEADER = struct.Struct("<20siii")
REFERENCE_RECORD = struct.Struct("<64s3i11f")
CAMERA_NAMES = {"Cine_Cam_Start", "Cine_Cam_End", "LookAt01"}


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def actorx_chunks(path: pathlib.Path):
    data = path.read_bytes()
    offset = 0
    result = {}
    while offset < len(data):
        tag, flags, size, count = CHUNK_HEADER.unpack_from(data, offset)
        offset += CHUNK_HEADER.size
        name = tag.split(b"\0", 1)[0].decode("ascii")
        payload = data[offset : offset + size * count]
        offset += size * count
        result[name] = {"flags": flags, "size": size, "count": count, "payload": payload}
    if offset != len(data):
        raise RuntimeError("ActorX chunk boundary mismatch: " + str(path))
    return result


def reference_rows(path: pathlib.Path, chunk_name: str):
    chunk = actorx_chunks(path)[chunk_name]
    if chunk["size"] != REFERENCE_RECORD.size:
        raise RuntimeError("Unexpected ActorX reference record size")
    rows = []
    for index, values in enumerate(REFERENCE_RECORD.iter_unpack(chunk["payload"])):
        name = values[0].split(b"\0", 1)[0].decode("utf-8")
        rows.append(
            {
                "index": index,
                "name": name,
                "flags": values[1],
                "child_count": values[2],
                "parent_index": values[3],
                "reference_translation": {
                    "x": values[8],
                    "y": values[9],
                    "z": values[10],
                },
            }
        )
    for row in rows:
        parent = row["parent_index"]
        row["parent_name"] = rows[parent]["name"] if 0 <= parent < len(rows) else None
    return rows


def original_sockets(path: pathlib.Path):
    rows = []
    for value in read_json(path):
        if value.get("Type") != "SkeletalMeshSocket":
            continue
        properties = value.get("Properties") or {}
        rows.append(
            {
                "name": properties.get("SocketName"),
                "parent_bone": properties.get("BoneName"),
            }
        )
    return rows


def scan_level_cameras():
    files = sorted(LEVEL_ROOT.rglob("*.json"))
    cine_camera_count = 0
    direct_external_root_attachments = []
    failed = []
    per_file_camera_counts = {}

    for path in files:
        try:
            values = read_json(path)
        except Exception as error:
            failed.append({"path": str(path), "error": str(error)})
            continue
        if not isinstance(values, list):
            continue
        relative = path.relative_to(LEVEL_ROOT).as_posix()
        file_camera_count = sum(
            1 for value in values if isinstance(value, dict) and value.get("Type") == "CineCameraActor"
        )
        if file_camera_count:
            per_file_camera_counts[relative] = file_camera_count
            cine_camera_count += file_camera_count

        for value in values:
            if not isinstance(value, dict) or value.get("Type") != "SceneComponent":
                continue
            outer = value.get("Outer") or {}
            outer_name = outer.get("ObjectName", "")
            if not outer_name.startswith("CineCameraActor'"):
                continue
            properties = value.get("Properties") or {}
            parent = properties.get("AttachParent")
            if not isinstance(parent, dict):
                continue
            parent_name = parent.get("ObjectName", "")
            # The CineCameraComponent-to-own-root relation is internal.  This
            # records only the camera actor root attached to another object.
            if outer_name.split("'", 1)[1].split("'", 1)[0] in parent_name:
                continue
            direct_external_root_attachments.append(
                {
                    "level_export": relative,
                    "camera_actor": outer_name,
                    "attach_parent": parent_name,
                    "attach_parent_path": parent.get("ObjectPath"),
                    "attach_socket_name": properties.get("AttachSocketName"),
                }
            )

    boss_cutscene_rows = {}
    for relative in (
        "HeinMach/HeinMach_Cine_BossStart.json",
        "HeinMach/HeinMach_Cine_BossEnd.json",
    ):
        path = LEVEL_ROOT / relative
        values = read_json(path)
        serialized = json.dumps(values, ensure_ascii=False)
        boss_cutscene_rows[relative] = {
            "cine_camera_actor_count": sum(
                1 for value in values if isinstance(value, dict) and value.get("Type") == "CineCameraActor"
            ),
            "contains_attach_socket_name": "AttachSocketName" in serialized,
            "contains_cutscene_character_flag": "bUseCutSceneLevelSequence" in serialized,
        }

    return {
        "json_files_scanned": len(files),
        "json_files_failed": failed,
        "cine_camera_actor_count": cine_camera_count,
        "cine_camera_actors_by_export": per_file_camera_counts,
        "direct_external_camera_root_attachments": direct_external_root_attachments,
        "boss_cutscene_level_exports": boss_cutscene_rows,
    }


def main():
    result = {
        "schema_version": 1,
        "date": "2026-09-30",
        "status": "running",
        "scope": "Read-only saved original ActorX/FModel metadata audit.",
    }
    try:
        player_mesh_rows = reference_rows(PLAYER_PSK, "REFSKELT")
        player_anim_rows = reference_rows(PLAYER_STAND_PSA, "BONENAMES")
        result["player_actorx"] = {
            "mesh_source": str(PLAYER_PSK),
            "mesh_reference_record_count": len(player_mesh_rows),
            "camera_named_mesh_reference_records": [
                row for row in player_mesh_rows if row["name"] in CAMERA_NAMES
            ],
            "animation_source": str(PLAYER_STAND_PSA),
            "animation_reference_record_count": len(player_anim_rows),
            "camera_named_animation_reference_records": [
                row for row in player_anim_rows if row["name"] in CAMERA_NAMES
            ],
        }
        result["boss_skeleton_metadata"] = {
            "yetuga": {
                "source": str(YETUGA_SKELETON_JSON),
                "sockets": original_sockets(YETUGA_SKELETON_JSON),
            },
            "big_bear": {
                "source": str(BIG_BEAR_SKELETON_JSON),
                "sockets": original_sockets(BIG_BEAR_SKELETON_JSON),
            },
        }
        result["level_camera_scan"] = scan_level_cameras()
        result["status"] = "passed"
    except Exception:
        result["status"] = "failed"
        result["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("KZ_ORIGINAL_CHARACTER_CAMERA_MOUNT_AUDIT_PASSED")


if __name__ == "__main__":
    main()
