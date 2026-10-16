// Development-only GPU geometry and actual contact integration test in HeinMach.
// Fixture distances/times below are test inputs, not original gameplay tuning.
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Environment/KZSnowDeformation.h"
#include "Character/KZPlayer.h"
#include "Character/KZMonster.h"
#include "AI/KZMonsterAIController.h"
#include "Components/StateTreeAIComponent.h"
#include "Ability/KZAbilitySystemComponent.h"
#include "Ability/PlayerAbility/KZDodgeAbility.h"
#include "Ability/Combo/KZComboActionAbility.h"
#include "Attribute/KZAttributeSet.h"
#include "KZGameplayTags.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/MeshComponent.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Engine/GameViewportClient.h"
#include "HighResScreenshot.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace
{
class FSnowPIECommand : public IAutomationLatentCommand
{
public:
 FSnowPIECommand(FAutomationTestBase* InTest, AKZPlayer* InPlayer, AKZSnowDeformation* InSnow)
  : Test(InTest),Player(InPlayer),Snow(InSnow),Deadline(FPlatformTime::Seconds()+420.) {}
 bool Update() override
 {
  if (!Player.IsValid() || !Snow.IsValid() || FPlatformTime::Seconds()>Deadline)
  { Test->AddError(TEXT("Snow PIE expired or failed to advance"));Cleanup();return true; }
  UWorld* W=Player->GetWorld(); const double Now=W->GetTimeSeconds();
  if (bMove) Player->HandleInputMove(FVector2D(0,1),FRotator::ZeroRotator);
  if(bDodgeReady && Stage==11 && Player->GetCharacterMovement()->IsMovingOnGround())
  {
   const FVector Bottom=Player->GetActorLocation()-FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
   FHitResult Hit;
   if(SurfaceHit(Bottom,Hit))
   {
    MinDodgeCapsuleGap=FMath::Min(MinDodgeCapsuleGap,Bottom.Z-Hit.ImpactPoint.Z);
    ++DodgeContactFrames;
    MaxDodgeCompression=FMath::Max(MaxDodgeCompression,Snow->GetCompressionAtLocation(Hit.ImpactPoint));
   }
  }
  if (bMonsterMove && Monster.IsValid()) Monster->AddMovementInput(FVector::ForwardVector);
  if (bWeaponSweep && Weapon.IsValid())
  {
   const float Alpha=FMath::Clamp(float((Now-SweepStart)/1.0),0.f,1.f);
   SetWeapon(WeaponPoint+FVector(0,Alpha*150.f,bAirSweep?200.f:1.f));
  }
  if (Now<Next) return false;
  switch (Stage++)
  {
  case 0:
  {
   SavedLocation=Player->GetActorLocation();SavedRotation=Player->GetActorRotation();
   SavedTickOption=Player->GetMesh()->VisibilityBasedAnimTickOption;
   SavedPlayerPause=Player->GetMesh()->bPauseAnims;
   SavedPlayerMeshRelative=Player->GetMesh()->GetRelativeTransform();bSavedPlayerMeshRelative=true;
   Player->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
   SavedView=Cast<APlayerController>(Player->GetController())->GetViewTarget();
   // Find exposed terrain near the source DeepSnow weight region; rocks occlude some texels.
   FHitResult Hit;
   bool bGroundHit=false;double BestDistance=TNumericLimits<double>::Max();
   for(int32 X=-8;X<=8;++X) for(int32 Y=-8;Y<=8;++Y)
   {
    FHitResult Candidate;const FVector P(12100+X*100,13500+Y*100,0);
    if(W->LineTraceSingleByChannel(Candidate,P+FVector(0,0,2000),P-FVector(0,0,2000),ECC_Visibility,
       FCollisionQueryParams(NAME_None,true,Player.Get())) && Candidate.GetComponent() &&
       Candidate.GetComponent()->ComponentHasTag(Snow->SurfaceTag) && X*X+Y*Y<BestDistance)
    { Hit=Candidate;bGroundHit=true;BestDistance=X*X+Y*Y; }
   }
   Test->AddInfo(FString::Printf(TEXT("SnowGround blocking=%d actor=%s component=%s point=%s normal=%s tag=%d"),
       bGroundHit,*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),*Hit.ImpactPoint.ToString(),*Hit.ImpactNormal.ToString(),
       Hit.GetComponent() && Hit.GetComponent()->ComponentHasTag(Snow->SurfaceTag)));
   if (!bGroundHit ||
       !Hit.GetComponent() || !Hit.GetComponent()->ComponentHasTag(Snow->SurfaceTag))
   { Test->AddError(TEXT("DeepSnow QA coordinate is not an exposed delivered snow surface"));Cleanup();return true; }
   Point=Hit.ImpactPoint;
   // Align the tiny foot fixture with a field cell centre; sample phase must
   // not move its flat core away from the scene-depth probe.
   Point.X=(FMath::FloorToDouble(Point.X/Snow->TexelSizeCm)+0.5)*Snow->TexelSizeCm;
   Point.Y=(FMath::FloorToDouble(Point.Y/Snow->TexelSizeCm)+0.5)*Snow->TexelSizeCm;
   FHitResult AlignedHit;
   if(W->LineTraceSingleByChannel(AlignedHit,Point+FVector(0,0,100),Point-FVector(0,0,100),ECC_Visibility,
      FCollisionQueryParams(NAME_None,true,Player.Get())) && AlignedHit.GetComponent() && AlignedHit.GetComponent()->ComponentHasTag(Snow->SurfaceTag))
    Point.Z=AlignedHit.ImpactPoint.Z;
   SnowGroundNormal=AlignedHit.ImpactNormal;
   // This editor fixture reads the delivered full-fallback mesh once. Nanite
   // displaces along interpolated vertex normals, rather than the hit face normal.
   const auto* GroundMesh=Cast<UStaticMeshComponent>(AlignedHit.GetComponent());
   const FStaticMeshRenderData* RenderData=GroundMesh && GroundMesh->GetStaticMesh() ? GroundMesh->GetStaticMesh()->GetRenderData():nullptr;
   if(!RenderData || RenderData->LODResources.Num()==0)
   { Test->AddError(TEXT("Snow GPU fixture needs its delivered mesh render data"));Cleanup();return true; }
   const auto& LOD=RenderData->LODResources[0];
   const FIndexArrayView Indices=LOD.IndexBuffer.GetArrayView();
   const FVector LocalPoint=GroundMesh->GetComponentTransform().InverseTransformPosition(Point);
   FVector LocalSmoothNormal=FVector::ZeroVector,ClosestLocal=FVector::ZeroVector;
   double NearestTriangleDistance=TNumericLimits<double>::Max();
   for(int32 I=0;I+2<Indices.Num();I+=3)
   {
    const uint32 A=Indices[I],B=Indices[I+1],C=Indices[I+2];
    const FVector PA(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(A));
    const FVector PB(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(B));
    const FVector PC(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(C));
    if(FVector::CrossProduct(PB-PA,PC-PA).IsNearlyZero(UE_DOUBLE_SMALL_NUMBER)) continue;
    const FVector Closest=FMath::ClosestPointOnTriangleToPoint(LocalPoint,PA,PB,PC);
    const double Distance=FVector::DistSquared(LocalPoint,Closest);
    if(Distance>=NearestTriangleDistance) continue;
    const FVector Weights=FMath::ComputeBaryCentric2D(Closest,PA,PB,PC);
    const FVector4f NA=LOD.VertexBuffers.StaticMeshVertexBuffer.VertexTangentZ(A);
    const FVector4f NB=LOD.VertexBuffers.StaticMeshVertexBuffer.VertexTangentZ(B);
    const FVector4f NC=LOD.VertexBuffers.StaticMeshVertexBuffer.VertexTangentZ(C);
    LocalSmoothNormal=FVector(NA.X,NA.Y,NA.Z)*Weights.X+FVector(NB.X,NB.Y,NB.Z)*Weights.Y+FVector(NC.X,NC.Y,NC.Z)*Weights.Z;
    ClosestLocal=Closest;NearestTriangleDistance=Distance;
   }
   const FVector SmoothNormal=GroundMesh->GetComponentTransform().TransformVector(LocalSmoothNormal).GetSafeNormal();
   if(SmoothNormal.IsNearlyZero())
   { Test->AddError(TEXT("Snow GPU fixture could not interpolate the delivered mesh normal"));Cleanup();return true; }
   Test->AddInfo(FString::Printf(TEXT("SnowDisplacementNormal face=%s smooth=%s meshDistanceCm=%.4f"),
      *AlignedHit.ImpactNormal.ToString(),*SmoothNormal.ToString(),FVector::Distance(Point,GroundMesh->GetComponentTransform().TransformPosition(ClosestLocal))));
   const UMaterialInterface* SnowMaterial=Hit.GetComponent()->GetMaterial(0);
   if(!SnowMaterial || !SnowMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("SnowHeightCm_DeepSnow")),ExpectedDepth) || ExpectedDepth<=0.f)
   { Test->AddError(TEXT("DeepSnow material must expose its authored thickness for GPU validation"));Cleanup();return true; }
   if(!SnowMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("HM_DepthReferenceCm_User")),DepthReferenceCm) || DepthReferenceCm<=0.f)
   { Test->AddError(TEXT("Snow material must expose its cm compression reference"));Cleanup();return true; }
   Player->HandleInputMoveReleased();Player->GetCharacterMovement()->DisableMovement();
   Snow->ClearSnow();
   Camera=W->SpawnActor<ACameraActor>(); Camera->GetCameraComponent()->FieldOfView=55.f;
   Camera->GetCameraComponent()->bConstrainAspectRatio=false;
   Camera->SetActorLocation(Point+FVector(0,-80,300));
   Camera->SetActorRotation((Point-Camera->GetActorLocation()).Rotation());
   Cast<APlayerController>(Player->GetController())->SetViewTarget(Camera.Get());
   Capture=W->SpawnActor<ASceneCapture2D>();
   // Nanite displaces along the mesh normal. A vertical ray can miss a small
   // footprint on a thick sloped layer because the raised snow moves sideways.
   Capture->SetActorLocation(Point+SmoothNormal*800.f);
   Capture->SetActorRotation((Point-Capture->GetActorLocation()).Rotation());
   Target=NewObject<UTextureRenderTarget2D>(Capture.Get());Target->RenderTargetFormat=RTF_RGBA16f;
   Target->InitAutoFormat(128,128);Target->UpdateResourceImmediate();
   auto* C=Capture->GetCaptureComponent2D();C->TextureTarget=Target;
   // Narrow QA optics keep the centre depth ray inside the small foot's flat core.
   C->CaptureSource=SCS_SceneDepth;C->ProjectionType=ECameraProjectionMode::Perspective;C->FOVAngle=4.f;
   C->bCaptureEveryFrame=false;C->bCaptureOnMovement=false;C->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
   for (TActorIterator<AActor> It(W);It;++It)
   {
    TInlineComponentArray<UPrimitiveComponent*> Parts(*It);
    for (auto* P:Parts) if (P->ComponentHasTag(Snow->SurfaceTag)) C->ShowOnlyComponent(P);
   }
   Next=Now+3.;break;
  }
  case 1: Capture->GetCaptureComponent2D()->CaptureScene();Shot(TEXT("Snow_Untouched.png"));Next=Now+0.5;break;
  case 2:
   if(PartialProbe==0)
   { Before=DepthRow();BeforeFootGrid=DepthGrid();Snow->StampSnow(Point,FVector::ForwardVector,Snow->FootRadiusCm,Snow->FootCompression);
     PartialProbe=1;--Stage;Next=Now+1.;break; }
   if(PartialProbe==1)
   { Capture->GetCaptureComponent2D()->CaptureScene();Shot(TEXT("Snow_FootCompressed.png"));
     PartialProbe=2;--Stage;Next=Now+0.5;break; }
   { const auto Foot=DepthGrid();FootDepth=-1.f;
     // Collision triangle normals and Nanite's interpolated vertex normals differ.
     // Read the actual deepest part of this isolated small brush rather than a
     // single ray that can hit its rim. The untouched capture supplies each baseline.
     if(Foot.Num()==128*128 && BeforeFootGrid.Num()==Foot.Num())
      for(int32 I=0;I<Foot.Num();++I) FootDepth=FMath::Max(FootDepth,Foot[I]-BeforeFootGrid[I]);
     Test->AddInfo(FString::Printf(TEXT("SnowFootGPU dentCm=%.3f layerMaximumCm=%.3f compression=%.3f"),FootDepth,ExpectedDepth,Snow->FootCompression));
     Test->TestTrue(TEXT("Foot field retains partial rather than full compression"),FMath::Abs(Snow->GetCompressionAtLocation(Point)-Snow->FootCompression)<0.001f);
     Test->TestEqual(TEXT("Isolated foot leaves snow untouched beyond its full length envelope"),
      Snow->GetCompressionAtLocation(Point+FVector(Snow->FootRadiusCm.X*1.4+Snow->TexelSizeCm*2,0,0)),0.f);
     Test->TestEqual(TEXT("Isolated foot leaves snow untouched beyond its full width envelope"),
      Snow->GetCompressionAtLocation(Point+FVector(0,Snow->FootRadiusCm.Y*1.4+Snow->TexelSizeCm*2,0)),0.f); }
   Snow->StampSnow(Point,FVector::ForwardVector,FVector2D(Snow->WeaponRadiusCm,Snow->WeaponRadiusCm),Snow->WeaponCompression);Next=Now+1.;break;
  case 3:
   Capture->GetCaptureComponent2D()->CaptureScene();Shot(TEXT("Snow_Compressed.png"));Next=Now+0.5;break;
  case 4:
  {
   if(ProbeStage==0)
   {
    Test->AddInfo(FString::Printf(TEXT("SnowCapture transform=%s materialScale=%f center=%f"),*Capture->GetTransform().ToString(),
        Capture->GetCaptureComponent2D()->ShowOnlyComponents[0].Get()->GetMaterial(0)->GetDisplacementScaling().Magnitude,
        Capture->GetCaptureComponent2D()->ShowOnlyComponents[0].Get()->GetMaterial(0)->GetDisplacementScaling().Center));
   }
   if(ProbeStage==0) { ProbeStage=1;GEngine->Exec(W,TEXT("r.Nanite 0"));--Stage;Next=Now+0.5;break; }
   if(ProbeStage==1) { Capture->GetCaptureComponent2D()->CaptureScene();ProbeStage=2;--Stage;Next=Now+0.5;break; }
   if(ProbeStage==2) { const auto Flat=DepthRow();SubstrateDepth=Flat[64];Test->AddInfo(FString::Printf(TEXT("SnowFallbackDepth=%.3f"),SubstrateDepth));
       GEngine->Exec(W,TEXT("r.Nanite 1"));ProbeStage=3;--Stage;Next=Now+0.5;break; }
   if(ProbeStage==3) { Capture->GetCaptureComponent2D()->CaptureScene();ProbeStage=4;--Stage;Next=Now+0.5;break; }
   After=DepthRow();
   Test->TestEqual(TEXT("Depth capture sample count"),Before.Num(),128);
   if (Before.Num()!=128 || After.Num()!=128) { Cleanup();return true; }
   DepthChange=After[64]-Before[64];
   Test->AddInfo(FString::Printf(TEXT("SnowGPU before=%.3f after=%.3f dentCm=%.3f at=%s"),Before[64],After[64],DepthChange,*Point.ToString()));
   // Source masks mix thinner layers: requested cm depths stop at the physical substrate.
   const float ActualLayerCm=SubstrateDepth-Before[64];
   const float ExpectedFootCm=FMath::Min(ActualLayerCm,DepthReferenceCm*Snow->FootCompression);
   const float ExpectedWeaponCm=FMath::Min(ActualLayerCm,DepthReferenceCm*Snow->WeaponCompression);
   const float ExpectedResidualCm=FMath::Max(ActualLayerCm-ExpectedWeaponCm,0.f);
   Test->AddInfo(FString::Printf(TEXT("SnowDepthTargets layerCm=%.3f footCm=%.3f weaponCm=%.3f residualCm=%.3f"),ActualLayerCm,ExpectedFootCm,ExpectedWeaponCm,ExpectedResidualCm));
   Test->TestTrue(TEXT("Untouched weighted snow stays within its authored maximum"),ActualLayerCm>0.f && ActualLayerCm<=ExpectedDepth+1.f);
   Test->TestTrue(TEXT("GPU foot depression reaches its requested centimetre depth"),FMath::Abs(FootDepth-ExpectedFootCm)<2.f);
   Test->TestTrue(TEXT("GPU weapon crater reaches its requested centimetre depth"),FMath::Abs(DepthChange-ExpectedWeaponCm)<1.5f && DepthChange>FootDepth);
   Test->TestTrue(TEXT("Weapon crater leaves the expected snow above the substrate"),FMath::Abs((SubstrateDepth-After[64])-ExpectedResidualCm)<1.5f);
   Test->TestTrue(TEXT("Weapon field uses the authored partial compression"),FMath::Abs(Snow->GetCompressionAtLocation(Point)-Snow->WeaponCompression)<0.001f);
   for(int32 I=0;I<50;++I) Snow->StampSnow(Point,FVector::ForwardVector,FVector2D(Snow->WeaponRadiusCm,Snow->WeaponRadiusCm),Snow->WeaponCompression);
   // Move the actual player window away and back; GPU republication must restore the dent.
   Player->SetActorLocation(SavedLocation+FVector(6000,0,500),false,nullptr,ETeleportType::TeleportPhysics);
   Next=Now+0.5;break;
  }
  case 5: Player->SetActorLocation(SavedLocation,false,nullptr,ETeleportType::TeleportPhysics);Next=Now+0.5;break;
  case 6: Capture->GetCaptureComponent2D()->CaptureScene();Next=Now+0.5;break;
  case 7:
  {
   if(FullClearProbe==1)
   { Capture->GetCaptureComponent2D()->CaptureScene();FullClearProbe=2;--Stage;Next=Now+0.5;break; }
   if(FullClearProbe==2)
   {
    const auto Full=DepthRow();
    Test->TestTrue(TEXT("Full-clear render surface agrees with CMC collision"),Full.Num()==128 && FMath::Abs(800.f-Full[64])<1.f);
    FullClearProbe=3;
   }
   else
   {
   const TArray<float> Recenter=DepthRow();
   Test->TestTrue(TEXT("Scroll/repeat preserves bounded GPU dent"),Recenter.Num()==128 && FMath::Abs(Recenter[64]-After[64])<1.f);
   Snow->StampSnow(Point,FVector::ForwardVector,FVector2D(Snow->WeaponRadiusCm,Snow->WeaponRadiusCm));
   FullClearProbe=1;--Stage;Next=Now+1.;break;
   }
   Snow->ClearSnow();
   Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+1),false,nullptr,ETeleportType::TeleportPhysics);
   Player->SetActorRotation(FRotator::ZeroRotator);Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
   WalkStart=Player->GetActorLocation();Next=Now+0.5;break;
  }
  case 8:
  {
   // Geometry fixture: keep the actual controlled capsule on snow while all
   // evaluated foot/body bones are raised clear. No field is stamped by this test.
   if(CapsuleProbe==0)
   {
    Player->GetCharacterMovement()->DisableMovement();
    Player->GetMesh()->bPauseAnims=true;
    Player->GetMesh()->SetRelativeLocation(SavedPlayerMeshRelative.GetLocation()+FVector(0,0,500));
    Player->GetMesh()->RefreshBoneTransforms();
    Snow->ClearSnow();CapsuleProbe=1;Stage=8;Next=Now+0.25;break;
   }
   if(CapsuleProbe==1)
   {
    const double Radius=Player->GetCapsuleComponent()->GetScaledCapsuleRadius()+Snow->PlayerCapsulePaddingCm;
    CapsuleCenter=Player->GetActorLocation();
    FHitResult CenterHit,NearHit,OutsideHit;
    const double NearRadius=Radius/1.4-Snow->TexelSizeCm*2;
    if(!SurfaceHit(CapsuleCenter,CenterHit) || !SurfaceHit(CapsuleCenter+FVector(NearRadius,0,0),NearHit) ||
       !SurfaceHit(CapsuleCenter+FVector(Radius+Snow->TexelSizeCm*2,0,0),OutsideHit))
    { Test->AddError(TEXT("Capsule footprint probes require exposed snow substrate"));Cleanup();return true; }
    CapsuleCenterGround=CenterHit.ImpactPoint;
    const float Center=Snow->GetCompressionAtLocation(CapsuleCenterGround);
    const float Near=Snow->GetCompressionAtLocation(NearHit.ImpactPoint);
    const float Outside=Snow->GetCompressionAtLocation(OutsideHit.ImpactPoint);
    Test->AddInfo(FString::Printf(TEXT("SnowPlayerCapsule radiusCm=%.3f center=%.6f nearDistanceCm=%.3f near=%.6f outside=%.6f raisedMeshCm=500"),Radius,Center,NearRadius,Near,Outside));
    Test->TestTrue(TEXT("Actual Player capsule center compresses snow with foot and torso bones raised"),FMath::Abs(Center-Snow->FootCompression)<0.001f);
    Test->TestTrue(TEXT("Capsule footprint reaches beyond the old narrow foot brush"),NearRadius>Snow->FootRadiusCm.GetMax()*1.4 && Near>0.f);
    Test->TestEqual(TEXT("Capsule depression stops outside its scaled radius plus authored padding"),Outside,0.f);
    CapsuleInitialCompression=Center;CapsuleProbe=2;Stage=8;Next=Now+0.75;break;
   }
   if(CapsuleProbe==2)
   {
    const float Repeat=Snow->GetCompressionAtLocation(CapsuleCenterGround);
    Test->TestTrue(TEXT("Stationary capsule contact remains bounded at the requested movement depth"),FMath::Abs(Repeat-CapsuleInitialCompression)<0.001f && Repeat<=Snow->FootCompression+0.001f);
    // Place the capsule bottom above even the maximum piled snow. CMC remains
    // disabled so gravity cannot turn this negative fixture into a real contact.
    Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+ExpectedDepth+Snow->WeaponSurfaceContactToleranceCm+Snow->TexelSizeCm*2),false,nullptr,ETeleportType::TeleportPhysics);
    Snow->ClearSnow();CapsuleProbe=3;Stage=8;Next=Now+0.25;break;
   }
   if(CapsuleProbe==3)
   {
    Test->TestEqual(TEXT("Airborne Player capsule cannot deform snow below it"),ContactCount(Point,Point),0);
    Player->GetMesh()->SetRelativeTransform(SavedPlayerMeshRelative);
    Player->GetMesh()->bPauseAnims=SavedPlayerPause;
    Player->GetMesh()->RefreshBoneTransforms();
    Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+1),false,nullptr,ETeleportType::TeleportPhysics);
    Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    WalkStart=Player->GetActorLocation();Snow->ClearSnow();CapsuleProbe=4;Stage=8;Next=Now+0.5;break;
   }
   float Maximum=0.f;ContactCount(WalkStart,WalkStart,&Maximum);
   Test->TestFalse(TEXT("Idle fixture has no active Attack ability"),ActiveAttack(CastChecked<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent()))!=nullptr);
   Test->TestTrue(TEXT("Equipped idle leaves no weapon-depth crater"),Maximum<=Snow->FootCompression+0.001f);
   bMove=true;Next=Now+1.;break;
  }
  case 9:
  {
   bMove=false;Player->HandleInputMoveReleased();
   Test->TestTrue(TEXT("Native player movement actually advances on HeinMach"),FVector::Dist2D(WalkStart,Player->GetActorLocation())>50.f);
   float Maximum=0.f;const int32 Count=ContactCount(WalkStart,Player->GetActorLocation(),&Maximum);
   Test->AddInfo(FString::Printf(TEXT("SnowPlayer runDistance=%.2f compressedSamples=%d maximumCompression=%.6f"),FVector::Dist2D(WalkStart,Player->GetActorLocation()),Count,Maximum));
   Test->TestTrue(TEXT("Actual moving Player capsule compresses snow"),Count>0);
   Test->TestFalse(TEXT("Walking fixture has no active Attack ability"),ActiveAttack(CastChecked<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent()))!=nullptr);
   Test->TestTrue(TEXT("Equipped walking leaves only capsule movement-depth compression"),Maximum<=Snow->FootCompression+0.001f);
   Test->TestTrue(TEXT("Grounded Run reaches the requested 35/40 capsule compression"),FMath::Abs(Maximum-Snow->FootCompression)<0.001f);
   Player->HandleInputSprint();bMove=true;Next=Now+1.;break;
  }
  case 10:
  {
   bMove=false;Player->HandleInputMoveReleased();Player->HandleInputSprintReleased();
   if(!bDodgeReady)
   {
    Player->GetCharacterMovement()->StopMovementImmediately();
    Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+1),false,nullptr,ETeleportType::TeleportPhysics);
    Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Snow->ClearSnow();
    bDodgeReady=true;Stage=10;Next=Now+0.5;break;
   }
   auto* ASC=CastChecked<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent());
   ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
   DodgeStart=Player->GetActorLocation();Player->HandleInputMove(FVector2D(0,1),FRotator::ZeroRotator);
   ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_A);
   Next=Now+1.5;break;
  }
  case 11:
  {
   auto* ASC=CastChecked<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent());
   ASC->AbilityInputTagReleased(KZGameplayTags::Input_Action_A);Player->HandleInputMoveReleased();
   if(ASC->GetActivatableAbilities().ContainsByPredicate([](const FGameplayAbilitySpec& Spec) {
       return Spec.IsActive() && Spec.Ability && Spec.Ability->IsA<UKZDodgeAbility>(); }))
   { Stage=11;Next=Now+0.1;break; }
   if(!bDodgeSettled) { bDodgeSettled=true;Stage=11;Next=Now+0.5;break; }
   float Maximum=0.f;const int32 Count=ContactCount(DodgeStart,Player->GetActorLocation(),&Maximum);
   Test->AddInfo(FString::Printf(TEXT("SnowPlayer dodgeDistance=%.2f compressedSamples=%d minCapsuleBottomGapCm=%.3f groundedCapsuleFrames=%d maxContactCompression=%.6f maximumCompression=%.6f"),FVector::Dist2D(DodgeStart,Player->GetActorLocation()),Count,MinDodgeCapsuleGap,DodgeContactFrames,MaxDodgeCompression,Maximum));
   Test->TestTrue(TEXT("Existing Dodge actually moves and makes grounded contact"),FVector::Dist2D(DodgeStart,Player->GetActorLocation())>20.f && Count>0);
   Test->TestTrue(TEXT("Actual grounded Dodge samples capsule contact"),DodgeContactFrames>0 && MaxDodgeCompression>0.f);
   Test->TestTrue(TEXT("Grounded Dodge reaches only the requested 35/40 capsule compression"),FMath::Abs(Maximum-Snow->FootCompression)<0.001f);
   Shot(TEXT("Snow_Player_Run_Dodge.png"));
   TInlineComponentArray<UMeshComponent*> Parts(Player.Get());
   for(auto* P:Parts) if(P->GetName().Contains(TEXT("DualAxeSword"))) { Weapon=P;break; }
   if(!Weapon.IsValid()) { Test->AddError(TEXT("Delivered Player has no DualAxeSword weapon for actual sweep test"));Cleanup();return true; }
   WeaponParent=Weapon->GetAttachParent();WeaponSocket=Weapon->GetAttachSocketName();WeaponRelative=Weapon->GetRelativeTransform();
   WeaponTags=Weapon->ComponentTags;Weapon->ComponentTags.AddUnique(TEXT("SnowWeapon"));
   Weapon->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
   // Keep the real blade's sampled long axis parallel to this ground plane for the near-surface
   // air fixture; a tilted blade could genuinely intersect the snow at one end.
   FBox WeaponBox(ForceInit);
   if(auto* StaticPart=Cast<UStaticMeshComponent>(Weapon.Get())) WeaponBox=StaticPart->GetStaticMesh()->GetBoundingBox();
   else if(auto* SkeletalPart=Cast<USkeletalMeshComponent>(Weapon.Get())) WeaponBox=SkeletalPart->GetSkeletalMeshAsset()->GetImportedBounds().GetBox();
   if(!WeaponBox.IsValid) { Test->AddError(TEXT("Actual weapon bounds unavailable"));Cleanup();return true; }
   const FVector Extent=WeaponBox.GetExtent();
   const int32 Axis=Extent.X>=Extent.Y && Extent.X>=Extent.Z ? 0:(Extent.Y>=Extent.Z ? 1:2);
   FVector LocalAxis=FVector::ZeroVector;LocalAxis[Axis]=1.;
   const FVector WorldAxis=Weapon->GetComponentTransform().TransformVector(LocalAxis).GetSafeNormal();
   const FVector GroundTangent=FVector::VectorPlaneProject(FVector::ForwardVector,SnowGroundNormal).GetSafeNormal();
   Weapon->SetWorldRotation(FQuat::FindBetweenNormals(WorldAxis,GroundTangent)*Weapon->GetComponentQuat());
   SavedFootReach=Snow->FootContactHeightCm;SavedBodyReach=Snow->BodyContactHeightCm;
   Snow->FootContactHeightCm=0.f;Snow->BodyContactHeightCm=0.f;
   Player->GetCharacterMovement()->DisableMovement();Snow->ClearSnow();
   // The new capsule contact intentionally ignores the old foot-reach test
   // switch. Move only the Player away while the detached blade stays at snow.
   Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+ExpectedDepth+500),false,nullptr,ETeleportType::TeleportPhysics);
   WeaponPoint=Point+FVector(0,50,0);
   FHitResult Hit;if(W->LineTraceSingleByChannel(Hit,WeaponPoint+FVector(0,0,1000),WeaponPoint-FVector(0,0,1000),ECC_Visibility)) WeaponPoint=Hit.ImpactPoint;
   bAirSweep=true;bWeaponSweep=true;SweepStart=Now;Next=Now+1.2;break;
  }
  case 12:
   bWeaponSweep=false;Test->TestEqual(TEXT("Inactive weapon movement in air leaves snow untouched"),ContactCount(WeaponPoint,WeaponPoint+FVector(0,150,0)),0);
   Snow->ClearSnow();
   bAirSweep=false;bWeaponSweep=true;SweepStart=Now;Next=Now+1.2;break;
  case 13:
  {
   bWeaponSweep=false;
   auto* ASC=CastChecked<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent());
   if(WeaponProbe==0)
   {
    Test->TestFalse(TEXT("Grounded equipment movement is not an Attack"),ActiveAttack(ASC)!=nullptr);
    Test->TestEqual(TEXT("Inactive grounded weapon movement leaves snow untouched"),ContactCount(WeaponPoint,WeaponPoint+FVector(0,150,0)),0);
    InactiveWeaponEndpoint=WeaponPoint+FVector(0,150,0);
    // The 200 cm gap is below the teleport guard and beyond the 140 cm crater
    // envelope. An inactive history must not bridge into this real activation.
    SetWeapon(Point+FVector(0,0,1));
    ASC->SetNumericAttributeBase(UKZAttributeSet::GetStaminaAttribute(),ASC->GetNumericAttribute(UKZAttributeSet::GetMaxStaminaAttribute()));
    ASC->AbilityInputTagPressed(KZGameplayTags::Input_Action_X);
    ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X,EKZComboCommandPhase::Begin);
    if(!VerifyAttack(ASC,TEXT("PlayerWeakBegin"),PlayerAttackHandle)) { Cleanup();return true; }
    Player->GetMesh()->bPauseAnims=true;
    WeaponProbe=1;Stage=13;Next=Now+0.25;break;
   }
   if(WeaponProbe==1)
   {
    if(!VerifyAttack(ASC,TEXT("PlayerGroundContact"),PlayerAttackHandle)) { Cleanup();return true; }
    Test->TestTrue(TEXT("Actual active Player Attack contact uses weapon depth"),FMath::Abs(Snow->GetCompressionAtLocation(Point)-Snow->WeaponCompression)<0.01f);
    Test->TestTrue(TEXT("Wide active Attack crater extends beyond the blade contact"),Snow->GetCompressionAtLocation(Point+FVector(60,50,0))>0.1f);
    Test->TestEqual(TEXT("Inactive walking history never bridges into an Attack"),Snow->GetCompressionAtLocation(InactiveWeaponEndpoint),0.f);
    Shot(TEXT("Snow_Weapon_Contact.png"));
    // Above even the maximum local snow plus its small contact tolerance, but
    // still inside the former 79 cm substrate ray: this must remain airborne.
    SetWeapon(Point+FVector(0,0,Snow->WeaponContactHeightCm-Snow->TexelSizeCm));
    Snow->ClearSnow();WeaponProbe=2;Stage=13;Next=Now+0.25;break;
   }
   if(WeaponProbe==2)
   {
    if(!VerifyAttack(ASC,TEXT("PlayerNearSurfaceAir"),PlayerAttackHandle)) { Cleanup();return true; }
    Test->TestEqual(TEXT("Active Attack above the snow surface cannot use the broad substrate ray"),ContactCount(Point,Point),0);
    SetWeapon(Point+FVector(0,0,200));Snow->ClearSnow();WeaponProbe=3;Stage=13;Next=Now+0.25;break;
   }
   if(WeaponProbe==3)
   {
    if(!VerifyAttack(ASC,TEXT("PlayerAirAttack"),PlayerAttackHandle)) { Cleanup();return true; }
    Test->TestEqual(TEXT("Actual active Attack in air leaves snow untouched"),ContactCount(Point,Point),0);
    ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X,EKZComboCommandPhase::Cancel);
    ASC->AbilityInputTagCanceled(KZGameplayTags::Input_Action_X);ASC->CancelAbilityHandle(PlayerAttackHandle);
    Test->TestFalse(TEXT("Cancel ends the actual Player Attack Spec"),ActiveAttack(ASC)!=nullptr);
    SetWeapon(Point+FVector(0,0,1));Snow->ClearSnow();WeaponProbe=4;Stage=13;Next=Now+0.25;break;
   }
   if(WeaponProbe==4)
   {
    Test->TestEqual(TEXT("Canceled Attack cannot stamp even while the real blade touches snow"),ContactCount(Point,Point),0);
    Weapon->ComponentTags=WeaponTags;Weapon->AttachToComponent(WeaponParent.Get(),FAttachmentTransformRules::KeepRelativeTransform,WeaponSocket);Weapon->SetRelativeTransform(WeaponRelative);
    Player->GetMesh()->bPauseAnims=SavedPlayerPause;
    Player->SetActorLocation(Point+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+1),false,nullptr,ETeleportType::TeleportPhysics);
    Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);WalkStart=Player->GetActorLocation();
    Snow->ClearSnow();bMove=true;WeaponProbe=5;Stage=13;Next=Now+1.;break;
   }
   bMove=false;Player->HandleInputMoveReleased();
   Test->TestTrue(TEXT("Canceled Attack fixture resumes actual CMC walking"),FVector::Dist2D(WalkStart,Player->GetActorLocation())>50.f);
   float CanceledWalkMaximum=0.f;
   const int32 CanceledWalkCount=ContactCount(WalkStart,Player->GetActorLocation(),&CanceledWalkMaximum);
   Test->TestTrue(TEXT("Walking after cancel restores actual capsule snow contact"),CanceledWalkCount>0);
   Test->TestTrue(TEXT("Walking after cancel cannot use weapon-depth compression"),CanceledWalkMaximum<=Snow->FootCompression+0.001f);
   Snow->FootContactHeightCm=SavedFootReach;Snow->BodyContactHeightCm=SavedBodyReach;SavedFootReach=-1.f;
   Weapon->ComponentTags=WeaponTags;Weapon->AttachToComponent(WeaponParent.Get(),FAttachmentTransformRules::KeepRelativeTransform,WeaponSocket);Weapon->SetRelativeTransform(WeaponRelative);
   Player->SetActorLocation(SavedLocation+FVector(0,0,1000),false,nullptr,ETeleportType::TeleportPhysics);
   if(!SpawnMonster()) { Cleanup();return true; }
   Snow->ClearSnow();Next=Now+1.;break;
  }
  case 14:
   MonsterStart=Monster->GetActorLocation();bMonsterMove=true;Next=Now+1.;break;
  case 15:
  {
   bMonsterMove=false;Monster->GetCharacterMovement()->StopMovementImmediately();
   float Maximum=0.f;const int32 Count=ContactCount(MonsterStart,Monster->GetActorLocation(),&Maximum);
   Test->AddInfo(FString::Printf(TEXT("SnowMonster distance=%.2f contacts=%d maximumCompression=%.6f class=%s"),FVector::Dist2D(MonsterStart,Monster->GetActorLocation()),Count,Maximum,*Monster->GetClass()->GetName()));
   Test->TestTrue(TEXT("Actual evaluated Monster feet compress snow while moving"),FVector::Dist2D(MonsterStart,Monster->GetActorLocation())>50.f && Count>0);
   Test->TestFalse(TEXT("Monster gait fixture has no active Attack ability"),ActiveAttack(CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()))!=nullptr);
   Test->TestTrue(TEXT("Merged equipment cannot carve a weapon crater during Monster gait"),Maximum<=Snow->FootCompression+0.001f);
   Monster->GetCharacterMovement()->DisableMovement();
   auto* M=Monster->GetMesh();M->bPauseAnims=true;FName Pelvis=NAME_None;
   for(int32 I=0;I<M->GetNumBones();++I) if(M->GetBoneName(I).ToString().EndsWith(TEXT("pelvis"))) { Pelvis=M->GetBoneName(I);break; }
   if(Pelvis.IsNone()) { Test->AddError(TEXT("Actual Monster pelvis missing"));Cleanup();return true; }
   // Pose fixture isolates torso contact with CMC disabled; it does not claim a gameplay knockdown action.
   M->SetWorldRotation(FRotator(0,0,90));M->RefreshBoneTransforms();
   M->SetWorldLocation(M->GetComponentLocation()+Point+FVector(0,0,6)-M->GetSocketLocation(Pelvis));M->RefreshBoneTransforms();
   Snow->ClearSnow();Next=Now+1.;break;
  }
  case 16:
   Test->TestTrue(TEXT("Lying torso contact compresses snow with MOVE_None"),Snow->GetCompressionAtLocation(Point)>0.99f);
   Shot(TEXT("Snow_Monster_Torso.png"));Next=Now+0.5;break;
  case 17:
  {
   // Use real imported weapon vertices and an evaluated pose, placing the blade
   // below every foot/torso writer. This isolates merged-mesh weapon contact.
   auto* M=Monster->GetMesh();
   auto* ASC=CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
   if(MergedAttackProbe==0)
   {
    // Start an already granted production attack and evaluate its authored
    // montage before freezing the geometry fixture. No Spec flags are forged.
    M->bPauseAnims=false;ASC->CancelAllAbilities();ASC->ClearComboCommands();
    const auto& Attacks=Monster->GetAttackAbilities();
    const auto* Spec=Attacks.IsEmpty() ? nullptr:ASC->FindAbilitySpecFromClass(Attacks[0]);
    if(!Test->TestNotNull(TEXT("Merged weapon fixture has its actual granted Attack"),Spec) ||
       !Test->TestTrue(TEXT("Merged weapon fixture activates its actual granted Attack"),ASC->TryActivateAbility(Spec->Handle)))
    { Cleanup();return true; }
    if(!VerifyAttack(ASC,TEXT("MonsterAttackBegin"),MonsterAttackHandle)) { Cleanup();return true; }
    MergedAttackProbe=1;Stage=17;Next=Now+0.1;break;
   }
   if(!VerifyAttack(ASC,TEXT("MonsterEvaluatedAttack"),MonsterAttackHandle)) { Cleanup();return true; }
   M->bPauseAnims=true;
   SavedFootReach=Snow->FootContactHeightCm;SavedBodyReach=Snow->BodyContactHeightCm;
   // Fixture isolation only: zero-length foot/torso traces while testing the
   // real equipment writer. Normal reaches remain active for gait/torso tests.
   Snow->FootContactHeightCm=0.f;Snow->BodyContactHeightCm=0.f;
   TInlineComponentArray<USkeletalMeshComponent*> Meshes(Monster.Get());
   USkeletalMeshComponent* Part=nullptr;const FKZSnowWeaponPoints* Profile=nullptr;FVector Tip;
   double Longest=0.;
   for(auto* P:Meshes) for(const auto& Row:Snow->MergedWeaponContacts)
    if(Row.Mesh.Get()==P->GetSkeletalMeshAsset()) for(const FVector& V:Row.Points)
     if(V.SizeSquared()>Longest) { Longest=V.SizeSquared();Part=P;Profile=&Row;Tip=V; }
   if(!Part || !Profile) { Test->AddError(TEXT("Actual Monster merged weapon profile missing"));Cleanup();return true; }
   const FVector Direction=Part->GetSocketTransform(Profile->Bone).TransformVector(Tip).GetSafeNormal();
   M->SetWorldRotation(FQuat::FindBetweenNormals(Direction,-FVector::UpVector)*M->GetComponentQuat());
   M->RefreshBoneTransforms();
   const FVector WorldTip=Part->GetSocketTransform(Profile->Bone).TransformPosition(Tip);
   M->SetWorldLocation(M->GetComponentLocation()+Point+FVector(0,0,1)-WorldTip);M->RefreshBoneTransforms();
   double LowestBody=TNumericLimits<double>::Max();
   for(int32 I=0;I<M->GetNumBones();++I)
   {
    const FName N=M->GetBoneName(I);const FString S=N.ToString().ToLower();
    if(S.Contains(TEXT("foot")) || S.Contains(TEXT("pelvis")) || S.Contains(TEXT("spine")) ||
       S.EndsWith(TEXT("head")) || S.EndsWith(TEXT("hand")) || S.EndsWith(TEXT("forearm")) ||
       S.EndsWith(TEXT("upperarm")) || S.EndsWith(TEXT("thigh")) || S.EndsWith(TEXT("calf")))
      LowestBody=FMath::Min(LowestBody,M->GetSocketLocation(N).Z-Point.Z);
   }
   Test->AddInfo(FString::Printf(TEXT("SnowMergedWeapon class=%s mesh=%s bone=%s length=%.2f lowestBody=%.2f"),
    *Monster->GetClass()->GetName(),*Part->GetSkeletalMeshAsset()->GetName(),*Profile->Bone.ToString(),FMath::Sqrt(Longest),LowestBody));
   Test->TestTrue(TEXT("Merged weapon fixture excludes foot and torso contacts"),LowestBody>Snow->BodyContactHeightCm);
   Snow->ClearSnow();Next=Now+0.25;break;
  }
  case 18:
   if(!VerifyAttack(CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()),TEXT("MonsterGroundContact"),MonsterAttackHandle)) { Cleanup();return true; }
   Test->TestTrue(TEXT("Actual merged Monster weapon uses the authored partial depth"),FMath::Abs(Snow->GetCompressionAtLocation(Point)-Snow->WeaponCompression)<0.01f);
   Snow->ClearSnow();Monster->GetMesh()->AddWorldOffset(FVector(0,0,200));Next=Now+0.25;break;
  case 19:
  {
   auto* ASC=CastChecked<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent());
   if(!bMergedCanceled)
   {
    if(!VerifyAttack(ASC,TEXT("MonsterAirAttack"),MonsterAttackHandle)) { Cleanup();return true; }
    Test->TestEqual(TEXT("Actual active merged Monster weapon in air leaves snow untouched"),Snow->GetCompressionAtLocation(Point),0.f);
    ASC->CancelAbilityHandle(MonsterAttackHandle);ASC->ClearComboCommands();
    Test->TestFalse(TEXT("Cancel ends the actual Monster Attack Spec"),ActiveAttack(ASC)!=nullptr);
    Monster->GetMesh()->AddWorldOffset(FVector(0,0,-200));Snow->ClearSnow();
    bMergedCanceled=true;Stage=19;Next=Now+0.25;break;
   }
   Test->TestEqual(TEXT("Canceled merged Monster weapon at ground contact leaves snow untouched"),Snow->GetCompressionAtLocation(Point),0.f);
   Snow->FootContactHeightCm=SavedFootReach;Snow->BodyContactHeightCm=SavedBodyReach;
   SavedFootReach=-1.f;MergedAttackProbe=0;bMergedCanceled=false;
   Monster->Destroy();
   if(++MonsterIndex<4)
   {
    if(!SpawnMonster()) { Cleanup();return true; }
    Snow->ClearSnow();Stage=14;Next=Now+1.;break;
   }
   WriteReport();
   // Destroying only the PIE field exercises material restoration.
   TInlineComponentArray<UPrimitiveComponent*> Parts;
   for(TActorIterator<AActor> It(W);It;++It)
   {
    TInlineComponentArray<UPrimitiveComponent*> P(*It);
    for(auto* C:P) if(C->ComponentHasTag(Snow->SurfaceTag)) Parts.Add(C);
   }
   Snow->Destroy();
   bool bRestored=true;for(auto* C:Parts) for(int32 I=0;I<C->GetNumMaterials();++I)
    bRestored &= C->GetMaterial(I) && C->GetMaterial(I)->GetName().StartsWith(TEXT("M_HM_Deformable_"));
   Test->TestTrue(TEXT("EndPlay restores owned terrain material slots"),bRestored);
   Cleanup();return true;
  }
  }
  return false;
 }
