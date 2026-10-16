"""Verify and back up three obsolete extraction-owned texture paths; nothing else."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
BACKUP = ROOT / 'Saved/ArtBackups/CombatEffects_20261006/ObsoleteTextureNames'
EXPECTED = {r['destination'].casefold(): r for r in json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))}
PATHS = ['/Game/_Art/Effects/Shared/Textures/External/BASE_Black',
         '/Game/_Art/Effects/Shared/Textures/External/BASE_Disolve',
         '/Game/_Art/Effects/Shared/Textures/External/BASE_SAPE']
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/Game/_Art/Effects'], force_rescan=True)
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
                                               include_searchable_names=True, include_soft_management_references=True,
                                               include_hard_management_references=True)
report = []
for path in PATHS:
    assert path.casefold() not in EXPECTED
    file = (ROOT / 'Content' / (path[len('/Game/'):] + '.uasset')).resolve()
    assert file.is_relative_to((ROOT / 'Content/_Art/Effects').resolve())
    if not file.exists():
        continue
    refs = [str(r) for r in (registry.get_referencers(path, options) or []) if str(r) != path]
    assert not refs, (path, refs)
    obj = unreal.load_asset(path)
    package = unreal.EditorAssetLibrary.get_metadata_tag(obj, 'KZFXSourcePackage')
    assert package and isinstance(obj, unreal.Texture), path
    owner = next(r for r in EXPECTED.values() if r['source_package'] == package)
    replacement = unreal.load_asset(owner['destination'])
    assert replacement and unreal.EditorAssetLibrary.get_metadata_tag(replacement, 'KZFXSourcePackage') == package
    raw = file.read_bytes()
    assert package.encode('ascii') in raw and b'KZFXSourcePackage' in raw
    backup = BACKUP / file.relative_to(ROOT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        assert backup.read_bytes() == raw, backup
    else:
        shutil.copy2(file, backup)
    entry = {'obsolete': path, 'source': package, 'replacement': owner['destination'], 'referencers': refs,
             'backup': str(backup), 'sha256': hashlib.sha256(raw).hexdigest()}
    assert unreal.EditorAssetLibrary.delete_loaded_asset(obj), path
    # In this engine, a successful delete can leave an original byte file.
    if file.exists():
        assert file.read_bytes() == raw
        file.unlink()
    entry['file_absent'] = not file.exists()
    report.append(entry)
(META / 'ObsoleteTextureCleanup.json').write_text(json.dumps({'status': 'passed', 'assets': report}, indent=2) + '\n', encoding='utf-8')
print('KZ_COMBAT_EFFECTS_OWNED_ORPHANS_CLEANED', flush=True)
