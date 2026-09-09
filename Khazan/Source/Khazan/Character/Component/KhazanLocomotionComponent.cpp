


#include "Character/Component/KhazanLocomotionComponent.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/Pawn.h"
#include "KhazanGameplayTags.h"
#include "LogChannels.h"

UKhazanLocomotionComponent::UKhazanLocomotionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UKhazanLocomotionComponent::BeginPlay()
{
	Super::BeginPlay();
	
	Intent.bMovementAllowed = false;
	
	UAbilitySystemComponent* ASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetOwner());
	
	if (!IsValid(ASC))
	{
		UE_LOG(LogDefault,Error,TEXT("%s requires an AbilitySystemComponent for locomotion."),*GetNameSafe(GetOwner()));
		return;
	}
	
	// ASC 관찰
	ObservedAbilitySystemComponent = ASC;
	
	FOnGameplayEffectTagCountChanged& event = 
		ASC->RegisterGameplayTagEvent(KhazanGameplayTags::Block_Movement_Input,EGameplayTagEventType::NewOrRemoved);
	
	MovementBlockChangedHandle = event.AddUObject(this,&UKhazanLocomotionComponent::HandleMovementBlockChanged);

	RefreshMovementPermission();
}

void UKhazanLocomotionComponent::SetMoveInputWorld(const FVector& Input)
{
	// 원시 Input을 무조건 저장한다. 이동이 제약은 ASC에서 계산함.
	
	const FVector Input2D(Input.X, Input.Y, 0.f);
	
	// 0~1범위
	Intent.MoveInputWorld = Input2D.GetClampedToMaxSize(1.f);
	// 0~1범위
	Intent.InputAmount = Intent.MoveInputWorld.Size2D();
}

void UKhazanLocomotionComponent::ClearMoveInput()
{
	Intent.MoveInputWorld = FVector::ZeroVector;
	Intent.InputAmount = 0.f;
}

void UKhazanLocomotionComponent::SetTargetGait(EKhazanGait Gait)
{
	Intent.TargetGait = Gait;
}

void UKhazanLocomotionComponent::SetMaxAllowedGait(EKhazanGait Gait)
{
	Intent.MaxAllowedGait = Gait;
}

void UKhazanLocomotionComponent::SetRotationMode(EKhazanRotationMode Mode)
{
	Intent.RotationMode = Mode;
}

void UKhazanLocomotionComponent::HandleMovementBlockChanged(const FGameplayTag Tag, int32 NewCount)
{
	// 인자를 사용하지 않음.
	// 인자를 저장하지 않고 현재 ASC를 조회. 현재 상태를 기준으로 결정함.
	(void)Tag;
	(void)NewCount;
	
	RefreshMovementPermission();
}

void UKhazanLocomotionComponent::RefreshMovementPermission()
{
	check(IsInGameThread());

	const UAbilitySystemComponent* ASC = ObservedAbilitySystemComponent.Get();

	// Block_Movement_Input 카운트가 0이면 -> 이동 입력이 막히지 않았다 -> bMovementAllowed = true 
	Intent.bMovementAllowed = ASC && ASC->GetTagCount(KhazanGameplayTags::Block_Movement_Input) == 0;

	if (!Intent.bMovementAllowed)
	{
		if (APawn* Pawn = Cast<APawn>(GetOwner()))
		{
			// CMC에 등록된 Input을 비우기.
			Pawn->ConsumeMovementInputVector();
		}
	}
}

bool UKhazanLocomotionComponent::IsMovementInputAllowed() const
{
	check(IsInGameThread());

	const APawn* Pawn = Cast<APawn>(GetOwner());

	return ObservedAbilitySystemComponent.IsValid()
		&& Intent.bMovementAllowed
		&& Pawn
		&& !Pawn->IsMoveInputIgnored();
}

EKhazanGait UKhazanLocomotionComponent::GetResolvedGait() const
{
	const uint8 TargetRank =
		static_cast<uint8>(Intent.TargetGait);

	const uint8 MaxAllowedRank =
		static_cast<uint8>(Intent.MaxAllowedGait);

	return TargetRank <= MaxAllowedRank
		? Intent.TargetGait
		: Intent.MaxAllowedGait;
}

void UKhazanLocomotionComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UAbilitySystemComponent* ASC = ObservedAbilitySystemComponent.Get())
	{
		// ASC에 Tag와 Event 등록해제.
		if (MovementBlockChangedHandle.IsValid())
		{
			ASC->UnregisterGameplayTagEvent(MovementBlockChangedHandle,
				KhazanGameplayTags::Block_Movement_Input,
				EGameplayTagEventType::NewOrRemoved
			);
		}
	}

	MovementBlockChangedHandle.Reset();
	ObservedAbilitySystemComponent.Reset();

	Intent.bMovementAllowed = false;
	ClearMoveInput();

	Super::EndPlay(EndPlayReason);
}