"""Targeted giant-grab/Armageddon repair. Run only in an owned hidden editor."""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabs_20261013/AuthoringReport.json"
REPORT = {"project": str(ROOT), "status": "preflight", "saved": [], "changes": [], "errors": []}


def get(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        if name.startswith("b_"):
            return obj.get_editor_property(name[2:])
        raise


def put(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception:
        if name.startswith("b_"):
            obj.set_editor_property(name[2:], value)
        else:
            raise


def save(obj):
    assert unreal.EditorAssetLibrary.save_loaded_asset(obj), obj.get_path_name()
    REPORT["saved"].append(obj.get_path_name().split(".")[0])


def blueprint(path):
    bp = unreal.load_asset(path)
    assert bp, path
    cls = unreal.load_class(None, bp.get_path_name() + "_C")
    assert cls, path
    return bp, unreal.get_default_object(cls)


def node_by_id(nodes, name):
    matches = [n for n in nodes if str(get(n, "node_id")) == name]
    assert len(matches) == 1, (name, len(matches))
    return matches[0]


try:
    apes = unreal.load_asset("/Game/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite")
    yetuga = unreal.load_asset("/Game/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga")
    rock = unreal.load_asset("/Game/_Art/Effects/Shared/Meshes/MonsterApesYetuga/FS_Rock_Big_009")
    hold = unreal.load_asset("/Game/_Art/Player/Animation/Weapons/DualAxeSword/Recovered/CA_P_Kazan_Hold_Demon")
    assert apes and yetuga and rock and hold
    apes_bp, apes_body = blueprint("/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite")
    yetuga_bp, yetuga_body = blueprint("/Game/Bluprints/Monsters/BP_Monster_Yetuga")
    grab_abilities = []
    for family, skills in (("ApesStoneHandElite", ("Dodge_A", "Level_DashAtk_New")),
                           ("Yetuga", ("CloseGrab", "RushGrab"))):
        for skill in skills:
            bp, defaults = blueprint(f"/Game/Monsters/{family}/Abilities/GA_Original_{skill}")
            assert str(get(defaults, "entry_node_id")).startswith(skill + "_Step")
            grab_abilities.append((bp, defaults, family, skill))

    apes_nodes = list(get(apes, "nodes"))
    yetuga_nodes = list(get(yetuga, "nodes"))
    for name in ("Level_DashAtk_New_Step8", "Level_DashAtk_New_Step12"):
        node = node_by_id(apes_nodes, name)
        windows = list(get(node, "attack_windows"))
        assert len(windows) == 2 and all(not get(w, "b_begins_capture") for w in windows), name
        for window in windows:
            put(window, "b_begins_capture", True)
            put(window, "b_blockable", False)  # Original HoldAttackAuto/bDontGuard adapter.
        put(node, "attack_windows", windows)
        REPORT["changes"].append(name + ":two capture windows, unblockable")

    # Original Armageddon AC Jump_End and Jump_End_Close each contain one
    # xxAnimNotifyState_Attack. The old builder required baked frame keys and
    # therefore silently omitted these keyless radial landing windows.
    for name, notify_index in (("Armageddon_Step3", 14), ("Armageddon_Step4", 17)):
        node = node_by_id(yetuga_nodes, name)
        assert len(get(node, "attack_windows")) == 0, name
        w = unreal.KZAttackCollisionWindow()
        put(w, "start_time", 0.6523101511593324)
        put(w, "end_time", 0.7023101185265546)
        put(w, "shape", unreal.KZAttackCollisionShape.CYLINDER)
        # Original EndRadius=2000 cm; Size.Z=500. The half-height conversion
        # and actor-local sum of the two raw offsets are adapter interpretations.
        put(w, "extent", unreal.Vector(2000.0, 2000.0, 250.0))
        put(w, "hit_group", "ArmageddonLanding")
        put(w, "hp_damage", 10.0)  # Existing project temporary absolute damage policy.
        put(w, "stamina_damage", 5.0)
        put(w, "b_blockable", True)
        put(w, "b_disallow_perfect_guard", True)  # SD_Yetuga_Proto_Armageddon_02.GuardDamageInfo.bDontJustGuard
        keys = []
        for t in (0.6523101511593324, 0.7023101185265546):
            key = unreal.KZAttackCollisionKey()
            put(key, "time", t)
            put(key, "center", unreal.Vector(-958.82715 - 256.86768, -0.010379791, 0.0))
            keys.append(key)
        put(w, "keys", keys)
        REPORT["changes"].append(f"{name}: source AC Notifies[{notify_index}] playback .652310151-.702310119 s, Cylinder EndRadius2000 cm, Size.Z500 cm, DamageInfoIndex1; offset sum/Z half-height inferred, HP10/ST5 temporary")
        put(node, "attack_windows", [w])
        REPORT["changes"].append(name + ":original landing attack window restored")

    objects = list(get(apes, "pattern_objects"))
    selected = [o for o in objects if str(get(o, "id")) == "COI_ApesStoneHand_E_FastBall_OBJ"]
    assert len(selected) == 1
    previous_rock = get(selected[0], "static_mesh")
    REPORT["changes"].append("Apes FastBall previous static mesh: " + (previous_rock.get_path_name() if previous_rock else "None"))
    put(selected[0], "static_mesh", rock)
    put(selected[0], "source", str(get(selected[0], "source")) + "; 2026-10-13 existing source-family FS_Rock_Big_009 visual adapter, original COI mesh reference absent")
    put(apes, "pattern_objects", objects)
    REPORT["changes"].append("Apes FastBall: placeholder sphere replaced by sourced rock-family mesh")

    choices = list(get(apes_body, "combat_patterns"))
    dodge = [c for c in choices if str(get(c, "skill")) == "Dodge_A"]
    assert len(dodge) == 1 and float(get(dodge[0], "weight")) == 0.0
    # Original CB DefaultSkillList owns Dodge_A, but its passive trigger is
    # unavailable. This is explicitly a temporary encounter selection adapter.
    put(dodge[0], "weight", 1.0)
    condition = get(dodge[0], "condition")
    put(condition, "min_distance", 0.0)
    put(condition, "max_distance", 400.0)
    put(dodge[0], "condition", condition)
    put(dodge[0], "source", str(get(dodge[0], "source")) + "; 2026-10-13 TEMP combat-choice weight1 at 0..400 cm, since original CB Dodge_A passive trigger is not yet mapped")
    put(apes_body, "combat_patterns", choices)
    REPORT["changes"].append("Apes Dodge_A: TEMP near grab selection enabled; original passive selector unresolved")

    yetuga_choices = list(get(yetuga_body, "combat_patterns"))
    tackle = [c for c in yetuga_choices if str(get(c, "skill")) == "ChargeTackle"]
    assert tackle
    for choice in tackle:
        put(choice, "weight", 0.0)
        put(choice, "source", str(get(choice, "source")) + "; 2026-10-13 user removal: disabled in encounter")
    put(yetuga_body, "combat_patterns", yetuga_choices)
    disabled = list(get(yetuga_body, "disabled_pattern_skills"))
    if "ChargeTackle" not in [str(x) for x in disabled]:
        disabled.append("ChargeTackle")
    put(yetuga_body, "disabled_pattern_skills", disabled)
    REPORT["changes"].append("Yetuga ChargeTackle: selection, StateTree source gate and follow-up blocked")

    for bp, defaults, family, skill in grab_abilities:
        put(defaults, "victim_capture_animation", hold)
        REPORT["changes"].append(f"{family}/{skill}: original player Hold_Demon sequence bound")

    REPORT["status"] = "saving"
    put(apes, "nodes", apes_nodes)
    put(yetuga, "nodes", yetuga_nodes)
    save(apes)
    save(yetuga)
    for bp, _, _, _ in grab_abilities:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
    unreal.BlueprintEditorLibrary.compile_blueprint(apes_bp)
    save(apes_bp)
    unreal.BlueprintEditorLibrary.compile_blueprint(yetuga_bp)
    save(yetuga_bp)
    REPORT["status"] = "saved"
except Exception:
    REPORT["errors"].append(traceback.format_exc())
    REPORT["status"] = "failed"
finally:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_GRABS_AUTHOR " + json.dumps({"status": REPORT["status"], "saved": len(REPORT["saved"]), "errors": REPORT["errors"]}, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
