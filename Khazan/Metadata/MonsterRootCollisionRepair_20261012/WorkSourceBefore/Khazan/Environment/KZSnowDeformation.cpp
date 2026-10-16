#include "Environment/KZSnowDeformation.h"

#include "AbilitySystemComponent.h"
#include "AbilitySystemInterface.h"
#include "Abilities/GameplayAbility.h"
#include "KZGameplayTags.h"

#include "Components/MeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpression.h"
#include "Math/Float16Color.h"
#include "RHI.h"
#include "PhysicsEngine/BodySetup.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif
#include "ProfilingDebugging/CsvProfiler.h"

CSV_DEFINE_CATEGORY(HeinMachSnow,true);

AKZSnowDeformation::AKZSnowDeformation()
{
	PrimaryActorTick.bCanEverTick=true;
	PrimaryActorTick.TickGroup=TG_PostUpdateWork; // Observe finalized component/bone transforms on GT.
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("SnowFieldRoot")));
}

void AKZSnowDeformation::ConfigureMaterialDisplacement(UMaterial* Material,UMaterialExpression* Expression)
{
#if WITH_EDITOR
	if (Material && Expression && Expression->GetOuter()==Material)
	{
		Material->Modify();
		UMaterialEditorOnlyData* Data=Material->GetEditorOnlyData();
		Data->Displacement.Expression=Expression;
		Data->Displacement.OutputIndex=0;
		Material->PostEditChange();
	}
#endif
}

void AKZSnowDeformation::BeginPlay()
{
	Super::BeginPlay();
	FieldResolution=FMath::Clamp(FMath::DivideAndRoundUp(FieldResolution,TileSize)*TileSize,TileSize,4096);
	TexelSizeCm=FMath::Max(TexelSizeCm,0.5f);
	FieldTexture=UTexture2D::CreateTransient(FieldResolution,FieldResolution,PF_FloatRGBA,TEXT("HeinMachSnowField"));
	if (!FieldTexture) { SetActorTickEnabled(false); return; }
	FieldTexture->SRGB=false;
	FieldTexture->Filter=TF_Bilinear;
	FieldTexture->AddressX=TA_Wrap;
	FieldTexture->AddressY=TA_Wrap;
	FieldTexture->UpdateResource();
	BindSurfaces();
	FollowPlayer();
	UploadTiles();
}

void AKZSnowDeformation::RebuildSurfaceCollision(UStaticMesh* Mesh)
{
#if WITH_EDITOR
	if (!Mesh || !Mesh->GetPathName().StartsWith(TEXT("/Game/_Art/Player/Environment/Rendering/HeinMachSnow/"))) return;
	if (UBodySetup* Body=Mesh->GetBodySetup())
	{
		Mesh->Modify(); Body->Modify();
		Body->InvalidatePhysicsData();
		Body->CreatePhysicsMeshes();
		Mesh->CreateNavCollision(true);
		Mesh->PostEditChange();
	}
#endif
}

int32 AKZSnowDeformation::AuthorMergedWeaponContacts(const TArray<USkeletalMesh*>& Meshes)
{
#if WITH_EDITOR
	Modify();MergedWeaponContacts.Reset();
	for(USkeletalMesh* Mesh:Meshes)
	{
		if(!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty()) continue;
		const FReferenceSkeleton& Skeleton=Mesh->GetRefSkeleton();
		TArray<FTransform> Ref=Skeleton.GetRefBonePose();
		for(int32 I=0;I<Ref.Num();++I) if(Skeleton.GetParentIndex(I)>=0) Ref[I]=Ref[I]*Ref[Skeleton.GetParentIndex(I)];
		TMap<int32,TArray<FVector>> Vertices;
		for(const FSkelMeshSection& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
		for(const FSoftSkinVertex& Vertex:Section.SoftVertices)
		{
			uint32 Total=0,Weight=0;int32 Bone=INDEX_NONE;
			for(int32 I=0;I<UE_ARRAY_COUNT(Vertex.InfluenceWeights);++I)
			{
				Total+=Vertex.InfluenceWeights[I];
				if(Vertex.InfluenceWeights[I]>Weight && Section.BoneMap.IsValidIndex(Vertex.InfluenceBones[I]))
				{ Weight=Vertex.InfluenceWeights[I];Bone=Section.BoneMap[Vertex.InfluenceBones[I]]; }
			}
			if(Bone==INDEX_NONE || !Total || Weight*2<Total) continue;
			const FString Name=Skeleton.GetBoneName(Bone).ToString().ToLower();
			if(!Name.StartsWith(TEXT("weapon")) || Name.Contains(TEXT("pack"))) continue;
			Vertices.FindOrAdd(Bone).Add(Ref[Bone].InverseTransformPosition(FVector(Vertex.Position)));
		}
		for(const auto& Pair:Vertices)
		{
			if(Pair.Value.Num()<2) continue;
			FKZSnowWeaponPoints& Profile=MergedWeaponContacts.AddDefaulted_GetRef();
			Profile.Mesh=Mesh;Profile.Bone=Skeleton.GetBoneName(Pair.Key);
			FBox Bounds(ForceInit);for(const FVector& P:Pair.Value) Bounds+=P;
			Profile.Points.Add(Bounds.GetCenter());
			for(int32 Axis=0;Axis<3;++Axis)
			{
				FVector Min=Pair.Value[0],Max=Min;
				for(const FVector& P:Pair.Value) { if(P[Axis]<Min[Axis]) Min=P;if(P[Axis]>Max[Axis]) Max=P; }
				Profile.Points.AddUnique(Min);Profile.Points.AddUnique(Max);
			}
		}
	}
#endif
	return MergedWeaponContacts.Num();
}

void AKZSnowDeformation::BindSurfaces()
{
	TMap<UMaterialInterface*,int32> MaterialIndices;
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		TInlineComponentArray<UPrimitiveComponent*> Components(*It);
		for (UPrimitiveComponent* Component : Components)
		{
			if (!Component->ComponentHasTag(SurfaceTag)) continue;
			for (int32 Slot=0;Slot<Component->GetNumMaterials();++Slot)
			{
				UMaterialInterface* Original=Component->GetMaterial(Slot);
				if (!Original) continue;
				int32* Found=MaterialIndices.Find(Original);
				int32 Index;
				if (Found) Index=*Found;
				else
				{
					Index=SurfaceMaterials.Num();
					UMaterialInstanceDynamic* MID=UMaterialInstanceDynamic::Create(Original,this);
					MID->SetTextureParameterValue(TEXT("HM_SnowField"),FieldTexture);
					SurfaceMaterials.Add(MID); OriginalMaterials.Add(Original);
					MaterialIndices.Add(Original,Index);
				}
				Bindings.Add({Component,Slot,Index});
				Component->SetMaterial(Slot,SurfaceMaterials[Index]);
			}
		}
	}
}

