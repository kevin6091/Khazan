"""Final fog bridge and read-only contracts for the two Blade Phantom arenas."""
import collections
from pathlib import Path
import runpy

import unreal

ROOT = Path(__file__).resolve().parents[2]
h = runpy.run_path(str(ROOT / "Scripts/StormPass/polish_blade_phantom_arenas.py"))
x = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_blade_phantom_missing_render.py"))
mel, eal = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary


def finish_fog():
    """Last content-writing stage: preserve the seven original fog planes."""
    profile = h["read"](h["META"] / "StormPass_EnvironmentProfile.json")["profiles"]["boss_phase_2"]
    values = profile["components"]["environment_material"]["properties"]["VectorValues"]
    raw = next(v["VectorValue"] for v in values if v["ParameterName"] == "FogSheetColor")
    color = unreal.LinearColor(raw["R"], raw["G"], raw["B"], raw["A"])
    records, parents = [], {}
    for a in h["actors"]():
        if not a.get_actor_label().startswith("SP_Fog_StormPass_Boss_Phase_2_"):
            continue
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        old = c.get_material(0)
        source_path = eal.get_metadata_tag(old, "BladePhantomOriginalFog") or old.get_path_name()
        original = unreal.load_asset(source_path)
        original_parent = original.get_editor_property("parent")
        parent_path = h["POLISH_ROOT"] + "/Fog/Materials/M_SP_BP_Phase2_FogSheet"
        parent = unreal.load_asset(parent_path)
        if not parent:
            parent = eal.duplicate_asset(original_parent.get_path_name(), parent_path)
        if eal.get_metadata_tag(parent, "BladePhantomFogBridgeReady") != "1":
            tint = x["expr"](parent, unreal.MaterialExpressionVectorParameter, parameter_name="BP_EnvironmentFogSheetColor", default_value=color)
            for prop, channel in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, "RGB"), (unreal.MaterialProperty.MP_OPACITY, "A")):
                node = mel.get_material_property_input_node(parent, prop)
                pin = mel.get_material_property_input_node_output_name(parent, prop)
                if not node:
                    raise RuntimeError("Missing native fog property input")
                multiply = x["expr"](parent, unreal.MaterialExpressionMultiply)
                x["connect"](node, pin, multiply, "A")
                x["connect"](tint, channel, multiply, "B")
                x["output"](parent, multiply, prop)
            mel.recompile_material(parent)
            eal.set_metadata_tag(parent, "BladePhantomFogBridgeReady", "1")
            x["save"](parent)
        path = h["POLISH_ROOT"] + "/Fog/MaterialInstances/MI_SP_BP_" + a.get_actor_label()
        mat = unreal.load_asset(path) or eal.duplicate_asset(original.get_path_name(), path)
        mel.set_material_instance_parent(mat, parent)
        mel.set_material_instance_vector_parameter_value(mat, "BP_EnvironmentFogSheetColor", color)
        mel.update_material_instance(mat)
        eal.set_metadata_tag(mat, "BladePhantomOriginalFog", source_path)
        x["save"](mat)
        c.set_material(0, mat)
        records.append({"actor": a.get_actor_label(), "original_material": source_path, "material": mat.get_path_name(), "parent": parent.get_path_name()})
        parents[parent.get_path_name()] = original_parent.get_path_name()
    if len(records) != 7:
        raise RuntimeError("Expected exactly seven phase2 fog sheets")
    h["write"]("FogBridge", {"source_json": profile["source_json"], "source_sha256": profile["source_sha256"], "source_field": "xxEnvironmentMaterialComponent.VectorValues[ParameterName=FogSheetColor].VectorValue", "source_rgba": raw,
                            "native_graph": "Multiply the retained native sheet emissive by source RGB and opacity by source A. Original MPC/shader graph is unavailable; this explicit native bridge is not a shader-bytecode port.", "actors": records, "parent_sources": parents})
    print("Original phase2 FogSheetColor connected to seven retained sheets")


