"""Reuse the current Main Niagara implementation and stage only the floor adapter."""
from pathlib import Path
import hashlib,json,shutil
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
OUT=MAIN/'Metadata/PlayerSlamDistort_20261012'
rels=['Source/Khazan/'+s for s in ['Animation/Notifies/KZAnimNotify_CombatEffect.h','Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Ability/KZActionAbility.cpp','Khazan.Build.cs']]
assert not (OUT/'MainMergeBaseline.json').exists()
files={}
for rel in rels:
    files[rel]=hashlib.sha256((MAIN/rel).read_bytes()).hexdigest()
    dest=OUT/'MainBeforeMerge'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/rel,dest)
    dest=OUT/'PrivateBeforeMerge'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(WORK/rel,dest)
    shutil.copyfile(MAIN/rel,WORK/rel)
rel=rels[1];p=WORK/rel;s=p.read_text(encoding='utf-8')
anchor='\tUMaterialInstanceDynamic* DecalMaterial = IsValid(Decal) ? Decal->CreateDynamicMaterialInstance() : nullptr;'
assert s.count(anchor)==1 and 'User.KZFloorNormal' not in s
s=s.replace(anchor,'''\tif (UNiagaraComponent* Niagara = Cast<UNiagaraComponent>(Component))
\t{
\t\tNiagara->SetTranslucentSortPriority(Effect.TranslucencySortPriority);
\t\tNiagara->SetCustomTimeDilation(Effect.CustomTimeDilation);
\t\tif (Effect.bSpawnOnFloor)
\t\t{
\t\t\t// Local-space sprite normals follow the traced floor, including slopes.
\t\t\tNiagara->SetVariableVec3(TEXT("User.KZFloorNormal"),
\t\t\t\tEffectWorld.GetRotation().UnrotateVector(FloorHit.ImpactNormal));
\t\t}
\t}
'''+anchor)
p.write_text(s,encoding='utf-8')
(OUT/'MainMergeBaseline.json').write_text(json.dumps({'files':files,'reuse_current_main':['NiagaraTemplate','Niagara module','generic UFXSystemComponent execution/cleanup'],'delivery_runtime':[rel]},indent=2)+'\n',encoding='utf-8')
print('SLAM_MERGE_STAGED',rel)