FIntPoint AKZSnowDeformation::CellKey(FVector Position) const
{
	return {FMath::FloorToInt32(Position.X/TexelSizeCm),FMath::FloorToInt32(Position.Y/TexelSizeCm)};
}

FIntPoint AKZSnowDeformation::TileKey(FIntPoint Cell) const
{
	return {FMath::FloorToInt32(double(Cell.X)/TileSize),FMath::FloorToInt32(double(Cell.Y)/TileSize)};
}

const AKZSnowDeformation::FCell* AKZSnowDeformation::FindCell(FIntPoint Cell) const
{
	const FIntPoint Key=TileKey(Cell);
	const FTile* Tile=Tiles.Find(Key);
	if (!Tile) return nullptr;
	return &Tile->Cells[(Cell.Y-Key.Y*TileSize)*TileSize+Cell.X-Key.X*TileSize];
}

float AKZSnowDeformation::GetCompressionAtLocation(FVector Position) const
{
	const FCell* Cell=FindCell(CellKey(Position));
	return Cell && FMath::Abs(Cell->GroundZ-Position.Z)<LayerHeightToleranceCm ? Cell->Compression : 0.f;
}

void AKZSnowDeformation::StampSnow(FVector Position,FVector Forward,FVector2D RadiusCm,float Compression)
{
	if (!FieldTexture || RadiusCm.GetMin()<=0.f || Compression<=0.f) return;
	FVector2D Along(Forward.X,Forward.Y);
	Along=Along.GetSafeNormal();
	if (Along.IsNearlyZero()) Along=FVector2D(1,0);
	const FVector2D Across(-Along.Y,Along.X);
	const double Reach=RadiusCm.GetMax()*1.4;
	const FIntPoint Min=CellKey(Position-FVector(Reach,Reach,0));
	const FIntPoint Max=CellKey(Position+FVector(Reach,Reach,0));
	const FIntPoint First=TileKey(Min),Last=TileKey(Max);
	// Wide brushes look up each tile once rather than hashing it for every texel.
	for (int32 TY=First.Y;TY<=Last.Y;++TY)
	for (int32 TX=First.X;TX<=Last.X;++TX)
	{
		const FIntPoint Key(TX,TY);
		FTile* Tile=nullptr;
		bool bChanged=false;
		for (int32 Y=FMath::Max(Min.Y,TY*TileSize);Y<=FMath::Min(Max.Y,(TY+1)*TileSize-1);++Y)
		for (int32 X=FMath::Max(Min.X,TX*TileSize);X<=FMath::Min(Max.X,(TX+1)*TileSize-1);++X)
		{
			const FVector2D Delta((X+0.5)*TexelSizeCm-Position.X,(Y+0.5)*TexelSizeCm-Position.Y);
			const double U=FVector2D::DotProduct(Delta,Along)/RadiusCm.X;
			const double V=FVector2D::DotProduct(Delta,Across)/RadiusCm.Y;
			const double Radius=FMath::Sqrt(U*U+V*V);
			if (Radius>=1.4) continue;
			// Quintic shoulder is C2 at both ends, avoiding a hard triangular/box depression.
			const double T=FMath::Clamp((Radius-0.3)/0.7,0.,1.);
			const float Depth=FMath::Clamp(Compression,0.f,1.f)*(1.-T*T*T*(T*(T*6.-15.)+10.));
			const double Q=FMath::Clamp(1.-FMath::Square((Radius-1.05)/0.35),0.,1.);
			const float Rim=FMath::Clamp(Compression,0.f,1.f)*Q*Q;
			if (!Tile)
			{
				Tile=&Tiles.FindOrAdd(Key);
				if (Tile->Cells.IsEmpty()) Tile->Cells.SetNum(TileSize*TileSize);
				Tile->LastTouched=GetWorld()->GetTimeSeconds();
			}
			FCell& Cell=Tile->Cells[(Y-TY*TileSize)*TileSize+X-TX*TileSize];
			const FCell Before=Cell;
			if ((Cell.Compression>0.f || Cell.Rim>0.f) && FMath::Abs(Cell.GroundZ-Position.Z)>LayerHeightToleranceCm) Cell=FCell();
			Cell.Compression=FMath::Max(Cell.Compression,Depth); // Repeated footsteps cannot drill through the substrate.
			Cell.Rim=FMath::Max(Cell.Rim,Rim)*(1.f-Cell.Compression);
			Cell.GroundZ=Position.Z;
			bChanged |= Cell.Compression!=Before.Compression || Cell.Rim!=Before.Rim || Cell.GroundZ!=Before.GroundZ;
		}
		if (bChanged) DirtyTiles.Add(Key);
	}
}

