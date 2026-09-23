"""Compare every extracted DualAxeSword animation with the current UE library.

This is an offline, read-only analysis.  It joins cooked AnimSequence metadata,
ActorX PSA headers, DualAxeSword skill AnimComposites, and the UE inventory
written by ``audit_das_animation_project_inventory.py``.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import pathlib
import re
import struct


PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/DualAxeSword_20260916"
ART_METADATA_ROOTS = (ROOT / "MetadataArt", ROOT / "MetadataExternal")
SKILL_METADATA_ROOT = ROOT / "MetadataSkill"
PROJECT_INVENTORY = (
    PROJECT / "Saved/ImportReports/Khazan_DAS_Animation_ProjectInventory_20260916.json"
)
LEGACY_PSA_REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_PSA_SourceMetadata.json"
REPORT = PROJECT / "Saved/ImportReports/Khazan_DAS_OriginalMetadataAudit_20260916.json"
SOURCE_CSV = PROJECT / "Saved/ImportReports/Khazan_DAS_SourceTimingComparison_20260916.csv"
COMPOSITE_CSV = PROJECT / "Saved/ImportReports/Khazan_DAS_CompositeTimingComparison_20260916.csv"

ORIGINAL_ART_PREFIX = (
    "BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/DualAxeSword/"
)
ORIGINAL_EXTERNAL_PREFIX = (
    "BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Animation/"
)
ORIGINAL_SKILL_PREFIX = "BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/"
UE_SOURCE_ROOT = "/Game/_Art/Player/Animation/Weapons/DualAxeSword"
PLAYBACK_ROOT = "/Game/_Art/Player/Animation/Playback/DualAxeSword/Composite"
CURRENT_LOCOMOTION_DERIVED_SOURCES = {
    "DAS_Player_Walk_Loop": "CA_P_Kazan_DualAxeSword_Walk_F",
    "DAS_Player_Run_Loop": "CA_P_Kazan_DualAxeSword_Run_F",
    "DAS_Player_Sprint_Loop": "CA_P_Kazan_DualAxeSword_Sprint_F",
}

HEADER = struct.Struct("<20siii")
ANIM_INFO = struct.Struct("<64s64s4i3f3i")
NUMERIC_TOLERANCE = 1.0e-5  # Serialization comparison tolerance, not gameplay tuning.


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def canonical_package(value) -> str:
    if isinstance(value, dict):
        value = value.get("ObjectPath", value.get("AssetPathName", ""))
    if not isinstance(value, str):
        return ""
    return value.split(".", 1)[0].replace("/Game/", "BBQ/Content/")


def metadata_exports(roots) -> list[dict]:
    rows = []
    for root in roots:
        for path in root.rglob("*.json"):
            if path.name == "MetadataExtractionReport.json":
                continue
            rows.extend(read(path))
    return rows


def actorx_info(path: pathlib.Path) -> dict:
    data = path.read_bytes()
    offset = 0
    chunks = {}
    while offset < len(data):
        tag, flags, size, count = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        payload = data[offset : offset + size * count]
        offset += size * count
        chunks[tag.split(b"\0", 1)[0].decode("ascii")] = (size, count, payload)
    if offset != len(data):
        raise RuntimeError("ActorX chunk boundary mismatch: " + str(path))
    if "ANIMINFO" not in chunks or "BONENAMES" not in chunks:
        raise RuntimeError("ActorX animation chunks missing: " + str(path))
    values = ANIM_INFO.unpack(chunks["ANIMINFO"][2][: ANIM_INFO.size])
    embedded_name = values[0].split(b"\0", 1)[0].decode("utf-8")
    digest = hashlib.sha256()
    for name in ("BONENAMES", "ANIMKEYS", "SCALEKEYS"):
        if name in chunks:
            digest.update(name.encode("ascii"))
            digest.update(chunks[name][2])
    return {
        "file": str(path),
        "name": path.stem,
        "embedded_name": embedded_name,
        "animation_payload_sha256": digest.hexdigest(),
        "bone_count": chunks["BONENAMES"][1],
        "track_time": float(values[8]),
        "anim_rate": float(values[9]),
        "num_raw_frames": int(values[-1]),
    }


def all_psa_files() -> list[pathlib.Path]:
    legacy = read(LEGACY_PSA_REPORT)
    roots = [
        pathlib.Path(legacy["psa_root"]),
        ROOT / "AssetsMissing",
        ROOT / "AssetsExternal",
        ROOT / "AssetsLongNames",
    ]
    files = []
    for root in roots:
        if root.is_dir():
            files.extend(root.rglob("*.psa"))
    # The five targeted re-exports and four external sources do not collide with
    # the legacy set.  Case-only duplicate names use the package metadata name.
    by_path = {str(path.resolve()).lower(): path.resolve() for path in files}
    return sorted(by_path.values())


def map_project_sources(
    inventory: dict, original_names: set[str], psa_by_source_name: dict[str, dict]
) -> tuple[dict, list[dict], list[dict]]:
    original_by_lower = {name.lower(): name for name in original_names}
    result = {}
    unresolved_rows = []
    for row in inventory["assets"]:
        asset = row.get("asset", "")
        if row.get("class") != "AnimSequence" or not asset.startswith(UE_SOURCE_ROOT + "/"):
            continue
        candidates = []
        for filename in row.get("import_filenames", []):
            stem = pathlib.Path(filename).stem
            if stem.lower() in original_by_lower:
                candidates.append(original_by_lower[stem.lower()])
        name = row.get("name", asset.rsplit("/", 1)[-1])
        if name.lower() in original_by_lower:
            candidates.append(original_by_lower[name.lower()])
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            result[candidates[0]] = row
        else:
            unresolved_rows.append(row)

    # ActorX stores an animation name in a fixed 64-byte field.  The ten very
    # long SpinningBeast names therefore share truncated embedded names.  The
    # Blender batch retained that embedded name and appended .001, .002, ...
    # on collisions.  Join each collision group in the same lexical package
    # order and record it explicitly for later pose verification.
    source_groups = collections.defaultdict(list)
    for name, psa in psa_by_source_name.items():
        source_groups[psa["embedded_name"].lower()].append(name)
    current_groups = collections.defaultdict(list)
    still_unresolved = []
    for row in unresolved_rows:
        filenames = row.get("import_filenames", [])
        if not filenames:
            still_unresolved.append(row)
            continue
        stem = pathlib.Path(filenames[0]).stem
        base = re.sub(r"\.\d{3}$", "", stem)
        if base.lower() not in source_groups:
            still_unresolved.append(row)
            continue
        suffix_match = re.search(r"\.(\d{3})$", stem)
        suffix = int(suffix_match.group(1)) if suffix_match else 0
        current_groups[base.lower()].append((suffix, row))

    collision_mappings = []
    for embedded, current_values in sorted(current_groups.items()):
        source_values = sorted(source_groups[embedded])
        current_values = sorted(current_values, key=lambda value: (value[0], value[1]["asset"]))
        if len(source_values) != len(current_values):
            still_unresolved.extend(value[1] for value in current_values)
            continue
        for source_name, (suffix, row) in zip(source_values, current_values):
            result[source_name] = row
            collision_mappings.append(
                {
                    "embedded_actorx_name": psa_by_source_name[source_name]["embedded_name"],
                    "blender_collision_suffix": suffix,
                    "source_name": source_name,
                    "current_asset": row["asset"],
                    "import_filenames": row.get("import_filenames", []),
                }
            )

    ambiguous = [
        {
            "asset": row["asset"],
            "candidates": [],
            "import_filenames": row.get("import_filenames", []),
        }
        for row in still_unresolved
    ]
    return result, ambiguous, collision_mappings


def active_dilation(properties: dict) -> tuple[bool, dict]:
    curve = properties.get("DilationCurve", {})
    positions = curve.get("DilationAnimPositions", [])
    active = bool(
        positions
        and curve.get("BakedDilationCurveName")
        and properties.get("ApplyDilationCurveType") != "EApplyDilationCurveType::None"
    )
    return active, curve


def rate_range(points: list[dict]) -> tuple[float | None, float | None]:
    values = []
    for left, right in zip(points, points[1:]):
        denominator = right["T_Dilation"] - left["T_Dilation"]
        if denominator > 0:
            values.append((right["T_Original"] - left["T_Original"]) / denominator)
    return (min(values), max(values)) if values else (None, None)


def relative_skill_path(package: str, name: str, used: dict[str, str]) -> str:
    relative = package.removeprefix(ORIGINAL_SKILL_PREFIX)
    if relative.startswith("Common/"):
        category = "Common"
    elif relative.startswith("Style/Flow/"):
        category = "Flow"
    elif relative.startswith("Style/Yaksha/"):
        category = "Yaksha"
    else:
        category = "Other"
    # Preserve the original cooked Composite basename verbatim.  The category
    # folder separates the one cross-style duplicate without inventing a name.
    asset_name = name
    key = f"{category}/{asset_name}"
    if key in used and used[key] != package:
        raise RuntimeError(
            "Original Composite basename collides inside its category: " + package
        )
    used[key] = package
    return f"{PLAYBACK_ROOT}/{category}/{asset_name}"


def main() -> None:
    art_exports = metadata_exports(ART_METADATA_ROOTS)
    source_objects = {
        row["Package"]: row for row in art_exports if row.get("Type") == "AnimSequence"
    }
    source_by_name = {row["Name"]: row for row in source_objects.values()}
    if len(source_by_name) != len(source_objects):
        raise RuntimeError("Duplicate AnimSequence export names need package-keyed handling")

    psa_rows = [actorx_info(path) for path in all_psa_files()]
    psa_by_lower = collections.defaultdict(list)
    for row in psa_rows:
        psa_by_lower[row["name"].lower()].append(row)
    for key, values in list(psa_by_lower.items()):
        by_payload = {}
        for value in values:
            by_payload.setdefault(value["animation_payload_sha256"], value)
        psa_by_lower[key] = list(by_payload.values())

    psa_by_source_name = {}
    for name in source_by_name:
        matches = psa_by_lower.get(name.lower(), [])
        if len(matches) == 1:
            psa_by_source_name[name] = matches[0]
    inventory = read(PROJECT_INVENTORY)
    current_by_name, ambiguous_project_assets, collision_name_mappings = map_project_sources(
        inventory, set(source_by_name), psa_by_source_name
    )
    protected_assets = set(inventory["protected_locomotion_sequences"])

    sources = []
    failures = []
    for package, source in sorted(source_objects.items()):
        name = source["Name"]
        properties = source.get("Properties", {})
        matches = psa_by_lower.get(name.lower(), [])
        if len(matches) != 1:
            failures.append({"source": package, "reason": f"Expected one PSA, found {len(matches)}"})
            continue
        psa = matches[0]
        metadata_frames = int(properties["NumFrames"])
        metadata_seconds = float(properties["SequenceLength"])
        if psa["num_raw_frames"] != metadata_frames:
            failures.append(
                {
                    "source": package,
                    "reason": "PSA NumRawFrames differs from cooked NumFrames",
                    "psa": psa["num_raw_frames"],
                    "metadata": metadata_frames,
                }
            )
        current = current_by_name.get(name)
        current_asset = current.get("asset") if current else None
        protected = bool(current_asset and current_asset in protected_assets)
        original_fps = (metadata_frames - 1) / metadata_seconds
        mismatches = []
        if current:
            if current["samples"] != metadata_frames:
                mismatches.append("sample_count")
            if abs(current["seconds"] - metadata_seconds) > NUMERIC_TOLERANCE:
                mismatches.append("duration")
            current_fps = current["fps"][0] / current["fps"][1]
            if abs(current_fps - original_fps) > NUMERIC_TOLERANCE:
                mismatches.append("sample_rate")
            if abs(current["rate_scale"] - float(properties.get("RateScale", 1.0))) > NUMERIC_TOLERANCE:
                mismatches.append("rate_scale")
            if current["enable_root_motion"] != bool(properties.get("bEnableRootMotion", False)):
                mismatches.append("enable_root_motion")
            if current["force_root_lock"] != bool(properties.get("bForceRootLock", False)):
                mismatches.append("force_root_lock")
        status = "missing_from_project"
        if current:
            status = "protected_locomotion_audit_only" if protected else (
                "correction_required" if mismatches else "already_matches_original"
            )
        sources.append(
            {
                "source_package": package,
                "source_name": name,
                "source_skeleton": canonical_package(properties.get("Skeleton")),
                "psa_file": psa["file"],
                "bone_count": psa["bone_count"],
                "num_frames": metadata_frames,
                "sequence_length_seconds": metadata_seconds,
                "sample_rate": original_fps,
                "rate_scale": float(properties.get("RateScale", 1.0)),
                "enable_root_motion": bool(properties.get("bEnableRootMotion", False)),
                "force_root_lock": bool(properties.get("bForceRootLock", False)),
                "root_motion_root_lock": properties.get("RootMotionRootLock"),
                "additive_anim_type": properties.get("AdditiveAnimType"),
                "ref_pose_type": properties.get("RefPoseType"),
                "ref_frame_index": properties.get("RefFrameIndex"),
                "current_asset": current_asset,
                "current": ({key: current.get(key) for key in (
                    "fps", "samples", "frames", "seconds", "rate_scale",
                    "enable_root_motion", "force_root_lock", "root_motion_root_lock",
                    "additive_anim_type", "ref_pose_type", "ref_frame_index", "skeleton",
                    "preview_mesh", "track_count", "import_filenames", "referencers"
                )} if current else None),
                "mismatches": mismatches,
                "status": status,
                "protected_from_modification": protected,
            }
        )

    source_lookup = {row["source_package"]: row for row in sources}
    source_lookup_lower = {key.lower(): value for key, value in source_lookup.items()}

    skill_exports = metadata_exports((SKILL_METADATA_ROOT,))
    composite_objects = {
        row["Package"]: row for row in skill_exports if row.get("Type") == "AnimComposite"
    }
    composite_lookup_lower = {key.lower(): value for key, value in composite_objects.items()}

    def leaves(package: str, stack=()) -> list[str]:
        source = source_lookup_lower.get(package.lower())
        if source:
            return [source["source_package"]]
        composite = composite_lookup_lower.get(package.lower())
        if not composite:
            return [package]
        canonical = composite["Package"]
        if canonical in stack:
            raise RuntimeError("Recursive AnimComposite graph: " + canonical)
        result = []
        for segment in composite.get("Properties", {}).get("AnimationTrack", {}).get("AnimSegments", []):
            result.extend(leaves(canonical_package(segment.get("AnimReference")), stack + (canonical,)))
        return result

    composites = []
    used_destinations = {}
    for package, composite in sorted(composite_objects.items()):
        properties = composite.get("Properties", {})
        segments = properties.get("AnimationTrack", {}).get("AnimSegments", [])
        leaf_packages = leaves(package)
        supported = all(value.lower() in source_lookup_lower for value in leaf_packages)
        protected_leaf_assets = sorted(
            {
                source_lookup_lower[value.lower()]["current_asset"]
                for value in leaf_packages
                if value.lower() in source_lookup_lower
                and source_lookup_lower[value.lower()]["protected_from_modification"]
            }
        )
        active, curve = active_dilation(properties)
        minimum_rate, maximum_rate = rate_range(curve.get("DilationAnimPositions", []))
        source_seconds = float(properties["SequenceLength"])
        playback_seconds = float(curve["DilationSequenceLength"]) if active else source_seconds
        segment_timing_changes = any(
            abs(float(segment.get("AnimPlayRate", 1.0)) - 1.0) > NUMERIC_TOLERANCE
            or int(segment.get("LoopingCount", 1)) != 1
            or abs(float(segment.get("AnimStartTime", 0.0))) > NUMERIC_TOLERANCE
            or abs(float(segment.get("AnimEndTime", 0.0)) - source_seconds) > NUMERIC_TOLERANCE
            for segment in segments
        )
        unsupported = sorted(
            {value for value in leaf_packages if value.lower() not in source_lookup_lower}
        )
        composites.append(
            {
                "source_package": package,
                "source_name": composite["Name"],
                "destination": relative_skill_path(package, composite["Name"], used_destinations),
                "sequence_length_seconds": source_seconds,
                "playback_length_seconds": playback_seconds,
                "rate_scale": float(properties.get("RateScale", 1.0)),
                "segment_count": len(segments),
                "segments": segments,
                "leaf_sources": leaf_packages,
                "supported_player_animation": supported,
                "unsupported_leaf_sources": unsupported,
                "uses_protected_locomotion_source": bool(protected_leaf_assets),
                "protected_leaf_assets": protected_leaf_assets,
                "active_dilation": active,
                "dilation_point_count": len(curve.get("DilationAnimPositions", [])),
                "dilation_time_per_frame": curve.get("TimePerFrame"),
                "dilation_rate_min": minimum_rate,
                "dilation_rate_max": maximum_rate,
                "segment_timing_changes": segment_timing_changes,
                "requires_distinct_playback_timeline": bool(active or segment_timing_changes or len(segments) != 1),
                "notify_count": len(properties.get("Notifies", [])),
            }
        )

    current_locomotion = []
    for asset in inventory["current_locomotion_dependencies"]:
        row = next(item for item in inventory["assets"] if item.get("asset") == asset)
        names = []
        for filename in row.get("import_filenames", []):
            stem = pathlib.Path(filename).stem.lower()
            if stem in {name.lower() for name in source_by_name}:
                names.append(next(name for name in source_by_name if name.lower() == stem))
        derived_source = CURRENT_LOCOMOTION_DERIVED_SOURCES.get(asset.rsplit("/", 1)[-1])
        if derived_source:
            names.append(derived_source)
        originals = [
            next(value for value in sources if value["source_name"] == name)
            for name in sorted(set(names))
        ]
        current_fps = row.get("fps", [0, 1])[0] / row.get("fps", [0, 1])[1]
        current_rate_scale = float(row.get("rate_scale", 1.0))
        effective_fps = current_fps * current_rate_scale
        effective_seconds = (
            float(row.get("seconds", 0.0)) / current_rate_scale
            if current_rate_scale
            else None
        )
        original_contracts = [
            {
                "source_name": original["source_name"],
                "num_frames": original["num_frames"],
                "sequence_length_seconds": original["sequence_length_seconds"],
                "sample_rate": original["sample_rate"],
                "rate_scale": original["rate_scale"],
                "enable_root_motion": original["enable_root_motion"],
                "force_root_lock": original["force_root_lock"],
                "current_sample_delta": row.get("samples") - original["num_frames"],
                "effective_duration_delta_seconds": (
                    effective_seconds - original["sequence_length_seconds"]
                    if effective_seconds is not None
                    else None
                ),
            }
            for original in originals
        ]
        current_locomotion.append(
            {
                "asset": asset,
                "fps": row.get("fps"),
                "samples": row.get("samples"),
                "seconds": row.get("seconds"),
                "rate_scale": row.get("rate_scale"),
                "enable_root_motion": row.get("enable_root_motion"),
                "force_root_lock": row.get("force_root_lock"),
                "effective_sample_rate_after_rate_scale": effective_fps,
                "effective_playback_seconds_after_rate_scale": effective_seconds,
                "import_filenames": row.get("import_filenames", []),
                "matched_original_sources": sorted(set(names)),
                "original_contracts": original_contracts,
                "needs_future_exact_source_rebuild_review": bool(original_contracts),
                "finding": (
                    "audit_only_current_locomotion; 24 fps keys with RateScale 1.25 produce an "
                    "effective 30 fps cadence, but key count/effective duration and root-motion "
                    "settings still differ from the matched cooked source contract. Preserve the "
                    "current locomotion asset until its loop/Stop policy is reviewed."
                    if row.get("fps") == [24, 1] and abs(current_rate_scale - 1.25) < NUMERIC_TOLERANCE
                    else "audit_only_current_locomotion; inspect source-specific timing and settings"
                ),
            }
        )

    counts = collections.Counter(row["status"] for row in sources)
    mismatch_counts = collections.Counter(
        mismatch for row in sources for mismatch in row["mismatches"]
    )
    report = {
        "schema": 1,
        "date": "2026-09-16",
        "status": "passed" if not failures and not ambiguous_project_assets else "failed",
        "scope": (
            "All cooked AnimSequence packages in the original DualAxeSword art folder, four external "
            "player sequences reached by DualAxeSword skill composites, all DualAxeSword skill "
            "AnimComposites, and current UE DAS animation assets."
        ),
        "source_of_truth": {
            "anim_sequence_metadata_roots": [str(value) for value in ART_METADATA_ROOTS],
            "skill_metadata_root": str(SKILL_METADATA_ROOT),
            "project_inventory": str(PROJECT_INVENTORY),
            "psa_files": len(psa_rows),
            "timing_rule": "Direct sample rate is (NumFrames - 1) / SequenceLength; source RateScale remains a separate property.",
        },
        "counts": {
            "original_anim_sequences": len(sources),
            "project_source_sequences": sum(1 for row in inventory["assets"] if row.get("class") == "AnimSequence" and row.get("asset", "").startswith(UE_SOURCE_ROOT + "/")),
            "source_status": dict(sorted(counts.items())),
            "mismatch_reasons": dict(sorted(mismatch_counts.items())),
            "skill_anim_composites": len(composites),
            "supported_player_composites": sum(row["supported_player_animation"] for row in composites),
            "unsupported_object_or_external_composites": sum(not row["supported_player_animation"] for row in composites),
            "active_dilation_composites": sum(row["active_dilation"] for row in composites),
            "distinct_timing_composites": sum(row["requires_distinct_playback_timeline"] for row in composites),
            "current_locomotion_dependencies": len(current_locomotion),
        },
        "policy": {
            "locomotion": "Audit only for the current ABP_Player locomotion dependency set. Restore unused source, InGame, and runtime locomotion packages from original timing while preserving their authored non-bone data.",
            "source_sequences": "Replace every current original-source package in-place, including unused locomotion sources; create missing original sources separately.",
            "root_motion": "Copy the original AnimSequence root-motion and force-root-lock properties; bake Root with all other tracks through Composite dilation.",
            "runtime_rate": "Baked Composite playback assets use RateScale 1.0 unless the Composite itself serializes another RateScale; do not apply dilation twice.",
        },
        "failures": failures,
        "ambiguous_project_assets": ambiguous_project_assets,
        "actorx_blender_collision_name_mappings": collision_name_mappings,
        "current_locomotion_audit": current_locomotion,
        "sources": sources,
        "composites": composites,
    }
    write(REPORT, report)

    with SOURCE_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "source_name", "source_package", "current_asset", "status", "mismatches",
            "num_frames", "sequence_length_seconds", "sample_rate", "rate_scale",
            "enable_root_motion", "force_root_lock", "bone_count", "psa_file",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in sources:
            value = {key: row.get(key) for key in fields}
            value["mismatches"] = ";".join(row["mismatches"])
            writer.writerow(value)

    with COMPOSITE_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "source_name", "source_package", "destination", "supported_player_animation",
            "uses_protected_locomotion_source", "sequence_length_seconds", "playback_length_seconds",
            "segment_count", "active_dilation", "dilation_point_count", "dilation_rate_min",
            "dilation_rate_max", "segment_timing_changes", "requires_distinct_playback_timeline",
            "notify_count", "unsupported_leaf_sources",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in composites:
            value = {key: row.get(key) for key in fields}
            value["unsupported_leaf_sources"] = ";".join(row["unsupported_leaf_sources"])
            writer.writerow(value)

    print(json.dumps({"status": report["status"], **report["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
