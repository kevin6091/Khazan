"""Reuse the actual-attack driver with a focused, denser visual inspection cadence."""
from pathlib import Path
import hashlib
import os

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
output = Path(os.environ['KZ_ATTACK_VFX_POLISH_OUTPUT']).resolve()
assert output.is_relative_to(MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008/Processes')
source = MAIN / 'Scripts/Art/player_attack_vfx_pie.py'
code = source.read_text(encoding='utf-8')
replacements = {
"VERIFY_MAIN = os.environ.get('KZ_ATTACK_VFX_VERIFY_MAIN') == '1'": "VERIFY_MAIN = WORK == ROOT",
"OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008' / ('MainRuntimePIE' if VERIFY_MAIN else 'RuntimePIE')": "OUT = Path(os.environ['KZ_ATTACK_VFX_POLISH_OUTPUT']).resolve()",
"LOG = OUT / 'PrivatePIE.log'": "LOG = OUT / 'Editor.log'",
"slot = int(position * 2)": "slot = int(position * 30)",
"CAPTURE_COUNTS.get(key, 0) >= 24 or len(REPORT['captures']) >= 300": "CAPTURE_COUNTS.get(key, 0) >= 72 or len(REPORT['captures']) >= 650",
"position = anim.montage_get_position(montage)": "position = anim.montage_get_position(montage)",
"key = montage.get_name() + '_' + section": "key = montage.get_name() + '_' + section\n        selected = {'AM_DAS_WeakAttackCombo_Attack01', 'AM_DAS_WeakAttackCombo_Attack03', 'AM_DAS_StrongAttackCombo_Attack03', 'AM_DAS_StrongChargeAttack_ChargeAttack03', 'AM_DAS_StrongChargeAttack_ChargeAttack04', 'AM_DAS_Player_SpinningAttack_SpinningAttack01', 'AM_DAS_Player_SpinningAttack_SpinningAttack02', 'AM_DAS_Player_OverFury_OverFury', 'AM_DAS_BrutalFront_Attack1', 'AM_DAS_BrutalFront_Attack2', 'AM_DAS_BrutalBack_Attack1', 'AM_DAS_BrutalBack_Attack2'}\n        if key not in selected:\n            return",
"'boundary': 'Real RHI and native test; test fixture is not original-game input or pixel parity.'": "'boundary': 'Focused nominal30Hz actual-attack capture; expensive capture/frame cadence can skip short effects. Before native test may fail historical HP0 assertions after user updated product Brutal damage50; visual baseline is not a new runtime pass. No original-game pixel parity.'"}
for old, new in replacements.items():
    assert code.count(old) == 1, old
    code = code.replace(old,new)
if os.environ.get('KZ_ATTACK_VFX_POLISH_FOCUSED_DIRECTION') == '1':
    guard = "        if key not in selected:\n            return"
    assert code.count(guard) == 1
    code = code.replace(guard, "        windows = {'AM_DAS_WeakAttackCombo_Attack01': (0.25, 0.85), 'AM_DAS_StrongAttackCombo_Attack03': (9.5, 10.5), 'AM_DAS_Player_SpinningAttack_SpinningAttack01': (0.3, 1.0)}\n        if key not in windows or not windows[key][0] <= position <= windows[key][1]:\n            return")
    code = code.replace('1280, 720', '640, 360').replace('slot = int(position * 30)', 'slot = int(position * 10)')
    code = code.replace('>= 72 or len(REPORT[\'captures\']) >= 650', '>= 16 or len(REPORT[\'captures\']) >= 48')
if os.environ.get('KZ_ATTACK_VFX_POLISH_FOCUSED_BRUTAL') == '1':
    # Technical capture scope only; the complete native18+5 test still runs.
    guard = "        if key not in selected:\n            return"
    assert code.count(guard) == 1
    code = code.replace(guard, "        windows = {'AM_DAS_BrutalFront_Attack2': (2.1, 2.95), 'AM_DAS_BrutalBack_Attack2': (2.1, 2.95)}\n        if key not in windows or not windows[key][0] <= position <= windows[key][1]:\n            return")
    code = code.replace('1280, 720', '640, 360')
    code = code.replace('>= 72 or len(REPORT[\'captures\']) >= 650', '>= 48 or len(REPORT[\'captures\']) >= 160')
(output / 'DriverSource.sha256').write_text(hashlib.sha256(code.encode()).hexdigest(),encoding='utf-8')
exec(compile(code,str(source),'exec'),dict(__name__='__main__',__file__=str(source)))
