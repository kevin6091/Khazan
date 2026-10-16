"""Fresh-process saved-asset assertions for Apes/Yetuga grab authoring."""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabs_20261013/FreshReadback.json"
report = {"project": str(ROOT), "checks": {}, "errors": []}


def get(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        if name.startswith("b_"):
            return obj.get_editor_property(name[2:])
        raise


def check(name, value):
    report["checks"][name] = bool(value)
    assert value, name


def node(asset, name):
    found = [n for n in get(asset, "nodes") if str(get(n, "node_id")) == name]
    check(name + " exists once", len(found) == 1)
    return found[0]


try:
    a = unreal.load_asset("/Game/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite")
    y = unreal.load_asset("/Game/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga")
    check("both data assets", a and y)
    for name in ("Level_DashAtk_New_Step8", "Level_DashAtk_New_Step12", "Dodge_A_Step8", "Dodge_A_Step12"):
        wins = list(get(node(a, name), "attack_windows"))
        check(name + " dodge-only capture windows", len(wins) == 2 and
              all(get(w, "b_begins_capture") and not get(w, "b_blockable") for w in wins))
    for name in ("CloseGrab_Step1", "RushGrab_Step3", "RushGrab_Step5"):
        wins = list(get(node(y, name), "attack_windows"))
        check(name + " dodge-only capture", wins and all(get(w, "b_begins_capture") and not get(w, "b_blockable") for w in wins))
    for name in ("Armageddon_Step3", "Armageddon_Step4"):
        wins = list(get(node(y, name), "attack_windows"))
        check(name + " saved landing", len(wins) == 1 and
              abs(get(wins[0], "start_time") - 0.6523101511593324) < 0.00001 and
              abs(get(wins[0], "end_time") - 0.7023101185265546) < 0.00001 and
              abs(get(wins[0], "extent").x - 2000.0) < 0.01 and
              get(wins[0], "b_disallow_perfect_guard"))
    rocks = [o for o in get(a, "pattern_objects") if str(get(o, "id")) == "COI_ApesStoneHand_E_FastBall_OBJ"]
    check("Apes rock mesh", len(rocks) == 1 and
          get(rocks[0], "static_mesh") and "FS_Rock_Big_009" in get(rocks[0], "static_mesh").get_path_name())
    for family, skills in (("ApesStoneHandElite", ("Dodge_A", "Level_DashAtk_New")),
                           ("Yetuga", ("CloseGrab", "RushGrab"))):
        for skill in skills:
            path = f"/Game/Monsters/{family}/Abilities/GA_Original_{skill}"
            bp = unreal.load_asset(path)
            cls = unreal.load_class(None, bp.get_path_name() + "_C") if bp else None
            defaults = unreal.get_default_object(cls) if cls else None
            anim = get(defaults, "victim_capture_animation") if defaults else None
            check(family + "/" + skill + " victim source animation", anim and
                  "Weapons/DualAxeSword/Recovered/CA_P_Kazan_Hold_Demon" in anim.get_path_name())
            effect = get(defaults, "capture_effect") if defaults else None
            check(family + "/" + skill + " capture state effect", effect and
                  "GE_MonsterCapture" in effect.get_path_name())
            check(family + "/" + skill + " stationary hold key", defaults and
                  abs(float(get(defaults, "victim_capture_hold_time_seconds")) - 39.0 / 30.0) < 0.00001)
            expected_socket = "Hold_Spine" if family == "Yetuga" else "Bip001-Spine"
            check(family + "/" + skill + " source target socket", defaults and
                  str(get(defaults, "victim_capture_target_socket")) == expected_socket)
    for family in ("ApesStoneHandElite", "Yetuga"):
        bp = unreal.load_asset("/Game/Bluprints/Monsters/BP_Monster_" + family)
        cls = unreal.load_class(None, bp.get_path_name() + "_C") if bp else None
        defaults = unreal.get_default_object(cls) if cls else None
        check(family + " BP class", defaults)
        choices = {str(get(c, "skill")): c for c in get(defaults, "combat_patterns")}
        if family == "Yetuga":
            check("Tackle disabled", float(get(choices["ChargeTackle"], "weight")) == 0 and
                  "ChargeTackle" in [str(x) for x in get(defaults, "disabled_pattern_skills")])
            check("both Yetuga grabs retained", "CloseGrab" in choices and "RushGrab" in choices)
            check("Armageddon active", float(get(choices["Armageddon"], "weight")) > 0)
        else:
            check("Apes near grab candidate", float(get(choices["Dodge_A"], "weight")) > 0)
    report["status"] = "passed"
except Exception:
    report["errors"].append(traceback.format_exc())
    report["status"] = "failed"
finally:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("GIANT_GRABS_READBACK " + json.dumps({"status": report["status"], "count": len(report["checks"]), "errors": report["errors"]}, ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
