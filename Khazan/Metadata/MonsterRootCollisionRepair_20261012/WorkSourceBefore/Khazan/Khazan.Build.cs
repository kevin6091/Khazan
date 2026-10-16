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
	        "NavigationSystem",
	        "AIModule", "StateTreeModule", "GameplayStateTreeModule", "UMG"
        });

		PrivateDependencyModuleNames.AddRange(new string[] { "RHI", "Slate", "SlateCore" });
		if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("Json"); // Native PIE report serialization only.
		if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", "AssetRegistry", "AssetTools", "JsonUtilities", "KismetCompiler", "BlueprintGraph", "AnimGraph", "StateTreeEditorModule", "PropertyBindingUtils", "AnimationWarpingRuntime", "AnimationWarpingEditor" });

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
		
		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
