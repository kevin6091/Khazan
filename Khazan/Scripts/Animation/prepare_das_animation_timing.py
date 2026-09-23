"""Build source-timed DualAxeSword pose data for Unreal import.

Original source sequences and unused locomotion derivatives are rebuilt from
cooked AnimSequence metadata and the original ActorX samples.  The nine current
ABP locomotion dependencies remain audit-only.  Skill AnimComposites become
standalone playback sequences with their original basenames and with segment
trims, rates, loops, and DilationCurve timing baked into every retained bone
track, including Root.
"""

from __future__ import annotations

import bisect
import collections
import fractions
import hashlib
import json
import math
import pathlib
import struct
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
AUDIT = PROJECT / "Saved/ImportReports/Khazan_DAS_OriginalMetadataAudit_20260916.json"
INVENTORY = PROJECT / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"
SKILL_METADATA = ROOT / "MetadataSkill"
DERIVED = ROOT / "Derived/AnimationData"
MANIFEST = ROOT / "AnimationImportManifest.json"
EVENTS = ROOT / "PlaybackEvents.json"
TIMING = ROOT / "AnimationTimingAudit.json"
SUMMARY = ROOT / "PreparationSummary.json"
RUNTIME_BUILD = PROJECT / "Saved/ImportReports/Khazan_DAS_Locomotion_RuntimeBuild.json"

sys.path.insert(0, str(PROJECT / "Saved/ArtTools/EnemyPython"))
import numpy as np


HEADER = struct.Struct("<20siii")
ANIM_INFO = struct.Struct("<64s64s4i3f3i")
SERIALIZED_TIME_EPSILON = 1.0e-6
COMPOSITE_PLAYBACK_FRAME_RATE = fractions.Fraction(60, 1)
COMPOSITE_TIMING_VERSION = "20260917_DAS_CompositeExact60HzV5"
PLAYER_SOURCE_SKELETON = (
    "BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Model/C_P_Kazan_Skeleton"
)
WEAPON_SOURCE_SKELETON = (
    "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Item/DualAxeSword/Model/"
    "C_I_DualAxeSword_ImperialGuard001_R/C_I_DualAxeSword_ImperialGuard001_R_Skeleton"
)
PLAYER_SKELETON = "/Game/_Art/Player/Character/Meshs/SK_Player"
PLAYER_MESH = "/Game/_Art/Player/Character/Meshs/SKM_Player"
# This compensation is derived only from the target skeleton's inserted root.
# A Character mesh-component scale is runtime state and must never enter asset data.
PLAYER_INSERTED_ROOT_REFERENCE_UNIFORM_SCALE = 100.0
PLAYER_ROOT_MOTION_TRANSLATION_SCALE = (
    1.0 / PLAYER_INSERTED_ROOT_REFERENCE_UNIFORM_SCALE
)
WEAPON_SKELETON = "/Game/_Art/Player/Item/Imperial/DualAxeSword_Imperial_R_Skeleton"
WEAPON_MESH = "/Game/_Art/Player/Item/Imperial/DualAxeSword_Imperial_R"
RECOVERED_ROOT = "/Game/_Art/Player/Animation/Weapons/DualAxeSword/Recovered"
INGAME_LOCOMOTION_ROOT = "/Game/_Art/Player/Animation/InGame/DAS/Locomotion"
RUNTIME_LOCOMOTION_ROOT = "/Game/_Art/Player/Animation/Locomotion/Runtime/DualAxeSword"


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package(value) -> str:
    if isinstance(value, dict):
        value = value.get("ObjectPath", value.get("AssetPathName", ""))
    if not isinstance(value, str):
        return ""
    return value.split(".", 1)[0].replace("/Game/", "BBQ/Content/")


def chunks(path: pathlib.Path) -> dict[str, tuple[int, int, bytes]]:
    data = path.read_bytes()
    offset = 0
    result = {}
    while offset < len(data):
        tag, flags, size, count = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        payload = data[offset : offset + size * count]
        offset += size * count
        result[tag.split(b"\0", 1)[0].decode("ascii")] = (size, count, payload)
    if offset != len(data):
        raise RuntimeError("ActorX chunk boundary mismatch: " + str(path))
    return result


def source_pose(row: dict, target_track_names: list[str] | None):
    source_path = pathlib.Path(row["psa_file"])
    values = chunks(source_path)
    bone_size, bone_count, raw_bones = values["BONENAMES"]
    source_bones = [
        raw_bones[index * bone_size : index * bone_size + 64]
        .split(b"\0", 1)[0]
        .decode("utf-8", errors="replace")
        for index in range(bone_count)
    ]
    lower_to_index = {name.lower(): index for index, name in enumerate(source_bones)}
    selected = (
        list(source_bones)
        if target_track_names is None
        else [name for name in target_track_names if name.lower() in lower_to_index]
    )
    indices = [lower_to_index[name.lower()] for name in selected]
    if not selected:
        raise RuntimeError("No target skeleton tracks exist in " + row["source_package"])

    info = ANIM_INFO.unpack(values["ANIMINFO"][2][: ANIM_INFO.size])
    frame_count = int(info[-1])
    if frame_count != row["num_frames"]:
        raise RuntimeError(
            f"PSA/source NumFrames mismatch {row['source_package']}: {frame_count} != {row['num_frames']}"
        )
    key_size, key_count, key_payload = values["ANIMKEYS"]
    if key_size != 32 or key_count != frame_count * bone_count:
        raise RuntimeError("Unexpected ActorX key layout: " + row["source_package"])
    keys = np.frombuffer(key_payload, dtype="<f4").reshape(frame_count, bone_count, 8)[:, indices]
    pose = np.empty((frame_count, len(indices), 10), dtype=np.float32)
    pose[:, :, :3] = keys[:, :, :3]
    pose[:, :, 1] *= -1
    pose[:, :, 3:7] = keys[:, :, 3:7]
    pose[:, :, 4] *= -1
    # ActorX's first skeleton record carries the top-level handedness sign.
    if indices and indices[0] == 0:
        pose[:, 0, 6] *= -1
    norms = np.linalg.norm(pose[:, :, 3:7], axis=2, keepdims=True)
    if not np.all(norms > 0):
        raise RuntimeError("Zero-length quaternion: " + row["source_package"])
    pose[:, :, 3:7] /= norms
    if "SCALEKEYS" in values:
        scale_size, scale_count, scale_payload = values["SCALEKEYS"]
        if scale_size != 16 or scale_count != frame_count * bone_count:
            raise RuntimeError("Unexpected ActorX scale layout: " + row["source_package"])
        pose[:, :, 7:10] = np.frombuffer(scale_payload, dtype="<f4").reshape(
            frame_count, bone_count, 4
        )[:, indices, :3]
    else:
        pose[:, :, 7:10] = 1.0
    return selected, pose, {
        "source_bone_count": bone_count,
        "retained_track_count": len(selected),
        "omitted_source_track_count": bone_count - len(selected),
        "target_skeleton_track_count": (
            len(source_bones) if target_track_names is None else len(target_track_names)
        ),
        "target_tracks_absent_from_source_layout": [
            name
            for name in (target_track_names or source_bones)
            if name.lower() not in lower_to_index
        ],
    }


