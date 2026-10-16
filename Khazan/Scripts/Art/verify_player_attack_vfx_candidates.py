"""Offline evidence/CAS inputs; does not write product source or assets."""
from pathlib import Path
import datetime
import hashlib
import json

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def inventory(root, folder):
    return {p.relative_to(root).as_posix(): sha(p) for p in (root / folder).rglob('*') if p.is_file()}

intake = json.loads((OUT / 'SourceIntake/MainIntake.json').read_text(encoding='utf-8'))['files']
current = inventory(MAIN, 'Source')
private = inventory(WORK, 'Source')
source_changes = [{'relative': p, 'before': current.get(p), 'after': private.get(p)}
                  for p in sorted(current.keys() | private.keys()) if current.get(p) != private.get(p)]
expected = {
    'Source/Khazan/Ability/Combo/KZComboActionAbility.h',
    'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp',
    'Source/Khazan/Environment/KZSnowDeformation.h',
    'Source/Khazan/Khazan.Build.cs',
    'Source/Khazan/Tests/KZCombatEffectPIETest.cpp',
}
author_file = OUT / 'Authoring/CombinedPrivateAuthoring.json'
if author_file.is_file():
    expected.update({
        'Source/Khazan/Ability/KZActionAbility.h',
        'Source/Khazan/Ability/KZActionAbility.cpp',
        'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.h',
        'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp',
    })
else:
    author_file = OUT / 'Authoring/PrivateAuthoring.json'
report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status': 'running', 'source_changes': source_changes,
          'MainSourceIntakeUnchanged': current == intake,
          'only_selected_private_source_changes': {r['relative'] for r in source_changes} == expected,
          'private_source': private,
          'private_native_module': sha(WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll'),
          'private_module_manifest': sha(WORK / 'Binaries/Win64/UnrealEditor.modules'),
          'native_build_exit': json.loads((OUT / 'Build/Exit.json').read_text(encoding='utf-8')),
          'MainConfig': inventory(MAIN, 'Config'), 'privateConfig': inventory(WORK, 'Config'),
          'authoring_receipt': author_file.relative_to(OUT).as_posix(),
          'montages': json.loads(author_file.read_text(encoding='utf-8'))}
try:
    assert current == intake, 'Main source changed independently; rebase before delivery'
    assert report['only_selected_private_source_changes'], 'Unexpected source difference'
    assert report['native_build_exit']['exit_code'] == 0
    build = report['native_build_exit']
    assert build['inputs_unchanged_during_build'], 'Private build inputs changed while compiling'
    compiled_source = {p: v for p, v in build['private_build_inputs'].items() if p.startswith('Source/')}
    assert compiled_source == private, 'Current private Source is not the source snapshot of the successful build'
    assert {p: v for p, v in build['private_build_inputs'].items() if p.startswith('Config/')} == report['privateConfig']
    assert build['private_build_inputs']['Khazan.uproject'] == sha(WORK / 'Khazan.uproject')
    assert build['native_binary_hashes']['UnrealEditor-Khazan.dll'] == report['private_native_module']
    assert build['native_binary_hashes']['UnrealEditor.modules'] == report['private_module_manifest']
    assert build['native_binary_hashes']['UnrealEditor-Khazan.pdb'] == sha(WORK / 'Binaries/Win64/UnrealEditor-Khazan.pdb')
    assert build['build_log_sha256'] == sha(OUT / 'Build/PrivateBuild.log')
    assert report['montages']['status'] == 'passed'
    for row in report['montages']['montages']:
        assert sha(MAIN / row['relative']) == row['before_sha256']
        assert sha(WORK / row['relative']) == row['after_sha256']
    report['status'] = 'passed_private_candidate_preflight'
except Exception as error:
    report['status'] = 'failed'
    report['error'] = str(error)
(OUT / 'NativeBuildCandidateProof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(report['status'], len(source_changes), 'source candidates', len(report['montages']['montages']), 'montages')
if report['status'] == 'failed':
    raise SystemExit(report['error'])
