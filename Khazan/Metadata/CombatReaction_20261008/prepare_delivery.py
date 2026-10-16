from pathlib import Path
import json, hashlib, datetime
main=Path(__file__).resolve().parents[2]; out=main/'Metadata/CombatReaction_20261008'
base=json.loads((out/'StageBaseline.json').read_text(encoding='utf8')); work=Path(base['work'])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(name): return json.loads((out/name).read_text(encoding='utf-8-sig'))
assert not (out/'PreparedDelivery.json').exists(), 'Preserve existing prepared manifest'
for name in ['NativePIE_Final.json','IntegratedRegression.json','WorkSavedReload.json']:
    assert read(name)['success'], name
regression=read('IntegratedRegression.json')
expected_tests={'Khazan.Guard.PIE','Khazan.Heal.PIE','Khazan.Combat.PlayerAttackCollision.PIE','Khazan.Monster.CombatPolicyPIE'}
assert {r['test'] for r in regression['tests']}==expected_tests
assert len(regression['tests'])==4 and all(r['success'] and r['engine_result']=='Success' for r in regression['tests'])
native=read('NativePIE_Final.json')
assert not native['partial_scope']
assert (native['completed_reaction_cases'],native['completed_pair_cases'],native['completed_collision_cases'])==(32,15,3)
assert 'Result: Succeeded' in (out/'StockBuild.log').read_text(encoding='utf8',errors='replace')
owned={r['relative'] for r in base['rows'] if r['relative'].startswith('Source/') and sha(work/r['relative']) != r['main']}
owned|={'Source/Khazan/Ability/KZHitReactionAbility.h','Source/Khazan/Ability/KZHitReactionAbility.cpp'}
assert 'Source/Khazan/Khazan.Build.cs' not in owned
assert len(owned)==16, sorted(owned)
before={r['relative']:r['main'] for r in base['rows']}
known={r['relative'] for r in base['rows']}
new_source={p.relative_to(work).as_posix() for p in (work/'Source').rglob('*') if p.is_file() and p.relative_to(work).as_posix() not in known}
assert new_source=={'Source/Khazan/Ability/KZHitReactionAbility.h','Source/Khazan/Ability/KZHitReactionAbility.cpp'}, new_source
tested=read('TestedSource.json')['source_config']
main_source_config={p.relative_to(main).as_posix() for directory in ['Source','Config'] for p in (main/directory).rglob('*') if p.is_file()}
assert main_source_config=={rel for rel in before if rel.startswith(('Source/','Config/'))}, 'Main Source/Config file set changed'
work_source_config={p.relative_to(work).as_posix():sha(p) for directory in ['Source','Config'] for p in (work/directory).rglob('*') if p.is_file()}
assert work_source_config==tested, 'Work Source/Config changed after final build snapshot'
for rel,expected in before.items():
    assert sha(main/rel)==expected, 'Main changed: '+rel
    if rel.startswith(('Source/','Config/')):
        assert sha(work/rel)==tested[rel], 'Untested source: '+rel
        if rel not in owned: assert sha(work/rel)==expected, 'Non-owned source mismatch: '+rel
for rel in owned: assert sha(work/rel)==tested[rel], rel
for row in read('PlayerBlueprintIntake.json')['rows']:
    assert sha(main/row['relative'])==row['main_sha256']==sha(work/row['relative']), row['relative']
author=read('Authoring_Final.json'); collision=read('CollisionAuthoring_Final.json')
assert author['success'] and collision['success']
packages=set(author['saved_packages'])|{a['definition'].split('.')[0] for a in collision['assets']}
asset_before={r['relative']:r['main_sha256'] for r in read('BeforeAuthor.json')}
rows=[dict(relative=rel,before=before.get(rel),after=sha(work/rel),kind='source') for rel in sorted(owned)]
for package in sorted(packages):
    assert package.startswith('/Game/')
    rel='Content/'+package[6:]+'.uasset'
    expected=asset_before.get(rel)
    assert sha(main/rel)==expected, 'Main asset changed or missing pre-author baseline: '+rel
    assert sha(work/rel), rel
    rows.append(dict(relative=rel,package=package,before=expected,after=sha(work/rel),kind='asset'))
dll=work/'Binaries/Win64/UnrealEditor-Khazan.dll'; module=main/'Binaries/Win64/UnrealEditor.modules'
assert sha(dll)==read('TestedSource.json')['dll_sha256']==read('WorkSavedReload.json')['loaded_module']['sha256']
manifest=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),main=str(main),work=str(work),rows=rows,
    runtime_source_count=len(owned),new_runtime_classes=1,asset_count=len(packages),
    dll_sha256=sha(dll),pdb_sha256=sha(dll.with_suffix('.pdb')),
    alias='UnrealEditor-KhazanReaction20261008-'+sha(dll)[:12]+'.dll',
    main_modules_before=sha(module),main_canonical_dll_before=sha(main/'Binaries/Win64/UnrealEditor-Khazan.dll'))
(out/'PreparedDelivery.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({k:manifest[k] for k in ['runtime_source_count','new_runtime_classes','asset_count','alias']}))
