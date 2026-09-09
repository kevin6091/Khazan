"""Sequential bounded Editor processes; checkpointed reports make retries safe."""
import pathlib,subprocess,json,sys,time
PROJECT=pathlib.Path(__file__).resolve().parents[2];ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
ENGINE=pathlib.Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
rows=json.loads((ROOT/'AnimationImportManifest.json').read_text(encoding='utf-8'))
limit=int(sys.argv[1]) if len(sys.argv)>1 else len(rows);batch=75
summary=[]
for start in range(0,min(limit,len(rows)),batch):
    count=min(batch,len(rows)-start,limit-start);report=PROJECT/'Saved/ImportReports/EnemyAnimationBatches'/('%04d.json'%start)
    prior=json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    if prior.get('status')=='passed' and len(prior.get('assets',[]))==count:summary.append(prior);continue
    log=PROJECT/'Saved/Logs'/('EnemyAnimations_%04d.log'%start)
    args=[str(ENGINE),str(PROJECT/'Khazan.uproject'),'-run=pythonscript','-script='+str(PROJECT/'Scripts/Enemies/import_enemy_expansion_animations.py'),'-EnemyStart='+str(start),'-EnemyCount='+str(count),'-unattended','-nullrhi','-nosound','-nosplash','-NoSourceControl','-abslog='+str(log)]
    with log.with_suffix('.stdout.txt').open('w',encoding='utf-8') as output:
        result=subprocess.run(args,stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    data=json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    if result.returncode or data.get('status')!='passed' or len(data.get('assets',[]))!=count:
        print('BATCH_FAILED',start,'exit',result.returncode,data.get('error'),flush=True);sys.exit(1)
    summary.append(data);print('BATCH_PASSED',start,count,'total',sum(len(s['assets']) for s in summary),'/',len(rows),flush=True)
if limit>=len(rows):
    assets=[r for b in summary for r in b['assets']]
    result={'status':'passed','assets':len(assets),'source_sequences':sum(r['kind']=='SourceSequence' for r in assets),'playback_clips':sum(r['kind']=='PlaybackClip' for r in assets),'maximum_duration_error_seconds':max(r['duration_error_seconds'] for r in assets),'maximum_pose_errors': [max(r['max_pose_errors_position_cm_quat_component_scale'][i] for r in assets) for i in range(3)],'batch_reports':[str(PROJECT/'Saved/ImportReports/EnemyAnimationBatches'/('%04d.json'%b['start'])) for b in summary]}
    (PROJECT/'Saved/ImportReports/HeinMachEnemyV2_AnimationImportAudit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result,flush=True)
