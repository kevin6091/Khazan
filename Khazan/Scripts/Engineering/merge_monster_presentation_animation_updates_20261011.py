"""Stage latest concurrent animation/audio assets, then reapply only our decal suppression."""
from pathlib import Path
import json,hashlib,shutil
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan');ROOT=MAIN/'Metadata/MonsterPresentationRepair_20261011'
plan=json.loads((ROOT/'DeliveryPreparation/Plan.json').read_text(encoding='utf-8'))
out=ROOT/'AnimationMergeBackups';out.mkdir(exist_ok=False)
rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for row in plan['conflicts']:
    rel=row['path'];assert rel.startswith('Content/_Art/Enemies/') and '/Animations/' in rel and row['reason']=='Concurrent asset change',row
    src=MAIN/rel;dest=WORK/rel;assert sha(src)==row['current'],rel
    backup=out/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
    shutil.copy2(src,dest);assert sha(src)==sha(dest)==row['current'],rel
    rows.append({'path':rel,'initial_baseline':row['baseline'],'merge_baseline':row['current'],'private_before':sha(backup)})
dependencies=0
for src in (MAIN/'Content/Audio').rglob('*'):
    if src.is_file():
        dest=WORK/src.relative_to(MAIN);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);dependencies+=1
receipt={'status':'stagedLatestConcurrentAnimations','animations':rows,'audio_dependencies':dependencies,'main_game_files_written':0,'next':'Reapply only blood decal Effect None; verify saved Notify census before Main delivery.'}
(ROOT/'ConcurrentAnimationMerge.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'animations':len(rows),'audio_dependencies':dependencies,'main_game_files_written':0}))
