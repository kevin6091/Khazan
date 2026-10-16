"""Scoped, preflighted UE rename/options; only used in the independent editor."""
from pathlib import Path
import json, unreal
WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
OUT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007')
rows=json.loads((OUT/'RenamePlan.json').read_text(encoding='utf-8'))['rows']
preflight=json.loads((OUT/'Preflight.json').read_text(encoding='utf-8'))
assert preflight['status']=='Passed' and len(preflight['rows'])==len(rows)
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
done=[]
for index,row in enumerate(rows):
    assert unreal.EditorAssetLibrary.rename_asset(row['old'],row['new']),row['old']
    asset=unreal.load_asset(row['new']);assert isinstance(asset,unreal.AnimSequence)
    for prop,value in [('enable_root_motion',True),('force_root_lock',True),('root_motion_root_lock',unreal.RootMotionRootLock.ANIM_FIRST_FRAME)]:
        asset.set_editor_property(prop,value,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False),row['new']
    done.append(dict(old=row['old'],new=row['new']))
    if (index+1)%25==0:
        (OUT/'RenameProgress.json').write_text(json.dumps(dict(done=index+1,total=len(rows))),encoding='utf-8')
(OUT/'RenameApplied.json').write_text(json.dumps(dict(status='AppliedPendingValidation',rows=done),indent=2),encoding='utf-8')
folder=WORK/'Saved/EnemyAnimationOrganization';folder.mkdir(parents=True,exist_ok=True)
(folder/'OldAssets.txt').write_text('\n'.join(r['old'] for r in rows)+'\n',encoding='utf-8')
(folder/'AssetPairs.tsv').write_text('\n'.join(r['new']+'|'+r['old'] for r in rows)+'\n',encoding='utf-8')
print(json.dumps(dict(status='AppliedPendingValidation',sequences=len(done))))
