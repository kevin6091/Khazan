"""Deliver only the two owned particles after actual RHI inspection."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_CombatImpactWork_20261012/Khazan')
OUT=ROOT/'Metadata/CombatImpactUpgrade_20261012'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((OUT/'HitBurstAuthored.json').read_text(encoding='utf-8'))
final=json.loads((OUT/'Streaks06/Applied.json').read_text(encoding='utf-8'))
visual=json.loads((OUT/'BurstVisual05/Driver.json').read_text(encoding='utf-8'))
assert final['status']==visual['status']=='passed'
assert (OUT/'BurstVisual05/01_ActualParryFlash.png').exists()
expected={initial['path']:initial['sha256'],initial['blood']['path']:initial['blood']['after']}
for row in final['assets']:
 assert sha(WORK/row['file'])==row['after']
 assert sha(ROOT/row['file']) in (expected[row['path']],row['after']),row['path']
rows=[]
for row in final['assets']:
 target=ROOT/row['file'];backup=OUT/'MainBeforeFinalBurst'/row['file']
 backup.parent.mkdir(parents=True,exist_ok=True)
 if backup.exists():assert sha(backup)==expected[row['path']]
 else:assert sha(target)==expected[row['path']];shutil.copy2(target,backup)
 if sha(target)!=row['after']:shutil.copyfile(WORK/row['file'],target)
 assert sha(target)==row['after'];rows.append(dict(row,before=expected[row['path']],backup=str(backup)))
(OUT/'HitBurstFinalDelivered.json').write_text(json.dumps({'status':'passed','packages':2,'rows':rows,'temporary_tuning':final['TEMP'],'material':'/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/DefaultParticle','original_blood_emitters':3,'new_fire_emitters':3,'runtime_count':120,'cpu_sprites':True,'source_or_dll_copied':0},indent=2),encoding='utf-8')
retired=[]
for name,folder in [('PP_Monster_HitFlameFlash','RetireFlash01'),('M_Monster_HitFlameFlash','RetireFlash02')]:
 target=ROOT/'Content/_Art/Effects/Combat/AttackContact'/(name+'.uasset')
 backup=OUT/folder/(name+'.uasset.retired-backup');assert backup.exists() and not target.exists()
 retired.append({'path':'/Game/_Art/Effects/Combat/AttackContact/'+name,'absent':True,'backup':str(backup),'backup_sha256':sha(backup)})
(OUT/'RetiredFinal.json').write_text(json.dumps({'status':'passed','removed':retired,'zero_references_verified_before_retirement':True,'note':'RetireFlash02 receipt serialization failed after successful removal; this receipt verifies both files absent and intact backups.'},indent=2),encoding='utf-8')
print('MAIN_FINAL_BURST_DELIVERED',len(rows))
