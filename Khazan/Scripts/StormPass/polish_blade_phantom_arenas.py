"""Targeted Blade Phantom arena inspection and reversible environment polish.

Only StormPass environment assets are edited. The source-coordinate review is
retained in metadata; the requested authoring layout translates Phase2 beside
Phase1 and keeps both visible. Review markers are editor-only and do not
implement the boss, teleport, AI, or phase gameplay.
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import shutil

import unreal

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "Content/_Art/Player/Environment/StormPass/Metadata"
SOURCE = Path.home() / "Desktop" / "\uce74\uc794/Exports/BBQ/Content/_Kazan_/Level/StormPass"
MAP = "/Game/Maps/L_StormPass_Environment"
BACKUP = ROOT / "Saved/ArtBackups/StormPass_BladePhantom_PrePolish_20261001"
REPORT = META / "BladePhantom_ArenaPolish_20261001"
PHASES = ("StormPass_Boss_Phase_1", "StormPass_Boss_Phase_2")
POLISH_ROOT = "/Game/_Art/Player/Environment/StormPass/Reconstructed/BladePhantomPolish"
SIDE_REPORT = META / "BladePhantom_SideBySide_20261002"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(name, data):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP + "."):
        raise RuntimeError("Open the StormPass environment map first")
    return list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())


def phase(label):
    for index, name in enumerate(PHASES, 1):
        if name + "_" in label:
            return index
    return 2 if label.startswith("SP_Landscape_Boss_") else None


def side_layout():
    path = SIDE_REPORT / "Layout.json"
    return read(path) if path.exists() else None


def vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def pose(a):
    r = a.get_actor_rotation()
    return {"location_cm": vec(a.get_actor_location()), "rotation_degrees": [r.pitch, r.yaw, r.roll], "scale": vec(a.get_actor_scale3d())}


def backup_file(path):
    path = Path(path).resolve()
    relative = path.relative_to(ROOT.resolve())
    destination = BACKUP / relative
    if path.is_file() and not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    return {"file": str(relative), "sha256": sha(destination)} if destination.is_file() else None


def preflight_backup():
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError("Unsaved map changes: " + repr(dirty))
    paths = [ROOT / (MAP.replace('/Game/', 'Content/') + '.umap')]
    paths += [META / n for n in ("StormPass_CurrentReviewVariant.json", "StormPass_PhaseVisibilityBaseline_20260907.json", "StormPass_PlayableCameraAnchors.json")]
    records = [backup_file(p) for p in paths]
    write("Backup", {"files": records, "dirty_content_at_start": [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]})
    print(json.dumps({"backup": str(BACKUP), "files": len(records)}))


def source_anchors():
    helper = runpy.run_path(str(ROOT / "Scripts/StormPass/analyze_stormpass_playable_route.py"))
    rows = []
    hashes = {}
    for filename in ("StormPass_Spawn_Main01.json", "StormPass_Boss_Phase_1.json", "StormPass_Boss_Phase_2.json", "StormPass_Cinema_Boss_Start.json"):
        path = SOURCE / filename
        data = read(path)
        hashes[filename] = sha(path)
        for i, a in enumerate(data):
            p = a.get("Properties") or {}
            ri = helper["local_index"](p.get("RootComponent"))
            if ri is None:
                continue
            transform = helper["transform_record"](helper["component_transform"](data, ri))
            if filename == "StormPass_Spawn_Main01.json" and transform["location_cm"][0] < 130000:
                continue
            if filename != "StormPass_Spawn_Main01.json" and a.get("Type") not in ("TargetPoint", "xxPlayerStart", "xxSimpleSkeletalMeshActor"):
                continue
            rows.append({"source_json": filename, "index": i, "name": a["Name"], "type": a["Type"], **transform, "properties": p})
    result = write("OriginalAnchors", {"source_hashes": hashes, "actors": rows})
    print(json.dumps({"anchors": [{k: r[k] for k in ("source_json", "name", "type", "location_cm")} for r in rows]}, ensure_ascii=False))
    return result


def audit(name="Preflight"):
    all_actors = actors()
    by_label = {a.get_actor_label(): a for a in all_actors}
    placements = read(META / "StormPass_ResolvedRootPlacements.json")["placements"]
    expected = [p for p in placements if p["source_level"] in PHASES]
    failures, missing, meshes, materials = [], [], {}, {}
    maximum_location_error = 0.0
    for row in expected:
        label = ("SP_Prop_{source_level}_{source_object_index}_{actor_name}".format(**row))[:220]
        a = by_label.get(label)
        if not a:
            missing.append(label)
            continue
        target = row["transform"]["location_cm"]
        error = max(abs(pose(a)["location_cm"][i] - target[k]) for i, k in enumerate("xyz"))
        maximum_location_error = max(error, maximum_location_error)
        if error > 0.002:  # Technical float comparison tolerance, not gameplay tuning.
            failures.append({"label": label, "problem": "location", "error_cm": error, "source": row["transform"], "actual": pose(a)})
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        m = c.get_editor_property("static_mesh") if c else None
        if not m or m.get_name() != "SM_" + row["static_mesh_package"].rsplit("/", 1)[1]:
            failures.append({"label": label, "problem": "mesh", "source_package": row["static_mesh_package"], "actual": m.get_path_name() if m else None})
    scope = [a for a in all_actors if phase(a.get_actor_label())]
    records = []
    for a in scope:
        item = {"label": a.get_actor_label(), "phase": phase(a.get_actor_label()), "class": a.get_class().get_name(), **pose(a), "hidden_game": bool(a.get_editor_property("hidden")), "components": []}
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            mesh = c.get_editor_property("static_mesh")
            slots = []
            for i in range(c.get_num_materials()):
                m = c.get_material(i)
                path = m.get_path_name() if m else None
                slots.append(path)
                if not m or any(b in path for b in ("WorldGridMaterial", "DefaultMaterial", "DisplayColor")):
                    failures.append({"label": a.get_actor_label(), "problem": "fallback_material", "slot": i, "material": path})
                if m:
                    materials[path] = m
            if mesh:
                meshes[mesh.get_path_name()] = mesh
            item["components"].append({"mesh": mesh.get_path_name() if mesh else None, "materials": slots, "visible": bool(c.get_editor_property("visible")), "collision": str(c.get_collision_enabled())})
        records.append(item)
    material_rows = []
    surface_reader = runpy.run_path(str(ROOT / "Scripts/HeinMach/audit_heinmach_material_rendering.py"))
    for path, m in sorted(materials.items()):
        parent = m.get_editor_property("parent") if isinstance(m, unreal.MaterialInstanceConstant) else None
        material_rows.append({"asset": path, "class": m.get_class().get_name(), "parent": parent.get_path_name() if parent else None, "surface": surface_reader["material_surface_state"](m), "scalars": [{"name": str(p.parameter_info.name), "value": p.parameter_value} for p in m.get_editor_property("scalar_parameter_values")] if isinstance(m, unreal.MaterialInstanceConstant) else [], "textures": [{"name": str(p.parameter_info.name), "value": p.parameter_value.get_path_name() if p.parameter_value else None} for p in m.get_editor_property("texture_parameter_values")] if isinstance(m, unreal.MaterialInstanceConstant) else []})
    result = write(name, {"map": MAP, "actor_count": len(all_actors), "phase_counts": dict(collections.Counter(phase(a.get_actor_label()) for a in scope)), "expected_root_props": len(expected), "maximum_root_location_error_cm": maximum_location_error, "missing": missing, "failures": failures, "unique_meshes": len(meshes), "unique_materials": len(materials), "actors": records, "materials": material_rows})
    print(json.dumps({k: result[k] for k in ("actor_count", "phase_counts", "expected_root_props", "maximum_root_location_error_cm", "unique_meshes", "unique_materials")}, ensure_ascii=False))
    print(json.dumps({"missing": len(missing), "failures": failures[:12]}))
    return result


def view(variant):
    helper = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_route_presentation.py"))
    return helper["set_variant"](variant, save=False)


def source_transform(row):
    t = row
    p, r, s = [t.get(k, {}) for k in ("location_cm", "rotation_degrees", "scale")]
    return unreal.Transform(location=unreal.Vector(*(p.get(k, 0) for k in "xyz")),
                            rotation=unreal.Rotator(pitch=r.get("pitch", 0), yaw=r.get("yaw", 0), roll=r.get("roll", 0)),
                            scale=unreal.Vector(*(s.get(k, 1) for k in "xyz")))


def transform_error(actual, expected):
    qa, qb = actual.rotation, expected.rotation
    dot = abs(sum(getattr(qa, k) * getattr(qb, k) for k in "xyzw"))
    dot /= math.sqrt(sum(getattr(qa, k) ** 2 for k in "xyzw") * sum(getattr(qb, k) ** 2 for k in "xyzw"))
    return {"location_cm": max(abs(getattr(actual.translation, k) - getattr(expected.translation, k)) for k in "xyz"),
            "rotation_degrees": math.degrees(2 * math.acos(min(1.0, dot))),
            "scale": max(abs(getattr(actual.scale3d, k) - getattr(expected.scale3d, k)) for k in "xyz")}


def audit_geometry(name="GeometryBefore"):
    """Compare every arena render actor against the stored/raw source data."""
    by_label = {a.get_actor_label(): a for a in actors()}
    helper = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_child_render_meshes.py"))
    foliage = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_foliage.py"))
    material_helper = helper["material_helper"]
    expectations = []
    for r in read(META / "StormPass_ResolvedRootPlacements.json")["placements"]:
        if r["source_level"] in PHASES:
            expectations.append({"category": "root", "label": ("SP_Prop_{source_level}_{source_object_index}_{actor_name}".format(**r))[:220], "transform": source_transform(r["transform"]), "mesh": r["static_mesh_package"], "overrides": r["override_material_packages"]})
    for r in read(REPORT / "ChildSourceAudit.json")["resolved_child_mesh_components"]:
        expectations.append({"category": "child", "label": "SP_ChildProp_{}_{:05d}_{:05d}".format(r["source_level"], r["actor_object_index"], r["component_object_index"]), "transform": helper["expected_world_transform"](r), "mesh": r["static_mesh_package"], "overrides": r["override_material_packages"]})
    for r in read(META / "StormPass_FogMaterials.json")["fog_actors"]:
        if r["source_level"] in PHASES:
            expectations.append({"category": "fog", "label": "SP_Fog_{}_{:05d}_{}".format(r["source_level"], r["source_actor_object_index"], r["source_actor_name"]), "transform": source_transform(r["transform"]), "mesh": None, "overrides": []})
    for r in read(META / "StormPass_SourceLights.json")["lights"]:
        if r["source_level"] in PHASES:
            expectations.append({"category": "light", "label": "SP_SourceLight_{}_{:d}_{}".format(r["source_level"], r["source_object_index"], r["actor_name"]), "transform": source_transform(r["transform"]), "mesh": None, "overrides": []})
    layout = side_layout()
    offset = unreal.Vector(*layout["source_phase2_translation_cm"]) if layout and layout.get("enabled") else unreal.Vector()
    for row in expectations:
        if phase(row["label"]) == 2:
            t = row["transform"]
            t.set_editor_property("translation", t.translation + offset)
    plan = {r["asset"].replace("/_Art/Kazan/", "/_Art/Player/"): r for r in read(META / "StormPass_InheritedSurfaceControls_20260907.json")["materials"]}
    errors, results, mesh_slots, tex_settings = [], [], {}, {}
    for r in expectations:
        a = by_label.get(r["label"])
        if not a:
            errors.append({"label": r["label"], "problem": "missing"})
            continue
        e = transform_error(a.get_actor_transform(), r["transform"])
        if e["location_cm"] > .02 or e["rotation_degrees"] > .01 or e["scale"] > .00002:
            errors.append({"label": r["label"], "problem": "transform", "error": e})
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if r["mesh"] and c:
            mesh = c.get_editor_property("static_mesh")
            if not mesh or mesh.get_name() != "SM_" + r["mesh"].rsplit("/", 1)[1]:
                errors.append({"label": r["label"], "problem": "mesh"})
            if mesh and r["mesh"] not in mesh_slots:
                parsed = material_helper.parse_mesh_materials(r["mesh"])
                mesh_slots[r["mesh"]] = {"source_slots": parsed["slots"], "actual_slots": [{"name": str(v.material_slot_name), "material": v.material_interface.get_path_name() if v.material_interface else None} for v in mesh.get_editor_property("static_materials")]}
            for i in range(c.get_num_materials()):
                material = c.get_material(i)
                original = unreal.EditorAssetLibrary.get_metadata_tag(material, "BladePhantomOriginalMaterial") if material else ""
                src = plan.get(original or (material.get_path_name() if material else ""))
                if src:
                    for override in material.get_editor_property("texture_parameter_values"):
                        t = override.parameter_value
                        if t:
                            tex_settings[t.get_path_name()] = {"srgb": bool(t.get_editor_property("srgb")), "compression": str(t.get_editor_property("compression_settings")), "parameter": str(override.parameter_info.name)}
        results.append({"label": r["label"], "category": r["category"], "error": e, "source_mesh": r["mesh"], "source_material_overrides": r["overrides"]})
    instance_count = 0
    for r in read(META / "StormPass_FoliageInstances.json")["components"]:
        if r["source_level"] not in PHASES:
            continue
        label = foliage["managed_label"](r)
        a = by_label.get(label)
        c = a.get_component_by_class(unreal.HierarchicalInstancedStaticMeshComponent) if a else None
        if not c or c.get_instance_count() != r["instance_count"]:
            errors.append({"label": label, "problem": "foliage_count"})
            continue
        maximum = {"location_cm": 0., "rotation_degrees": 0., "scale": 0.}
        for i, item in enumerate(r["instances"]):
            e = transform_error(c.get_instance_transform(i, world_space=False), foliage["instance_transform"](item))
            for k, v in e.items():
                maximum[k] = max(maximum[k], v)
        instance_count += c.get_instance_count()
        if maximum["location_cm"] > .02 or maximum["rotation_degrees"] > .01 or maximum["scale"] > .00002:
            errors.append({"label": label, "problem": "foliage_transform", "error": maximum})
        results.append({"label": label, "category": "foliage", "instances": c.get_instance_count(), "error": maximum})
    land = next(v for v in read(META / "StormPass_LandscapeComponents.json")["levels"] if v["source_level"] == PHASES[1])
    for row in land["components"]:
        label = "SP_Landscape_Boss_" + row["component_name"]
        a = by_label.get(label)
        if not a:
            errors.append({"label": label, "problem": "landscape_missing"})
        else:
            t = source_transform(land["root_transform"])
            t.set_editor_property("translation", t.translation + offset)
            expected = t
            e = transform_error(a.get_actor_transform(), expected)
            if e["location_cm"] > .02 or e["rotation_degrees"] > .01 or e["scale"] > .00002:
                errors.append({"label": label, "problem": "landscape_transform", "error": e})
            results.append({"label": label, "category": "landscape", "source": row["source_object_index"], "error": e})
    result = write(name, {"tolerances": {"location_cm": .02, "rotation_degrees": .01, "scale": .00002, "purpose": "float/quat comparison only"}, "categories": dict(collections.Counter(r["category"] for r in results)), "foliage_instances": instance_count, "failures": errors, "actors": results, "mesh_slots": mesh_slots, "texture_settings": tex_settings})
    print(json.dumps({"categories": result["categories"], "foliage_instances": instance_count, "failures": errors[:20], "failure_count": len(errors)}))
    return result


def prepare_policy():
    path = REPORT / "PolishPolicy.json"
    if path.exists():
        return read(path)
    return write("PolishPolicy", {
        "scope": "Environment/editor review only; no boss gameplay, teleport, PlayerStart or Character changes.",
        "source": "StormPass_EnvironmentProfile.json -> profiles.boss_phase_1 / boss_phase_2; original JSON hashes retained there.",
        "temporary_native_adapter": {
            "phase1_exposure_bias_ev": 2.25,
            "reason": "2026-10-01 reference review supersedes the overbright 3 EV adapter. Native light units, film-pass and fog quality differ from the source renderer; these are explicitly temporary visual corrections, not original photometric values.",
            "phase1_light_review": {
                "status": "Temporary native tuning; source photometric unit conversion and custom film shader are unverified.",
                "root_source_intensity_scale": .05,
                "added_source_intensity_scale": .08,
                "added_unspecified_intensity": 2.,
                "added_light_falloff_exponent": 1.,
                "added_light_color_source": "profiles.boss_phase_1.components.sky_light.properties.LightColor; native warm fill palette, not original torch color",
                "sky_source_intensity_scale": .48,
                "post_process_scalars": {"bloom_intensity": .5},
                "post_process_vectors": {"color_gain_shadows": [1., 1., 1., 1.], "color_gain_highlights": [1., 1., 1., 1.],
                                         "color_saturation_midtones": [1., 1., 1., 1.], "color_saturation_highlights": [1., 1., 1., 1.],
                                         "color_saturation_shadows": [1., 1., 1., 1.]},
                "scene_color_tint_linear_rgba": [1., .65, .75, 1.],
                "enable_volumetric_fog_for_editor_review": True,
                "render_setting_boundary": "r.VolumetricFog is enabled for this editor session; no project/scalability INI is changed."
            },
            "fog_density_scale": .01,
            "fog_height_falloff_scale": .1,
            "fog_scale_status": "Retained earlier native adapter coefficients; source-renderer unit conversion is unverified, not an original measurement.",
            "review_camera_lift_cm": 300.,
            "review_camera_fov_degrees": 80.,
            "camera_status": "Editor review viewpoint only, not a gameplay camera/spawn tuning value."
        },
        "original_direct_values": {"phase1_surface": {"GlobalMetallic": .5, "GlobalRoughness": .5, "GlobalSpecular": .25},
                                   "phase2_surface": {"GlobalMetallic": .4, "GlobalRoughness": .4, "GlobalSpecular": .2}},
        "remaining_boundary": "Source-only rendering features (covering, BBQ shading, wind, film-pass) remain approximations; no source shader bytecode is available."
    })


def prepare_sky_assets():
    """Use the actual WEP-assigned DeepGray/DeepNight and zero-cloud presets."""
    source_root = ROOT / "Saved/Extracted/StormPass/BladePhantom_20261001"
    presets = {}
    for p in read(REPORT / "OriginalSkyRequests.json"):
        path = source_root / (p + ".json")
        row = next(v for v in read(path) if v["Type"] == "MaterialInstanceConstant")
        props = row["Properties"]
        presets[p.rsplit("/", 1)[1]] = {"source_package": p, "source_sha256": sha(path), "source_json": str(path.relative_to(ROOT)),
                                      "parent": props["Parent"], "scalars": {v["ParameterInfo"]["Name"]: v["ParameterValue"] for v in props.get("ScalarParameterValues", [])},
                                      "vectors": {v["ParameterInfo"]["Name"]: v["ParameterValue"] for v in props.get("VectorParameterValues", [])},
                                      "cached_textures": props.get("CachedReferencedTextures", [])}
        destination = REPORT / "OriginalSkyMetadata" / (p.rsplit("/", 1)[1] + ".json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    sky = next(a for a in actors() if a.get_actor_label() == "SP_Environment_SkyMesh")
    base = sky.get_component_by_class(unreal.StaticMeshComponent).get_material(0)
    # Always duplicate the retained outside preset, even when a phase is open.
    base = unreal.load_asset("/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/MaterialInstances/MI_SP_Sky_GloomyDay_V2")
    result = {}
    mel = unreal.MaterialEditingLibrary
    for key, preset in (("boss_phase_1", "SkyColor_DeepGray"), ("boss_phase_2", "SkyColor_DeepNight")):
        path = POLISH_ROOT + "/Sky/MI_SP_BP_" + preset
        m = unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset(base.get_path_name(), path)
        if not m:
            raise RuntimeError("Sky duplication failed")
        unsupported = []
        scalar_names = {str(n) for n in mel.get_scalar_parameter_names(m)}
        vector_names = {str(n) for n in mel.get_vector_parameter_names(m)}
        for n, v in presets[preset]["scalars"].items():
            if n not in scalar_names:
                unsupported.append(n)
                continue
            mel.set_material_instance_scalar_parameter_value(m, n, float(v))
        for n, v in presets[preset]["vectors"].items():
            if n not in vector_names:
                unsupported.append(n)
                continue
            mel.set_material_instance_vector_parameter_value(m, n, unreal.LinearColor(*(v[k] for k in "RGBA")))
        mel.update_material_instance(m)
        unreal.EditorAssetLibrary.set_metadata_tag(m, "BladePhantomSourceSky", presets[preset]["source_package"])
        if not unreal.EditorAssetLibrary.save_loaded_asset(m, only_if_is_dirty=False):
            raise RuntimeError("Sky save failed")
        result[key] = {"asset": m.get_path_name(), "preset": preset, "unsupported_parameters": unsupported}
    write("SkyPresets", {"source_presets": presets, "assets": result})
    print(json.dumps({"sky_assets": result, "source_zero_cloud_intensity": [presets[n]["scalars"]["CloudIntensity"] for n in ("CCM_BaseZeroCloud_Layer1", "CCM_BaseZeroCloud_Layer2")]}))
    return result


def phase_surface_batch(offset=0, limit=40):
    all_actors = actors()
    plan = {r["asset"].replace("/_Art/Kazan/", "/_Art/Player/"): r for r in read(META / "StormPass_InheritedSurfaceControls_20260907.json")["materials"]}
    profile = read(META / "StormPass_EnvironmentProfile.json")["profiles"]
    occurrences = collections.defaultdict(list)
    for a in all_actors:
        ph = phase(a.get_actor_label())
        if not ph:
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                m = c.get_material(i)
                if not m:
                    continue
                original = unreal.EditorAssetLibrary.get_metadata_tag(m, "BladePhantomOriginalMaterial") or m.get_path_name()
                if original in plan:
                    occurrences[(ph, original)].append((c, i))
    keys = sorted(occurrences)
    path = REPORT / "SurfaceAssignments.json"
    result = read(path) if path.exists() else {"materials": {}, "total": len(keys)}
    mel = unreal.MaterialEditingLibrary
    for ph, original in keys[offset:offset + limit]:
        source = plan[original]
        name = original.rsplit("/", 1)[1].split(".")[0]
        destination = POLISH_ROOT + "/Phase%d/Materials/" % ph + name + "_" + hashlib.sha256(original.encode()).hexdigest()[:8]
        m = unreal.load_asset(destination) or unreal.EditorAssetLibrary.duplicate_asset(original, destination)
        if not m:
            raise RuntimeError("Surface duplication failed: " + original)
        globals_ = {v["ParameterName"]: v["ScalarValue"] for v in profile["boss_phase_%d" % ph]["components"]["environment_material"]["properties"]["ScalarValues"]}
        values = dict(source["controls"], **{n: globals_[n] for n in ("GlobalMetallic", "GlobalRoughness", "GlobalSpecular")})
        for n, v in values.items():
            if "SP_" + n not in {str(x) for x in mel.get_scalar_parameter_names(m)}:
                raise RuntimeError("Missing native scalar: " + n)
            mel.set_material_instance_scalar_parameter_value(m, "SP_" + n, float(v))
        mel.update_material_instance(m)
        for n, v in values.items():
            if abs(mel.get_material_instance_scalar_parameter_value(m, "SP_" + n) - v) > .00001:
                raise RuntimeError("Scalar readback failed: " + n)
        unreal.EditorAssetLibrary.set_metadata_tag(m, "BladePhantomOriginalMaterial", original)
        unreal.EditorAssetLibrary.set_metadata_tag(m, "BladePhantomSourceMaterial", source["source_package"])
        if not unreal.EditorAssetLibrary.save_loaded_asset(m, only_if_is_dirty=False):
            raise RuntimeError("Surface save failed: " + destination)
        for c, i in occurrences[(ph, original)]:
            c.set_material(i, m)
        result["materials"][m.get_path_name()] = {"phase": ph, "original": original, "source_package": source["source_package"], "controls": values, "assigned_component_slots": len(occurrences[(ph, original)])}
    write("SurfaceAssignments", result)
    print(json.dumps({"offset": offset, "total": len(keys), "completed": len(result["materials"])}))
    return result


def apply_phase_environment(variant):
    """Apply a review variant's sun, sky, background and local fog together."""
    policy = prepare_policy()
    metadata = read(META / "StormPass_EnvironmentProfile.json")
    key = variant if variant in ("boss_phase_1", "boss_phase_2") else "outside"
    profile = metadata["profiles"][key]
    by_label = {a.get_actor_label(): a for a in actors()}
    bridge = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_environment_profile.py"))
    sun = by_label["SP_Environment_DirectionalLight"]
    sky = by_label["SP_Environment_SkyLight"]
    d, s = [profile["components"][n]["properties"] for n in ("directional_light", "sky_light")]
    r = d["RelativeRotation"]
    sun.set_actor_rotation(unreal.Rotator(pitch=r["Pitch"], yaw=r["Yaw"], roll=r["Roll"]), False)
    dc, sc = sun.get_component_by_class(unreal.DirectionalLightComponent), sky.get_component_by_class(unreal.SkyLightComponent)
    for n, v in (("light_color", bridge["fcolor"](d["LightColor"])), ("specular_scale", d.get("SpecularScale", .01)), ("bloom_scale", d.get("BloomScale", .05)), ("occlusion_mask_darkness", d.get("OcclusionMaskDarkness", .9))):
        dc.set_editor_property(n, v)
    sc.set_editor_property("intensity", s["Intensity"])
    sc.set_editor_property("light_color", bridge["fcolor"](s["LightColor"]))
    sc.set_editor_property("lower_hemisphere_color", bridge["linear_color"](s["LowerHemisphereColor"]))
    sky_component = by_label["SP_Environment_SkyMesh"].get_component_by_class(unreal.StaticMeshComponent)
    if key == "outside":
        sky_material = unreal.load_asset("/Game/_Art/Player/Environment/StormPass/Reconstructed/EnvironmentAssets/MaterialInstances/MI_SP_Sky_GloomyDay_V2")
    else:
        sky_material = unreal.load_asset(read(REPORT / "SkyPresets.json")["assets"][key]["asset"])
    if not sky_material:
        raise RuntimeError("Prepared sky preset missing")
    sky_component.set_material(0, sky_material)
    for i in (0, 1):
        a = by_label["SP_Environment_Cloud_%d" % i]
        a.set_actor_hidden_in_game(key != "outside")
        a.get_component_by_class(unreal.StaticMeshComponent).set_visibility(key == "outside", False)
    sc.recapture_sky()
    # This source BossClear WEP lives in StormPass_Light and therefore was not
    # included by the previous name-only phase visibility helper.
    by_label["SP_Environment_PP_StormPass_Light_298"].set_editor_property("enabled", variant == "boss_phase_clear")
    if key == "boss_phase_1":
        pp = by_label["SP_Environment_PP_StormPass_Boss_Phase_1_117"]
        settings = pp.get_editor_property("settings")
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", policy["temporary_native_adapter"]["phase1_exposure_bias_ev"])
        review = policy["temporary_native_adapter"].get("phase1_light_review")
        if review:
            # The source custom film pass is unported. Keep adapter values in
            # the policy and retain source saturation / FilmSlope separately.
            source_settings = profile["default_properties"]["Settings"]
            for field, value in review["post_process_scalars"].items():
                settings.set_editor_property("override_" + field, True)
                settings.set_editor_property(field, value)
            for field, value in review["post_process_vectors"].items():
                settings.set_editor_property("override_" + field, True)
                settings.set_editor_property(field, unreal.Vector4(*value))
            saturation = source_settings["ColorSaturation"]
            settings.set_editor_property("override_color_saturation", True)
            settings.set_editor_property("color_saturation", unreal.Vector4(*(saturation[k] for k in "XYZW")))
            settings.set_editor_property("override_film_slope", source_settings["bOverride_FilmSlope"])
            settings.set_editor_property("film_slope", source_settings["FilmSlope"])
            settings.set_editor_property("override_scene_color_tint", True)
            settings.set_editor_property("scene_color_tint", unreal.LinearColor(*review["scene_color_tint_linear_rgba"]))
            sc.set_editor_property("intensity", s["Intensity"] * review["sky_source_intensity_scale"])
            # xx light defaults/units are not serialized. Use a documented
            # unitless native adapter instead of treating source values as cd.
            for row in read(META / "StormPass_SourceLights.json")["lights"]:
                if row["source_level"] != PHASES[0]:
                    continue
                label = "SP_SourceLight_{}_{:d}_{}".format(row["source_level"], row["source_object_index"], row["actor_name"])
                component = by_label[label].get_component_by_class(unreal.PointLightComponent)
                raw = next(c["properties"] for c in row["components"] if c["type"] == "xxPointLightComponent")
                component.set_use_inverse_squared_falloff(False)
                component.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
                component.set_editor_property("light_falloff_exponent", raw["LightFalloffExponent"])
                component.set_intensity(raw["Intensity"] * review["root_source_intensity_scale"])
            for row in read(REPORT / "MissingRenderPlan.json")["components"]:
                if row["source_level"] != PHASES[0] or row["component_type"] != "xxPointLightComponent":
                    continue
                raw_intensity = row["inherited"]["Intensity"]["value"]
                if raw_intensity == 0:
                    continue  # Source placeholder, not an omitted light.
                label = "SP_BossExtra_{}_{:05d}_{:05d}".format(row["source_level"], row["actor_object_index"], row["component_object_index"])
                component = by_label[label].get_component_by_class(unreal.PointLightComponent)
                component.set_use_inverse_squared_falloff(False)
                component.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
                component.set_editor_property("light_falloff_exponent", review["added_light_falloff_exponent"])
                component.set_intensity(raw_intensity * review["added_source_intensity_scale"] if raw_intensity is not None else review["added_unspecified_intensity"])
                component.set_editor_property("light_color", bridge["fcolor"](s["LightColor"]))
            if review["enable_volumetric_fog_for_editor_review"]:
                world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
                unreal.SystemLibrary.execute_console_command(world, "r.VolumetricFog 1")
        pp.set_editor_property("settings", settings)
    fog = profile["components"]["fog"]["properties"]
    actor = by_label["SP_Environment_HeightFog"]
    if key == "outside":
        location = read(REPORT / "GlobalEnvironmentBefore.json")["fog_pose"]["location_cm"]
    else:
        anchor = next(r for r in read(REPORT / "OriginalAnchors.json")["actors"] if r["name"] == "Mission02_Start_BossZone")["location_cm"]
        location = [anchor[i] + fog["CameraFollowOffset"].get(k, 0) for i, k in enumerate("XYZ")]
    actor.set_actor_location(unreal.Vector(*location), False, False)
    fc = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    density = policy["temporary_native_adapter"]["fog_density_scale"]
    falloff = policy["temporary_native_adapter"]["fog_height_falloff_scale"]
    pairs = [("fog_density", fog["FogDensity"] * density), ("fog_height_falloff", fog["FogHeightFalloff"] * falloff), ("fog_max_opacity", fog.get("FogMaxOpacity", 1)),
             ("fog_inscattering_luminance", bridge["linear_color"](fog["FogInscatteringColor"])), ("enable_volumetric_fog", True),
             ("volumetric_fog_albedo", bridge["fcolor"](fog["VolumetricFogAlbedo"])), ("volumetric_fog_emissive", bridge["linear_color"](fog["VolumetricFogEmissive"])),
             ("volumetric_fog_distance", fog["VolumetricFogDistance"]), ("volumetric_fog_extinction_scale", fog["VolumetricFogExtinctionScale"])]
    if "DirectionalInscatteringColor" in fog:
        pairs.append(("directional_inscattering_luminance", bridge["linear_color"](fog["DirectionalInscatteringColor"])))
    else:
        # Avoid leaking Phase1's direction tint into the phase with no override.
        pairs.append(("directional_inscattering_luminance", unreal.LinearColor(0, 0, 0, 1)))
    for n, v in pairs:
        fc.set_editor_property(n, v)
    second = fog.get("SecondFogData", {})
    fc.set_second_fog_density(second.get("FogDensity", 0) * density)
    fc.set_second_fog_height_falloff(second.get("FogHeightFalloff", 0) * falloff)
    result = {"active_variant": variant, "profile": key, "source_json": profile["source_json"], "source_sha256": profile["source_sha256"],
              "sun_rotation_source_degrees": r, "sky_intensity_source": s["Intensity"], "sky_intensity_native": sc.get_editor_property("intensity"), "sky_material": sky_material.get_path_name(), "clouds_visible": key == "outside",
              "fog_location_cm": location, "fog_native_density": fog["FogDensity"] * density, "fog_native_falloff": fog["FogHeightFalloff"] * falloff,
              "fog_location_boundary": "Static editor proxy at source spawn + camera-follow offset; not a runtime camera-follow implementation."}
    write("ActiveEnvironment", result)
    return result


