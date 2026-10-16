"""Read cached original Apes/Yetuga metadata; write owned reports only."""
from pathlib import Path
import collections
import csv
import datetime
import hashlib
import json
import math
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "Metadata/MonsterVFX_20261008/ApesYetugaOriginal"
LIBRARY = ROOT / "Metadata/EnemyBehaviorResearch_20261008/CurrentApesYetugaLibrary.csv"
BASES = {
    "Yetuga": ROOT / "Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911",
    "ApesStoneHandElite": ROOT / "Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return str(Path(path).relative_to(ROOT)).replace("\\", "/")


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def leaves(value, prefix="Properties"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, prefix + "." + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from leaves(item, prefix + f"[{i}]")
    else:
        yield prefix, value


def refs(value, prefix="Properties"):
    if isinstance(value, dict):
        path = value.get("ObjectPath") or value.get("AssetPathName")
        if path:
            name = value.get("ObjectName", "")
            cls = name.split("'", 1)[0] if "'" in name else None
            yield dict(field=prefix, object_path_raw=path, object_name_raw=name, class_hint=cls,
                       package=path.rsplit(".", 1)[0] if "." in path.rsplit("/", 1)[-1] else path,
                       raw_reference=value)
        for key, item in value.items():
            yield from refs(item, prefix + "." + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from refs(item, prefix + f"[{i}]")


def visual_category(typ):
    name = typ.lower()
    if "particle" in name:
        return "Particle"
    if "decal" in name:
        return "Decal"
    if "surfacetrail" in name:
        return "SurfaceTrailDeepSnow" if "snow" in name else "SurfaceTrail"
    if "materialparam" in name or "bonelocationtomaterial" in name:
        return "MaterialParameter"
    if "footstep" in name:
        return "FootprintAndFootstep"
    if "water" in name:
        return "WaterFeedback"
    if "foliage" in name:
        return "FoliageInteraction"
    if "camerashake" in name:
        return "CameraShake"
    if "changestatus" in name:
        return "GameplayStatusContext"
    return None


def filtered_fields(props, words):
    return {path: raw for path, raw in leaves(props)
            if any(word in path.lower() for word in words)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(LIBRARY.open(encoding="utf-8-sig")))
    reports, windows, resources, actor_bindings, packages = [], [], [], [], []
    missing, unreferenced, mismatches = [], [], []
    class_counts = collections.Counter()
    zip_inputs = {}
    for family, base in BASES.items():
        archive_path = base / "SourceMetadata.zip"
        zip_inputs[relative(archive_path)] = digest(archive_path.read_bytes())
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            events_path = base / "PlaybackEventTimes.json"
            events = json.loads(events_path.read_text(encoding="utf-8-sig"))["events"]
            event_map = {(e["source_package"], e["notify_index"]): e for e in events}
            old_library = {r["SourcePackage"]: r for r in csv.DictReader((base / "AnimationLibrary.csv").open(encoding="utf-8-sig"))}
            for row in (r for r in rows if r["Family"] == family):
                package = row["OriginalPackage"]
                entry = package + ".json"
                if entry not in names:
                    missing.append(dict(family=family, current_asset=row["CurrentAsset"], package=package))
                    continue
                raw_bytes = archive.read(entry)
                exports = json.loads(raw_bytes)
                source_hash = digest(raw_bytes)
                animation = next((e for e in exports if e.get("Type") in ("AnimComposite", "AnimSequence")), None)
                assert animation, package
                props = animation.get("Properties", {})
                notifies = props.get("Notifies", [])
                used = set()
                clip_ids = []
                for notify_index, notify in enumerate(notifies):
                    reference = notify.get("NotifyStateClass") or notify.get("Notify")
                    if not reference:
                        continue
                    object_path = reference.get("ObjectPath", "")
                    index_text = object_path.rsplit(".", 1)[-1]
                    export_index = int(index_text) if index_text.isdigit() and object_path.rsplit(".", 1)[0] == package else None
                    target = exports[export_index] if export_index is not None and export_index < len(exports) else None
                    typ = target.get("Type", "") if target else reference.get("ObjectName", "").split("'", 1)[0]
                    category = visual_category(typ)
                    if category is None:
                        continue
                    if export_index is not None:
                        used.add(export_index)
                    raw_props = target.get("Properties", {}) if target else {}
                    saved = event_map.get((package, notify_index))
                    if saved is None:
                        missing.append(dict(family=family, package=package, notify_index=notify_index, issue="Missing exact saved playback event mapping"))
                    else:
                        raw_link_start = float(notify.get("LinkValue", 0.0))
                        raw_start = raw_link_start + float(notify.get("TriggerTimeOffset", 0.0))
                        raw_end = float(notify.get("EndLink", {}).get("LinkValue", raw_link_start + float(notify.get("Duration", 0.0)))) + float(notify.get("EndTriggerTimeOffset", 0.0))
                        if abs(raw_start - saved["original_start_seconds"]) > 1e-5 or abs(raw_end - saved["original_end_seconds"]) > 1e-5:
                            mismatches.append(dict(package=package, notify_index=notify_index, notify_times=[raw_start, raw_end], saved=saved))
                    rid = family + ":" + row["CurrentAsset"].rsplit("/", 1)[-1] + f":N{notify_index}"
                    clip_ids.append(rid)
                    refs_raw = list(refs(raw_props))
                    for ref in refs_raw:
                        resources.append(dict(family=family, event_id=rid, source_package=package,
                                              source_sha256=source_hash, export_index=export_index, **ref))
                    modes = [value for field, value in leaves(raw_props) if field.endswith("ParticleMode")]
                    pipeline = "Existing Particle/Decal adapter candidate; exact version/default/condition support must be checked"
                    if "Niagara" in modes or any(ref["class_hint"] == "NiagaraSystem" for ref in refs_raw):
                        pipeline = "Niagara source; Cascade-only path insufficient; stripped graph restoration is not proved"
                    elif category not in ("Particle", "Decal"):
                        pipeline = "Separate environment/material/camera/gameplay path; do not report as native Particle/Decal completion"
                    old = old_library[package]
                    start = saved["playback_start_seconds"] if saved else None
                    end = saved["playback_end_seconds"] if saved else None
                    record = dict(id=rid, family=family, category=row["Category"], source_event_category=category,
                                  current_asset=row["CurrentAsset"], owner_kind="Prop" if row["Category"] == "Prop" else "Character",
                                  legacy_asset=row["LegacyAsset"], original_package=package,
                                  source_zip=relative(archive_path), source_zip_sha256=zip_inputs[relative(archive_path)],
                                  source_zip_entry=entry, source_metadata_sha256=source_hash,
                                  notify_index=notify_index, source_export_index=export_index,
                                  source_export_name=target.get("Name") if target else None, source_export_type=typ,
                                  raw_notify=notify, raw_properties=raw_props, original_reference=reference,
                                  resource_references=refs_raw,
                                  attach_transform_fields=filtered_fields(raw_props, ["attach", "socket", "relative", "absolute", "heightfromfloor", "worldowner"]),
                                  lifetime_cleanup_fields=filtered_fields(raw_props, ["lifespan", "lifetime", "destroy", "deactiv", "detach", "deattach", "blendtime", "onlystart", "dilation"]),
                                  condition_fields=filtered_fields(raw_props, ["success", "damage", "state", "condition", "version", "trigger", "chance", "filter", "status"]),
                                  timing=dict(raw_link_start_seconds=notify.get("LinkValue"), raw_end_link_seconds=notify.get("EndLink", {}).get("LinkValue"), raw_duration_seconds=notify.get("Duration"),
                                              original_start_seconds=saved.get("original_start_seconds") if saved else None,
                                              original_end_seconds=saved.get("original_end_seconds") if saved else None,
                                              original_trigger_offset=saved.get("original_trigger_offset") if saved else None,
                                              original_end_trigger_offset=saved.get("original_end_trigger_offset") if saved else None,
                                              baked_sequence_start_seconds=start, baked_sequence_end_seconds=end,
                                              current_clip_seconds=float(row["Seconds"]), current_rate_scale=float(row["RateScale"]),
                                              current_real_time_seconds_if_unmodified=[start / float(row["RateScale"]), end / float(row["RateScale"])] if saved else None,
                                              current_fps=row["FPS"], intervals=int(row["Frames"]), derivation=row["TimelineDerivation"],
                                              source_duration_seconds=float(old["SourceSequenceLength"]), baked_duration_seconds=float(old["DurationSeconds"]),
                                              dilation_applied=old["DilationApplied"], saved_conversion_source=relative(events_path),
                                              saved_conversion_source_sha256=digest(events_path.read_bytes()),
                                              saved_event=saved,
                                              formula="Reuse exact source_package + notify_index saved original->baked map; source start LinkValue+TriggerTimeOffset and source end EndLink.LinkValue+EndTriggerTimeOffset are already included. Current rename preserves timeline. Sequence-local seconds are not stretched to current length. Divide by actual current RateScale for wallclock; caller montage segment/actor/live rate and hit-stop remain separate.",
                                              out_of_clip=bool(saved and (start > float(row["Seconds"]) + 1e-5 or end > float(row["Seconds"]) + 1e-5))),
                                  pipeline_status=pipeline,
                                  default_limit="Absent original fields are unverified native/CDO defaults, not false/zero confirmation. Duration is emission/eligibility window; remaining component lifespan follows original resource/module/cleanup rules.")
                    windows.append(record)
                    class_counts[typ] += 1
                for index, export in enumerate(exports):
                    if visual_category(export.get("Type", "")) and index not in used:
                        unreferenced.append(dict(family=family, package=package, source_sha256=source_hash, export_index=index,
                                                 name=export.get("Name"), type=export.get("Type"), reason="No actual source notify references this export; do not play it just because it exists"))
                asset_file = ROOT / "Content" / (row["CurrentAsset"][len("/Game/"):] + ".uasset")
                reports.append(dict(**row, current_asset_file_exists=asset_file.exists(),
                                    current_asset_sha256=digest(asset_file.read_bytes()) if asset_file.exists() else None,
                                    source_metadata_sha256=source_hash, original_animation_type=animation["Type"],
                                    visual_event_ids=clip_ids, visual_event_count=len(clip_ids),
                                    original_segment_track=props.get("AnimationTrack"),
                                    original_dilation_curve=props.get("DilationCurve")))
            # Existing family design/cache records only. These are actor-owned
            # aura/state/spawn/prop bindings, not freely runnable clip notifies.
            prefix = "BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/" if family == "Yetuga" else "BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/"
            for entry in sorted(n for n in names if n.startswith(prefix) and n.endswith(".json")):
                data = archive.read(entry)
                for index, export in enumerate(json.loads(data)):
                    typ = export.get("Type", "")
                    if "AnimNotify" in typ or typ in ("AnimSequence", "AnimComposite", "xxDamageBoxComponent", "xxAttackBoxComponent"):
                        continue
                    props = export.get("Properties", {})
                    rr = list(refs(props))
                    visual_refs = [r for r in rr if r["class_hint"] in ("ParticleSystem", "NiagaraSystem", "MaterialInterface", "Material", "MaterialInstanceConstant", "StaticMesh", "SkeletalMesh", "CurveFloat") or "/VFX/" in r["package"]]
                    context = filtered_fields(props, ["anger", "spawn", "summon", "ice", "status", "particle", "aura", "material", "effect"])
                    if visual_refs or (context and any(x in typ.lower() for x in ("spawn", "status", "skill", "character", "particle", "yetuga", "apes"))):
                        actor_bindings.append(dict(family=family, original_package=entry[:-5], source_zip=relative(archive_path),
                            source_zip_entry=entry, source_metadata_sha256=digest(data), source_export_index=index,
                            source_export_name=export.get("Name"), source_export_type=typ,
                            resource_references=visual_refs, condition_lifecycle_fields=context, raw_properties=props,
                            execution_status="Original actor/state/projectile/skill context only; autonomous source AI and native conditional consumers are not implemented by this audit; never auto-run from class existence"))
                        for ref in visual_refs:
                            resources.append(dict(family=family, event_id=None, source_package=entry[:-5], source_sha256=digest(data), export_index=index, **ref))
    current_saved = ROOT / "Metadata/MonsterStamina_20261008/MainSavedReload_ConcurrentBuild.json"
    current = json.loads(current_saved.read_text(encoding="utf-8-sig"))
    row_by_path = {r["CurrentAsset"]: r for r in rows}
    aliases = []
    for clip in current["clips"]:
        source = clip["source"].split(".")[0]
        if source in row_by_path:
            aliases.append(dict(family=row_by_path[source]["Family"], source_current_art=source,
                                gameplay_copy=clip["copy"].split(".")[0], original_package=row_by_path[source]["OriginalPackage"],
                                source_saved_readback=relative(current_saved), raw_saved_clip_record=clip))
    stats = dict(clips=len(reports), family_clips=dict(collections.Counter(r["Family"] for r in reports)),
                 clips_with_visual_events=sum(bool(r["visual_event_count"]) for r in reports),
                 timed_visual_events=len(windows), category_counts=dict(collections.Counter(w["source_event_category"] for w in windows)),
                 original_class_counts=dict(class_counts), actor_visual_bindings=len(actor_bindings),
                 unique_resource_packages=len(set(r["package"] for r in resources)), gameplay_copy_aliases=len(aliases),
                 missing_records=len(missing), timing_mismatches=len(mismatches), orphan_exports=len(unreferenced))
    manifest = dict(schema="Khazan.MonsterVFX.ApesYetugaOriginal.v1", utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    domain="Art original resource/timing audit", summary=stats, inputs=dict(source_zips=zip_inputs,
                    current_library=relative(LIBRARY), current_library_sha256=digest(LIBRARY.read_bytes()),
                    current813_library="Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv"),
                    clips=reports, effect_windows=windows, gameplay_copy_aliases=aliases,
                    current_gameplay_bodies=[b for b in current["bodies"] if b["family"] in BASES],
                    actor_visual_bindings_report="ActorVisualBindings.json", resource_references_report="ResourceReferences.json",
                    limitations=["No Content/native/Main/editor/FModel UI mutation, no resource import, no current effect render or runtime proof.",
                    "Apes and Yetuga current BP/ABP/Definition/exhaustion montage availability does not implement original autonomous AI/pattern selection/anger or summons.",
                    "Current212 is the preserved Art library. Existing saved16 gameplay derivatives are aliases, not extra original source packages.",
                    "Particle/Decal native playback, Niagara, surface meshes/snow/water/footprint/camera/material curves/status/actor-spawn lifecycles require separate verified adapters.",
                    "Imported/source timing identity is from saved library and rename audits; actor time dilation, hit-stop, gameplay montage offsets/trim/rates must be applied once by caller.",
                    "Do not attach Prop events to main character solely by family; source skeleton and actual spawned visual owner remain separate.",
                    "No original cooked shader/native CDO/conditional execution/pixel parity guarantee."])
    write("Manifest.json", manifest)
    write("ActorVisualBindings.json", dict(schema=manifest["schema"], records=actor_bindings))
    write("ResourceReferences.json", dict(records=resources, packages=sorted(set(r["package"] for r in resources))))
    write("AuditDiagnostics.json", dict(missing=missing, timing_mismatches=mismatches, orphan_exports=unreferenced))
    fields = ["id", "family", "category", "current_asset", "original_package", "source_export_type", "notify_index", "start", "end", "rate_scale", "resource_paths", "pipeline_status"]
    with (OUT / "EffectWindows.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in windows:
            writer.writerow(dict({k: record[k] for k in fields if k in record}, start=record["timing"]["baked_sequence_start_seconds"],
                                end=record["timing"]["baked_sequence_end_seconds"], rate_scale=record["timing"]["current_rate_scale"],
                                resource_paths=" | ".join(r["object_path_raw"] for r in record["resource_references"])))
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
