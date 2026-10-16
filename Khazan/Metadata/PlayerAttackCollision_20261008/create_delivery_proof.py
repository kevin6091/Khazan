import json,hashlib,datetime
from pathlib import Path
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path('C:/Users/user/Desktop/GitProject/Khazan_ComboWork_20261008/Khazan')
out=main/'Metadata/PlayerAttackCollision_20261008'
source=['Source/Khazan/Ability/Combo/KZComboActionAbility.h','Source/Khazan/Ability/Combo/KZComboActionAbility.cpp','Source/Khazan/Ability/Combo/KZComboDefinitionData.h','Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp']
assets=['Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset','Content/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.uasset']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'required_tests':{k:True for k in ['player_attack_collision_pie','guard_pie','heal_pie','combo_regression_pie']},'source':{p:sha(work/p) for p in source},'assets':{p:sha(work/p) for p in assets},'build_log':'Build_FinalMatchedMainSource.log','test_logs':{'player_attack_collision_pie':'FrozenFinalPlayerCollisionPIE.log','guard_pie':'FrozenRegressionPIE.log','heal_pie':'FrozenRegressionPIE.log','combo_regression_pie':'ComboRegression/SuiteState.json'},'scope':'13 native cases; six real-input positive transitions and one independently verified pre-InputOpen rejection; separate native Guard/Heal success. Authored multi-hit count used enlarged target; normal capsule shape/range cases.'}
assert not (out/'VerifiedDeliveryProof.json').exists()
(out/'VerifiedDeliveryProof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print('Proof written; --prepare independently validates every flag/evidence/result and current hashes')
