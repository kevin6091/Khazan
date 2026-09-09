"""Back up the exact unused-asset deletion plan and hash all retained assets."""
import pathlib,json,hashlib,shutil,subprocess,datetime
PROJECT=pathlib.Path(__file__).resolve().parents[2]
PLAN=PROJECT/'Saved/ImportReports/HeinMachEnemy_CleanupPlan_20260909.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def file(p):return PROJECT/(p.replace('/Game/','Content/')+('.umap' if p.endswith('L_HeinMach_EnemyCatalogue') else '.uasset'))

def main():
    plan=read(PLAN);assert plan['status']=='planned'
    backup=pathlib.Path.home()/'Desktop'/'\uce74\uc794'/'EnemyExtracts'/'ProjectCleanup_20260909'
    assert not (backup/'BackupManifest.json').exists(),'Existing baseline must not be overwritten'
    backup.mkdir(parents=True,exist_ok=True)
    root=(PROJECT/'Content/_Art/Enemies').resolve()
    deleted={};retained={}
    for r in plan['candidates']:
        f=file(r['asset']).resolve();assert f.is_relative_to(root)
        key=str(f.relative_to(PROJECT)).replace('\\','/');target=backup/key;target.parent.mkdir(parents=True,exist_ok=True)
        value=sha(f);shutil.copy2(f,target);assert sha(target)==value;deleted[key]=value
    for p in plan['keep']:
        f=file(p);retained[str(f.relative_to(PROJECT)).replace('\\','/')]=sha(f)
    doc_own={'Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_PIPELINE_RULES.md','Docs/Art/ART_KNOWLEDGE_INDEX.md','Docs/Art/ART_WORK_CONTINUITY.md','Docs/Art/HEINMACH_ENEMY_EXTRACTION_2026-09-08.md','Docs/Art/HEINMACH_ENEMY_EXPANSION_2026-09-09.md'}
    names=subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z','--','.'],cwd=PROJECT).decode('utf-8').split('\0')
    protected={}
    for n in set(names):
        if not n or n.startswith(('Content/_Art/Enemies/','Scripts/Enemies/')) or n in doc_own:continue
        f=PROJECT/n
        if f.is_file():protected[n]=sha(f)
    for n in ['Content/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment.umap','Content/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment.umap']:
        protected[n]=sha(PROJECT/n)
    out={'date':datetime.datetime.now().astimezone().isoformat(),'backup':str(backup),'deleted_asset_candidates':deleted,'retained_assets':retained,'protected_worktree_files':protected,'plan_sha256':sha(PLAN)}
    (backup/'BackupManifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    shutil.copy2(PLAN,backup/PLAN.name)
    (PROJECT/'Saved/ImportReports/HeinMachEnemy_CleanupBackup_20260909.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    print('CLEANUP_BACKUP_VERIFIED',len(deleted),'assets;',len(retained),'retained hashes;',len(protected),'protected files;',backup)

if __name__=='__main__':main()
