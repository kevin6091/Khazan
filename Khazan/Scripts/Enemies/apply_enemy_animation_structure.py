"""Move every retained Enemy animation into the canonical playback structure.

Run inside Unreal Editor after backup_enemy_animation_structure.py.
"""
import collections
import hashlib
import json
import pathlib
import traceback

import unreal

PROJECT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORTS = PROJECT / 'Saved/ImportReports'
PLAN_PATH = REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json'
BACKUP_PATH = REPORTS / 'HeinMachEnemy_AnimationStructureBackup_20260909.json'
EXECUTION_PATH = REPORTS / 'HeinMachEnemy_AnimationStructureExecution_20260909.json'
ROOT = '/Game/_Art/Enemies'
VERSION = '20260909_PlaybackUnifiedV1'
EAL = unreal.EditorAssetLibrary


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk_file(package):
    path = PROJECT / (package.replace('/Game/', 'Content/') + '.uasset')
    assert path.resolve().is_relative_to((PROJECT / 'Content/_Art/Enemies').resolve())
    return path


def data_for(registry, package):
    return list(registry.get_assets_by_package_name(package, include_only_on_disk_assets=False) or [])


def asset_class(registry, package):
    rows = data_for(registry, package)
    return str(rows[0].asset_class_path.asset_name) if len(rows) == 1 else None


def verify_backup(plan, backup):
    assert sha(PLAN_PATH) == backup['plan_sha256']
    backup_root = pathlib.Path(backup['backup'])
    for row in backup['changed_assets']:
        copy = backup_root / row['file']
        assert copy.is_file() and sha(copy) == row['sha256'], ('Backup mismatch', row['asset'])
    for name, value in backup['protected_worktree_files'].items():
        path = PROJECT / name
        assert path.is_file() and sha(path) == value, ('Protected work changed before apply', name)
    assert plan['rename_count'] == 884 and plan['delete_equivalent_legacy_count'] == 3


def set_playback_metadata(sequence, row):
    current_role = EAL.get_metadata_tag(sequence, 'EnemyArtRole')
    if current_role != 'PlaybackSequence':
        assert current_role == row['previous_role'], (row['new_asset'], current_role, row['previous_role'])
    EAL.set_metadata_tag(sequence, 'PreviousEnemyArtRole', row['previous_role'])
    EAL.set_metadata_tag(sequence, 'EnemyArtRole', 'PlaybackSequence')
    EAL.set_metadata_tag(sequence, 'PlaybackDerivation', row['playback_derivation'])
    EAL.set_metadata_tag(sequence, 'CanonicalAnimationStructureVersion', VERSION)
    EAL.set_metadata_tag(sequence, 'CanonicalPlaybackPath', row['new_asset'])
    if row['playback_derivation'] == 'CompositeBake':
        usage = 'Runtime playback sequence. Composite segment rates and DilationCurve are already baked; do not apply them again.'
    else:
        usage = 'Runtime playback sequence using the original AnimSequence timeline directly; stored frame rate, length and RateScale are preserved.'
    EAL.set_metadata_tag(sequence, 'PlaybackUsage', usage)
    assert EAL.get_metadata_tag(sequence, 'OriginalPackage') == row['original_package']
    if not EAL.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError('Save failed ' + row['new_asset'])