private:
 const FGameplayAbilitySpec* ActiveAttack(UKZAbilitySystemComponent* ASC) const
 {
  for(const FGameplayAbilitySpec& Spec:ASC->GetActivatableAbilities())
   if(Spec.IsActive() && Spec.Ability && Spec.Ability->GetAssetTags().HasTag(KZGameplayTags::Ability_Action_Attack)) return &Spec;
  return nullptr;
 }
 bool VerifyAttack(UKZAbilitySystemComponent* ASC,const TCHAR* Fixture,FGameplayAbilitySpecHandle& Handle)
 {
  const FGameplayAbilitySpec* Spec=ActiveAttack(ASC);
  const auto* Ability=Spec ? Cast<UKZComboActionAbility>(Spec->GetPrimaryInstance()):nullptr;
  const bool bActual=Spec && Ability && !Ability->GetCurrentNodeId().IsNone() &&
   Ability->GetCurrentMontage() && ASC->GetAnimatingAbility()==Ability;
  Test->AddInfo(FString::Printf(TEXT("SnowActualAttack fixture=%s avatar=%s active=%d ability=%s node=%s montage=%s"),
   Fixture,*GetNameSafe(ASC->GetAvatarActor()),Spec!=nullptr,*GetNameSafe(Ability),
   Ability ? *Ability->GetCurrentNodeId().ToString():TEXT("None"),*GetNameSafe(Ability ? Ability->GetCurrentMontage():nullptr)));
  if(Spec) Handle=Spec->Handle;
  return Test->TestTrue(TEXT("Snow weapon fixture uses a real active Attack Spec, node and montage"),bActual);
 }
 bool SpawnMonster()
 {
  static const TCHAR* Names[]={TEXT("Swordsman"),TEXT("SwordShield"),TEXT("HeavySwordsman"),TEXT("HalberdElite")};
  const FString Path=FString::Printf(TEXT("/Game/Bluprints/Monsters/BP_Monster_%s.BP_Monster_%s_C"),Names[MonsterIndex],Names[MonsterIndex]);
  UClass* Class=LoadClass<AKZMonster>(nullptr,*Path);
  if(!Class) { Test->AddError(TEXT("Actual Monster Blueprint unavailable: ")+Path);return false; }
  FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
  Monster=Player->GetWorld()->SpawnActor<AKZMonster>(Class,Point+FVector(0,0,100),FRotator::ZeroRotator,Spawn);
  Monster->GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
  Monster->SetActorLocation(Point+FVector(0,0,Monster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+1),false,nullptr,ETeleportType::TeleportPhysics);
  if(auto* AI=Cast<AKZMonsterAIController>(Monster->GetController()))
  {
   AI->GetStateTreeComponent()->StopLogic(TEXT("Snow contact fixture"));
   AI->StopMovement();
   // This newly spawned fixture must not bootstrap AI on its next controller tick.
   // The actor is destroyed after the contact test; no gameplay controller is changed.
   AI->SetActorTickEnabled(false);
  }
  if(auto* ASC=Cast<UKZAbilitySystemComponent>(Monster->GetAbilitySystemComponent()))
  {
   ASC->CancelAllAbilities();
   ASC->ClearComboCommands();
  }
  return true;
 }
 TArray<float> DepthRow()
 {
  // UE5.8 implementation passes the last two arguments as Width/Height, despite MaxX/MaxY names.
  const TArray<FLinearColor> Pixels=UKismetRenderingLibrary::ReadRenderTargetRawPixelArea(Player.Get(),Target,0,64,128,1,false);
  TArray<float> Values;for(const FLinearColor& P:Pixels) Values.Add(P.R);return Values;
 }
 TArray<float> DepthGrid()
 {
  const auto Pixels=UKismetRenderingLibrary::ReadRenderTargetRawPixelArea(Player.Get(),Target,0,0,128,128,false);
  TArray<float> Values;Values.Reserve(Pixels.Num());for(const auto& P:Pixels) Values.Add(P.R);return Values;
 }
 int32 ContactCount(FVector A,FVector B,float* Maximum=nullptr)
 {
  if(Maximum) *Maximum=0.f;
  // Match the technical field resolution: a coarser grid can miss the small
  // foot core even when finalized sole contacts have written real field cells.
  const double Spacing=Snow->TexelSizeCm;
  const FVector Direction=(B-A).GetSafeNormal2D();
  FVector Across(-Direction.Y,Direction.X,0);
  if(Across.IsNearlyZero()) Across=FVector::RightVector;
  int32 Count=0;const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Dist2D(A,B)/Spacing));
  const int32 Width=FMath::CeilToInt(Snow->WeaponRadiusCm*1.4f/Spacing);
  for(int32 I=0;I<=Steps;++I) for(int32 Side=-Width;Side<=Width;++Side)
  {
   FVector P=FMath::Lerp(A,B,double(I)/Steps)+Across*(Side*Spacing);
   P.X=(FMath::FloorToDouble(P.X/Spacing)+0.5)*Spacing;
   P.Y=(FMath::FloorToDouble(P.Y/Spacing)+0.5)*Spacing;
   FHitResult H;FCollisionQueryParams Query(NAME_None,true,Player.Get());
   while(Player->GetWorld()->LineTraceSingleByChannel(H,P+FVector(0,0,500),P-FVector(0,0,500),ECC_Visibility,Query))
   {
    if(!H.GetComponent() || !H.GetComponent()->ComponentHasTag(TEXT("HeinMachMicroDressing"))) break;
    Query.AddIgnoredComponent(H.GetComponent());
   }
   if(H.bBlockingHit && H.GetComponent() && H.GetComponent()->ComponentHasTag(Snow->SurfaceTag))
   {
    const float Compression=Snow->GetCompressionAtLocation(H.ImpactPoint);
    if(Compression>0.1f) ++Count;
    if(Maximum) *Maximum=FMath::Max(*Maximum,Compression);
   }
  }
  return Count;
 }
 bool SurfaceHit(FVector Position,FHitResult& Hit) const
 {
  FCollisionQueryParams Query(NAME_None,true,Player.Get());
  while(Player->GetWorld()->LineTraceSingleByChannel(Hit,Position+FVector(0,0,1000),Position-FVector(0,0,1000),ECC_Visibility,Query))
  {
   if(!Hit.GetComponent() || !Hit.GetComponent()->ComponentHasTag(TEXT("HeinMachMicroDressing"))) break;
   Query.AddIgnoredComponent(Hit.GetComponent());
  }
  return Hit.bBlockingHit && Hit.GetComponent() && Hit.GetComponent()->ComponentHasTag(Snow->SurfaceTag);
 }
 void SetWeapon(FVector Center)
 {
  const FVector LocalCenter=Weapon->CalcBounds(FTransform::Identity).Origin;
  Weapon->SetWorldLocation(Center-Weapon->GetComponentTransform().TransformVector(LocalCenter));
 }
 void Shot(const TCHAR* Name)
 {
  auto& Config=GetHighResScreenshotConfig();Config.SetResolution(1280,720,1.f);
  Config.FilenameOverride=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("SnowQA")/Name);
  if(GEngine->GameViewport && GEngine->GameViewport->Viewport) GEngine->GameViewport->Viewport->TakeHighResScreenShot();
 }
 void WriteReport()
 {
  FString Text=FString::Printf(TEXT("{\"depth_change_cm\":%.9f,\"foot_depth_cm\":%.9f,\"depth_reference_cm\":%.9f,\"weighted_layer_cm\":%.9f,\"before\":["),DepthChange,FootDepth,DepthReferenceCm,Before.Num()==128?SubstrateDepth-Before[64]:0.f);
  for(int32 I=0;I<Before.Num();++I) Text+=FString::Printf(TEXT("%s%.9f"),I?TEXT(","):TEXT(""),Before[I]);
  Text+=TEXT("],\"after\":[");for(int32 I=0;I<After.Num();++I) Text+=FString::Printf(TEXT("%s%.9f"),I?TEXT(","):TEXT(""),After[I]);
  Text+=TEXT("]}");FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectSavedDir()/TEXT("SnowQA/RuntimeGeometry.json")));
 }
 void Cleanup()
 {
  bMove=bWeaponSweep=bMonsterMove=false;
  if(Snow.IsValid() && SavedFootReach>=0.f) { Snow->FootContactHeightCm=SavedFootReach;Snow->BodyContactHeightCm=SavedBodyReach; }
  if(Monster.IsValid()) Monster->Destroy();
  if(Weapon.IsValid() && WeaponParent.IsValid()) { Weapon->ComponentTags=WeaponTags;Weapon->AttachToComponent(WeaponParent.Get(),FAttachmentTransformRules::KeepRelativeTransform,WeaponSocket);Weapon->SetRelativeTransform(WeaponRelative); }
  if(Player.IsValid())
  {
   if(auto* ASC=Cast<UKZAbilitySystemComponent>(Player->GetAbilitySystemComponent()))
   {
    ASC->SubmitComboCommand(KZGameplayTags::Command_Player_Attack_X,EKZComboCommandPhase::Cancel);
    ASC->AbilityInputTagCanceled(KZGameplayTags::Input_Action_X);
    if(PlayerAttackHandle.IsValid()) ASC->CancelAbilityHandle(PlayerAttackHandle);
   }
   Player->GetMesh()->bPauseAnims=SavedPlayerPause;
   if(bSavedPlayerMeshRelative) Player->GetMesh()->SetRelativeTransform(SavedPlayerMeshRelative);
   Player->HandleInputMoveReleased();Player->HandleInputSprintReleased();
   Player->GetMesh()->VisibilityBasedAnimTickOption=SavedTickOption;
   Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);Player->SetActorLocation(SavedLocation,false,nullptr,ETeleportType::TeleportPhysics);Player->SetActorRotation(SavedRotation);
   if(auto* PC=Cast<APlayerController>(Player->GetController());PC && SavedView.IsValid()) PC->SetViewTarget(SavedView.Get());
  }
  if(Camera.IsValid()) Camera->Destroy();if(Capture.IsValid()) Capture->Destroy();
 }
 FAutomationTestBase* Test;TWeakObjectPtr<AKZPlayer> Player;TWeakObjectPtr<AKZSnowDeformation> Snow;
 TWeakObjectPtr<ACameraActor> Camera;TWeakObjectPtr<ASceneCapture2D> Capture;UTextureRenderTarget2D* Target=nullptr;
 TWeakObjectPtr<AActor> SavedView;TWeakObjectPtr<UMeshComponent> Weapon;TWeakObjectPtr<USceneComponent> WeaponParent;
 TWeakObjectPtr<AKZMonster> Monster;
 FName WeaponSocket;FTransform WeaponRelative;FRotator SavedRotation;
 FTransform SavedPlayerMeshRelative;
 TArray<FName> WeaponTags;
 FVector SavedLocation,Point,WalkStart,DodgeStart,WeaponPoint,MonsterStart,InactiveWeaponEndpoint,SnowGroundNormal;
 FVector CapsuleCenter,CapsuleCenterGround;float CapsuleInitialCompression=0.f;int32 CapsuleProbe=0;
 FGameplayAbilitySpecHandle PlayerAttackHandle,MonsterAttackHandle;
  TArray<float> Before,After,BeforeFootGrid;float DepthChange=0.f,ExpectedDepth=0.f,FootDepth=0.f,DepthReferenceCm=0.f,SubstrateDepth=0.f;int32 PartialProbe=0,FullClearProbe=0;
 float SavedFootReach=-1.f,SavedBodyReach=0.f;
 double MinDodgeCapsuleGap=TNumericLimits<double>::Max();
 int32 DodgeContactFrames=0;float MaxDodgeCompression=0.f;
 EVisibilityBasedAnimTickOption SavedTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPose;
 double Deadline,Next=0.,SweepStart=0.;int32 Stage=0,ProbeStage=0,MonsterIndex=0,WeaponProbe=0,MergedAttackProbe=0;
 bool bMove=false,bWeaponSweep=false,bAirSweep=false,bMonsterMove=false,bDodgeReady=false,bDodgeSettled=false,bMergedCanceled=false,SavedPlayerPause=false,bSavedPlayerMeshRelative=false;
};

