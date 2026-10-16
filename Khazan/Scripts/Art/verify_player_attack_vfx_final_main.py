"""Read-only product verification; append final task evidence after Main delivery."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('selected_vfx_delivery', MAIN / 'Scripts/Art/deliver_player_attack_vfx.py')
delivery_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery_helper)
plan = read(OUT / 'MainDelivery/Prepared.json')
delivery_helper.check(plan, delivered=True)
delivery = read(OUT / 'MainDelivery/Delivered.json')
assert delivery['status'] == 'SourceContentAndNativeAliasDelivered'
assert delivery['prepared_sha256'] == sha(OUT / 'MainDelivery/Prepared.json')
manifest = MAIN / 'Binaries/Win64/UnrealEditor.modules'
assert sha(manifest) == delivery['module_manifest_sha256']
assert read(manifest)['Modules']['Khazan'] == delivery['module']
native = next(r for r in delivery['native_files'] if r['destination'].endswith('.dll'))
driver = read(OUT / 'MainRuntimePIE/Driver.json')
exit_result = read(OUT / 'MainRuntimePIE/Exit.json')
loaded = read(OUT / 'MainRuntimePIE/ActualNativeModule.json')
saved = read(OUT / 'MainCombinedSavedAssetAudit.json')
saved_exit = read(OUT / 'Processes/player_attack_vfx_main_combined_saved_audit_exit.json')
user = read(OUT / 'MainUserEditorFinalObservation.json')
review = read(OUT / 'MainRuntimePIE/RootVisualReview.json')
assert driver['status'] == 'passed' and driver['verification'] == 'fresh_saved_Main'
assert driver['package_saves'] == 0 and driver['material_compile_failures'] == []
assert 'Result={Success}' in driver['native_completion'] and exit_result['exit_code'] == 0
assert exit_result['pid'] == loaded['pid'] != plan['main_pid']
assert loaded['status'] == 'passed' and Path(loaded['actual_path']).resolve() == (MAIN / native['destination']).resolve()
assert loaded['sha256'] == native['sha256']
assert saved['status'] == 'passed' and saved['checked_event_ids'] == 401 and len(saved['montages']) == 8
assert sum(r['start_markers'] for r in saved['montages']) == 401
assert sum(r['end_markers'] for r in saved['montages']) == 401 and saved['field_checks'] == 8308
assert saved['asset_saves'] == saved['source_writes'] == 0 and saved['package_bytes_unchanged']
assert saved['selected_source_assets_unchanged'] and saved['task_owned_process'] and not saved['user_editor_controlled']
assert saved_exit['exit_code'] == 0 and saved_exit['pid'] == saved['pid'] != plan['main_pid']
assert saved['actual_loaded_module']['sha256'] == native['sha256']
assert saved['inputs']['plan_sha256'] == sha(OUT / 'CombinedPreparedPlaybackPlan.json')
assert saved['inputs']['authoring_sha256'] == sha(OUT / 'Authoring/CombinedPrivateAuthoring.json')
assert user['pid'] == plan['main_pid'] and user['world'] == plan['world']
assert user['pie'] is False and user['dirty_content'] == user['dirty_maps'] == []
assert not user['editor_saved'] and not user['editor_reloaded'] and not user['editor_closed']
assert review['status'] == 'passed_limited_actual_Main_attack_visual_review'
assert review['original_game_pixel_parity_verified'] is False
images = {r['file']: sha(OUT / 'MainRuntimePIE' / r['file']) for r in review['inspected_images']}
assert set(images) <= {Path(r['image']).name for r in driver['captures']}
paths = ('MainDelivery/Prepared.json', 'MainDelivery/Delivered.json', 'MainDelivery/MainRelease.json',
         'Build/Exit.json', 'NativeBuildCandidateProof.json', 'CombinedPreparedPlaybackPlan.json',
         'Authoring/CombinedPrivateAuthoring.json', 'CombinedSavedAssetAudit.json',
         'ResourceAudit/ArtCandidateManifest.json', 'ReviewedAttackAndFloorProof.json',
         'RuntimePIE/Driver.json', 'RuntimePIE/RootVisualReview.json',
         'MainRuntimePIE/Driver.json', 'MainRuntimePIE/Exit.json', 'MainRuntimePIE/ActualNativeModule.json',
         'MainRuntimePIE/RootVisualReview.json', 'MainRuntimePIE/PrivatePIE.log',
         'MainCombinedSavedAssetAudit.json', 'Processes/player_attack_vfx_main_combined_saved_audit_exit.json',
         'MainUserEditorFinalObservation.json')
result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='MainDeliveredAndFreshVerified',
    complete_current_attack_vfx_scope=True, selected_files=len(plan['files']), source_files=11,
    runtime_source_files=10, development_test_files=1, new_runtime_files=2,
    selected_packages=len(plan['packages']), montages=8, art_candidates=15,
    source_effect_windows=401, particle_windows=345, decal_windows=56,
    saved_start_children=401, saved_end_children=401, exact_saved_field_checks=8308,
    entry_node_cases=18, brutal_cases=5, actual_Main_captures=len(driver['captures']),
    native_module=delivery['module'], native_sha256=native['sha256'],
    full_Source_and_selected_bytes_match_compiled_private=True,
    protected_Config_Data_Maps_unselected_DAS_Effects_preserved=True,
    original_stock_and_prior_alias_binaries_preserved=True,
    main_RHI_pid=exit_result['pid'], main_saved_audit_pid=saved['pid'],
    main_RHI_elapsed_seconds=exit_result['elapsed_seconds'],
    main_saved_elapsed_seconds=saved_exit['elapsed_seconds'],
    material_compile_fallback_errors=[], Main_package_saves=0,
    user_editor=user, normal_editor_restart_required_for_new_native_notify_schema=True,
    original_game_pixel_parity_verified=False, all_401_screen_visibility_verified=False,
    shipping_performance_profiled=False,
    unsupported_source_environment_windows=dict(original_snow=65, original_water=20, added_brutal_snow=4),
    boundaries=['Source fields, references and time mappings verified; cooked shader/static-switch/VAT/refraction/normal topology incomplete.',
                'BattleEffectIndex/default CDO, first Brutal hit linkage, transform/floor/curve-age interpretations are documented project adapters.',
                'Current product BrutalHPDamage is zero; actual HP damage gates conditional blood. Positive HP/16 fixture is test-only.',
                'OverFury B01 prelude matching original effect notify remains unconfirmed; different-leaf effects were not fabricated.',
                'Capture cadence and victim occlusion limit visual coverage; no original-game pixel parity or multiplayer/shipping performance claim.'],
    frozen_manifest_supersession=dict(actual_overfury_visual_pass=True,
        actual_attack_visual_scope='Limited private 11 and Main 4 image transparency/silhouette review; no fallback/opaque quad in inspected images.',
        pending_runtime_and_Main_write_fields='Historical frozen pre-delivery fields; current delivery/hashes/results are this final receipt.',
        art_current_Main_SHA='Every selected asset equals the frozen expected_private_sha256, verified by delivered CAS check.'),
    inspected_Main_images=images, evidence_sha256={p: sha(OUT / p) for p in paths})
final = OUT / 'FinalVerification.json'
assert not final.exists(), 'Preserve an existing final receipt'
final.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('status', 'selected_files', 'selected_packages', 'source_effect_windows', 'main_RHI_pid', 'main_saved_audit_pid')}))
