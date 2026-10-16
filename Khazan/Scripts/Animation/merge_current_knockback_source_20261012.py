from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parents[2];W=P.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan';O=P/'Metadata/AnimationTimingKnockback_20261012'
assert not (O/'RuntimeMergeBaseline.json').exists()
rels=['Source/Khazan/Data/KZCharacterDefinitionData.h','Source/Khazan/Ability/KZHitReactionAbility.cpp','Source/Khazan/Ability/KZHitReactionAbility.h']
files={}
for r in rels:
 files[r]=hashlib.sha256((P/r).read_bytes()).hexdigest();d=O/'MainBeforeRuntimeMerge'/r;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/r,d);shutil.copyfile(P/r,W/r)
p=W/rels[0];s=p.read_text(encoding='utf-8');anchor='\tfloat KnockbackDistance = 250.f;'
assert s.count(anchor)==1 and 'KnockbackTimeMappingCurve' not in s
s=s.replace(anchor,anchor+'\n\t// Optional normalized distance-over-time profile; current monster curve is\n\t// assistant TEMP tuning, not recovered original curve keys.\n\tUPROPERTY(EditAnywhere, Category = "Reaction|Movement")\n\tTObjectPtr<class UCurveFloat> KnockbackTimeMappingCurve;');p.write_text(s,encoding='utf-8')
p=W/rels[1];s=p.read_text(encoding='utf-8');anchor='ERootMotionFinishVelocityMode::SetVelocity, FVector::ZeroVector, 0.f, nullptr, nullptr);'
assert s.count(anchor)==1
s=s.replace(anchor,'ERootMotionFinishVelocityMode::SetVelocity, FVector::ZeroVector, 0.f, nullptr,\n\t\t\tbLaunch ? nullptr : Settings.KnockbackTimeMappingCurve.Get());');p.write_text(s,encoding='utf-8')
(O/'RuntimeMergeBaseline.json').write_text(json.dumps({'files':files,'preserved':'ARCH-94 Player deadline/ground-hit classification and CharacterDefinition OriginalPatternStateTree','delivery':[rels[0],rels[1]]},indent=2)+'\n',encoding='utf-8')
print('CURRENT_RUNTIME_MERGED',len(rels))
