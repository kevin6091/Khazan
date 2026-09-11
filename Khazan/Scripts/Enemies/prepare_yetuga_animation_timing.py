"""Bake source-authored Yetuga composite timing into runtime playback poses.

Source ActorX samples stay in the external archive.  UE receives one playback
library: active composites with segment rates/dilation baked, plus source
sequences consumed directly by the original profile or BlendSpaces.
"""

from __future__ import annotations

import bisect
import collections
import csv
import fractions
import json
import math
import pathlib
import struct
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
PROJECT_META = PROJECT / "Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911"
sys.path.insert(0, str(PROJECT / "Saved/ArtTools/EnemyPython"))
import numpy as np


HEADER = struct.Struct("<20siii")
SERIALIZED_TIME_EPSILON = 1e-6


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def package(value) -> str:
    return value.get("ObjectPath", value.get("AssetPathName", "")).split(".", 1)[0].replace(
        "/Game/", "BBQ/Content/"
    )


def actorx_chunks(path: pathlib.Path):
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
        raise RuntimeError(f"ActorX chunk boundary mismatch in {path}")
    return result


def source_data(row: dict):
    chunks = actorx_chunks(pathlib.Path(row["source_file"]))
    size, bone_count, raw_bones = chunks["BONENAMES"]
    bones = [
        raw_bones[index * size : index * size + 64].split(b"\0", 1)[0].decode("utf-8")
        for index in range(bone_count)
    ]
    anim_info = struct.unpack("<64s64s4i3f3i", chunks["ANIMINFO"][2][:168])
    frame_count = anim_info[-1]
    properties = row["properties"]
    if frame_count != properties["NumFrames"]:
        raise RuntimeError(
            f"PSA/source NumFrames mismatch {row['source_package']}: {frame_count} != {properties['NumFrames']}"
        )
    keys = np.frombuffer(chunks["ANIMKEYS"][2], dtype="<f4").reshape(frame_count, bone_count, 8)
    pose = np.empty((frame_count, bone_count, 10), dtype=np.float32)
    pose[:, :, :3] = keys[:, :, :3]
    pose[:, :, 1] *= -1
    pose[:, :, 3:7] = keys[:, :, 3:7]
    pose[:, :, 4] *= -1
    pose[:, 0, 6] *= -1
    norms = np.linalg.norm(pose[:, :, 3:7], axis=2, keepdims=True)
    if not np.all(norms > 0):
        raise RuntimeError(f"Zero-length quaternion in {row['source_package']}")
    pose[:, :, 3:7] /= norms
    if "SCALEKEYS" in chunks:
        pose[:, :, 7:10] = np.frombuffer(chunks["SCALEKEYS"][2], dtype="<f4").reshape(
            frame_count, bone_count, 4
        )[:, :, :3]
    else:
        pose[:, :, 7:10] = 1.0
    return bones, pose, anim_info[8]


def interpolate_pose(pose, seconds, length):
    frames = np.clip(np.asarray(seconds, dtype=np.float64) / length * (len(pose) - 1), 0, len(pose) - 1)
    lower = np.floor(frames).astype(np.int64)
    upper = np.minimum(lower + 1, len(pose) - 1)
    alpha = (frames - lower).astype(np.float32)[:, None, None]
    first = pose[lower]
    second = pose[upper].copy()
    dot = np.sum(first[:, :, 3:7] * second[:, :, 3:7], axis=2)
    second[:, :, 3:7] *= np.where(dot < 0, -1, 1)[:, :, None]
    result = first * (1 - alpha) + second * alpha
    result[:, :, 3:7] /= np.linalg.norm(result[:, :, 3:7], axis=2, keepdims=True)
    return result


def dilation_spec(properties: dict):
    curve = properties.get("DilationCurve", {})
    positions = curve.get("DilationAnimPositions", [])
    active = bool(
        positions
        and curve.get("BakedDilationCurveName")
        and properties.get("ApplyDilationCurveType") != "EApplyDilationCurveType::None"
    )
    if active:
        dilated = [value["T_Dilation"] for value in positions]
        original = [value["T_Original"] for value in positions]
        if not all(right > left for left, right in zip(dilated, dilated[1:])):
            raise RuntimeError("Non-monotonic source dilation time")
        if not all(right >= left for left, right in zip(original, original[1:])):
            raise RuntimeError("Non-monotonic source original time")
        if abs(dilated[-1] - curve["DilationSequenceLength"]) >= 0.0001:
            raise RuntimeError("DilationSequenceLength does not match its final table key")
    return active, curve


