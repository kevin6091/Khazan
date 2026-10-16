"""Fresh read-only saved audit for the existing six plus new two Brutal montages."""
from pathlib import Path
import json
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
author = json.loads((OUT / 'Authoring/CombinedPrivateAuthoring.json').read_text(encoding='utf-8'))
assert author['status'] == 'passed' and len(author['montages']) == 8 and len(author['events']) == 401
source = MAIN / 'Scripts/Art/player_attack_vfx_saved_audit.py'
code = source.read_text(encoding='utf-8-sig')
replacements = {"'PreparedPlaybackPlan.json'": "'CombinedPreparedPlaybackPlan.json'",
                "'Authoring/PrivateAuthoring.json'": "'Authoring/CombinedPrivateAuthoring.json'",
                "len(paths) == 6 and len(PLAN['events']) == 347": "len(paths) == 8 and len(PLAN['events']) == 401",
                "six authored montages and 347 source windows": "eight authored montages and 401 source windows",
                "REPORT['checked_event_ids'] == 347": "REPORT['checked_event_ids'] == 401",
                "'SavedAssetAuditExports'": "'CombinedSavedAssetAuditExports'",
                "'SavedAssetAudit.json'": "'CombinedSavedAssetAudit.json'",
                "OUT / 'Authoring' / (name + '_Before.t3d')": "OUT / AUTHOR['before_export_directories'][path] / (name + '_Before.t3d')",
                "OUT / 'Authoring' / (name + '_After.t3d')": "OUT / AUTHOR['before_export_directories'][path] / (name + '_After.t3d')"}
for before, after in replacements.items():
    assert code.count(before) == 1, before
    code = code.replace(before, after)
exec(compile(code, str(source), 'exec'), {'__name__': '__main__', '__file__': str(source)})
print('KZ_PLAYER_ATTACK_VFX_COMBINED_SAVED_AUDIT_FINISHED', flush=True)
