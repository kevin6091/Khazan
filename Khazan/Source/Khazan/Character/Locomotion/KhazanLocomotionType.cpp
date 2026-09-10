


#include "Character/Locomotion/KhazanLocomotionType.h"

namespace KhazanLocomotion
{
    int32 GetGaitRestrictionRank(const EKhazanGait Gait)
    {
        switch (Gait)
        {
        case EKhazanGait::Walk:
            return 0;

        case EKhazanGait::Run:
            return 1;

        case EKhazanGait::Sprint:
            return 2;

        default:
            return INDEX_NONE;
        }
    }
    
    bool IsSupportedGait(const EKhazanGait Gait)
    {
        return GetGaitRestrictionRank(Gait) != INDEX_NONE;
    }

    bool IsSupportedRotationMode(const EKhazanRotationMode Mode)
    {
        switch (Mode)
        {
        case EKhazanRotationMode::VelocityDirection:
        case EKhazanRotationMode::LookingDirection:
        case EKhazanRotationMode::LockOn:
            return true;
        default:
            return false;
        }
    }
}

bool FKhazanLocomotionConfig::IsValid(FString& OutError) const
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

    if (!KhazanLocomotion::IsSupportedGait(DefaultRequestedGait) || 
        !KhazanLocomotion::IsSupportedGait(DefaultMaxAllowedGait) ||
        !KhazanLocomotion::IsSupportedRotationMode(DefaultRequestedRotationMode))
    {
        OutError = TEXT("Locomotion config contains an unsupported enum value.");
        return false;
    }

    OutError.Reset();
    return true;
}

float FKhazanLocomotionConfig::GetSpeedForGait(const EKhazanGait Gait) const
{
    switch (Gait)
    {
    case EKhazanGait::Walk:
        return WalkSpeed;
    case EKhazanGait::Run:
        return RunSpeed;
    case EKhazanGait::Sprint:
        return SprintSpeed;
    default:
        checkNoEntry();
        return WalkSpeed;
    }
}