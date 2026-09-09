"""Fresh-process verification after deleting the unused Enemy closure."""
import unreal,pathlib,json,hashlib,collections
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();REPORTS=PROJECT/'Saved/ImportReports'
ROOT='/Game/_Art/Enemies'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan=read(REPORTS/'HeinMachEnemy_CleanupPlan_20260909.json');backup=read(REPORTS/'HeinMachEnemy_CleanupBackup_20260909.json');execution=read(REPORTS/'HeinMachEnemy_CleanupExecution_20260909.json');assert execution['status']=='passed'
    reg=unreal.AssetRegistryHelpers.get_asset_registry();reg.search_all_assets(True)
    assets={str(a.package_name):a for a in reg.get_assets_by_path(ROOT,recursive=True)}
    assert set(assets)==set(plan['keep']),'Saved asset inventory differs from retained plan'
    for rel,value in backup['retained_assets'].items():assert sha(PROJECT/rel)==value,rel
    opts=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
    missing=[]
    for p in assets:
        missing.extend({'asset':p,'missing':str(d)} for d in reg.get_dependencies(p,opts) if str(d).startswith(ROOT+'/') and str(d) not in assets)
    assert not missing,missing
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert level.load_level(ROOT+'/HeinMach/Preview/L_HeinMach_EnemyCatalogue')
    catalogue={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('EN_Variant_')}
    assert len(catalogue)==16
    inspected=[]
    for rec in read(PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AssemblyCatalog.json'):
        a=catalogue['EN_Variant_'+rec['asset'].rsplit('/',1)[1]]
        cs={c.get_name():c for c in a.get_components_by_class(unreal.SkeletalMeshComponent)};body=cs['EnemyBody']
        rot=body.get_editor_property('relative_rotation');assert abs(rot.pitch)<1e-5 and abs(rot.roll)<1e-5 and abs(rot.yaw+90)<1e-5
        assert body.get_editor_property('animation_data').anim_to_play.get_path_name().split('.')[0]==rec['idle_asset']
        for name,c in cs.items():
            assert c.get_skinned_asset() and c.get_skinned_asset().get_editor_property('skeleton')
            assert all(c.get_material(i) for i in range(c.get_num_materials()))
            if name!='EnemyBody':assert c.get_attach_parent()==body
            if name.startswith(('EnemyWeapon','EnemyShield','EnemyQuiver')):assert body.does_socket_exist(c.get_attach_socket_name())
        inspected.append({'asset':rec['asset'],'components':len(cs),'mesh_material_animation_attachments_valid':True})
    counts=dict(collections.Counter(str(a.asset_class_path.asset_name) for a in assets.values()))
    assert counts['Blueprint']==16 and counts['AnimSequence']==1436
    external_changes=[]
    for rel,value in backup['protected_worktree_files'].items():
        current=sha(PROJECT/rel) if (PROJECT/rel).is_file() else None
        if current!=value:external_changes.append({'path':rel,'before':value,'after':current})
    # The cleanup tool writes no source/gameplay files. Preserve concurrent work
    # and report it instead of resetting it to an earlier checksum.
    result={'status':'passed','counts_after':counts,'removed_counts':execution['deleted_counts'],'removed_bytes':execution['removed_bytes'],'retained_assets_hash_unchanged':len(backup['retained_assets']),'animations_unchanged':1436,'remaining_missing_enemy_dependencies':missing,'blueprints':inspected,'external_changes_observed':external_changes,'backup':backup['backup'],'validation_scope':'Fresh registry + saved map reload, complete retained-file hashes, live component references; no animation key data or gameplay code changed.'}
    (REPORTS/'HeinMachEnemy_CleanupAudit_20260909.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_CLEANUP_AUDIT_PASSED',counts)

if __name__=='__main__':main()
