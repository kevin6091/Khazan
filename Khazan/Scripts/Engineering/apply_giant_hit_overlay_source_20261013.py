from pathlib import Path
import json,hashlib,shutil
m=Path(__file__).resolve().parents[2];o=m/'Metadata/GiantHitOverlay_20261013';receipt={}
def edit(relative,pairs):
 p=m/relative;b=p.read_bytes();s=b.decode('utf-8-sig');newline='\r\n' if b'\r\n' in b else '\n';s=s.replace('\r\n','\n')
 backup=o/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();backup.write_bytes(b)
 for a,c in pairs:
  assert s.count(a)==1,(relative,a[:70],s.count(a));s=s.replace(a,c,1)
 assert p.read_bytes()==b,'Concurrent edit: '+relative
 p.write_bytes(s.replace('\n',newline).encode('utf-8'))
 receipt[relative]={'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
edit('Source/Khazan/Data/KZCharacterDefinitionData.h',[(
 '\tTArray<TObjectPtr<class UAnimMontage>> ShortHits;',
 '\tTArray<TObjectPtr<class UAnimMontage>> ShortHits;\n\t// Nonempty: ordinary hits use additive presentation only, never the blocking Hit Ability.\n\t// Author no-root-motion local-space additive montages in KZHitReactionGroup/KZHitReaction.\n\tUPROPERTY(EditAnywhere, Category = "Reaction|Additive")\n\tTArray<TObjectPtr<UAnimMontage>> AdditiveHits;')])
edit('Source/Khazan/Character/KZCharacter.h',[
 ('class UKZAttributeSet;','class UKZAttributeSet;\nclass UAnimInstance;\nclass UAnimMontage;'),
 ('// Called only after an accepted damage result; direction is selected by the Ability\'s pool.', '// Called only after an accepted damage result; the Definition selects blocking/additive presentation.'),
 ('\tvirtual void BeginPlay() override;','\tvirtual void BeginPlay() override;\n\t// Stops only the owned additive instance; does not touch action/Exhaustion montages.\n\tvoid StopAdditiveHitReaction();'),
 ('\tTObjectPtr<UKZAttributeSet> AttributeSet;','\tTObjectPtr<UKZAttributeSet> AttributeSet;\n\t// Presentation receipts, not gameplay state; finished engine instances are harmless stale IDs.\n\tTWeakObjectPtr<UAnimInstance> AdditiveHitAnim;\n\tTWeakObjectPtr<UAnimMontage> AdditiveHitMontage;\n\tint32 AdditiveHitInstanceId = INDEX_NONE;')])
edit('Source/Khazan/Character/KZCharacter.cpp',[
 ('#include "KZCharacter.h"','#include "KZCharacter.h"\n#include "Animation/AnimInstance.h"\n#include "Animation/AnimMontage.h"'),
 ('void AKZCharacter::UnPossessed()\n{','void AKZCharacter::UnPossessed()\n{\n\tStopAdditiveHitReaction();'),
 ('void AKZCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)\n{','void AKZCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)\n{\n\tStopAdditiveHitReaction();'),
 ('\tFGameplayEventData Event;\n\tEvent.Instigator = Attacker;', '''\tif (CharacterDefinition && !CharacterDefinition->GetHitReactionSettings().AdditiveHits.IsEmpty())
\t{
\t\t// Direct presentation keeps ASC's action montage/task, input, AI and CMC alive.
\t\t// The independent group prevents a flinch from replacing the attack slot.
\t\tconst auto& Pool = CharacterDefinition->GetHitReactionSettings().AdditiveHits;
\t\tUAnimMontage* Montage = Pool[FMath::RandRange(0, Pool.Num() - 1)];
\t\tUAnimInstance* Anim = GetMesh()->GetAnimInstance();
\t\tif (Anim && Montage && Montage->IsValidAdditive() && !Montage->HasRootMotion() &&
\t\t\tMontage->GetGroupName() == TEXT("KZHitReactionGroup"))
\t\t{
\t\t\t// UE 5.8 stops only montages in the new group. Repeated hits crossfade here.
\t\t\tif (Anim->Montage_Play(Montage, 1.f, EMontagePlayReturnType::MontageLength, 0.f, true) > 0.f)
\t\t\t\tif (FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage))
\t\t\t\t{
\t\t\t\t\tAdditiveHitAnim = Anim;
\t\t\t\t\tAdditiveHitMontage = Montage;
\t\t\t\t\tAdditiveHitInstanceId = Instance->GetInstanceID();
\t\t\t\t}
\t\t}
\t\t// Invalid presentation must never accidentally fall back to an interrupting hit.
\t\treturn;
\t}
\tFGameplayEventData Event;
\tEvent.Instigator = Attacker;'''),
 ('void AKZCharacter::PlayHitReaction(const EKZHitReactionType Type, AActor* Attacker)', '''void AKZCharacter::StopAdditiveHitReaction()
{
\tif (UAnimInstance* Anim = AdditiveHitAnim.Get())
\t\tif (FAnimMontageInstance* Instance = Anim->GetMontageInstanceForID(AdditiveHitInstanceId);
\t\t\tInstance && Instance->Montage == AdditiveHitMontage.Get())
\t\t\tInstance->Stop(FAlphaBlend(0.f));
\tAdditiveHitAnim.Reset();
\tAdditiveHitMontage.Reset();
\tAdditiveHitInstanceId = INDEX_NONE;
}

void AKZCharacter::PlayHitReaction(const EKZHitReactionType Type, AActor* Attacker)''')])
edit('Source/Khazan/Character/KZMonster.cpp',[
 ('\tif (ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)\n\t{','\tif (ASC->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f)\n\t{\n\t\tStopAdditiveHitReaction();'),
 ('\tif (ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) > 0.f || Exhaustion) return;', '\tif (ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f) StopAdditiveHitReaction();\n\tif (ASC->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) > 0.f || Exhaustion) return;')])
edit('Source/Khazan/AI/KZMonsterAIController.cpp',[(
 '\tconst UAnimMontage* Montage = Anim ? Anim->GetCurrentActiveMontage() : nullptr;',
 '\t// Presentation overlays are independent of the executing attack timeline.\n\tconst UAnimMontage* Montage = Anim ? Attack->GetCurrentMontage() : nullptr;')])
(o/'SourceChanges.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('Changed existing runtime files:',len(receipt))