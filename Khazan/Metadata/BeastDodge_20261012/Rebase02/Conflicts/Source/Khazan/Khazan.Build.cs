// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class Khazan : ModuleRules
{
	public Khazan(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicIncludePaths.AddRange(new string[]
        {
            "Khazan"
        });

        PublicDependencyModuleNames.AddRange(new string[]
        {
	        "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "GameplayTags", 
	        "Cog", "CogEngine", "CogDebug", "CogImgui",
	        "GameplayAbilities",
	        "GameplayTasks", "AnimGraphRuntime", "PhysicsCore",
<<<<<<< C:\Users\user\Desktop\GitProject\Khazan_BeastDodgeWork_20261012\Khazan\Source\Khazan\Khazan.Build.cs
			"NavigationSystem", "Niagara",
	        "AIModule", "StateTreeModule", "GameplayStateTreeModule", "UMG"
=======
	        "NavigationSystem",
	        "AIModule", "StateTreeModule", "GameplayStateTreeModule", "UMG", "Niagara"
>>>>>>> C:\Users\user\Desktop\GitProject\Khazan\Khazan\Source\Khazan\Khazan.Build.cs
        });

		PrivateDependencyModuleNames.AddRange(new string[] { "RHI", "Slate", "SlateCore" });
		if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new string[] { "Json", "UnrealEd" }); // Owned native PIE QA and reports only.

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
		
		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