def main():
    plan = read(PLAN_PATH)
    backup = read(BACKUP_PATH)
    verify_backup(plan, backup)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True, include_searchable_names=False,
        include_soft_management_references=True, include_hard_management_references=True)
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not any(package.get_name().startswith(ROOT) for package in dirty), 'Unsaved Enemy packages must be preserved'
    progress = {'status': 'running', 'renamed': 0, 'metadata_saved': 0, 'legacy_deleted': 0,
        'redirectors_deleted': 0, 'batches': [], 'error': None}
    write(EXECUTION_PATH, progress)
    try:
        changed_by_asset = {row['asset']: row for row in backup['changed_assets']}
        for row in plan['legacy_duplicates']:
            old = row['old_asset']
            if not disk_file(old).exists():
                progress['legacy_deleted'] += 1
                continue
            expected = changed_by_asset[old]
            assert sha(disk_file(old)) == expected['sha256']
            assert not registry.get_referencers(old, options), ('Legacy Idle is referenced', old)
            asset = unreal.load_asset(old)
            assert isinstance(asset, unreal.AnimSequence)
            assert EAL.delete_loaded_assets([asset]), 'Delete legacy duplicate failed ' + old
            assert not disk_file(old).exists(), old
            progress['legacy_deleted'] += 1
            write(EXECUTION_PATH, progress)
        groups = collections.defaultdict(list)
        for row in plan['renames']:
            groups[row['new_asset'].rsplit('/', 1)[0]].append(row)
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        for folder in sorted(groups):
            batch = groups[folder]
            pending = []
            for row in batch:
                old_class = asset_class(registry, row['old_asset'])
                new_class = asset_class(registry, row['new_asset'])
                if new_class == 'AnimSequence' and old_class in (None, 'ObjectRedirector'):
                    continue
                assert old_class == 'AnimSequence' and new_class is None, (row['old_asset'], old_class, row['new_asset'], new_class)
                expected = changed_by_asset[row['old_asset']]
                assert sha(disk_file(row['old_asset'])) == expected['sha256']
                asset = unreal.load_asset(row['old_asset'])
                assert isinstance(asset, unreal.AnimSequence)
                rename = unreal.AssetRenameData()
                rename.set_editor_property('asset', asset)
                rename.set_editor_property('new_package_path', folder)
                rename.set_editor_property('new_name', row['new_name'])
                pending.append(rename)
            if pending:
                assert asset_tools.rename_assets(pending), 'Rename batch failed ' + folder
            for row in batch:
                target = unreal.load_asset(row['new_asset'])
                assert isinstance(target, unreal.AnimSequence), row['new_asset']
            progress['renamed'] += len(batch)
            progress['batches'].append({'folder': folder, 'assets': len(batch), 'renamed': True})
            write(EXECUTION_PATH, progress)
            print('ENEMY_ANIMATION_RENAME_BATCH', folder, len(batch), flush=True)
        # Store the runtime-facing role after the move. Import derivation remains
        # queryable without SRC folders or SRC names in the Content Browser.
        for index, row in enumerate(plan['renames']):
            sequence = unreal.load_asset(row['new_asset'])
            assert isinstance(sequence, unreal.AnimSequence)
            set_playback_metadata(sequence, row)
            progress['metadata_saved'] += 1
            if (index + 1) % 50 == 0:
                write(EXECUTION_PATH, progress)
                print('ENEMY_ANIMATION_METADATA', index + 1, '/', len(plan['renames']), flush=True)
        registry.search_all_assets(True)
        redirectors = []
        for row in plan['renames']:
            old = row['old_asset']
            rows = data_for(registry, old)
            if not rows:
                continue
            assert len(rows) == 1 and str(rows[0].asset_class_path.asset_name) == 'ObjectRedirector', (old, rows)
            refs = [str(x) for x in registry.get_referencers(old, options)]
            assert not refs, ('Old redirector still referenced', old, refs)
            redirector = rows[0].get_asset()
            assert str(redirector.get_class().get_name()) == 'ObjectRedirector'
            redirectors.append(redirector)
        for start in range(0, len(redirectors), 100):
            batch = redirectors[start:start + 100]
            assert EAL.delete_loaded_assets(batch), 'Redirector delete failed'
            progress['redirectors_deleted'] += len(batch)
            write(EXECUTION_PATH, progress)
        registry.search_all_assets(True)
        for row in plan['renames']:
            assert asset_class(registry, row['new_asset']) == 'AnimSequence'
            assert not data_for(registry, row['old_asset'])
            assert not disk_file(row['old_asset']).exists()
        for row in plan['legacy_duplicates']:
            assert not data_for(registry, row['old_asset']) and not disk_file(row['old_asset']).exists()
        dirty_enemy = [package for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            + unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() if package.get_name().startswith(ROOT)]
        assert not dirty_enemy, [package.get_name() for package in dirty_enemy]
        progress['status'] = 'passed'
    except Exception:
        progress['status'] = 'failed'
        progress['error'] = traceback.format_exc()
        raise
    finally:
        write(EXECUTION_PATH, progress)
    print('ENEMY_ANIMATION_STRUCTURE_APPLIED', json.dumps(progress, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
