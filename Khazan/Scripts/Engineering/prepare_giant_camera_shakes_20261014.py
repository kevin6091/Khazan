"""Extract only the saved Yetuga/Apes camera modifiers and map their notify clocks.

This is a read-only source audit. The original archive bytes and current assets
are not modified; its report is the input to the targeted UE authoring pass.
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ActorVisualBindings.json"
LIBRARY = ROOT / "Metadata/EnemyBehaviorResearch_20261008/CurrentApesYetugaLibrary.csv"
FPS_LIBRARY = ROOT / "Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv"
OUTPUT = ROOT / "Metadata/GiantCamera_20261014/OriginalCameraEvents.json"


def map_time(seconds: float, raw_points: list[dict]) -> float:
    points = sorted((float(p["T_Original"]), float(p["T_Dilation"])) for p in raw_points)
    if not points:
        return seconds
    if seconds <= points[0][0]:
        return points[0][1]
    if seconds >= points[-1][0]:
        return points[-1][1]
    index = bisect.bisect_right([p[0] for p in points], seconds) - 1
    (start, mapped_start), (end, mapped_end) = points[index : index + 2]
    return mapped_start + (seconds - start) * (mapped_end - mapped_start) / (end - start)


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    with LIBRARY.open(encoding="utf-8-sig", newline="") as stream:
        library = {row["OriginalPackage"]: row for row in csv.DictReader(stream)}
    with FPS_LIBRARY.open(encoding="utf-8-sig", newline="") as stream:
        fps_library = {row["OriginalPackage"]: row for row in csv.DictReader(stream)}
    camera = [record for record in index["records"] if record["source_export_type"] == "xxCameraMod_Shake"]
    opened: dict[str, zipfile.ZipFile] = {}
    output: list[dict] = []
    try:
        for record in camera:
            archive_name = record["source_zip"]
            if archive_name not in opened:
                opened[archive_name] = zipfile.ZipFile(ROOT / archive_name)
            archive = opened[archive_name]
            raw = archive.read(record["source_zip_entry"])
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == record["source_metadata_sha256"], record["original_package"]
            exports = json.loads(raw)
            camera_export = exports[record["source_export_index"]]
            assert camera_export["Type"] == "xxCameraMod_Shake"
            assert camera_export["Properties"] == record["raw_properties"]
            state_name = camera_export["Outer"]["ObjectName"]
            state = next(item for item in exports if item["Type"] == "xxAnimNotifyState_CameraMod"
                         and item["Name"] in state_name)
            composite = next(item for item in exports if item["Type"] == "AnimComposite")
            notify = next(item for item in composite["Properties"]["Notifies"]
                          if (item.get("NotifyStateClass") or {}).get("ObjectName") == state_name)
            source_start = float(notify["LinkValue"])
            source_end = float(notify["EndLink"]["LinkValue"])
            assert source_end > source_start and abs(source_end-source_start-float(notify["Duration"])) < 0.0001
            clip = library.get(record["original_package"])
            fps_clip = fps_library.get(record["original_package"])
            clock = composite["Properties"].get("DilationCurve", {}).get("DilationAnimPositions", [])
            pre_fps_start = map_time(source_start, clock)
            pre_fps_end = map_time(source_end, clock)
            pre_fps_seconds = float(clip["Seconds"]) if clip else None
            if fps_clip and clip and fps_clip["PreviousSeconds"]:
                assert abs(float(fps_clip["PreviousSeconds"]) - pre_fps_seconds) < 0.0001, record["original_package"]
            clip_seconds = float(fps_clip["Seconds"]) if fps_clip else pre_fps_seconds
            fps_ratio = clip_seconds / pre_fps_seconds if clip else None
            mapped_start = pre_fps_start * fps_ratio if clip else None
            mapped_end = pre_fps_end * fps_ratio if clip else None
            supported = bool(clip and mapped_end > mapped_start and mapped_start < clip_seconds)
            properties = record["raw_properties"]
            show_range = state["Properties"].get("ShowRange", {})
            axes = properties.get("LocOscillation", {})
            event_id = "KZCAM_" + hashlib.sha256(
                f"{record['original_package']}:{record['source_export_index']}:{source_start}".encode()
            ).hexdigest()[:20]
            output.append({
                "event_id": event_id,
                "family": record["family"],
                "category": clip["Category"] if clip else None,
                "current_asset": clip["CurrentAsset"] if clip else None,
                "current_clip_seconds": clip_seconds,
                "pre_integer_fps_clip_seconds": pre_fps_seconds,
                "integer_fps_time_ratio": fps_ratio,
                "integer_fps_rate_scale": float(fps_clip["RateScale"]) if fps_clip else None,
                "author_supported": supported,
                "source_zip": archive_name,
                "source_zip_entry": record["source_zip_entry"],
                "source_sha256": digest,
                "original_package": record["original_package"],
                "camera_export_index": record["source_export_index"],
                "camera_state": state["Name"],
                "source_notify_name": notify["NotifyName"],
                "source_notify_start_seconds": source_start,
                "source_notify_end_seconds": source_end,
                "source_notify_duration_seconds": float(notify["Duration"]),
                "current_start_seconds": mapped_start,
                "current_end_seconds": min(mapped_end, clip_seconds) if clip else None,
                "clock_conversion": "DilationCurve.DilationAnimPositions piecewise linear T_Original -> T_Dilation; then current integer-FPS Seconds/PreviousSeconds to stored sequence seconds",
                "raw_camera_properties": properties,
                "raw_show_range": show_range,
                "raw_axis_amplitude_cm": {axis: float(axes.get(axis, {}).get("Amplitude", 0)) for axis in "XYZ"},
                "raw_axis_frequency_hz": {axis: float(axes.get(axis, {}).get("Frequency", 0)) for axis in "XYZ"},
                "raw_fov_amplitude_degrees": float(properties.get("FOVOscillation", {}).get("Amplitude", 0)),
                "raw_fov_frequency_hz": float(properties.get("FOVOscillation", {}).get("Frequency", 0)),
                "source_status": "direct extracted metadata; native camera implementation/curve evaluation unavailable",
            })
    finally:
        for archive in opened.values():
            archive.close()
    assert len(output) == len(camera) == 88
    assert len({item["event_id"] for item in output}) == len(output)
    report = {
        "schema": "Khazan.GiantCamera.OriginalCameraEvents.v1",
        "sources": {"camera_index": str(INDEX.relative_to(ROOT)), "current_library": str(LIBRARY.relative_to(ROOT)),
                    "integer_fps_library": str(FPS_LIBRARY.relative_to(ROOT))},
        "summary": {"source_events": len(output), "author_supported": sum(e["author_supported"] for e in output),
                    "missing_current_asset": [e["original_package"] for e in output if not e["author_supported"]],
                    "families": dict(Counter(e["family"] for e in output)),
                    "unique_current_assets": len({e["current_asset"] for e in output if e["author_supported"]})},
        "events": output,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
