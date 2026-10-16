#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KZSnowDeformation.generated.h"

class ACharacter;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMaterial;
class UMaterialExpression;
class UPrimitiveComponent;
class UTexture2D;
class UStaticMesh;
class USkeletalMesh;

/** Authored from actual rigid weapon vertices in the imported reference pose. */
USTRUCT()
struct FKZSnowWeaponPoints
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) TSoftObjectPtr<USkeletalMesh> Mesh;
	UPROPERTY(EditAnywhere) FName Bone;
	UPROPERTY(EditAnywhere) TArray<FVector> Points;
};

/** Existing terrain shader weights, baked once for local physical snow contact. */
USTRUCT()
struct FKZSnowSurfaceSamples
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere) TSoftObjectPtr<UMaterialInterface> Material;
	UPROPERTY(EditAnywhere) FVector2D UVOriginCm = FVector2D::ZeroVector;
	UPROPERTY(EditAnywhere) FVector2D UVScaleCm = FVector2D::ZeroVector;
	UPROPERTY(EditAnywhere) FIntPoint Resolution = FIntPoint::ZeroValue;
	// Per texel: height numerator, total non-puddle weight, snow weight.
	// Bilinear interpolation precedes division, matching the existing material.
	UPROPERTY(EditAnywhere) TArray<float> Samples;
	UPROPERTY(EditAnywhere) float DepthReferenceCm = 0.f;
	UPROPERTY(EditAnywhere) float RimHeightCm = 0.f;
};

/** Level-owned presentation field. Does not change CMC collision or gameplay state. */
UCLASS()
class KHAZAN_API AKZSnowDeformation : public AActor
{
	GENERATED_BODY()

public:
	AKZSnowDeformation();
	virtual void Tick(float DeltaSeconds) override;

	/** Physical contacts and editor verification share the same field writer. Units: cm. */
	UFUNCTION(BlueprintCallable, Category="Snow")
	void StampSnow(FVector Position, FVector Forward, FVector2D RadiusCm, float Compression = 1.f);

	UFUNCTION(BlueprintPure, Category="Snow")
	float GetCompressionAtLocation(FVector Position) const;

	UFUNCTION(BlueprintCallable, Category="Snow")
	void ClearSnow();

	// UE Python hides MP_Displacement; authoring uses the native engine input directly.
	UFUNCTION(BlueprintCallable, Category="Snow|Editor", meta=(DevelopmentOnly))
	static void ConfigureMaterialDisplacement(UMaterial* Material, UMaterialExpression* Expression);
	UFUNCTION(BlueprintCallable, Category="Snow|Editor", meta=(DevelopmentOnly))
	static void RebuildSurfaceCollision(UStaticMesh* Mesh);
	UFUNCTION(BlueprintCallable, Category="Snow|Editor", meta=(DevelopmentOnly))
	int32 AuthorMergedWeaponContacts(const TArray<USkeletalMesh*>& Meshes);
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	TArray<FKZSnowWeaponPoints> MergedWeaponContacts;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	TArray<FKZSnowSurfaceSamples> SurfaceContactSamples;

	UPROPERTY(EditAnywhere, Category="Snow|Surface")
	FName SurfaceTag = TEXT("HeinMachSnowSurface");

	// Technical sampling budget: 2 cm per texel over a 40.96 m moving window.
	UPROPERTY(EditAnywhere, Category="Snow|Field", meta=(ClampMin="128", ClampMax="4096"))
	int32 FieldResolution = 2048;
	UPROPERTY(EditAnywhere, Category="Snow|Field", meta=(ClampMin="0.5"))
	float TexelSizeCm = 2.f;
	// Temporary cache budget: bounded persistent tiles; oldest distant tiles are evicted.
	UPROPERTY(EditAnywhere, Category="Snow|Field", meta=(ClampMin="16"))
	int32 MaxCachedTiles = 256;

	// Monster feet: complete disturbance (including the 1.4-radius rim) fits 8 x 5 cm.
	// Player contacts instead use the actual capsule/snow intersection; no separate radius tuning.
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	FVector2D FootRadiusCm = FVector2D(8.f/1.4f, 5.f/1.4f);
	// User depths normalized against the material's 55 cm depth reference; thin snow clips at ground.
	UPROPERTY(EditAnywhere, Category="Snow|Contact", meta=(ClampMin="0", ClampMax="1"))
	float FootCompression = 35.f/55.f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact", meta=(ClampMin="0", ClampMax="1"))
	float WeaponCompression = 50.f/55.f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float FootContactHeightCm = 8.f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float BodyContactHeightCm = 24.f;
	// Temporary torso/limb brush, checked against evaluated pose contacts rather than action state.
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	FVector2D BodyRadiusCm = FVector2D(22.f,18.f);
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float LayerHeightToleranceCm = 32.f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float MinSurfaceNormalZ = 0.5f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float WeaponRadiusCm = 100.f;
	// Separate brush size from vertical contact reach so a wide crater still requires contact.
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float WeaponContactHeightCm = 24.f;
	// Native contact tolerance, not an original-game value. Crater size does not expand contact.
	UPROPERTY(EditAnywhere, Category="Snow|Contact", meta=(ClampMin="0", Units="cm"))
	float WeaponSurfaceContactToleranceCm = 6.f;
	UPROPERTY(EditAnywhere, Category="Snow|Contact")
	float TeleportDistanceCm = 256.f;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	static constexpr int32 TileSize = 128;
	struct FCell { float Compression=0.f; float Rim=0.f; float GroundZ=0.f; };
	struct FTile { TArray<FCell> Cells; double LastTouched=0.; };
	struct FContact { FVector Previous=FVector::ZeroVector; FName SoleBone=NAME_None; bool bTouching=false; bool bBody=false; bool bWeapon=false; bool bHasPrevious=false; };
	struct FBinding { TWeakObjectPtr<UPrimitiveComponent> Component; int32 Slot=0; int32 MaterialIndex=0; };

	void BindSurfaces();
	void ObserveCharacter(ACharacter* Character);
	bool GroundContact(AActor* Source, FVector Position, float Reach, FHitResult& Hit) const;
	bool GetSnowSurfaceHeight(const FHitResult& Hit, double& SurfaceHeight) const;
	bool WeaponSnowContact(AActor* Source, FVector Position, FHitResult& Hit) const;
	void FollowPlayer();
	void UploadTiles();
	void SetFieldParameters();
	FIntPoint CellKey(FVector Position) const;
	FIntPoint TileKey(FIntPoint Cell) const;
	const FCell* FindCell(FIntPoint Cell) const;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> FieldTexture;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> SurfaceMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> OriginalMaterials;
	TArray<FBinding> Bindings;
	TMap<FIntPoint, FTile> Tiles;
	TSet<FIntPoint> DirtyTiles;
	TMap<TWeakObjectPtr<UPrimitiveComponent>, TMap<FName,FContact>> Contacts;
	FIntPoint WindowOrigin=FIntPoint::ZeroValue;
	bool bWindowInitialized=false;
	bool bClearTexture=true;
};