def interpolate_pose(pose, seconds, length):
    frame_positions = np.clip(
        np.asarray(seconds, dtype=np.float64) / length * (len(pose) - 1),
        0,
        len(pose) - 1,
    )
    lower = np.floor(frame_positions).astype(np.int64)
    upper = np.minimum(lower + 1, len(pose) - 1)
    alpha = (frame_positions - lower).astype(np.float32)[:, None, None]
    first = pose[lower]
    second = pose[upper].copy()
    dot = np.sum(first[:, :, 3:7] * second[:, :, 3:7], axis=2)
    second[:, :, 3:7] *= np.where(dot < 0, -1, 1)[:, :, None]
    result = first * (1 - alpha) + second * alpha
    result[:, :, 3:7] /= np.linalg.norm(result[:, :, 3:7], axis=2, keepdims=True)
    return result


def quat_multiply(left, right):
    """Hamilton product matching Unreal's FQuat operator*."""
    lx, ly, lz, lw = [float(value) for value in left]
    rx, ry, rz, rw = [float(value) for value in right]
    result = np.asarray(
        [
            lw * rx + lx * rw + ly * rz - lz * ry,
            lw * ry - lx * rz + ly * rw + lz * rx,
            lw * rz + lx * ry - ly * rx + lz * rw,
            lw * rw - lx * rx - ly * ry - lz * rz,
        ],
        dtype=np.float64,
    )
    norm = np.linalg.norm(result)
    if norm <= 0:
        raise RuntimeError("Zero-length quaternion during Composite root-motion bake")
    return result / norm


def quat_inverse(value):
    value = np.asarray(value, dtype=np.float64)
    denominator = float(np.dot(value, value))
    if denominator <= 0:
        raise RuntimeError("Zero-length quaternion during Composite root-motion inverse")
    return np.asarray([-value[0], -value[1], -value[2], value[3]], dtype=np.float64) / denominator


def quat_rotate(value, vector):
    value = np.asarray(value, dtype=np.float64)
    vector = np.asarray(vector, dtype=np.float64)
    axis = value[:3]
    return vector + 2.0 * np.cross(axis, np.cross(axis, vector) + value[3] * vector)


def normalized_root_transform(value):
    result = np.asarray(value, dtype=np.float64).copy()
    norm = np.linalg.norm(result[3:7])
    if norm <= 0:
        raise RuntimeError("Zero-length root quaternion")
    result[3:7] /= norm
    # UAnimSequence::ExtractRootMotionFromRange clears root scale when
    # bUseNormalizedRootMotionScale is enabled. Every recovered player Root
    # track is authored at unit scale, and the baked playback assets preserve
    # that engine contract explicitly.
    result[7:10] = 1.0
    return result


def multiply_transform(first, second):
    """Return first * second with UE FTransform multiplication order."""
    first = normalized_root_transform(first)
    second = normalized_root_transform(second)
    result = np.empty(10, dtype=np.float64)
    result[3:7] = quat_multiply(second[3:7], first[3:7])
    result[:3] = quat_rotate(second[3:7], second[7:10] * first[:3]) + second[:3]
    result[7:10] = first[7:10] * second[7:10]
    return result


def relative_transform(value, base):
    """Return value.GetRelativeTransform(base) using UE's VQS equations."""
    value = normalized_root_transform(value)
    base = normalized_root_transform(base)
    inverse = quat_inverse(base[3:7])
    result = np.empty(10, dtype=np.float64)
    result[3:7] = quat_multiply(inverse, value[3:7])
    result[:3] = quat_rotate(inverse, value[:3] - base[:3]) / base[7:10]
    result[7:10] = value[7:10] / base[7:10]
    return result


def root_delta_error(left, right):
    left = normalized_root_transform(left)
    right = normalized_root_transform(right)
    translation = float(np.linalg.norm(left[:3] - right[:3]))
    rotation = float(1.0 - min(1.0, abs(float(np.dot(left[3:7], right[3:7])))))
    return translation, rotation


def active_dilation(properties: dict):
    curve = properties.get("DilationCurve", {})
    positions = curve.get("DilationAnimPositions", [])
    active = bool(
        positions
        and curve.get("BakedDilationCurveName")
        and properties.get("ApplyDilationCurveType") != "EApplyDilationCurveType::None"
    )
    if active:
        dilated = [float(value["T_Dilation"]) for value in positions]
        original = [float(value["T_Original"]) for value in positions]
        if not all(right > left for left, right in zip(dilated, dilated[1:])):
            raise RuntimeError("Non-monotonic Dilation time")
        if not all(right >= left for left, right in zip(original, original[1:])):
            raise RuntimeError("Non-monotonic source time")
        if abs(dilated[-1] - float(curve["DilationSequenceLength"])) >= 0.0001:
            raise RuntimeError("DilationSequenceLength differs from final mapping point")
    return active, curve


