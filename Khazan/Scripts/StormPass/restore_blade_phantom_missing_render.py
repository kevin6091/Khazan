"""Restore boss-room flag geometry, omitted local lights and fire presentation.

The animated fire billboards are an explicitly documented native approximation,
not a port of cooked Cascade/Niagara VM programs. Source positions are exact.
"""
import hashlib
import json
from pathlib import Path
import runpy

import unreal

ROOT = Path(__file__).resolve().parents[2]
env = runpy.run_path(str(ROOT / "Scripts/StormPass/polish_blade_phantom_arenas.py"))
REPORT, DEST = env["REPORT"], env["POLISH_ROOT"]
EX = ROOT / "Saved/Extracted/StormPass/BladePhantom_Extras_20261001"
ASSETS = ROOT / "Saved/Extracted/StormPass/BladePhantom_ExtrasAssets_20261001"
mel, eal = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary


def policy():
    p = REPORT / "MissingRenderPolicy.json"
    if p.exists():
        data = env["read"](p)
        data["temporary_native_adapter"].setdefault("unspecified_light_radius_cm", 1000.)
        data["temporary_native_adapter"].setdefault("added_light_cast_shadows", False)
        data["temporary_native_adapter"].setdefault("light_radius_shadow_boundary", "Unknown native radius uses temporary 1000 cm. Added fill lights do not cast shadows to avoid redundant local shadow atlases; this is a native presentation choice, not a verified source shadow setting.")
        data["temporary_native_adapter"].setdefault("cascade_atlas_frames_per_second", 30.)
        data["temporary_native_adapter"].setdefault("cascade_animation_boundary", "Native continuous flipbook uses temporary 30 frames/s; source looping_speed is not proven to be frames/s. Source core material atlas grids, separate emissive/opacity textures and serialized StartSize are preserved. Source emitter spawn/lifetime/distortion are not ported.")
        data["temporary_native_adapter"].setdefault("billboard_scale_boundary", "UE 5.8 MaterialBillboardComponent.cpp builds camera-facing world-size vertices with transform scale cancelled by ViewToLocal. Bake source scale into element size: FireWall width uses authored local Y (length), height Z; ordinary fire uses X/Z. This axis mapping is a native approximation of the source emitter, not recovered Niagara code.")
        return env["write"]("MissingRenderPolicy", data)
    return env["write"]("MissingRenderPolicy", {
        "temporary_native_adapter": {"unspecified_light_intensity_candelas": 2250., "explicit_source_light_to_candelas": 750.,
            "light_status": "Retain the earlier source-light adapter scale. xxPointLightComponent C++ defaults are unavailable; unspecified active lights use a temporary 2250 cd, with source-default colour unresolved (native white). Serialized zero-intensity placeholders remain off.",
            "niagara_fire_full_size_cm": [120., 160.], "fire_opacity_scale": .5, "fire_emissive_gain": 1., "atlas_a_columns": 8, "atlas_a_rows": 8,
            "fire_status": "Niagara sprite sizes and Atlas-A hardcoded grid are unconfirmed; size/grid are temporary display settings. Use original actor scale, exact texture, source FM_FireSubUV_A Speed=35, and source B_01 SubUVTexRC=(8,4), Speed=30. Cascade fire uses its serialized core StartSize and Fire_core_size.",
            "flag_wave_amplitude_cm": 9., "flag_wave_cycles_per_second": .25,
            "flag_status": "Small native cloth wave, temporary. Source FlagWave_Big records Height_Light=60 and Speed_Light=.25 but source shader units/formula are not reconstructed. Native 9 cm avoids large reference-pose deformation; no Chaos/PhysX cloth port."},
        "boundary": "No gameplay phase logic, damage, blocking, camera attachment or Character edits. Fire proxies have no collision. Water spline Niagara interfaces are recorded separately; existing native water surfaces are retained."
    })


def save(obj):
    if not eal.save_loaded_asset(obj, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + obj.get_path_name())


