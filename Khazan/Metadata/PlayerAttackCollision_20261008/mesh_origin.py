import unreal,json
from pathlib import Path
cls=unreal.EditorAssetLibrary.load_blueprint_class('/Game/_Art/Player/Character/Bluprints/BP_Player')
if not cls:
  reg=unreal.AssetRegistryHelpers.get_asset_registry()
  assets=reg.get_assets_by_package_name('/Game/Bluprints/Player/BP_Player')
  print('CLASS?',assets)
else:
  cdo=unreal.get_default_object(cls)
  mesh=cdo.get_editor_property('mesh')
  print('MESH',mesh.get_path_name(),mesh.get_editor_property('relative_location'),mesh.get_editor_property('relative_rotation'),mesh.get_editor_property('relative_scale3d'))

