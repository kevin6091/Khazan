import unreal,json
from pathlib import Path
print('GETBONE',unreal.AnimPoseExtensions.get_bone_pose.__doc__)
print('EVAL',dir(unreal.AnimDataEvalType))
print('SPACE',dir(unreal.AnimPoseSpaces))
print('ROOT',str(Path(unreal.Paths.project_dir()).resolve()))
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008/PlayerDefinitionsBefore.json')
registry=unreal.AssetRegistryHelpers.get_asset_registry()
defs=registry.get_assets_by_class(unreal.TopLevelAssetPath('/Script/Khazan','KZComboDefinitionData'))
rows=[]
import hashlib
for data in defs:
    name=str(data.package_name)
    if '/Monsters/' in name:continue
    obj=unreal.load_asset(name)
    path=Path(unreal.Paths.project_content_dir())/(name.removeprefix('/Game/')+'.uasset')
    rows.append(dict(asset=name,file=str(path.relative_to(Path(unreal.Paths.project_dir()))),before=hashlib.sha256(path.read_bytes()).hexdigest(),nodes=[str(n.get_editor_property('node_id')) for n in obj.get_editor_property('nodes')]))
out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(rows)
