import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
meta = main / 'Metadata/MonsterStamina_20261008'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
completed = json.loads((main / 'Metadata/PlayerAttackCollision_20261008/FinalDeliveryVerification.json').read_text(encoding='utf-8-sig'))
if completed['status'] != 'VerifiedDelivered':
    raise RuntimeError('External collision delivery has not completed')
relative = [
    'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
    'Source/Khazan/Ability/Combo/KZComboActionAbility.h',
    'Source/Khazan/Ability/Combo/KZComboDefinitionData.h',
    'Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp',
    'Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset',
    'Content/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.uasset',
]
rows = []
for rel in relative:
    src, dst = main / rel, work / rel
    before, after = sha(dst), sha(src)
    if not after:
        raise RuntimeError('Missing completed Main file ' + rel)
    if before != after:
        if before:
            backup = meta / 'BeforeCollisionIntake' / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                raise RuntimeError('Intake backup already exists; do not repeat')
            shutil.copy2(dst, backup)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if sha(dst) != after or sha(src) != after:
        raise RuntimeError('Intake source changed during copy ' + rel)
    rows.append(dict(path=rel, work_before=before, main_and_work=after, copied=before != after))
baseline = {p.relative_to(main).as_posix(): sha(p) for folder in ('Source', 'Config') for p in (main / folder).rglob('*') if p.is_file()}
(meta / 'MainSourceBaselineAfterCollision.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
(meta / 'CompletedCollisionIntake.json').write_text(json.dumps(dict(success=True, utc=datetime.now(timezone.utc).isoformat(), main_write=False, rows=rows, source_config_count=len(baseline)), indent=2), encoding='utf-8')
print(json.dumps(dict(success=True, copied=sum(x['copied'] for x in rows), rows=rows), indent=2))
