import json, unreal
from pathlib import Path
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
rows=json.loads((main/'Metadata/FabVFX_20261012/Completion/InputManifest.json').read_text())
old=[r for r in rows if r['prior_main']]
names={'/Game/'+str(Path(r['relative_path']).with_suffix('')).replace('\\','/') for r in old}
registry=unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(synchronous_search=True)
opts=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_hard_management_references=False,include_soft_management_references=False)
outside=[];loaded=[]
for package in sorted(names):
 refs=[str(x) for x in registry.get_referencers(package,opts) if str(x).startswith('/Game/') and str(x) not in names]
 if refs: outside.append({'package':package,'referencers':refs})
 object_name=package.rsplit('/',1)[-1]
 if unreal.find_object(None,package+'.'+object_name):loaded.append(package)
r={'outside_referencers':outside,'loaded_target_packages':loaded,'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
(main/'Metadata/FabVFX_20261012/Completion/MainOwnership.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({'outside_referencers':len(outside),'loaded_targets':len(loaded),'dirty_content':r['dirty_content'],'dirty_maps':r['dirty_maps']}))