def event_rows(source_package: str, destination: str, properties: dict, active: bool, curve: dict):
    output = []
    if active:
        x = [value["T_Dilation"] for value in curve["DilationAnimPositions"]]
        y = [value["T_Original"] for value in curve["DilationAnimPositions"]]

        def to_playback(value: float) -> float:
            return float(np.interp(value, y, x))

    else:

        def to_playback(value: float) -> float:
            return float(value)

    for index, notify in enumerate(properties.get("Notifies", [])):
        original_start = float(notify.get("LinkValue", 0.0) + notify.get("TriggerTimeOffset", 0.0))
        end_link = notify.get("EndLink", {})
        original_end = float(
            end_link.get("LinkValue", original_start + notify.get("Duration", 0.0))
            + notify.get("EndTriggerTimeOffset", 0.0)
        )
        source_type = notify.get("Notify") or notify.get("NotifyStateClass")
        output.append(
            {
                "source_package": source_package,
                "playback_asset": destination,
                "notify_index": index,
                "name": notify.get("NotifyName"),
                "original_start_seconds": original_start,
                "original_end_seconds": original_end,
                "playback_start_seconds": to_playback(original_start),
                "playback_end_seconds": to_playback(original_end),
                "original_trigger_offset": notify.get("TriggerTimeOffset", 0.0),
                "original_end_trigger_offset": notify.get("EndTriggerTimeOffset", 0.0),
                "source_type": source_type,
                "mapping": "Original absolute event time mapped through the saved source dilation table; proprietary event behavior remains metadata only.",
            }
        )
    return output


