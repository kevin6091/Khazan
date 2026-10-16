

#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboTypes.h"
#include "Engine/DataAsset.h"
#include "GameplayEffectTypes.h"
#include "Data/KZCharacterDefinitionData.h"
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
	EKZHitReactionType HitReaction = EKZHitReactionType::Short;
	UPROPERTY(EditAnywhere, Category = "Attack")
	bool bBlockable = false;
	UPROPERTY(EditAnywhere, Category = "Attack") bool bBeginsCapture = false;
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

UENUM(BlueprintType)
enum class EKZPatternEvent : uint8 { Animation, Tick, ConfirmedHit, Parried, HoldingSuccess, Collision, StepStart, Landed };

/** An original SB event, not an additional Character behaviour state. */
USTRUCT(BlueprintType)
struct FKZMonsterPatternBranch
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FName Notify = NAME_None;
	UPROPERTY(EditAnywhere) EKZPatternEvent Event = EKZPatternEvent::Animation;
	UPROPERTY(EditAnywhere) TArray<FKZCombatPatternCondition> Conditions;
	UPROPERTY(EditAnywhere) FName TargetNode = NAME_None;
	UPROPERTY(EditAnywhere) bool bDeferUntilStepEnd = false;
	UPROPERTY(EditAnywhere) bool bCheckCooldown = false;
	UPROPERTY(EditAnywhere) float Weight = 1.f;
	UPROPERTY(EditAnywhere) float Probability = 1.f;
	// Node-local montage seconds; empty means the event itself owns the boundary.
	UPROPERTY(EditAnywhere) TArray<FVector2D> ActiveWindows;
	UPROPERTY(EditAnywhere) bool bRequireConfirmedHit = false;
	UPROPERTY(EditAnywhere) FString Source;
};

USTRUCT(BlueprintType)
struct FKZMonsterPatternObject
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FName Id;
	UPROPERTY(EditAnywhere) TObjectPtr<class USkeletalMesh> Mesh;
	UPROPERTY(EditAnywhere) TObjectPtr<class UStaticMesh> StaticMesh;
	UPROPERTY(EditAnywhere) TMap<FName,TObjectPtr<class UAnimSequence>> Animations;
	UPROPERTY(EditAnywhere) TObjectPtr<class UCurveVector> MovementCurve;
	UPROPERTY(EditAnywhere) FVector CurveScale = FVector::OneVector;
	UPROPERTY(EditAnywhere) float MovementSeconds = 0.f;
	UPROPERTY(EditAnywhere) float LinearSpeed = 0.f;
	UPROPERTY(EditAnywhere) bool bKeepEndVelocity = false;
	UPROPERTY(EditAnywhere) FVector FieldExtent = FVector::ZeroVector;
	UPROPERTY(EditAnywhere) float Radius = 0.f;
	UPROPERTY(EditAnywhere) float DestructionRadius = 0.f;
	UPROPERTY(EditAnywhere) float Scale = 1.f;
	UPROPERTY(EditAnywhere) float LifeSeconds = 0.f;
	UPROPERTY(EditAnywhere) float HPDamage = 0.f;
	UPROPERTY(EditAnywhere) float StaminaDamage = 0.f;
	UPROPERTY(EditAnywhere) bool bField = false;
	UPROPERTY(EditAnywhere) FName TrailObjectId;
	UPROPERTY(EditAnywhere) float TrailInterval = 0.f;
	UPROPERTY(EditAnywhere) int32 TrailMaxCount = 0;
	UPROPERTY(EditAnywhere) bool bDestroyOnAbilityEnd = false;
	UPROPERTY(EditAnywhere) FString Source;
};

UENUM()
enum class EKZPatternAction : uint8 { SpawnObject, ShootObject, Capture, DirectDamage, AddCooldown, DestroyObjects };

