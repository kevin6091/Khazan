"""Import only HeinMach PointInstancer foliage into an isolated UE map.

The first all-in-one USD import enabled asset sharing and collapsed 113 unique
PointInstancer batches into a small set of reused baked meshes.  This importer
selects only the 15 foliage actor prims, disables asset/slot sharing, and keeps
the result in a sandbox map until it has been audited for transfer to the main
reconstruction map.
"""

import json
import os
import re
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_LEVEL_ROOT = os.path.join(
    FMODEL_ROOT, "BBQ", "Content", "_Kazan_", "Level", "HeinMach"
)
STAGE_NAME = "HeinMach_FoliageOnly_Corrected"
GENERATED_STAGE_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportSources", STAGE_NAME + ".usda"
)
DESTINATION_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/FoliageBatches"
)
SANDBOX_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_FoliageImportSandbox"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_Foliage_Batch_Import.json",
)

FOLIAGE_LAYERS = (
    "HeinMach_Landscape2",
    "HeinMach_Landscape1",
    "HeinMach_SubLV01_OP",
    "HeinMach_SubLV03_Cave_1",
    "HeinMach_SubLV03_Cave_2",
    "HeinMach_SubLV04_WaterfallUp_1",
    "HeinMach_SubLV02_Blizzard",
    "HeinMach_SubLV02_Blizzard_1",
    "HeinMach_SubLV02_CaveEntry",
    "HeinMach_SubLV03_Cave",
    "HeinMach_SubLV04_Waterfall",
    "HeinMach_SubLV04_WaterfallUp",
    "HeinMach_SubLV05_Escape",
    "HeinMach_SubLV06_Boss",
    "HeinMach_SubLV05_Escape_1",
)

EXPECTED_BATCH_COUNT = 113
EXPECTED_INSTANCE_COUNT = 12495

FOLIAGE_ACTOR_RE = re.compile(r'def\s+Scope\s+"(InstancedFoliageActor[^"]*)"')
POINT_BLOCK_RE = re.compile(
    r'def\s+PointInstancer\s+"([^"]+)"(.*?)'
    r'(?=\n\s{12}def\s+PointInstancer|\n\s{8}\})',
    re.DOTALL,
)
REFERENCE_RE = re.compile(r'prepend\s+references\s*=\s*@([^@]+)@')
POSITIONS_RE = re.compile(
    r'point3f\[\]\s+positions\s*=\s*\[(.*?)\]', re.DOTALL
)
TUPLE_RE = re.compile(r'\([^\)]*\)')


