

#include "KhazanGameMode.h"

#include "CogSubsystem.h"
#include "CogEngineWindow_Selection.h"
#include "CogEngineWindow_TimeScale.h"
#include "CogEngineWindow_Skeleton.h"
#include "CogEngineWindow_Stats.h"
#include "CogEngineWindow_Console.h"
#include "CogEngineWindow_OutputLog.h"
#include "CogEngineWindow_CollisionViewer.h"
#include "CogEngineWindow_CollisionTester.h"
#include "CogEngineWindow_Inspector.h"
#include "CogEngineWindow_Spawns.h"
#include "CogEngineWindow_Transform.h"
#include "CogEngineWindow_Cheats.h"

void AKhazanGameMode::BeginPlay()
{
	Super::BeginPlay();
	if (UWorld* World = GetWorld())
	{
		if (UCogSubsystem* CogSubsystem = World->GetSubsystem<UCogSubsystem>())
		{
			CogSubsystem->AddWindow<FCogEngineWindow_Selection>(TEXT("Engine.Selection"));
			CogSubsystem->AddWindow<FCogEngineWindow_Inspector>(TEXT("Engine.Inspector"));
    
			CogSubsystem->AddWindow<FCogEngineWindow_CollisionViewer>(TEXT("Engine.Collision Viewer"));
			CogSubsystem->AddWindow<FCogEngineWindow_CollisionTester>(TEXT("Engine.Collision Tester"));
			CogSubsystem->AddWindow<FCogEngineWindow_TimeScale>(TEXT("Engine.Time Scale"));
			CogSubsystem->AddWindow<FCogEngineWindow_Stats>(TEXT("Engine.Stats"));
			CogSubsystem->AddWindow<FCogEngineWindow_Skeleton>(TEXT("Engine.Skeleton"));
			UE_LOG(LogTemp, Warning, TEXT(">>> Cog Windows Registered Successfully! <<<"));
		}
	}
}
