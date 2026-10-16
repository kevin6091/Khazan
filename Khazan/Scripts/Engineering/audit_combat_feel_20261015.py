"""Targeted saved-asset baseline for parry, giant transitions and root consumption."""
from pathlib import Path
import json
import os
import re
import runpy
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ.get("KZ_COMBAT_FEEL_OUT", ROOT / "Metadata/CombatFeel_20261015/AuditBefore"))
OUT.mkdir(parents=True, exist_ok=True)
report = {"status": "running", "project": str(ROOT), "families": {}, "root_assets": []}

def prop(obj, key, default=None):
    try:
        return obj.get_editor_property(key)
    except Exception:
        try:
            return obj.get_editor_property(key[2:]) if key.startswith("b_") else default
        except Exception:
            return default

def value(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, unreal.Object):
        return obj.get_path_name()
    if isinstance(obj, (list, tuple, unreal.Array)):
        return [value(item) for item in obj]
    if hasattr(obj, "export_text"):
        return obj.export_text()
    return str(obj)

def fields(obj, keys):
    return {key: value(prop(obj, key)) for key in keys}

def notify_rows(asset):
    rows = []
    for event in unreal.AnimationLibrary.get_animation_notify_events(asset):
        notify = prop(event, "notify") or prop(event, "notify_state_class")
        if not notify:
            continue
        clock = re.search(r"(?:^\(|,)LinkValue=([^,()]+)", event.export_text())
        row = {"time": float(clock.group(1)) if clock else None,
               "class": notify.get_class().get_name(), "name": str(prop(event, "notify_name")),
               "event": event.export_text()}
        keys = ("event_id", "particle_template", "niagara_template", "source_socket", "scale3d",
                "relative_location", "relative_rotation", "b_use_world_particle_units", "source_package",
                "source_field", "window_start_time", "window_end_time", "b_end_event", "effect")
        row.update(fields(notify, keys))
        row["children"] = [fields(child, keys) for child in prop(notify, "batched_effects", [])]
        rows.append(row)
    return rows

def montage_row(asset):
    if not asset:
        return None
    return {"path": value(asset), "length": asset.get_play_length(),
            "blend_in": value(prop(asset, "blend_in")), "blend_out": value(prop(asset, "blend_out")),
            "auto_blend_out": prop(asset, "enable_auto_blend_out"),
            "sections": [value(section) for section in prop(asset, "composite_sections", [])],
            "segments": [value(segment) for track in prop(asset, "slot_anim_tracks", [])
                         for segment in prop(prop(track, "anim_track"), "anim_segments", [])],
            "notifies": notify_rows(asset)}

