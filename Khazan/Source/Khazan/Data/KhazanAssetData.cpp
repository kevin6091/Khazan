


#include "Data/KhazanAssetData.h"
#include "LogChannels.h"
#include "UObject/ObjectSaveContext.h"

void UKhazanAssetData::PostLoad()
{
	Super::PostLoad();
	RebuildRuntimeLookupMaps();
}

void UKhazanAssetData::PreSave(FObjectPreSaveContext ObjectSaveContext)
{
	Super::PreSave(ObjectSaveContext);
	RebuildRuntimeLookupMaps();
}

void UKhazanAssetData::RebuildRuntimeLookupMaps()
{
	AssetNameToPath.Empty();
	AssetLabelToSet.Empty();
	
	AssetGroupNameToSet.KeySort([](const FName& A, const FName& B)
	{
		return (A.Compare(B) < 0);
	});
	
	for (const auto& Pair : AssetGroupNameToSet)
	{
		const FAssetSet& AssetSet = Pair.Value;
		for (FAssetEntry AssetEntry : AssetSet.AssetEntries)
		{
			FSoftObjectPath& AssetPath = AssetEntry.AssetPath;
			const FString& AssetName = AssetPath.GetAssetName();
			if (AssetName.StartsWith(TEXT("BP_")) || AssetName.StartsWith(TEXT("B_")) ||
				AssetName.StartsWith(TEXT("GE_")) || AssetName.StartsWith(TEXT("GA_")))
			{
				FString AssetPathString = AssetPath.GetAssetPathString();
				AssetPathString.Append(TEXT("_C"));
				AssetPath = FSoftObjectPath(AssetPathString);
			}
			
			AssetNameToPath.Emplace(AssetEntry.AssetName, AssetEntry.AssetPath);
			for (const FGameplayTag& Label : AssetEntry.AssetLabels)
			{
				AssetLabelToSet.FindOrAdd(Label).AssetEntries.Emplace(AssetEntry);
			}
		}
	}
}

FSoftObjectPath UKhazanAssetData::GetAssetPathByName(const FGameplayTag& AssetName)
{
	FSoftObjectPath* AssetPath = AssetNameToPath.Find(AssetName);
	if (!AssetPath)
	{
		UE_LOG(LogDefault, Error, TEXT("Cant find Asset Path from Asset Name [%s]."), *AssetName.ToString());
		return FSoftObjectPath();
	}
	return *AssetPath;
}

const FAssetSet* UKhazanAssetData::GetAssetSetByLabel(const FGameplayTag& Label)
{
	const FAssetSet* AssetSet = AssetLabelToSet.Find(Label);
	if (!AssetSet)
	{
		UE_LOG(LogDefault, Error, TEXT("Cant find Asset Set from Label [%s]."), *Label.ToString());
	}
	return AssetSet;
}