def audit_slots(name="MaterialSlotsAfter"):
    helper = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_child_render_meshes.py"))
    helper["configure_shared"]()
    by = {a.get_actor_label(): a for a in h["actors"]()}
    rows = h["read"](h["REPORT"] / "GeometryBefore.json")["actors"]
    plan = {r["asset"].replace("/_Art/Kazan/", "/_Art/Player/"): r for r in h["read"](h["META"] / "StormPass_InheritedSurfaceControls_20260907.json")["materials"]}
    water = {r["label"]:r for r in h["read"](h["META"] / "StormPass_NativeWaterMaterials.json")["water_actors"]}
    maps, checks, failures, non_render = {}, [], [], []
    def base(v):
        name = v.split(".")[0].rsplit("/", 1)[-1].lower()
        return name[3:] if name.startswith("mi_") else name
    for row in rows:
        if row["category"] not in ("root", "child"):
            continue
        c = by[row["label"]].get_component_by_class(unreal.StaticMeshComponent)
        mesh = c.get_editor_property("static_mesh")
        package = row["source_mesh"]
        if package not in maps:
            maps[package] = helper["build_slot_mapping"](package, mesh)
        mapping, layout = maps[package]
        defaults = {v["source_slot"]: v["source_material"] for v in layout["assignments"]}
        overrides = row["source_material_overrides"]
        for source_slot, ue_slot in mapping.items():
            expected = overrides[source_slot] if source_slot < len(overrides) and overrides[source_slot] else defaults[source_slot]
            actual = c.get_material(ue_slot)
            path = eal.get_metadata_tag(actual, "BladePhantomOriginalMaterial") or actual.get_path_name()
            source = plan.get(path, {}).get("source_package") or eal.get_metadata_tag(actual, "BladePhantomSourceMaterial") or path
            record = {"actor": row["label"], "source_slot": source_slot, "ue_slot": ue_slot, "source_material": expected, "actual_source": source, "material": actual.get_path_name()}
            if row["label"] in water and expected=="WorldGridMaterial":
                w=water[row["label"]]
                target=w["actor_instance_path"].replace("/_Art/Kazan/", "/_Art/Player/")
                record.update({"source_material":w["source_material_package"],"native_runtime_binding":target,"source_level_json_sha256":w["source_level_json_sha256"],"binding_boundary":"Source WaterBody actor supplies its water MI at runtime; its mesh's WorldGridMaterial is a serialized placeholder."})
                if actual.get_path_name().split(".")[0]!=target:
                    failures.append(record)
                checks.append(record)
                continue
            checks.append(record)
            if base(expected) != base(source):
                failures.append(record)
        for slot, override in enumerate(overrides):
            if override and slot not in mapping:
                non_render.append({"actor": row["label"], "source_slot": slot, "source_material": override})
    result = h["write"](name, {"meshes": len(maps), "render_slots_checked": len(checks), "failures": failures, "non_render_source_override_slots": non_render,
                             "boundary": "Use source USD bindings and texture-based source-slot to UE-slot matching; ordinal slot order is not assumed.", "checks": checks,
                             "slot_mappings": {k: v[1] for k,v in maps.items()}})
    print({"mesh_layouts":len(maps), "render_slots":len(checks), "failure_count":len(failures), "first_failures":failures[:8]})
    return result


