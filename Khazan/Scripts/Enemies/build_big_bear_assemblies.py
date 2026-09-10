"""Build three source-authored BigBear material variants as visual Enemy BPs.

The HeinMach and StormPass spawns both reference CB_BigBear_E.  These Actor
Blueprints therefore share one mesh/skeleton/animation library and differ only
by the three material indices serialized by the source character recipe.  They
contain no gameplay, AI, hit, collision-damage, or ability implementation.
"""

from __future__ import annotations

import json
import pathlib
import traceback

import unreal


PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT = PROJECT / "Saved/Extracted/BigBear_20260910"
MANIFEST = json.loads((ROOT / "ImportManifest.json").read_text(encoding="utf-8"))
META = PROJECT / "Content/_Art/Enemies/Shared/Beasts/BigBear/Metadata/Extraction_20260910"
LEVEL_PRESENCE = json.loads((META / "LevelPresence.json").read_text(encoding="utf-8"))
REPORT = PROJECT / "Saved/ImportReports/BigBear_AssemblyBuild_20260910.json"
CATALOG = META / "BigBearAssemblyCatalog.json"
VERSION = "20260910_BigBearVisualAssemblyV1"
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUBOBJECTS = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SUBOBJECT_LIBRARY = unreal.SubobjectDataBlueprintFunctionLibrary


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load(path: str):
    asset = unreal.load_asset(path)
    check(asset is not None, "Missing UE asset " + path)
    return asset


def save(asset) -> None:
    check(EAL.save_loaded_asset(asset, only_if_is_dirty=False), "Unable to save " + asset.get_path_name())


def package_path(value) -> str | None:
    if not value:
        return None
    return value.get("ObjectPath", value.get("AssetPathName", "")).split(".", 1)[0].replace(
        "/Game/", "BBQ/Content/"
    ) or None


def level_context() -> dict:
    result = {}
    for row in LEVEL_PRESENCE:
        properties = row["properties"]
        result[row["level"]] = {
            "source_level_package": row["source_level_package"],
            "source_actor": row["actor_name"],
            "actor_blueprint": package_path(properties.get("ActorBP_Soft")),
            "ai_data": package_path(properties.get("AIData")),
            "dependent_level": properties.get("DependentLevelPath"),
            "start_animation": package_path(properties.get("StartAnimation")),
            "vigilant_reaction_animation": package_path(properties.get("VigilantReactionAnimation")),
        }
    return result


def add_body_component(blueprint, mesh):
    handles = SUBOBJECTS.k2_gather_subobject_data_for_blueprint(blueprint)
    check(bool(handles), "Blueprint has no root subobject")
    params = unreal.AddNewSubobjectParams(
        parent_handle=handles[-1],
        new_class=unreal.SkeletalMeshComponent,
        blueprint_context=blueprint,
        conform_transform_to_parent=True,
    )
    handle, reason = SUBOBJECTS.add_new_subobject(params)
    data = SUBOBJECT_LIBRARY.get_data(handle)
    component = SUBOBJECT_LIBRARY.get_object_for_blueprint(data, blueprint)
    check(component is not None, "Unable to add EnemyBody: " + str(reason))
    SUBOBJECTS.rename_subobject(handle, unreal.Text("EnemyBody"))
    component.set_skinned_asset_and_update(mesh)
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    transform = MANIFEST["preview_component_transform"]
    rotation = transform["RelativeRotation"]
    location = transform["RelativeLocation"]
    scale = transform["RelativeScale3D"]
    component.set_editor_property(
        "relative_rotation",
        unreal.Rotator(pitch=rotation["Pitch"], yaw=rotation["Yaw"], roll=rotation["Roll"]),
    )
    component.set_editor_property("relative_location", unreal.Vector(location["X"], location["Y"], location["Z"]))
    component.set_editor_property("relative_scale3d", unreal.Vector(scale["X"], scale["Y"], scale["Z"]))
    return component


def configure_animation(component, animation) -> None:
    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = component.get_editor_property("animation_data")
    data.set_editor_property("anim_to_play", animation)
    data.set_editor_property("saved_looping", True)
    data.set_editor_property("saved_playing", True)
    data.set_editor_property("saved_play_rate", 1.0)
    component.set_editor_property("animation_data", data)


def build_variant(row: dict, context: dict) -> dict:
    path = row["blueprint"]
    if EAL.does_asset_exist(path):
        blueprint = load(path)
        check(EAL.get_metadata_tag(blueprint, "BigBearAssemblyVersion") == VERSION, "Unknown existing BP " + path)
        created = False
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        folder, name = path.rsplit("/", 1)
        blueprint = TOOLS.create_asset(name, folder, unreal.Blueprint, factory)
        check(blueprint is not None, "Unable to create " + path)
        body = add_body_component(blueprint, load(MANIFEST["body"]["destination"]))
        for index, material_path in enumerate(row["materials"]):
            body.set_material(index, load(material_path))
        configure_animation(body, load(row["idle_asset"]))
        created = True

    selection = {
        "variant": row["variant"],
        "source_material_index": row["source_material_index"],
        "source_materials": row["source_materials"],
        "project_materials": row["materials"],
        "mesh": MANIFEST["body"]["destination"],
        "idle_source": row["idle_source"],
        "idle_asset": row["idle_asset"],
        "idle_play_rate": 1.0,
        "level_context": context,
    }
    tags = {
        "EnemyArtRole": "VisualAssembly_NoGameplayAI",
        "EnemySpecies": "BigBear",
        "EnemySourceLevels": json.dumps(MANIFEST["source_levels"], ensure_ascii=False),
        "OriginalPackage": MANIFEST["source_character"],
        "BigBearLibraryVersion": MANIFEST["library_version"],
        "BigBearAssemblyVersion": VERSION,
        "SourceMaterialVariationIndex": str(row["source_material_index"]),
        "AssemblySelection": json.dumps(selection, ensure_ascii=False),
        "SourceComponentTransform": json.dumps(MANIFEST["source_component_transform"], ensure_ascii=False),
        "PreviewComponentTransform": json.dumps(MANIFEST["preview_component_transform"], ensure_ascii=False),
        "AnimationContract": "Single-node A_EN_PLAY source-timed sequence; loop enabled; saved play rate 1.0.",
        "GameplayCoverage": "None: visual catalogue assembly only; source level AI/spawn data remains metadata.",
    }
    for key, value in tags.items():
        EAL.set_metadata_tag(blueprint, key, value)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    save(blueprint)
    selection.update({"asset": path, "created": created, "role": tags["EnemyArtRole"]})
    return selection


def main() -> None:
    report = {"status": "running", "version": VERSION, "assemblies": []}
    try:
        context = level_context()
        check(set(context) == {"HeinMach", "StormPass"}, "Expected both source level contexts")
        for row in MANIFEST["material_variants"]:
            record = build_variant(row, context)
            report["assemblies"].append(record)
            print("BIG_BEAR_ASSEMBLY", record["asset"], flush=True)
        CATALOG.write_text(json.dumps(report["assemblies"], indent=2, ensure_ascii=False), encoding="utf-8")
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("BIG_BEAR_ASSEMBLY_BUILD_PASSED", flush=True)


if __name__ == "__main__":
    main()
