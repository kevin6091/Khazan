"""Targeted readback of already extracted FModel JustGuard/Parry particles."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/Extracted/CombatEffects_20261006/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Attack"


def referenced_name(value):
    if not isinstance(value, dict):
        return None
    return value.get("ObjectName", "").split("'")[-2] if "'" in value.get("ObjectName", "") else value.get("ObjectName")


def referenced_object(value, objects):
    path = value.get("ObjectPath", "") if isinstance(value, dict) else ""
    suffix = path.rsplit(".", 1)[-1]
    return objects[int(suffix)] if suffix.isdigit() else None


def describe(particle):
    path = SOURCE / f"{particle}.json"
    objects = json.loads(path.read_text(encoding="utf-8"))
    output = []
    for emitter in (obj for obj in objects if obj["Type"] == "ParticleSpriteEmitter"):
        lod_ref = emitter.get("Properties", {}).get("LODLevels", [None])[0]
        lod = referenced_object(lod_ref, objects)
        props = lod.get("Properties", {})
        required = referenced_object(props.get("RequiredModule"), objects)
        required_props = required.get("Properties", {})
        modules = []
        for ref in props.get("Modules", []):
            module = referenced_object(ref, objects)
            if module:
                modules.append({
                    "type": module["Type"],
                    "name": module["Name"],
                    "enabled": module.get("Properties", {}).get("bEnabled", True),
                })
        output.append({
            "source_emitter": emitter["Name"],
            "display_name": emitter["Properties"].get("EmitterName"),
            "enabled": required_props.get("bEnabled", True),
            "material": referenced_name(required_props.get("Material")),
            "duration": required_props.get("EmitterDuration"),
            "modules": modules,
        })
    return {"source": str(path.relative_to(ROOT)), "emitters": output}


if __name__ == "__main__":
    result = {name: describe(name) for name in ("PP_AtkEx_JustGuard", "PP_AtkEx_Parry")}
    target = Path(__file__).with_name("SourceEmitterRoles.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, info in result.items():
        print(name)
        for emitter in info["emitters"]:
            print(" ", emitter["source_emitter"], emitter["display_name"], "enabled=" + str(emitter["enabled"]), emitter["material"])