def mapped_events(
    source_package: str,
    destination: str,
    properties: dict,
    active: bool,
    curve: dict,
    authored_duration: float,
    quantized_duration: float,
):
    timeline_scale = quantized_duration / authored_duration
    if active:
        x = [float(value["T_Dilation"]) for value in curve["DilationAnimPositions"]]
        y = [float(value["T_Original"]) for value in curve["DilationAnimPositions"]]

        def to_playback(value: float) -> float:
            return float(np.interp(value, y, x)) * timeline_scale

    else:

        def to_playback(value: float) -> float:
            return float(value) * timeline_scale

    rows = []
    for index, notify in enumerate(properties.get("Notifies", [])):
        original_start = float(notify.get("LinkValue", 0.0) + notify.get("TriggerTimeOffset", 0.0))
        end_link = notify.get("EndLink", {})
        original_end = float(
            end_link.get("LinkValue", original_start + notify.get("Duration", 0.0))
            + notify.get("EndTriggerTimeOffset", 0.0)
        )
        rows.append(
            {
                "source_package": source_package,
                "playback_asset": destination,
                "notify_index": index,
                "name": notify.get("NotifyName"),
                "source_type": notify.get("Notify") or notify.get("NotifyStateClass"),
                "original_start_seconds": original_start,
                "original_end_seconds": original_end,
                "playback_start_seconds": to_playback(original_start),
                "playback_end_seconds": to_playback(original_end),
                "contract": "Original event times are mapped to playback time; proprietary behavior remains metadata and is not instantiated as a UE notify.",
            }
        )
    return rows


def metadata_composites() -> dict[str, dict]:
    result = {}
    for path in SKILL_METADATA.rglob("*.json"):
        if path.name == "MetadataExtractionReport.json":
            continue
        for value in read(path):
            if value.get("Type") == "AnimComposite":
                result[value["Package"].lower()] = value
    return result


def topology_adapter(target_skeleton: str) -> dict:
    if target_skeleton == PLAYER_SKELETON:
        return {
            "inserted_root_bone": "C_P_Kazan",
            "source_motion_bone": "Root",
            "root_motion_translation_scale": PLAYER_ROOT_MOTION_TRANSLATION_SCALE,
            "contract": (
                "Move the source Root local transform onto the inserted C_P_Kazan skeleton "
                "root and hold Root at reference pose. For Root-Motion-enabled player clips, "
                "multiply only the transferred C_P_Kazan translation relative to its reference "
                f"origin by {PLAYER_ROOT_MOTION_TRANSLATION_SCALE:g}, cancelling the inserted "
                f"root's reference scale of {PLAYER_INSERTED_ROOT_REFERENCE_UNIFORM_SCALE:g} "
                "before UE "
                "root-motion extraction from skeleton bone index zero. Rotation and scale remain "
                "unchanged."
            ),
        }
    if target_skeleton == WEAPON_SKELETON:
        return {
            "inserted_root_bone": "C_I_DualAxeSword_ImperialGuard001_R",
            "source_motion_bone": "Weapon_R",
            "contract": (
                "Move the original Weapon_R root transform onto the mesh-import root and hold "
                "Weapon_R at reference pose, preserving the original weapon component pose."
            ),
        }
    raise RuntimeError("Missing topology adapter for " + target_skeleton)


def inventory_root_lock(value) -> str:
    text = str(value).upper()
    if "ANIM_FIRST_FRAME" in text or "ANIMFIRSTFRAME" in text:
        return "AnimFirstFrame"
    if "REF_POSE" in text or "REFPOSE" in text:
        return "RefPose"
    if "ZERO" in text:
        return "Zero"
    raise RuntimeError("Unsupported inventory root-motion lock: " + str(value))


def current_locomotion_properties(row: dict) -> dict:
    return {
        "bEnableRootMotion": bool(row["enable_root_motion"]),
        "bForceRootLock": bool(row["force_root_lock"]),
        "RootMotionRootLock": inventory_root_lock(row["root_motion_root_lock"]),
    }


def remapped_sync_markers(row: dict, target_rate: float, target_duration: float) -> list[dict]:
    source_rate = float(row["fps"][0]) / float(row["fps"][1])
    result = []
    for track, markers in row.get("sync_markers", {}).items():
        for marker in markers:
            source_time = float(marker["time"])
            source_frame = source_time * source_rate
            target_time = source_frame / target_rate
            if target_time < -SERIALIZED_TIME_EPSILON or target_time > target_duration + 1.0e-5:
                raise RuntimeError(
                    f"Remapped sync marker leaves target timeline: {row['asset']} {marker}"
                )
            result.append(
                {
                    "track": track,
                    "name": marker["name"],
                    "source_time": source_time,
                    "source_frame": source_frame,
                    "target_time": min(target_duration, max(0.0, target_time)),
                }
            )
    return result


