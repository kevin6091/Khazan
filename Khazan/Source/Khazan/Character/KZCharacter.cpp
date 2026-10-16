
#include "KZCharacter.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Component/KZLocomotionComponent.h"
#include "Data/KZCharacterDefinitionData.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Attribute/KZAttributeSet.h"
#include "GameplayAbilitySpec.h"
#include "LogChannels.h"
#include "Engine/World.h"
#include "KZGameplayTags.h"
#include "Character/KZMonster.h"
#include "System/KZAssetManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Animation/AnimMontage.h"

// Sets default values
AKZCharacter::AKZCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	LocomotionComponent = CreateDefaultSubobject<UKZLocomotionComponent>(TEXT("LocomotionComponent"));

	AbilitySystemComponent = CreateDefaultSubobject<UKZAbilitySystemComponent>(TEXT("AbilitySystemComponent"));
	
	AttributeSet = CreateDefaultSubobject<UKZAttributeSet>(TEXT("KZPlayerAttributeSet"));
	AbilitySystemComponent->AddAttributeSetSubobject(AttributeSet.Get());
}

void AKZCharacter::BeginPlay()
{
	Super::BeginPlay();
}

void AKZCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

UAbilitySystemComponent* AKZCharacter::GetAbilitySystemComponent() const
{
	return AbilitySystemComponent.Get();
}

void AKZCharacter::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	// 현재 GameWorld라면
	const UWorld* World = GetWorld();

	if (!World || !World->IsGameWorld())
	{
		return;
	}

	// ASC등록
	// 생성자에서 하지 않는 이유 : ASC의 OnRegister()가 ActorInfo 저장소를 준비함.
	// 따라서 생성자에서 ASC를 만들고 여기서 ActorInfo를 연결.
	AbilitySystemComponent->InitAbilityActorInfo(this, this);
	
	CharacterDefinition = UKZAssetManager::GetAssetByName<UKZCharacterDefinitionData>(CharacterDefinitionAssetName, false);

	//  Character가 사용할 정적 Definition이 지정됐는지 검사한다.
	if (!IsValid(CharacterDefinition))
	{
		UE_LOG(LogDefault, Error, TEXT("%s has no loaded CharacterDefinition for tag [%s]."),
			*GetNameSafe(this),
			*CharacterDefinitionAssetName.ToString());
		return;
	}

	// Definition의 Config를 LocomotionComponent의 런타임 사본으로 전달한다.
	if (!LocomotionComponent->InitializeMovementConfig(CharacterDefinition->GetLocomotionConfig()))
	{
		UE_LOG(LogDefault, Error, TEXT("%s failed to initialize locomotion from %s."),
			*GetNameSafe(this), *GetNameSafe(CharacterDefinition));

		return;
	}

	if (HasAuthority())
	{
		FGameplayEffectContextHandle Context = AbilitySystemComponent->MakeEffectContext();

		Context.AddSourceObject(this);

		for (const TSubclassOf<UGameplayEffect>& EffectClass : CharacterDefinition->GetInitialEffects())
		{
			if (!EffectClass)
			{
				continue;
			}

			FGameplayEffectSpecHandle Spec = AbilitySystemComponent->MakeOutgoingSpec(EffectClass, 1.f, Context);

			if (!Spec.IsValid())
			{
				continue;
			}

			AbilitySystemComponent->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
		}
		
		for (const FKZInitialAbilityGrant& InitialAbilityGrant : CharacterDefinition->GetInitialAbilityGrants())
		{
			if (!InitialAbilityGrant.AbilityClass)
			{
				UE_LOG(LogDefault, Error,
					TEXT("%s has an InitialAbilityGrant with no AbilityClass in %s (InputTag: %s)."),
					*GetNameSafe(this),
					*GetNameSafe(CharacterDefinition),
					*InitialAbilityGrant.InputTag.ToString());

				continue;
			}

			FGameplayAbilitySpec AbilitySpec(InitialAbilityGrant.AbilityClass);

			if (InitialAbilityGrant.InputTag.IsValid())
			{
				AbilitySpec.GetDynamicSpecSourceTags().AddTag(InitialAbilityGrant.InputTag);
			}

			AbilitySystemComponent->GiveAbility(AbilitySpec);
		}
	}
}

void AKZCharacter::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);

	// ASC에 연결된 Avatar가 현재 Character인지
	if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
	{
		// 이미 현재 Character로 연결되어있음. Controller가 바뀐거니까 갱신
		// 최초 캐릭터 연결에는 InitAbilityActorInfo(), 같은 캐릭터의 참조 갱신은 RefreshAbilityActorInfo().
		AbilitySystemComponent->RefreshAbilityActorInfo();
	}

	// ASC에 Avatar가 없다면 아직 초기연결 전이니까 갱신을 건너뜀. PostInitializeComponents()에서 Init할거.
}

// 빙의 해제
void AKZCharacter::UnPossessed()
{
	StopAdditiveHitReaction();
	if (UKZAbilitySystemComponent* ASC = Cast<UKZAbilitySystemComponent>(AbilitySystemComponent))
	{
		FGameplayTagContainer ActionTags;
		ActionTags.AddTag(KZGameplayTags::Ability_Action);
		ActionTags.AddTag(KZGameplayTags::Ability_Reaction_Hit);

		ASC->CancelAbilities(&ActionTags);
		ASC->ClearComboCommands();
	}
	
	Super::UnPossessed();

	if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
	{
		AbilitySystemComponent->RefreshAbilityActorInfo();
	}
}

