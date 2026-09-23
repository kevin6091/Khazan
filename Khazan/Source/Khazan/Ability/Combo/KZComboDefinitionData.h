

#pragma once

#include "CoreMinimal.h"
#include "Ability/Combo/KZComboTypes.h"
#include "Engine/DataAsset.h"
#include "GameplayEffectTypes.h"
#include "KZComboDefinitionData.generated.h"

class UAnimMontage;

// 한 입력에서 다음 공격으로 넘어가기 위한 조건이다.
USTRUCT()
struct FKZComboCommandEdge
{
	GENERATED_BODY()

	// 어떤 공격 명령을 받았을 때 이 전환을 검사할지 정한다.
	UPROPERTY(EditAnywhere, Category = "Combo", meta = (Categories = "Command"))
	FGameplayTag CommandTag;

	// 버튼을 눌렀을 때인지 뗐을 때인지 정한다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	EKZComboCommandPhase CommandPhase = EKZComboCommandPhase::Begin;

	// 이 전환을 할 때 계속 누르고 있어야 하는 다른 명령들이다.
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
	UPROPERTY(EditAnywhere, Category = "Combo")
	TArray<FKZComboCommandEdge> CommandEdges;
};


// 콤보 노드와 연결 규칙을 에디터에서 작성하는 Data Asset이다.
UCLASS()
class KHAZAN_API UKZComboDefinitionData : public UDataAsset
{
	GENERATED_BODY()

public:
	// 이름이 같은 노드를 찾고, 없으면 nullptr를 돌려준다.
	const FKZComboNode* FindNode(FName NodeId) const;

private:
	// 이 콤보에 들어 있는 모든 공격 노드다.
	UPROPERTY(EditAnywhere, Category = "Combo")
	TArray<FKZComboNode> Nodes;
};