def audit_extras(name="MissingRenderAfter"):
    by = {a.get_actor_label(): a for a in h["actors"]()}
    applied = h["read"](h["REPORT"] / "MissingRenderApplied.json")["actors"]
    rows = h["read"](h["REPORT"] / "MissingRenderPlan.json")["components"]
    failures, records = [], []
    skipped = []
    for row in rows:
        label = "SP_BossExtra_{}_{:05d}_{:05d}".format(row["source_level"],row["actor_object_index"],row["component_object_index"])
        typ = row["component_type"]
        if typ=="xxPointLightComponent" and row["inherited"]["Intensity"]["value"]==0:
            skipped.append({"actor":row["actor_name"],"type":typ,"reason":"serialized zero intensity placeholder"})
            continue
        if typ=="xxNiagaraComponent" and "WaterDecal" in row["inherited"]["Asset"]["value"]["ObjectPath"]:
            skipped.append({"actor":row["actor_name"],"type":typ,"reason":"source spline Niagara DI is unported; existing native water retained"})
            continue
        a = by.get(label)
        if not a or label not in applied:
            failures.append({"actor":label,"problem":"missing"})
            continue
        expected = x["component_transform"](row)
        layout = h["side_layout"]()
        if layout and layout.get("enabled") and row["source_level"] == "StormPass_Boss_Phase_2":
            expected.set_editor_property("translation", expected.translation + unreal.Vector(*layout["source_phase2_translation_cm"]))
        error = h["transform_error"](a.get_actor_transform(), expected)
        if error["location_cm"]>.02 or error["rotation_degrees"]>.01 or error["scale"]>.00002:
            failures.append({"actor":label,"problem":"transform","error":error})
        components = a.get_components_by_class(unreal.PrimitiveComponent)
        materials=[]
        for c in components:
            if c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION:
                failures.append({"actor":label,"problem":"extra blocks movement"})
            for slot in range(c.get_num_materials()):
                m=c.get_material(slot);materials.append(m.get_path_name() if m else None)
                if not m or "WorldGridMaterial" in m.get_path_name():
                    failures.append({"actor":label,"problem":"fallback material","slot":slot})
        records.append({"actor":label,"type":typ,"error":error,"materials":materials})
    flag = unreal.load_asset(x["DEST"] + "/Flags/SKM_SP_BP_Flag")
    actual = flag.get_bounds()
    raw = h["read"](h["REPORT"] / "FlagAssets.json")["original_bounds"]
    bound_error = max(abs(getattr(actual.origin,k.lower())-raw["Origin"][k]) for k in "XYZ")
    bound_error = max(bound_error,max(abs(getattr(actual.box_extent,k.lower())-raw["BoxExtent"][k]) for k in "XYZ"))
    if bound_error>.002:
        failures.append({"mesh":flag.get_path_name(),"problem":"source bounds mismatch","error_cm":bound_error})
    result = h["write"](name,{"restored":dict(collections.Counter(r["type"] for r in records)),"actors":records,"source_flag_bounds_max_error_cm":bound_error,"skipped":skipped,"failures":failures})
    print({"restored":result["restored"],"failure_count":len(failures),"first_failures":failures[:8],"flag_bounds_error_cm":bound_error})
    return result


def audit_variant(name="VariantAfter"):
    variant=h["read"](h["META"] / "StormPass_CurrentReviewVariant.json")["active_variant"]
    baseline=h["read"](h["META"] / "StormPass_PhaseVisibilityBaseline_20260907.json")["actors"]
    by={a.get_actor_label():a for a in h["actors"]()}
    failures=[]
    editor_icons=0
    layout = h["side_layout"]()
    separated = bool(layout and layout.get("enabled"))
    for row in baseline:
        a=by.get(row["label"])
        if not a:
            failures.append({"actor":row["label"],"problem":"missing"});continue
        active=row["variant"] in ("boss_phase_1", "boss_phase_2") if separated else row["variant"]==variant
        if bool(a.get_editor_property("hidden")) != (bool(row["hidden_in_game"]) if active else True):
            failures.append({"actor":row["label"],"problem":"hidden flag"})
        components={c.get_name():c for c in a.get_components_by_class(unreal.SceneComponent)}
        for rc in row["components"]:
            c=components.get(rc["name"])
            if not c:
                failures.append({"actor":row["label"],"problem":"component missing"});continue
            if isinstance(c,unreal.BillboardComponent) and c.get_editor_property("is_editor_only"):
                # UE rebuilds editor icon sprites during PostLoad. They are
                # different from our persistent MaterialBillboard FX and do
                # not describe the render/collision visibility contract.
                editor_icons+=1
                continue
            if bool(c.get_editor_property("visible"))!=(bool(rc["visible"]) if active else False):
                failures.append({"actor":row["label"],"component":rc["name"],"problem":"visible flag"})
            if isinstance(c,unreal.PrimitiveComponent) and not active and c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION:
                failures.append({"actor":row["label"],"problem":"inactive collision"})
    markers=h["read"](h["REPORT"] / "ArenaMarkers.json")["markers"]
    for row in markers:
        a=by.get(row["label"])
        shift = layout["source_phase2_translation_cm"] if separated and row["label"].startswith("SP_BP_Phase2_") else [0, 0, 0]
        if not a or not a.get_editor_property("is_editor_only_actor") or max(abs(h["vec"](a.get_actor_location())[i]-row["location_cm"][i]-shift[i]) for i in range(3))>.002:
            failures.append({"marker":row["label"],"problem":"marker contract"})
    result=h["write"](name,{"variant":variant,"baseline_actors":len(baseline),"markers":len(markers),"editor_only_icon_visibility_excluded":editor_icons,"failures":failures})
    print({"variant":variant,"actors_checked":len(baseline),"failure_count":len(failures),"first_failures":failures[:5]})
    return result