def mark_arenas():
    layout = side_layout()
    if layout and layout.get("enabled"):
        # Source markers already exist; do not recreate their old shared pose.
        return layout["markers"]
    data = read(REPORT / "OriginalAnchors.json")["actors"]
    sources = {r["name"]: r for r in data}
    definitions = [("Phase1", "ArenaReference", "TargetPoint_Boss"),
                   ("Phase1", "PlayerEntry", "Mission02_Start_BossZone"),
                   ("Phase2", "ArenaReference", "TargetPoint_Boss"),
                   ("Phase2", "BossSpawn", "SA_BladePhantom"),
                   ("CinemaReference", "BossStart", "C_M_BladePhantom_5")]
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in actors()}
    records = []
    for group, purpose, name in definitions:
        row = sources[name]
        label = "SP_BP_{}_{}_{}".format(group, purpose, name)
        a = by_label.get(label) or subsystem.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*row["location_cm"]))
        a.set_actor_label(label)
        a.set_actor_location(unreal.Vector(*row["location_cm"]), False, False)
        r = row["rotation_degrees"]
        a.set_actor_rotation(unreal.Rotator(pitch=r[0], yaw=r[1], roll=r[2]), False)
        a.set_editor_property("is_editor_only_actor", True)
        a.set_folder_path("StormPass/01_BladePhantom/" + group + "/SourceMarkers")
        a.set_editor_property("tags", ["BladePhantomArenaReference", group, "Source_" + row["source_json"].removesuffix(".json")])
        records.append({"label": label, "group": group, "purpose": purpose, "source_actor": name, "source_json": row["source_json"], "source_object_index": row["index"], **pose(a)})
    policy = prepare_policy()["temporary_native_adapter"]
    entry = sources["Mission02_Start_BossZone"]
    for group in ("Phase1", "Phase2"):
        label = "SP_BP_" + group + "_ReviewCamera"
        location = list(entry["location_cm"])
        location[2] += policy["review_camera_lift_cm"]
        a = by_label.get(label) or subsystem.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*location))
        a.set_actor_label(label)
        a.set_actor_location(unreal.Vector(*location), False, False)
        r = entry["rotation_degrees"]
        a.set_actor_rotation(unreal.Rotator(pitch=r[0], yaw=r[1], roll=r[2]), False)
        a.set_editor_property("is_editor_only_actor", True)
        a.set_folder_path("StormPass/01_BladePhantom/" + group + "/ReviewCameras")
        a.get_component_by_class(unreal.CameraComponent).set_editor_property("field_of_view", policy["review_camera_fov_degrees"])
        records.append({"label": label, "group": group, "purpose": "review_camera", "source_anchor": entry["name"], "temporary_viewpoint": True, **pose(a)})
    for a in actors():
        ph = phase(a.get_actor_label())
        if ph:
            prefix = "SP_" + a.get_actor_label().split("_", 2)[1]
            a.set_folder_path("StormPass/01_BladePhantom/Phase%d/" % ph + prefix)
    payload = {"map": MAP, "editor_only": True, "phase1": "Source StormPass_Boss_Phase_1: castle hall", "phase2": "Source StormPass_Boss_Phase_2: forest/landscape alternate arena",
               "coordinate_boundary": "The two source variants occupy the same coordinate neighbourhood. Their distinct environments are selected by review variant; a distant PP volume centroid is not a phase2 teleport/spawn.",
               "source_phase2_spawn_dependency": sources["SA_BladePhantom"]["properties"].get("DependentLevelPath"),
               "markers": records, "gameplay_implementation": False}
    write("ArenaMarkers", payload)
    print(json.dumps({"editor_only_markers_and_cameras": len(records)}))
    return payload


