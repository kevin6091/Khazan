"""Prepare a reviewed, CAS guarded Main delivery; preserve concurrent source edits."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, subprocess
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
ROOT=MAIN/'Metadata/MonsterPresentationRepair_20261011'
BASE=json.loads((ROOT/'Baseline.json').read_text(encoding='utf-8'))['files']
MERGED={r['path']:r['merge_baseline'] for r in json.loads((ROOT/'ConcurrentAnimationMerge.json').read_text(encoding='utf-8'))['animations']} if (ROOT/'ConcurrentAnimationMerge.json').exists() else {}
OUT=ROOT/'DeliveryPreparation';OUT.mkdir(exist_ok=True)
FILES=['Character/KZMonster.h','Character/KZMonster.cpp','UI/KZCombatHUDWidget.h','UI/KZCombatHUDWidget.cpp','Ability/Combo/KZComboActionAbility.cpp','Ability/PlayerAbility/KZBrutalAttackAbility.cpp','Tests/KZCombatUIPIEEditor.cpp','Tests/KZPlayerAttackCollisionPIETest.cpp','Tests/KZMonsterPresentationRepairPIETest.cpp','Khazan.Build.cs']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
plan={'utc':datetime.now(timezone.utc).isoformat(),'status':'prepared','source':[],'assets':[],'conflicts':[]}
patch=[]
for suffix in FILES:
    rel='Source/Khazan/'+suffix;main=MAIN/rel;work=WORK/rel;base=ROOT/'WorkSourceBefore/Khazan'/suffix
    target=OUT/'Staged'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    current=main.read_bytes() if main.exists() else b''
    if suffix=='Khazan.Build.cs':
        needle='if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("Json"); // Native PIE report serialization only.'
        text=current.decode('utf-8-sig');assert needle in text
        merged=text.replace(needle,'if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new string[] { "Json", "UnrealEd" }); // Owned native PIE QA and reports only.').encode('utf-8')
    elif suffix=='Ability/Combo/KZComboActionAbility.cpp':
        text=main.read_text(encoding='utf-8-sig');needle='\t\t\t\t\tRecipient->PlayHitReaction(Window.HitReaction, Avatar);'
        assert text.count(needle)==1
        merged=text.replace(needle,'\t\t\t\t\tif (AKZMonster* Victim = Cast<AKZMonster>(Recipient)) Victim->PlayHitBlood(Avatar, Center);\n'+needle).encode('utf-8')
        # Only our accepted-hit call is added; all newer Main impact/body sound behavior is retained.
    elif suffix=='Ability/PlayerAbility/KZBrutalAttackAbility.cpp':
        text=main.read_text(encoding='utf-8-sig');needle='\t\t\t// Presentation adapter: only this existing accepted negative-HP producer'
        assert text.count(needle)==1
        merged=text.replace(needle,'\t\t\tMonster->PlayHitBlood(GetAvatarActorFromActorInfo(), Monster->GetMesh()->GetSocketLocation(Monster->CombatReticleSocket));\n'+needle).encode('utf-8')
    elif sha(main)==BASE.get(rel) and main.exists():
        merged=work.read_bytes()
    elif not base.exists():
        assert rel not in BASE and not main.exists(),rel
        merged=work.read_bytes()
    else:
        assert sha(base)==BASE[rel],('Backup not baseline',rel)
        normalized=[]
        for label,p in [('main',main),('base',base),('work',work)]:
            q=OUT/(label+'_'+suffix.replace('/','_'))
            q.write_text(p.read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n');normalized.append(str(q))
        result=subprocess.run(['git','merge-file','-p',*normalized],capture_output=True)
        if result.returncode:
            plan['conflicts'].append({'path':rel,'exit':result.returncode,'stderr':result.stderr.decode(errors='replace')});continue
        merged=result.stdout
    text=merged.decode('utf-8-sig').replace('\r\n','\n')
    if current.count(b'\r\n')>current.count(b'\n')*.5:text=text.replace('\n','\r\n')
    merged=(b'\xef\xbb\xbf' if current.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    target.write_bytes(merged)
    patch.extend(difflib.unified_diff(current.decode('utf-8-sig').splitlines(True),merged.decode('utf-8-sig').splitlines(True),fromfile=rel,tofile=rel))
    plan['source'].append({'path':rel,'before':sha(main),'after':sha(target),'concurrent_before':sha(main)!=BASE.get(rel)})
for package in json.loads((ROOT/'AssetSelection.json').read_text(encoding='utf-8'))['packages']:
    rel='Content/'+package.removeprefix('/Game/')+'.uasset'
    before=sha(MAIN/rel)
    if before!=MERGED.get(rel,BASE.get(rel)):plan['conflicts'].append({'path':rel,'reason':'Concurrent asset change','baseline':BASE.get(rel),'current':before});continue
    assert (WORK/rel).is_file(),rel
    plan['assets'].append({'path':rel,'before':before,'after':sha(WORK/rel),'concurrent_animation_preserved':rel in MERGED})
plan['status']='conflicted' if plan['conflicts'] else 'prepared'
(OUT/'Source.diff').write_text(''.join(patch),encoding='utf-8')
(OUT/'Plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in plan.items()},ensure_ascii=False))
