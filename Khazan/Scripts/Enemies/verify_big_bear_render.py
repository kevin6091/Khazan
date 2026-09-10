"""Real-RHI shader and saved BigBear catalogue validation."""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/BigBear_20260910"
META = PROJECT / "Content/_Art/Enemies/Shared/Beasts/BigBear/Metadata/Extraction_20260910"
MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
CATALOG = json.loads((META / "BigBearAssemblyCatalog.json").read_text(encoding="utf-8"))
REPORT = PROJECT / "Saved/ImportReports/BigBear_RenderAudit_20260910.json"
SUMMARY = META / "RenderValidationSummary.json"
MAP_PATH = MANIFEST["destination_root"] + "/Preview/L_EN_BigBear_Catalogue"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def asset_path(value) -> str | None:
    return value.get_path_name().split(".", 1)[0] if value else None


def main() -> None:
    command_line = unreal.SystemLibrary.get_command_line()
    report = {"status": "running", "command_line": command_line, "materials": [], "assemblies": []}
    try:
        check("-nullrhi" not in command_line.lower(), "Render audit requires a real RHI")
        check("-allowcommandletrendering" in command_line.lower(), "Commandlet rendering was not enabled")
        material_paths = [
            MANIFEST["destination_root"] + "/Materials/Masters/M_EN_BigBear_SurfacePreview",
            MANIFEST["destination_root"] + "/Materials/Masters/M_EN_BigBear_EyePreview",
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
            print("BIG_BEAR_SHADER_OK", path, flush=True)

        level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        check(level_subsystem.load_level(MAP_PATH), "Unable to reload saved BigBear catalogue")
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
            check(body.get_num_bones() == 79, "Skeleton load mismatch " + label)
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
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("BIG_BEAR_RENDER_AUDIT_PASSED", flush=True)


if __name__ == "__main__":
    main()