def log(message):
    unreal.log("KHAZAN_HEINMACH_FOLIAGE_IMPORT: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_HEINMACH_FOLIAGE_IMPORT: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def source_path(layer):
    return os.path.join(SOURCE_LEVEL_ROOT, layer + ".usda")


def object_path(obj):
    return obj.get_path_name() if obj else None


def vector_dict(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def rotator_dict(value):
    return {
        "pitch": float(value.pitch),
        "yaw": float(value.yaw),
        "roll": float(value.roll),
    }


def asset_class_name(asset_path):
    data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
    if not data or not data.is_valid():
        return "Invalid"
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        return asset.get_class().get_name() if asset else "Invalid"


def parse_sources():
    rows = []
    prim_paths = []
    sources = []
    for layer in FOLIAGE_LAYERS:
        path = source_path(layer)
        if not os.path.isfile(path):
            raise RuntimeError("Missing foliage source layer: " + path)
        sources.append(path)
        with open(path, "r", encoding="utf-8", errors="replace") as source:
            text = source.read()

        foliage_actor_match = FOLIAGE_ACTOR_RE.search(text)
        if not foliage_actor_match:
            raise RuntimeError("Layer has no foliage actor prim: " + layer)
        foliage_actor = foliage_actor_match.group(1)
        prim_paths.append("/{}/{}".format(layer, foliage_actor))

        for block in POINT_BLOCK_RE.finditer(text):
            point_name = block.group(1)
            body = block.group(2)
            reference_match = REFERENCE_RE.search(body)
            positions_match = POSITIONS_RE.search(body)
            if not reference_match or not positions_match:
                raise RuntimeError(
                    "Incomplete PointInstancer {} in {}".format(point_name, layer)
                )
            rows.append(
                {
                    "layer": layer,
                    "foliage_actor": foliage_actor,
                    "point_instancer": point_name,
                    "prim_path": "/{}/{}/RootComponent0/{}".format(
                        layer, foliage_actor, point_name
                    ),
                    "prototype_reference": reference_match.group(1),
                    "prototype_basename": os.path.splitext(
                        os.path.basename(reference_match.group(1))
                    )[0],
                    "instance_count": len(TUPLE_RE.findall(positions_match.group(1))),
                }
            )

    instance_count = sum(row["instance_count"] for row in rows)
    if len(rows) != EXPECTED_BATCH_COUNT or instance_count != EXPECTED_INSTANCE_COUNT:
        raise RuntimeError(
            "Unexpected foliage source counts: batches={} instances={}".format(
                len(rows), instance_count
            )
        )
    return rows, prim_paths, sources


def write_stage(sources):
    sublayers = ["        @{}@".format(path.replace("\\", "/")) for path in sources]
    stage_text = "\n".join(
        [
            "#usda 1.0",
            "(",
            "    metersPerUnit = 0.01",
            '    upAxis = "Z"',
            "    subLayers = [",
            ",\n".join(sublayers),
            "    ]",
            ")",
            "",
        ]
    )
    os.makedirs(os.path.dirname(GENERATED_STAGE_PATH), exist_ok=True)
    with open(GENERATED_STAGE_PATH, "w", encoding="utf-8", newline="\n") as output:
        output.write(stage_text)


def load_or_create_sandbox():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(SANDBOX_MAP_PATH):
        if not subsystem.load_level(SANDBOX_MAP_PATH):
            raise RuntimeError("Failed to load foliage sandbox map")
        return subsystem, False
    if not subsystem.new_level(SANDBOX_MAP_PATH, False):
        raise RuntimeError("Failed to create foliage sandbox map")
    return subsystem, True


def imported_asset_stats():
    paths = []
    if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION_ROOT):
        paths = list(
            unreal.EditorAssetLibrary.list_assets(
                DESTINATION_ROOT, recursive=True, include_folder=False
            )
        )
    class_counts = {}
    for path in paths:
        class_name = asset_class_name(path)
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    return paths, dict(sorted(class_counts.items()))


def actor_ancestry(actor):
    labels = []
    seen = set()
    current = actor
    while current:
        path = current.get_path_name()
        if path in seen:
            break
        seen.add(path)
        labels.append(current.get_actor_label())
        try:
            current = current.get_attach_parent_actor()
        except Exception:
            current = None
    return labels


def material_record(material):
    textures = []
    if material:
        library = unreal.MaterialEditingLibrary
        try:
            names = list(library.get_texture_parameter_names(material))
        except Exception:
            names = []
        for name in names:
            try:
                texture = library.get_material_instance_texture_parameter_value(
                    material, name
                )
            except Exception:
                texture = None
            if texture:
                textures.append(texture.get_path_name())
    return {
        "path": object_path(material),
        "name": material.get_name() if material else None,
        "textures": sorted(set(textures)),
    }


def collect_batch_records():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    records = []
    for component in actor_subsystem.get_all_level_actors_components():
        if not isinstance(component, unreal.StaticMeshComponent):
            continue
        mesh = component.get_editor_property("static_mesh")
        mesh_path = object_path(mesh)
        if not mesh_path or not mesh_path.startswith(DESTINATION_ROOT + "/"):
            continue
        actor = component.get_owner()
        bounds = mesh.get_bounds()
        try:
            vertex_count = int(unreal.EditorStaticMeshLibrary.get_number_verts(mesh, 0))
        except Exception:
            vertex_count = None
        records.append(
            {
                "actor_path": actor.get_path_name() if actor else None,
                "actor_label": actor.get_actor_label() if actor else None,
                "actor_ancestry": actor_ancestry(actor) if actor else [],
                "component_path": component.get_path_name(),
                "mesh_path": mesh_path,
                "mesh_name": mesh.get_name(),
                "location": vector_dict(actor.get_actor_location()),
                "rotation": rotator_dict(actor.get_actor_rotation()),
                "scale": vector_dict(actor.get_actor_scale3d()),
                "mesh_bounds_origin": vector_dict(bounds.origin),
                "mesh_bounds_extent": vector_dict(bounds.box_extent),
                "lod0_vertex_count": vertex_count,
                "materials": [material_record(item) for item in component.get_materials()],
            }
        )
    return sorted(records, key=lambda row: (row["mesh_path"], row["actor_path"]))


def import_foliage_stage(prim_paths):
    options = unreal.UsdStageImportOptions()
    options.set_editor_property("import_actors", True)
    options.set_editor_property("import_geometry", True)
    options.set_editor_property("import_skeletal_animations", False)
    options.set_editor_property("import_level_sequences", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_only_used_materials", True)
    options.set_editor_property("import_groom_assets", False)
    options.set_editor_property("import_sparse_volume_textures", False)
    options.set_editor_property("import_sounds", False)
    options.set_editor_property("prims_to_import", prim_paths)
    options.set_editor_property("share_assets_for_identical_prims", False)
    options.set_editor_property("prim_path_folder_structure", True)
    options.set_editor_property("merge_identical_material_slots", False)
    options.set_editor_property("interpret_lods", True)
    options.set_editor_property("existing_actor_policy", unreal.ReplaceActorPolicy.APPEND)
    options.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.IGNORE)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", GENERATED_STAGE_PATH)
    task.set_editor_property("destination_path", DESTINATION_ROOT)
    task.set_editor_property("destination_name", STAGE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    task.set_editor_property("factory", unreal.UsdStageImportFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths"))


def main():
    source_batches, prim_paths, source_files = parse_sources()
    write_stage(source_files)
    level_subsystem, sandbox_created = load_or_create_sandbox()

    before_records = collect_batch_records()
    if before_records and len(before_records) != EXPECTED_BATCH_COUNT:
        raise RuntimeError(
            "Partial foliage sandbox import exists: {} batches".format(
                len(before_records)
            )
        )

    imported_paths = []
    status = "skipped_existing_valid"
    if not before_records:
        imported_paths = import_foliage_stage(prim_paths)
        if not level_subsystem.save_current_level():
            raise RuntimeError("Failed to save foliage sandbox map")
        unreal.EditorAssetLibrary.save_directory(
            DESTINATION_ROOT, only_if_is_dirty=False, recursive=True
        )
        status = "imported"

    records = collect_batch_records()
    assets, class_counts = imported_asset_stats()
    if len(records) != EXPECTED_BATCH_COUNT:
        status = "validation_failed"

    report = {
        "status": status,
        "source_level_root": SOURCE_LEVEL_ROOT,
        "source_layers": list(FOLIAGE_LAYERS),
        "source_files": source_files,
        "source_batches": source_batches,
        "source_batch_count": len(source_batches),
        "source_instance_count": sum(
            row["instance_count"] for row in source_batches
        ),
        "prim_paths_to_import": prim_paths,
        "generated_stage": GENERATED_STAGE_PATH,
        "destination_root": DESTINATION_ROOT,
        "sandbox_map_path": SANDBOX_MAP_PATH,
        "sandbox_created": sandbox_created,
        "imported_object_paths": imported_paths,
        "asset_count": len(assets),
        "asset_class_counts": class_counts,
        "batch_actor_count": len(records),
        "batch_records": records,
        "import_options": {
            "share_assets_for_identical_prims": False,
            "merge_identical_material_slots": False,
            "prim_path_folder_structure": True,
        },
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT status={} source_batches={} source_instances={} imported_batches={} "
        "assets={} report={}".format(
            status,
            report["source_batch_count"],
            report["source_instance_count"],
            report["batch_actor_count"],
            report["asset_count"],
            REPORT_PATH,
        )
    )
    if status not in ("imported", "skipped_existing_valid"):
        raise RuntimeError("Foliage batch import validation failed; see " + REPORT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        write_json(REPORT_PATH, failure)
        error(str(exception))
        error(failure["traceback"])
        raise