bool AKZSnowDeformation::GroundContact(AActor* Source,FVector Position,float Reach,FHitResult& Hit) const
{
	FCollisionQueryParams Query(SCENE_QUERY_STAT(HeinMachSnowContact),true,Source);
	while (GetWorld()->LineTraceSingleByChannel(Hit,Position+FVector(0,0,Reach),
		Position-FVector(0,0,Reach),ECC_Visibility,Query))
	{
		if (!Hit.GetComponent() || !Hit.GetComponent()->ComponentHasTag(TEXT("HeinMachMicroDressing"))) break;
		Query.AddIgnoredComponent(Hit.GetComponent());
	}
	if (!Hit.bBlockingHit) return false;
	return Hit.GetComponent() && Hit.GetComponent()->ComponentHasTag(SurfaceTag) && Hit.ImpactNormal.Z>MinSurfaceNormalZ;
}

bool AKZSnowDeformation::WeaponSnowContact(AActor* Source,FVector Position,FHitResult& Hit) const
{
	// The broad ray locates the substrate only. It is never the blade's collision volume.
	// Displacement follows the surface normal, so the substrate can be farther away
	// along a vertical locator on slopes. The final normal-distance gate stays narrow.
	const float SubstrateReach=WeaponContactHeightCm/FMath::Max(MinSurfaceNormalZ,UE_SMALL_NUMBER);
	if (!GroundContact(Source,Position,SubstrateReach,Hit)) return false;
	double SurfaceHeight=0.;
	if (!GetSnowSurfaceHeight(Hit,SurfaceHeight)) return false;
	// Plane-normal distance accounts for sloped terrain. The small tolerance also
	// covers source weight mip/filter and face-vs-interpolated displacement normal differences.
	const double Distance=FVector::DotProduct(Position-Hit.ImpactPoint,Hit.ImpactNormal);
	return Distance>=-WeaponSurfaceContactToleranceCm && Distance<=SurfaceHeight+WeaponSurfaceContactToleranceCm;
}

