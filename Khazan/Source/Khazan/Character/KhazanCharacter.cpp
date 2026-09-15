
#include "KhazanCharacter.h"
#include "Component/KhazanLocomotionComponent.h"
#include "Data/KhazanCharacterDefinitionData.h"
#include "Ability/KhazanAbilitySystemComponent.h"
#include "GameplayAbilitySpec.h"
#include "LogChannels.h"
#include "Engine/World.h"
#include "System/KhazanAssetManager.h"

// Sets default values
AKhazanCharacter::AKhazanCharacter()
{
	PrimaryActorTick.bCanEverTick = true;
	
	LocomotionComponent = CreateDefaultSubobject<UKhazanLocomotionComponent>(TEXT("LocomotionComponent"));
	
	AbilitySystemComponent = CreateDefaultSubobject<UKhazanAbilitySystemComponent>(TEXT("AbilitySystemComponent"));
}

void AKhazanCharacter::BeginPlay()
{
	Super::BeginPlay();
}
 
void AKhazanCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

UAbilitySystemComponent* AKhazanCharacter::GetAbilitySystemComponent() const
{
	return AbilitySystemComponent.Get();
}

void AKhazanCharacter::PostInitializeComponents()
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
	
	CharacterDefinition = 
		UKhazanAssetManager::GetAssetByName<UKhazanCharacterDefinitionData>
	(CharacterDefinitionAssetName, false);
	
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
		for (const FKhazanInitialAbilityGrant& InitialAbilityGrant : CharacterDefinition->GetInitialAbilityGrants())
		{
			if (!InitialAbilityGrant.AbilityClass)
			{
				UE_LOG(LogDefault, Error,
					TEXT("%s has an InitialAbilityGrant with no AbilityClass "
						 "in %s (InputTag: %s)."),
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

void AKhazanCharacter::PossessedBy(AController* NewController)
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
void AKhazanCharacter::UnPossessed()
{
	Super::UnPossessed();

	if (AbilitySystemComponent->GetAvatarActor_Direct() == this)
	{
		AbilitySystemComponent->RefreshAbilityActorInfo();
	}
}

// ASC와 Actor수명 연결
void AKhazanCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	AbilitySystemComponent->DestroyActiveState();

	Super::EndPlay(EndPlayReason);
}