class FWaitForSnowPIE : public IAutomationLatentCommand
{
public:
 explicit FWaitForSnowPIE(FAutomationTestBase* InTest):Test(InTest),Deadline(FPlatformTime::Seconds()+90.) {}
 bool Update() override
 {
  for(const auto& C:GEngine->GetWorldContexts())
  {
   if(C.WorldType!=EWorldType::PIE || !C.World() || !C.World()->HasBegunPlay()) continue;
   AKZSnowDeformation* Snow=nullptr;for(TActorIterator<AKZSnowDeformation> It(C.World());It;++It) { Snow=*It;break; }
   for(TActorIterator<AKZPlayer> It(C.World());It;++It) if(Snow && It->IsPlayerControlled() && It->GetMesh()->GetAnimInstance() && It->GetCharacterMovement()->IsMovingOnGround())
   { FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FSnowPIECommand>(Test,*It,Snow));return true; }
  }
  if(FPlatformTime::Seconds()>Deadline) { Test->AddError(TEXT("Start PIE in HeinMach; initialized Player/Snow owner not found"));return true; }
  return false;
 }
private: FAutomationTestBase* Test;double Deadline;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKZSnowPIETest,"Khazan.Snow.PIE",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FKZSnowPIETest::RunTest(const FString& Parameters)
{
 AddInfo(TEXT("Waiting for isolated HeinMach PIE"));
 FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<FWaitForSnowPIE>(this));return true;
}
#endif