bool AKZSnowDeformation::GetSnowSurfaceHeight(const FHitResult& Hit,double& SurfaceHeight) const
{
	if (!Hit.GetComponent()) return false;
	UMaterialInterface* Material=Hit.GetComponent()->GetMaterial(0);
	if (const UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(Material)) Material=MID->Parent;
	for (const FKZSnowSurfaceSamples& Profile:SurfaceContactSamples)
	{
		if (Profile.Material.Get()!=Material || Profile.Resolution.X<=0 || Profile.Resolution.Y<=0 ||
			Profile.UVScaleCm.X<=0. || Profile.UVScaleCm.Y<=0. ||
			Profile.Samples.Num()!=int64(Profile.Resolution.X)*Profile.Resolution.Y*3) continue;
		const double X=FMath::Clamp((Hit.ImpactPoint.X-Profile.UVOriginCm.X)/Profile.UVScaleCm.X*Profile.Resolution.X-0.5,0.,double(Profile.Resolution.X-1));
		const double Y=FMath::Clamp((Hit.ImpactPoint.Y-Profile.UVOriginCm.Y)/Profile.UVScaleCm.Y*Profile.Resolution.Y-0.5,0.,double(Profile.Resolution.Y-1));
		const int32 X0=FMath::FloorToInt(X),Y0=FMath::FloorToInt(Y);
		const int32 X1=FMath::Min(X0+1,Profile.Resolution.X-1),Y1=FMath::Min(Y0+1,Profile.Resolution.Y-1);
		auto Sample=[&](int32 Channel)
		{
			auto At=[&](int32 PX,int32 PY) { return Profile.Samples[(PY*Profile.Resolution.X+PX)*3+Channel]; };
			return FMath::Lerp(FMath::Lerp(double(At(X0,Y0)),double(At(X1,Y0)),X-X0),
				FMath::Lerp(double(At(X0,Y1)),double(At(X1,Y1)),X-X0),Y-Y0);
		};
		const double Total=Sample(1),Snow=Sample(2);
		if (Total<=UE_DOUBLE_SMALL_NUMBER || Snow<=UE_DOUBLE_SMALL_NUMBER) return false;
		const double Denominator=FMath::Max(Total,0.00001); // Existing material's division guard.
		const double Height=Sample(0)/Denominator;
		// Match the existing material's mip-0 field filter, half-float storage and
		// altitude/window validity, including small foot dents beneath the blade.
		const double FX=Hit.ImpactPoint.X/TexelSizeCm-0.5,FY=Hit.ImpactPoint.Y/TexelSizeCm-0.5;
		const FIntPoint K(FMath::FloorToInt(FX),FMath::FloorToInt(FY));
		auto FieldAt=[&](FIntPoint Key)
		{
			const FCell* Cell=FindCell(Key);
			if (!Cell) return FLinearColor::Transparent;
			return FLinearColor(FFloat16Color(FLinearColor(Cell->Compression,Cell->Rim,Cell->GroundZ,
				(Cell->Compression>0.f || Cell->Rim>0.f)?1.f:0.f)));
		};
		const FLinearColor Field=FMath::Lerp(
			FMath::Lerp(FieldAt(K),FieldAt(K+FIntPoint(1,0)),float(FX-K.X)),
			FMath::Lerp(FieldAt(K+FIntPoint(0,1)),FieldAt(K+FIntPoint(1,1)),float(FX-K.X)),float(FY-K.Y));
		const FVector2D Local(Hit.ImpactPoint.X/TexelSizeCm-WindowOrigin.X,Hit.ImpactPoint.Y/TexelSizeCm-WindowOrigin.Y);
		const double Edge=FMath::Min(FMath::Min(Local.X,Local.Y),FMath::Min(FieldResolution-Local.X,FieldResolution-Local.Y));
		const double Inside=FMath::Clamp(Edge/16.,0.,1.); // Existing FIELD_CODE's 16-texel window shoulder.
		const double Altitude=1.-FMath::SmoothStep(double(LayerHeightToleranceCm)*0.75,
			double(LayerHeightToleranceCm),FMath::Abs(Hit.ImpactPoint.Z-Field.B));
		const double Valid=Field.A*Inside*Inside*(3.-2.*Inside)*Altitude;
		SurfaceHeight=Height-FMath::Min(Height,double(Profile.DepthReferenceCm)*FMath::Clamp(double(Field.R),0.,1.))*Valid+
			Profile.RimHeightCm*FMath::Clamp(double(Field.G),0.,1.)*Valid*(Snow/Denominator);
		return true;
	}
	// Unauthored terrain must not produce a full crater from the broad substrate ray.
	return false;
}