USTRUCT()
struct FKZMonsterPatternAction
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FName Notify;
	UPROPERTY(EditAnywhere) EKZPatternAction Action = EKZPatternAction::SpawnObject;
	UPROPERTY(EditAnywhere) EKZPatternEvent Event = EKZPatternEvent::Animation;
	UPROPERTY(EditAnywhere) FName ObjectId;
	UPROPERTY(EditAnywhere) FName TargetSkill;
	UPROPERTY(EditAnywhere) float CooldownSeconds = 0.f;
	UPROPERTY(EditAnywhere) FName Socket;
	UPROPERTY(EditAnywhere) FName CaptureTargetSocket = TEXT("Bip001-Spine");
	UPROPERTY(EditAnywhere) FName RagdollBone;
	UPROPERTY(EditAnywhere) float PhysicsBlendWeight = 0.f;
	UPROPERTY(EditAnywhere) FVector Offset = FVector::ZeroVector;
	UPROPERTY(EditAnywhere) bool bSpawnOnFloor = false;
	UPROPERTY(EditAnywhere) bool bFlatAim = false;
	UPROPERTY(EditAnywhere) TArray<FVector2D> ActiveWindows;
	UPROPERTY(EditAnywhere) TArray<float> Times;
	UPROPERTY(EditAnywhere) float Interval = 0.f;
	UPROPERTY(EditAnywhere) int32 MaxCount = 1;
	UPROPERTY(EditAnywhere) FString Source;
	UPROPERTY(EditAnywhere) float HPDamage = 0.f;
	UPROPERTY(EditAnywhere) float StaminaDamage = 0.f;
};

USTRUCT()
struct FKZMonsterPatternMove
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) FVector2D Window = FVector2D::ZeroVector;
	UPROPERTY(EditAnywhere) FVector Destination = FVector::ZeroVector;
	UPROPERTY(EditAnywhere) bool bTraceTarget = false;
	UPROPERTY(EditAnywhere) float TargetMin = 0.f;
	UPROPERTY(EditAnywhere) float TargetMax = 0.f;
	UPROPERTY(EditAnywhere) float TargetOffset = 0.f;
	UPROPERTY(EditAnywhere) float StopDistance = 0.f;
	UPROPERTY(EditAnywhere) TObjectPtr<class UCurveFloat> TimeCurve;
	UPROPERTY(EditAnywhere) TObjectPtr<class UCurveVector> OffsetCurve;
	UPROPERTY(EditAnywhere) FString Source;
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
	// Used only by the original monster pattern Ability. Existing player/human command edges are unchanged.
	UPROPERTY(EditAnywhere, Category = "Monster Pattern") FName PatternSkill = NAME_None;
	UPROPERTY(EditAnywhere, Category = "Monster Pattern") FName AutomaticNextNode = NAME_None;
	UPROPERTY(EditAnywhere, Category = "Monster Pattern") TArray<FKZMonsterPatternAction> PatternActions;
	UPROPERTY(EditAnywhere, Category = "Monster Pattern") TArray<FKZMonsterPatternMove> PatternMoves;
	UPROPERTY(EditAnywhere, Category = "Monster Pattern") float PatternBlendSeconds = -1.f;
	UPROPERTY(EditAnywhere, Category = "Monster Pattern", meta = (TitleProperty = "{Notify} -> {TargetNode}"))
	TArray<FKZMonsterPatternBranch> PatternBranches;

	// 이 공격 다음에 갈 수 있는 모든 전환 규칙이다.
	UPROPERTY(EditAnywhere, Category = "Combo",
		meta = (TitleProperty = "{CommandTag} | {CommandPhase} | Hold={Hold} | Move={Move} -> {TargetNodeId}"))
	TArray<FKZComboCommandEdge> CommandEdges;

	// Maps the original baked ground/model frame to actor-local cm; no mesh .01 rescaling.
	UPROPERTY(EditAnywhere, Category = "Attack")
	FTransform CollisionToActor = FTransform::Identity;
	UPROPERTY(EditAnywhere, Category = "Attack", meta = (TitleProperty = "{StartTime} - {EndTime} | {HitGroup} | {HitReaction}"))
	TArray<FKZAttackCollisionWindow> AttackWindows;
	// Original DamageType=SystemGuard notify intervals, mapped to this node's playback seconds.
	UPROPERTY(EditAnywhere, Category = "Shield", meta = (ToolTip = "Node-local playback seconds: X=start, Y=end."))
	TArray<FVector2D> SystemGuardWindows;
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
	const TArray<FKZMonsterPatternObject>& GetPatternObjects() const { return PatternObjects; }
	bool ShouldDrawAttackCollision() const { return bDrawAttackCollision; }

private:
	// 이 콤보에 들어 있는 모든 공격 노드다.
	UPROPERTY(EditAnywhere, Category = "Combo", meta = (TitleProperty = "NodeId"))
	TArray<FKZComboNode> Nodes;
	UPROPERTY(EditAnywhere, Category="Monster Pattern", meta=(TitleProperty="Id"))
	TArray<FKZMonsterPatternObject> PatternObjects;
	UPROPERTY(EditAnywhere, Category = "Attack")
	TSubclassOf<UGameplayEffect> AttackDamageEffect;
	UPROPERTY(EditAnywhere, Category = "Attack")
	bool bDrawAttackCollision = false;
};
