"""Back up every asset changed by the unified Enemy playback structure."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess

PROJECT = pathlib.Path(__file__).resolve().parents[2]
REPORTS = PROJECT / 'Saved/ImportReports'
PLAN = REPORTS / 'HeinMachEnemy_AnimationStructurePlan_20260909.json'
BASELINE = REPORTS / 'HeinMachEnemy_AnimationStructureBackup_20260909.json'
CURRENT = PROJECT / 'Content/_Art/Enemies/HeinMach/Metadata/AnimationPruning_20260909/RetainedAssets.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_file(package):
    path = PROJECT / (package.replace('/Game/', 'Content/') + ('.umap' if package.endswith('L_HeinMach_EnemyCatalogue') else '.uasset'))
    assert path.resolve().is_relative_to((PROJECT / 'Content/_Art/Enemies').resolve())
    return path


def main():
    plan = read(PLAN)
    assert plan['status'] == 'planned' and plan['rename_count'] == 884
    assert not BASELINE.exists(), 'Never overwrite an existing animation structure baseline'
    destination = pathlib.Path.home() / 'Desktop/카잔/EnemyExtracts/AnimationStructure_20260909'
    assert not (destination / 'BackupManifest.json').exists(), 'Never overwrite an external backup baseline'
    destination.mkdir(parents=True, exist_ok=True)
    previous = read(CURRENT)
    assert previous['status'] == 'current' and len(previous['assets']) == 1222
    previous_by_asset = {row['asset']: row for row in previous['assets']}
    changed_packages = {row['old_asset'] for row in plan['renames']}
    changed_packages.update(row['old_asset'] for row in plan['legacy_duplicates'])
    referencers = sorted({package for row in plan['renames'] for package in row['referencers']})
    assert len(changed_packages) == 887 and len(referencers) == 16
    changed = []
    for package in sorted(changed_packages | set(referencers)):
        source = package_file(package)
        assert source.is_file(), package
        relative = source.relative_to(PROJECT).as_posix()
        value = sha(source)
        if package in previous_by_asset:
            assert value == previous_by_asset[package]['sha256'], ('Changed since previous audit', package)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert sha(target) == value
        changed.append({'asset': package, 'file': relative, 'sha256': value, 'bytes': source.stat().st_size,
            'kind': 'AnimSequence' if package in changed_packages else 'BlueprintReferencer'})
    retained = {}
    for row in previous['assets']:
        source = PROJECT / row['file']
        assert source.is_file() and sha(source) == row['sha256'], ('Current inventory drift', row['asset'])
        retained[row['file']] = row['sha256']
    dirty = subprocess.check_output(['git', 'ls-files', '-m', '-o', '--exclude-standard', '-z', '--', '.'], cwd=PROJECT).decode('utf-8').split('\0')
    dirty += [path.relative_to(PROJECT).as_posix() for path in (PROJECT / 'Config').glob('*.ini')]
    dirty += ['Content/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment.umap',
        'Content/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment.umap']
    protected = {}
    for name in sorted(set(dirty)):
        if not name or name.startswith(('Content/_Art/Enemies/', 'Scripts/Enemies/')):
            continue
        source = PROJECT / name
        if source.is_file():
            protected[name] = sha(source)
    result = {
        'status': 'backed_up',
        'date': datetime.datetime.now().astimezone().isoformat(),
        'backup': str(destination),
        'plan_sha256': sha(PLAN),
        'previous_inventory_sha256': sha(CURRENT),
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT).decode().strip(),
        'changed_assets': changed,
        'retained_assets': retained,
        'protected_worktree_files': protected,
    }
    write(BASELINE, result)
    write(destination / 'BackupManifest.json', result)
    shutil.copy2(PLAN, destination / PLAN.name)
    print('ENEMY_ANIMATION_STRUCTURE_BACKUP', len(changed), 'copied;', len(retained), 'inventory hashes;', len(protected), 'protected')


if __name__ == '__main__':
    main()