void AKZSnowDeformation::ObserveCharacter(ACharacter* Character)
{
	USkeletalMeshComponent* Mesh=Character->GetMesh();
	if (!Mesh || !Mesh->GetSkeletalMeshAsset()) return;
	UCapsuleComponent* Capsule=Character->IsPlayerControlled() ? Character->GetCapsuleComponent():nullptr;
	const bool bUseCapsule=Capsule!=nullptr;
	if (bUseCapsule)
	{
		const double Radius=Capsule->GetScaledCapsuleRadius();
		const double HalfHeight=Capsule->GetScaledCapsuleHalfHeight();
		// ACharacter's movement capsule is upright. Use its physical bottom rather than
		// animation foot pivots; changing capsule scale automatically changes the brush.
		const FVector Bottom=Capsule->GetComponentLocation()-FVector(0,0,HalfHeight);
		float HeightBudget=0.f;
		for (const FKZSnowSurfaceSamples& Profile:SurfaceContactSamples)
			HeightBudget=FMath::Max(HeightBudget,Profile.DepthReferenceCm+Profile.RimHeightCm);
		const float Reach=(HeightBudget+FootContactHeightCm)/FMath::Max(MinSurfaceNormalZ,UE_SMALL_NUMBER);
		auto Contact=[&](FVector P,FHitResult& Hit,double& ContactRadius)
		{
			double SnowHeight=0.;
			if (Radius<=0. || Capsule->GetCollisionEnabled()==ECollisionEnabled::NoCollision ||
				!GroundContact(Character,P,Reach,Hit) || !GetSnowSurfaceHeight(Hit,SnowHeight)) return false;
			// Convert the local plane-normal surface height to height above the capsule
			// bottom. A grazing lower hemisphere produces a small disc; beyond its
			// equator the actual capsule radius bounds the whole contact envelope.
			const double Immersion=(SnowHeight-FVector::DotProduct(P-Hit.ImpactPoint,Hit.ImpactNormal))/Hit.ImpactNormal.Z;
			if (Immersion<=0.) return false;
			const double CapHeight=FMath::Min(Immersion,Radius);
			ContactRadius=FMath::Sqrt(CapHeight*(2.*Radius-CapHeight))+FMath::Max(0.f,PlayerCapsulePaddingCm);
			return ContactRadius>UE_DOUBLE_SMALL_NUMBER;
		};
		FContact& State=Contacts.FindOrAdd(Capsule).FindOrAdd(TEXT("SnowCapsule"));
		FHitResult Hit;double ContactRadius=0.;
		const bool bTouching=Contact(Bottom,Hit,ContactRadius);
		if (bTouching)
		{
			// The existing rim extends to 1.4 brush radii: divide it out so even its
			// faint edge stays inside the capsule contact plus its authored padding.
			const double Spacing=FMath::Max(double(TexelSizeCm),ContactRadius/1.4*0.25);
			const double Distance=FVector::Dist2D(Bottom,State.Previous);
			if (!State.bTouching || Distance>=Spacing)
			{
				const int32 Steps=State.bTouching && Distance<TeleportDistanceCm ?
					FMath::Max(1,FMath::CeilToInt(Distance/Spacing)):1;
				for (int32 I=1;I<=Steps;++I)
				{
					const FVector P=Steps>1 ? FMath::Lerp(State.Previous,Bottom,double(I)/Steps):Bottom;
					FHitResult Ground;double SampleRadius=0.;
					if (Contact(P,Ground,SampleRadius))
						StampSnow(Ground.ImpactPoint,Character->GetActorForwardVector(),FVector2D(SampleRadius/1.4,SampleRadius/1.4),FootCompression);
				}
				State.Previous=Bottom;
			}
		}
		else State.Previous=Bottom;
		State.bTouching=bTouching;
	}
	else if (UCapsuleComponent* PreviousCapsule=Character->GetCapsuleComponent())
		Contacts.Remove(PreviousCapsule); // Re-possession must not sweep from an old player contact.
	TMap<FName,FContact>& Feet=Contacts.FindOrAdd(Mesh);
	// Discover actual authored foot/paw bones. No Player/AI animation state copies.
	if (Feet.IsEmpty())
	{
		for (int32 I=0;I<Mesh->GetNumBones();++I)
		{
			const FName Name=Mesh->GetBoneName(I);
			const FString Text=Name.ToString().ToLower();
			const bool bFoot=Text.Contains(TEXT("foot")) || Text.Contains(TEXT("paw"));
			const bool bBody=Text.Contains(TEXT("pelvis")) || Text.Contains(TEXT("spine")) ||
				Text.EndsWith(TEXT("head")) || Text.EndsWith(TEXT("hand")) ||
				Text.EndsWith(TEXT("forearm")) || Text.EndsWith(TEXT("upperarm")) ||
				Text.EndsWith(TEXT("thigh")) || Text.EndsWith(TEXT("calf"));
			if ((bFoot || bBody) &&
				!Text.Contains(TEXT("ik_")) && !Text.Contains(TEXT("twist")) &&
				!Text.Contains(TEXT("water")) && !Text.Contains(TEXT("nub")))
			{
				FContact& Contact=Feet.Add(Name);
				Contact.bBody=bBody;
				if (!bFoot) continue;
				// Original human Toe0 is at the sole; Foot is an ankle pivot above the ground.
				for (int32 Child=0;Child<Mesh->GetNumBones();++Child)
				{
					const FName ChildName=Mesh->GetBoneName(Child);
					if (ChildName.ToString().EndsWith(TEXT("toe0")) && Mesh->GetParentBone(ChildName)==Name)
					{ Contact.SoleBone=ChildName;break; }
				}
			}
		}
	}
	for (auto& Pair:Feet)
	{
		if(Pair.Value.bWeapon) continue;
		if (bUseCapsule && !Pair.Value.bBody)
		{
			Pair.Value.bTouching=false;
			Pair.Value.bHasPrevious=false;
			continue;
		}
		FVector Position=Mesh->GetSocketLocation(Pair.Key);
		FVector Forward=Character->GetActorForwardVector();
		FContact& State=Pair.Value;
		if (!State.SoleBone.IsNone())
		{
			const FVector Sole=Mesh->GetSocketLocation(State.SoleBone);
			Forward=Sole-Position;
			Position=(Position+Sole)*0.5;
			Position.Z=Sole.Z;
		}
		FHitResult Hit;
		const float Reach=State.bBody ? BodyContactHeightCm:FootContactHeightCm;
		// Contact comes from the finalized pose, also during falling, knockdown and ragdoll/MOVE_None.
		bool bTouching=GroundContact(Character,Position,Reach,Hit);
		// A foot can straddle a stone and snow. The centre ray alone misses the
		// exposed toe contact during a roll; probe the actual sole as well.
		if(!bTouching && !State.SoleBone.IsNone())
		{
			const FVector Sole=Mesh->GetSocketLocation(State.SoleBone);
			if(GroundContact(Character,Sole,Reach,Hit)) { Position=Sole;bTouching=true; }
		}
		if (bTouching)
		{
			const double Distance=FVector::Dist2D(Position,State.Previous);
			// Technical overlap spacing: at most one quarter of the smaller brush radius.
			const double Spacing=FMath::Max(double(TexelSizeCm),double((State.bBody ? BodyRadiusCm:FootRadiusCm).GetMin())*0.25);
			if (!State.bTouching || Distance>=Spacing)
			{
				const int32 Steps=State.bTouching && Distance<TeleportDistanceCm ?
					FMath::Max(1,FMath::CeilToInt(Distance/Spacing)):1;
				for (int32 I=1;I<=Steps;++I)
				{
					FVector P=Steps>1 ? FMath::Lerp(State.Previous,Position,double(I)/Steps):Position;
					FHitResult Contact;
					if (GroundContact(Character,P,Reach,Contact))
						StampSnow(Contact.ImpactPoint,Forward,State.bBody ? BodyRadiusCm:FootRadiusCm,
							State.bBody ? 1.f:FootCompression);
				}
				State.Previous=Position;
			}
		}
		else State.Previous=Position;
		State.bTouching=bTouching;
	}

	// Observe the existing GAS execution; Attack is an Ability asset tag, not an owned state tag.
	bool bAttacking=false;
	if (const IAbilitySystemInterface* Interface=Cast<IAbilitySystemInterface>(Character))
		if (UAbilitySystemComponent* ASC=Interface->GetAbilitySystemComponent())
		{
			FScopedAbilityListLock Lock(*ASC);
			for (const FGameplayAbilitySpec& Spec:ASC->GetActivatableAbilities())
				if (Spec.IsActive() && Spec.Ability && Spec.Ability->GetAssetTags().HasTag(KZGameplayTags::Ability_Action_Attack))
				{ bAttacking=true;break; }
		}
	TInlineComponentArray<UMeshComponent*> Components(Character);
	for (UMeshComponent* Weapon:Components)
	{
		if (!bAttacking)
		{
			// Merged weapons share the body mesh's map: retain its foot/body history.
			if (TMap<FName,FContact>* History=Contacts.Find(Weapon))
				for (auto It=History->CreateIterator();It;++It) if (It.Value().bWeapon) It.RemoveCurrent();
			continue;
		}
		UStaticMeshComponent* Static=Cast<UStaticMeshComponent>(Weapon);
		USkeletalMeshComponent* Skeletal=Cast<USkeletalMeshComponent>(Weapon);
		TArray<FVector> Positions;
		if(Skeletal) for(const FKZSnowWeaponPoints& Profile:MergedWeaponContacts)
			if(Profile.Mesh.Get()==Skeletal->GetSkeletalMeshAsset())
			{
				const FTransform Bone=Skeletal->GetSocketTransform(Profile.Bone,RTS_World);
				for(const FVector& P:Profile.Points) Positions.Add(Bone.TransformPosition(P));
			}
		if(Positions.IsEmpty() && Weapon==Mesh) continue;
		FBox Box;
		FString AssetName;
		if (Static && Static->GetStaticMesh()) { Box=Static->GetStaticMesh()->GetBoundingBox();AssetName=Static->GetStaticMesh()->GetName(); }
		else if (Skeletal && Skeletal->GetSkeletalMeshAsset()) { Box=Skeletal->GetSkeletalMeshAsset()->GetImportedBounds().GetBox();AssetName=Skeletal->GetSkeletalMeshAsset()->GetName(); }
		else continue;
		if (Positions.IsEmpty() && !Weapon->IsVisible()) { Contacts.Remove(Weapon);continue; }
		const FString Name=Weapon->GetName()+AssetName;
		if (Positions.IsEmpty() && !Weapon->ComponentHasTag(TEXT("SnowWeapon")) && !Name.Contains(TEXT("sword")) &&
			!Name.Contains(TEXT("axe")) && !Name.Contains(TEXT("halberd")) && !Name.Contains(TEXT("weapon"))) continue;
		// Armor shares family names such as EmpireSword; only attached equipment is a weapon.
		if (Positions.IsEmpty() && !Weapon->ComponentHasTag(TEXT("SnowWeapon")) && Weapon->GetAttachSocketName().IsNone()) continue;
		const FVector Extent=Box.GetExtent();
		const int32 Axis=Extent.X>=Extent.Y && Extent.X>=Extent.Z ? 0 : (Extent.Y>=Extent.Z ? 1:2);
		TMap<FName,FContact>& Points=Contacts.FindOrAdd(Weapon);
		if(Positions.IsEmpty()) for(int32 I=0;I<5;++I)
		{
			FVector Local=Box.GetCenter();
			Local[Axis]+=(double(I)/4.-0.5)*Extent[Axis]*2.;
			Positions.Add(Weapon->GetComponentTransform().TransformPosition(Local));
		}
		for(int32 I=0;I<Positions.Num();++I)
		{
			const FVector Position=Positions[I];
			FContact& State=Points.FindOrAdd(FName(*FString::Printf(TEXT("SnowWeapon_%d"),I)));
			State.bWeapon=true;
			const double Distance=FVector::Dist(Position,State.Previous);
			// Sweep resolution follows contact tolerance, independently of crater radius.
			const double Spacing=FMath::Max(double(TexelSizeCm),double(WeaponSurfaceContactToleranceCm));
			if (State.bHasPrevious && Distance>=Spacing && Distance<TeleportDistanceCm)
			{
				const int32 Steps=FMath::CeilToInt(Distance/Spacing);
				for (int32 S=1;S<=Steps;++S)
				{
					const FVector P=FMath::Lerp(State.Previous,Position,double(S)/Steps);
					FHitResult Hit;
					if (WeaponSnowContact(Character,P,Hit) && GetCompressionAtLocation(Hit.ImpactPoint)<WeaponCompression)
						StampSnow(Hit.ImpactPoint,Position-State.Previous,FVector2D(WeaponRadiusCm,WeaponRadiusCm),WeaponCompression);
				}
			}
			FHitResult Current;
			const bool bGrounded=WeaponSnowContact(Character,Position,Current);
			if(bGrounded && !State.bTouching && GetCompressionAtLocation(Current.ImpactPoint)<WeaponCompression)
				StampSnow(Current.ImpactPoint,Character->GetActorForwardVector(),FVector2D(WeaponRadiusCm,WeaponRadiusCm),WeaponCompression);
			if(!State.bHasPrevious || Distance>=Spacing || bGrounded!=State.bTouching) State.Previous=Position;
			State.bTouching=bGrounded;State.bHasPrevious=true;
		}
	}
}

