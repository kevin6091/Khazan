"""Root-operated Saved-only assembly of the exact two-Decal/one-WPO revision.

Receipt paths and hashes are explicit CLI arguments. This never launches UE,
copies Main products, changes original manifests, or claims a visual QA pass.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import runpy

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
RES = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
TARGET = OUT / 'Authoring/VisualMaterialRepairRevision.json'
DECALS = {
    'Content/_Art/Effects/Shared/Materials/MonsterHuman/M_New_Decal_Deferred_D.uasset':
        '5f320f6bde51a0bd0de7d7297caeadedaa91e28e5f849d3f7787656d91772ecc',
    'Content/_Art/Effects/Shared/Materials/MonsterHuman/FM_Decal_Deferred_D.uasset':
        'd8a25f31feb2e33e425e0dcb2bc49e0d1644e56c1051e39ab98a2ffdf23ee5d5',
}
WPO = 'Content/_Art/Effects/Shared/Materials/Trail/FM_WPO_Trail_A.uasset'
WPO_BEFORE = '608a0ded1cd59f72a09835b512f9deb516dd2f0f622ad0e6387c9c6e78305cf2'


def sha(file):
    file = Path(file)
    return hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None


def load(file):
    return json.loads(Path(file).read_text(encoding='utf-8-sig'))


def proof(row):
    file = Path(row['path']).resolve()
    assert file.is_file() and (file.is_relative_to(OUT.resolve()) or file.is_relative_to(RES.resolve())
        or file.is_relative_to((MAIN / 'Metadata/MonsterVFX_20261008').resolve())
        or file.is_relative_to((MAIN / 'Saved/Extracted/CombatEffects_20261006').resolve())), file
    assert sha(file) == row['sha256'] and row['sha256'], file
    return file


def check_map(root, mapping):
    for relative, value in mapping.items():
        assert isinstance(relative, str) and '\\' not in relative and '..' not in Path(relative).parts
        file = (root / relative).resolve()
        assert file.is_relative_to(root.resolve()) and sha(file) == value, relative


def input_map(root):
    result = {p.relative_to(root).as_posix(): sha(p) for folder in ('Source', 'Config')
        for p in (root / folder).rglob('*') if p.is_file()}
    result['Khazan.uproject'] = sha(root / 'Khazan.uproject')
    return result


def assemble(decal_file, decal_sha, wpo_file, wpo_sha, delivered=False):
    decal_file, wpo_file = Path(decal_file).resolve(), Path(wpo_file).resolve()
    assert decal_file.is_relative_to((OUT / 'MaterialVisualRepairRevision/Decal').resolve())
    assert wpo_file.is_relative_to((OUT / 'MaterialVisualRepairRevision/Roar02').resolve())
    assert decal_file.name == wpo_file.name == 'Repair.json'
    assert sha(decal_file) == decal_sha and sha(wpo_file) == wpo_sha
    decal, wpo = load(decal_file), load(wpo_file)
    assert decal['schema'] == 'Khazan.MonsterVFX.DecalMaterialVisualRepair.v1'
    assert decal['status'] == 'passed' and decal['mode'] == 'apply' and decal['package_saves'] == 2
    assert decal['main_mutations'] == decal['source_writes'] == decal['new_material_nodes'] == 0
    assert decal['modified_own_art_count'] == 2 and Path(decal['project']).resolve() == WORK.resolve()
    assert all(decal[k] is True for k in ('main_unchanged', 'original_particle_MI_timing_unchanged',
        'all_other_455_art_unchanged', 'original_reports_immutable', 'build19_native_preserved'))
    assert wpo['schema'] == 'Khazan.MonsterVFX.Roar02MaterialVisualRepair.v1'
    assert wpo['status'] == 'passed' and wpo['package_saves'] == wpo['selected_dependency_count'] == 1
    assert wpo['source_writes'] == wpo['main_asset_writes'] == 0
    assert wpo['main_unchanged'] is True and wpo['protected_particle_and_instance_unchanged'] is True
    assert Path(wpo['project']).resolve() == WORK.resolve() and wpo['settings_before'] == wpo['settings_after']
    proof(wpo['graph_before']); proof(wpo['graph_after']); proof(wpo['fresh_probe'])
    for evidence in wpo['source_evidence']:
        proof(evidence)
    proof(decal['probe']); proof(decal['root_pixel_attribution'])
    assert decal['root_pixel_attribution']['root_confirmed'] is True
    assert decal['root_pixel_attribution']['event_id'] == 'KZMVFX_d3f1b3f723e1c147b406fa5c'
    pixel = load(decal['root_pixel_attribution']['path'])
    isolation = pixel['decal_isolation']
    assert all(isolation[k] is True for k in ('same_pose', 'same_game_time', 'same_camera_per_view'))
    assert all(isolation['restore'].values())
    # An earlier finite-tail failure is preserved. Pixel attribution is a
    # separate actual same-pose proof, not an overall Driver pass assertion.
    assert {'Normal', 'OnlyOwnD00', 'WithoutOwnD00'} <= {r['label'] for r in isolation['captures']}
    attribution_images = []
    for capture in pixel['captures']:
        image = Path(capture['image']).resolve()
        assert image.is_relative_to(Path(decal['root_pixel_attribution']['path']).parent.resolve())
        image_proof = {'path': str(image), 'sha256': sha(image)}
        proof(image_proof)
        attribution_images.append(image_proof)
    art_file = RES / 'ArtCandidateManifest.json'
    art = {r['relative_file']: r for r in load(art_file)['assets']}
    original_art = {p: r['native_sha256'] for p, r in art.items()}
    main_art = {p: r['before_main_sha256'] for p, r in art.items()}
    assert len(art) == 457 and all(original_art[p] == h and main_art[p] is None for p, h in DECALS.items())
    assert decal['art_before_sha256'] == original_art
    assert decal['main_art_before_sha256'] == decal['main_art_after_sha256'] == main_art
    assert decal['protected_private_before'] == decal['protected_private_after']
    check_map(WORK, decal['protected_private_after'])
    assert decal['immutable_report_sha256'] == decal['immutable_report_after_sha256']
    for file, value in decal['immutable_report_sha256'].items():
        assert sha(file) == value, file
    selected = {r['relative']: r for r in decal['selected_assets']}
    assert len(selected) == len(decal['selected_assets']) == 2 and set(selected) == set(DECALS)
    rows = []
    after_art = dict(original_art)
    for relative, row in selected.items():
        assert row['kind'] == 'OriginalArtOverride' and row['before_private_sha256'] == DECALS[relative]
        assert row['before_main_sha256'] is None and row['backup_sha256'] == DECALS[relative]
        backup = Path(row['backup_path']).resolve()
        assert backup == (decal_file.parent / 'Before' / relative).resolve() and sha(backup) == DECALS[relative]
        assert sha(row['source_json']) == row['source_sha256'] == art[relative]['source_sha256']
        assert row['source_package'] == art[relative]['source_package']
        proof(row['export_before']); proof(row['export_after'])
        before, after = row['graph_before'], row['graph_after']
        assert before['settings'] == after['settings'] and before['roots'] == after['roots']
        assert before['nodes'].keys() == after['nodes'].keys()
        assert row['all_other_nodes_defaults_roots_settings_preserved'] is True
        for name in before['nodes']:
            proof(row['node_exports_before'][name]); proof(row['node_exports_after'][name])
            if name != 'MaterialExpressionCustom_0':
                assert before['nodes'][name] == after['nodes'][name]
                assert row['node_exports_before'][name]['sha256'] == row['node_exports_after'][name]['sha256']
        original_pins = before['nodes']['MaterialExpressionCustom_0']['inputs']
        revised_pins = after['nodes']['MaterialExpressionCustom_0']['inputs']
        assert set(original_pins) == {'P' + str(i) for i in range(6)}
        assert set(revised_pins) == {'P' + str(i) for i in range(9)}
        assert all(revised_pins[k] == v for k, v in original_pins.items())
        assert row['code_after'] == decal['hlsl'] and row['code_before'] != row['code_after']
        assert sha(WORK / relative) == row['after_sha256'] != DECALS[relative]
        after_art[relative] = row['after_sha256']
        rows.append({k: row[k] for k in ('relative', 'before_private_sha256', 'before_main_sha256', 'after_sha256',
            'kind', 'backup_path', 'backup_sha256', 'source_json', 'source_sha256')} | {
            'author_receipt_path': str(decal_file), 'author_receipt_sha256': decal_sha})
    assert decal['art_after_sha256'] == after_art
    check_map(WORK, after_art); check_map(MAIN, after_art if delivered else main_art)
    shared_file = OUT / 'Authoring/SharedEffectsRebaseRevision.json'
    shared = load(shared_file)
    assert shared['status'] == 'passed' and shared['content_scope'] == 14
    assert sha(WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json') == sha(shared_file)
    before_reuse = shared['reuse_audit']['private_after_sha256']
    assert before_reuse == shared['reuse_audit']['main_after_sha256'] and len(before_reuse) == 2034
    assert shared['reuse_audit']['intentional_updates'] == 14 and shared['reuse_audit']['unchanged_count'] == 2020
    baseline = {p: h for p, h in load(OUT / 'WorkBaseline.json')['main_sha256'].items() if p.startswith('Content/_Art/Effects/')}
    assert len(baseline) == 2034
    assert before_reuse == dict(baseline, **{r['relative']: r['after_sha256'] for r in shared['rows']})
    assert len(shared['rows']) == 14 and not set(before_reuse) & set(original_art)
    for row in shared['rows']:
        assert sha(row['backup_path']) == row['backup_sha256'] == baseline[row['relative']]
        assert sha(MAIN / row['source_json']) == row['source_sha256']
    for file, value in shared['immutable_report_sha256'].items():
        assert sha(file) == value, file
    dependency = wpo['selected_dependencies']
    assert len(dependency) == 1 and dependency[0]['file'] == WPO
    dependency = dependency[0]
    assert dependency['before_private'] == dependency['before_main'] == before_reuse[WPO] == WPO_BEFORE
    asset = dependency['asset']
    assert asset == '/Game/' + WPO.removeprefix('Content/').removesuffix('.uasset')
    assert wpo['before_main'] == wpo['after_main'] == {asset: WPO_BEFORE}
    assert set(wpo['before_private']) == set(wpo['after_private'])
    assert {p for p in wpo['before_private'] if wpo['before_private'][p] != wpo['after_private'][p]} == {asset}
    for package, value in wpo['after_private'].items():
        assert sha(WORK / ('Content/' + package.removeprefix('/Game/') + '.uasset')) == value
    backup = Path(wpo['source_backup_root']).resolve() / WPO
    assert backup == (wpo_file.parent / 'Before' / WPO).resolve() and sha(backup) == WPO_BEFORE
    after_reuse = dict(before_reuse, **{WPO: dependency['candidate_sha256']})
    check_map(MAIN, after_reuse if delivered else before_reuse); check_map(WORK, after_reuse)
    source = wpo['source_evidence'][0]
    rows.append({'relative': WPO, 'before_private_sha256': WPO_BEFORE, 'before_main_sha256': WPO_BEFORE,
        'after_sha256': dependency['candidate_sha256'], 'kind': 'ReusedMaterialDependency',
        'backup_path': str(backup), 'backup_sha256': WPO_BEFORE, 'source_json': source['path'],
        'source_sha256': source['sha256'], 'author_receipt_path': str(wpo_file), 'author_receipt_sha256': wpo_sha})
    source_file = OUT / 'MainRebase/PlayerPolishSourceIntake.json'
    D = runpy.run_path(str(MAIN / 'Scripts/Art/deliver_monster_vfx_main_20261008.py'), run_name='revision_readonly_helpers')
    D['verify_player_polish_source_intake'](source_file, {p: h for p, h in input_map(WORK).items() if p.startswith('Source/')})
    build_dir = Path(load(OUT / 'Build/Latest.json')['attempt']).resolve()
    assert build_dir == (OUT / 'Build/Attempt19').resolve(), 'Root must explicitly revise this frozen Build19 contract for a later build'
    build = load(build_dir / 'Exit.json')
    assert build['exit_code'] == 0 and build['private_inputs_unchanged'] and build['main_inputs_unchanged']
    main_inputs = dict(build['main_inputs'])
    if delivered:
        main_inputs = {p: h for p, h in main_inputs.items() if not p.startswith('Source/')}
        main_inputs.update({p: h for p, h in build['private_inputs'].items() if p.startswith('Source/')})
    assert input_map(MAIN) == main_inputs and input_map(WORK) == build['private_inputs']
    native = {p: sha(WORK / 'Binaries/Win64' / p) for p in build['native']}
    assert len(native) == 3 and native == build['native'] == decal['native_before'] == decal['native_after']
    immutable = dict(decal['immutable_report_sha256'], **shared['immutable_report_sha256'])
    immutable[str(source_file)] = sha(source_file)
    source_intake = load(source_file)
    prior = source_intake['prior_main_rebase_intake']
    assert sha(prior['path']) == prior['sha256']
    immutable[prior['path']] = prior['sha256']
    result = {'schema': 'Khazan.MonsterVFX.VisualMaterialRepairRevision.v1',
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'passed', 'mode': 'apply',
        'main_mutations': 0, 'asset_saves': 3, 'modified_own_art_count': 2, 'modified_reused_count': 1,
        'original_art_manifest_sha256': sha(art_file), 'shared_effects_rebase_revision_sha256': sha(shared_file),
        'source_intake_sha256': sha(source_file), 'rows': sorted(rows, key=lambda r: r['relative']),
        'immutable_report_sha256': immutable, 'reuse_before_sha256': before_reuse, 'reuse_after_sha256': after_reuse,
        'art_before_sha256': original_art, 'art_after_sha256': after_art, 'main_art_before_sha256': main_art,
        'authoring_receipts': [{'path': str(decal_file), 'sha256': decal_sha}, {'path': str(wpo_file), 'sha256': wpo_sha}],
        'build19_native_preserved': True, 'actualnativeSHA': native,
        'build_proof': {'path': str(build_dir / 'Exit.json'), 'sha256': sha(build_dir / 'Exit.json')},
        'original_particle_MI_timing_unchanged': True, 'selected_delivery_count': 968,
        'pixel_attribution_images': attribution_images,
        'overall_visual_pass': False, 'fresh_saved_runtime_and_root_visual_review_required': True,
        'boundary': 'Exactly two original-Art master overrides and one reused WPO dependency. Shader topology is explicitly reconstructed; original parameter/timing bytes remain unchanged. Fresh RHI and actual image review remain required.',
        'assembler_sha256': sha(__file__)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decal-receipt', required=True)
    parser.add_argument('--decal-sha256', required=True)
    parser.add_argument('--wpo-receipt', required=True)
    parser.add_argument('--wpo-sha256', required=True)
    parser.add_argument('--write', action='store_true', help='Write new immutable MainSaved/private mirror; default is read-only preflight')
    args = parser.parse_args()
    result = assemble(args.decal_receipt, args.decal_sha256, args.wpo_receipt, args.wpo_sha256)
    if args.write:
        mirror = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json'
        assert not TARGET.exists() and not mirror.exists(), 'Preserve existing immutable revision'
        payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        for file in (TARGET, mirror):
            file.parent.mkdir(parents=True, exist_ok=True)
            with file.open('x', encoding='utf-8') as stream:
                stream.write(payload)
        assert sha(TARGET) == sha(mirror)
    print(json.dumps({'status': result['status'], 'mode': 'write' if args.write else 'preflight',
        'rows': len(result['rows']), 'selected_delivery_count': 968, 'asset_mutations': 0,
        'report': str(TARGET) if args.write else None, 'sha256': sha(TARGET) if args.write else None}))


if __name__ == '__main__':
    main()
