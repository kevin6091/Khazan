"""Preserve cooked originals and portable source metadata for this extraction."""
import pathlib,json,runpy,shutil,hashlib
D=runpy.run_path(str(pathlib.Path(__file__).with_name('discover_enemy_expansion.py')))
P=runpy.run_path(str(pathlib.Path(__file__).with_name('prepare_enemy_expansion.py')))
ROOT=D['ROOT'];OLD=D['OLD'];PROJECT=D['PROJECT'];read=D['read'];write=D['write']
def main():
    closure=read(ROOT/'SourceClosure.json');raw=ROOT/'RawCookedArchive';needed=[]
    for p in closure['packages']:
        target=raw/(p+'.uasset')
        if target.exists():continue
        previous=OLD/'RawCookedArchive'/(p+'.uasset')
        if previous.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            for ext in ['.uasset','.uexp','.ubulk','.uptnl']:
                f=previous.with_suffix(ext)
                if f.exists():shutil.copy2(f,target.with_suffix(ext))
        else:needed.append(p)
    if needed:P['run']('raw',raw,needed,'RawCookedExport')
    missing=[p for p in closure['packages'] if not (raw/(p+'.uasset')).exists()]
    assert not missing,missing
    out=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909';out.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'Metadata',out/'Source',dirs_exist_ok=True)
    for name in ['HumanCBRequests.json','HumanSourceInventory.json','SourceClosure.json','ImportManifest.json','CombinedMeshManifest.json','AnimationImportManifest.json','AnimationTimingAudit.json','UnselectedAnimationInputs.json']:
        shutil.copy2(ROOT/name,out/name)
    archive=pathlib.Path.home()/'Desktop'/'\uce74\uc794'/'EnemyExtracts'/'HumanoidExpansion_20260909'
    archive.mkdir(parents=True,exist_ok=True)
    for name in ['Metadata','Assets','RawCookedArchive','Derived']:
        shutil.copytree(ROOT/name,archive/name,dirs_exist_ok=True)
    for f in ROOT.glob('*.json'):shutil.copy2(f,archive/f.name)
    hashes={str(f.relative_to(archive)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ['Metadata','Assets','RawCookedArchive','Derived'] for f in (archive/folder).rglob('*') if f.is_file()}
    write(archive/'SHA256.json',hashes)
    result={'status':'passed','archive':str(archive),'source_packages':len(closure['packages']),'raw_packages_verified':len(closure['packages']),'source_files_hashed':len(hashes),'archive_bytes':sum(f.stat().st_size for f in archive.rglob('*') if f.is_file()),'metadata_in_project':str(out),'missing_original_references':closure['missing']}
    write(PROJECT/'Saved/ImportReports/HeinMachEnemyV2_SourceArchive.json',result);print(result)
if __name__=='__main__':main()