def main() -> None:
    audit = read(AUDIT)
    inventory = read(INVENTORY)
    runtime_build = read(RUNTIME_BUILD)
    if audit["status"] != "passed" or inventory["status"] != "passed":
        raise RuntimeError("Source audit and UE inventory must pass before pose preparation")
    source_rows = {row["source_package"].lower(): row for row in audit["sources"]}
    source_rows_by_name = {row["source_name"].lower(): row for row in audit["sources"]}
    composite_rows = {row["source_package"].lower(): row for row in audit["composites"]}
    composite_objects = metadata_composites()
    inventory_by_asset = {row.get("asset"): row for row in inventory["assets"]}

    canonical = next(
        row
        for row in inventory["assets"]
        if row.get("name") == "CA_P_Kazan_DualAxeSword_Off_FastAtk01_M1"
    )
    player_target_tracks = list(canonical["track_names"])
    if len(player_target_tracks) != 226:
        raise RuntimeError("Unexpected current SK_Player animation track contract")
    weapon_target_tracks = list(
        inventory["target_skeletons"][WEAPON_SKELETON]["bone_names"]
    )
    if {name.lower() for name in weapon_target_tracks} != {
        "c_i_dualaxesword_imperialguard001_r",
        "weapon_r",
        "fx",
    }:
        raise RuntimeError("Unexpected Imperial right-weapon skeleton contract")

    def target_contract(row: dict):
        source_skeleton = row["source_skeleton"]
        if source_skeleton == PLAYER_SOURCE_SKELETON:
            return PLAYER_SKELETON, PLAYER_MESH, player_target_tracks
        if source_skeleton == WEAPON_SOURCE_SKELETON:
            # This layout belongs to the right Imperial DualAxeSword skeletal
            # mesh. The project mesh has an inserted mesh-root and an FX bone;
            # Weapon_R is the single source-authored track shared by both.
            return WEAPON_SKELETON, WEAPON_MESH, weapon_target_tracks
        raise RuntimeError("Unmapped source skeleton: " + str(source_skeleton))

    DERIVED.mkdir(parents=True, exist_ok=True)
    output_rows = []
    timing_rows = []
    playback_events = []
    source_cache = {}
    track_diagnostics = {}

    def load_source(source_package: str):
        key = source_package.lower()
        if key not in source_cache:
            row = source_rows[key]
            _, _, target_tracks = target_contract(row)
            bones, pose, diagnostics = source_pose(row, target_tracks)
            source_cache[key] = (bones, pose)
            track_diagnostics[row["source_package"]] = diagnostics
        return source_cache[key]

    def source_rate(source_package: str) -> float:
        row = source_rows[source_package.lower()]
        return (row["num_frames"] - 1) / row["sequence_length_seconds"]

    def source_fps(row: dict) -> fractions.Fraction:
        return fractions.Fraction(
            (row["num_frames"] - 1) / row["sequence_length_seconds"]
        ).limit_denominator(100000)

    def source_properties(row: dict) -> dict:
        result = {
            "bEnableRootMotion": row["enable_root_motion"],
            "bForceRootLock": row["force_root_lock"],
        }
        for source_key, target_key in (
            ("root_motion_root_lock", "RootMotionRootLock"),
            ("additive_anim_type", "AdditiveAnimType"),
            ("ref_pose_type", "RefPoseType"),
            ("ref_frame_index", "RefFrameIndex"),
        ):
            if row.get(source_key) is not None:
                result[target_key] = row[source_key]
        return result

    def leaf_packages(source_package: str, stack=()):
        key = source_package.lower()
        if key in source_rows:
            return [source_rows[key]["source_package"]]
        if key in stack:
            raise RuntimeError("Recursive Composite graph: " + source_package)
        composite = composite_objects[key]
        result = []
        for segment in composite.get("Properties", {}).get("AnimationTrack", {}).get("AnimSegments", []):
            result.extend(leaf_packages(package(segment["AnimReference"]), stack + (key,)))
        return result

    def leaf_rates(source_package: str):
        return [source_rate(value) for value in leaf_packages(source_package)]

    def evaluate(source_package: str, times, stack=()):
        key = source_package.lower()
        if key in source_rows:
            row = source_rows[key]
            bones, pose = load_source(row["source_package"])
            return bones, interpolate_pose(pose, times, row["sequence_length_seconds"])
        if key in stack:
            raise RuntimeError("Recursive Composite pose graph: " + source_package)
        composite = composite_objects[key]
        properties = composite["Properties"]
        segments = properties["AnimationTrack"]["AnimSegments"]
        result = None
        output_bones = None
        for segment in segments:
            rate = float(segment["AnimPlayRate"])
            if rate == 0:
                raise RuntimeError("Zero AnimPlayRate: " + source_package)
            span = float(segment["AnimEndTime"] - segment["AnimStartTime"])
            end = float(segment["StartPos"]) + span / abs(rate) * int(segment["LoopingCount"])
            selected = (times >= float(segment["StartPos"]) - SERIALIZED_TIME_EPSILON) & (
                times <= end + SERIALIZED_TIME_EPSILON
            )
            elapsed = np.clip(
                (times[selected] - float(segment["StartPos"])) * abs(rate),
                0,
                span * int(segment["LoopingCount"]),
            )
            local = np.mod(elapsed, span)
            local = np.where(
                elapsed >= span * int(segment["LoopingCount"]) - SERIALIZED_TIME_EPSILON,
                span,
                local,
            )
            local = (
                float(segment["AnimStartTime"]) + local
                if rate > 0
                else float(segment["AnimEndTime"]) - local
            )
            child_package = package(segment["AnimReference"])
            child_bones, child_pose = evaluate(child_package, local, stack + (key,))
            if result is None:
                result = np.empty((len(times), len(child_bones), 10), dtype=np.float32)
                result[:] = np.nan
                output_bones = child_bones
            if child_bones != output_bones:
                raise RuntimeError("Composite skeleton/track mismatch: " + source_package)
            result[selected] = child_pose
        if result is None or not np.isfinite(result).all():
            raise RuntimeError("Uncovered Composite time: " + source_package)
        return output_bones, result

    source_root_cache = {}

    def source_root_track(source_package: str):
        key = source_package.lower()
        if key not in source_root_cache:
            bones, source_pose_values = load_source(source_package)
            matches = [index for index, name in enumerate(bones) if name.lower() == "root"]
            if len(matches) != 1:
                raise RuntimeError("Player source does not have exactly one Root track: " + source_package)
            source_root_cache[key] = np.asarray(
                source_pose_values[:, matches[0], :], dtype=np.float64
            )
        return source_root_cache[key]

    def source_root_delta(source_package: str, start_time: float, end_time: float):
        row = source_rows[source_package.lower()]
        root = source_root_track(source_package)
        sampled = interpolate_pose(
            root[:, None, :],
            np.asarray([start_time, end_time], dtype=np.float64),
            row["sequence_length_seconds"],
        )[:, 0, :]
        return relative_transform(sampled[1], sampled[0])

    def root_extraction_steps(source_package: str, start_time: float, end_time: float, stack=()):
        """Yield leaf AnimSequence ranges using FAnimSegment's forward rules."""
        key = source_package.lower()
        if key in source_rows:
            if abs(end_time - start_time) <= SERIALIZED_TIME_EPSILON:
                return
            yield source_rows[key]["source_package"], float(start_time), float(end_time)
            return
        if end_time < start_time - SERIALIZED_TIME_EPSILON:
            raise RuntimeError("Nested Composite reverse playback is not implemented: " + source_package)
        if end_time <= start_time + SERIALIZED_TIME_EPSILON:
            return
        if key in stack:
            raise RuntimeError("Recursive Composite root-motion graph: " + source_package)
        composite = composite_objects[key]
        segments = composite["Properties"]["AnimationTrack"]["AnimSegments"]
        for segment in segments:
            rate = float(segment["AnimPlayRate"])
            if rate == 0:
                raise RuntimeError("Zero AnimPlayRate: " + source_package)
            anim_start_time = float(segment["AnimStartTime"])
            anim_end_time = float(segment["AnimEndTime"])
            span = anim_end_time - anim_start_time
            if span <= 0:
                raise RuntimeError("Non-positive Composite segment span: " + source_package)
            loop_count = max(1, int(segment["LoopingCount"]))
            segment_start = float(segment["StartPos"])
            segment_end = segment_start + span / abs(rate) * loop_count
            overlap_start = max(float(start_time), segment_start)
            overlap_end = min(float(end_time), segment_end)
            if overlap_end <= overlap_start + SERIALIZED_TIME_EPSILON:
                continue

            unwrapped = (overlap_start - segment_start) * rate
            completed_loops = min(
                math.floor(abs(unwrapped) / span),
                max(loop_count - 1, 0),
            )
            anim_point = anim_start_time if rate >= 0 else anim_end_time
            current = anim_point + (unwrapped - completed_loops * span)
            current = min(anim_end_time, max(anim_start_time, current))
            remaining = overlap_end - overlap_start
            reset = anim_start_time if rate >= 0 else anim_end_time
            endpoint = anim_end_time if rate >= 0 else anim_start_time
            child = package(segment["AnimReference"])

            for _ in range(loop_count + 1):
                if remaining <= SERIALIZED_TIME_EPSILON:
                    break
                track_to_endpoint = abs((endpoint - current) / rate)
                if remaining < track_to_endpoint - SERIALIZED_TIME_EPSILON:
                    child_end = current + remaining * rate
                    yield from root_extraction_steps(
                        child, current, child_end, stack + (key,)
                    )
                    remaining = 0.0
                    break
                yield from root_extraction_steps(
                    child, current, endpoint, stack + (key,)
                )
                remaining -= track_to_endpoint
                current = reset
            if remaining > 1.0e-4:
                raise RuntimeError(
                    f"Composite root extraction did not consume segment range: "
                    f"{source_package} ({remaining})"
                )

    def composite_root_delta(source_package: str, start_time: float, end_time: float):
        total = np.asarray(
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0],
            dtype=np.float64,
        )
        for leaf, leaf_start, leaf_end in root_extraction_steps(
            source_package, start_time, end_time
        ):
            total = multiply_transform(
                source_root_delta(leaf, leaf_start, leaf_end), total
            )
        return total

    def stitch_composite_root(source_package: str, times, bones, pose):
        matches = [index for index, name in enumerate(bones) if name.lower() == "root"]
        if len(matches) != 1:
            raise RuntimeError("Composite player pose does not have exactly one Root track")
        root_index = matches[0]
        raw = np.asarray(pose[:, root_index, :], dtype=np.float64).copy()
        stitched = np.empty_like(raw)
        # Generated gameplay playback always enables Root Motion and uses RefPose
        # locking. Rebase the first root sample to identity so a trimmed child
        # sequence cannot carry a large absolute offset into the standalone bake.
        stitched[0] = np.asarray(
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0],
            dtype=np.float64,
        )
        corrected_intervals = 0
        maximum_raw_contract_error = np.zeros(2, dtype=np.float64)
        maximum_stitched_contract_error = np.zeros(2, dtype=np.float64)
        for index in range(1, len(stitched)):
            expected = composite_root_delta(
                source_package, float(times[index - 1]), float(times[index])
            )
            raw_delta = relative_transform(raw[index], raw[index - 1])
            raw_error = np.asarray(root_delta_error(raw_delta, expected))
            maximum_raw_contract_error = np.maximum(maximum_raw_contract_error, raw_error)
            if raw_error[0] > 0.001 or raw_error[1] > 1.0e-8:
                corrected_intervals += 1
            stitched[index] = multiply_transform(expected, stitched[index - 1])
            if np.dot(stitched[index - 1, 3:7], stitched[index, 3:7]) < 0:
                stitched[index, 3:7] *= -1
            actual = relative_transform(stitched[index], stitched[index - 1])
            maximum_stitched_contract_error = np.maximum(
                maximum_stitched_contract_error,
                np.asarray(root_delta_error(actual, expected)),
            )
        if (
            maximum_stitched_contract_error[0] >= 0.0001
            or maximum_stitched_contract_error[1] >= 1.0e-10
        ):
            raise RuntimeError(
                "Stitched Composite root motion differs from extraction contract: "
                + repr(maximum_stitched_contract_error.tolist())
            )
        raw_steps = np.linalg.norm(np.diff(raw[:, :3], axis=0), axis=1)
        stitched_steps = np.linalg.norm(np.diff(stitched[:, :3], axis=0), axis=1)
        pose[:, root_index, :] = stitched.astype(np.float32)
        return {
            "contract": (
                "Standalone playback Root is rebased at the reference origin and every "
                "leaf segment/trim/reverse/loop delta is accumulated in Unreal FTransform "
                "order before transfer to C_P_Kazan."
            ),
            "initial_raw_root_translation": [float(value) for value in raw[0, :3]],
            "initial_baked_root_translation": [float(value) for value in stitched[0, :3]],
            "endpoint_baked_root_translation": [float(value) for value in stitched[-1, :3]],
            "raw_maximum_translation_step": float(np.max(raw_steps)) if len(raw_steps) else 0.0,
            "baked_maximum_translation_step": (
                float(np.max(stitched_steps)) if len(stitched_steps) else 0.0
            ),
            "corrected_interval_count": corrected_intervals,
            "maximum_raw_interval_contract_error": maximum_raw_contract_error.tolist(),
            "maximum_baked_interval_contract_error": maximum_stitched_contract_error.tolist(),
        }

    # Replace every original source in place, including unused locomotion
    # sources. Missing original packages receive a recovered source asset.
    direct_index = 0
    direct_data_by_source = {}
    for row in sorted(audit["sources"], key=lambda value: value["source_package"]):
        if row["protected_from_modification"]:
            continue
        destination = row["current_asset"] or f"{RECOVERED_ROOT}/{row['source_name']}"
        bones, pose = load_source(row["source_package"])
        target_skeleton, target_mesh, _ = target_contract(row)
        data_file = DERIVED / f"direct_{direct_index:03d}.npy"
        np.save(data_file, pose)
        fps = source_fps(row)
        properties = source_properties(row)
        direct_data_by_source[row["source_package"].lower()] = {
            "file": data_file,
            "sha256": sha256(data_file),
        }
        output_rows.append(
            {
                "kind": "SourceTimelineReplacement",
                "operation": "replace_existing" if row["current_asset"] else "create_missing",
                "source_package": row["source_package"],
                "source_name": row["source_name"],
                "destination": destination,
                "skeleton_destination": target_skeleton,
                "mesh_destination": target_mesh,
                "data_file": str(data_file),
                "data_sha256": direct_data_by_source[row["source_package"].lower()]["sha256"],
                "bones": bones,
                "samples": row["num_frames"],
                "duration": row["sequence_length_seconds"],
                "fps": [fps.numerator, fps.denominator],
                "rate_scale": row["rate_scale"],
                "properties": properties,
                "topology_adapter": topology_adapter(target_skeleton),
                "timing_contract": "Cooked AnimSequence NumFrames/SequenceLength with original PSA pose samples; no Composite dilation applied.",
                "track_diagnostics": track_diagnostics[row["source_package"]],
            }
        )
        timing_rows.append(
            {
                "source": row["source_package"],
                "destination": destination,
                "kind": "SourceTimelineReplacement",
                "source_seconds": row["sequence_length_seconds"],
                "playback_seconds": row["sequence_length_seconds"],
                "fps": [fps.numerator, fps.denominator],
                "samples": row["num_frames"],
                "dilation_applied": False,
            }
        )
        direct_index += 1

    protected_locomotion = set(inventory["protected_locomotion_sequences"])
    all_locomotion = set(inventory["all_locomotion_sequences"])
    unused_locomotion = set(inventory["unused_locomotion_sequences"])
    if protected_locomotion != set(inventory["current_locomotion_dependencies"]):
        raise RuntimeError("Only current ABP locomotion dependencies may be protected")
    if all_locomotion != protected_locomotion | unused_locomotion:
        raise RuntimeError("Locomotion protection partition is incomplete")

    locomotion_index = 0

    def append_unused_locomotion(
        current: dict,
        source: dict,
        pose,
        samples: int,
        fps: fractions.Fraction,
        rate_scale: float,
        properties: dict,
        derivation: dict,
        reuse_data: dict | None = None,
    ) -> None:
        nonlocal locomotion_index
        if current["asset"] in protected_locomotion:
            raise RuntimeError("Current locomotion dependency entered mutation set")
        if current["asset"] not in unused_locomotion:
            raise RuntimeError("Locomotion destination is outside the audited unused set")
        if current.get("notify_events"):
            raise RuntimeError(
                "Unused locomotion has authored notify events requiring a behavior review: "
                + current["asset"]
            )
        if samples < 2 or samples > len(pose):
            raise RuntimeError("Invalid locomotion sample range: " + current["asset"])
        selected = pose[:samples]
        if reuse_data is None:
            data_file = DERIVED / f"locomotion_{locomotion_index:03d}.npy"
            np.save(data_file, selected)
            data_hash = sha256(data_file)
        else:
            if samples != len(pose):
                raise RuntimeError("Cannot reuse full source data for a cropped locomotion asset")
            data_file = reuse_data["file"]
            data_hash = reuse_data["sha256"]
        duration = (samples - 1) * fps.denominator / fps.numerator
        marker_rows = remapped_sync_markers(
            current, fps.numerator / fps.denominator, duration
        )
        bones, _ = load_source(source["source_package"])
        output_rows.append(
            {
                "kind": "UnusedLocomotionReplacement",
                "operation": "replace_existing",
                "source_package": source["source_package"],
                "source_name": source["source_name"],
                "destination": current["asset"],
                "skeleton_destination": PLAYER_SKELETON,
                "mesh_destination": PLAYER_MESH,
                "data_file": str(data_file),
                "data_sha256": data_hash,
                "bones": bones,
                "samples": samples,
                "duration": duration,
                "fps": [fps.numerator, fps.denominator],
                "rate_scale": rate_scale,
                "properties": properties,
                "topology_adapter": topology_adapter(PLAYER_SKELETON),
                "sync_marker_remap": marker_rows,
                "locomotion_derivation": derivation,
                "timing_contract": (
                    "Unused locomotion rebuilt from the original ActorX pose and cooked "
                    "source rate; current ABP locomotion dependencies remain untouched."
                ),
            }
        )
        timing_rows.append(
            {
                "source": source["source_package"],
                "destination": current["asset"],
                "kind": "UnusedLocomotionReplacement",
                "source_seconds": source["sequence_length_seconds"],
                "playback_seconds": duration,
                "fps": [fps.numerator, fps.denominator],
                "samples": samples,
                "dilation_applied": False,
            }
        )
        locomotion_index += 1

    # InGame duplicates which are not reachable from the current player ABP.
    # Original-name assets receive the complete original timeline. The three
    # existing Legacy derivatives retain their reviewed end-sample exclusion.
    for current in sorted(inventory["assets"], key=lambda value: value.get("asset", "")):
        path = current.get("asset", "")
        if (
            current.get("class") != "AnimSequence"
            or not path.startswith(INGAME_LOCOMOTION_ROOT + "/")
            or path in protected_locomotion
        ):
            continue
        source = source_rows_by_name.get(current["name"].lower())
        exact_original_name = source is not None
        if source is None:
            candidates = {
                pathlib.Path(filename).stem.lower()
                for filename in current.get("import_filenames", [])
            }
            matches = [source_rows_by_name[value] for value in candidates if value in source_rows_by_name]
            if len(matches) != 1:
                raise RuntimeError("Cannot resolve unused InGame locomotion source: " + path)
            source = matches[0]
        bones, pose = load_source(source["source_package"])
        fps = source_fps(source)
        if exact_original_name:
            samples = source["num_frames"]
            rate_scale = source["rate_scale"]
            properties = source_properties(source)
            reuse = direct_data_by_source[source["source_package"].lower()]
            mode = "complete_original_timeline"
        else:
            samples = min(int(current["samples"]), source["num_frames"])
            rate_scale = float(current["rate_scale"])
            properties = current_locomotion_properties(current)
            reuse = None
            mode = "existing_legacy_sample_span_at_original_source_rate"
        append_unused_locomotion(
            current,
            source,
            pose,
            samples,
            fps,
            rate_scale,
            properties,
            {
                "family": "InGame",
                "mode": mode,
                "existing_name_preserved": current["name"],
                "original_source_name": source["source_name"],
            },
            reuse,
        )

    # The existing RT_DAS library is an unused derived library. Preserve its
    # reviewed crop/loop identity and markers, but rebuild poses and timing from
    # the original 30 Hz source. Two formerly truncated idle clips can now use
    # the full original range except the duplicated terminal loop sample.
    runtime_build_by_target = {row["target"]: row for row in runtime_build["assets"]}
    for current in sorted(inventory["assets"], key=lambda value: value.get("asset", "")):
        path = current.get("asset", "")
        if current.get("class") != "AnimSequence" or not path.startswith(
            RUNTIME_LOCOMOTION_ROOT + "/"
        ):
            continue
        build_row = runtime_build_by_target.get(path)
        if build_row is None:
            raise RuntimeError("Runtime locomotion provenance is missing: " + path)
        source_name = pathlib.PurePosixPath(build_row["source"]).name.lower()
        source = source_rows_by_name.get(source_name)
        if source is None:
            raise RuntimeError("Runtime locomotion original source is missing: " + path)
        bones, pose = load_source(source["source_package"])
        samples = int(build_row["target_final_frame"]) + 1
        if int(build_row.get("source_truncated_frames", 0)) > 0:
            samples = max(2, source["num_frames"] - 1)
        fps = source_fps(source)
        append_unused_locomotion(
            current,
            source,
            pose,
            samples,
            fps,
            float(current["rate_scale"]),
            current_locomotion_properties(current),
            {
                "family": "Runtime",
                "mode": "existing_reviewed_crop_at_original_source_rate",
                "existing_name_preserved": current["name"],
                "original_source_name": source["source_name"],
                "previous_target_final_frame": build_row["target_final_frame"],
                "expanded_from_truncated_fbx": bool(build_row.get("source_truncated_frames", 0)),
            },
        )

    expected_unused_locomotion = len(unused_locomotion) - sum(
        row["kind"] == "SourceTimelineReplacement"
        and row["destination"] in unused_locomotion
        for row in output_rows
    )
    actual_derived_locomotion = sum(
        row["kind"] == "UnusedLocomotionReplacement" for row in output_rows
    )
    if actual_derived_locomotion != expected_unused_locomotion:
        raise RuntimeError(
            f"Unused locomotion coverage mismatch: {actual_derived_locomotion} != "
            f"{expected_unused_locomotion}"
        )

    skipped = []
    composite_index = 0
    for audit_row in sorted(audit["composites"], key=lambda value: value["source_package"]):
        if not audit_row["supported_player_animation"]:
            skipped.append(
                {
                    "source": audit_row["source_package"],
                    "reason": "Composite uses a missile/object or unextracted weapon animation skeleton; metadata retained without assigning it to SK_Player.",
                    "unsupported_leaf_sources": audit_row["unsupported_leaf_sources"],
                }
            )
            continue
        if audit_row["uses_protected_locomotion_source"]:
            skipped.append(
                {
                    "source": audit_row["source_package"],
                    "reason": "Locomotion source is audit-only under the user protection rule.",
                    "protected_leaf_assets": audit_row["protected_leaf_assets"],
                }
            )
            continue
        source_package = audit_row["source_package"]
        composite = composite_objects[source_package.lower()]
        properties = composite["Properties"]
        active, curve = active_dilation(properties)
        authored_duration = (
            float(curve["DilationSequenceLength"])
            if active
            else float(properties["SequenceLength"])
        )
        # Variable playback speed belongs to the baked source-time mapping, not
        # to the AnimSequence sampling rate. Quantize the output length to the
        # nearest 60 Hz interval and keep the first/last authored poses exact.
        fps = COMPOSITE_PLAYBACK_FRAME_RATE
        intervals = max(1, round(authored_duration * fps.numerator / fps.denominator))
        duration = intervals * fps.denominator / fps.numerator
        playback_times = np.arange(intervals + 1, dtype=np.float64) / float(fps)
        authored_playback_times = playback_times * authored_duration / duration
        if active:
            source_times = np.interp(
                authored_playback_times,
                [float(value["T_Dilation"]) for value in curve["DilationAnimPositions"]],
                [float(value["T_Original"]) for value in curve["DilationAnimPositions"]],
            )
        else:
            source_times = authored_playback_times
        source_times = np.clip(source_times, 0, float(properties["SequenceLength"]))
        try:
            bones, pose = evaluate(source_package, source_times)
        except Exception as error:
            skipped.append({"source": source_package, "reason": str(error)})
            continue
        leaves = leaf_packages(source_package)
        leaf_rows = [source_rows[value.lower()] for value in leaves]
        leaf_targets = {
            target_contract(row)[:2]
            for row in leaf_rows
        }
        if len(leaf_targets) != 1:
            skipped.append(
                {
                    "source": source_package,
                    "reason": "Composite mixes source skeleton contracts.",
                    "leaf_sources": leaves,
                }
            )
            continue
        target_skeleton, target_mesh = next(iter(leaf_targets))
        root_motion_bake = None
        if target_skeleton == PLAYER_SKELETON:
            try:
                root_motion_bake = stitch_composite_root(
                    source_package, source_times, bones, pose
                )
            except Exception as error:
                skipped.append(
                    {
                        "source": source_package,
                        "reason": "Composite root-motion continuity bake failed: " + str(error),
                    }
                )
                continue
        data_file = DERIVED / f"composite_{composite_index:03d}.npy"
        np.save(data_file, pose)
        force_root_lock = bool(leaf_rows) and all(row["force_root_lock"] for row in leaf_rows)
        output_properties = {
            # Explicit user project contract: every character gameplay skill
            # playback extracts authored Root motion. Auxiliary weapon-object
            # clips keep their original non-character root-motion policy.
            "bEnableRootMotion": target_skeleton == PLAYER_SKELETON,
            "bForceRootLock": force_root_lock,
            "RootMotionRootLock": "RefPose",
        }
        output_rows.append(
            {
                "kind": "CompositePlayback",
                "operation": "create_or_replace_generated",
                "source_package": source_package,
                "source_name": audit_row["source_name"],
                "destination": audit_row["destination"],
                "skeleton_destination": target_skeleton,
                "mesh_destination": target_mesh,
                "data_file": str(data_file),
                "data_sha256": sha256(data_file),
                "bones": bones,
                "samples": intervals + 1,
                "duration": duration,
                "fps": [fps.numerator, fps.denominator],
                "authored_duration": authored_duration,
                "duration_quantization_error_seconds": duration - authored_duration,
                "sampling_policy": "Exact 60/1 Hz; nearest interval count; authored timeline scaled uniformly so both endpoints are preserved.",
                "rate_scale": float(properties.get("RateScale", 1.0)),
                "properties": output_properties,
                "topology_adapter": topology_adapter(target_skeleton),
                "dilation_applied": active,
                "source_sequence_length": float(properties["SequenceLength"]),
                "source_dilation_length": curve.get("DilationSequenceLength"),
                "segments": properties["AnimationTrack"]["AnimSegments"],
                "leaf_sources": leaves,
                "interpolation": "Translation/scale linear; shortest-path normalized linear quaternion; saved dilation table inverted piecewise linearly.",
                "timing_contract": "AnimComposite trims/rates/loops and active DilationCurve are baked once; runtime Rate and Montage segment rate remain 1.0.",
                "root_motion_policy": (
                    "User project override: character gameplay skill playback enables Root Motion; "
                    "source Root is baked through the same time map and transferred to C_P_Kazan. "
                    "Auxiliary weapon-object "
                    "animations preserve their non-character root-motion role."
                ),
                "root_motion_bake": root_motion_bake,
            }
        )
        playback_events.extend(
            mapped_events(
                source_package,
                audit_row["destination"],
                properties,
                active,
                curve,
                authored_duration,
                duration,
            )
        )
        timing_rows.append(
            {
                "source": source_package,
                "destination": audit_row["destination"],
                "kind": "CompositePlayback",
                "source_seconds": float(properties["SequenceLength"]),
                "playback_seconds": duration,
                "authored_playback_seconds": authored_duration,
                "duration_quantization_error_seconds": duration - authored_duration,
                "fps": [fps.numerator, fps.denominator],
                "samples": intervals + 1,
                "dilation_applied": active,
            }
        )
        composite_index += 1
        if composite_index % 25 == 0:
            print("DAS_COMPOSITE_BAKE", composite_index, flush=True)

    destinations = [row["destination"] for row in output_rows]
    if len(destinations) != len(set(destinations)):
        raise RuntimeError("Generated destination collision")
    if any(
        row["destination"] in set(inventory["protected_locomotion_sequences"])
        for row in output_rows
    ):
        raise RuntimeError("Protected locomotion destination entered the write manifest")

    write(MANIFEST, output_rows)
    write(EVENTS, playback_events)
    write(TIMING, timing_rows)
    summary = {
        "schema": 1,
        "status": "passed",
        "version": COMPOSITE_TIMING_VERSION,
        "source_replacements": sum(row["kind"] == "SourceTimelineReplacement" for row in output_rows),
        "unused_locomotion_replacements": sum(row["kind"] == "UnusedLocomotionReplacement" for row in output_rows),
        "existing_sources_to_replace": sum(row["operation"] == "replace_existing" for row in output_rows),
        "missing_sources_to_create": sum(row["operation"] == "create_missing" for row in output_rows),
        "composite_playback_assets": sum(row["kind"] == "CompositePlayback" for row in output_rows),
        "dilation_baked_composites": sum(row.get("dilation_applied", False) for row in output_rows),
        "player_composite_root_motion_bakes": sum(
            row.get("root_motion_bake") is not None for row in output_rows
        ),
        "player_composite_corrected_root_intervals": sum(
            int((row.get("root_motion_bake") or {}).get("corrected_interval_count", 0))
            for row in output_rows
        ),
        "player_root_motion_translation_scale": PLAYER_ROOT_MOTION_TRANSLATION_SCALE,
        "player_root_motion_normalized_assets": sum(
            row["skeleton_destination"] == PLAYER_SKELETON
            and bool(row["properties"].get("bEnableRootMotion", False))
            for row in output_rows
        ),
        "protected_locomotion_source_count": sum(row["protected_from_modification"] for row in audit["sources"]),
        "protected_current_locomotion_count": len(inventory["protected_locomotion_sequences"]),
        "skipped_composites": len(skipped),
        "skipped": skipped,
        "event_rows_preserved_as_metadata": len(playback_events),
        "target_skeletons": [PLAYER_SKELETON, WEAPON_SKELETON],
        "player_target_skeleton_import_track_count": len(player_target_tracks),
        "source_layout_groups": dict(collections.Counter(str(row["bone_count"]) for row in audit["sources"])),
        "write_manifest": str(MANIFEST),
        "timing_report": str(TIMING),
        "event_report": str(EVENTS),
    }
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
