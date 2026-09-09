"""Read-only dependency plan for retaining curated Enemy visuals and all animations."""
import unreal,pathlib,json,collections,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT='/Game/_Art/Enemies'
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_CleanupPlan_20260909.json'
CAT=json.loads((PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/AssemblyCatalog.json').read_text(encoding='utf-8'))
REG=unreal.AssetRegistryHelpers.get_asset_registry()
OPTIONS=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)

def main():
    REG.search_all_assets(True)
    assets={str(a.package_name):a for a in REG.get_assets_by_path(ROOT,recursive=True)}
    classes={p:str(a.asset_class_path.asset_name) for p,a in assets.items()}
    deps={p:[str(x) for x in REG.get_dependencies(p,OPTIONS)] for p in assets}
    refs={p:[str(x) for x in REG.get_referencers(p,OPTIONS)] for p in assets}
    roots={r['asset'] for r in CAT}
    roots.update(p for p,c in classes.items() if c in ['AnimSequence','AnimComposite','AnimMontage','BlendSpace','BlendSpace1D','AimOffsetBlendSpace','AnimBlueprint'])
    roots.add(ROOT+'/HeinMach/Preview/L_HeinMach_EnemyCatalogue')
    outside={p:[r for r in ref if not r.startswith(ROOT+'/')] for p,ref in refs.items()}
    roots.update(p for p,r in outside.items() if r)
    keep=set();todo=list(roots)
    while todo:
        p=todo.pop()
        if p in keep:continue
        keep.add(p);todo.extend(x for x in deps.get(p,[]) if x in assets)
    candidates=sorted(set(assets)-keep)
    rows=[]
    for p in candidates:
        file=PROJECT/(p.replace('/Game/','Content/')+('.umap' if classes[p]=='World' else '.uasset'))
        rows.append({'asset':p,'class':classes[p],'bytes':file.stat().st_size if file.exists() else 0,'referencers':refs[p]})
    mesh_rows=[]
    for p,c in classes.items():
        if c in ['SkeletalMesh','Skeleton']:
            mesh_rows.append({'asset':p,'class':c,'retained':p in keep,'referencers':refs[p],'dependencies':deps[p]})
    bp_rows=[]
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    for rec in CAT:
        bp=unreal.load_asset(rec['asset']);assert bp
        comps={}
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            comp=lib.get_object_for_blueprint(lib.get_data(h),bp)
            if not isinstance(comp,unreal.SkeletalMeshComponent):continue
            data=comp.get_editor_property('animation_data')
            comps[comp.get_name()]={'mesh':comp.get_skinned_asset().get_path_name(),'animation':data.anim_to_play.get_path_name() if data.anim_to_play else None,'play_rate':data.saved_play_rate,'looping':data.saved_looping,'collision':str(comp.get_collision_enabled()),'rotation':str(comp.get_editor_property('relative_rotation')),'scale':str(comp.get_editor_property('relative_scale3d'))}
        bp_rows.append({'asset':rec['asset'],'family':rec['family'],'parent':assets[rec['asset']].get_tag_value('NativeParentClass'),'components':comps})
    result={'status':'planned','counts_before':dict(collections.Counter(classes.values())),'roots':sorted(roots),'keep':sorted(p for p in keep if p in assets),'candidates':rows,'candidate_counts':dict(collections.Counter(r['class'] for r in rows)),'candidate_bytes':sum(r['bytes'] for r in rows),'external_referencers':{p:r for p,r in outside.items() if r},'meshes_and_skeletons':mesh_rows,'blueprints':bp_rows,'dependencies':deps}
    REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_CLEANUP_PLAN',result['counts_before'],result['candidate_counts'],result['candidate_bytes'])

if __name__=='__main__':main()