void AKZSnowDeformation::FollowPlayer()
{
	ACharacter* Player=UGameplayStatics::GetPlayerCharacter(this,0);
	const FIntPoint Center=CellKey(Player ? Player->GetActorLocation():GetActorLocation());
	const FIntPoint Desired(TileKey(Center).X*TileSize-FieldResolution/2,
		TileKey(Center).Y*TileSize-FieldResolution/2);
	if (bWindowInitialized && FMath::Abs(Center.X-WindowOrigin.X-FieldResolution/2)<FieldResolution/4 &&
		FMath::Abs(Center.Y-WindowOrigin.Y-FieldResolution/2)<FieldResolution/4) return;
	// Toroidal texture: retain overlapping GPU tiles and publish only newly exposed strips.
	const FIntPoint Previous=WindowOrigin;
	const bool bHadWindow=bWindowInitialized;
	WindowOrigin=Desired; bWindowInitialized=true;
	const int32 Across=FieldResolution/TileSize;
	const FIntPoint First=TileKey(WindowOrigin),OldFirst=TileKey(Previous);
	for(int32 Y=0;Y<Across;++Y) for(int32 X=0;X<Across;++X)
	{
		const FIntPoint Key=First+FIntPoint(X,Y);
		if(!bHadWindow || Key.X<OldFirst.X || Key.Y<OldFirst.Y ||
			Key.X>=OldFirst.X+Across || Key.Y>=OldFirst.Y+Across) DirtyTiles.Add(Key);
	}
	SetFieldParameters();
}