def audit_materials(name="MaterialsAfter"):
    by_label = {a.get_actor_label(): a for a in actors()}
    plan = {r["asset"].replace("/_Art/Kazan/", "/_Art/Player/"): r for r in read(META / "StormPass_InheritedSurfaceControls_20260907.json")["materials"]}
    profiles = read(META / "StormPass_EnvironmentProfile.json")["profiles"]
    library = runpy.run_path(str(ROOT / "Scripts/HeinMach/audit_heinmach_material_rendering.py"))
    library["material_record"].__globals__["PROJECT_ASSET_PREFIX"] = "/Game/_Art/Player/Environment/StormPass/"
    assignments = read(REPORT / "SurfaceAssignments.json")
    mel = unreal.MaterialEditingLibrary
    usage, failures = collections.defaultdict(list), []
    for a in by_label.values():
        if not phase(a.get_actor_label()):
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                m = c.get_material(i)
                if not m:
                    failures.append({"actor": a.get_actor_label(), "slot": i, "problem": "null"})
                else:
                    usage[m.get_path_name()].append((a, c, i))
    records = []
    for path, uses in sorted(usage.items()):
        m = uses[0][1].get_material(uses[0][2])
        record = library["material_record"](path, m, len(uses), [a.get_actor_label() for a, _, _ in uses[:3]])
        parent = m.get_editor_property("parent") if isinstance(m, unreal.MaterialInstanceConstant) else None
        if parent and parent.get_name() == "M_SP_SourceTreeFoliage_V2":
            # The generic USD audit reads obsolete component-selector vectors.
            # This native tree parent directly samples G for roughness and R
            # for AO; its metallic output is a separate zero-valued parameter.
            rn = mel.get_material_property_input_node(parent, unreal.MaterialProperty.MP_ROUGHNESS)
            inputs = mel.get_inputs_for_material_expression(parent, rn)
            rough_ok = any(isinstance(n, unreal.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property("parameter_name")) == "RoughnessTexture" and mel.get_input_node_output_name_for_material_expression(rn, n) == "G" for n in inputs)
            ao = mel.get_material_property_input_node(parent, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
            ao_ok = isinstance(ao, unreal.MaterialExpressionTextureSampleParameter2D) and mel.get_material_property_input_node_output_name(parent, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION) == "R"
            mn = mel.get_material_property_input_node(parent, unreal.MaterialProperty.MP_METALLIC)
            metal_ok = isinstance(mn, unreal.MaterialExpressionScalarParameter) and mel.get_material_instance_scalar_parameter_value(m, str(mn.get_editor_property("parameter_name"))) == 0
            record["native_tree_graph_audit"] = {"roughness_G":rough_ok, "AO_R":ao_ok, "nonmetallic":metal_ok,"legacy_selector_vectors_unused":True}
            if rough_ok and ao_ok and metal_ok:
                record["classification"]["packed_channel_mapping_correct"] = True
                record["classification"]["needs_channel_repair"] = False
        if record["classification"]["needs_channel_repair"]:
            failures.append({"material": path, "problem": "packed_channels"})
        original = unreal.EditorAssetLibrary.get_metadata_tag(m, "BladePhantomOriginalMaterial")
        source = plan.get(original or path)
        if source:
            ph = phase(uses[0][0].get_actor_label())
            g = {v["ParameterName"]: v["ScalarValue"] for v in profiles["boss_phase_%d" % ph]["components"]["environment_material"]["properties"]["ScalarValues"]}
            expected = dict(source["controls"], **{n: g[n] for n in ("GlobalMetallic", "GlobalRoughness", "GlobalSpecular")})
            for n, v in expected.items():
                actual = mel.get_material_instance_scalar_parameter_value(m, "SP_" + n)
                if abs(actual - v) > .00001:
                    failures.append({"material": path, "parameter": "SP_" + n, "expected": v, "actual": actual})
            if not original or path not in assignments["materials"]:
                failures.append({"material": path, "problem": "phase_assignment_missing"})
        records.append(record)
    result = write(name, {"unique_materials": len(records), "phase_surface_instances": len(assignments["materials"]), "failures": failures, "materials": records})
    print(json.dumps({"materials": len(records), "phase_instances": len(assignments["materials"]), "failures": failures[:12], "failure_count": len(failures)}))
    return result


def capture_review(filename, location=None, rotation=None):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = next((a for a in actors() if a.get_actor_label() == "SP_TemporaryArenaCapture"), None)
    if not a:
        a = subsystem.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
        a.set_actor_label("SP_TemporaryArenaCapture")
        a.set_editor_property("is_editor_only_actor", True)
    if location:
        a.set_actor_location(unreal.Vector(*location), False, False)
    if rotation:
        a.set_actor_rotation(unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), False)
    c = a.get_component_by_class(unreal.SceneCaptureComponent2D)
    if not c.get_editor_property("texture_target"):
        c.set_editor_property("texture_target", unreal.RenderingLibrary.create_render_target2d(a, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8))
    c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property("capture_every_frame", False)
    c.set_editor_property("capture_on_movement", False)
    c.set_editor_property("always_persist_rendering_state", True)
    c.set_editor_property("fov_angle", prepare_policy()["temporary_native_adapter"]["review_camera_fov_degrees"])
    variant = read(META / "StormPass_CurrentReviewVariant.json")["active_variant"]
    label = "SP_Environment_PP_StormPass_Boss_Phase_" + ("1_117" if variant == "boss_phase_1" else "2_244")
    pp = next(a for a in actors() if a.get_actor_label() == label)
    settings = pp.get_editor_property("settings")
    settings.set_editor_property("override_dynamic_global_illumination_method", True)
    settings.set_editor_property("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN)
    settings.set_editor_property("override_reflection_method", True)
    settings.set_editor_property("reflection_method", unreal.ReflectionMethod.LUMEN)
    c.set_editor_property("post_process_settings", settings)
    c.capture_scene()
    path = ROOT / "Saved/ArtReviews/BladePhantom_20261001"
    path.mkdir(parents=True, exist_ok=True)
    unreal.RenderingLibrary.export_render_target(a, c.get_editor_property("texture_target"), str(path), filename)
    print(str(path / filename))


def save_polish():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actors():
        if a.get_actor_label() == "SP_TemporaryArenaCapture":
            subsystem.destroy_actor(a)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
        raise RuntimeError("StormPass save failed")
    print("StormPass arena map saved; temporary capture removed")


def separate_arenas():
    """Move the existing Phase2 scene once; preserve each native local pose."""
    layout = side_layout()
    if layout and layout.get("enabled"):
        return show_side_by_side()
    before = read(SIDE_REPORT / "ActorsBefore.json")
    bounds = read(SIDE_REPORT / "ForegroundBoundsBefore.json")["bounds"]
    by = {a.get_actor_label(): a for a in actors()}
    p1 = by["SP_Environment_PP_StormPass_Boss_Phase_1_117"]
    p2 = by["SP_Environment_PP_StormPass_Boss_Phase_2_244"]
    origin, extent = p1.get_actor_bounds(False)
    # Temporary authoring clearance, not an original arena separation value.
    clearance_cm = 2000.
    dx = max(bounds["1"]["max"][0], origin.x + extent.x) + clearance_cm - bounds["2"]["min"][0]
    shift = [dx, 0., 0.]
    destination = POLISH_ROOT + "/Landscape/M_SP_BP_Phase2Landscape_Separated"
    if unreal.EditorAssetLibrary.does_asset_exist(destination) or "SP_BP_Phase2_Sun" in by:
        raise RuntimeError("Unexpected prior layout asset/actor; inspect the preflight backup before rebuilding")
    targets = [r for r in before["actors"] if r["phase"] == 2 or r["label"].startswith("SP_BP_Phase2_")]
    for row in targets:
        a = by[row["label"]]
        if a.get_attach_parent_actor() or pose(a) != row["pose"]:
            raise RuntimeError("Actor changed or attached since preflight: " + row["label"])
    moved = []
    for row in targets:
        label = row["label"]
        if row["phase"] != 2 and not label.startswith("SP_BP_Phase2_"):
            continue
        a = by[label]
        if a.get_attach_parent_actor():
            raise RuntimeError("Unexpected actor attachment: " + label)
        # Immutable pre-task poses prevent accumulating a second offset.
        if pose(a) != row["pose"]:
            raise RuntimeError("Actor changed since preflight: " + label)
        location = [row["pose"]["location_cm"][i] + shift[i] for i in range(3)]
        a.set_actor_location(unreal.Vector(*location), False, False)
        if max(abs(vec(a.get_actor_location())[i] - location[i]) for i in range(3)) > .002:
            raise RuntimeError("Actor move failed: " + label)
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            c.set_lighting_channels(False, True, False)
        for c in a.get_components_by_class(unreal.LightComponent):
            c.set_lighting_channels(False, True, False)
        moved.append(label)
    # Reuse the existing box brush and settings. Bound only the forest scene,
    # excluding distant non-colliding background mountains and editor icons.
    old_origin, old_extent = p2.get_actor_bounds(False)
    old_scale = p2.get_actor_scale3d()
    lo = [bounds["2"]["min"][i] + shift[i] for i in range(3)]
    hi = [bounds["2"]["max"][i] + shift[i] for i in range(3)]
    center = [(lo[i] + hi[i]) / 2 for i in range(3)]
    half = [(hi[i] - lo[i]) / 2 for i in range(3)]
    p2.set_actor_location(unreal.Vector(*center), False, False)
    p2.set_actor_scale3d(unreal.Vector(*(getattr(old_scale, k) * half[i] / getattr(old_extent, k) for i, k in enumerate("xyz"))))

    # The retained landscape uses (WorldXY - original RootXY)/RootScale.
    # Duplicate this single native parent, changing only the RootXY constant.
    source = "/Game/_Art/Player/Environment/StormPass/Reconstructed/Landscape/Materials/M_SP_Landscape_Boss"
    material = unreal.EditorAssetLibrary.duplicate_asset(source, destination)
    if not material:
        raise RuntimeError("Landscape material duplication failed")
    nodes = []
    mel = unreal.MaterialEditingLibrary
    def visit(node):
        if not node or node in nodes:
            return
        nodes.append(node)
        for child in mel.get_inputs_for_material_expression(material, node):
            if child:
                visit(child)
    for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_NORMAL, unreal.MaterialProperty.MP_ROUGHNESS):
        visit(mel.get_material_property_input_node(material, prop))
    land = next(r for r in read(META / "StormPass_LandscapeComponents.json")["levels"] if r["source_level"] == PHASES[1])
    raw = land["root_transform"]["location_cm"]
    anchors = [n for n in nodes if isinstance(n, unreal.MaterialExpressionConstant2Vector)
               and n.get_editor_property("r") == raw["x"] and n.get_editor_property("g") == raw["y"]]
    if len(anchors) != 1:
        raise RuntimeError("Expected one landscape world-origin constant")
    anchors[0].set_editor_property("r", raw["x"] + dx)
    mel.recompile_material(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, "BladePhantomSourceWorldOffsetCm", json.dumps(shift))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("Separated landscape material save failed")
    for label, a in by.items():
        if label.startswith("SP_Landscape_Boss_"):
            a.get_component_by_class(unreal.StaticMeshComponent).set_material(0, material)

    # Direct sunlight can be separated with native lighting channels. Sky and
    # height fog remain shared world features; there is no runtime region code.
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sun = subsystem.duplicate_actor(by["SP_Environment_DirectionalLight"],
                                    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), unreal.Vector(*shift))
    if not sun:
        raise RuntimeError("Phase2 sun duplication failed")
    sun.set_actor_label("SP_BP_Phase2_Sun")
    sun.set_folder_path("StormPass/01_BladePhantom/Phase2/Lighting")
    profile = read(META / "StormPass_EnvironmentProfile.json")["profiles"]["boss_phase_2"]
    d = profile["components"]["directional_light"]["properties"]
    rot = d["RelativeRotation"]
    sun.set_actor_rotation(unreal.Rotator(pitch=rot["Pitch"], yaw=rot["Yaw"], roll=rot["Roll"]), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("light_color", unreal.Color(r=d["LightColor"]["R"], g=d["LightColor"]["G"], b=d["LightColor"]["B"], a=d["LightColor"]["A"]))
    c.set_editor_property("specular_scale", d["SpecularScale"])
    c.set_lighting_channels(False, True, False)
    # Screen-space shaft bloom is global, so do not add a second shaft pass.
    c.set_editor_property("enable_light_shaft_bloom", False)
    c.set_editor_property("enable_light_shaft_occlusion", False)
    primary = ["SP_BP_Phase1_ArenaReference_TargetPoint_Boss", "SP_BP_Phase2_ArenaReference_TargetPoint_Boss"]
    for label in primary:
        by[label].set_folder_path("StormPass/01_BladePhantom/ArenaMarkers")
    layout = {"enabled": True, "map": MAP, "source_phase2_translation_cm": shift,
              "clearance_cm": clearance_cm, "clearance_status": "Temporary authoring clearance chosen by assistant; not an original gameplay/phase separation value.",
              "calculation": "dx = max(Phase1 foreground maxX, Phase1 PP maxX) + clearance - Phase2 foreground minX; no rotation/scale change.",
              "foreground_bounds_before": bounds, "moved_labels": moved,
              "phase2_pp_pose": pose(p2), "phase2_pp_bounds": {"min": lo, "max": hi},
              "landscape_material": material.get_path_name(), "source_landscape_material": source,
              "source_landscape_root_xy_cm": [raw["x"], raw["y"]], "native_landscape_root_xy_cm": [raw["x"] + dx, raw["y"]],
              "phase2_sun": {"label": sun.get_actor_label(), "source_json": profile["source_json"], "source_sha256": profile["source_sha256"],
                             "native_intensity_lux": c.get_editor_property("intensity"), "intensity_status": "Retained native sun intensity, not an original serialized Intensity.", "channel": 1},
              "markers": [{"label": label, "phase": i + 1, "editor_only": True, **pose(by[label])} for i, label in enumerate(primary)],
              "environment_boundary": "Bounded PP, source local lights, and channel-separated direct sun; sky/height fog/indirect GI are shared. Existing Pawn lighting channels are not changed.",
              "actor_count_before": before["actor_count"], "actor_count_after": len(actors())}
    SIDE_REPORT.mkdir(parents=True, exist_ok=True)
    (SIDE_REPORT / "Layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return show_side_by_side()


def show_side_by_side(focus="boss_phase_1", save=False):
    """Keep both physical arenas active; old phase commands now select views."""
    layout = side_layout()
    if not layout or not layout.get("enabled"):
        raise RuntimeError("Separate the arenas before showing this layout")
    helper = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_route_presentation.py"))
    baseline = helper["capture_phase_baseline"]()
    by = {a.get_actor_label(): a for a in actors()}
    layers = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    groups = {v: [] for v in helper["VARIANTS"]}
    for row in baseline["actors"]:
        a = by[row["label"]]
        active = row["variant"] in ("boss_phase_1", "boss_phase_2")
        groups[row["variant"]].append(a)
        a.set_actor_hidden_in_game(row["hidden_in_game"] if active else True)
        a.set_is_temporarily_hidden_in_editor(False)
        if row["post_process_enabled"] is not None:
            a.set_editor_property("enabled", row["post_process_enabled"] if active else False)
        components = {c.get_name(): c for c in a.get_components_by_class(unreal.SceneComponent)}
        for saved in row["components"]:
            c = components[saved["name"]]
            c.set_visibility(saved["visible"] if active else False, False)
            if "collision" in saved:
                c.set_collision_enabled(getattr(unreal.CollisionEnabled, saved["collision"]) if active else unreal.CollisionEnabled.NO_COLLISION)
    for value, members in groups.items():
        name = "SP_SourceVariant_" + value
        layers.add_actors_to_layer(members, name)
        layers.set_layer_visibility(name, value in ("boss_phase_1", "boss_phase_2"))
    marker = next(r for r in layout["markers"] if r["phase"] == (2 if focus == "boss_phase_2" else 1))
    camera_label = "SP_BP_Phase%d_ReviewCamera" % marker["phase"]
    camera = by[camera_label]
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([by[marker["label"]]])
    if prepare_policy()["temporary_native_adapter"].get("phase1_light_review", {}).get("enable_volumetric_fog_for_editor_review"):
        unreal.SystemLibrary.execute_console_command(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), "r.VolumetricFog 1")
    result = {"active_variant": focus, "layout_mode": "side_by_side", "both_arenas_visible": True,
              "source_phase2_translation_cm": layout["source_phase2_translation_cm"], "markers": layout["markers"], "deleted_actors": 0}
    (META / "StormPass_CurrentReviewVariant.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if save:
        save_polish()
    print(json.dumps(result))
    return result


def add_arena_collision_floors():
    """Two native support boxes for authoring; original collision is unported."""
    layout = side_layout()
    if not layout or not layout.get("enabled"):
        raise RuntimeError("The separated layout must exist")
    if layout.get("collision_floors"):
        return layout["collision_floors"]  # Never respawn a user-deleted actor.
    by = {a.get_actor_label(): a for a in actors()}
    footprint = read(SIDE_REPORT / "ForegroundBoundsBefore.json")["components"]
    tiles = [r for r in footprint if r["phase"] == 1 and "HISM_WP_Base_Floor_001_500X500_a" in r["label"]]
    center = next(r["location_cm"] for r in layout["markers"] if r["phase"] == 1)
    core_tiles = [r for r in tiles if r["min"][0] <= center[0] <= r["max"][0]
                  and r["min"][1] <= center[1] <= r["max"][1]]
    if len(core_tiles) != 1:
        raise RuntimeError("Expected one native floor tile beneath the Phase1 arena reference")
    core_tile = core_tiles[0]
    top, thickness = core_tile["max"][2], core_tile["max"][2] - core_tile["min"][2]
    if thickness <= 0:
        raise RuntimeError("The native core floor tile has no thickness")
    sources = ((1, "SP_ChildProp_StormPass_Boss_Phase_1_02379_00076"),
               (2, "SP_ChildProp_StormPass_Boss_Phase_2_02538_00179"))
    for ph, source_label in sources:
        label = "SP_BP_Phase%d_CollisionFloor" % ph
        if label in by or source_label not in by:
            raise RuntimeError("Support floor preflight failed: " + label)
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    b = cube.get_bounds()
    cube_size = vec(b.box_extent * 2)
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rows = []
    for ph, source_label in sources:
        label = "SP_BP_Phase%d_CollisionFloor" % ph
        origin, extent = by[source_label].get_actor_bounds(False)
        location = [origin.x, origin.y, top - thickness / 2]
        dimensions = [extent.x * 2, extent.y * 2, thickness]
        a = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*location))
        a.set_actor_label(label)
        a.set_folder_path("StormPass/01_BladePhantom/Collision")
        a.set_actor_scale3d(unreal.Vector(*(dimensions[i] / cube_size[i] for i in range(3))))
        a.set_actor_enable_collision(True)
        a.set_actor_hidden_in_game(True)
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        c.set_static_mesh(cube)
        c.set_collision_profile_name("BlockAll")
        c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        c.set_visibility(False, False)
        c.set_cast_shadow(False)
        rows.append({"label": label, "phase": ph, "source_water_actor": source_label, "pose": pose(a),
                     "dimensions_cm": dimensions, "support_top_z_cm": top, "render_visible": False,
                     "collision": "BlockAll / QueryAndPhysics", "editor_only": False})
    layout["collision_floors"] = rows
    layout["collision_floor_derivation"] = {"source_floor_bounds": tiles, "selected_core_floor_bounds": core_tile,
        "selection": "The single retained floor tile whose XY bounds contain the Phase1 primary arena reference; raised entrance/stair tiles are excluded.",
        "cube_asset": cube.get_path_name(), "cube_dimensions_cm": cube_size,
        "formula": "XY footprint = retained phase water actor world bounds; topZ = native Phase1 floor tile maxZ; thickness = tile maxZ-minZ; centerZ=topZ-thickness/2; scale=dimensions/engine cube dimensions.",
        "status": "Native authoring support approximation. Applying the Phase1 flat floor height to the Phase2 blood-water core is an explicit authoring assumption, not original collision metadata. No original actor collision mode is replaced."}
    layout["actor_count_after"] = len(actors())
    (SIDE_REPORT / "Layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows
