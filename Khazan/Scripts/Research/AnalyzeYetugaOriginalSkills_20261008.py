import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal"
TARGETS = ["NormalAtk01", "NormalAtk02", "DempseyRoll", "DashAtk", "Armageddon", "IceBreath", "RushGrab", "CloseGrab"]
sys.stdout.reconfigure(encoding="utf-8")
FILES_READ = {}

def source_read(path):
    path = Path(path)
    if str(path) not in FILES_READ:
        raw = path.read_bytes()
        FILES_READ[str(path)] = {"file": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "data": json.loads(raw.decode("utf-8-sig"))}
    return FILES_READ[str(path)]["data"]

def read(name):
    return source_read(SOURCE / (name + ".json"))

def scan(value, path="$", refs=None):
    refs = [] if refs is None else refs
    if isinstance(value, dict):
        if "ObjectPath" in value:
            refs.append({"field": path, **value})
        for key, item in value.items():
            scan(item, path + "." + key, refs)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            scan(item, path + f"[{i}]", refs)
    return refs

def resolve(ref):
    object_path = ref["ObjectPath"]
    package, index_text = object_path.rsplit(".", 1)
    package_index = source_read(SOURCE / "Index.json")
    index_record = next((row for row in package_index if row["package"] == package), None)
    source_file = SOURCE / (index_record["local_path"] if index_record else package.rsplit("/", 1)[-1] + ".json")
    exports = source_read(source_file)
    index = int(index_text)
    export = exports[index]
    referenced_name = ref.get("ObjectName", "").split("'")[1].split(":")[-1].split(".")[-1]
    if referenced_name != export.get("Name"):
        raise ValueError(f"Reference name mismatch: {object_path}: {referenced_name} != {export.get('Name')}")
    return {"file": str(source_file), "package": package, "export_index": index, "type": export.get("Type"), "name": export.get("Name"), "properties": export.get("Properties", {})}

def animation_info(ref):
    resolved = resolve(ref)
    properties = resolved["properties"]
    attacks = []
    events = []
    for notify_index, notify in enumerate(properties.get("Notifies", [])):
        notify_ref = notify.get("Notify") or notify.get("NotifyStateClass")
        if not notify_ref:
            continue
        entry = resolve(notify_ref)
        if entry["type"] not in ("xxAnimNotifyState_Attack", "xxAnimNotifyState_SkillEventTag"):
            continue
        entry["notify_index"] = notify_index
        entry["time_original"] = notify.get("LinkValue")
        entry["duration_original"] = notify.get("Duration")
        if entry["type"] == "xxAnimNotifyState_Attack":
            entry["properties"] = {key: val for key, val in entry["properties"].items() if key not in ("PostCleaningAttackInfo", "BakingAttackDirections")}
            attacks.append(entry)
        else:
            events.append(entry)
    resolved["properties"] = {"AnimationTrack": properties.get("AnimationTrack"), "bApplyDilation": properties.get("bApplyDilation", "OMITTED")}
    resolved["attack_notifies"] = attacks
    resolved["skill_event_notifies"] = events
    resolved["explicit_attack_groups"] = sorted({a["properties"]["Group"] for a in attacks if "Group" in a["properties"]})
    resolved["missing_group_notify_exports"] = [a["export_index"] for a in attacks if "Group" not in a["properties"]]
    return resolved

def main():
    result = {"created": "2026-10-08", "source_root": str(SOURCE), "scope": TARGETS, "skills": []}
    for target in TARGETS:
        name = "SB_Yetuga_" + target
        path = SOURCE / (name + ".json")
        exports = read(name)
        rows = []
        for index, export in enumerate(exports):
            rows.append({"export_index": index, "type": export.get("Type"), "name": export.get("Name"), "properties": export.get("Properties", {})})
        resolved_steps = []
        animations = {}
        for step in exports[1].get("Properties", {}).get("SubStateInfos", []):
            value = step["Value"]
            step_info = {"step": step["Key"], "default_next": value.get("NextSubStateStep"), "animation": value.get("SkillAnimation"), "events": []}
            if value.get("SkillAnimation"):
                animation = animation_info(value["SkillAnimation"])
                animations[animation["name"]] = animation
            for event in value.get("SkillEventMap", []):
                event_value = event["Value"]
                tag = resolve(event_value["SkillTag"])
                conditions = [resolve(condition) for condition in tag["properties"].get("SkillTagCondition", [])]
                funcs = [resolve(func) for func in event_value.get("Funcs", [])]
                step_info["events"].append({"event_index": event["Key"], "tag": tag, "conditions": conditions, "functions": funcs})
            resolved_steps.append(step_info)
        si = read("SI_Yetuga_" + target)
        damages = [resolve(ref) for ref in si[0].get("Properties", {}).get("DamageInfos", [])]
        attack_groups_by_animation = [{"animation": a["name"], "group_enum_values": a["explicit_attack_groups"], "group_count_calculated": len(a["explicit_attack_groups"]), "attack_notify_count_not_hit_count": len(a["attack_notifies"]), "omitted_group_exports": a["missing_group_notify_exports"]} for a in animations.values()]
        result["skills"].append({"skill": name, "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "package": exports[0].get("Package"), "exports": rows, "references": scan(exports), "resolved_steps": resolved_steps, "animations": list(animations.values()), "attack_groups_by_animation": attack_groups_by_animation, "skill_info_exports": si, "resolved_damage_infos": damages, "native_consumer_verified": False})
    source_index = read("Index")
    source_index_map = {row["package"]: row for row in source_index}
    result["source_files"] = []
    for path, info in FILES_READ.items():
        if Path(path).name == "Index.json":
            continue
        package = info["data"][0].get("Package")
        index_record = source_index_map.get(package)
        if not index_record:
            package = next((e.get("Package") for e in info["data"] if e.get("Package")), None)
            index_record = source_index_map.get(package)
        expected_hash = index_record.get("sha256") if index_record else None
        result["source_files"].append({"file": path, "package": package, "saved_json_sha256": info["sha256"], "source_index_sha256": expected_hash, "hash_matches_source_index": expected_hash == info["sha256"] if expected_hash else None})
    result["verification"] = {"export_index_and_object_name_matches": True, "source_files_count": len(result["source_files"]), "all_source_hashes_match_index": all(row["hash_matches_source_index"] for row in result["source_files"]), "native_code_or_runtime_not_checked": True, "attack_group_count_is_not_confirmed_hit_count": True, "omitted_serialized_fields_are_not_replaced_with_guessed_defaults": True}
    out = SOURCE / "YetugaOriginalSkillAnalysis.json"
    if len(sys.argv) < 2:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] in ("groups", "events", "si"):
        for skill in result["skills"]:
            if len(sys.argv) > 2 and sys.argv[2] not in skill["skill"]:
                continue
            print("SKILL", skill["skill"])
            if sys.argv[1] == "groups":
                for anim in skill["animations"]:
                    print("ANIM", anim["name"], "GROUPS", anim["explicit_attack_groups"], "OMITTED", anim["missing_group_notify_exports"])
                    for notify in anim["attack_notifies"]:
                        print("ATTACK", notify["export_index"], notify["time_original"], notify["duration_original"], json.dumps(notify["properties"], ensure_ascii=False))
                    for notify in anim["skill_event_notifies"]:
                        print("EVENT_NOTIFY", notify["export_index"], notify["time_original"], notify["duration_original"], json.dumps(notify["properties"], ensure_ascii=False))
            elif sys.argv[1] == "events":
                for step in skill["resolved_steps"]:
                    print("STEP", step["step"], "DEFAULT", step["default_next"], "ANIM", step["animation"]["ObjectName"])
                    for event in step["events"]:
                        print("EVENT", event["event_index"], "TAG_EXPORT", event["tag"]["export_index"], event["tag"]["type"], "TAG_PROPERTIES", json.dumps(event["tag"]["properties"], ensure_ascii=False))
                        for condition in event["conditions"]:
                            print("CONDITION", condition["export_index"], condition["type"], json.dumps(condition["properties"], ensure_ascii=False))
                        for func in event["functions"]:
                            print("FUNC", func["export_index"], func["type"], json.dumps(func["properties"], ensure_ascii=False))
            else:
                print(json.dumps(skill["skill_info_exports"], ensure_ascii=False))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        for skill in result["skills"]:
            if len(sys.argv) > 2 and sys.argv[2] not in skill["skill"]:
                continue
            print("\nSKILL", skill["skill"])
            for export in skill["exports"]:
                props = export["properties"]
                if export["name"].startswith("Default__"):
                    print("CDO_KEYS", list(props))
                    for step in props.get("SubStateInfos", []):
                        val = step["Value"]
                        print("STEP", step["Key"], "NEXT", val.get("NextSubStateStep"), "ANIM", val.get("SkillAnimation"), "EVENTS", json.dumps(val.get("SkillEventMap"), ensure_ascii=False))
                    for key, val in props.items():
                        if key != "SubStateInfos":
                            print("CDO_OTHER", key, json.dumps(val, ensure_ascii=False))
                else:
                    print("EXPORT", export["export_index"], export["type"], export["name"], json.dumps(props, ensure_ascii=False))
    else:
        print(json.dumps({"output": str(out), "skills": len(result["skills"])}))

if __name__ == "__main__":
    main()