def expr(m, cls, **values):
    n = mel.create_material_expression(m, cls)
    for k, v in values.items():
        n.set_editor_property(k, v)
    return n


def connect(a, pin, b, target):
    if not mel.connect_material_expressions(a, pin, b, target):
        raise RuntimeError("Cannot connect " + target)


def output(m, n, prop, pin=""):
    if not mel.connect_material_property(n, pin, prop):
        raise RuntimeError("Cannot connect material output")


def scalar(m, name, value):
    return expr(m, unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(value))


def custom(m, names, code, kind):
    n = expr(m, unreal.MaterialExpressionCustom, code=code, output_type=kind)
    inputs = []
    for name in names:
        item = unreal.CustomInput()
        item.set_editor_property("input_name", name)
        inputs.append(item)
    n.set_editor_property("inputs", inputs)
    return n


def component_transform(row):
    h = runpy.run_path(str(ROOT / "Scripts/StormPass/restore_stormpass_child_render_meshes.py"))
    return h["expected_world_transform"](row)


def add_component(actor, cls):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_instance(actor)
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=cls, conform_transform_to_parent=True)
    handle, failure = sub.add_new_subobject(params)
    c = lib.get_object(lib.get_data(handle))
    if not c:
        raise RuntimeError("Cannot add component: " + str(failure))
    return c


