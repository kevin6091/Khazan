"""Minimal scoped geometry correction; run only after the owned baseline PIE exits."""
from pathlib import Path
import json, hashlib
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerSlashWork_20261013/Khazan'
OUT=MAIN/'Metadata/PlayerSlashAlignment_20261013'
cpp=WORK/'Source/Khazan/Ability/KZActionAbility.cpp'
hdr=WORK/'Source/Khazan/Ability/KZActionAbility.h'
def read(p): return p.read_bytes().decode('utf-8').replace('\r\n','\n')
def write(p,s): p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
s=read(cpp)
a=s.index('\tif (Effect.bAlignToWeaponSweep && Cast<UNiagaraComponent>(Component)')
b=s.index('\telse if (Cast<UFXSystemComponent>(Component)',a)
old=s[a:b]; new=old
replacements=[
 ('\t\t\t\t CentreOffset = Effect.RelativeLocation, ReferenceEdges]()','\t\t\t\t ReferenceEdges]()'),
 ('\t\t\t\t\tconst FTransform Actor = PoseMesh->GetOwner()->GetActorTransform();','\t\t\t\t\tconst FVector ActorLocation = PoseMesh->GetOwner()->GetActorLocation();\n\t\t\t\t\tconst FVector ActorTranslation = Pending->bHasPreviousWeaponPose ?\n\t\t\t\t\t\tActorLocation - Pending->PreviousActorLocation : FVector::ZeroVector;'),
 ('\t\t\t\t\tFVector TipsActor[2] = {FVector::ZeroVector,FVector::ZeroVector}, Sweeps[2] = {FVector::ZeroVector,FVector::ZeroVector};','\t\t\t\t\tFVector Grips[2] = {FVector::ZeroVector,FVector::ZeroVector}, Sweeps[2] = {FVector::ZeroVector,FVector::ZeroVector};'),
 ('\t\t\t\t\t\tTipsActor[Index] = Actor.InverseTransformPosition(Ends[Index]);','\t\t\t\t\t\tGrips[Index] = Grip.GetLocation();'),
 ('\t\t\t\t\t\t\tActor.TransformVectorNoScale(TipsActor[Index] - Pending->PreviousWeaponTips[Index]), Blade) : FVector::ZeroVector;','\t\t\t\t\t\t\tEnds[Index] - Pending->PreviousWeaponTips[Index] - ActorTranslation, Blade) : FVector::ZeroVector;'),
 ('\t\t\t\t\t\tPending->PreviousWeaponTips[Index] = TipsActor[Index];','\t\t\t\t\t\tPending->PreviousWeaponTips[Index] = Ends[Index];'),
 ('\t\t\t\t\tPending->bHasPreviousWeaponPose = true;','\t\t\t\t\tPending->PreviousActorLocation = ActorLocation;\n\t\t\t\t\tPending->bHasPreviousWeaponPose = true;'),
 ('''\t\t\t\t\t// Slash mesh XY plane: X follows travel, Y follows the actual cutting edge.
\t\t\t\t\t// Renderer-local rotation and mesh centre are authored from its real asset.
\t\t\t\t\tconst FQuat Rotation = FRotationMatrix::MakeFromXY(Sweeps[Chosen], Blade).ToQuat() * MeshRotation.Quaternion();
\t\t\t\t\tconst FVector Scale = SourceScale * (Blade.Size() / ReferenceSpan);
\t\t\t\t\tconst FVector Centre = (Starts[Chosen] + Ends[Chosen]) * .5;
\t\t\t\t\tFX->SetWorldTransform(FTransform(Rotation, Centre + Rotation.RotateVector(CentreOffset * Scale), Scale));''',
 '''\t\t\t\t\t// X follows world-space weapon travel, retaining body/root yaw but excluding
\t\t\t\t\t// locomotion translation. Y follows the equipped weapon's cutting edge.
\t\t\t\t\tconst FQuat SweepFrame = FRotationMatrix::MakeFromXY(Sweeps[Chosen], Blade).ToQuat();
\t\t\t\t\tconst FVector EdgeDirection = Blade.GetSafeNormal();
\t\t\t\t\tconst FVector Pivot = Starts[Chosen] + EdgeDirection *
\t\t\t\t\t\tFVector::DotProduct(Grips[Chosen] - Starts[Chosen], EdgeDirection);
\t\t\t\t\tconst double WeaponRadius = FVector::Distance(Pivot, Ends[Chosen]);
\t\t\t\t\t// SM_VFX_SlashRing_01 measured diameter is ReferenceSpan (200 cm).
\t\t\t\t\t// Its leading vertex is (0,100,0); renderer and notify yaw180 cancel.
\t\t\t\t\t// Anchor that endpoint to the real tip instead of offsetting a bounding centre.
\t\t\t\t\tconst double ReferenceRadius = ReferenceSpan * .5;
\t\t\t\t\tconst FVector Scale = SourceScale * (WeaponRadius / ReferenceRadius);
\t\t\t\t\tconst FQuat Rotation = SweepFrame * MeshRotation.Quaternion();
\t\t\t\t\tconst FVector Origin = Ends[Chosen] - SweepFrame.GetAxisY() * ReferenceRadius * Scale.Y;
\t\t\t\t\tFX->SetWorldTransform(FTransform(Rotation, Origin, Scale));''')]
for oldpart,newpart in replacements:
 assert new.count(oldpart)==1,repr(oldpart)
 new=new.replace(oldpart,newpart,1)
write(cpp,s[:a]+new+s[b:])
h=read(hdr)
hold='\t\tFVector PreviousWeaponTips[2] = {FVector::ZeroVector, FVector::ZeroVector};'
assert h.count(hold)==1
write(hdr,h.replace(hold,'\t\t// World tips minus avatar translation preserve the actual rotational sweep.\n'+hold+'\n\t\tFVector PreviousActorLocation = FVector::ZeroVector;',1))
(OUT/'RuntimePatch.json').write_text(json.dumps({'status':'private_applied','files':[str(cpp),str(hdr)],'old_branch':old,'new_branch':new,'header_old':hold,'header_new':'\t\t// World tips minus avatar translation preserve the actual rotational sweep.\n'+hold+'\n\t\tFVector PreviousActorLocation = FVector::ZeroVector;'},ensure_ascii=True,indent=2),encoding='utf-8')
print('Applied only existing Action presentation branch/history in private workspace')