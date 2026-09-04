"""Read-only reload audit for the two StormPass native-water bindings."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MODULE_PATH = os.path.join(
    SCRIPT_DIR, "restore_stormpass_native_water_materials.py"
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_NativeWaterMaterial_ReloadAudit.json",
)
MAP_DISK_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "StormPass",
    "Maps",
    "L_StormPass_Environment.umap",
)


def log(message):
    unreal.log("KHAZAN_STORMPASS_NATIVE_WATER_RELOAD_AUDIT: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_water_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_stormpass_native_water_reload", MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load native-water restoration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def color_delta(actual, expected):
    return max(
        abs(float(actual.r) - float(expected[0])),
        abs(float(actual.g) - float(expected[1])),
        abs(float(actual.b) - float(expected[2])),
        abs(float(actual.a) - float(expected[3])),
    )


def hierarchy_audit(water, metadata, master, source_instances, actor_instances):
    library = unreal.MaterialEditingLibrary
    statistics = library.get_statistics(master)
    failures = []
    parameter_checks = {
        "scalar": 0,
        "vector": 0,
        "texture": 0,
        "switch": 0,
        "actor_color": 0,
    }
    maxima = {"scalar_delta": 0.0, "vector_delta": 0.0}
    expected_parent_paths = {
        "skoffa": master.get_path_name(),
        "stormpass": source_instances["skoffa"].get_path_name(),
        "stormpass_inst1": source_instances["stormpass"].get_path_name(),
    }
    for key, instance in source_instances.items():
        parent = instance.get_editor_property("parent")
        actual_parent = parent.get_path_name() if parent else None
        if actual_parent != expected_parent_paths[key]:
            failures.append(
                {
                    "asset": instance.get_path_name(),
                    "issue": "parent",
                    "actual": actual_parent,
                    "expected": expected_parent_paths[key],
                }
            )
        record = metadata["material_instances"][key]
        for item in record.get("scalars", []):
            parameter_checks["scalar"] += 1
            actual = library.get_material_instance_scalar_parameter_value(
                instance, item["name"]
            )
            delta = abs(float(actual) - float(item["value"]))
            maxima["scalar_delta"] = max(maxima["scalar_delta"], delta)
            if delta > 0.00002:
                failures.append(
                    {
                        "asset": instance.get_path_name(),
                        "issue": "scalar:" + item["name"],
                        "delta": delta,
                    }
                )
        for item in record.get("vectors", []):
            parameter_checks["vector"] += 1
            actual = library.get_material_instance_vector_parameter_value(
                instance, item["name"]
            )
            delta = color_delta(actual, item["value"])
            maxima["vector_delta"] = max(maxima["vector_delta"], delta)
            if delta > 0.00002:
                failures.append(
                    {
                        "asset": instance.get_path_name(),
                        "issue": "vector:" + item["name"],
                        "delta": delta,
                    }
                )
        for item in record.get("textures", []):
            parameter_checks["texture"] += 1
            actual = library.get_material_instance_texture_parameter_value(
                instance, item["name"]
            )
            expected_name = water.package_basename(
                str(item.get("object_path") or "").rsplit(".", 1)[0]
            )
            if not actual or actual.get_name() != expected_name:
                failures.append(
                    {
                        "asset": instance.get_path_name(),
                        "issue": "texture:" + item["name"],
                        "actual": actual.get_path_name() if actual else None,
                        "expected_name": expected_name,
                    }
                )
        for item in record.get("switches", []):
            parameter_checks["switch"] += 1
            actual = library.get_material_instance_static_switch_parameter_value(
                instance, item["name"]
            )
            if bool(actual) != bool(item["value"]):
                failures.append(
                    {
                        "asset": instance.get_path_name(),
                        "issue": "switch:" + item["name"],
                    }
                )

    for record in metadata["water_actors"]:
        instance = actor_instances[record["label"]]
        expected_parent = source_instances[
            record["source_material_key"]
        ].get_path_name()
        parent = instance.get_editor_property("parent")
        if not parent or parent.get_path_name() != expected_parent:
            failures.append(
                {"asset": instance.get_path_name(), "issue": "actor_instance_parent"}
            )
        for name, expected in (
            ("EffectColor", record["effect_color"]),
            ("FoamColor", record["foam_color"]),
        ):
            parameter_checks["actor_color"] += 1
            actual = library.get_material_instance_vector_parameter_value(instance, name)
            delta = color_delta(actual, expected)
            maxima["vector_delta"] = max(maxima["vector_delta"], delta)
            if delta > 0.00002:
                failures.append(
                    {
                        "asset": instance.get_path_name(),
                        "issue": "actor_color:" + name,
                        "delta": delta,
                    }
                )

    scalar_names = {str(name) for name in library.get_scalar_parameter_names(master)}
    vector_names = {str(name) for name in library.get_vector_parameter_names(master)}
    texture_names = {str(name) for name in library.get_texture_parameter_names(master)}
    required_scalars = {
        item["name"] for item in metadata["master_parameters"]["scalars"]
    }
    required_vectors = {
        item["name"] for item in metadata["master_parameters"]["vectors"]
    }
    required_textures = {
        item["name"] for item in metadata["master_parameters"]["textures"]
    }
    missing_master_parameters = {
        "scalars": sorted(required_scalars - scalar_names),
        "vectors": sorted(required_vectors - vector_names),
        "textures": sorted(required_textures - texture_names),
    }
    if any(missing_master_parameters.values()):
        failures.append(
            {"asset": master.get_path_name(), "issue": "missing_master_parameters"}
        )
    if master.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_MASKED:
        failures.append({"asset": master.get_path_name(), "issue": "blend_mode"})
    if (
        master.get_editor_property("shading_model")
        != unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER
    ):
        failures.append({"asset": master.get_path_name(), "issue": "shading_model"})
    if not bool(master.get_editor_property("two_sided")):
        failures.append({"asset": master.get_path_name(), "issue": "two_sided"})

    return {
        "master_material": master.get_path_name(),
        "master_expression_count": int(library.get_num_material_expressions(master)),
        "master_scalar_parameter_count": len(scalar_names),
        "master_vector_parameter_count": len(vector_names),
        "master_texture_parameter_count": len(texture_names),
        "shader_statistics": {
            "vertex_shader_instructions": int(
                statistics.get_editor_property("num_vertex_shader_instructions")
            ),
            "pixel_shader_instructions": int(
                statistics.get_editor_property("num_pixel_shader_instructions")
            ),
            "samplers": int(statistics.get_editor_property("num_samplers")),
            "pixel_texture_samples": int(
                statistics.get_editor_property("num_pixel_texture_samples")
            ),
        },
        "missing_master_parameters": missing_master_parameters,
        "source_instance_count": len(source_instances),
        "actor_instance_count": len(actor_instances),
        "parameter_checks": parameter_checks,
        "maximum_parameter_deltas": maxima,
        "failure_count": len(failures),
        "failures": failures[:30],
    }


def main():
    water = load_water_module()
    metadata = water.load_json(water.METADATA_PATH)
    restoration = water.load_json(water.REPORT_PATH)
    if metadata.get("status") != "analyzed":
        raise RuntimeError("Native-water source metadata is incomplete")
    if restoration.get("status") != "restored":
        raise RuntimeError("Native-water restoration report is incomplete")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(water.DEV_MAP_PATH):
        raise RuntimeError("Failed to leave StormPass for native-water audit")
    if not level_subsystem.load_level(water.MAP_PATH):
        raise RuntimeError("Failed to reload StormPass for native-water audit")

    actor_records = metadata["water_actors"]
    master, source_instances, actor_instances = water.load_prepared_assets(
        actor_records
    )
    hierarchy = hierarchy_audit(
        water, metadata, master, source_instances, actor_instances
    )
    bindings = water.validate_map_bindings(
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem),
        actor_records,
        actor_instances,
    )
    failures = []
    if hierarchy["failure_count"]:
        failures.append("material_hierarchy")
    if bindings["failure_count"]:
        failures.append("map_bindings")

    report = {
        "status": "passed" if not failures else "failed",
        "operation": "stormpass_native_water_saved_map_reload_audit",
        "map_path": water.MAP_PATH,
        "reload_cycle": [water.DEV_MAP_PATH, water.MAP_PATH],
        "map_modified": False,
        "metadata_path": water.METADATA_PATH,
        "restoration_report_path": water.REPORT_PATH,
        "material_hierarchy": hierarchy,
        "map_bindings": bindings,
        "failed_stages": failures,
        "map_size_bytes": os.path.getsize(MAP_DISK_PATH),
        "map_sha256": sha256_file(MAP_DISK_PATH),
        "content_boundary": {
            "visual_level_content_only": True,
            "gameplay_or_source_code_audited_or_modified": False,
            "collision_or_navigation_audited_or_modified": False,
        },
    }
    write_json(REPORT_PATH, report)
    if failures:
        raise RuntimeError("Native-water reload audit failed: " + ", ".join(failures))
    log(
        "RESULT status=passed actors={} water={} fog={} hierarchy_checks={} "
        "binding_failures={} sha256={} report={}".format(
            bindings["actor_count"],
            bindings["checked_water_actor_count"],
            bindings["fog_count"],
            sum(hierarchy["parameter_checks"].values()),
            bindings["failure_count"],
            report["map_sha256"],
            REPORT_PATH,
        )
    )
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        if not os.path.isfile(REPORT_PATH):
            write_json(
                REPORT_PATH,
                {
                    "status": "failed",
                    "error": str(exception),
                    "traceback": traceback.format_exc(),
                    "map_modified": False,
                },
            )
        unreal.log_error(
            "KHAZAN_STORMPASS_NATIVE_WATER_RELOAD_AUDIT: " + str(exception)
        )
        raise
