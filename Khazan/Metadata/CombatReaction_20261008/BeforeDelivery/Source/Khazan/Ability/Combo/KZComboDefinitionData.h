

#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboTypes.h"
#include "Engine/DataAsset.h"
#include "GameplayEffectTypes.h"
#include "KZComboDefinitionData.generated.h"

class UAnimMontage;
class UGameplayEffect;

UENUM(BlueprintType)
enum class EKZAttackCollisionShape : uint8
{
	Box,
	Cylinder,
	Sphere
};

// Original baked keys, converted to this node's playback seconds and centimetres.
USTRUCT(BlueprintType)
struct KHAZAN_API FKZAttackCollisionKey
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (ClampMin = "0", Units = "s"))
	float Time = 0.f;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (Units = "cm"))
	FVector Center = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, Category = "Attack")
	FRotator Rotation = FRotator::ZeroRotator;
};

USTRUCT(BlueprintType)
struct KHAZAN_API FKZAttackCollisionWindow
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (ClampMin = "0", Units = "s"))
	float StartTime = 0.f;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (ClampMin = "0", Units = "s"))
	float EndTime = 0.f;
	UPROPERTY(EditAnywhere, Category = "Attack")
	EKZAttackCollisionShape Shape = EKZAttackCollisionShape::Box;
	// Box: half extents. Cylinder: X/Y radius, Z half height. Sphere: X radius.
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (Units = "cm"))
	FVector Extent = FVector::ZeroVector;
	// Empty means one hit per target in THIS window. Equal nonempty groups share that hit.
	UPROPERTY(EditAnywhere, Category = "Attack")
	FName HitGroup = NAME_None;
	// Absolute attribute damage, NOT an unverified original attack-power multiplier.
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (ClampMin = "0"))
	float HPDamage = 0.f;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (ClampMin = "0"))
	float StaminaDamage = 0.f;
	UPROPERTY(EditAnywhere, Category = "Attack")
	bool bBlockable = false;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (TitleProperty = "Time"))
	TArray<FKZAttackCollisionKey> Keys;
	// Exact source/field/unit/conversion and any provisional interpretation/tuning.
	UPROPERTY(VisibleAnywhere, Category = "Attack")
	FString Source;
};

// 한 입력에서 다음 공격으로 넘어가기 위한 조건이다.
USTRUCT()
struct FKZComboCommandEdge
{
	GENERATED_BODY()

	// 어떤 공격 명령을 받았을 때 이 전환을 검사할지 정한다.
	UPROPERTY(EditAnywhere, Category = "Combo", meta = (Categories = "Command"))
	FGameplayTag CommandTag;

	// Begin, Release, InputEnd, HoldCommit, HoldEnd 중 언제 검사할 Edge인지 정한다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	EKZComboCommandPhase CommandPhase = EKZComboCommandPhase::Begin;

	// HoldCommit 전후 중 어느 상태에서 허용되는 Edge인지 정한다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	EKZComboHold Hold = EKZComboHold::Any;

	// Edge를 실제 검사하는 순간의 이동 입력 상태다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	EKZComboMove Move = EKZComboMove::Any;
	
	// 현재 명령 말고 추가로 계속 누르고 있어야 하는 명령들이다.
	// 예: X 사건에 Y도 필요할 때만 Y를 넣는다. Y 사건에 Y를 다시 넣지는 않는다.
	UPROPERTY(EditAnywhere, Category = "Combo", meta = (Categories = "Command"))
	FGameplayTagContainer RequiredHeldCommands;

	// 해금 여부처럼 캐릭터 태그로 확인할 조건이다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	FGameplayTagRequirements OwnerTagRequirements;

	// 조건을 통과했을 때 이동할 다음 노드다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	FName TargetNodeId = NAME_None;
};

// 콤보 한 타의 몽타주 위치와 다음 공격 규칙을 묶은 데이터다.
USTRUCT(BlueprintType)
struct KHAZAN_API FKZComboNode
{
	GENERATED_BODY()

	// 콤보 안에서 이 공격을 찾을 때 쓰는 이름이다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	FName NodeId = NAME_None;

	// 이 공격이 들어 있는 몽타주다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	TObjectPtr<UAnimMontage> Montage = nullptr;

	// 몽타주에서 이 공격이 시작되는 섹션이다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	FName SectionName = NAME_None;

	// 이 공격 다음에 갈 수 있는 모든 전환 규칙이다.
	UPROPERTY(EditAnywhere, Category = "Combo",
		meta = (TitleProperty = "{CommandTag} | {CommandPhase} | Hold={Hold} | Move={Move} -> {TargetNodeId}"))
	TArray<FKZComboCommandEdge> CommandEdges;

	// Maps the original baked ground/model frame to actor-local cm; no mesh .01 rescaling.
	UPROPERTY(EditAnywhere, Category = "Attack")
	FTransform CollisionToActor = FTransform::Identity;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (TitleProperty = "{StartTime} - {EndTime} | {HitGroup}"))
	TArray<FKZAttackCollisionWindow> AttackWindows;
};


// 콤보 노드와 연결 규칙을 에디터에서 작성하는 Data Asset이다.
UCLASS()
class KHAZAN_API UKZComboDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	// 이름이 같은 노드를 찾고, 없으면 nullptr를 돌려준다.
	const FKZComboNode* FindNode(FName NodeId) const;
	TSubclassOf<UGameplayEffect> GetAttackDamageEffect() const { return AttackDamageEffect; }
	bool ShouldDrawAttackCollision() const { return bDrawAttackCollision; }

private:
	// 이 콤보에 들어 있는 모든 공격 노드다.
	UPROPERTY(EditAnywhere, Category = "Combo", meta = (TitleProperty = "NodeId"))
	TArray<FKZComboNode> Nodes;
	UPROPERTY(EditAnywhere, Category = "Attack")
	TSubclassOf<UGameplayEffect> AttackDamageEffect;
	UPROPERTY(EditAnywhere, Category = "Attack")
	bool bDrawAttackCollision = false;
};
