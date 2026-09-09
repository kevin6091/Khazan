"""Preserve extraction outputs under the established FModel export root.

No game key is copied. Source package paths are retained below each format root.
This only copies this task's outputs and never mirrors/deletes destination files.
"""
import pathlib,json,shutil,hashlib,datetime,collections
PROJECT=pathlib.Path(__file__).resolve().parents[2]
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemies'
DEST=pathlib.Path.home()/'Desktop'/'\uce74\uc794'/'EnemyExtracts/HeinMach_20260908'
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def main():
    counts={};hashes={}
    for name in ['Assets','Animation','Metadata','RawCookedArchive','Derived']:
        shutil.copytree(ROOT/name,DEST/name,dirs_exist_ok=True)
        files=[p for p in (ROOT/name).rglob('*') if p.is_file()]
        counts[name]={'files':len(files),'bytes':sum(p.stat().st_size for p in files)}
        for p in files:
            rel=p.relative_to(ROOT).as_posix();a=hashlib.sha256(p.read_bytes()).hexdigest()
            if a!=hashlib.sha256((DEST/rel).read_bytes()).hexdigest():raise RuntimeError('Copy hash '+rel)
            hashes[rel]=a
    shutil.copytree(ROOT/'Metadata',META/'Source',dirs_exist_ok=True)
    for n in ['SourceSpawnActors.json','SourceClosure.json','VisualRecipes.json','TargetedPackageIndex.json','ArtExportRequests.json','IdleAnimationRequests.json']:
        shutil.copy2(ROOT/n,DEST/n);shutil.copy2(ROOT/n,META/n)
    manifest=read(META/'EnemyImportManifest.json')
    closure=read(ROOT/'SourceClosure.json')
    exports=read(ROOT/'Assets/ExportReport.json');anims=read(ROOT/'Animation/ExportReport.json');raw=read(ROOT/'RawCookedArchive/ExportReport.json')
    if any(not r['Success'] for r in exports+anims+raw):raise RuntimeError('Unsuccessful source export')
    # Identify the installed original version without recording the AES key.
    config=read(pathlib.Path.home()/'AppData/Roaming/FModel/AppSettings.json')
    paks=pathlib.Path(config['GameDirectory'])/'Content/Paks'
    snapshot=[{'file':p.name,'bytes':p.stat().st_size,'mtime_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()} for p in sorted(paks.iterdir()) if p.suffix in {'.pak','.ucas','.utoc'}]
    native=PROJECT/'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/CUE4Parse-Natives.dll'
    combined=read(META/'CombinedMeshManifest.json')
    report={'status':'passed','source_archive':str(DEST),'work_archive':str(ROOT),'selected_dependency_packages':len(closure['packages']),'missing_dependencies':closure['missing'],'art_exports_succeeded':len(exports),'idle_exports_succeeded':len(anims),'raw_packages_succeeded':len(raw),'archive_counts':counts,'source_snapshot':snapshot,'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'source_mesh_assets':len(manifest['meshes']),'combined_body_meshes':len(combined),'source_materials':len(manifest['materials']),'textures':len(manifest['textures']),'actorx_source_mesh_lod_files':len(list((ROOT/'Assets').rglob('*.psk'))),'source_morph_records':sum(len(r['morph_targets']) for r in manifest['meshes']),'hash_manifest':'SourceFileHashes.json'}
    write(ROOT/'SourceFileHashes.json',hashes);write(DEST/'SourceFileHashes.json',hashes);write(META/'SourceFileHashes.json',hashes)
    for p in [ROOT/'FinalExtractionReport.json',DEST/'FinalExtractionReport.json',META/'FinalExtractionReport.json',PROJECT/'Saved/ImportReports/HeinMachEnemy_SourceExtraction.json']:write(p,report)
    for name in ['EnemyImportManifest.json','CombinedMeshManifest.json','EnemyAssemblyCatalog.json']:
        shutil.copy2(META/name,DEST/name)
    (DEST/'Reports').mkdir(exist_ok=True);(META/'Reports').mkdir(exist_ok=True)
    for p in (PROJECT/'Saved/ImportReports').glob('HeinMachEnemy_*.json'):
        shutil.copy2(p,DEST/'Reports'/p.name);shutil.copy2(p,META/'Reports'/p.name)
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_snapshot']},ensure_ascii=False))
if __name__=='__main__':main()