void AKZSnowDeformation::SetFieldParameters()
{
	for (UMaterialInstanceDynamic* MID:SurfaceMaterials)
	{
		MID->SetVectorParameterValue(TEXT("HM_FieldTransform"),FLinearColor(
			WindowOrigin.X*TexelSizeCm,WindowOrigin.Y*TexelSizeCm,
			FieldResolution*TexelSizeCm,TexelSizeCm));
		MID->SetScalarParameterValue(TEXT("HM_LayerHeightToleranceCm"),LayerHeightToleranceCm);
	}
}

void AKZSnowDeformation::UploadTiles()
{
	const int32 Across=FieldResolution/TileSize;
	auto Wrap=[Across](int32 V) { return (V%Across+Across)%Across; };
	TArray<FUpdateTextureRegion2D> EmptyRegions;
	struct FUpload { int32 X,Y;FFloat16Color* Data; };
	TArray<FUpload> Pending;
	const bool bFullClear=bClearTexture;
	auto Upload=[this](int32 X,int32 Y,int32 Width,int32 Height,FFloat16Color* Data)
	{
		auto* Region=new FUpdateTextureRegion2D(X,Y,0,0,Width,Height);
		FieldTexture->UpdateTextureRegions(0,1,Region,Width*sizeof(FFloat16Color),sizeof(FFloat16Color),
			reinterpret_cast<uint8*>(Data),[](uint8* Bytes,const FUpdateTextureRegion2D* Update)
			{ delete[] reinterpret_cast<FFloat16Color*>(Bytes); delete Update; });
	};
	if (bClearTexture)
	{
		for(int32 Y=0;Y<Across;++Y) for(int32 X=0;X<Across;++X)
			EmptyRegions.Emplace(X*TileSize,Y*TileSize,0,0,TileSize,TileSize);
		bClearTexture=false;
	}
	for (FIntPoint Key:DirtyTiles)
	{
		const FIntPoint Local=Key*TileSize-WindowOrigin;
		if (Local.X<0 || Local.Y<0 || Local.X>=FieldResolution || Local.Y>=FieldResolution) continue;
		const int32 X=Wrap(Key.X)*TileSize,Y=Wrap(Key.Y)*TileSize;
		const FTile* Tile=Tiles.Find(Key);
		if(!Tile) { if(!bFullClear) EmptyRegions.Emplace(X,Y,0,0,TileSize,TileSize);continue; }
		auto* Data=new FFloat16Color[TileSize*TileSize];
		for (int32 I=0;I<TileSize*TileSize;++I)
		{
			const FCell Cell=Tile ? Tile->Cells[I]:FCell();
			Data[I]=FFloat16Color(FLinearColor(Cell.Compression,Cell.Rim,Cell.GroundZ,
				(Cell.Compression>0.f || Cell.Rim>0.f)?1.f:0.f));
		}
		Pending.Add({X,Y,Data});
	}
	if(!EmptyRegions.IsEmpty())
	{
		auto* Clear=new FFloat16Color[TileSize*TileSize];
		FMemory::Memzero(Clear,TileSize*TileSize*sizeof(FFloat16Color));
		auto* Regions=new FUpdateTextureRegion2D[EmptyRegions.Num()];
		FMemory::Memcpy(Regions,EmptyRegions.GetData(),EmptyRegions.Num()*sizeof(FUpdateTextureRegion2D));
		FieldTexture->UpdateTextureRegions(0,EmptyRegions.Num(),Regions,TileSize*sizeof(FFloat16Color),sizeof(FFloat16Color),
			reinterpret_cast<uint8*>(Clear),[](uint8* Bytes,const FUpdateTextureRegion2D* Update)
			{ delete[] reinterpret_cast<FFloat16Color*>(Bytes);delete[] Update; });
	}
	for(const FUpload& Job:Pending) Upload(Job.X,Job.Y,TileSize,TileSize,Job.Data);
	DirtyTiles.Empty();
}