def audit_environment(name="EnvironmentAfter"):
    variant=h["read"](h["META"] / "StormPass_CurrentReviewVariant.json")["active_variant"]
    key=variant if variant in ("boss_phase_1","boss_phase_2") else "outside"
    layout = h["side_layout"]()
    if layout and layout.get("enabled"):
        key = "boss_phase_1"  # Separated direct sun; retained shared sky/fog.
    profile=h["read"](h["META"] / "StormPass_EnvironmentProfile.json")["profiles"][key]
    by={a.get_actor_label():a for a in h["actors"]()}
    failures=[]
    def number(field,actual,expected):
        if abs(actual-expected)>.00001:
            failures.append({"field":field,"actual":actual,"expected":expected})
    sun=by["SP_Environment_DirectionalLight"].get_component_by_class(unreal.DirectionalLightComponent)
    sky=by["SP_Environment_SkyLight"].get_component_by_class(unreal.SkyLightComponent)
    source_sun=profile["components"]["directional_light"]["properties"]
    rotation=source_sun.get("RelativeRotation",{})
    expected=unreal.Transform(rotation=unreal.Rotator(pitch=rotation.get("Pitch",0),yaw=rotation.get("Yaw",0),roll=rotation.get("Roll",0)))
    actual=unreal.Transform(rotation=by["SP_Environment_DirectionalLight"].get_actor_rotation())
    error=h["transform_error"](actual,expected)["rotation_degrees"]
    if error>.01:
        failures.append({"field":"sun.rotation","error_degrees":error})
    for label,component,source in (("sun",sun,source_sun),("sky",sky,profile["components"]["sky_light"]["properties"])):
        c=component.get_editor_property("light_color")
        for lower,upper in zip("rgba","RGBA"):
            number(label+".LightColor."+upper,getattr(c,lower),source["LightColor"].get(upper,255))
    active=h["read"](h["REPORT"] / "ActiveEnvironment.json")
    # Phase1's 2026-10-01 lighting review explicitly scales the source sky.
    # Validate the saved adapter, retaining the original value in the report.
    number("sky.Intensity",sky.get_editor_property("intensity"),active.get("sky_intensity_native",profile["components"]["sky_light"]["properties"]["Intensity"]))
    sky_mesh=by["SP_Environment_SkyMesh"].get_component_by_class(unreal.StaticMeshComponent)
    if sky_mesh.get_material(0).get_path_name()!=active["sky_material"]:
        failures.append({"field":"sky.material"})
    for label in ("SP_Environment_Cloud_0","SP_Environment_Cloud_1"):
        if label in by:
            for c in by[label].get_components_by_class(unreal.PrimitiveComponent):
                if bool(c.get_editor_property("visible"))!=active["clouds_visible"]:
                    failures.append({"field":label+".visible"})
    fog=by["SP_Environment_HeightFog"].get_component_by_class(unreal.ExponentialHeightFogComponent)
    number("fog.density",fog.get_editor_property("fog_density"),active["fog_native_density"])
    number("fog.height_falloff",fog.get_editor_property("fog_height_falloff"),active["fog_native_falloff"])
    if max(abs(h["vec"](by["SP_Environment_HeightFog"].get_actor_location())[i]-active["fog_location_cm"][i]) for i in range(3))>.002:
        failures.append({"field":"fog.location"})
    if bool(by["SP_Environment_PP_StormPass_Light_298"].get_editor_property("enabled"))!=(variant=="boss_phase_clear"):
        failures.append({"field":"BossClear PP override leakage"})
    fog_bridge=h["read"](h["REPORT"] / "FogBridge.json")
    for row in fog_bridge["actors"]:
        m=by[row["actor"]].get_component_by_class(unreal.StaticMeshComponent).get_material(0)
        if m.get_path_name()!=row["material"]:
            failures.append({"field":"fog_sheet.material","actor":row["actor"]})
        c=mel.get_material_instance_vector_parameter_value(m,"BP_EnvironmentFogSheetColor")
        for lower,upper in zip("rgba","RGBA"):
            number(row["actor"]+".FogSheetColor."+upper,getattr(c,lower),fog_bridge["source_rgba"][upper])
    result=h["write"](name,{"variant":variant,"source_profile":key,"source_sha256":profile["source_sha256"],"sun_rotation_error_degrees":error,"active_environment":active,"failures":failures})
    print({"environment":variant,"failure_count":len(failures),"first_failures":failures[:8]})
    return result
