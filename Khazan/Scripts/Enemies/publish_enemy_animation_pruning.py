"""Publish the new inventory while preserving all previous import/audit history."""
import csv
import json
import pathlib
import shutil
import runpy

PROJECT = pathlib.Path(__file__).resolve().parents[2]
LIB = runpy.run_path(str(PROJECT / 'Scripts/Enemies/prune_enemy_source_animations.py'), run_name='enemy_pruning')
read, write, sha = LIB['read'], LIB['write'], LIB['sha']
REPORTS = PROJECT / 'Saved/ImportReports'
OUT = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationPruning_20260909'


def main():
    audit = read(LIB['AUDIT'])
    assert audit['status'] == 'passed'
    baseline = LIB['check_baseline']()
    plan = read(LIB['PLAN'])
    execution = read(LIB['EXECUTION'])
    OUT.mkdir(parents=True, exist_ok=True)
    retained = [{k: v for k, v in r.items() if k != 'delete'} for r in baseline['assets'] if not r['delete']]
    removed = [{k: v for k, v in r.items() if k != 'delete'} for r in baseline['assets'] if r['delete']]
    write(OUT / 'RetainedAssets.json', {'status': 'current', 'counts': audit['counts_after'], 'assets': retained})
    write(OUT / 'RemovedSources.json', {'reason': plan['policy'], 'backup': baseline['backup'], 'assets': removed})
    write(OUT / 'RetainedSourceDecisions.json', {'sources': [r for r in plan['sources'] if r['decision'] == 'RetainOriginal'],
        'legacy_idles': [r for r in retained if r['class'] == 'AnimSequence' and '/PlaybackClips/' not in r['asset'] and '/SourceSequences/' not in r['asset']],
        'legacy_policy': 'No new equivalence audit for the three legacy idles; preserve rather than infer redundancy from their names.'})
    for path in [LIB['PLAN'], LIB['EXECUTION'], LIB['AUDIT']]:
        shutil.copy2(path, OUT / path.name)
    write(OUT / 'RetentionPolicy.json', {'delete_all_sources_safe': False, 'deleted_sources': execution['deleted_count'],
        'deleted_bytes': execution['deleted_bytes'], 'playback_retained': audit['playback_count'],
        'source_retained': audit['source_count'], 'legacy_idles_retained': 3,
        'current_blueprint_direct_source_assets': sum(bool(r['project_referencers']) for r in plan['sources']),
        'direct_original_source_assets': plan['original_direct_source_count'],
        'source_assets_without_baked_clip': plan['without_composite_count'],
        'policy': plan['policy'], 'all_remaining_animation_settings_unchanged': True,
        'source_metadata_preserved': True, 'previous_inventory': '../Cleanup_20260909/RetainedAssets.json'})
    with (OUT / 'AnimationRetention.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['Family', 'SourceAsset', 'OriginalPackage', 'Decision', 'Reasons', 'CurrentReferencers', 'OriginalDirectConsumers', 'PlaybackAssets'])
        for row in plan['sources']:
            writer.writerow([row['family'], row['asset'], row['source_package'], row['decision'],
                ' | '.join(row['retention_reasons']), ' | '.join(row['project_referencers']),
                ' | '.join(c['package'] + ':' + c['field'] for c in row['original_direct_consumers']), ' | '.join(row['playback_assets'])])
    doc = PROJECT / 'Docs/Art/ENEMY_SOURCE_ANIMATION_PRUNING_2026-09-09.md'
    shutil.copy2(doc, OUT / 'README_KO.md')
    archive = pathlib.Path(baseline['backup'])
    shutil.copytree(OUT, archive / 'Reports', dirs_exist_ok=True)
    for name in ['plan_enemy_animation_pruning.py', 'prune_enemy_source_animations.py', 'publish_enemy_animation_pruning.py']:
        shutil.copy2(PROJECT / 'Scripts/Enemies' / name, archive / name)
    write(archive / 'ReportSHA256.json', {p.relative_to(archive).as_posix(): sha(p) for p in (archive / 'Reports').rglob('*') if p.is_file()})
    print('ANIMATION_PRUNING_PUBLISHED', len(removed), 'removed;', len(retained), 'retained')


if __name__ == '__main__':
    main()
