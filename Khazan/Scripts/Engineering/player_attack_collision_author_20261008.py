"""Author the current Player Combo collision data in the isolated ComboWork only.

No Main editor calls. Original fields, playback conversions and assistant-selected
fallbacks are recorded in the report and in every saved window's Source field.
Run through the owned editor mailbox after its native collision schema is built.
"""
from pathlib import Path
import bisect
import datetime
import hashlib
import json
import math
import os
import re
import traceback

MAIN = Path("C:/Users/user/Desktop/GitProject/Khazan/Khazan")
WORK = Path("C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan")
REPORT_ROOT = MAIN / "Metadata/PlayerAttackCollision_20261008"
DEFINITION = "/Game/Data/ComboCommand/DA_Player_Combo_Definition"
DAMAGE_EFFECT = "/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def fields(text):
    result = {}
    for name, raw in re.findall(r'(\w+)=("[^\"]*"|[^,()]+)', text):
        if name in ("AnimReference", "LinkedSequence"):
            result["sequence"] = raw.strip('"').split("'")[1].split(".")[0]
        else:
            try:
                result[name] = float(raw)
            except ValueError:
                result[name] = raw.strip('"')
    return result


def parse_montage(path):
    sections, segments = [], []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip().startswith("CompositeSections("):
            data = fields(line)
            data.update(section=data["SectionName"], next_section=data.get("NextSectionName"),
                        start=data.get("SegmentBeginTime", 0.0), source_line=number)
            sections.append(data)
        if line.strip().startswith("SlotAnimTracks("):
            for text in re.findall(r"\(CachedPlayLength=[^()]+\)", line):
                data = fields(text)
                data.update(start=data.get("StartPos", 0.0), sequence_start=data.get("AnimStartTime", 0.0),
                            sequence_end=data.get("AnimEndTime"), segment_play_rate=data.get("AnimPlayRate", 1.0),
                            loop_count=data.get("LoopingCount", 1.0), source_line=number)
                segments.append(data)
    assert sections and segments, f"Missing reflected montage sections/segments: {path}"
    assert all(s["segment_play_rate"] > 0 and s["loop_count"] == 1 for s in segments), "Reverse/repeated montage segments need explicit occurrence authoring"
    return dict(sections=sections, segments=segments, source_file=str(path), source_sha256=sha(path))


def normal_package(value):
    return re.sub(r"\.\d+$", "", value)


def interpolate(x, pairs):
    pairs = sorted(pairs)
    assert all(pairs[i + 1][0] >= pairs[i][0] for i in range(len(pairs) - 1))
    if x <= pairs[0][0]:
        return pairs[0][1]
    if x >= pairs[-1][0]:
        return pairs[-1][1]
    i = bisect.bisect_right([p[0] for p in pairs], x) - 1
    a, b = pairs[i:i + 2]
    return a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0])


def vector(raw):
    return [float((raw or {}).get(k, 0.0)) for k in ("X", "Y", "Z")]


def qmul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def qrotate(q, v):
    return qmul(qmul(q, [*v, 0.0]), [-q[0], -q[1], -q[2], q[3]])[:3]


def quat_list(q):
    return [float(q.x), float(q.y), float(q.z), float(q.w)]