def main() -> None:
    manifest = read(ROOT / "ImportManifest.json")
    sources = {row["source_package"]: row for row in manifest["source_animations"]}
    composites = {row["source_package"]: row for row in manifest["composites"]}
    direct = set(manifest["direct_source_animation_packages"])
    cache = {}
    output_rows = []
    timing_rows = []
    playback_events = []

    def load_source(source_package: str):
        if source_package not in cache:
            row = sources[source_package]
            cache[source_package] = source_data(row)[:2]
        return cache[source_package]

    def source_rate(source_package: str) -> float:
        properties = sources[source_package]["properties"]
        return (properties["NumFrames"] - 1) / properties["SequenceLength"]

    def leaf_rates(source_package: str, stack=()):
        if source_package in sources:
            return [source_rate(source_package)]
        if source_package in stack:
            raise RuntimeError(f"Recursive composite rate graph: {source_package}")
        values = []
        for segment in composites[source_package]["properties"]["AnimationTrack"]["AnimSegments"]:
            values.extend(leaf_rates(package(segment["AnimReference"]), stack + (source_package,)))
        return values

    def has_root_motion(source_package: str, stack=()) -> bool:
        if source_package in sources:
            return bool(sources[source_package]["properties"].get("bEnableRootMotion", False))
        if source_package in stack:
            raise RuntimeError(f"Recursive composite root-motion graph: {source_package}")
        return any(
            has_root_motion(package(segment["AnimReference"]), stack + (source_package,))
            for segment in composites[source_package]["properties"]["AnimationTrack"]["AnimSegments"]
        )

    def all_force_root_lock(source_package: str, stack=()) -> bool:
        if source_package in sources:
            return bool(sources[source_package]["properties"].get("bForceRootLock", False))
        if source_package in stack:
            raise RuntimeError(f"Recursive composite root-lock graph: {source_package}")
        segments = composites[source_package]["properties"]["AnimationTrack"]["AnimSegments"]
        return bool(segments) and all(
            all_force_root_lock(package(segment["AnimReference"]), stack + (source_package,))
            for segment in segments
        )

    def evaluate(source_package: str, times, stack=()):
        if source_package in sources:
            bones, pose = load_source(source_package)
            return bones, interpolate_pose(pose, times, sources[source_package]["properties"]["SequenceLength"])
        if source_package in stack:
            raise RuntimeError(f"Recursive composite pose graph: {source_package}")
        properties = composites[source_package]["properties"]
        segments = properties["AnimationTrack"]["AnimSegments"]
        result = None
        bone_names = None
        for segment in segments:
            rate = segment["AnimPlayRate"]
            if rate == 0:
                raise RuntimeError(f"Zero AnimPlayRate in {source_package}")
            span = segment["AnimEndTime"] - segment["AnimStartTime"]
            end = segment["StartPos"] + span / abs(rate) * segment["LoopingCount"]
            # CUE4Parse's JSON decimal rendering can differ from the segment-derived
            # endpoint by a few 1e-7 seconds (for example 2.9700003 vs 2.97).
            # Treat that serialization residue as the same endpoint; larger gaps
            # remain uncovered and still fail the bake.
            selected = (times >= segment["StartPos"] - SERIALIZED_TIME_EPSILON) & (
                times <= end + SERIALIZED_TIME_EPSILON
            )
            elapsed = np.clip((times[selected] - segment["StartPos"]) * abs(rate), 0, span * segment["LoopingCount"])
            local = np.mod(elapsed, span)
            local = np.where(
                elapsed >= span * segment["LoopingCount"] - SERIALIZED_TIME_EPSILON,
                span,
                local,
            )
            local = segment["AnimStartTime"] + local if rate > 0 else segment["AnimEndTime"] - local
            child_package = package(segment["AnimReference"])
            child_bones, child_pose = evaluate(child_package, local, stack + (source_package,))
            if result is None:
                result = np.empty((len(times), len(child_bones), 10), dtype=np.float32)
                result[:] = np.nan
                bone_names = child_bones
            if child_bones != bone_names:
                raise RuntimeError(f"Composite skeleton/bone order mismatch in {source_package}")
            result[selected] = child_pose
        if result is None or not np.isfinite(result).all():
            raise RuntimeError(f"Uncovered composite time in {source_package}")
        return bone_names, result

    for index, source_package in enumerate(sorted(direct)):
        row = sources[source_package]
        properties = row["properties"]
        bones, pose, psa_rate = source_data(row)
        frames = properties["NumFrames"]
        duration = properties["SequenceLength"]
        fps = fractions.Fraction((frames - 1) / duration).limit_denominator(1000)
        data_file = ROOT / "Derived/AnimationData" / f"direct_{index:03d}.npy"
        data_file.parent.mkdir(parents=True, exist_ok=True)
        np.save(data_file, pose)
        playback_properties = {"bEnableRootMotion": has_root_motion(source_package)}
        if all_force_root_lock(source_package):
            playback_properties["bForceRootLock"] = True
        output = {
            "source_package": source_package,
            "destination": row["destination"],
            "mesh_destination": row["mesh_destination"],
            "skeleton_destination": row["skeleton_destination"],
            "playback_derivation": "DirectOriginalTimeline",
            "data_file": str(data_file),
            "bones": bones,
            "samples": frames,
            "duration": duration,
            "fps": [fps.numerator, fps.denominator],
            "source_num_frames": frames,
            "source_sequence_length": duration,
            "source_psa_anim_rate": psa_rate,
            "rate_scale": properties.get("RateScale", 1.0),
            "direct_consumers": row["direct_consumers"],
            "properties": {
                key: value
                for key, value in properties.items()
                if key
                in {
                    "bEnableRootMotion",
                    "bForceRootLock",
                    "RootMotionRootLock",
                    "AdditiveAnimType",
                    "RefPoseType",
                    "RefFrameIndex",
                }
            },
        }
        output_rows.append(output)
        playback_events.extend(event_rows(source_package, row["destination"], properties, False, {}))
        timing_rows.append(
            {
                "source": source_package,
                "destination": row["destination"],
            "mesh_destination": row["mesh_destination"],
            "skeleton_destination": row["skeleton_destination"],
                "derivation": output["playback_derivation"],
                "source_seconds": duration,
                "playback_seconds": duration,
                "fps": output["fps"],
                "samples": frames,
                "dilation_applied": False,
            }
        )

    skipped = []
    changed_duration = 0
    for index, row in enumerate(manifest["composites"]):
        source_package = row["source_package"]
        properties = row["properties"]
        unsupported = [
            package(segment["AnimReference"])
            for segment in properties["AnimationTrack"]["AnimSegments"]
            if package(segment["AnimReference"]) not in sources
            and package(segment["AnimReference"]) not in composites
        ]
        if unsupported:
            skipped.append(
                {
                    "source": source_package,
                    "inputs": unsupported,
                    "reason": "Composite references a non-Yetuga or unsupported animation asset; metadata retained and no incompatible skeleton assigned.",
                }
            )
            continue
        if not properties.get("SequenceLength"):
            skipped.append(
                {
                    "source": source_package,
                    "reason": "No positive source SequenceLength; metadata retained and no duration invented.",
                }
            )
            continue
        active, curve = dilation_spec(properties)
        duration = curve["DilationSequenceLength"] if active else properties["SequenceLength"]
        rates = leaf_rates(source_package)
        target_rate = 1 / curve["TimePerFrame"] if active else max(rates)
        intervals = max(1, round(duration * target_rate))
        fps = fractions.Fraction(intervals / duration).limit_denominator(100000)
        playback_times = np.linspace(0, duration, intervals + 1)
        if active:
            source_times = np.interp(
                playback_times,
                [value["T_Dilation"] for value in curve["DilationAnimPositions"]],
                [value["T_Original"] for value in curve["DilationAnimPositions"]],
            )
        else:
            source_times = playback_times
        source_times = np.clip(source_times, 0, properties["SequenceLength"])
        bones, pose = evaluate(source_package, source_times)
        data_file = ROOT / "Derived/AnimationData" / f"composite_{index:03d}.npy"
        data_file.parent.mkdir(parents=True, exist_ok=True)
        np.save(data_file, pose)
        changed_duration += int(active and abs(duration - properties["SequenceLength"]) > 0.0001)
        playback_properties = {"bEnableRootMotion": has_root_motion(source_package)}
        if all_force_root_lock(source_package):
            playback_properties["bForceRootLock"] = True
        output = {
            "source_package": source_package,
            "destination": row["destination"],
            "mesh_destination": row["mesh_destination"],
            "skeleton_destination": row["skeleton_destination"],
            "playback_derivation": "CompositeBake",
            "data_file": str(data_file),
            "bones": bones,
            "samples": intervals + 1,
            "duration": duration,
            "fps": [fps.numerator, fps.denominator],
            "rate_scale": properties.get("RateScale", 1.0),
            "dilation_applied": active,
            "source_sequence_length": properties["SequenceLength"],
            "source_dilation_length": curve.get("DilationSequenceLength"),
            "target_sample_rate_source": "DilationCurve.TimePerFrame" if active else "Referenced sequence (NumFrames-1)/SequenceLength",
            "segments": properties["AnimationTrack"]["AnimSegments"],
            "interpolation": "Translation/scale linear; shortest-path normalized linear quaternion; source dilation table inverted piecewise linearly.",
            "properties": playback_properties,
        }
        output_rows.append(output)
        playback_events.extend(event_rows(source_package, row["destination"], properties, active, curve))
        timing_rows.append(
            {
                "source": source_package,
                "destination": row["destination"],
            "mesh_destination": row["mesh_destination"],
            "skeleton_destination": row["skeleton_destination"],
                "derivation": output["playback_derivation"],
                "source_seconds": properties["SequenceLength"],
                "playback_seconds": duration,
                "fps": output["fps"],
                "samples": intervals + 1,
                "dilation_applied": active,
            }
        )
        if index % 20 == 0:
            print("YETUGA_BAKE", index, "/", len(manifest["composites"]), flush=True)

    destinations = [row["destination"] for row in output_rows]
    if len(destinations) != len(set(destinations)):
        raise RuntimeError("Playback destination collision")
    write(ROOT / "AnimationImportManifest.json", output_rows)
    write(ROOT / "PlaybackEventTimes.json", {"events": playback_events})
    audit = {
        "status": "passed" if not skipped else "passed_with_metadata_only_composites",
        "source_sequences_for_bake": len(sources),
        "direct_original_timeline": len(direct),
        "composite_playback": len(output_rows) - len(direct),
        "playback_total": len(output_rows),
        "changed_duration_composites": changed_duration,
        "metadata_only_composites": skipped,
        "source_fps": dict(
            sorted(
                collections.Counter(
                    str(row["fps"])
                    for row in output_rows
                    if row["playback_derivation"] == "DirectOriginalTimeline"
                ).items()
            )
        ),
        "playback_events": len(playback_events),
        "numpy_version": np.__version__,
        "runtime_limitations": "Actor time dilation, AI state rates and hit-stop remain gameplay contracts. Proprietary notify behavior is metadata only.",
        "clips": timing_rows,
    }
    write(ROOT / "AnimationTimingAudit.json", audit)

    csv_path = ROOT / "AnimationLibrary.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            [
                "SourcePackage",
                "Destination",
                "PlaybackDerivation",
                "FPSNumerator",
                "FPSDenominator",
                "Samples",
                "DurationSeconds",
                "SourceSequenceLength",
                "DilationApplied",
                "RateScale",
            ]
        )
        for row in output_rows:
            writer.writerow(
                [
                    row["source_package"],
                    row["destination"],
                    row["playback_derivation"],
                    row["fps"][0],
                    row["fps"][1],
                    row["samples"],
                    row["duration"],
                    row.get("source_sequence_length"),
                    row.get("dilation_applied", False),
                    row["rate_scale"],
                ]
            )

    PROJECT_META.mkdir(parents=True, exist_ok=True)
    for name in [
        "AnimationImportManifest.json",
        "AnimationTimingAudit.json",
        "PlaybackEventTimes.json",
        "AnimationLibrary.csv",
    ]:
        (PROJECT_META / name).write_bytes((ROOT / name).read_bytes())
    print(json.dumps({key: audit[key] for key in audit if key != "clips"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()


