from pathlib import Path
import json,unreal
root=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');meta=root/'Metadata/FabVFX_20261012/Completion'
r=unreal.AssetRegistryHelpers.get_asset_registry();r.search_all_assets(synchronous_search=True)
names=['/Game/Cursed_Magic/Maps/Cursed_Magic','/Game/Cursed_Magic/Blueprints/BP_Cursed_Magic_GameMode','/Game/Cursed_Magic/VFX_Niagara/NS_Cursed_Magic_Attack1']
out={p:[{'name':str(x.asset_name),'class':str(x.asset_class_path.asset_name)} for x in r.get_assets_by_package_name(p)] for p in names}
(meta/'WPSourceProbe.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