def main():
    import unreal
    root = Path(unreal.Paths.project_dir()).resolve()
    assert root == WORK.resolve(), "This author is restricted to the isolated ComboWork project"
    if globals().get("expected_editor_pid") is not None:
        assert os.getpid() == int(globals()["expected_editor_pid"]), "Owned editor PID changed"
    report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), project=str(root),
                  pid=os.getpid(), success=False, mutations=[], nodes=[], limitations=[])
    input_files = [REPORT_ROOT / "Original/SourceAttackWindows.json", REPORT_ROOT / "Original/BoxSemantics.json",
                   REPORT_ROOT / "AssetAudit/CurrentNodeMapping.json", MAIN / "Metadata/InGamePlayback_20261002/PlaybackPlan.json",
                   MAIN / "Scripts/Engineering/player_attack_collision_author_20261008.py"]
    report["source_inputs"] = {str(p.relative_to(MAIN)).replace("\\", "/"): sha(p) for p in input_files}
    report_path = REPORT_ROOT / "AuthorReport.json"
    definition = unreal.load_asset(DEFINITION)
    assert definition, DEFINITION
    candidate_path = root / "Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset"
    report["before_sha256"] = sha(candidate_path)
    original = read_json(REPORT_ROOT / "Original/SourceAttackWindows.json")
    boxes = read_json(REPORT_ROOT / "Original/BoxSemantics.json")
    mapping = read_json(REPORT_ROOT / "AssetAudit/CurrentNodeMapping.json")
    composites = {c["package"]: c for c in original["composites"]}
    box_lookup = {(b["package"], b["attack_export_index"]): b for b in boxes["windows"]}
    metadata = {}
    for node in mapping["nodes"]:
        metadata.update(node["sequence_metadata"])
    sequence_cache, montage_cache, pose_cache = {}, {}, {}
    scope = read_json(MAIN / "Metadata/InGamePlayback_20261002/ScopeMapping.json")
    plan = read_json(MAIN / "Metadata/InGamePlayback_20261002/PlaybackPlan.json")["assets"]
    bp = unreal.load_asset("/Game/_Art/Player/Character/Bluprints/BP_Player")
    assert bp, "BP_Player must be read from the private project"
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh_location = mesh.get_editor_property("relative_location")
    mesh_rotation = mesh.get_editor_property("relative_rotation")
    mesh_scale = mesh.get_editor_property("relative_scale3d")
    assert abs(mesh_scale.x - mesh_scale.y) < 1e-6 and abs(mesh_scale.x - mesh_scale.z) < 1e-6
    mesh_q = quat_list(mesh_rotation.quaternion())
    report["mesh_relative_transform"] = dict(location=[mesh_location.x, mesh_location.y, mesh_location.z],
                                             rotation=[mesh_rotation.pitch, mesh_rotation.yaw, mesh_rotation.roll],
                                             scale=[mesh_scale.x, mesh_scale.y, mesh_scale.z])
    report["coordinate_policy"] = "Original baked geometry is already actor-facing ground/model cm (Weak01 PoseWeak01 calibration); baked keys: translation by current mesh relative location only, no yaw or .01. Pose fallback: RAW, extract_root_motion=True, incorporate_root_motion_into_pose=False, should_retarget=False so current runtime root lock is honored; AnimPose WORLD multiplied by mesh scale then current mesh relative rotation; no extra root translation subtraction."

    def sequence_info(path):
        if path in sequence_cache:
            return sequence_cache[path]
        asset = unreal.load_asset(path)
        assert asset, path
        data = dict(metadata.get(path, {}))
        if not data:
            source = next((s for s in scope if s["path"] == path), None)
            assert source, f"No current sequence metadata: {path}"
            data["original_package"] = source["metadata"].get("OriginalPackage")
        selected_plan = data.get("retime_plan") or next((p for p in plan if p.get("original") == data.get("original_package")), {})
        if selected_plan.get("action") == "retime" and "inverse_map" not in selected_plan:
            # The asset's embedded migration summary intentionally omits the
            # dense inverse table. Resolve its exact canonical old path to the
            # stored full authoring plan, and bind the exact original package.
            full_plan = next((p for p in plan if p.get("path") == selected_plan.get("path")), None)
            assert full_plan and full_plan.get("original") == data.get("original_package"), f"Missing exact full retime provenance: {path}"
            assert full_plan.get("inverse_map"), f"No saved inverse retime table: {path}"
            selected_plan = full_plan
        data.update(asset=asset, length=float(asset.get_editor_property("sequence_length")),
                    rate_scale=float(asset.get_editor_property("rate_scale")), plan=selected_plan)
        assert data["rate_scale"] > 0, "Negative/zero sequence RateScale needs explicit mapping"
        frames = int(unreal.AnimationLibrary.get_num_frames(asset))
        report.setdefault("sequence_sampling", {})[path] = dict(current_seconds=data["length"],
                    current_sample_intervals=frames, current_fps=frames / data["length"],
                    original_full_baked_seconds=(data.get("timing_contract") or {}).get("duration"),
                    original_full_retime_target_seconds=selected_plan.get("target_duration"),
                    original_full_retime_authored_seconds=selected_plan.get("authored_duration"),
                    rule="Current user crop clips the existing baked time axis; it does not compress the original full clip timeline.")
        sequence_cache[path] = data
        return data

    def source_choices(info):
        contract = info.get("timing_contract") or {}
        if contract.get("kind") == "CompositePlayback":
            return [contract["source"]]
        selected = info.get("plan", {}).get("selected_composites", [])
        if selected:
            return list(dict.fromkeys(s["package"] for s in selected))
        matches = info.get("direct_ca_referencing_ac_candidates", info.get("source_ac_candidates", []))
        # These ordinary variants are proved by exact source CA references. Variant
        # colliders are not merged just because the variants reuse the same CA.
        ordinary = [p for p in matches if not any(w in p.rsplit("/", 1)[-1] for w in ("BeastRush", "SuperSpeed", "BurstFury", "ChargeFail", "Final_", "NoLoop", "JustMoment", "RecklessRush"))]
        return ordinary or matches

    def ac_to_sequence(info, composite, raw_time):
        if info.get("temporary_same_family_fraction"):
            # Different original CA: the relation is expressly a temporary
            # same-family window fraction, not a verified original time map.
            return raw_time * info["length"] / composite["sequence_length_raw"]
        contract = info.get("timing_contract") or {}
        if contract.get("kind") == "CompositePlayback":
            curve = composite.get("composite_timing_raw", {}).get("DilationCurve", {})
            points = curve.get("DilationAnimPositions", [])
            rendered = interpolate(raw_time, [(p["T_Original"], p["T_Dilation"]) for p in points]) if points else raw_time
            authored = float(contract.get("authored_duration", curve.get("DilationSequenceLength", contract["duration"])))
            return rendered * float(contract["duration"]) / authored
        source = info.get("original_package")
        matching = [s for s in composite["animation_track_raw"]["AnimSegments"]
                    if normal_package(s["AnimReference"]["ObjectPath"]) == normal_package(source or "")]
        assert len(matching) == 1, f"Ambiguous source occurrence: {composite['package']}->{source}"
        segment = matching[0]
        source_time = segment.get("AnimStartTime", 0) + (raw_time - segment.get("StartPos", 0)) * segment.get("AnimPlayRate", 1)
        if source_time < segment.get("AnimStartTime", 0) - 1e-5 or source_time > segment["AnimEndTime"] + 1e-5:
            return None
        p = info.get("plan", {})
        if p.get("action") == "retime":
            inverse = p["inverse_map"]
            return interpolate(source_time, [(pair[1], pair[0]) for pair in inverse]) * p["target_duration"] / p["authored_duration"]
        return source_time

    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    # AnimPose's engine implementation assigns bIgnoreRootLock from
    # bIncorporateRootMotionIntoPose. Keep it false so fallback sockets use the
    # locked presentation pose while CMC applies extracted root motion once.
    options.set_editor_property("extract_root_motion", True)
    options.set_editor_property("incorporate_root_motion_into_pose", False)
    options.set_editor_property("should_retarget", False)

    def fallback_key(info, sequence_time, raw_window):
        bone = raw_window.get("bone_name_raw") or "Root"
        cache_key = (info["asset"].get_path_name(), round(sequence_time, 9), bone)
        if cache_key not in pose_cache:
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(info["asset"], sequence_time, options)
            assert pose.is_valid(), f"Invalid sampled pose: {cache_key}"
            tr = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
            pos = qrotate(mesh_q, [tr.translation.x * mesh_scale.x, tr.translation.y * mesh_scale.y, tr.translation.z * mesh_scale.z])
            rot = qmul(mesh_q, quat_list(tr.rotation))
            pose_cache[cache_key] = (pos, rot)
        pos, rot = pose_cache[cache_key]
        relative = vector(raw_window.get("relative_offset_raw"))
        absolute = vector(raw_window.get("absolute_offset_raw"))
        offset = qrotate(rot, relative)
        pos = [pos[i] + offset[i] + absolute[i] for i in range(3)]
        relative_rotation = raw_window.get("relative_rotation_raw") or {}
        if relative_rotation:
            r = unreal.Rotator(pitch=relative_rotation.get("Pitch", 0), yaw=relative_rotation.get("Yaw", 0), roll=relative_rotation.get("Roll", 0))
            rot = qmul(rot, quat_list(r.quaternion()))
        return pos, rot

    def export_montage(asset):
        name = asset.get_name()
        if name not in montage_cache:
            filename = REPORT_ROOT / "AssetAudit" / f"Current_{name}.t3d"
            task = unreal.AssetExportTask()
            task.object = asset
            task.filename = str(filename)
            task.exporter = unreal.ObjectExporterT3D()
            task.automated, task.prompt = True, False
            assert unreal.Exporter.run_asset_export_task(task)
            montage_cache[name] = parse_montage(filename)
        return montage_cache[name]

    staged = []
    for node in list(definition.get_editor_property("nodes")):
        node_id = str(node.get_editor_property("node_id"))
        if node_id.startswith("Dodge_"):
            staged.append((node, [], None))
            continue
        montage = node.get_editor_property("montage")
        section_name = str(node.get_editor_property("section_name"))
        m = export_montage(montage)
        by_name = {s["section"]: s for s in m["sections"]}
        ordered = sorted(m["sections"], key=lambda s: s["start"])
        section = by_name[section_name]
        node_start = section["start"]
        selected_segments, chain = [], []
        while section and section["section"] not in chain:
            chain.append(section["section"])
            start = section["start"]
            end = next((s["start"] for s in ordered if s["start"] > start), math.inf)
            selected_segments += [s for s in m["segments"] if start - 1e-5 <= s["start"] < end - 1e-5]
            section = by_name.get(section.get("next_section"))
        windows, evidence = [], []
        for segment_number, segment in enumerate(selected_segments):
            info = sequence_info(segment["sequence"])
            rate = segment["segment_play_rate"] * info["rate_scale"]
            local_start = segment["start"] - node_start
            choices = source_choices(info)
            if not choices and segment["sequence"].endswith("/CA_P_Kazan_DASword_B_OverFury_01"):
                info = dict(info, temporary_same_family_fraction=True)
                choices = [p for p in composites if p.endswith("/AC_Kazan_DualAxeSword_Yaksha_OverFury_Start")]
                report["limitations"].append("OverFury_01 uses different CA from original Yaksha Start: assistant-selected same-family Start-window fractions multiplied by current .666667s / original AC .62s; current Weapon_L/R pose supplies geometry. This is temporary and requires observed impact alignment, not original equality.")
            for package in choices:
                c = composites[package]
                for raw in c["attack_windows"]:
                    a = ac_to_sequence(info, c, raw["start_seconds_raw"])
                    b = ac_to_sequence(info, c, raw["end_seconds_raw"])
                    if a is None or b is None:
                        continue
                    a, b = max(a, segment["sequence_start"]), min(b, segment["sequence_end"], info["length"])
                    if b <= a:
                        continue
                    derived = box_lookup.get((package, raw["attack_export_index"]))
                    geometry = derived.get("geometry_keys_derived_using_best_model", []) if derived and not info.get("temporary_same_family_fraction") else []
                    key_values = []
                    for g in geometry:
                        t = ac_to_sequence(info, c, g["original_time_seconds"])
                        if t is not None and a - 1e-6 <= t <= b + 1e-6:
                            key_values.append((t, g["source_local_center_cm"], g["source_local_quaternion_xyzw"]))
                    pose_fallback = not key_values
                    if pose_fallback:
                        # Source sequence sampling cadence is a technical sampling
                        # policy; it is not an invented gameplay duration or size.
                        # UE5.8 GetNumFrames is GetNumberOfSampledKeys()-1,
                        # so this is interval count / actual sequence seconds.
                        intervals = int(unreal.AnimationLibrary.get_num_frames(info["asset"]))
                        assert intervals > 0 and info["length"] > 0
                        fps = float(intervals) / info["length"]
                        count = max(1, math.ceil((b - a) * fps))
                        for i in range(count + 1):
                            t = a + (b - a) * i / count
                            pos, rot = fallback_key(info, t, raw)
                            key_values.append((t, pos, rot))
                    shape_raw = raw.get("shape_raw") or "TemporaryBox_UnserializedOriginalDefault"
                    is_cylinder = "Cylinder" in shape_raw
                    is_sphere = "Sphere" in shape_raw
                    extent = vector(raw.get("size_raw"))
                    if is_cylinder:
                        # Original cylinder dimensions have no verified class
                        # implementation. Interim interpretation is stated below.
                        radius = float((raw.get("cylinder_shape_info_raw") or {}).get("EndRadius", extent[0]))
                        extent = [radius, radius, extent[2] * 0.5]
                    elif is_sphere:
                        extent = [extent[0], extent[0], extent[0]]
                    assert all(math.isfinite(x) and x > 0 for x in extent), (node_id, package, extent)
                    window = unreal.KZAttackCollisionWindow()
                    window.set_editor_property("start_time", local_start + (a - segment["sequence_start"]) / rate)
                    window.set_editor_property("end_time", local_start + (b - segment["sequence_start"]) / rate)
                    window.set_editor_property("shape", unreal.KZAttackCollisionShape.CYLINDER if is_cylinder else unreal.KZAttackCollisionShape.SPHERE if is_sphere else unreal.KZAttackCollisionShape.BOX)
                    window.set_editor_property("extent", unreal.Vector(*extent))
                    group = raw.get("group_number_from_description") or raw.get("hit_group_raw")
                    window.set_editor_property("hit_group", f"S{segment_number}_{package.rsplit('/', 1)[-1]}_G{group}" if group is not None else "None")
                    window.set_editor_property("hp_damage", 10.0)
                    window.set_editor_property("stamina_damage", 5.0)
                    window.set_editor_property("blockable", True)
                    keys = []
                    for t, pos, rot in sorted(key_values):
                        key = unreal.KZAttackCollisionKey()
                        key.set_editor_property("time", local_start + (t - segment["sequence_start"]) / rate)
                        key.set_editor_property("center", unreal.Vector(*pos))
                        key.set_editor_property("rotation", unreal.Quat(*rot).rotator())
                        keys.append(key)
                    window.set_editor_property("keys", keys)
                    provenance = dict(package=package, source_file=c["metadata_file"], source_sha256=c["metadata_sha256"],
                                      attack_export_index=raw["attack_export_index"], sequence=segment["sequence"],
                                      original_window=[raw["start_seconds_raw"], raw["end_seconds_raw"]],
                                      current_window=[window.get_editor_property("start_time"), window.get_editor_property("end_time")], sequence_rate_scale=info["rate_scale"], segment_play_rate=segment["segment_play_rate"],
                                      current_sequence_seconds=info["length"], full_baked_seconds=(info.get("timing_contract") or {}).get("duration"), full_retime_seconds=info.get("plan", {}).get("target_duration"), crop_policy="Clip current user crop bounds; preserve full baked time axis, no proportional compression",
                                      geometry="AnimPose-derived current raw root-locked pose; original offsets; absent BoneName temporarily Root" if pose_fallback else "BoxSemantics bounds-matched derived center/quaternion; raw Size is half extent",
                                      timing="TEMPORARY different-CA same-family window fraction: raw Start time * current sequence length / original AC .62s; pose-derived current geometry" if info.get("temporary_same_family_fraction") else "Composite dilation->normalized exact60 or original AC segment->CA source time->inverse retime map, then current RateScale/segmentRate and montage occurrence offset",
                                      temporary="HPDamage10/StaminaDamage5 absolute; blockable=true. Cylinder radius=EndRadius and halfheight=Size.Z/2 is unverified interpretation; absent shape uses temporary Box." )
                    source_text = json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))
                    def protected_window_fields(value):
                        e = value.get_editor_property("extent")
                        return dict(start=value.get_editor_property("start_time"), end=value.get_editor_property("end_time"),
                                    shape=str(value.get_editor_property("shape")), extent=[e.x, e.y, e.z],
                                    hit_group=str(value.get_editor_property("hit_group")),
                                    hp=value.get_editor_property("hp_damage"), stamina=value.get_editor_property("stamina_damage"),
                                    blockable=value.get_editor_property("blockable"),
                                    keys=[key.export_text() for key in value.get_editor_property("keys")])
                    protected_before = protected_window_fields(window)
                    # VisibleAnywhere provenance deliberately remains readonly
                    # in the runtime schema. Struct import assigns that field
                    # without changing the schema or touching any other field.
                    window.import_text("(Source=" + json.dumps(source_text, ensure_ascii=False) + ")")
                    assert window.get_editor_property("source") == source_text
                    assert protected_window_fields(window) == protected_before, "Partial Source import changed authored geometry or damage"
                    windows.append(window)
                    evidence.append(dict(provenance, key_count=len(keys), extent=extent, shape=shape_raw, pose_fallback=pose_fallback))
            if not choices:
                report["limitations"].append(f"{node_id}:{segment['sequence']} has no verified direct source AC: left without collision pending explicit same-family temporary motion authoring")
        transform = unreal.Transform()
        transform.translation = mesh_location
        transform.rotation = unreal.Quat(0, 0, 0, 1)
        transform.scale3d = unreal.Vector(1, 1, 1)
        staged.append((node, windows, transform))
        report["nodes"].append(dict(node_id=node_id, section_chain=chain, windows=evidence, window_count=len(windows), segments=selected_segments))

    assert staged and any(windows for _, windows, _ in staged), "Authoring produced no windows"
    assert all(sha(p) == report["source_inputs"][str(p.relative_to(MAIN)).replace("\\", "/")] for p in input_files), "Author inputs changed during staging"
    # All reflection/geometry preparation occurs before the single allowed asset mutation.
    effect = unreal.load_class(None, DAMAGE_EFFECT)
    assert effect, DAMAGE_EFFECT
    for node, windows, transform in staged:
        node.set_editor_property("attack_windows", windows)
        if transform:
            node.set_editor_property("collision_to_actor", transform)
    definition.set_editor_property("nodes", [s[0] for s in staged])
    definition.set_editor_property("attack_damage_effect", effect)
    definition.set_editor_property("draw_attack_collision", True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(definition, only_if_is_dirty=False)
    report["mutations"] = [DEFINITION]
    report["after_sha256"] = sha(candidate_path)
    report["success"] = True
    assert all(sha(p) == report["source_inputs"][str(p.relative_to(MAIN)).replace("\\", "/")] for p in input_files), "Author inputs changed during staging"
    write_json(report_path, report)
    return report


if __name__ == "__main__" or globals().get("run_collision_author", True):
    try:
        AUTHOR_RESULT = main()
    except Exception:
        error_path = REPORT_ROOT / "AuthorError.json"
        if error_path.exists():
            previous = read_json(error_path)
            previous_name = re.sub(r"[^0-9A-Za-z]", "_", previous.get("utc", "previous"))
            archive = REPORT_ROOT / "AuthorErrors" / (previous_name + ".json")
            if not archive.exists():
                write_json(archive, previous)
        error = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pid=os.getpid(), error=traceback.format_exc())
        stamp = re.sub(r"[^0-9A-Za-z]", "_", error["utc"])
        write_json(REPORT_ROOT / "AuthorErrors" / (stamp + ".json"), error)
        write_json(error_path, error)
        raise
