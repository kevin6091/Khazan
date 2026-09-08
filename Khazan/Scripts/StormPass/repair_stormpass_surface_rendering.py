"""Close live USD surface-rendering gaps without rebuilding placements.

Unlike the old slot audit, this checks effective inheritance AND packed input
channels. Source packages come from the existing per-slot provenance reports;
basename matching is never used. Fog, water and bespoke repair graphs are not
reparented. Every changed binary is backed up before mutation.
Run audit(), then repair_batch(offset, limit), then audit() in the live map.
"""

import collections
import importlib.util
import json
import os

import unreal

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSET_ROOT = "/Game/_Art/Kazan/Environment/StormPass/"
MAP = ASSET_ROOT + "Maps/L_StormPass_Environment"
REPORTS = os.path.join(ROOT, "Saved", "ImportReports")
PLAN = os.path.join(REPORTS, "StormPass_SurfaceRendering_Plan_20260907.json")
AUDIT = os.path.join(REPORTS, "StormPass_SurfaceRendering_Audit_20260907.json")
BACKUPS = os.path.join(ROOT, "Saved", "ArtBackups", "StormPass_PreRoutePresentation_20260907")
PROVENANCE_REPORTS = (
    "StormPass_Material_Surface_Repair.json",
    "StormPass_OverrideMaterial_Restoration.json",
    "StormPass_ChildOverrideMaterial_Restoration.json",
    "StormPass_FoliageOverrideMaterial_Restoration.json",
    "StormPass_ChildRender_Restoration.json",
    "StormPass_Foliage_AssetPreparation.json",
)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "Scripts", "HeinMach", filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


reader = module("sp_surface_reader", "audit_heinmach_material_rendering.py")
fixer = module("sp_surface_fixer", "repair_heinmach_material_rendering.py")
source_helper = module("sp_surface_source", "repair_heinmach_materials.py")
reader.PROJECT_ASSET_PREFIX = ASSET_ROOT
fixer.PROJECT_ASSET_PREFIX = ASSET_ROOT
fixer.BACKUP_ROOT = BACKUPS


def read(path):
    with open(path, encoding="utf-8-sig") as stream:
        return json.load(stream)


def write(path, value):
    reader.write_json(path, value)


def actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP + "."):
        raise RuntimeError("StormPass must already be open; this script never loads a different map")
    return list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())


def source_index():
    result = collections.defaultdict(list)

    def walk(value):
        if isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, dict):
            # Child/foliage reports use a different key, with the source package
            # on the enclosing mesh record. Resolve the exact USD reference for
            # its source slot instead of guessing from a suffixed MI name.
            if value.get("mesh_package") and value.get("assignments"):
                bindings = None
                for slot in value["assignments"]:
                    target = slot.get("actual_default_material") or slot.get("actual_material_path")
                    name = slot.get("source_material")
                    if target and name:
                        if bindings is None:
                            bindings = source_helper.parse_mesh_materials(value["mesh_package"])
                        reference = bindings["references"].get(name)
                        if reference:
                            result[target].append(source_helper.source_material_info(name, reference_usd=reference))
            path = value.get("actual_material_path") or value.get("material_path")
            package = value.get("package") or value.get("source_package")
            info = value.get("source")
            if path and path.startswith(ASSET_ROOT):
                if isinstance(info, dict) and info.get("json_path"):
                    result[path].append(info)
                if package and isinstance(package, str) and package.startswith("BBQ/Content/"):
                    result[path].append(source_helper.source_material_info(None, package=package))
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)

    for filename in PROVENANCE_REPORTS:
        walk(read(os.path.join(REPORTS, filename)))
    return result


def source_policy(infos):
    infos = [complete_source_info(i) for i in infos]
    usable = [i for i in infos if i.get("json_exists") and i.get("blend_mode") is not None]
    blends = {str(source_helper.blend_mode_value(i["blend_mode"])) for i in usable}
    if len(blends) > 1:
        raise RuntimeError("Conflicting full-package source blend policies: " + repr(usable))
    return usable[0] if usable else None


def complete_source_info(info):
    """Cooked JSON omits zero-valued fields, even when their override is true."""
    result = dict(info)
    path = info.get("json_path")
    if not path or not os.path.isfile(path):
        return result
    payload = read(path)
    if isinstance(payload, list):
        entry = next((r for r in payload if r.get("Type") in ("MaterialInstanceConstant", "Material")), {})
        overrides = (entry.get("Properties") or {}).get("BasePropertyOverrides") or {}
        if overrides.get("bOverride_BlendMode") and result.get("blend_mode") is None:
            result["blend_mode"] = "BLEND_Opaque"
            result["serialization_note"] = "bOverride_BlendMode=true; omitted enum is native zero BLEND_Opaque"
        if overrides.get("bOverride_TwoSided") and result.get("two_sided") is None:
            result["two_sided"] = False
    return result


