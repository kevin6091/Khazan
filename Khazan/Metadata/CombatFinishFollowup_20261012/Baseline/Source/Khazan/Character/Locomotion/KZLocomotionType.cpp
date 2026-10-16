


#include "Character/Locomotion/KZLocomotionType.h"

namespace KZLocomotion
{
    int32 GetGaitRestrictionRank(const EKZGait Gait)
    {
        switch (Gait)
        {
        case EKZGait::Walk:
            return 0;

        case EKZGait::Run:
            return 1;

        case EKZGait::Sprint:
            return 2;

        default:
            return INDEX_NONE;
        }
    }

    bool IsSupportedGait(const EKZGait Gait)
    {
        return GetGaitRestrictionRank(Gait) != INDEX_NONE;
    }

    bool IsSupportedRotationMode(const EKZRotationMode Mode)
    {
        switch (Mode)
        {
        case EKZRotationMode::VelocityDirection:
        case EKZRotationMode::LookingDirection:
        case EKZRotationMode::LockOn:
            return true;
        default:
            return false;
        }
    }
}

bool FKZLocomotionConfig::IsValid(FString& OutError) const
{
    const bool bFiniteNumbers =
        FMath::IsFinite(WalkSpeed) &&
        FMath::IsFinite(RunSpeed) &&
        FMath::IsFinite(SprintSpeed) &&
        FMath::IsFinite(MinAnalogWalkSpeed) &&
        FMath::IsFinite(MaxAcceleration) &&
        FMath::IsFinite(BrakingDecelerationWalking) &&
        !RotationRate.ContainsNaN();

    if (!bFiniteNumbers)
    {
        OutError = TEXT("Locomotion config contains NaN or infinity.");
        return false;
    }

    if (WalkSpeed < 0.f || RunSpeed < 0.f || SprintSpeed < 0.f ||
        MinAnalogWalkSpeed < 0.f || MaxAcceleration < 0.f ||
        BrakingDecelerationWalking < 0.f ||
        RotationRate.Pitch < 0.f || RotationRate.Yaw < 0.f ||
        RotationRate.Roll < 0.f)
    {
        OutError = TEXT("Locomotion config contains a negative movement value.");
        return false;
    }

    if (WalkSpeed > RunSpeed || RunSpeed > SprintSpeed)
    {
        OutError = TEXT("Expected WalkSpeed <= RunSpeed <= SprintSpeed.");
        return false;
    }

    if (MinAnalogWalkSpeed > WalkSpeed)
    {
        OutError = TEXT("MinAnalogWalkSpeed must not exceed WalkSpeed.");
        return false;
    }

    if (!KZLocomotion::IsSupportedGait(DefaultRequestedGait) ||
        !KZLocomotion::IsSupportedGait(DefaultMaxAllowedGait) ||
        !KZLocomotion::IsSupportedRotationMode(DefaultRequestedRotationMode))
    {
        OutError = TEXT("Locomotion config contains an unsupported enum value.");
        return false;
    }

    OutError.Reset();
    return true;
}

float FKZLocomotionConfig::GetSpeedForGait(const EKZGait Gait) const
{
    switch (Gait)
    {
    case EKZGait::Walk:
        return WalkSpeed;
    case EKZGait::Run:
        return RunSpeed;
    case EKZGait::Sprint:
        return SprintSpeed;
    default:
        checkNoEntry();
        return WalkSpeed;
    }
}