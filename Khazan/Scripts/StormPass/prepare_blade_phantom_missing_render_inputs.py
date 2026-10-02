"""Target the omitted flag, child lights and fire inputs in two boss levels.

Runs outside UE with the engine's bundled Python. Existing FModel credentials
are consumed only by EnemyExtractor and never copied into these reports.
"""
from pathlib import Path
import hashlib
import json
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "Content/_Art/Player/Environment/StormPass/Metadata/BladePhantom_ArenaPolish_20261001"
EXTRACTED = ROOT / "Saved/Extracted/StormPass/BladePhantom_Extras_20261001"


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def write(name, data):
    p = REPORT / (name + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def extract(packages, tag, mode="metadata"):
    request = write(tag + "Requests", sorted(set(packages)))
    output = EXTRACTED if mode == "metadata" else ROOT / "Saved/Extracted/StormPass/BladePhantom_ExtrasAssets_20261001"
    subprocess.run([str(Path.home() / ".dotnet/dotnet.exe"), str(ROOT / "Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.dll"), mode, str(output), str(request)], check=True)


def package(value):
    return value["ObjectPath"].split(".")[0] if isinstance(value, dict) and value.get("ObjectPath") else None


def main():
    h = runpy.run_path(str(ROOT / "Scripts/StormPass/audit_stormpass_child_template_coverage.py"))["load_shared"]()
    resolver = h.root.PackageResolver(h.FMODEL_ROOT)
    rows, failed = [], []
    for level in ("StormPass_Boss_Phase_1", "StormPass_Boss_Phase_2"):
        pkg = "BBQ/Content/_Kazan_/Level/StormPass/" + level
        objects = read(h.FMODEL_ROOT / "Exports" / (pkg + ".json"))
        for index, c in enumerate(objects):
            if c["Type"] not in ("xxWPropSkeletalMeshComponent", "xxParticleSystemComponent", "xxNiagaraComponent", "xxPointLightComponent"):
                continue
            ai = h.root.object_index(c.get("Outer"))
            # helper versions expose different local-index parsers; the source
            # ObjectPath has a stable .export_index suffix.
            if ai is None:
                failed.append({"component": index, "reason": "owner"})
                continue
            actor = objects[ai]
            if c["Type"] == "xxPointLightComponent" and actor["Type"] == "xxPointLight":
                continue  # Already restored as SP_SourceLight.
            root_ref = (actor.get("Properties") or {}).get("RootComponent")
            ri = h.root.object_index(root_ref)
            if ri is None:
                failed.append({"component": index, "reason": "actor_root"})
                continue
            chain, error = h.attachment_parent_chain(resolver, c, index, objects[ri], ri, pkg, objects)
            if error:
                failed.append({"component": index, "reason": error})
                continue
            fields = {}
            for n in ("SkeletalMesh", "Template", "Asset", "bVisible", "bHiddenInGame", "bAutoActivate", "AnimationData", "AnimationMode", "AnimClass", "OverrideMaterials", "Intensity", "LightColor", "AttenuationRadius", "LightFalloffExponent", "bUseInverseSquaredFalloff", "SpecularScale", "CastShadows"):
                v, p, i, _ = resolver.inherited_property(c, pkg, objects, n)
                fields[n] = {"value": v, "source_package": p, "source_index": i}
            rows.append({"source_level": level, "source_package": pkg, "actor_object_index": ai, "actor_name": actor["Name"], "component_object_index": index, "component_name": c["Name"], "component_type": c["Type"],
                         "actor_world_transform": h.root.actor_transform(actor, objects[ri], pkg, objects, resolver), "local_transform": h.local_transform(resolver, c, pkg, objects), "attachment_parent_chain": chain,
                         "inherited": fields, "instance_parameters": (c.get("Properties") or {}).get("InstanceParameters", []), "actor_properties": actor.get("Properties") or {}})
    write("MissingRenderPlan", {"components": rows, "unresolved": failed})
    dependencies = {"BBQ/Content/Art/World/World_Material/Prop/Material/WM_COM_Flag_Base_001_WW",
                    "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/SubUV/MI/FMI_FireSubUV_A_03", "BBQ/Content/_Kazan_/Art/VFX/VFX_Material/SubUV/MI/FMI_FireSubUV_B_01"}
    for f in EXTRACTED.rglob("FP_LVL_WBP_LightObj_001_*.json"):
        for obj in read(f):
            if obj["Type"] == "ParticleModuleRequired":
                p = package((obj.get("Properties") or {}).get("Material"))
                if p and p.startswith("BBQ/"):
                    dependencies.add(p)
    extract(dependencies, "RenderMaterial")
    print(json.dumps({"components": len(rows), "unresolved": failed, "materials": len(dependencies)}))


if __name__ == "__main__":
    main()
