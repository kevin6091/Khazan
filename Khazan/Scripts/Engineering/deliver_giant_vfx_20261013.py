"""Scoped compare-and-swap delivery; no stale private DLL or manifest copying."""
from pathlib import Path
import json,hashlib,shutil,sys,datetime
main=Path(__file__).resolve().parents[2];work=main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan';out=main/'Metadata/GiantVFX_20261013'
mode=sys.argv[1];assert mode in ['plan','apply']
baseline=json.loads((out/'Baseline.json').read_text(encoding='utf-8'))
ownership=json.loads((out/'AnimationOwnership.json').read_text(encoding='utf-8'))
audit=json.loads((out/'WorkAuditFinal03/SavedAudit.json').read_text(encoding='utf-8'))
assert json.loads((out/'WorkAuditFinal03/Preservation.json').read_text(encoding='utf-8'))['status']=='passed'
author=json.loads((out/'AssetAuthor02/Author.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative_asset(path):return 'Content/'+path.split('.',1)[0].removeprefix('/Game/')+'.uasset'
original=dict(baseline.get('asset_sha256',baseline.get('assets',{})));original.update(ownership['files'])
source=baseline['source_sha256']
# A separate, completed task added the Main modular secondary-physics block.
# Permit only the reviewed one-line VFX delta against that latest Main source.
monster_path='Source/Khazan/Character/KZMonster.cpp'
old='Transform.SetScale3D(Effect->Scale3D * PoseMesh->GetComponentScale().GetAbs());'
new='Transform.SetScale3D(Effect->Scale3D * (Effect->bUseWorldParticleUnits ? FVector::OneVector : PoseMesh->GetComponentScale().GetAbs()));'
current=(main/monster_path).read_text(encoding='utf-8-sig');candidate=(work/monster_path).read_text(encoding='utf-8-sig')
assert current.count(old)==1 and candidate.count(new)==1
# The private VFX module was built before the separately completed physics
# work. Preserve the latest Main initialization and stage only this VFX line.
merged=out/'MergedSource/Source/Khazan/Character/KZMonster.cpp'
merged.parent.mkdir(parents=True,exist_ok=True);merged.write_text(current.replace(old,new),encoding='utf-8')
source_override={monster_path:sha(main/monster_path)}
changed_source=[p for p,h in source.items() if (work/p).is_file() and sha(work/p)!=h]
assert set(changed_source)=={
 'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h','Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp',
 'Source/Khazan/Animation/Notifies/KZAnimNotifyState_MonsterVisual.cpp','Source/Khazan/Character/KZMonster.cpp',
 'Source/Khazan/Ability/Combo/KZComboDefinitionData.h','Source/Khazan/Ability/MonsterAbility/KZMonsterSkillObject.h',
 'Source/Khazan/Ability/MonsterAbility/KZMonsterSkillObject.cpp','Source/Khazan/Tests/KZMonsterPresentationRepairPIETest.cpp'},changed_source
assets=[relative_asset(p) for p in author['changed_sequences']]
assets += ['Content/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family+'.uasset' for family in ['ApesStoneHandElite','Yetuga']]
new_assets=[relative_asset(p) for p in audit['owned_dependencies']]
rows=[]
for p in changed_source+assets+new_assets:
    target=main/p;owned=merged if p==monster_path else work/p
    assert owned.is_file() and (owned.resolve().is_relative_to(work) or owned==merged)
    expected=source_override.get(p,source[p]) if p in changed_source else original.get(p)
    if p in new_assets:assert not target.exists(),p
    else:assert expected and target.is_file() and sha(target)==expected,('Main changed since snapshot; preserve and merge',p)
    rows.append({'relative':p,'before_sha256':expected,'after_sha256':sha(owned)})
plan={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_count':len(changed_source),'changed_assets':len(assets),'new_assets':len(new_assets),'files':rows}
if mode=='plan':
    (out/'DeliveryPlan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in plan.items() if k!='files'}));sys.exit(0)
quality=json.loads((out/'WorkFocusFinal03/Driver.json').read_text(encoding='utf-8'));assert quality['status']=='passed' and not quality['material_compile_failures']
patterns=json.loads((out/'WorkPatternsFinal01/Driver.json').read_text(encoding='utf-8'));assert patterns['status']=='passed'
assert json.loads((out/'PrivateVisualReview.json').read_text(encoding='utf-8'))['status']=='accepted_with_documented_limits'
for label in ['WorkFocusFinal03','WorkPatternsFinal01']:
    assert json.loads((out/label/'Exit.json').read_text(encoding='utf-8'))['input_unchanged']
backup=out/'MainDeliveryBackup';assert not backup.exists();backup.mkdir()
# Preserve a receipt of all latest Main sources; only the eight selected paths
# are copied, so independently added tests/character changes stay in place.
plan['main_source_intake']={str(p.relative_to(main)).replace('\\','/'):sha(p) for p in (main/'Source').rglob('*') if p.is_file()}
for row in rows:
    p=row['relative'];target=main/p
    if target.exists():
        saved=backup/p;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(merged if p==monster_path else work/p,target)
    if p.startswith('Source/'):target.touch() # UHT must see imported changes after its last successful run.
    assert sha(target)==row['after_sha256']
plan['status']='applied_pending_main_build_and_validation'
(out/'MainDelivery.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in plan.items() if k not in ['files','main_source_intake']}))
