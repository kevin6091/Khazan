"""Final integrity receipt; missing listing sources stay explicitly incomplete."""
from pathlib import Path
from collections import Counter
import datetime
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']


def read(name):
    return json.loads((META / name).read_text(encoding='utf-8'))


def main():
    delivery = read('Delivery.json')
    load = read('MainLoad02/AssetLoadAudit.json')
    shaders = read('MainShaders01/ShaderAudit.json')
    deps = read('StageDependencies08/DependencyAudit.json')
    assert delivery['status'] == 'delivered'
    assert load['status'] == shaders['status'] == 'passed'
    assert read('MainLoad02/Exit.json')['exit_code'] == read('MainShaders01/Exit.json')['exit_code'] == 0
    assert not load['errors'] and not shaders['errors']
    assert load['processed'] == deps['registered_packages'] == len(delivery['files'])
    rows = []
    for row in delivery['files']:
        target = Path(row['target'])
        assert SHA(target) == row['sha256'], target
        assert SHA(Path(row['source'])) == row['sha256'], row['source']
        rows.append({'path': target.relative_to(ROOT).as_posix(), 'sha256': row['sha256'], 'bytes': row['bytes']})
    protected = read('ProtectedBefore.json')
    observed_changes = [rel for rel, checksum in protected.items() if not (ROOT / rel).is_file() or SHA(ROOT / rel) != checksum]
    mappings = read('ListingMap.json')
    for pack in mappings:
        if pack['listing_id'] == 'de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4':
            pack['status'] = 'listing_unresolved'
        if pack.get('target_package_root'):
            pack['status'] = 'imported_and_native_load_verified'
            pack['niagara_systems'] = sum(r['class'] == 'NiagaraSystem' and r['package'].startswith(pack['target_package_root'] + '/') for r in deps['assets'])
    (META / 'ListingMap.json').write_text(json.dumps(mappings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    imported = [r for r in mappings if r['status'] == 'imported_and_native_load_verified']
    unavailable = [r for r in mappings if r not in imported]
    log = (META / 'MainLoad02/Editor.log').read_text(encoding='utf-8', errors='replace')
    warnings = [l for l in log.splitlines() if 'Warning:' in l and any(s in l for s in ['/Game/Cursed_Magic', '\\Cursed_Magic\\', '/Game/Characters', '\\Characters\\', '/Game/NiagaraVFXBundle', '\\NiagaraVFXBundle\\', '/Game/ARPGVFXPack03', '\\ARPGVFXPack03\\'])]
    report = {'status': 'matched_local_packs_verified_missing_sources_remain', 'all_seven_complete': False, 'matched_local_packs_complete': True, 'timestamp': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(), 'imported_packs': imported, 'unresolved_listings': unavailable, 'native_files': len(rows), 'bytes': sum(r['bytes'] for r in rows), 'public_assets_loaded': sum(r['status'] == 'loaded' for r in load['assets']), 'external_actor_object_packages': sum(r['status'] == 'external_package_registered' for r in load['assets']), 'niagara_systems': load['classes']['NiagaraSystem'], 'materials_shader_compiled': shaders['material_count'], 'shader_stats_positive_pixel_instructions': sum(r.get('pixel_instructions', 0) > 0 for r in shaders['materials']), 'compile_errors': shaders['errors'], 'load_errors': load['errors'], 'asset_classes': load['classes'], 'source_and_target_sha_verified': True, 'overwrite_count': delivery['overwrite_count'], 'asset_saves': 0, 'gameplay_source_config_uproject_writes': 0, 'source_config_uproject_observed_concurrent_changes': observed_changes, 'unresolved_source_soft_references': deps['missing_game_dependencies'], 'demo_load_warnings': warnings, 'engine_version': load['engine_version'], 'files': rows, 'boundaries': ['No gameplay Ability/Notify/Cue/Blueprint hookups or existing effect replacements.', 'Demo character legacy input bindings and copied RigVM private-memory warnings are retained; demos are not validated as playable in Khazan.', 'Five source-unavailable mannequin editor preview soft paths remain; all imported Game hard package dependencies are present.', 'Material graph real-RHI compile is verified; full-system particle rendering, individual effect visual quality and Shipping performance are not tested.', 'Fourth listing was unavailable to web fetch (403) and no browser connection was available; it is not assumed to be FlaresEffect or another local pack.']}
    (META / 'FinalVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (META / 'ResumeState.json').write_text(json.dumps({'imported_packs_complete': True, 'all_seven_complete': False, 'remaining': unavailable, 'last_verified': 'FinalVerification.json', 'resume': ['Obtain the missing local pack paths and the fourth listing title/correct URL.', 'Use LocalInventory.json and SourcePackageIndex.json; do not re-import the three completed packs.', 'Inventory only new source folders, match the exact product and engine version, then stage dependency closure at unchanged /Game paths.', 'Preflight all new targets; never overwrite unrelated project packages.', 'Deliver only new packages and run native load plus real-RHI material compile checks.', 'Append dated results to Docs/Art documents.']}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('files', 'demo_load_warnings', 'unresolved_source_soft_references', 'imported_packs', 'unresolved_listings', 'asset_classes')}), flush=True)


if __name__ == '__main__':
    main()
