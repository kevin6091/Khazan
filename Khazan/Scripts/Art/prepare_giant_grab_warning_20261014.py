"""Targeted original-source warning windows and resource manifest, no UE writes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Metadata/GiantGrabWarning_20261014"
BASE = "/Game/_Art/Effects/Combat/GrabWarning"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def warning(notifies):
    found = [(i, n) for i, n in enumerate(notifies) if n.get("NotifyName") == "xxHoldingAttackWarning"]
    assert len(found) == 1, found
    return found[0]


def interpolate(points, value):
    assert points[0][0] <= value <= points[-1][0], (value, points[0], points[-1])
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return points[-1][1]


apes = read("Metadata/EnemyBehaviorResearch_20261008/ApesOriginalEvidence.json")
audio = read("Saved/ImportReports/GameplayAudio_20261011/AudioAuthoringPlan01.json")
audio_by_source = {}
for event in audio["events"]:
    audio_by_source.setdefault((event["asset"], event["source"]["source_package"]), event)

rows = []
apes_names = {"AC_ApesStoneHand_E_CloseGrab_Start": "Attack_CloseGrab_Start",
              "AC_ApesStoneHand_E_CloseGrab_Start2_Stone": "Attack_CloseGrab_Start2_Stone",
              "AC_ApesStoneHand_E_CloseGrab_Start_Stone": "Attack_CloseGrab_Start_Stone"}
for item in apes["referenced_animation_exports"]:
    name = item["package"].split("/")[-1]
    if name not in apes_names:
        continue
    root = next(e for e in item["exports"] if e["export_type"] == "AnimComposite")
    index, n = warning(root["properties"]["Notifies"])
    mapped = [e for e in apes["playback_events"] if e["source_package"] == item["package"] and e["notify_index"] == index and e["name"] == "xxHoldingAttackWarning"]
    assert len(mapped) == 1
    event = mapped[0]
    asset = "/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Attack/" + apes_names[name]
    assert (asset, item["package"]) in audio_by_source, asset
    rows.append({"asset": asset, "source_package": item["package"], "source_notify_index": index,
                 "source_start": event["original_start_seconds"], "source_end": event["original_end_seconds"],
                 "start": event["playback_start_seconds"], "end": event["playback_end_seconds"],
                 "timing_proof": "ApesOriginalEvidence.playback_events: saved source Dilation mapping"})

yetuga_names = {"AC_Yetuga_CloseGrab_Start": "Attack_CloseGrab_Start",
                "AC_Yetuga_CloseGrab_Start_Ori": "Attack_CloseGrab_Start_Ori",
                "AC_Yetuga_RushGrab": "Attack_RushGrab",
                "AC_Yetuga_RushGrab_Slow": "Attack_RushGrab_Slow"}
for name, asset_name in yetuga_names.items():
    source = "BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga/Skill/" + ("06_CloseGrab" if "CloseGrab" in name else "07_RushGrab") + "/" + name
    source_file = "Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/" + name + ".json"
    data = read(source_file)
    root = next(e for e in data if e["Type"] == "AnimComposite")
    index, n = warning(root["Properties"]["Notifies"])
    raw_start = n["LinkValue"] + n.get("TriggerTimeOffset", 0.)
    raw_end = n["EndLink"]["LinkValue"] + n.get("EndTriggerTimeOffset", 0.)
    asset = "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/" + asset_name
    timing = audio_by_source[(asset, source)]["source"]["timing"]
    points = [(p["T_Original"], p["T_Dilation"]) for p in timing["dilation_points"]]
    assert points, (asset, timing)
    rows.append({"asset": asset, "source_package": source, "source_file": source_file,
                 "source_sha256": sha(source_file), "source_notify_index": index,
                 "source_start": raw_start, "source_end": raw_end,
                 "start": interpolate(points, raw_start), "end": interpolate(points, raw_end),
                 "timing_proof": "AudioAuthoringPlan01.source.timing.dilation_points from same original composite"})

assert len(rows) == 7
assert len({x["asset"] for x in rows}) == 7
for row in rows:
    assert 0 <= row["start"] < row["end"]

manifest = []
effect_dir = "BBQ/Content/_Kazan_/Art/VFX/"
for name in ("FT_UI_BurstAttack_Font", "FT_UI_BurstAttack_Font_Blur"):
    package = effect_dir + "VFX_Texture/UI/" + name
    source_json = "Metadata/GiantGrabWarning_20261014/TextureMetadata/" + package + ".json"
    source_image = "Metadata/GiantGrabWarning_20261014/VisualExport/" + package + ".png"
    manifest.append({"name": name, "source_type": "Texture2D", "source_package": package,
                     "source_json": source_json, "source_image": source_image,
                     "source_sha256": sha(source_json), "destination": BASE + "/Textures/" + name})
name = "FT_Splash_Decal_02"
package = effect_dir + "VFX_Texture/Decal/" + name
source_json = "Metadata/GiantGrabWarning_20261014/TextureMetadata/" + package + ".json"
source_image = "Metadata/GiantGrabWarning_20261014/VisualExport/" + package + ".png"
manifest.append({"name": name, "source_type": "Texture2D", "source_package": package,
                 "source_json": source_json, "source_image": source_image,
                 "source_sha256": sha(source_json), "destination": BASE + "/Textures/" + name})
for name in ("FM_calligraphie", "FM_BurstAttack_BG"):
    package = effect_dir + "VFX_Material/UI/" + name
    source_json = "Metadata/GiantGrabWarning_20261014/VisualMetadata/" + package + ".json"
    manifest.append({"name": name, "source_type": "Material", "source_package": package,
                     "source_json": source_json, "source_sha256": sha(source_json),
                     "destination": BASE + "/Materials/" + name})
name = "FMI_calligraphie"
package = effect_dir + "VFX_Material/UI/MI/" + name
source_json = "Metadata/GiantGrabWarning_20261014/VisualMetadata/" + package + ".json"
manifest.append({"name": name, "source_type": "MaterialInstanceConstant", "source_package": package,
                 "source_json": source_json, "source_sha256": sha(source_json),
                 "destination": BASE + "/Materials/" + name})
for name in ("FS_BurstA_001", "FS_BurstA_002", "FS_BurstA_003"):
    package = effect_dir + "VFX_Mesh/UI/" + name
    source_json = "Metadata/GiantGrabWarning_20261014/VisualMetadata/" + package + ".json"
    source_mesh = "Metadata/GiantGrabWarning_20261014/VisualExport/" + package + ".pskx"
    manifest.append({"name": name, "source_type": "StaticMesh", "source_package": package,
                     "source_json": source_json, "source_mesh": source_mesh,
                     "source_sha256": sha(source_json), "destination": BASE + "/Meshes/" + name})
name = "FP_UI_BurstAttact_Grab"
package = effect_dir + "VFX_Particle/UI/" + name
source_json = "Metadata/GiantGrabWarning_20261014/TelegraphMetadata/" + package + ".json"
manifest.append({"name": name, "source_type": "ParticleSystem", "source_package": package,
                 "source_json": source_json, "source_sha256": sha(source_json),
                 "destination": BASE + "/" + name})
existing = read("Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json")
for name in ("FMI_fluid_A_14", "FMI_fluid_A_15"):
    matches = [r for r in existing if r["name"] == name and r["source_type"] == "MaterialInstanceConstant"]
    assert len(matches) == 1, matches
    manifest.append(matches[0])

(OUT / "WarningPlan.json").write_text(json.dumps({"source_warning": "xxHoldingAttackWarning",
    "source_particle": package, "source_audio": "BBQ/Content/_Kazan_/Sound/Ui/ui_holding_attack",
    "source_audio_media": "BBQ/Content/WwiseAudio/Media/881646502.wem",
    "windows": sorted(rows, key=lambda r: r["asset"]), "resources": manifest},
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"windows": [{k: r[k] for k in ("asset", "source_start", "source_end", "start", "end")}
                              for r in rows], "resources": len(manifest)}, indent=2))
