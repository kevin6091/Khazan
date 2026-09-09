"""Publish current Enemy paths after the playback folder/name migration."""
import csv
import hashlib
import json
import pathlib
import shutil

PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / 'Saved/ImportReports'
OUT = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationStructure_20260909'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset_file(package, asset_class):
    return PROJECT / (package.replace('/Game/', 'Content/') + ('.umap' if asset_class == 'World' else '.uasset'))


def main():
    plan = read(REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json')
    backup = read(REPORTS / 'HeinMachEnemy_AnimationStructureBackup_20260909.json')
    execution = read(REPORTS / 'HeinMachEnemy_AnimationStructureExecution_20260909.json')
    audit = read(REPORTS / 'HeinMachEnemy_AnimationStructureAudit_20260909.json')
    assert execution['status'] == audit['status'] == 'passed'
    previous = read(PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationPruning_20260909/RetainedAssets.json')
    previous_by_asset = {row['asset']: row for row in previous['assets']}
    remap = {row['old_asset']: row['new_asset'] for row in plan['renames']}
    removed = {row['old_asset'] for row in plan['legacy_duplicates']}
    current = []
    for row in previous['assets']:
        if row['asset'] in removed:
            continue
        package = remap.get(row['asset'], row['asset'])
        path = asset_file(package, row['class'])
        assert path.is_file(), package
        current.append({'asset': package, 'class': row['class'], 'file': path.relative_to(PROJECT).as_posix(),
            'sha256': sha(path), 'bytes': path.stat().st_size})
    assert len(current) == 1219 and len({row['asset'] for row in current}) == 1219
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / 'CurrentAssets.json', {'status': 'current', 'structure_version': plan['structure_version'],
        'counts': audit['counts_after'], 'assets': sorted(current, key=lambda row: row['asset'])})
    write(OUT / 'RenameMap.json', {'structure_version': plan['structure_version'],
        'renames': [{key: row[key] for key in ('old_asset', 'new_asset', 'previous_role', 'playback_derivation', 'original_package')} for row in plan['renames']]})
    write(OUT / 'LegacyIdleDuplicates.json', {'status': 'removed_after_equivalence_check',
        'comparison_scope': 'Every frame and bone in RAW and COMPRESSED poses; numeric tolerances are validation tolerances, not gameplay values.',
        'duplicates': plan['legacy_duplicates'], 'backup': backup['backup']})
    write(OUT / 'BlueprintComponents.json', audit['blueprints'])
    write(OUT / 'StructurePolicy.json', {
        'structure_version': plan['structure_version'],
        'animation_count': audit['animation_count'],
        'name_contract': plan['name_contract'],
        'folder_contract': plan['folder_contract'],
        'metadata_contract': plan['metadata_contract'],
        'derivation_counts': audit['derivation_counts'],
        'legacy_duplicates_removed': audit['legacy_duplicates_removed'],
        'redirectors': audit['redirectors'],
        'historical_manifests_keep_old_paths': True,
        'current_paths_source': 'CurrentAssets.json and RenameMap.json',
    })
    for path in [
        REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json',
        REPORTS / 'HeinMachEnemy_AnimationStructureExecution_20260909.json',
        REPORTS / 'HeinMachEnemy_AnimationStructureAudit_20260909.json',
    ]:
        shutil.copy2(path, OUT / path.name)
    with (OUT / 'AnimationLibrary.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['Family', 'PlaybackAsset', 'Derivation', 'OriginalPackage', 'FPS', 'Samples', 'Seconds', 'RateScale', 'PreviousRole'])
        plan_by_target = {row['new_asset']: row for row in plan['renames']}
        for sequence in sorted(audit['sequences'], key=lambda row: row['asset']):
            source = plan_by_target[sequence['asset']]
            writer.writerow([sequence['family'], sequence['asset'], sequence['playback_derivation'],
                source['original_package'], '%s/%s' % tuple(sequence['fps']), sequence['samples'],
                sequence['seconds'], sequence['rate_scale'], source['previous_role']])
    doc = PROJECT / 'Docs/Art/ENEMY_ANIMATION_LIBRARY_STRUCTURE_2026-09-09.md'
    shutil.copy2(doc, OUT / 'README_KO.md')
    archive = pathlib.Path(backup['backup'])
    shutil.copytree(OUT, archive / 'Reports', dirs_exist_ok=True)
    for name in ['plan_enemy_animation_structure.py', 'backup_enemy_animation_structure.py',
                 'apply_enemy_animation_structure.py', 'verify_enemy_animation_structure.py',
                 'publish_enemy_animation_structure.py']:
        shutil.copy2(PROJECT / 'Scripts/Enemies' / name, archive / name)
    write(archive / 'ReportSHA256.json', {path.relative_to(archive).as_posix(): sha(path)
        for path in (archive / 'Reports').rglob('*') if path.is_file()})
    print('ENEMY_ANIMATION_STRUCTURE_PUBLISHED', len(current), 'assets;', len(audit['sequences']), 'animations')


if __name__ == '__main__':
    main()