def audit():
    usage, labels, materials = collections.Counter(), collections.defaultdict(list), {}
    for actor in actors():
        if not actor.get_actor_label().startswith(("SP_Prop_", "SP_ChildProp_", "SP_Foliage_")):
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(component.get_num_materials()):
                material = component.get_material(slot)
                if not isinstance(material, unreal.MaterialInstanceConstant):
                    continue
                path = material.get_path_name()
                if not path.startswith(ASSET_ROOT):
                    continue
                materials[path] = material
                usage[path] += 1
                if len(labels[path]) < 3:
                    labels[path].append(actor.get_actor_label())
    provenance = source_index()
    rows, counts = [], collections.Counter()
    for path, material in sorted(materials.items()):
        parent = material.get_editor_property("parent")
        if not parent or not parent.get_path_name().startswith("/USDCore/"):
            counts["bespoke_graphs_preserved"] += 1
            continue
        record = reader.material_record(path, material, usage[path], labels[path])
        policy = source_policy(provenance.get(path, []))
        record["source_policy"] = policy
        issues = []
        if record["classification"]["needs_channel_repair"]:
            issues.append("packed_channels")
        if policy:
            expected = str(source_helper.blend_mode_value(policy["blend_mode"]))
            if expected != record["surface"]["effective_blend_mode"]:
                issues.append("effective_blend")
        elif "TRANSLUCENT" in str(record["surface"]["effective_blend_mode"]):
            issues.append("unresolved_translucent_source")
        record["issues"] = issues
        rows.append(record)
        counts["usd_materials"] += 1
        counts["usd_live_slots"] += usage[path]
        counts["unresolved_source"] += int(policy is None)
        for issue in issues:
            counts[issue] += 1
    payload = {"map": MAP, "counts": dict(counts), "materials": rows,
               "failure_count": sum(bool(r["issues"]) for r in rows),
               "policy": "source blend preserved; source packed ORM: R AO, G roughness, B metallic"}
    write(AUDIT, payload)
    if not os.path.isfile(PLAN):
        write(PLAN, payload)
    print(json.dumps({"report": AUDIT, "failure_count": payload["failure_count"], **dict(counts)}))
    return payload


def repair_batch(offset=0, limit=30):
    actors()  # Scope assertion, not map mutation.
    plan = read(PLAN)
    selected = plan["materials"][int(offset):int(offset) + int(limit)]
    provenance = source_index()
    results = []
    for record in selected:
        if not record["issues"]:
            continue
        path = record["path"]
        info = source_policy(provenance.get(path, [])) or record.get("source_policy")
        if not path.startswith(ASSET_ROOT) or "/Fog/" in path:
            raise RuntimeError("Out-of-scope material: " + path)
        if "unresolved_translucent_source" in record["issues"] and not info:
            results.append({"path": path, "deferred": "extract exact source policy"})
            continue
        material = unreal.load_asset(path)
        fixer.backup_asset(path)
        # Keep source cutout alpha even when the current diffuse has constant alpha.
        # The shared generic helper's alpha-only opaque heuristic is not used.
        safe_record = dict(record)
        safe_record["classification"] = dict(record["classification"], render_policy="alpha_preserving")
        if info:
            expected_blend = source_helper.blend_mode_value(info["blend_mode"])
            if expected_blend in (unreal.BlendMode.BLEND_OPAQUE, unreal.BlendMode.BLEND_MASKED):
                unreal.MaterialEditingLibrary.set_material_instance_parent(material, unreal.load_asset(fixer.USD_OPAQUE_PARENT))
            overrides = material.get_editor_property("base_property_overrides")
            overrides.set_editor_property("override_blend_mode", True)
            overrides.set_editor_property("blend_mode", expected_blend)
            if info.get("two_sided") is not None:
                overrides.set_editor_property("override_two_sided", True)
                overrides.set_editor_property("two_sided", bool(info["two_sided"]))
            if info.get("opacity_mask_clip_value") is not None:
                overrides.set_editor_property("override_opacity_mask_clip_value", True)
                overrides.set_editor_property("opacity_mask_clip_value", float(info["opacity_mask_clip_value"]))
            material.set_editor_property("base_property_overrides", overrides)
        changes = []
        if record["classification"].get("packed_mask_texture"):
            mask = fixer.texture_from_record(record, "roughness")
            scalar_names = fixer.parameter_names(material, "scalar")
            vector_names = fixer.parameter_names(material, "vector")
            texture_names = fixer.parameter_names(material, "texture")
            for name, value in (("RoughnessTextureComponent", (0, 1, 0, 0)),
                                ("MetallicTextureComponent", (0, 0, 1, 0)),
                                ("AmbientOcclusionTextureComponent", (1, 0, 0, 0))):
                if not reader.component_matches(reader.vector_value(material, name), value):
                    fixer.set_vector(material, vector_names, name, value)
                    changes.append(name)
            for name in ("UseRoughnessTexture", "UseMetallicTexture", "UseAmbientOcclusionTexture"):
                if reader.scalar_value(material, name) != 1.0:
                    fixer.set_scalar(material, scalar_names, name, 1.0)
            if reader.texture_value(material, "AmbientOcclusionTexture") != mask:
                fixer.set_texture(material, texture_names, "AmbientOcclusionTexture", mask)
        result = {"path": path, "changes": changes, "source_policy": info}
        unreal.MaterialEditingLibrary.update_material_instance(material)
        unreal.EditorAssetLibrary.set_metadata_tag(material, "StormPassSurfaceRendering", "20260907: source blend + packed ORM")
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError("Save failed: " + path)
        results.append(result)
    destination = os.path.join(REPORTS, "StormPass_SurfaceRendering_Batch_{:04d}.json".format(int(offset)))
    write(destination, {"offset": offset, "limit": limit, "results": results})
    print(json.dumps({"offset": offset, "selected": len(selected), "processed": len(results), "report": destination}))
    return results


if __name__ == "__main__":
    audit()
