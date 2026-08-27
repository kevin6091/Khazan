import unreal


ROOT = "/Game/_Art/Kazan"


def log(message):
    unreal.log("KHAZAN_INSPECT: " + str(message))


asset_paths = unreal.EditorAssetLibrary.list_assets(ROOT, recursive=True, include_folder=False)
log("asset_count={}".format(len(asset_paths)))

for asset_path in sorted(asset_paths):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset or not isinstance(asset, unreal.SkeletalMesh):
        continue

    log("MESH {}".format(asset_path))
    for index, skeletal_material in enumerate(asset.get_editor_property("materials")):
        material = skeletal_material.get_editor_property("material_interface")
        material_path = material.get_path_name() if material else "None"
        slot_name = skeletal_material.get_editor_property("material_slot_name")
        imported_slot_name = skeletal_material.get_editor_property("imported_material_slot_name")
        log(
            "  SLOT {} slot={} imported={} material={}".format(
                index, slot_name, imported_slot_name, material_path
            )
        )

log("MATERIAL ASSETS")
for asset_path in sorted(asset_paths):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset or not isinstance(asset, unreal.MaterialInterface):
        continue
    parent_path = ""
    if isinstance(asset, unreal.MaterialInstanceConstant):
        parent = asset.get_editor_property("parent")
        parent_path = parent.get_path_name() if parent else "None"
    log("  {} class={} parent={}".format(asset_path, asset.get_class().get_name(), parent_path))