try:
    guard_class = unreal.load_class(None, "/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.GA_Player_Guard_C")
    if not guard_class:
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        candidates = registry.get_assets_by_path("/Game/Bluprints/AbilitySystem/Abilities/Player", recursive=True)
        guards = [a for a in candidates if "Guard" in str(a.asset_name) and "Ability" in str(a.asset_name)]
        report["guard_candidates"] = [str(a.package_name) for a in guards]
        for data in guards:
            guard_class = unreal.load_class(None, str(data.package_name) + "." + str(data.asset_name) + "_C")
            if guard_class:
                break
    assert guard_class, "Guard class missing"
    guard = unreal.get_default_object(guard_class)
    report["guard"] = fields(guard, ("guard_montage", "parry_impact_effect", "parry_billboard_distortion",
                                      "parry_screen_distortion", "parry_sound", "parry_billboard_distortion_scale",
                                      "parry_billboard_distortion_pull_cm", "parry_billboard_distortion_tail_seconds",
                                      "parry_billboard_distortion_max_lifetime_seconds"))
    report["guard"]["class"] = value(guard_class)
    report["guard"]["montage"] = montage_row(prop(guard, "guard_montage"))
    report["guard"]["brutal_effects"] = [fields(effect, ("particle_template", "source_socket", "source_package",
        "source_field", "scale3d", "window_start_time", "window_end_time", "b_end_event"))
        for effect in prop(guard, "parry_brutal_effects", [])]
    report["brutal_montages"] = [montage_row(unreal.load_asset(
        "/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_Brutal" + name)) for name in ("Front", "Back")]
    distort = unreal.load_asset("/Game/VFX/03_SlashHit/KZ_Parring_Distort")
    assert distort, "Requested KZ_Parring_Distort missing"
    report["requested_distort"] = {"path": value(distort), "exposed_parameters": value(prop(distort, "exposed_parameters"))}
    roots = set()
    for family in ("ApesStoneHandElite", "Yetuga"):
        base = "/Game/Monsters/" + family
        definition = unreal.load_asset(base + "/Data/DA_Character_" + family)
        settings = prop(definition, "monster_stamina")
        combo = unreal.load_asset(base + "/Data/DA_OriginalPatterns_" + family)
        bp_class = unreal.load_class(None, f"/Game/Bluprints/Monsters/BP_Monster_{family}.BP_Monster_{family}_C")
        cdo = unreal.get_default_object(bp_class)
        row = {"definition": value(definition), "settings": value(settings),
               "bp": fields(cdo, ("b_ordered_combat_patterns", "disabled_pattern_skills", "ai_settings")),
               "choices": [fields(choice, ("skill", "ability", "condition", "weight", "end_cooldown",
                                           "battle_start_cooldown", "source")) for choice in prop(cdo, "combat_patterns", [])],
               "state_tree": value(prop(definition, "original_pattern_state_tree")), "nodes": [], "montages": {}}
        for node in prop(combo, "nodes", []):
            node_row = fields(node, ("node_id", "pattern_skill", "section_name", "automatic_next_node",
                                     "pattern_blend_seconds", "pattern_branches", "pattern_moves", "attack_windows"))
            montage = prop(node, "montage")
            index = montage.get_section_index(prop(node, "section_name"))
            segments = prop(prop(prop(montage, "slot_anim_tracks")[0], "anim_track"), "anim_segments")
            clip = prop(segments[index], "anim_reference")
            node_row["clip"] = value(clip)
            node_row["segment"] = value(segments[index])
            if any(token in str(prop(node, "node_id")) for token in ("PartGroggy", "Groggy")):
                roots.add(value(clip))
            row["nodes"].append(node_row)
        names = {"exhaustion": prop(settings, "exhaustion_montage"),
                 "part_groggy": prop(settings, "part_group1_groggy_montage"),
                 "brutal_front": prop(settings, "brutal_front_victim_montage"),
                 "brutal_back": prop(settings, "brutal_back_victim_montage"),
                 "patterns": unreal.load_asset(base + "/Animations/AM_OriginalPatterns_" + family)}
        for key, montage in names.items():
            row["montages"][key] = montage_row(montage)
            if key in ("exhaustion", "part_groggy") and montage:
                for track in prop(montage, "slot_anim_tracks", []):
                    for seg in prop(prop(track, "anim_track"), "anim_segments", []):
                        roots.add(value(prop(seg, "anim_reference")))
        report["families"][family] = row
    report["root_assets"] = sorted(roots)
    runpy.run_path(r"C:/Users/user/.codex/skills/unreal-root-motion-repair/scripts/audit_root_motion.py",
                  init_globals={"ROOT_MOTION_AUDIT_ASSETS": [{"asset": path, "expects_root_motion": False,
                                  "motion_bones": ["Root", "Bip001"]} for path in sorted(roots)],
                                "ROOT_MOTION_AUDIT_REPORT": str(OUT / "RootAudit.json")}, run_name="__main__")
    report["status"] = "passed"
except Exception:
    report["status"] = "failed"
    report["error"] = traceback.format_exc()
    unreal.log_error(report["error"])
finally:
    (OUT / "Audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("COMBAT_FEEL_AUDIT " + report["status"])
    unreal.SystemLibrary.quit_editor()
