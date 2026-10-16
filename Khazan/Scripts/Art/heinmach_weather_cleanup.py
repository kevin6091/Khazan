"""Remove only this task's unused trial systems/QA materials, after backup."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
BASE='/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
DIR=ROOT/'Content/_Art/Player/Environment/Rendering/HeinMachWeather'
META=DIR.parent/'Metadata/HeinMachWeather_20261006'
BACKUP=ROOT/'Saved/ArtBackups/HeinMachWeather_20261006/GeneratedUnused'
registry=unreal.AssetRegistryHelpers.get_asset_registry()
registry.wait_for_completion()
registry.scan_paths_synchronous([BASE],True)
options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,
                                              include_searchable_names=True,include_hard_management_references=True,
                                              include_soft_management_references=True)
names=['NS_HM_SourceSnow','NS_HM_SourceSnow_Validated','NS_HM_SourceSnow_Game','NS_HM_SourceSnow_Final',
       '_QA/M_QA_Signal','_QA/M_QA_Albedo','_QA/MI_QA_Shadow2','_QA/MI_QA_Shadow4','_QA/MI_QA_Shadow8']
report_path=META/'GeneratedUnusedCleanup.json'
prior=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
prior_rows={r['package']:r for r in prior.get('rows',[])}
rows=[]
for name in names:
    package=BASE+'/'+name
    queried_refs=registry.get_referencers(package,options)
    refs=[str(p) for p in queried_refs] if queried_refs is not None else None
    row=dict(prior_rows.get(package,{}))
    row.update(package=package,referencers=refs,
               referencer_query_state='package_missing' if refs is None else 'queried')
    path=DIR/(name+'.uasset')
    target=BACKUP/(name+'.uasset')
    if not unreal.EditorAssetLibrary.does_asset_exist(package):
        # Keep deletion evidence on repeated verification passes. Backups
        # identify the exact task-owned files; an absent package is not a
        # request to create or delete anything else.
        assert not path.exists(),package
        if target.exists():
            digest=hashlib.sha256(target.read_bytes()).hexdigest()
            if row.get('sha256'):assert row['sha256']==digest,package
            row.update(backup=str(target),sha256=digest,
                       already_absent_on_this_pass=True,disk_file_removed=True,deleted=True)
            rows.append(row)
        continue
    if refs:
        row['deleted']=False;rows.append(row);continue
    assert refs is not None,'Present package missing registry dependency data: '+package
    assert path.resolve().is_relative_to(DIR.resolve())
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
    row.update(backup=str(target),sha256=digest)
    assert unreal.EditorAssetLibrary.delete_asset(package),package
    # ObjectTools can report success for a multi-export Niagara package while
    # leaving its original byte-identical file behind in a commandlet. Remove
    # only that exact unreferenced, task-owned file after the verified backup.
    if path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Unexpected package write during deletion: '+package
        assert path.resolve().is_relative_to(DIR.resolve())
        path.unlink()
    assert not path.exists(),package
    row['disk_file_removed']=True
    row['deleted']=True;rows.append(row)
report={'scope':'Only task-generated unused trial systems and explicit QA graphs; active TwoLayers system retained.',
        'map_saved':False,'rows':rows}
report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('KZ_HEINMACH_UNUSED_TRIALS_CLEANED')
