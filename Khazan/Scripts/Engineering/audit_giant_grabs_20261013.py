"""Read-only audit of the current giant pattern bindings and grab clips."""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata" / "GiantGrabs_20261013" / "MainBefore.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
report = {"project": str(ROOT), "read_only": True, "families": {}, "player": {}, "rocks": {}, "errors": []}


def get(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        if name.startswith("b_"):
            return obj.get_editor_property(name[2:])
        raise


def ref(obj):
    return obj.get_path_name() if obj else None


def row(obj, fields):
    result = {}
    for field in fields:
        try:
            value = get(obj, field)
            if hasattr(value, "get_path_name"):
                value = ref(value)
            elif not isinstance(value, (int, float, bool, str)):
                value = str(value)
            result[field] = value
        except Exception as exc:
            result[field] = "ERROR: " + str(exc)
    return result


try:
    for family in ("ApesStoneHandElite", "Yetuga"):
        base = "/Game/Monsters/" + family
        combo = unreal.load_asset(base + "/Data/DA_OriginalPatterns_" + family)
        montage = unreal.load_asset(base + "/Animations/AM_OriginalPatterns_" + family)
        body_path = "/Game/Bluprints/Monsters/BP_Monster_" + family
        body_cls = unreal.load_class(None, body_path + ".BP_Monster_" + family + "_C")
        body = unreal.get_default_object(body_cls)
        info = {"combo": ref(combo), "montage": ref(montage), "choices": [], "nodes": [], "abilities": []}
        for choice in get(body, "combat_patterns"):
            info["choices"].append({"skill": str(get(choice, "skill")), "weight": get(choice, "weight"),
                                    "ability": ref(get(choice, "ability")),
                                    "condition": row(get(choice, "condition"), ("min_distance", "max_distance", "max_hp", "b_hp_is_ratio", "min_stamina"))})
        for node in get(combo, "nodes"):
            name = str(get(node, "node_id"))
            if not any(token in name for token in ("Grab", "Armageddon", "Tackle", "FastBall", "Dodge_A", "Level_DashAtk_New")):
                continue
            section = get(node, "section_name")
            index = montage.get_section_index(section)
            track = get(get(montage, "slot_anim_tracks")[0], "anim_track")
            segment = get(track, "anim_segments")[index]
            clip = get(segment, "anim_reference")
            n = {"id": name, "skill": str(get(node, "pattern_skill")), "next": str(get(node, "automatic_next_node")),
                 "section": str(section),
                 "clip": ref(clip), "clip_length": clip.get_play_length() if clip else None,
                 "clip_rate": get(clip, "rate_scale") if clip else None,
                 "segment_rate": get(segment, "anim_play_rate"),
                 "blend_seconds": get(node, "pattern_blend_seconds"),
                 "branches": [], "actions": [], "capture_windows": []}
            for branch in get(node, "pattern_branches"):
                n["branches"].append({"event": str(get(branch, "event")), "notify": str(get(branch, "notify")),
                                      "target": str(get(branch, "target_node")), "defer": get(branch, "b_defer_until_step_end"),
                                      "require_hit": get(branch, "b_require_confirmed_hit"),
                                      "windows": [str(w) for w in get(branch, "active_windows")]})
            for action in get(node, "pattern_actions"):
                n["actions"].append({"event": str(get(action, "event")), "action": str(get(action, "action")),
                                     "notify": str(get(action, "notify")), "socket": str(get(action, "socket")),
                                     "target_socket": str(get(action, "capture_target_socket")),
                                     "ragdoll_bone": str(get(action, "ragdoll_bone")),
                                     "interval": get(action, "interval"), "max_count": get(action, "max_count"),
                                     "windows": [str(w) for w in get(action, "active_windows")]})
            for window in get(node, "attack_windows"):
                if get(window, "b_begins_capture"):
                    n["capture_windows"].append(row(window, ("start_time", "end_time", "b_blockable", "hp_damage", "stamina_damage", "hit_group", "source")))
            info["nodes"].append(n)
        for asset in (ROOT / "Content" / "Monsters" / family / "Abilities").glob("GA_Original_*.uasset"):
            name = asset.stem
            cls = unreal.load_class(None, base + "/Abilities/" + name + "." + name + "_C")
            cdo = unreal.get_default_object(cls) if cls else None
            info["abilities"].append({"name": name, "entry": str(get(cdo, "entry_node_id")) if cdo else None,
                                      "capture_effect": ref(get(cdo, "capture_effect")) if cdo else None})
        report["families"][family] = info
    for p in ("/Game/_Art/Player/Animation/Common/Interaction/Hold/CA_P_Kazan_Hold_Demon",
              "/Game/_Art/Player/Animation/Weapons/DualAxeSword/Recovered/CA_P_Kazan_Hold_Demon"):
        clip = unreal.load_asset(p)
        report["player"][p] = {"loaded": bool(clip), "skeleton": ref(clip.get_skeleton()) if clip else None,
                               "length": clip.get_play_length() if clip else None,
                               "root_motion": get(clip, "enable_root_motion") if clip else None}
    for p in ("/Game/_Art/Effects/Shared/Meshes/FS_Rock_01",
              "/Game/_Art/Effects/Shared/Meshes/MonsterApesYetuga/FS_Yetuga_Rock_01",
              "/Game/_Art/Effects/Shared/Meshes/MonsterApesYetuga/FS_Rock_Big_009"):
        mesh = unreal.load_asset(p)
        report["rocks"][p] = {"loaded": bool(mesh), "extent": str(mesh.get_bounds().box_extent) if mesh else None}
except Exception:
    report["errors"].append(traceback.format_exc())
finally:
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_GRAB_AUDIT " + json.dumps({"errors": report["errors"], "families": list(report["families"])}, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
