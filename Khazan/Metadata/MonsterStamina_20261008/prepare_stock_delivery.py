import datetime, hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
OUT = MAIN / 'Metadata/MonsterStamina_20261008'
PRODUCT = [
 'Source/Khazan/KZGameplayTags.h', 'Source/Khazan/KZGameplayTags.cpp',
 'Source/Khazan/Data/KZCharacterDefinitionData.h', 'Source/Khazan/Ability/KZActionAbility.cpp',
 'Source/Khazan/Ability/KZAbilitySystemComponent.cpp',
 'Source/Khazan/Character/KZMonster.h', 'Source/Khazan/Character/KZMonster.cpp',
 'Source/Khazan/AI/KZMonsterAIController.h', 'Source/Khazan/AI/KZMonsterAIController.cpp',
 'Source/Khazan/Ability/Combo/KZComboActionAbility.h', 'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
 'Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.h', 'Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.cpp',
 'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.h', 'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp',
 'Source/Khazan/Tests/KZMonsterAIPIETest.cpp']
def read(name): return json.loads((OUT / name).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
if (OUT / 'PreparedDeliveryManifest.json').exists(): raise RuntimeError('Preserve prepared manifest')
assert read('NativePIE.json')['success'] and read('IntegratedRegression.json')['success']
assert read('WorkSavedReload.json')['success']
assert 'Result: Succeeded' in (OUT / 'StockDeliveryBuild.log').read_text(encoding='utf-8', errors='replace')
baseline = read('MainSourceBaselineAfterCollision.json')
tested = read('IntegratedTestedSource.json')['source_config']
for relative in PRODUCT:
    assert sha(WORK / relative) == tested[relative], 'Untested source: ' + relative
for relative, expected in baseline.items():
    assert sha(MAIN / relative) == expected, 'Main source changed: ' + relative
    if relative not in PRODUCT:
        assert sha(WORK / relative) == expected, 'Stale non-owned source/config: ' + relative
author, bodies = read('Authoring.json'), read('BodiesAuthoring.json')
packages = set(author['saved_packages']) | set(bodies['saved_packages'])
packages |= {x['package'] for x in read('LatestCombatBlendSpaceAuthoring.json')['families']}
asset_before = {x['package']:x['main_before'] for x in read('AssetBaseline.json')['rows']}
for row in read('LatestInputBlendSpaceIntake.json')['rows']:
    if '/BS_Combat_' in row['relative']:
        asset_before['/Game/' + row['relative'].removeprefix('Content/').removesuffix('.uasset')] = row['main_before']
rows = []
for relative in PRODUCT:
    expected = baseline.get(relative)
    assert sha(MAIN / relative) == expected
    rows.append(dict(relative=relative, before=expected, after=sha(WORK / relative), kind='source'))
for package in sorted(packages):
    assert package in asset_before, 'Missing pre-author asset baseline: ' + package
    relative = 'Content/' + package.removeprefix('/Game/') + '.uasset'
    assert sha(MAIN / relative) == asset_before[package], 'Main asset changed: ' + package
    assert (WORK / relative).is_file()
    rows.append(dict(relative=relative, package=package, before=asset_before[package], after=sha(WORK / relative), kind='asset'))
module = WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll'
module_sha = sha(module); alias = 'UnrealEditor-KhazanStamina20261008-' + module_sha[:12] + '.dll'
manifest = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), main=str(MAIN), work=str(WORK),
 rows=rows, runtime_source_count=15, dev_source_count=1, asset_count=len(packages),
 dll_sha256=module_sha, pdb_sha256=sha(WORK / 'Binaries/Win64/UnrealEditor-Khazan.pdb'), alias=alias,
 main_modules_before=sha(MAIN / 'Binaries/Win64/UnrealEditor.modules'),
 main_canonical_dll_before=sha(MAIN / 'Binaries/Win64/UnrealEditor-Khazan.dll'),
 tested_editor_helpers_removed=True, stock_build_cs_preserved=True)
(OUT / 'PreparedDeliveryManifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(dict(runtime_sources=15, dev_sources=1, assets=len(packages), alias=alias)))
