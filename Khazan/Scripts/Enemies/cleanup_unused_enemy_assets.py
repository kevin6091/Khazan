"""Delete only the backed-up, unreferenced closure outside the 16 curated BPs."""
import unreal,pathlib,json,hashlib,collections,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORTS=PROJECT/'Saved/ImportReports'
ROOT='/Game/_Art/Enemies'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan_file=REPORTS/'HeinMachEnemy_CleanupPlan_20260909.json';plan=read(plan_file);backup=read(REPORTS/'HeinMachEnemy_CleanupBackup_20260909.json')
    assert sha(plan_file)==backup['plan_sha256'],'Plan changed since backup'
    candidates={r['asset'] for r in plan['candidates']};keep=set(plan['keep'])
    assert not candidates.intersection(keep)
    allowed={'Blueprint','SkeletalMesh','Material','MaterialInstanceConstant','Texture2D'}
    reg=unreal.AssetRegistryHelpers.get_asset_registry();reg.search_all_assets(True)
    opts=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
    remaining=[]
    for r in plan['candidates']:
        p=r['asset'];assert p.startswith(ROOT+'/') and r['class'] in allowed,p
        rel=p.replace('/Game/','Content/')+'.uasset';source=PROJECT/rel;copy=pathlib.Path(backup['backup'])/rel
        assert source.resolve().is_relative_to((PROJECT/'Content/_Art/Enemies').resolve())
        assert sha(copy)==backup['deleted_asset_candidates'][rel],p
        if not source.exists():continue # Resume an interrupted exact deletion plan.
        assert sha(source)==backup['deleted_asset_candidates'][rel],p
        external=[str(x) for x in reg.get_referencers(p,opts) if str(x) not in candidates]
        assert not external,(p,'retained or external references',external)
        remaining.append(p)
    # The complete unused closure is deleted together so references between
    # unused BPs, old meshes, and their unused materials are removed together.
    objects=[unreal.load_asset(p) for p in sorted(remaining)];assert all(objects)
    if objects:assert unreal.EditorAssetLibrary.delete_loaded_assets(objects),'Deletion API failed'
    for p in candidates:assert not (PROJECT/(p.replace('/Game/','Content/')+'.uasset')).exists(),p
    for rel,value in backup['retained_assets'].items():assert sha(PROJECT/rel)==value,('Retained asset changed',rel)
    result={'status':'passed','deleted_assets':plan['candidates'],'deleted_counts':plan['candidate_counts'],'removed_bytes':plan['candidate_bytes'],'retained_assets_hash_unchanged':len(backup['retained_assets']),'animations_deleted_or_modified':0,'backup':backup['backup']}
    (REPORTS/'HeinMachEnemy_CleanupExecution_20260909.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_UNUSED_ASSETS_REMOVED',len(candidates))

if __name__=='__main__':main()
