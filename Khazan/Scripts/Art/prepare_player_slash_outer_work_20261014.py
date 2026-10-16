"""Make a current Main snapshot with only the five slash montages writable."""
from pathlib import Path
import hashlib
import json
import os
import shutil

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
work = main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
out = main/'Metadata/PlayerSlashOuter_20261014'
assert main.exists() and not work.exists() and work.parent.parent == main.parent.parent
targets = [
    'Content/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_Player_DodgeAttack.uasset',
    'Content/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack.uasset',
    'Content/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongAttackCombo.uasset',
    'Content/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongChargeAttack.uasset',
    'Content/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo.uasset',
]
work.mkdir(parents=True)
shutil.copy2(main/'Khazan.uproject', work/'Khazan.uproject')
for folder in ('Source', 'Config', 'Scripts'):
    shutil.copytree(main/folder, work/folder, ignore=shutil.ignore_patterns('__pycache__'))
for folder in ('Content', 'Plugins'):
    for base, dirs, files in os.walk(main/folder):
        dirs[:] = [d for d in dirs if d not in ('Intermediate', 'Saved', 'DerivedDataCache')]
        rel = Path(base).relative_to(main)
        dest = work/rel
        dest.mkdir(parents=True, exist_ok=True)
        for name in files:
            os.link(Path(base)/name, dest/name)

manifest = main/'Binaries/Win64/UnrealEditor.modules'
data = json.loads(manifest.read_text(encoding='utf-8-sig'))
binary = main/'Binaries/Win64'/data['Modules']['Khazan']
bin_dir = work/'Binaries/Win64'
bin_dir.mkdir(parents=True)
shutil.copy2(manifest, bin_dir/manifest.name)
shutil.copy2(binary, bin_dir/binary.name)

reference = 'Metadata/CombatImpactUpgrade_20261012/WeaponSlashProbe04/WeaponProbe.json'
(work/reference).parent.mkdir(parents=True)
shutil.copy2(main/reference, work/reference)

receipt = {'main': str(main), 'work': str(work), 'targets': {},
           'binary': binary.name, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}
for rel in targets:
    src, dst = main/rel, work/rel
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    dst.unlink()
    shutil.copy2(src, dst)
    assert not os.path.samefile(src, dst)
    receipt['targets'][rel] = digest
out.mkdir(parents=True, exist_ok=True)
(out/'WorkPreparation.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SLASH_OUTER_WORK_PREPARED', work, len(targets))
