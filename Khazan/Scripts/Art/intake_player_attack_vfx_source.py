"""CAS refresh of private unowned Source and exact delivered Brutal DAS dependencies."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_AttackVFXWork_20261008/Khazan')
REPORTS = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008'
OUT = REPORTS / 'SourceIntake'
OWNED = {
    'Source/Khazan/Ability/Combo/KZComboActionAbility.h',
    'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp',
    'Source/Khazan/Khazan.Build.cs', 'Source/Khazan/Environment/KZSnowDeformation.h',
    'Source/Khazan/Tests/KZCombatEffectPIETest.cpp',
    'Source/Khazan/Ability/KZActionAbility.h', 'Source/Khazan/Ability/KZActionAbility.cpp',
    'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.h',
    'Source/Khazan/Ability/PlayerAbility/KZBrutalAttackAbility.cpp'}
DAS = 'Content/_Art/Player/Animation/InGame/DAS/'
BRUTAL = DAS + 'BrutalAttack/'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def inventory(root, prefix):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted((root / prefix).rglob('*')) if p.is_file()}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')

def atomic_copy(source, target, before, after):
    assert sha(source) == after and sha(target) == before, str(target) + ': CAS conflict'
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.AttackVFXIntake.tmp')
    assert not temp.exists()
    shutil.copy2(source, temp)
    try:
        assert sha(temp) == after and sha(target) == before
        os.replace(temp, target)
        if target.relative_to(WORK).parts[0] == 'Source':
            # A copied Main timestamp can precede a private cached .obj even
            # when the source bytes changed. Force normal UBT invalidation.
            os.utime(target, None)
    finally:
        if temp.exists(): temp.unlink()
    assert sha(target) == after

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--apply', action='store_true', help='Private-only refresh; never modifies Main Source/Content/Config')
    apply = args.parse_args().apply
    old = read(OUT / 'MainIntake.json')
    source = inventory(ROOT, 'Source')
    private = inventory(WORK, 'Source')
    main_das, private_das = inventory(ROOT, DAS), inventory(WORK, DAS)
    main_config, private_config = inventory(ROOT, 'Config'), inventory(WORK, 'Config')
    assert (WORK / 'Source').resolve() == WORK / 'Source'
    assert (WORK / DAS).resolve() == WORK / DAS, 'DAS must be a private physical snapshot'
    assert not (set(old['files']) - set(source)), 'Main Source deletion requires separate review'
    changed = []
    for rel, digest in source.items():
        if rel in OWNED or private.get(rel) == digest: continue
        assert private.get(rel) == old['files'].get(rel), rel + ': private unowned source changed'
        changed.append({'relative': rel, 'before': private.get(rel), 'after': digest, 'kind': 'source'})
    delivery = ROOT / 'Metadata/MonsterStamina_20261008/PreparedDeliveryManifest.json'
    assets = [r for r in read(delivery)['rows'] if r['relative'].startswith(BRUTAL)]
    assert len(assets) == 7 and len({r['relative'] for r in assets}) == 7
    for row in assets:
        rel = row['relative']
        assert main_das.get(rel) == row['after'], rel + ': latest Main differs from verified delivery'
        assert private_das.get(rel) in (None, row['after']), rel + ': preserve existing private Brutal edit'
        if private_das.get(rel) != row['after']:
            changed.append({'relative': rel, 'before': private_das.get(rel), 'after': row['after'], 'kind': 'asset'})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    iteration = REPORTS / 'SourceIntakeHistory' / stamp
    iteration.mkdir(parents=True, exist_ok=False)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'prepared_private_only',
              'files': source, 'copied': [], 'planned': changed, 'owned_for_three_way_merge': sorted(OWNED),
              'owned_private_before': {r: private.get(r) for r in OWNED}, 'prior_intake_sha256': sha(OUT / 'MainIntake.json'),
              'main_source_before': source, 'private_source_before': private,
              'main_das_before': main_das, 'private_das_before': private_das,
              'main_config_before': main_config, 'private_config_before': private_config,
              'monster_delivery_manifest_sha256': sha(delivery), 'iteration': str(iteration), 'main_product_mutations': False}
    write(iteration / 'Prepared.json', report)
    if not apply:
        print(json.dumps({'status': report['status'], 'source': sum(r['kind'] == 'source' for r in changed),
                          'assets': sum(r['kind'] == 'asset' for r in changed), 'report': str(iteration / 'Prepared.json')}))
        return
    # Complete immutable snapshots before any private source/content copy.
    shutil.copytree(OUT, iteration / 'PreviousSourceIntake')
    next_out = iteration / 'NextSourceIntake'
    for rel, digest in source.items():
        backup = next_out / 'Main' / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, backup)
        assert sha(backup) == digest
    for row in changed:
        if row['before'] is not None:
            backup = iteration / 'PrivateBefore' / row['relative']
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(WORK / row['relative'], backup)
            assert sha(backup) == row['before']
    assert inventory(ROOT, 'Source') == source and inventory(WORK, 'Source') == private
    assert inventory(ROOT, DAS) == main_das and inventory(WORK, DAS) == private_das
    assert inventory(ROOT, 'Config') == main_config and inventory(WORK, 'Config') == private_config
    committed = []
    try:
        for row in changed:
            atomic_copy(ROOT / row['relative'], WORK / row['relative'], row['before'], row['after'])
            committed.append(row)
        expected_source, expected_das = dict(private), dict(private_das)
        for row in changed:
            (expected_source if row['kind'] == 'source' else expected_das)[row['relative']] = row['after']
        assert inventory(WORK, 'Source') == expected_source and inventory(WORK, DAS) == expected_das
        assert inventory(ROOT, 'Source') == source and inventory(ROOT, DAS) == main_das
        assert inventory(ROOT, 'Config') == main_config and inventory(WORK, 'Config') == private_config
        report.update(status='passed_private_intake', copied=[r['relative'] for r in changed],
                      private_source_after=expected_source, private_das_after=expected_das,
                      immutable_previous_intake=str(iteration / 'PreviousSourceIntake'))
        write(next_out / 'MainIntake.json', report)
        assert sha(OUT / 'MainIntake.json') == report['prior_intake_sha256']
        os.replace(OUT, iteration / 'PreviousCurrentFolder')
        os.replace(next_out, OUT)
        write(iteration / 'Applied.json', report)
    except Exception:
        for row in reversed(committed):
            target = WORK / row['relative']
            if sha(target) != row['after']: continue
            if row['before'] is None: target.unlink()
            else: atomic_copy(iteration / 'PrivateBefore' / row['relative'], target, row['after'], row['before'])
        raise
    print(json.dumps({'status': report['status'], 'copied': report['copied'], 'source_files': len(source),
                      'immutable_previous_intake': report['immutable_previous_intake'], 'receipt': str(OUT / 'MainIntake.json')}))

if __name__ == '__main__': main()
