#include "Character/KhazanPlayer.h"


#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/KismetMathLibrary.h"

AKhazanPlayer::AKhazanPlayer()
{
	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(GetCapsuleComponent());
	SpringArm->TargetArmLength = 600.f;
	SpringArm->SetRelativeRotation(FRotator(-30,0,0));

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm);

	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -88.f), FRotator(0, -90, 0));
	GetMesh()->SetRelativeScale3D(FVector(0.009f, 0.009f, 0.009f));
}

void AKhazanPlayer::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
}

void AKhazanPlayer::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	
	// 이전에 지역적으로 보관하던 Handle 값을 비운다.
	// 정상 빙의 교체에서는 이전 Unpossessed()가 실제 Source를 먼저 종료한다.
	PlayerIntentHandle.Reset();
	
	// 새 Controller가 이전 Controller의 Sprint 요청을 상속하지 않게 한다.
	bSprintRequested = false;
	
	if (UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent())
	{
		// LocomotionComponent가 Handle의 Owner가 되고, NewController는 현재 raw Intent의 Source가 된다.
		PlayerIntentHandle = 
			Locomotion->BeginLocomotionIntentSource(NewController, EKhazanLocomotionIntentSource::PlayerController);
	}
}

void AKhazanPlayer::UnPossessed()
{
	// 현재 Handle이 아직 활성일 때 Player가 작성한
	// 방향·세기·요청 gait를 먼저 정리한다.
	HandleInputMoveReleased();
	
	// 홀드 Sprint는 Move Released만으로 false가 되지 않을 수 있으므로
	// 빙의 종료에서는 모드와 관계없이 반드시 정리한다.
	bSprintRequested = false;
	
	if (UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent())
	{
		// 현재 Controller의 Intent 작성 권한을 종료한다.
		// 함수 내부에서 활성 Source와 Id를 비우고 Handle도 Reset한다.
		Locomotion->EndLocomotionIntentSource(PlayerIntentHandle);
	}

	// LocomotionComponent를 얻지 못한 경우에도
	// Player가 보관한 지역 Handle 값은 남기지 않는다.
	PlayerIntentHandle.Reset();

	// Player의 입력 수명을 먼저 정리한 뒤
	// Character의 ASC ActorInfo 및 엔진 빙의 해제를 진행한다.
	Super::UnPossessed();
}

void AKhazanPlayer::HandleInputMove(const FVector2D& MovementInput, const FRotator& ControlRotation)
{
	UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();

	// Component가 없거나 현재 Controller에 발급된 Handle이 아니면
	// raw Intent와 CMC 입력을 모두 작성하지 않는다.
	if (!Locomotion || !Locomotion->IsActiveLocomotionIntentHandle(PlayerIntentHandle))
	{
		return;
	}
	
	// Enhanced Input에서 받은 장치 공간 2D 입력의 원래 크기다.
	const float RawInputAmount = static_cast<float>(MovementInput.Length());
	
	// 원시 입력의 크기가 DeadZone보다 작으면 입력 취소.
	if (RawInputAmount <= MoveInputDeadZone)
	{
		HandleInputMoveReleased();
		return;
	}
	
	const FRotator YawRotation(0.f, ControlRotation.Yaw, 0.f);
	const FVector Forward = UKismetMathLibrary::GetForwardVector(YawRotation);
	const FVector Right = UKismetMathLibrary::GetRightVector(YawRotation);
	
	const FVector WorldInput = Forward * MovementInput.X + Right * MovementInput.Y;
	
	// 이동 허용 여부보다 먼저 raw Intent를 기록한다.
	// Component 내부에서 Z를 제거하고 길이를 최대 1로 제한한다.
	if (!Locomotion->SetMoveInputWorld(PlayerIntentHandle, WorldInput))
	{
		return;
	}
	
	//gait 결정하기
	RefreshRequestedGait();
	
	// Config, ASC 태그, 현재 Source와 Id, Pawn, 엔진 입력 차단을
	// 모두 통과한 경우에만 CMC에 실제 이동 입력을 출력한다.
	if (!Locomotion->IsMovementInputAllowed())
	{
		return;
	}
	
	const FVector MoveDirection = Locomotion->GetLocomotionIntent().MoveInputWorld.GetSafeNormal2D();
	AddMovementInput(MoveDirection, 1.f);
}

void AKhazanPlayer::HandleInputMoveReleased()
{
	// 토글 Sprint는 Move 입력 수명이 끝날 때 요청도 해제한다.
	if (bToggleSprint)
	{
		bSprintRequested = false;
	}
	
	if (UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent())
	{
		// 실제 Move Released이므로 raw 방향과 세기를 0으로 만든다.
		Locomotion->ClearMoveInput(PlayerIntentHandle);
		
		// 이전 Run/Sprint 요청이 idle 상태에 남지 않도록
		// Character Definition의 기본 RequestedGait로 되돌린다.
		Locomotion->ResetRequestedGaitToDefault(PlayerIntentHandle);
	}
}

void AKhazanPlayer::HandleInputSprint()
{
	// 토글 방식은 Started마다 요청을 반전한다.
	// 홀드 방식은 Started에서 요청을 활성화한다.
	bSprintRequested = bToggleSprint ? !bSprintRequested : true;
	RefreshRequestedGait();
}

void AKhazanPlayer::HandleInputSprintReleased()
{
	// 토글 방식은 키를 놓아도 현재 요청을 유지한다.
	// 홀드 방식만 Completed에서 요청을 해제한다.
	if (!bToggleSprint)
	{
		bSprintRequested = false;
	}

	RefreshRequestedGait();
}

void AKhazanPlayer::HandleInputSprintCanceled()
{
	// Canceled는 정상 Completed와 다를 수 있으므로
	// 입력 방식과 관계없이 요청을 확실히 해제한다.
	bSprintRequested = false;
	RefreshRequestedGait();
}

void AKhazanPlayer::RefreshRequestedGait()
{
	UKhazanLocomotionComponent* Locomotion = GetLocomotionComponent();
	
	// 현재 Player Controller가 가진 Handle로만 gait 요청을 쓴다.
	if (!Locomotion || !Locomotion->IsActiveLocomotionIntentHandle(PlayerIntentHandle))
	{
		return;
	}
	
	const FKhazanLocomotionIntent& Intent = Locomotion->GetLocomotionIntent();
	
	if (Intent.InputAmount <= 0.f)
	{
		return;
	}
	// 정확히 RunInputThreshold와 같으면 Walk,
	// 그것보다 클 때만 Run을 요청한다.
	const EKhazanGait StickGait = Intent.InputAmount > RunInputThreshold ? EKhazanGait::Run : EKhazanGait::Walk;
	
	// Sprint 입력 요청이 있으면 StickGait보다 Sprint 요청이 우선한다.
	// 이 값은 아직 Constraint가 적용되지 않은 RequestedGait다.
	const EKhazanGait RequestedGait = bSprintRequested 	? EKhazanGait::Sprint : StickGait;

	// LocomotionComponent가 RequestedGait와 모든 Constraint를 다시 해결하고
	// ResolvedGait에 해당하는 MaxWalkSpeed를 CMC에 적용한다.
	Locomotion->SetRequestedGait(PlayerIntentHandle, RequestedGait);
}
