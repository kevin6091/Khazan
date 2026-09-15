"""Targeted source discovery and usage selection for ApesStoneHandElite.

Reuse the tested FModel extraction entry point, without importing the complete
name-matched inventory into Unreal. Keep usage evidence and exclusions.
"""
from __future__ import annotations
import collections
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import prepare_yetuga_sources as extraction

PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / "Saved/Extracted/ApesStoneHandElite_20260915"
META = ROOT / "Metadata"
EXTERNAL = pathlib.Path.home() / "Desktop/카잔/EnemyExtracts/ApesStoneHandElite_20260915"
DEST = "/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite"
DESIGN_ROOT = "BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/"
MODEL_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/ApesStoneHandElite/"
RECIPE_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Data/RandomLookInfo/MonsterType/CD_RD_M_ApesStoneHandElite"
INDEX = ROOT / "Discovery/TargetedPackageIndex.json"
extraction.ROOT, extraction.META, extraction.EXTERNAL = ROOT, META, EXTERNAL
read, write = extraction.read, extraction.write
references, package_path = extraction.references, extraction.package_path


def baseline():
    target = ROOT / "WorkspaceBaseline.json"
    if target.exists():
        return
    git_root = pathlib.Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=PROJECT, text=True).strip())
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "-z"], cwd=git_root).decode("utf-8")
    dirty = {}
    for record in status.split("\0"):
        if record:
            path = git_root / record[3:]
            if path.is_file():
                dirty[record[3:]] = hashlib.sha256(path.read_bytes()).hexdigest()
    protected = {}
    for folder in ["Source", "Config"]:
        for path in (PROJECT / folder).rglob("*"):
            if path.is_file():
                protected[path.relative_to(PROJECT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(target, {"git_root": str(git_root), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(), "status": status, "dirty_file_sha256": dirty, "source_config_sha256": protected})


def inspect():
    baseline()
    indexed = [p.removesuffix(".uasset") for p in read(INDEX)]
    requested = {p for p in indexed if p.startswith((DESIGN_ROOT, MODEL_ROOT, RECIPE_ROOT)) or "/CHA_Material/Material/" in p or "/CHA_Data/BoneModInfo/" in p or "/Prop/Dead/" in p or "/Prop_Instances/Dead/" in p}
    objects, failures = extraction.ensure_metadata(requested, "Apes_InitialUsageMetadata")
    write(ROOT / "Discovery/InitialTypes.json", {p: sorted({o.get("Type", "") for o in values}) for p, values in objects.items()})
    summary = {"requested": len(requested), "metadata_failures": failures, "types": dict(collections.Counter(o.get("Type", "") for values in objects.values() for o in values))}
    write(ROOT / "Discovery/InitialSummary.json", summary)
    print(json.dumps(summary), flush=True)


def cdo(objects):
    return next(o for o in objects if o.get("Name", "").startswith("Default__"))


def usage():
    variants = []
    for suffix, role in [("_Early", "Early"), ("", "Standard")]:
        cb = DESIGN_ROOT + "Base_Setting/CB_ApesStoneHand_E" + suffix
        objects = read(META / (cb + ".json"))
        component = next(o for o in objects if o.get("Name", "").startswith("CD_RD_") and o["Name"].endswith("_GEN_VARIABLE"))
        recipe = package_path(component["Template"]["ObjectPath"])
        defaults = cdo(read(META / (recipe + ".json")))["Properties"]
        effective = {**defaults, **component.get("Properties", {})}
        parts = effective["FacePartsList"]
        for part_index, part in enumerate(parts):
            for material_index, materials in enumerate(part["MaterialVariations"]):
                variants.append({"role": role, "source_character": cb, "source_recipe": recipe,
                    "source_component": component["Name"], "recipe_defaults": defaults,
                    "component_overrides": component.get("Properties", {}), "effective_recipe": effective,
                    "part_index": part_index, "material_index": material_index,
                    "mesh": package_path(part["Mesh"]["AssetPathName"]),
                    "materials": [package_path(v["AssetPathName"]) for v in materials["Materials"]],
                    "source_character_properties": cdo(objects).get("Properties", {}),
                    "source_mesh_component": next(o["Properties"] for o in objects if o["Name"] == "CharacterMesh0")})
    spawns = []
    for level in ["HeinMach", "StormPass"]:
        path = extraction.FMODEL_ROOT / f"Exports/BBQ/Content/_Kazan_/Level/{level}/{level}_Spawn_Main01.json"
        for obj in read(path):
            if obj.get("Type") == "xxSpawnHandler_Character" and "ApesStoneHand" in json.dumps(obj):
                spawns.append({"level": level, "source_level_package": f"BBQ/Content/_Kazan_/Level/{level}/{level}_Spawn_Main01",
                    "actor_name": obj["Name"], "properties": obj.get("Properties", {}),
                    "references": sorted(set(references(obj)))})
    write(ROOT / "VariantUsage.json", {"variants": variants, "level_spawns": spawns,
        "selection_basis": "CB SCS component template overrides replace recipe CDO arrays. Early uses base mesh/materials; Standard overrides the recipe V2 default with V3.",
        "excluded": [
            {"asset": MODEL_ROOT + "Model/C_M_ApesStoneHandEliteV2", "reason": "Recipe CDO default superseded by Standard CB component FacePartsList=V3; no effective consumer in inspected CB/spawns."},
            {"asset": MODEL_ROOT + "Model/C_M_ApesStoneHandElite_EmptyMesh", "reason": "Original modular animation carrier; use visible full-body mesh directly, preserve source component metadata."},
            {"asset": "CM_M_Ghost_ApesStoneHandElite_* / AP_ApesStoneHand_E_Wraith", "reason": "Ghost/Wraith special representation, no consumer from selected live CB/spawn closure; metadata retained, not asserted unused throughout the game."},
            {"asset": "WP_COM_ApesStoneHandElite_Dead_002/003", "reason": "Static environment corpse props, not animated living character variants."}]})
    write(ROOT / "LevelPresence.json", spawns)
    return variants, spawns


def discover():
    baseline()
    variants, spawns = usage()
    visible_meshes = {v["mesh"] for v in variants}
    material_leaves = {p for v in variants for p in v["materials"]}
    selected_recipe_refs = set()
    for v in variants:
        selected_recipe_refs.update(references(v["effective_recipe"]))
    def follow(owner, kind, target):
        if owner.startswith(RECIPE_ROOT):
            return target in selected_recipe_refs
        if target.startswith(DESIGN_ROOT):
            return True
        if kind in {"Material", "MaterialInstanceConstant", "MaterialFunction", "Texture2D"}:
            return target.startswith("BBQ/Content/")
        if kind == "Skeleton":
            return False  # Its Yetuga PreviewMesh is not an Apes character dependency.
        if target.startswith(MODEL_ROOT):
            return target in visible_meshes or not "/Model/C_M_ApesStoneHandEliteV" in target
        if kind in {"AnimComposite", "xxAnimationProfile", "BlendSpace", "BlendSpace1D"} and "/Art/Character/CHA_Model/" in target:
            return True  # Verify actual Skeleton, including shared Yetuga-named sources.
        if kind == "SkeletalMesh":
            return target in material_leaves or any(token in target for token in ["_Skeleton", "Physics", "AnimBlueprint", "CtrlRig"])
        return target.startswith(RECIPE_ROOT) or "/CHA_Data/BoneModInfo/" in target or "/CHA_Data/ColorInfo/" in target
    pending = {v["source_character"] for v in variants} | visible_meshes | material_leaves
    pending.update(r for row in spawns for r in row["references"] if r.startswith(DESIGN_ROOT))
    visited, types, edges, excluded, failures = set(), {}, [], set(), []
    round_number = 0
    while pending:
        round_number += 1
        objects, errors = extraction.ensure_metadata(pending, f"Apes_Closure_{round_number:02d}")
        failures.extend(errors)
        visited.update(pending)
        upcoming = set()
        for owner, values in objects.items():
            types[owner] = sorted({v.get("Type", "") for v in values})
            for obj in values:
                kind = obj.get("Type", "")
                for target in set(references(obj)) - {owner}:
                    followed = follow(owner, kind, target)
                    edges.append({"source": owner, "target": target, "owner_type": kind, "followed": followed})
                    if followed:
                        upcoming.add(target)
                    else:
                        excluded.add(target)
        pending = upcoming - visited
        print("APES_CLOSURE", round_number, len(visited), "next", len(pending), "failures", len(errors), flush=True)
    exports = sorted(p for p, ts in types.items() if "Texture2D" in ts or "AnimSequence" in ts or p in visible_meshes)
    result = {"schema_version": 1, "source_character": "CB_ApesStoneHand_E_Early / CB_ApesStoneHand_E", "levels": ["HeinMach", "StormPass"],
        "spawn_records": spawns, "packages": sorted(types), "exports": exports, "types": types,
        "dependencies": sorted(edges, key=lambda e: (e["source"],e["target"],e["owner_type"])), "external_references": sorted(excluded),
        "metadata_failures": failures, "selected_meshes": sorted(visible_meshes), "material_leaves": sorted(material_leaves)}
    write(ROOT / "SourceClosure.json", result)
    summary = {"status": "passed" if not failures else "failed", "selected_packages": len(types), "export_packages": len(exports),
        "meshes": sorted(visible_meshes), "type_counts": dict(collections.Counter(t for ts in types.values() for t in ts)), "metadata_failures": failures}
    write(ROOT / "DiscoverySummary.json", summary)
    print(json.dumps({k:v for k,v in summary.items() if k != "type_counts"}), flush=True)
    if failures:
        raise RuntimeError("Resolve selected metadata failures before export")


def export():
    extraction.export_sources()


if __name__ == "__main__":
    {"inspect": inspect, "discover": discover, "export": export}[sys.argv[1] if len(sys.argv) > 1 else "inspect"]()