// ASC와 Actor수명 연결
void AKZCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopAdditiveHitReaction();
	AbilitySystemComponent->DestroyActiveState();

	Super::EndPlay(EndPlayReason);
}

void AKZCharacter::StopAdditiveHitReaction()
{
	if (UAnimInstance* Anim = AdditiveHitAnim.Get())
		if (FAnimMontageInstance* Instance = Anim->GetMontageInstanceForID(AdditiveHitInstanceId);
			Instance && Instance->Montage == AdditiveHitMontage.Get())
			// This private presentation group also owns any outgoing flinch crossfades.
			Anim->Montage_StopGroupByName(0.f, TEXT("KZHitReactionGroup"));
	AdditiveHitAnim.Reset();
	AdditiveHitMontage.Reset();
	AdditiveHitInstanceId = INDEX_NONE;
}

void AKZCharacter::PlayHitReaction(const EKZHitReactionType Type, AActor* Attacker)
{
	// The callers have already approved this hit. A lethal/None reaction still
	// gives feedback; only the reaction Ability below requires a living target.
	if (HasAuthority() && GetNetMode() != NM_DedicatedServer && IsValid(Attacker) && CharacterDefinition)
		if (UParticleSystem* Impact = CharacterDefinition->GetHitReactionSettings().ImpactEffect)
		{
			const FVector BodyContact = GetMesh()->DoesSocketExist(TEXT("Bip001-Spine2"))
				? GetMesh()->GetSocketLocation(TEXT("Bip001-Spine2")) : GetActorLocation();
			FVector Outward = (Attacker->GetActorLocation() - BodyContact).GetSafeNormal2D();
			if (Outward.IsNearlyZero()) Outward = GetActorForwardVector();
			// Use the existing receiver capsule surface so the shared Brutal blood
			// burst is visible outside player and monster bodies at an approved hit.
			const UCapsuleComponent* Capsule = GetCapsuleComponent();
			const float Radius = Capsule->GetScaledCapsuleRadius();
			const FVector Axis = Capsule->GetUpVector() * (Capsule->GetScaledCapsuleHalfHeight() - Radius);
			const FVector Centre = FMath::ClosestPointOnSegment(BodyContact,
				Capsule->GetComponentLocation() - Axis, Capsule->GetComponentLocation() + Axis);
			const FVector Contact = Centre + Outward * Radius;
			if (UParticleSystemComponent* FX = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Impact,
				Contact, Outward.Rotation(), FVector::OneVector, true))
				FX->ComponentTags.Add(TEXT("KZReceivedHitImpact"));
		}
	if (!HasAuthority() || !IsValid(Attacker) ||
		!AbilitySystemComponent || AbilitySystemComponent->GetNumericAttribute(UKZAttributeSet::GetHPAttribute()) <= 0.f ||
		AbilitySystemComponent->HasMatchingGameplayTag(KZGameplayTags::State_Dead) ||
		AbilitySystemComponent->HasMatchingGameplayTag(KZGameplayTags::State_Exhausted) ||
		(IsA<AKZMonster>() && AbilitySystemComponent->GetNumericAttribute(UKZAttributeSet::GetStaminaAttribute()) <= 0.f)) return;
	if (CharacterDefinition && !CharacterDefinition->GetHitReactionSettings().AdditiveHits.IsEmpty())
	{
		// Direct presentation keeps ASC's action montage/task, input, AI and CMC alive.
		// The independent group prevents a flinch from replacing the attack slot.
		const auto& Pool = CharacterDefinition->GetHitReactionSettings().AdditiveHits;
		UAnimMontage* Montage = Pool[FMath::RandRange(0, Pool.Num() - 1)];
		UAnimInstance* Anim = GetMesh()->GetAnimInstance();
		if (Anim && Montage && Montage->IsValidAdditive() && !Montage->HasRootMotion() &&
			Montage->GetGroupName() == TEXT("KZHitReactionGroup"))
		{
			// UE 5.8 stops only montages in the new group. Repeated hits crossfade here.
			if (Anim->Montage_Play(Montage, 1.f, EMontagePlayReturnType::MontageLength, 0.f, true) > 0.f)
				if (FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(Montage))
				{
					AdditiveHitAnim = Anim;
					AdditiveHitMontage = Montage;
					AdditiveHitInstanceId = Instance->GetInstanceID();
				}
		}
		// Invalid presentation must never accidentally fall back to an interrupting hit.
		return;
	}
	// None suppresses the blocking reaction; configured super-armour overlays still give flinch feedback.
	if (Type == EKZHitReactionType::None) return;
	FGameplayEventData Event;
	Event.Instigator = Attacker;
	Event.Target = this;
	UAnimMontage* VictimFront = Type == EKZHitReactionType::VictimFront && IsA<AKZMonster>() && CharacterDefinition
		? CharacterDefinition->GetHitReactionSettings().VictimFront.Get() : nullptr;
	// The approved hit carries the fixed pose through the existing Short event.
	// Bodies without this humanoid setting keep StrongCombo's previous Knockback.
	Event.OptionalObject = VictimFront;
	Event.EventTag = Type == EKZHitReactionType::Launch ? KZGameplayTags::Event_Combat_Hit_Launch :
		(Type == EKZHitReactionType::Knockback || (Type == EKZHitReactionType::VictimFront && !VictimFront)
			? KZGameplayTags::Event_Combat_Hit_Knockback : KZGameplayTags::Event_Combat_Hit_Short);
	AbilitySystemComponent->HandleGameplayEvent(Event.EventTag, &Event);
}
