"""Import FModel ActorX PSK files through the project-local UnrealPSKPSA plugin.

Run from UnrealEditor-Cmd. The importer preserves the source folder hierarchy
below CHA_Model and never replaces an existing Unreal asset.
"""

import json
import os
import re
import traceback

import unreal


FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_ROOT = os.path.join(
    FMODEL_ROOT,
    "BBQ",
    "Content",
    "_Kazan_",
    "Art",
    "Character",
    "CHA_Model",
)
DESTINATION_ROOT = "/Game/_Art/Kazan/FModel/PSK"
FACTORY_CLASS_PATH = "/Script/UnrealPSKPSA.PSKFactory"
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(), "ImportReports", "FModel_PSK_Import.json"
)


def log(message):
    unreal.log("KHAZAN_PSK_IMPORT: " + str(message))


def warn(message):
    unreal.log_warning("KHAZAN_PSK_IMPORT: " + str(message))


def error(message):
    unreal.log_error("KHAZAN_PSK_IMPORT: " + str(message))


def command_line_value(name):
    command_line = unreal.SystemLibrary.get_command_line()
    match = re.search(r'(?:^|\s)-{}=(?:"([^"]*)"|(\S+))'.format(re.escape(name)), command_line)
    if not match:
        return ""
    return match.group(1) if match.group(1) is not None else match.group(2)


def discover_sources(filter_text=""):
    if not os.path.isdir(SOURCE_ROOT):
        raise RuntimeError("FModel PSK source directory does not exist: " + SOURCE_ROOT)

    normalized_filter = filter_text.casefold()
    sources = []
    for directory, _, filenames in os.walk(SOURCE_ROOT):
        for filename in filenames:
            if not filename.casefold().endswith(".psk"):
                continue
            source = os.path.normpath(os.path.join(directory, filename))
            if normalized_filter and normalized_filter not in source.casefold():
                continue
            sources.append(source)
    return sorted(sources, key=str.casefold)


def destination_for(source):
    relative_parent = os.path.relpath(os.path.dirname(source), SOURCE_ROOT)
    if relative_parent == ".":
        return DESTINATION_ROOT
    relative_parent = relative_parent.replace("\\", "/")
    return DESTINATION_ROOT + "/" + relative_parent


def expected_asset_path(source):
    asset_name = os.path.splitext(os.path.basename(source))[0].replace("_LOD0", "")
    return "{0}/{1}.{1}".format(destination_for(source), asset_name)


def write_report(report):
    report_directory = os.path.dirname(REPORT_PATH)
    os.makedirs(report_directory, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2, sort_keys=True)
        report_file.write("\n")


def save_destination_assets(destination):
    saved = []
    asset_paths = unreal.EditorAssetLibrary.list_assets(
        destination, recursive=False, include_folder=False
    )
    for asset_path in sorted(asset_paths):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            continue
        unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
        saved.append(asset.get_path_name())
    return saved


def main():
    factory_class = unreal.load_class(None, FACTORY_CLASS_PATH)
    if not factory_class:
        raise RuntimeError(
            "UnrealPSKPSA factory is unavailable. Build and enable the project plugin first: "
            + FACTORY_CLASS_PATH
        )

    filter_text = command_line_value("KhazanPskFilter")
    sources = discover_sources(filter_text)
    if not sources:
        raise RuntimeError("No PSK sources matched filter: " + (filter_text or "<none>"))

    report = {
        "source_root": SOURCE_ROOT,
        "destination_root": DESTINATION_ROOT,
        "filter": filter_text,
        "discovered": len(sources),
        "imported": [],
        "skipped_existing": [],
        "failed": [],
    }
    tasks = []
    task_sources = []

    for source in sources:
        expected_path = expected_asset_path(source)
        if unreal.EditorAssetLibrary.does_asset_exist(expected_path):
            existing_asset = unreal.EditorAssetLibrary.load_asset(expected_path)
            if (
                existing_asset
                and isinstance(existing_asset, unreal.SkeletalMesh)
                and existing_asset.get_editor_property("skeleton")
            ):
                report["skipped_existing"].append(
                    {
                        "source": source,
                        "asset": existing_asset.get_path_name(),
                        "skeleton": existing_asset.get_editor_property(
                            "skeleton"
                        ).get_path_name(),
                    }
                )
            else:
                report["failed"].append(
                    {
                        "source": source,
                        "expected_asset": expected_path,
                        "reason": "Existing asset is not a loadable Skeletal Mesh with a Skeleton",
                    }
                )
            continue

        task = unreal.AssetImportTask()
        task.set_editor_property("filename", source)
        task.set_editor_property("destination_path", destination_for(source))
        task.set_editor_property("destination_name", os.path.splitext(os.path.basename(source))[0])
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("replace_existing_settings", False)
        task.set_editor_property("save", True)
        tasks.append(task)
        task_sources.append(source)

    if tasks:
        log("Importing {} PSK file(s)".format(len(tasks)))
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    companion_assets = {}
    for source in task_sources:
        destination = destination_for(source)
        if destination not in companion_assets:
            companion_assets[destination] = save_destination_assets(destination)

    for source, task in zip(task_sources, tasks):
        imported_paths = list(task.get_editor_property("imported_object_paths"))
        valid_paths = []
        for asset_path in imported_paths:
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if (
                asset
                and isinstance(asset, unreal.SkeletalMesh)
                and asset.get_editor_property("skeleton")
            ):
                unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
                valid_paths.append(asset.get_path_name())
        if valid_paths:
            report["imported"].append(
                {
                    "source": source,
                    "assets": valid_paths,
                    "saved_companion_assets": companion_assets[destination_for(source)],
                }
            )
            log("IMPORTED {} -> {}".format(source, ", ".join(valid_paths)))
        else:
            expected_path = expected_asset_path(source)
            expected_asset = unreal.EditorAssetLibrary.load_asset(expected_path)
            if (
                expected_asset
                and isinstance(expected_asset, unreal.SkeletalMesh)
                and expected_asset.get_editor_property("skeleton")
            ):
                unreal.EditorAssetLibrary.save_loaded_asset(
                    expected_asset, only_if_is_dirty=False
                )
                report["imported"].append(
                    {
                        "source": source,
                        "assets": [expected_asset.get_path_name()],
                        "saved_companion_assets": companion_assets[
                            destination_for(source)
                        ],
                    }
                )
                log("IMPORTED {} -> {}".format(source, expected_asset.get_path_name()))
            else:
                report["failed"].append(
                    {"source": source, "expected_asset": expected_path}
                )
                error("FAILED {} (expected {})".format(source, expected_path))

    write_report(report)
    log(
        "RESULT discovered={} imported={} skipped={} failed={} report={}".format(
            report["discovered"],
            len(report["imported"]),
            len(report["skipped_existing"]),
            len(report["failed"]),
            REPORT_PATH,
        )
    )
    if report["failed"]:
        raise RuntimeError("One or more PSK imports failed; see " + REPORT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        error(str(exception))
        error(traceback.format_exc())
        raise