void AKZSnowDeformation::ClearSnow()
{
	Tiles.Empty(); DirtyTiles.Empty(); Contacts.Empty(); bClearTexture=true;
}

void AKZSnowDeformation::Tick(float DeltaSeconds)
{
	CSV_SCOPED_TIMING_STAT(HeinMachSnow,SnowTick);
	Super::Tick(DeltaSeconds);
	if (!FieldTexture) return;
	FollowPlayer();
	for (TActorIterator<ACharacter> It(GetWorld());It;++It) ObserveCharacter(*It);
	for (auto It=Contacts.CreateIterator();It;++It) if (!It.Key().IsValid()) It.RemoveCurrent();
	while (Tiles.Num()>MaxCachedTiles)
	{
		FIntPoint Oldest=FIntPoint::ZeroValue; double Time=TNumericLimits<double>::Max(); bool bFound=false;
		for (const auto& Pair:Tiles)
		{
			const FIntPoint P=Pair.Key*TileSize-WindowOrigin;
			if (P.X>=0 && P.Y>=0 && P.X<FieldResolution && P.Y<FieldResolution) continue;
			if (Pair.Value.LastTouched<Time) { Time=Pair.Value.LastTouched;Oldest=Pair.Key;bFound=true; }
		}
		if (!bFound) break;
		Tiles.Remove(Oldest);
	}
	UploadTiles();
}

void AKZSnowDeformation::EndPlay(const EEndPlayReason::Type Reason)
{
	for (const FBinding& Binding:Bindings)
		if (UPrimitiveComponent* Component=Binding.Component.Get();Component &&
			Component->GetMaterial(Binding.Slot)==SurfaceMaterials[Binding.MaterialIndex])
			Component->SetMaterial(Binding.Slot,OriginalMaterials[Binding.MaterialIndex]);
	Bindings.Empty(); Contacts.Empty(); Tiles.Empty(); DirtyTiles.Empty();
	SurfaceMaterials.Empty(); OriginalMaterials.Empty(); FieldTexture=nullptr;
	Super::EndPlay(Reason);
}
