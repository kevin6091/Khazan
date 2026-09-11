"""Real-RHI shader and saved Yetuga catalogue validation."""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/Yetuga_20260911"
META = PROJECT / "Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911"
MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
CATALOG = json.loads((META / "YetugaAssemblyCatalog.json").read_text(encoding="utf-8"))
REPORT = PROJECT / "Saved/ImportReports/Yetuga_RenderAudit_20260911.json"
SUMMARY = META / "RenderValidationSummary.json"
MAP_PATH = MANIFEST["destination_root"] + "/Preview/L_EN_Yetuga_Catalogue"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def asset_path(value) -> str | None:
    return value.get_path_name().split(".", 1)[0] if value else None


def capture_preview(report):
    # Presentation-only camera/resolution; these are not original gameplay values.
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    position = unreal.Vector(950.0, -1100.0, 470.0)
    target = unreal.Vector(0.0, 80.0, 285.0)
    rotation = unreal.MathLibrary.find_look_at_rotation(position, target)
    preview_light = actors.spawn_actor_from_class(unreal.DirectionalLight, position, rotation)
    light = preview_light.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    light.set_intensity(5.0)
    light.set_cast_shadows(False)
    for entry in actors.get_all_level_actors():
        for mesh_component in entry.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh_component.set_update_animation_in_editor(True)
            mesh_component.set_position(0.0, False)
    actor = actors.spawn_actor_from_class(unreal.SceneCapture2D, position, rotation)
    component = actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    texture = unreal.RenderingLibrary.create_render_target2d(world, 1200, 1000, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.set_editor_property("texture_target", texture)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    component.set_editor_property("capture_every_frame", False)
    component.set_editor_property("fov_angle", 50.0)
    component.capture_scene()
    folder = PROJECT / "Saved/ImportReports"
    unreal.RenderingLibrary.export_render_target(world, texture, str(folder), "Yetuga_RenderPreview_20260911.png")
    path = folder / "Yetuga_RenderPreview_20260911.png"
    check(path.exists() and path.stat().st_size > 0, "Preview capture was not exported")
    report["preview_capture"] = str(path)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, texture, str(folder), "Yetuga_BaseColorPreview_20260911.png")
    report["base_color_capture"] = str(folder / "Yetuga_BaseColorPreview_20260911.png")
    if "-YetugaDiagnostic" in unreal.SystemLibrary.get_command_line():
        material = unreal.new_object(unreal.Material)
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        expression = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        expression.set_editor_property("constant", unreal.LinearColor(1.0, 0.1, 0.3, 1.0))
        unreal.MaterialEditingLibrary.connect_material_property(expression, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.MaterialEditingLibrary.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.MaterialEditingLibrary.get_statistics(material)
        report["diagnostic_components"] = []
        for entry in actors.get_all_level_actors():
            for mesh_component in entry.get_components_by_class(unreal.SkeletalMeshComponent):
                report["diagnostic_components"].append({"actor":entry.get_actor_label(),"bounds":str(entry.get_actor_bounds(False)),"location":str(mesh_component.get_world_location()),"scale":str(mesh_component.get_world_scale()),"visible":mesh_component.is_visible()})
                for index in range(mesh_component.get_num_materials()):
                    mesh_component.set_material(index, material)
        component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        component.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, texture, str(folder), "Yetuga_DiagnosticOpaque_20260911.png")
    report["preview_capture_settings"] = {"status":"Assistant-selected presentation settings; not source gameplay metadata", "resolution":[1200,1000], "fov_degrees":50.0, "camera_cm":[950,-1100,470], "target_cm":[0,80,285]}
    actors.destroy_actor(actor)
    actors.destroy_actor(preview_light)


def main() -> None:
    command_line = unreal.SystemLibrary.get_command_line()
    report = {"status": "running", "command_line": command_line, "materials": [], "assemblies": []}
    report["capture_context"] = "EditorAfterWarmup" if "capture_yetuga_editor_preview.py" in command_line else "ImmediateCommandletCapture"
    try:
        check("-nullrhi" not in command_line.lower(), "Render audit requires a real RHI")
        check("-allowcommandletrendering" in command_line.lower(), "Commandlet rendering was not enabled")
        material_paths = [
            MANIFEST["destination_root"] + "/Materials/Masters/M_EN_Yetuga_SurfacePreview",
            MANIFEST["destination_root"] + "/Materials/Masters/M_EN_Yetuga_EyePreview",
            MANIFEST["destination_root"] + "/Materials/Masters/M_EN_Yetuga_PropPreview",
        ] + [row["destination"] for row in MANIFEST["materials"]]
        for path in material_paths:
            material = unreal.load_asset(path)
            check(material is not None, "Missing material " + path)
            statistics = unreal.MaterialEditingLibrary.get_statistics(material)
            values = {
                key: statistics.get_editor_property(key)
                for key in [
                    "num_vertex_shader_instructions",
                    "num_pixel_shader_instructions",
                    "num_samplers",
                    "num_pixel_texture_samples",
                ]
            }
            check(
                values["num_vertex_shader_instructions"] > 0 and values["num_pixel_shader_instructions"] > 0,
                "No compiled shader instructions for " + path + ": " + repr(values),
            )
            report["materials"].append({"asset": path, **values})
            print("YETUGA_SHADER_OK", path, flush=True)

        level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        current_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if not current_world or current_world.get_path_name().split(".", 1)[0] != MAP_PATH:
            check(level_subsystem.load_level(MAP_PATH), "Unable to reload saved Yetuga catalogue")
        actor_map = {
            actor.get_actor_label(): actor
            for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        }
        for row in CATALOG:
            label = row["asset"].rsplit("/", 1)[1]
            actor = actor_map.get(label)
            check(actor is not None, "Missing saved catalogue actor " + label)
            components = actor.get_components_by_class(unreal.SkeletalMeshComponent)
            check(len(components) == 1, "Unexpected component count " + label)
            body = components[0]
            check(asset_path(body.get_skinned_asset()) == MANIFEST["body"]["destination"], "Mesh load mismatch " + label)
            check(body.get_num_bones() == MANIFEST["body"]["animation_reference_bones"], "Skeleton load mismatch " + label)
            check(all(body.get_material(index) is not None for index in range(body.get_num_materials())), "Material load mismatch " + label)
            animation = body.get_editor_property("animation_data").anim_to_play
            check(animation is not None and animation.get_play_length() > 0.0, "Animation load mismatch " + label)
            report["assemblies"].append(
                {
                    "asset": row["asset"],
                    "mesh": asset_path(body.get_skinned_asset()),
                    "bones": body.get_num_bones(),
                    "materials": body.get_num_materials(),
                    "animation": asset_path(animation),
                }
            )
        report["catalogue_map"] = MAP_PATH
        capture_preview(report)
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("YETUGA_RENDER_AUDIT_PASSED", flush=True)


if __name__ == "__main__":
    main()
