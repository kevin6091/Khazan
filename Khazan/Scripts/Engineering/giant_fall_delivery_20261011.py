"""Only this task's exact paths. Snapshot/CAS and byte backups; no whole-tree delivery."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil

WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan').resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT=WORK/'Metadata/GiantCombatFall_20261011'
SOURCE=[
 'Ability/KZAbilitySystemComponent.cpp','Ability/Combo/KZComboActionAbility.h','Ability/Combo/KZComboActionAbility.cpp',
 'Ability/Combo/KZComboDefinitionData.h','Data/KZCharacterDefinitionData.h','Data/KZCharacterDefinitionData.cpp',
 'AI/KZMonsterAIController.h','AI/KZMonsterAIController.cpp','AI/KZMonsterStateTreeNodes.cpp',
 'Character/KZMonster.h','Character/KZMonster.cpp','Character/KZPlayer.h','Character/KZPlayer.cpp',
 'Ability/MonsterAbility/KZMonsterPatternAbility.h','Ability/MonsterAbility/KZMonsterPatternAbility.cpp',
 'Ability/MonsterAbility/KZMonsterSkillObject.h','Ability/MonsterAbility/KZMonsterSkillObject.cpp',
 'Ability/PlayerAbility/KZFallAbility.h','Ability/PlayerAbility/KZFallAbility.cpp','Tests/KZGiantFallPIETest.cpp'
]
SCRIPTS=['giant_fall_plan_20261011.py','GiantFallAuthorEditor.cpp','giant_fall_pie_20261011.py',
         'giant_fall_delivery_20261011.py','giant_fall_saved_audit_20261011.py']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def save(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def paths():
 report=json.loads((OUT/'AuthoringReport.json').read_text(encoding='utf-8'))
 assets={'Content/'+p.removeprefix('/Game/')+'.uasset' for p in report['saved_packages']}
 assets.add('Content/Maps/DevMap.umap')
 result=['Source/Khazan/'+p for p in SOURCE]+sorted(assets)
 result+=['Scripts/Engineering/'+p for p in SCRIPTS if (WORK/'Scripts/Engineering'/p).exists()]
 metadata=['AuthoringPlan.json','AuthoringReport.json','OwnedSourceDiff.patch','ObjectSourceTargeted.json','CommonCurveTargets.json','SavedAssetAudit.json',
           'BaselineHashes.json','MainConcurrentChanges.json','PIEResult.json','PIEDriver.json']
 metadata += [p.relative_to(OUT).as_posix() for p in (OUT/'OriginalCommonCurves').rglob('*.json')]
 metadata += [p.name for p in OUT.glob('Fall*.png')]
 metadata += [p.name for p in OUT.glob('WorkBuild*.log')]+[p.name for p in OUT.glob('PrivatePIE*.log')]+[p.name for p in OUT.glob('Author*.log')]
 metadata += [p.name for p in OUT.glob('SavedAudit*.log')]
 result+=['Metadata/GiantCombatFall_20261011/'+p for p in metadata]
 for p in result:
  assert (MAIN/p).resolve().is_relative_to(MAIN) and (WORK/p).resolve().is_relative_to(WORK),p
  assert (WORK/p).is_file(),p
 return result
args=argparse.ArgumentParser();args.add_argument('--deliver',action='store_true');a=args.parse_args()
if not a.deliver:
 baseline={r['path']:r['sha256'] for r in json.loads((OUT/'BaselineHashes.json').read_text(encoding='utf-8-sig'))}
 concurrent={r['path']:r['main_sha256'] for r in json.loads((OUT/'MainConcurrentChanges.json').read_text(encoding='utf-8-sig'))}
 rows=[]
 for p in paths():
  current=sha(MAIN/p); expected=concurrent.get(p,baseline.get(p)); kind='baseline-or-merged-latest'
  if current!=expected:
   # ABP_Player was not in the narrow initial hash inventory; Main timestamp predates this work.
   if p=='Content/_Art/Player/Character/Bluprints/ABP_Player.uasset' and current=='0ad4b8e25a4124b8523116f258f63c5b085cf2654616d620377cb5974a3d5f28' and (MAIN/p).stat().st_mtime<1791633600:
    kind='uncaptured-original-player-abp; pre-work timestamp and current exact backup'
   elif p.startswith('Scripts/Engineering/') or p.startswith('Metadata/GiantCombatFall_20261011/'):
    kind='task-owned-tool/report snapshot'
   else:raise RuntimeError('Unmerged concurrent Main change: '+p)
  rows.append({'path':p,'before':current,'after':sha(WORK/p),'intake':kind})
 save('DeliveryPrepared.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main':str(MAIN),'work':str(WORK),'files':rows})
 print(json.dumps({'status':'PreparedOnly','files':len(rows),'assets':sum(r['path'].startswith('Content/') for r in rows)}))
else:
 result=json.loads((OUT/'PIEResult.json').read_text(encoding='utf-8'))
 assert result['passed'] and result['pattern_cases']==8,'Latest full native PIE must pass before delivery'
 assert json.loads((OUT/'SavedAssetAudit.json').read_text(encoding='utf-8'))['passed'],'Cold saved-package readback must pass'
 prepared=json.loads((OUT/'DeliveryPrepared.json').read_text(encoding='utf-8'))
 rows=prepared['files'];assert {r['path'] for r in rows}==set(paths()),'Asset/source selection changed; prepare again'
 for r in rows:
  assert sha(MAIN/r['path'])==r['before'],'Concurrent Main change: '+r['path']
  assert sha(WORK/r['path'])==r['after'],'Work changed after prepare: '+r['path']
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 backup=MAIN/'Saved/GiantFallBackup_20261011'/stamp
 assert backup.resolve().is_relative_to(MAIN/'Saved')
 for r in rows:
  p=r['path'];target=MAIN/p;target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():
   old=backup/p;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
  temporary=target.with_name(target.name+'.giantfall.tmp')
  shutil.copy2(WORK/p,temporary);temporary.replace(target)
  assert sha(target)==r['after'],p
 receipt={'status':'DeliveredNeedsFreshMainBuildAndReadback','backup':str(backup),'prepared':sha(OUT/'DeliveryPrepared.json'),'files':rows}
 save('DeliveryReceipt.json',receipt)
 destination=MAIN/'Metadata/GiantCombatFall_20261011';destination.mkdir(parents=True,exist_ok=True)
 for name in ['DeliveryPrepared.json','DeliveryReceipt.json']:shutil.copy2(OUT/name,destination/name)
 print(json.dumps({'status':receipt['status'],'files':len(rows),'backup':str(backup)}))