def prepare_flag():
    path = DEST + "/Flags/SKM_SP_BP_Flag"
    mesh = unreal.load_asset(path)
    if not mesh:
        task = unreal.AssetImportTask()
        values = {"filename": str(ASSETS / "BBQ/Content/Art/World/World_Model/Prop/Flag/WSP_DKE_Flag_Base_002.psk"),
                  "destination_path": path.rsplit("/", 1)[0], "destination_name": path.rsplit("/", 1)[1], "automated": True, "save": False,
                  "factory": unreal.new_object(unreal.load_class(None, "/Script/UnrealPSKPSA.PSKFactory"))}
        for k, v in values.items():
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = unreal.load_asset(path)
    if not mesh:
        raise RuntimeError("Flag PSK import failed")
    original = unreal.load_asset("/Game/_Art/Player/Environment/StormPass/Reconstructed/SourceAssets/StormPass_StaticMeshLibrary/Materials/MI_WM_COM_Flag_Base_001")
    parent_path = DEST + "/Flags/M_SP_BP_FlagWave"
    parent = unreal.load_asset(parent_path)
    if not parent:
        parent = eal.duplicate_asset(original.get_editor_property("parent").get_path_name(), parent_path)
    if eal.get_metadata_tag(parent, "BladePhantomWaveReady") != "1":
        coord = expr(parent, unreal.MaterialExpressionTextureCoordinate)
        time = expr(parent, unreal.MaterialExpressionTime)
        normal = expr(parent, unreal.MaterialExpressionVertexNormalWS)
        wave = custom(parent, ["UV", "T", "N", "A", "F"], "float pin = saturate(UV.y); return N * (sin((T*F + UV.x)*6.28318530718) * A * pin * pin);", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        for n, node in (("UV", coord), ("T", time), ("N", normal), ("A", scalar(parent, "BP_FlagWaveAmplitudeCm", policy()["temporary_native_adapter"]["flag_wave_amplitude_cm"])), ("F", scalar(parent, "BP_FlagWaveFrequencyHz", policy()["temporary_native_adapter"]["flag_wave_cycles_per_second"]))):
            connect(node, "", wave, n)
        output(parent, wave, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        mel.recompile_material(parent)
        eal.set_metadata_tag(parent, "BladePhantomWaveReady", "1")
        save(parent)
    mat_path = DEST + "/Flags/MI_SP_BP_Flag_WW"
    mat = unreal.load_asset(mat_path) or eal.duplicate_asset(original.get_path_name(), mat_path)
    mel.set_material_instance_parent(mat, parent)
    for n, v in (("SP_GlobalMetallic", .5), ("SP_GlobalRoughness", .5), ("SP_GlobalSpecular", .25)):
        mel.set_material_instance_scalar_parameter_value(mat, n, v)
    # Same exact source D/N/S as the static flag, verified against WW metadata.
    source = "BBQ/Content/Art/World/World_Material/Prop/Material/WM_COM_Flag_Base_001_WW"
    eal.set_metadata_tag(mat, "BladePhantomOriginalMaterial", source)
    eal.set_metadata_tag(mat, "BladePhantomSourceMaterial", source)
    mel.update_material_instance(mat)
    save(mat)
    invisible_path = DEST + "/Flags/M_SP_BP_InvisibleSourceProxy"
    invisible = unreal.load_asset(invisible_path)
    if not invisible:
        invisible = unreal.AssetToolsHelpers.get_asset_tools().create_asset(invisible_path.rsplit("/",1)[1], invisible_path.rsplit("/",1)[0], unreal.Material, unreal.MaterialFactoryNew())
        invisible.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        zero = expr(invisible, unreal.MaterialExpressionConstant, r=0.)
        output(invisible, zero, unreal.MaterialProperty.MP_OPACITY_MASK)
        mel.recompile_material(invisible)
        save(invisible)
    slots = mesh.get_editor_property("materials")
    slots[0].set_editor_property("material_interface", mat)
    slots[1].set_editor_property("material_interface", invisible)  # Original SkeletalMaterials[1] Proxy=None.
    mesh.set_editor_property("materials", slots)
    eal.set_metadata_tag(mesh, "BladePhantomSourceMesh", "BBQ/Content/Art/World/World_Model/Prop/Flag/WSP_DKE_Flag_Base_002")
    skel = mesh.get_editor_property("skeleton")
    if skel:
        save(skel)
    save(mesh)
    env["write"]("FlagAssets", {"mesh": mesh.get_path_name(), "material": mat.get_path_name(), "source_psk_sha256": env["sha"](ASSETS / "BBQ/Content/Art/World/World_Model/Prop/Flag/WSP_DKE_Flag_Base_002.psk"), "original_bounds": env["read"](EX / "BBQ/Content/Art/World/World_Model/Prop/Flag/WSP_DKE_Flag_Base_002.json")[-1].get("ImportedBounds"), "animation_boundary": policy()["temporary_native_adapter"]["flag_status"]})
    print("Source flag imported and native material prepared")
    return mesh


def cascade_sources():
    result = {}
    for p in EX.rglob("FP_LVL_WBP_LightObj_001*.json"):
        objects = env["read"](p)
        def index(ref):
            return int(ref["ObjectPath"].rsplit(".", 1)[1])
        emitter = next(o for o in objects if o.get("Properties", {}).get("EmitterName") == "core_fire")
        lod = objects[index(emitter["Properties"]["LODLevels"][0])]["Properties"]
        required = objects[index(lod["RequiredModule"])]["Properties"]
        source = required["Material"]["ObjectPath"].split(".")[0]
        material = env["read"](EX / (source + ".json"))[0]["Properties"]
        scalars = {v["ParameterInfo"]["Name"]: v["ParameterValue"] for v in material["ScalarParameterValues"]}
        textures = {v["ParameterInfo"]["Name"]: v["ParameterValue"]["ObjectPath"].split(".")[0].rsplit("/", 1)[1] for v in material["TextureParameterValues"]}
        si = next(index(v) for v in lod["Modules"] if objects[index(v)]["Type"] == "ParticleModuleSize")
        size = objects[si]["Properties"]["StartSize"]["MinValueVec"]
        ci = next(index(v) for v in lod["Modules"] if objects[index(v)]["Type"] == "ParticleModuleColor")
        color = objects[ci]["Properties"]["StartColor"]["MinValueVec"]
        group = "Small" if "small" in p.name else "Medium"
        result[group] = {"source_json": str(p), "source_sha256": env["sha"](p), "size_object_index": si, "size_field": "Properties.StartSize.MinValueVec", "full_size_cm": [size["X"], size["Y"]], "source_material": source,
                         "columns": scalars["SubUV_U"], "rows": scalars["SubUV_V"], "emissive_texture": textures["Tex_Emi"], "opacity_texture": textures["Tex_Opa"], "source_looping_speed": scalars["looping_speed"],
                         "color_object_index": ci, "color_field": "Properties.StartColor.MinValueVec", "start_color_linear_rgb": [color[k] for k in "XYZ"]}
    env["write"]("CascadeCoreSources", result)
    return result


def prepare_fire_materials():
    result = {}
    core = cascade_sources()
    recipes = [("A", "FT_FireTex_RGB", None, policy()["temporary_native_adapter"]["atlas_a_columns"], policy()["temporary_native_adapter"]["atlas_a_rows"], 35.), ("B", "FT_FireTex_RGB_4", None, 8, 4, 30.)]
    recipes += [(k, v["emissive_texture"], v["opacity_texture"], v["columns"], v["rows"], policy()["temporary_native_adapter"]["cascade_atlas_frames_per_second"]) for k,v in core.items()]
    root = ASSETS / "BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/SubUV"
    def import_texture(source, native_color=False):
        tex_path = DEST + "/FX/Textures/T_SP_BP_" + source
        texture = unreal.load_asset(tex_path)
        if not texture:
            task = unreal.AssetImportTask()
            for k,v in {"filename":str(root / (source + ".png")), "destination_path":tex_path.rsplit("/",1)[0], "destination_name":tex_path.rsplit("/",1)[1], "automated":True, "save":False, "factory":unreal.TextureFactory()}.items():
                task.set_editor_property(k,v)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            texture = unreal.load_asset(tex_path)
        if not texture:
            raise RuntimeError("Fire atlas import failed")
        # The P1 Torchfire red atlases contain actual orange RGB. sRGB is a
        # native color interpretation; the source texture omits that flag.
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT if native_color else unreal.TextureCompressionSettings.TC_MASKS)
        # Compression changes can reset sRGB; apply the color flag last.
        texture.set_editor_property("srgb", native_color)
        save(texture)
        return texture
    for name, source, opacity_source, columns, rows, speed in recipes:
        color_core = name in core
        texture = import_texture(source, color_core)
        opacity_texture = import_texture(opacity_source) if opacity_source else texture
        path = DEST + "/FX/Materials/M_SP_BP_FireAtlas_" + name
        m = unreal.load_asset(path)
        if not m:
            m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit("/",1)[1], path.rsplit("/",1)[0], unreal.Material, unreal.MaterialFactoryNew())
        ready_version = "2" if color_core else "1"
        if eal.get_metadata_tag(m,"BladePhantomFireReady") != ready_version:
            mel.delete_all_material_expressions(m)
            m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
            m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
            m.set_editor_property("two_sided", True)
            coord = expr(m, unreal.MaterialExpressionTextureCoordinate)
            time = expr(m, unreal.MaterialExpressionTime)
            uv = custom(m, ["UV", "T", "C", "R", "F"], "float count=C*R; float frame=fmod(floor(T*F),count); float2 cell=float2(fmod(frame,C),floor(frame/C)); return (cell+saturate(UV))/float2(C,R);", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
            for n, node in (("UV", coord), ("T", time), ("C", scalar(m,"BP_AtlasColumns",columns)), ("R",scalar(m,"BP_AtlasRows",rows)), ("F",scalar(m,"BP_AtlasFramesPerSecond",speed))):
                connect(node,"",uv,n)
            sample=expr(m,unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BP_FireAtlas",texture=texture,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if color_core else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            connect(uv,"",sample,"UVs")
            mask=custom(m,["RGB"],"return saturate(max(RGB.r,max(RGB.g,RGB.b)));",unreal.CustomMaterialOutputType.CMOT_FLOAT1)
            connect(sample,"RGB",mask,"RGB")
            opa_sample=expr(m,unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BP_FireOpacityAtlas",texture=opacity_texture,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            connect(uv,"",opa_sample,"UVs")
            opa_mask=custom(m,["RGB"],"return saturate(max(RGB.r,max(RGB.g,RGB.b)));",unreal.CustomMaterialOutputType.CMOT_FLOAT1)
            connect(opa_sample,"RGB",opa_mask,"RGB")
            tint=expr(m,unreal.MaterialExpressionVectorParameter,parameter_name="BP_FireTint",default_value=unreal.LinearColor(1,1,1,1))
            emit=expr(m,unreal.MaterialExpressionMultiply)
            connect(sample if color_core else mask,"RGB" if color_core else "",emit,"A");connect(tint,"",emit,"B")
            gain=expr(m,unreal.MaterialExpressionMultiply)
            connect(emit,"",gain,"A");connect(scalar(m,"BP_FireEmissiveGain",policy()["temporary_native_adapter"]["fire_emissive_gain"]),"",gain,"B")
            output(m,gain,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            opacity=expr(m,unreal.MaterialExpressionMultiply)
            connect(opa_mask,"",opacity,"A");connect(scalar(m,"BP_FireOpacity",policy()["temporary_native_adapter"]["fire_opacity_scale"]),"",opacity,"B")
            output(m,opacity,unreal.MaterialProperty.MP_OPACITY)
            mel.recompile_material(m);eal.set_metadata_tag(m,"BladePhantomFireReady",ready_version);save(m)
        result[name]=m
    # P1 core color comes from the actual core_fire emitter, preserving atlas
    # RGB. P2 retains the previous native palette approximation.
    profiles=env["read"](env["META"] / "StormPass_EnvironmentProfile.json")["profiles"]
    colors={"Phase1Small":unreal.LinearColor(*core["Small"]["start_color_linear_rgb"],1),"Phase1Medium":unreal.LinearColor(*core["Medium"]["start_color_linear_rgb"],1),"Phase2":unreal.LinearColor(1,.25,0,1)}
    mats={}
    for group, typ in (("Phase1Small","Small"),("Phase1Medium","Medium"),("Phase2Fire","A"),("Phase2Wall","B")):
        path=DEST+"/FX/Materials/MI_SP_BP_"+group
        mat=unreal.load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit("/",1)[1],path.rsplit("/",1)[0],unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mat,result[typ]);mel.set_material_instance_vector_parameter_value(mat,"BP_FireTint",colors[group if group.startswith("Phase1") else "Phase2"]);mel.update_material_instance(mat);save(mat);mats[group]=mat
    env["write"]("FireAssets", {"materials":{k:v.get_path_name() for k,v in mats.items()},"boundary":policy()["temporary_native_adapter"]["fire_status"],"colour_boundary":"P1 uses source core_fire StartColor and original atlas RGB through a native billboard shader. P2 retains source WEP FogSheetColor RGB (1,.25,0) as a palette approximation. Full particle/material programs remain unported."})
    print("Animated source fire atlases prepared")
    return mats


def place_missing(mesh=None, fire=None):
    rows=env["read"](REPORT/"MissingRenderPlan.json")["components"]
    by={a.get_actor_label():a for a in env["actors"]()}
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    records=[]
    for row in rows:
        typ=row["component_type"];fields={k:v["value"] for k,v in row["inherited"].items()};target=component_transform(row)
        label="SP_BossExtra_{}_{:05d}_{:05d}".format(row["source_level"],row["actor_object_index"],row["component_object_index"])
        a=by.get(label)
        if typ=="xxWPropSkeletalMeshComponent":
            if not mesh:continue
            a=a or sub.spawn_actor_from_class(unreal.SkeletalMeshActor, target.translation)
            c=a.get_component_by_class(unreal.SkeletalMeshComponent)
            c.set_skeletal_mesh_asset(mesh)
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        elif typ=="xxPointLightComponent":
            value=fields["Intensity"]
            if value==0:continue
            a=a or sub.spawn_actor_from_class(unreal.PointLight,target.translation)
            c=a.get_component_by_class(unreal.PointLightComponent)
            c.set_editor_property("mobility",unreal.ComponentMobility.MOVABLE)
            c.set_editor_property("intensity_units",unreal.LightUnits.CANDELAS)
            c.set_editor_property("intensity",value*policy()["temporary_native_adapter"]["explicit_source_light_to_candelas"] if value is not None else policy()["temporary_native_adapter"]["unspecified_light_intensity_candelas"])
            c.set_editor_property("attenuation_radius",fields["AttenuationRadius"] if fields["AttenuationRadius"] is not None else policy()["temporary_native_adapter"]["unspecified_light_radius_cm"])
            c.set_editor_property("cast_shadows",policy()["temporary_native_adapter"]["added_light_cast_shadows"])
            if fields["LightColor"]:
                p=fields["LightColor"];c.set_editor_property("light_color",unreal.Color(r=p["R"],g=p["G"],b=p["B"],a=p.get("A",255)))
        else:
            if not fire:continue
            asset=fields["Asset"] if typ=="xxNiagaraComponent" else fields["Template"]
            path=asset["ObjectPath"]
            if "WaterDecal" in path:
                continue  # Spline Niagara DI is separately recorded, no fake fire.
            group=("Phase1Small" if "small" in path else "Phase1Medium") if typ=="xxParticleSystemComponent" else "Phase2Wall" if "FireWall" in path else "Phase2Fire"
            a=a or sub.spawn_actor_from_class(unreal.Actor,target.translation)
            c=a.get_component_by_class(unreal.MaterialBillboardComponent) or add_component(a,unreal.MaterialBillboardComponent)
            c.set_editor_property("elements",[])
            size=policy()["temporary_native_adapter"]["niagara_fire_full_size_cm"]
            if typ=="xxParticleSystemComponent":
                # Exact source core StartSize, then the authored size parameter.
                factor=next((v["Vector"]["X"] for v in row["instance_parameters"] if v["Name"]=="Fire_core_size"),1)
                raw=cascade_sources()["Small" if group=="Phase1Small" else "Medium"]["full_size_cm"]
                size=[v*factor for v in raw]
            sx = abs(target.scale3d.y if group=="Phase2Wall" else target.scale3d.x)
            sy = abs(target.scale3d.z)
            c.add_element(fire[group],None,False,size[0]*sx/2,size[1]*sy/2,None)
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        a.set_actor_label(label);a.set_actor_transform(target,False,False)
        a.set_folder_path("StormPass/01_BladePhantom/Phase%d/AddedRender" % env["phase"](label))
        a.set_editor_property("tags",["BladePhantomSourceExtra",typ])
        records.append({"label":label,"source_level":row["source_level"],"component_object_index":row["component_object_index"],"source_component_type":typ,"source_world_transform":{"location_cm":env["vec"](target.translation),"scale":env["vec"](target.scale3d)},"native_class":a.get_class().get_name(),"render_boundary":"source geometry" if typ=="xxWPropSkeletalMeshComponent" else "native approximation"})
    p=REPORT/"MissingRenderApplied.json"
    previous=env["read"](p) if p.exists() else {"actors":{}}
    previous["actors"].update({r["label"]:r for r in records});env["write"]("MissingRenderApplied",previous)
    print(json.dumps({"added_or_updated":len(records),"total_recorded":len(previous["actors"])}))
    return previous


def register_variants():
    path=env["META"]/"StormPass_PhaseVisibilityBaseline_20260907.json"
    data=env["read"](path);known={r["label"] for r in data["actors"]}
    helper=runpy.run_path(str(ROOT/"Scripts/StormPass/restore_stormpass_route_presentation.py"))
    for a in env["actors"]():
        variant=helper["phase"](a)
        if not variant or a.get_actor_label() in known:continue
        components=[]
        for c in a.get_components_by_class(unreal.SceneComponent):
            d={"name":c.get_name(),"visible":bool(c.get_editor_property("visible"))}
            if isinstance(c,unreal.PrimitiveComponent):d["collision"]=c.get_collision_enabled().name
            components.append(d)
        data["actors"].append({"label":a.get_actor_label(),"variant":variant,"hidden_in_game":False,"post_process_enabled":None,"components":components,"added_source_render_20261001":True})
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Added render actors registered with source review variants")
