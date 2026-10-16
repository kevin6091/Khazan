"""Root candidate freeze; only report/source-evidence copies, no product writes."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_AttackVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
ready = read(OUT / 'PrivateReady.json')
assert not (OUT / 'FrozenCandidateManifest.json').exists()
world = read(OUT / 'WorldAtlasCandidateManifest.json')['asset_candidates']
blood = read(OUT / 'Blood/BloodCandidateManifest_Final.json')['rows']
assert len(world) == 6 and len(blood) == 4
art = []
for row in world + blood:
    asset = row['asset']
    relative = 'Content/' + asset.removeprefix('/Game/') + '.uasset'
    current = row.get('after_private_sha256', row.get('expected_private_sha256'))
    assert sha(WORK / relative) == current
    assert sha(MAIN / relative) == row['before_main_sha256'] == ready['baseline']['Content/_Art/Effects'][relative]
    package = row['source_package']
    source = MAIN / 'Content/_Art/Effects/Metadata/Extraction_20261006/Source' / (package + '.json')
    assert sha(source) == row['source_sha256']
    evidence = OUT / 'OriginalSources' / (package + '.json')
    evidence.parent.mkdir(parents=True, exist_ok=True)
    assert not evidence.exists()
    shutil.copy2(source, evidence)
    art.append(dict(asset=asset, before_main_sha256=row['before_main_sha256'], expected_private_sha256=current,
        source_package=package, source_sha256=row['source_sha256'],
        source_evidence=dict(path=evidence.relative_to(MAIN).as_posix(), sha256=sha(evidence)),
        change_kind='user-requested temporary double density/burst tuning' if asset.rsplit('/',1)[-1] in
            ('PP_Dmg_Blood_Trail', 'PP_Dmg_Blood_Trail_Sub') else 'source-supported material recovery adapter'))
sources = []
for relative in ('Source/Khazan/Ability/KZActionAbility.h', 'Source/Khazan/Ability/KZActionAbility.cpp',
                 'Source/Khazan/Tests/KZCombatEffectPIETest.cpp'):
    assert sha(MAIN / relative) == ready['baseline']['Source'][relative]
    sources.append(dict(file=relative, before_main_sha256=sha(MAIN / relative), expected_private_sha256=sha(WORK / relative)))
result = dict(status='FrozenForPolishDelivery', producer_role='root', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    private_ready_sha256=sha(OUT / 'PrivateReady.json'), module_alias='UnrealEditor-KhazanPlayerAttackVFXPolish20261008',
    selected_sources=sources, art=art, evidence={}, build_evidence_directory='BuildFinal01',
    verification_state='candidate bytes frozen; final RHI/saved/visual proof pending',
    scope_change=dict(root_authorized=True, reason='Fix stale notify-time bone anchors: source-supported owner-ground9 and first finalized attached13; Ability-owned one-shot cleanup, no montage retime or damage change',
        allowed_sources=['Source/Khazan/Ability/KZActionAbility.h', 'Source/Khazan/Ability/KZActionAbility.cpp']))
(OUT / 'FrozenCandidateManifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(art=len(art), sources=len(sources), Main_product_writes=0)))
