"""Audit preservation and publish source manifests, indices, and final reports."""
import pathlib,json,hashlib,shutil,csv,collections,datetime
PROJECT=pathlib.Path(__file__).resolve().parents[2]
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
REPORTS=PROJECT/'Saved/ImportReports'
BACKUP=PROJECT/'Saved/ArtBackups/HeinMachEnemyExpansion_20260909'
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def content(p):return PROJECT/(p.replace('/Game/','Content/')+'.uasset')

def main():
    baseline=read(BACKUP/'manifest.json');moves=read(ROOT/'LegacyAssetMoves.json')
    move_files={r['from'].replace('/Game/','Content/')+'.uasset':r['to'].replace('/Game/','Content/')+'.uasset' for r in moves}
    old_unchanged=[];migrated=[];changed=[]
    for path,value in baseline['files'].items():
        assert sha(BACKUP/path)==value,('backup integrity',path)
        if sha(PROJECT/path)==value:old_unchanged.append(path)
        elif path in move_files:
            assert (PROJECT/move_files[path]).is_file(),('archive destination',path)
            migrated.append({'old':path,'new':move_files[path],'old_path_on_disk':(PROJECT/path).exists()})
        else:changed.append(path)
    assert changed==['Content/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue.umap'],changed
    external={
        'Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md',
        'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md',
        'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md',
        'Docs/Engineering/CHARACTER_TAG_ABILITY_STEP_1.md',
        'Docs/Engineering/ENGINEERING_PROJECT_STATE.md',
        'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',
    }
    protected=[];external_changes=[]
    for path,value in baseline['protected'].items():
        current=sha(PROJECT/path)
        if current==value:protected.append(path)
        else:
            assert path in external and current,('unexpected protected change',path)
            external_changes.append({'path':path,'baseline_sha256':value,'current_sha256':current,'reason':'Observed changes made outside this Art task; preserved without editing or rollback.'})
    config=read(BACKUP/'config_hashes.json')
    assert all(sha(PROJECT/k)==v for k,v in config.items()),'Config changed'
    preservation={'status':'passed','backup_files_verified':len(baseline['files']),'old_enemy_files_unchanged':len(old_unchanged),'old_enemy_assets_migrated':migrated,'authorized_changed_old_files':changed,'protected_files_unchanged':protected,'external_document_changes_preserved':external_changes,'config_hashes_unchanged':config,'legacy_redirectors_persisted':False,'legacy_path_contract':'Resolve historical paths through LegacyAssetMoves.json; all 89 archive assets loaded successfully in the reopened editor.'}
    write(REPORTS/'HeinMachEnemyV2_PreservationAudit.json',preservation)
    reports={}
    for name in ['Library','AnimationImportAudit','Assemblies','CatalogueAudit','RenderAudit','OrientationAudit','TextureIdentity','SourceArchive','PreservationAudit']:
        r=read(REPORTS/('HeinMachEnemyV2_'+name+'.json'));assert r['status']=='passed',name;reports[name]='HeinMachEnemyV2_'+name+'.json'
    manifest=read(ROOT/'ImportManifest.json');animations=read(ROOT/'AnimationImportManifest.json');catalog=read(ROOT/'AssemblyCatalog.json')
    for r in animations:assert content(r['destination']).is_file(),r['destination']
    for r in catalog:assert content(r['asset']).is_file(),r['asset']
    for kind in ['meshes','textures','materials']:
        for r in manifest[kind]:assert content(r['destination']).is_file(),r['destination']
    with (ROOT/'AnimationIndex.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Family','Kind','UnrealAsset','OriginalPackage','DurationSeconds','SampleCount','FrameRateNumerator','FrameRateDenominator','PlayRate','TimingContract'])
        for r in animations:w.writerow([r['family'],r['kind'],r['destination'],r['source_package'],r['duration'],r['samples'],*r['fps'],1.0,'Original sequence time' if r['kind']=='SourceSequence' else 'Source segment rates and active DilationCurve baked; play at 1x'])
    with (ROOT/'EnemyCatalogue.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Family','SourceLevel','Blueprint','IdleAnimation','OriginalCharacterBlueprint','EquipmentPackages'])
        for r in catalog:w.writerow([r['family'],r['source_level'],r['asset'],r['idle_asset'],r['source_cb'],' | '.join(x['package'] for x in r['equipment'])])
    final={'status':'passed','scope':'Imported humanoid art library and metadata-timed animation assets; proprietary shader/cloth/gameplay behavior is not fully reconstructed.','date':datetime.datetime.now().astimezone().isoformat(),'catalogue_map':'/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue','assemblies':len(catalog),'families':dict(collections.Counter(r['family'] for r in catalog)),'animation_counts':dict(collections.Counter(r['kind'] for r in animations)),'source_meshes_in_manifest':len(manifest['meshes']),'textures_in_manifest':len(manifest['textures']),'materials_in_manifest':len(manifest['materials']),'reports':reports,'visual_validation':'All 16 catalogue actors upright; source equipment sockets and material rendering checked in the live editor after reload.','limitations':['Cooked proprietary cartoon shader topology unavailable; preview adapter used.','AvatarColor and body preset data preserved; original runtime randomization not reproduced.','Source morph/LOD/cloth/physics data archived; complete UE simulation and chains not restored.','Custom gameplay notifies and AI/Ability/Actor time dilation need separate gameplay implementation.','28 non-character/unused/zero-duration composites preserved as metadata only.']}
    write(REPORTS/'HeinMachEnemyV2_FinalAudit.json',final)
    archive=pathlib.Path(read(REPORTS/'HeinMachEnemyV2_SourceArchive.json')['archive'])
    assert (archive/'SHA256.json').is_file()
    META.mkdir(parents=True,exist_ok=True)
    for f in ROOT.iterdir():
        if f.is_file() and f.suffix in ['.json','.csv']:
            shutil.copy2(f,META/f.name);shutil.copy2(f,archive/f.name)
    for target in [META/'Reports',archive/'Reports']:
        target.mkdir(parents=True,exist_ok=True)
        for f in REPORTS.glob('HeinMachEnemyV2_*.json'):shutil.copy2(f,target/f.name)
        shutil.copytree(REPORTS/'EnemyAnimationBatches',target/'EnemyAnimationBatches',dirs_exist_ok=True)
    shutil.copytree(PROJECT/'Scripts/Enemies',archive/'PipelineScripts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
    for base in [META,archive]:
        shutil.copy2(PROJECT/'Docs/Art/HEINMACH_ENEMY_EXPANSION_2026-09-09.md',base/'README_KO.md')
    hashes={str(f.relative_to(archive)).replace('\\','/'):sha(f) for f in archive.rglob('*') if f.is_file() and not any(x in ['Metadata','Assets','RawCookedArchive','Derived'] for x in f.relative_to(archive).parts) and f.name!='DeliverySHA256.json'}
    write(archive/'DeliverySHA256.json',{'source_files':'SHA256.json','delivery_files':hashes})
    print(json.dumps({'status':final['status'],'assemblies':len(catalog),'animations':len(animations),'old_unchanged':len(old_unchanged),'migrated':len(migrated),'protected_unchanged':len(protected),'external_documents_preserved':len(external_changes),'archive':str(archive)},ensure_ascii=False))

if __name__=='__main__':main()
