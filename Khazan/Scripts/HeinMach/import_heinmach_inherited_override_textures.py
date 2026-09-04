"""Import inherited HeinMach override textures in an editor commandlet.

UE 5.8 Interchange asserts when AssetImportTasks is entered synchronously from
RiderLink's game-thread Python callback.  Run this file through
UnrealEditor-Cmd -run=pythonscript so texture import is isolated from the live
editor, map loading, and Fog actors.
"""

import importlib.util
import json
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESTORE_SCRIPT = os.path.join(
    SCRIPT_DIR, "restore_heinmach_inherited_override_materials.py"
)


def load_restore_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_inherited_material_texture_import", RESTORE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load inherited material restoration helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


restore = load_restore_module()
REPORT_PATH = os.path.join(
    restore.PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_InheritedOverrideTexture_Import.json",
)


def main():
    restoration = restore.load_json(restore.ROOT_RESTORATION_PATH)
    packages = sorted(
        item["package"]
        for item in restoration.get("placement_result", {}).get(
            "unresolved_override_materials", []
        )
    )
    if len(packages) != restore.EXPECTED_REBUILT_MATERIAL_COUNT:
        raise RuntimeError("Unexpected inherited material package inventory")
    records = [restore.raw_material_record(package) for package in packages]
    required_names = {
        item["texture_name"] for record in records for item in record["textures"]
    }
    before = restore.existing_texture_index()
    texture_index, import_count, configured = restore.import_textures(records)
    missing_after = sorted(required_names - set(texture_index))
    if missing_after:
        raise RuntimeError("Texture import incomplete: " + str(missing_after[:5]))
    report = {
        "status": "imported",
        "execution_mode": "UnrealEditor-Cmd PythonScript commandlet",
        "required_texture_count": len(required_names),
        "existing_required_texture_count_before": len(required_names & set(before)),
        "import_task_count": import_count,
        "resolved_required_texture_count_after": len(required_names & set(texture_index)),
        "configured_texture_count": len(
            [path for path in configured if path]
        ),
        "missing_texture_count_after": 0,
        "destination_root": restore.TEXTURE_ROOT,
        "reason": (
            "Avoid UE 5.8 Interchange TaskGraph recursion when importing through "
            "RiderLink's game-thread Python callback."
        ),
        "excluded_content": ["Level actors", "Fog actors", "Fog materials"],
    }
    restore.write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        failure = {
            "status": "failed",
            "error": str(exception),
            "traceback": traceback.format_exc(),
        }
        restore.write_json(REPORT_PATH, failure)
        unreal.log_error(str(exception))
        unreal.log_error(failure["traceback"])
        raise
