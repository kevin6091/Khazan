"""Read-only saved-asset audit for the two giant reaction paths."""
from pathlib import Path
import json
import os
import re
import traceback
import unreal

out = Path(os.environ["KZ_GIANT_REACTION_OUT"])
out.mkdir(parents=True, exist_ok=True)
report = {"status": "running", "project": str(Path(unreal.Paths.project_dir()).resolve()), "families": {}}


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def ref(obj):
    return obj.get_path_name() if obj else None


def value(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, unreal.Object):
        return ref(obj)
    if isinstance(obj, (list, tuple, unreal.Array)):
        return [value(item) for item in obj]
    return str(obj)


def notifies(asset):
    rows = []
    for event in unreal.AnimationLibrary.get_animation_notify_events(asset):
        notify = prop(event, "notify") or prop(event, "notify_state_class")
        if not notify:
            continue
        cls = notify.get_class().get_name()
        exported = event.export_text()
        clock = re.search(r"^\([^,]*LinkValue=([^,()]+)", exported)
        if not clock:
            clock = re.search(r"(?:^|,)LinkValue=([^,()]+)", exported)
        data = {"time": float(clock.group(1)) if clock else None, "duration": prop(event, "duration"),
                "class": cls, "name": str(prop(event, "notify_name")),
                "sound": ref(prop(notify, "sound")), "end_sound": ref(prop(notify, "end_sound")),
                "particle": ref(prop(notify, "particle_template")),
                "niagara": ref(prop(notify, "niagara_template")),
                "decal": ref(prop(notify, "decal_material"))}
        playback = prop(notify, "playback")
        if playback:
            data["playback_sound"] = ref(prop(playback, "sound"))
        effect = prop(notify, "effect")
        if effect:
            data["visual_effect"] = ref(effect)
            data["visual_particle"] = ref(prop(effect, "particle_template"))
            data["visual_niagara"] = ref(prop(effect, "niagara_template"))
            data["visual_decal"] = ref(prop(effect, "decal_material"))
        children = prop(notify, "batched_effects")
        if children:
            data["batched_effects"] = len(children)
        rows.append(data)
    return rows


try:
    clips = {
        "ApesStoneHandElite": ["Damage/Damage_GroggyStr_F_Start", "Damage/Damage_PartGroggy_Start",
                               "Damage/Damage_PartGroggy_Loop", "Damage/Damage_PartGroggy_End",
                               "Damage/Damage_JustGuardReaction", "Attack/Attack_DempseyRoll_Step2"],
        "Yetuga": ["Damage/Damage_GroggyStr_F_Start_New", "Damage/Damage_PartGroggy_Start",
                   "Damage/Damage_PartGroggy_Loop", "Damage/Damage_PartGroggy_End",
                   "Attack/Attack_ChargeTackle_Stun", "Attack/Attack_ChargeTackle_Stun_End"],
    }
    for family, names in clips.items():
        base = "/Game/Monsters/" + family
        art = "/Game/_Art/Enemies/" + ("Shared/Elites/ApesStoneHandElite" if family == "ApesStoneHandElite"
                                           else "HeinMach/Bosses/Yetuga") + "/Animations/"
        definition = unreal.load_asset(base + "/Data/DA_Character_" + family)
        settings = prop(definition, "monster_stamina")
        combo = unreal.load_asset(base + "/Data/DA_OriginalPatterns_" + family)
        family_report = {"definition": ref(definition), "combo": ref(combo), "settings": {},
                         "nodes": [], "clips": {}, "montages": {}}
        for key in ("b_enabled", "exhaustion_seconds", "exhaustion_montage", "damage_effect"):
            family_report["settings"][key] = value(prop(settings, key))
        for node in prop(combo, "nodes", []):
            name = str(prop(node, "node_id"))
            if not any(token in name for token in ("DempseyRoll", "ChargeTackle", "PartGroggy", "Groggy")):
                continue
            row = {"id": name, "skill": str(prop(node, "pattern_skill")),
                   "next": str(prop(node, "automatic_next_node")),
                   "section": str(prop(node, "section_name")), "montage": ref(prop(node, "montage")),
                   "branches": []}
            montage = prop(node, "montage")
            section_index = montage.get_section_index(prop(node, "section_name")) if montage else -1
            tracks = prop(montage, "slot_anim_tracks", []) if montage else []
            if section_index >= 0 and tracks:
                track = prop(tracks[0], "anim_track")
                segments = prop(track, "anim_segments", [])
                if section_index < len(segments):
                    row["clip"] = ref(prop(segments[section_index], "anim_reference"))
            for branch in prop(node, "pattern_branches", []):
                row["branches"].append({"event": str(prop(branch, "event")),
                                        "target": str(prop(branch, "target_node")),
                                        "notify": str(prop(branch, "notify")),
                                        "windows": [value(w) for w in prop(branch, "active_windows", [])],
                                        "source": str(prop(branch, "source"))[:240]})
            family_report["nodes"].append(row)
        for name in names:
            asset = unreal.load_asset(art + name)
            family_report["clips"][name] = {"path": ref(asset), "length": asset.get_play_length() if asset else None,
                                            "notifies": notifies(asset) if asset else []}
        for name in ("AM_Exhaustion", "AM_OriginalPatterns_" + family):
            asset = unreal.load_asset(base + "/Animations/" + name)
            family_report["montages"][name] = {"path": ref(asset), "sections": [],
                                                "notifies": notifies(asset) if asset else []}
            if asset:
                tracks = prop(asset, "slot_anim_tracks", [])
                segments = prop(prop(tracks[0], "anim_track"), "anim_segments", []) if tracks else []
                for index in range(asset.get_num_sections()):
                    family_report["montages"][name]["sections"].append({"name": str(asset.get_section_name(index)),
                                                                            "clip": ref(prop(segments[index], "anim_reference")) if index < len(segments) else None})
        report["families"][family] = family_report
    report["status"] = "passed"
except Exception:
    report["status"] = "failed"
    report["error"] = traceback.format_exc()
    unreal.log_error(report["error"])
finally:
    (out / "Audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_REACTION_AUDIT " + report["status"])
    unreal.SystemLibrary.quit_editor()
