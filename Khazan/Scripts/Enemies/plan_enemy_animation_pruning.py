"""Read saved source metadata before deciding which original animations are redundant.

Run with the engine's standalone Python. Does not mutate UE assets.
"""
import collections
import json
import pathlib
import re

PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / 'Saved/ImportReports'
META = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def references(value, field=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from references(child, field + '.' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from references(child, field + '[%d]' % index)
    elif isinstance(value, str):
        # Include soft paths and typed object strings as well as ObjectPath.
        match = re.search(r"(?:/Game/|BBQ/Content/)[^'\"\s]+", value)
        if match:
            yield match.group(0).split('.')[0].replace('/Game/', 'BBQ/Content/'), field, value


def main():
    assert not (REPORTS / 'HeinMachEnemy_AnimationPruning_Backup_20260909.json').exists(), 'Plan frozen by backup; use the existing plan to resume, or create a separately reviewed run'
    manifest = read(META / 'AnimationImportManifest.json')
    comparison = read(PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/Cleanup_20260909/HeinMachEnemy_PlaybackComparison_20260909.json')
    scan = read(REPORTS / 'HeinMachEnemy_PlaybackOnly_InitialScan_20260909.json')
    sources = {r['source_package']: r for r in manifest if r['kind'] == 'SourceSequence'}
    playback = {r['source_package']: r for r in manifest if r['kind'] == 'PlaybackClip'}
    source_root = PROJECT / 'Saved/Extracted/HeinMachEnemiesV2/Metadata'
    consumers = collections.defaultdict(list)
    for path in source_root.rglob('*.json'):
        package = path.relative_to(source_root).as_posix()[:-5]
        for index, obj in enumerate(read(path)):
            if not isinstance(obj, dict):
                continue
            for target, field, raw in references(obj.get('Properties', {}), 'Properties'):
                if target in sources and package != target:
                    consumers[target].append({'package': package, 'export': obj.get('Name'),
                        'class': obj.get('Type'), 'field': field, 'value': raw,
                        # A weapon notify in a baked composite remains a direct
                        # consumer: baking body keys does not implement that notify.
                        'baked_composite': package in playback and obj.get('Type') == 'AnimComposite'
                        and field.startswith('Properties.AnimationTrack.AnimSegments[')})
    rows = []
    for package, source in sources.items():
        asset = source['destination']
        clips = [r for r in comparison['clips'] if asset in r['source_assets']]
        direct = [r for r in consumers[package] if not r['baked_composite']]
        rows.append({'asset': asset, 'source_package': package, 'family': source['family'],
            'seconds': source['duration'], 'fps': source['fps'],
            'project_referencers': scan['source_refs'].get(asset, []),
            'original_direct_consumers': direct,
            'original_baked_composite_consumers': [r for r in consumers[package] if r['baked_composite']],
            'playback_assets': [r['asset'] for r in clips],
            'equivalent_playbacks': [r['asset'] for r in clips if r['classification'] == 'EquivalentSourceTimeline']})
        row = rows[-1]
        row['decision'] = 'DeleteBackingSource' if clips and not direct and not row['project_referencers'] else 'RetainOriginal'
        row['retention_reasons'] = ([reason for condition, reason in [
            (bool(row['project_referencers']), 'CurrentProjectConsumer'),
            (bool(direct), 'OriginalDirectConsumerNotReplaced'),
            (not clips, 'NoBakedPlaybackCoverage')] if condition])
    result = {'status': 'planned', 'source_count': len(rows),
        'original_direct_source_count': sum(bool(r['original_direct_consumers']) for r in rows),
        'without_composite_count': sum(not r['playback_assets'] for r in rows),
        'decision_counts': dict(collections.Counter(r['decision'] for r in rows)),
        'policy': 'Delete only current-unreferenced source assets whose known original consumers are baked composite segments. Keep direct source consumers and motions without playback coverage. No assertion about undiscovered original-game consumers.',
        'sources': rows}
    (REPORTS / 'HeinMachEnemy_AnimationPruning_Metadata_20260909.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'sources'}))
    print('DIRECT_CLASSES', dict(collections.Counter(c['class'] for r in rows for c in r['original_direct_consumers'])))
    print('ACTIVE_PROJECT', [(r['source_package'], len(r['project_referencers'])) for r in rows if r['project_referencers']])
    print('DELETE_BYTES', sum((PROJECT / (r['asset'].replace('/Game/', 'Content/') + '.uasset')).stat().st_size for r in rows if r['decision'] == 'DeleteBackingSource'))


if __name__ == '__main__':
    main()
