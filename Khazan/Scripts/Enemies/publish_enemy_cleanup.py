"""Publish the current retained inventory without rewriting historical manifests."""
import pathlib,json,shutil,hashlib,re
PROJECT=pathlib.Path(__file__).resolve().parents[2];REPORTS=PROJECT/'Saved/ImportReports'
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata';OUT=META/'Cleanup_20260909'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    audit=read(REPORTS/'HeinMachEnemy_CleanupAudit_20260909.json');assert audit['status']=='passed'
    plan=read(REPORTS/'HeinMachEnemy_CleanupPlan_20260909.json');backup=read(REPORTS/'HeinMachEnemy_CleanupBackup_20260909.json')
    OUT.mkdir(parents=True,exist_ok=True)
    retained=[]
    for p in plan['keep']:
        rel=p.replace('/Game/','Content/')+('.umap' if p.endswith('L_HeinMach_EnemyCatalogue') else '.uasset')
        retained.append({'asset':p,'file':rel,'sha256':backup['retained_assets'][rel],'bytes':(PROJECT/rel).stat().st_size})
    write(OUT/'RetainedAssets.json',{'status':'current','counts':audit['counts_after'],'assets':retained,'usage':'Current inventory after user-requested cleanup; historical import manifests include intentionally removed assets.'})
    removed=[]
    for r in plan['candidates']:
        rel=r['asset'].replace('/Game/','Content/')+'.uasset'
        removed.append({k:v for k,v in r.items() if k!='referencers'}|{'sha256':backup['deleted_asset_candidates'][rel],'backup_file':str(pathlib.Path(backup['backup'])/rel)})
    write(OUT/'RemovedAssets.json',{'reason':'User requested removal of non-selected source/legacy characters; no retained or external package references.','backup':backup['backup'],'assets':removed})
    rows=plan['blueprints']
    for row in rows:
        for c in row['components'].values():
            for key in ['rotation','scale']:
                c[key]={k:float(v) for k,v in re.findall(r'\b(x|y|z|pitch|yaw|roll): (-?\d+(?:\.\d+)?)',c[key])}
    write(OUT/'BlueprintComponents.json',rows)
    for name in ['HeinMachEnemy_CleanupAudit_20260909.json','HeinMachEnemy_PlaybackComparison_20260909.json']:shutil.copy2(REPORTS/name,OUT/name)
    shutil.copy2(PROJECT/'Saved/Extracted/HeinMachEnemiesV2/PlaybackComparison.csv',OUT/'PlaybackComparison.csv')
    doc=PROJECT/'Docs/Art/ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md';shutil.copy2(doc,OUT/'README_KO.md')
    write(OUT/'RetentionPolicy.json',{'curated_blueprints':16,'animations_retained':1436,'animation_cleanup_deferred_by_user':True,'do_not_regenerate_removed_assets_without_user_request':True,'current_inventory':'RetainedAssets.json','deleted_inventory':'RemovedAssets.json','canonical_document':'Docs/Art/ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md'})
    archive=pathlib.Path(read(REPORTS/'HeinMachEnemyV2_SourceArchive.json')['archive'])
    shutil.copytree(OUT,archive/'Cleanup_20260909',dirs_exist_ok=True)
    shutil.copytree(PROJECT/'Scripts/Enemies',archive/'PipelineScripts',dirs_exist_ok=True,ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
    expanded=PROJECT/'Docs/Art/HEINMACH_ENEMY_EXPANSION_2026-09-09.md'
    shutil.copy2(expanded,META/'Expansion_20260909/README_KO.md');shutil.copy2(expanded,archive/'README_KO.md')
    delivery={str(f.relative_to(archive)).replace('\\','/'):sha(f) for f in archive.rglob('*') if f.is_file() and not any(x in ['Metadata','Assets','RawCookedArchive','Derived'] for x in f.relative_to(archive).parts) and f.name!='DeliverySHA256.json'}
    write(archive/'DeliverySHA256.json',{'source_files':'SHA256.json','delivery_files':delivery})
    print('PUBLISHED_ENEMY_CLEANUP',len(retained),'retained',len(removed),'removed')

if __name__=='__main__':main()
