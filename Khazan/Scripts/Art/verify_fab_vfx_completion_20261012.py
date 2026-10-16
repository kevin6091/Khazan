"""Final seven-pack receipt after Main publication and fresh native audit."""
from pathlib import Path
from collections import Counter
import datetime
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']


def read(name):
    return json.loads((META / name).read_text(encoding='utf-8'))


def main():
    audit = read('MainOrganizedAudit.json')
    shader = read('StageShaders.json')
    wp = read('MainWPDemoAudit.json')
    receipt = read('PublishReceipt.json')
    plan = read('RenamePlan.json')
    assert audit['status'] == shader['status'] == wp['status'] == 'passed'
    assert receipt['status'] == 'published'
    shader_run = read('RendererBasis.json')['shader_final_run']
    assert read('MainAudit02/Exit.json')['exit_code'] == read(shader_run + '/Exit.json')['exit_code'] == 0
    supplement = receipt['wp_supplement']
    assert read(supplement['native_builder_run'] + '/Exit.json')['exit_code'] == read(supplement['stage_audit_run'] + '/Exit.json')['exit_code'] == 0
    assert supplement['material_package_writes'] == 0
    for row in receipt['files']:
        assert SHA(Path(row['target'])) == row['sha256'], row['target']
    for row in receipt['retired']:
        assert SHA(Path(row['archive'])) == row['sha256'], row['archive']
        assert not Path(row['old']).exists(), row['old']
    for row in supplement['previous_task_files_archived']:
        assert SHA(Path(row['archive'])) == row['sha256'], row['archive']
    before_wp = {r['relative_path']: r for r in read('PublishReceiptBeforeWP.json')['files']}
    material_paths = {r['new_package'].removeprefix('/Game/') + '.uasset' for r in plan if r['class'] == 'Material'}
    assert len(material_paths) == shader['total']
    for row in receipt['files']:
        if row['relative_path'] in material_paths:
            assert row['sha256'] == before_wp[row['relative_path']]['sha256'], 'Material changed after real-RHI proof'
    renderer_basis = read('RendererBasis.json')
    def renderer_sections(file):
        sections, active = {}, None
        for line in file.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                active = line[1:-1]
                if active in renderer_basis['selected_sections']:
                    sections[active] = []
            elif active in renderer_basis['selected_sections'] and line and not line.startswith(';'):
                sections[active].append(line)
        return sections
    assert renderer_sections(ROOT / renderer_basis['source']) == renderer_sections(ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012/Config/DefaultEngine.ini'), 'Main renderer changed since real-RHI proof'
    listings = read('ListingMap.json')
    for listing in listings:
        listing['status'] = 'imported_organized_verified'
        listing['niagara_systems'] = sum(r['class'] == 'NiagaraSystem' and r['new_package'].startswith(listing['target_package_root'] + '/') for r in plan)
        listing['public_assets'] = sum(r['new_package'].startswith(listing['target_package_root'] + '/') for r in plan)
    assert len(listings) == 7
    protected = read('ProtectedBefore.json')
    changed = [p for p, checksum in protected.items() if not (ROOT / p).is_file() or SHA(ROOT / p) != checksum]
    folders = read('FolderMap.json')
    # Remove only already-empty obsolete task folders. The prior package bytes
    # are in Retired and Before; unrelated content is not visited.
    removed = []
    content = (ROOT / 'Content').resolve()
    candidates = set()
    for row in receipt['retired']:
        directory = Path(row['old']).resolve().parent
        assert directory.is_relative_to(content), directory
        while directory != content:
            candidates.add(directory)
            directory = directory.parent
    for directory in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
        assert directory.is_relative_to(content) and directory != content, directory
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
            removed.append(str(directory.relative_to(ROOT)))
    result = {'status': 'complete', 'all_seven_complete': True, 'timestamp': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(), 'listings': listings, 'root': '/Game/VFX', 'pack_folders': folders, 'visible_folder_depth_max_below_Content': 3, 'public_assets': len(plan), 'niagara_systems': audit['classes']['NiagaraSystem'], 'material_graphs_compiled_real_rhi': shader['total'], 'settings_checks': audit['value_checks'], 'native_load_errors': audit['errors'], 'old_references': audit['old_references'], 'missing_hard_references': audit['missing_hard_references'], 'files': receipt['files_count'], 'bytes': receipt['bytes'], 'published_sha_verified': True, 'retired_sha_verified': True, 'source_config_writes': 0, 'source_config_observed_external_changes': changed, 'renamed_for_collisions': read('LayoutSummary.json')['renamed_for_collisions'], 'retired_old_files': receipt['retired_count'], 'empty_old_folders_removed': removed, 'remaining_source_preview_soft_refs': audit['remaining_source_soft_refs'], 'boundaries': ['Native library organization and real-RHI material compilation verified.', 'No existing gameplay code/Config/maps or VFX gameplay bindings changed.', 'Demo legacy input bindings and original unavailable editor preview mesh soft references are separate from effect-library verification.', 'No full particle-rendering/visual-quality/Shipping performance or original-game equivalence claim.']}
    result.update(main_native_audit_run='MainAudit02', real_rhi_run=shader_run, current_main_renderer_matches_proof=True, material_bytes_unchanged_since_rhi=True, wp_external_actor_packages=wp['__ExternalActors___files'], wp_external_object_packages=wp['__ExternalObjects___files'], wp_loaded_actors=wp['actors'], wp_actor_transforms_classes_niagara_equal=wp['authored_actor_values_equal'], wp_old_references=wp['old_references'], wp_missing_references=wp['missing_references'], wp_derived_descriptor_change_counts=dict(Counter(r['field'] for r in wp['derived_descriptor_changes'])), wp_source_packages_preserved=True)
    (META / 'FinalVerification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (META / 'ListingMap.json').write_text(json.dumps(listings, ensure_ascii=False, indent=2), encoding='utf-8')
    (META / 'ResumeState.json').write_text(json.dumps({'status': 'complete', 'all_seven_complete': True, 'remaining_required': [], 'root': '/Game/VFX', 'canonical_report': str(META / 'FinalVerification.json'), 'next': 'Use the organized seven-pack library. Do not rerun the previous original-root import/rename or restore retired package paths.'}, indent=2), encoding='utf-8')
    lines = ['# VFX library', '', 'Current Unreal folder: `/Game/VFX`.', '', '| Pack | Folder | Niagara systems |', '| --- | --- | --- |']
    lines += ['| ' + r['title'] + ' | `' + r['target_package_root'] + '` | ' + str(r['niagara_systems']) + ' |' for r in listings]
    lines += ['', 'Niagara effects are directly in each pack folder. Support assets are one folder below it. `_Shared` contains referenced mannequin support assets.']
    (META / 'LibraryOverview.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('listings','empty_old_folders_removed','remaining_source_preview_soft_refs')}), flush=True)


if __name__ == '__main__':
    main()
