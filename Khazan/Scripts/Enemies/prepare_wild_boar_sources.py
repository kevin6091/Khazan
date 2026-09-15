"""Targeted source discovery and usage selection for WildBoar.

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
ROOT = PROJECT / "Saved/Extracted/WildBoar_20260915"
META = ROOT / "Metadata"
EXTERNAL = pathlib.Path.home() / "Desktop/카잔/EnemyExtracts/WildBoar_20260915"
DEST = "/Game/_Art/Enemies/Shared/Beasts/WildBoar"
DESIGN_ROOT = "BBQ/Content/_Kazan_/Design/Monster/Beast/WildBoar_New/"
MODEL_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/WildBoar/"
RECIPE_ROOT = "BBQ/Content/_Kazan_/Art/Character/CHA_Data/RandomLookInfo/MonsterType/"
RECIPE = RECIPE_ROOT + "CD_RD_M_WildBoar_001"
CB = DESIGN_ROOT + "Base_Setting/CB_WildBoar_New"
AP = DESIGN_ROOT + "Base_Setting/AP_WildBoar_New"
SA = DESIGN_ROOT + "Base_Setting/SA_WildBoar"
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
    task_prefixes = (
        "Khazan/Scripts/Enemies/", "Khazan/Content/_Art/Enemies/Shared/Beasts/",
        "Khazan/Docs/Art/WILD_", "Khazan/Docs/Art/ART_",
    )
    for record in status.split("\0"):
        if record:
            relative = record[3:]
            if relative.startswith(task_prefixes) and ("wild_" in relative.lower() or "/Beasts/" in relative or "/WILD_" in relative):
                continue
            path = git_root / relative
            if path.is_file():
                dirty[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    protected = {}
    for folder in ["Source", "Config"]:
        for path in (PROJECT / folder).rglob("*"):
            if path.is_file():
                protected[path.relative_to(PROJECT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(target, {"git_root": str(git_root), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(), "status": status, "dirty_file_sha256": dirty, "source_config_sha256": protected})


def ensure_index():
    if INDEX.exists():
        return
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [str(extraction.DOTNET), str(extraction.DLL), "index", str(INDEX.parent), "WildBoar"],
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"WildBoar targeted index failed with exit code {result.returncode}")


def inspect():
    baseline()
    ensure_index()
    indexed = [p.removesuffix(".uasset") for p in read(INDEX)]
    requested = {
        p for p in indexed
        if p in {CB, AP, SA, RECIPE}
        or p.startswith(MODEL_ROOT + "Model/")
        or ("/CHA_Material/Material/" in p and "WildBoar" in p)
        or ("/CHA_Data/BoneModInfo/" in p and "Boar" in p)
    }
    objects, failures = extraction.ensure_metadata(requested, "WildBoar_InitialUsageMetadata")
    write(ROOT / "Discovery/InitialTypes.json", {p: sorted({o.get("Type", "") for o in values}) for p, values in objects.items()})
    summary = {"requested": len(requested), "metadata_failures": failures, "types": dict(collections.Counter(o.get("Type", "") for values in objects.values() for o in values))}
    write(ROOT / "Discovery/InitialSummary.json", summary)
    print(json.dumps(summary), flush=True)


def cdo(objects):
    return next(o for o in objects if o.get("Name", "").startswith("Default__"))


def usage():
    objects = read(META / (CB + ".json"))
    component = next(o for o in objects if o.get("Name", "").startswith("CD_RD_") and o["Name"].endswith("_GEN_VARIABLE"))
    recipe = package_path(component["Template"]["ObjectPath"])
    if recipe != RECIPE:
        raise RuntimeError(f"CB_WildBoar_New recipe changed: {recipe}")
    defaults = cdo(read(META / (recipe + ".json")))["Properties"]
    effective = {**defaults, **component.get("Properties", {})}
    meshes = [package_path(value["AssetPathName"]) for value in effective["FaceMesh"]]
    parts = effective["FacePartsList"]
    if len(parts) != 1 or len(parts[0]["MaterialVariations"]) != len(meshes):
        raise RuntimeError("WildBoar live FaceMesh/FacePartsList variation alignment changed")
    variants = []
    for material_index, (mesh, materials) in enumerate(zip(meshes, parts[0]["MaterialVariations"])):
        stem = mesh.rsplit("/", 1)[-1]
        suffix = stem.removeprefix("C_M_WildBoar") or "1"
        role = "CoatV" + suffix.removeprefix("V")
        variants.append({"role": role, "source_character": CB, "source_recipe": recipe,
            "source_component": component["Name"], "recipe_defaults": defaults,
            "component_overrides": component.get("Properties", {}), "effective_recipe": effective,
            "part_index": 0, "material_index": material_index,
            "mesh": mesh, "source_parts_mesh": package_path(parts[0]["Mesh"]["AssetPathName"]),
            "materials": [package_path(v["AssetPathName"]) for v in materials["Materials"]],
            "source_character_properties": cdo(objects).get("Properties", {}),
            "source_mesh_component": next(o["Properties"] for o in objects if o["Name"] == "CharacterMesh0")})
    spawns = []
    for level in ["HeinMach", "StormPass"]:
        path = extraction.FMODEL_ROOT / f"Exports/BBQ/Content/_Kazan_/Level/{level}/{level}_Spawn_Main01.json"
        for obj in read(path):
            actor_bp = obj.get("Properties", {}).get("ActorBP_Soft", {}).get("AssetPathName", "")
            if obj.get("Type") == "xxSpawnHandler_Character" and "/WildBoar_New/" in actor_bp:
                spawns.append({"level": level, "source_level_package": f"BBQ/Content/_Kazan_/Level/{level}/{level}_Spawn_Main01",
                    "actor_name": obj["Name"], "properties": obj.get("Properties", {}),
                    "references": sorted(set(references(obj)))})
    if len(spawns) != 2 or {row["level"] for row in spawns} != {"StormPass"}:
        raise RuntimeError(f"Expected the two live StormPass WildBoar spawns, found {len(spawns)}")
    write(ROOT / "VariantUsage.json", {"variants": variants, "level_spawns": spawns,
        "selection_basis": "StormPass uses CB_WildBoar_New. Its SCS component keeps the CD_RD_M_WildBoar_001 CDO arrays, whose PartsIndexCache exposes three aligned coat outcomes. The V1/V2/V3 ActorX meshes differ only in MATT0000 and therefore become one geometry asset with three materialized Blueprints.",
        "excluded": [
            {"asset": MODEL_ROOT + "Model/C_M_WildBoar_EmptyMesh", "reason": "Original animation carrier; the visible WildBoar mesh is used directly while component transform metadata is preserved."},
            {"asset": MODEL_ROOT + "Model/C_M_WildBoar_BodyHit / _IKHit / _PA / _CtrlRig", "reason": "Hit/physics/control helper assets are metadata dependencies, not visible character geometry."}]})
    write(ROOT / "LevelPresence.json", spawns)
    return variants, spawns


def discover():
    baseline()
    ensure_index()
    inspect()
    variants, spawns = usage()
    visible_meshes = {v["mesh"] for v in variants}
    material_leaves = {p for v in variants for p in v["materials"]}
    selected_recipe_refs = set()
    for v in variants:
        selected_recipe_refs.update(references(v["effective_recipe"]))
    def follow(owner, kind, target):
        if owner == RECIPE:
            return target in selected_recipe_refs
        if target.startswith(DESIGN_ROOT):
            return True
        if kind in {"Material", "MaterialInstanceConstant", "MaterialFunction", "Texture2D"}:
            return target.startswith("BBQ/Content/")
        if kind == "Skeleton":
            return False  # PreviewMesh is not a runtime dependency; socket metadata stays on this Skeleton package.
        if target.startswith(MODEL_ROOT):
            name = target.rsplit("/", 1)[-1]
            if "/Model/" in target:
                return target in visible_meshes or name.endswith(("_Skeleton", "_Physics", "_AB", "_CtrlRig", "_IKHit", "_BodyHit", "_PA"))
            return True
        if kind in {"AnimComposite", "xxAnimationProfile", "BlendSpace", "BlendSpace1D"} and "/Art/Character/CHA_Model/" in target:
            return True  # Verify actual Skeleton, including shared Yetuga-named sources.
        if kind == "SkeletalMesh":
            return target in material_leaves or any(token in target for token in ["_Skeleton", "Physics", "AnimBlueprint", "CtrlRig"])
        return target == RECIPE or "/CHA_Data/BoneModInfo/" in target or "/CHA_Data/ColorInfo/" in target
    pending = {CB, AP, SA, RECIPE} | visible_meshes | material_leaves
    pending.update(r for row in spawns for r in row["references"] if r.startswith(DESIGN_ROOT))
    visited, types, edges, excluded, failures = set(), {}, [], set(), []
    round_number = 0
    while pending:
        round_number += 1
        objects, errors = extraction.ensure_metadata(pending, f"WildBoar_Closure_{round_number:02d}")
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
        print("WILD_BOAR_CLOSURE", round_number, len(visited), "next", len(pending), "failures", len(errors), flush=True)
    exports = sorted(p for p, ts in types.items() if "Texture2D" in ts or "AnimSequence" in ts or p in visible_meshes)
    result = {"schema_version": 1, "source_character": CB, "source_animation_profile": AP,
        "inspected_levels": ["HeinMach", "StormPass"], "levels": ["StormPass"],
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
    closure = read(ROOT / "SourceClosure.json")
    extraction.run_exporter("export", ROOT / "Assets", closure["exports"], "WildBoar_ArtAnimationExport")
    extraction.run_exporter("raw", EXTERNAL / "RawCookedArchive", closure["packages"], "WildBoar_RawArchive")
    missing = []
    for package in closure["exports"]:
        if not any((ROOT / "Assets" / f"{package}{suffix}").exists() for suffix in (".psk", ".pskx", ".psa", ".png")):
            missing.append(package)
    if missing:
        raise RuntimeError(f"Missing converted WildBoar exports: {missing}")
    shutil.copytree(META, EXTERNAL / "Metadata", dirs_exist_ok=True)
    shutil.copytree(ROOT / "Assets", EXTERNAL / "Assets", dirs_exist_ok=True)
    for name in ["SourceClosure.json", "LevelPresence.json", "DiscoverySummary.json", "VariantUsage.json"]:
        shutil.copy2(ROOT / name, EXTERNAL / name)
    summary = {"status": "passed", "selected_packages": len(closure["packages"]),
        "export_packages": len(closure["exports"]), "missing_exports": missing,
        "work_assets": str(ROOT / "Assets"), "external_archive": str(EXTERNAL)}
    write(ROOT / "SourceExportSummary.json", summary)
    shutil.copy2(ROOT / "SourceExportSummary.json", EXTERNAL / "SourceExportSummary.json")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    {"inspect": inspect, "discover": discover, "export": export}[sys.argv[1] if len(sys.argv) > 1 else "inspect"]()
